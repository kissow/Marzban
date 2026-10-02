import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def load(name, file):
    spec = importlib.util.spec_from_file_location(name, ROOT / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


policy = load("test_policy_builder", "app/xray/device_policy.py")
# Isolate orchestration from the application's startup, DB and core processes.
app = types.ModuleType("app")
app.logger, app.xray = Mock(), types.SimpleNamespace(nodes={})
db = types.ModuleType("app.db")
db.GetDB, db.crud = Mock(), Mock()
node_models, user_models = types.ModuleType("app.models.node"), types.ModuleType("app.models.user")
node_models.NodeStatus = types.SimpleNamespace(disabled="disabled", connecting="connecting", connected="connected", error="error")
user_models.UserResponse = Mock()
user_models.UserStatus = types.SimpleNamespace(active="active", limited="limited", on_hold="on_hold")
concurrency = types.ModuleType("app.utils.concurrency")
concurrency.threaded_function = lambda fn: fn
node_module = types.ModuleType("app.xray.node")
node_module.XRayNode = Mock()
egress, store = types.ModuleType("app.xray.node_egress"), types.ModuleType("app.xray.node_egress_store")
egress.for_node, store.read_egress = Mock(), Mock()
api, account = types.ModuleType("xray_api"), types.ModuleType("xray_api.types.account")
api.XRay, account.Account, account.XTLSFlows = Mock(), Mock(), Mock()
with patch.dict(sys.modules, {"app": app, "app.db": db, "app.models.node": node_models,
                             "app.models.user": user_models, "app.utils.concurrency": concurrency,
                             "app.xray.node": node_module, "app.xray.device_policy": policy,
                             "app.xray.node_egress": egress, "app.xray.node_egress_store": store,
                             "xray_api": api, "xray_api.types.account": account}):
    operations = load("test_policy_operations", "app/xray/operations.py")


class DevicePolicySyncTests(unittest.TestCase):
    def setUp(self):
        app.xray.nodes = {}
        self.snapshot = [{"user": "1.alice", "device_limit": 2,
                          "device_limit_mode": "hwid", "device_limit_action": "reject_new"}]

    def node(self, result=None):
        node = Mock(connected=True, started=True)
        node.set_device_policies.return_value = result
        return node

    def test_builder_sends_only_policy_fields_and_filters_inactive_users(self):
        rows = [{"id": 1, "username": "alice", "status": "active", "device_limit": 2,
                 "device_limit_action": "reject_new", "password": "secret", "hwid": "raw"},
                {"id": 2, "username": "disabled", "status": "disabled"},
                {"id": 3, "username": "expired", "status": "expired"}]
        self.assertEqual(policy.build_device_policy_snapshot(rows), self.snapshot)

    def test_invalid_policy_does_not_silently_change_limits(self):
        with self.assertRaises(ValueError):
            policy.build_device_policy_snapshot([{"id": 1, "username": "alice", "status": "active", "device_limit": 100001}])

    def test_old_node_does_not_break_sync_or_connection(self):
        app.xray.nodes[1] = node = self.node()
        self.assertIsNone(operations.sync_node_device_policies(1, self.snapshot))
        self.assertEqual(node.device_policy_sync["policy_sync_status"], "unsupported")

    def test_valid_acknowledgement_reports_synced(self):
        app.xray.nodes[1] = node = self.node({"accepted": True, "policy_count": 1,
                                            "policy_enforcement": "subscription_request_and_node_credentials",
                                            "direct_connection_enforced": True})
        operations.sync_node_device_policies(1, self.snapshot)
        self.assertEqual(node.device_policy_sync["policy_sync_status"], "synced")

    def test_incorrect_acknowledgement_and_rpc_failure_report_failed(self):
        app.xray.nodes[1] = node = self.node({"accepted": True, "policy_count": 0})
        operations.sync_node_device_policies(1, self.snapshot)
        self.assertEqual(node.device_policy_sync["policy_sync_status"], "failed")
        node.set_device_policies.return_value = {"accepted": True, "policy_count": True,
                                                "policy_enforcement": "subscription_request_and_node_credentials",
                                                "direct_connection_enforced": True}
        operations.sync_node_device_policies(1, self.snapshot)
        self.assertEqual(node.device_policy_sync["policy_sync_status"], "failed")
        node.set_device_policies.side_effect = TimeoutError()
        operations.sync_node_device_policies(1, self.snapshot)
        self.assertEqual(node.device_policy_sync["policy_sync_status"], "failed")

    def test_batch_reads_snapshot_once_and_continues_after_a_node_failure(self):
        app.xray.nodes[1] = bad = self.node()
        bad.set_device_policies.side_effect = TimeoutError()
        app.xray.nodes[2] = good = self.node({"accepted": True, "policy_count": 1,
                                            "policy_enforcement": "subscription_request_and_node_credentials",
                                            "direct_connection_enforced": True})
        with patch.object(operations, "_read_device_policies", return_value=self.snapshot) as read:
            operations.sync_all_node_device_policies()
        read.assert_called_once()
        good.set_device_policies.assert_called_once_with(self.snapshot)
        self.assertEqual(good.device_policy_sync["policy_sync_status"], "synced")

    def test_offline_nodes_are_skipped(self):
        app.xray.nodes[1] = node = self.node()
        node.connected = False
        operations.sync_node_device_policies(1, self.snapshot)
        node.set_device_policies.assert_not_called()
