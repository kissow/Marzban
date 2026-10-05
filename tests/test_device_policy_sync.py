import importlib.util
import sys
import types
import unittest
import threading
from contextlib import ExitStack
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


class NodeConnectionOrderTests(unittest.TestCase):
    """Execute the production orchestration with isolated DB/core transports."""

    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        operations._connecting_nodes.clear()
        self.addCleanup(operations._connecting_nodes.clear)
        operations._node_retry_after.clear()
        self.addCleanup(operations._node_retry_after.clear)
        self.events = []
        self.node = Mock(connected=False)
        self.node.connect.side_effect = self.connect
        self.node.get_health.side_effect = self.health
        self.node.start.side_effect = self.start
        self.node.get_version.return_value = '26.3.27'
        self.capabilities = ['managed-outbounds-v1', 'managed-outbounds-udp-v1']
        self.profile = {'protocol': 'socks', 'server': 'proxy.example', 'port': 1080,
                        'udp_mode': 'tcp_only'}
        self.config = {'outbounds': [{'tag': 'DIRECT', 'protocol': 'freedom'}]}
        self.stack.enter_context(patch.object(operations, 'GetDB'))
        crud_mock = self.stack.enter_context(patch.object(operations, 'crud'))
        self.crud = crud_mock
        crud_mock.get_node_by_id.return_value = types.SimpleNamespace(id=1, name='test-node', status='error')
        self.stack.enter_context(patch.object(operations, 'read_egress', side_effect=lambda *a: self.profile))
        real_egress = load('test_connection_egress', 'app/xray/node_egress.py')
        self.stack.enter_context(patch.object(operations, 'for_node', real_egress.for_node))
        runtime = types.SimpleNamespace(
            nodes={}, operations=Mock(), config=Mock())
        runtime.operations.add_node.return_value = self.node
        runtime.config.include_db_users.return_value = self.config
        self.runtime = runtime
        self.stack.enter_context(patch.object(operations, 'xray', runtime))
        self.status = self.stack.enter_context(patch.object(operations, '_change_node_status'))
        self.sync = self.stack.enter_context(patch.object(operations, 'sync_node_device_policies'))
        self.accounts = self.stack.enter_context(patch.object(operations, 'sync_all_node_device_accounts'))
        self.logger = self.stack.enter_context(patch.object(operations, 'logger'))

    def connect(self):
        self.events.append('connect')
        self.node.connected = True

    def health(self):
        if not self.node.connected:
            raise ConnectionError('Node is not connected')
        self.events.append('health')
        return {'source': 'node-runtime', 'capabilities': self.capabilities}

    def start(self, config):
        self.assertTrue(self.node.connected)
        self.events.append('start')

    def run_connection(self, config=None):
        operations.connect_node(1, config)
        self.assertNotIn(1, operations._connecting_nodes)

    def test_tcp_only_connects_before_health_and_start(self):
        self.run_connection()
        self.assertEqual(self.events, ['connect', 'health', 'start'])
        self.sync.assert_called_once_with(1)
        self.accounts.assert_called_once_with()
        self.status.assert_called_with(1, node_models.NodeStatus.connected, version='26.3.27')
        self.assertNotIn('marzban_node_extensions', self.config)

    def test_proxy_mode_connects_before_health_and_start(self):
        self.profile['udp_mode'] = 'proxy'
        self.run_connection(self.config)
        self.assertEqual(self.events, ['connect', 'health', 'start'])
        self.runtime.config.include_db_users.assert_not_called()

    def test_legacy_skips_health(self):
        self.profile['udp_mode'] = 'legacy'
        self.run_connection()
        self.assertEqual(self.events, ['connect', 'start'])
        self.node.get_health.assert_not_called()
        self.assertNotIn('udp_mode', self.node.start.call_args.args[0]['marzban_node_extensions']['outbounds'][0])

    def test_no_egress_skips_health(self):
        self.profile = None
        self.run_connection()
        self.assertEqual(self.events, ['connect', 'start'])
        self.node.start.assert_called_once_with(self.config)

    def test_connected_session_is_reused(self):
        self.node.connected = True
        self.runtime.nodes[1] = self.node
        self.run_connection()
        self.assertEqual(self.events, ['health', 'start'])
        self.node.connect.assert_not_called()
        self.runtime.operations.add_node.assert_not_called()

    def test_old_node_fails_capability_check_before_start(self):
        self.capabilities = ['managed-outbounds-v1']
        self.run_connection()
        self.assertEqual(self.events, ['connect', 'health'])
        self.node.start.assert_not_called()
        self.assertIn('Upgrade', self.status.call_args.kwargs['message'])
        self.sync.assert_not_called()

    def test_auth_failure_preserves_reason_and_cleans_pending_state(self):
        self.node.connect.side_effect = ConnectionError('test authentication failed')
        self.run_connection()
        self.node.get_health.assert_not_called()
        self.node.start.assert_not_called()
        self.status.assert_called_with(1, node_models.NodeStatus.error, message='Control session / TLS: test authentication failed')
        self.assertIn('test authentication failed', self.logger.warning.call_args.args[-1])

    def test_health_failure_preserves_reason_and_allows_retry(self):
        self.node.get_health.side_effect = TimeoutError('test health timeout')
        self.run_connection()
        self.node.start.assert_not_called()
        self.status.assert_called_with(1, node_models.NodeStatus.error, message='Prepare node configuration / health: test health timeout')
        self.node.get_health.side_effect = self.health
        self.run_connection()
        self.node.start.assert_called_once()

    def test_start_api_failure_preserves_reason_and_skips_sync(self):
        self.node.start.side_effect = ConnectionError("Failed to connect to node's API")
        self.run_connection()
        self.assertEqual(self.events, ['connect', 'health'])
        self.status.assert_called_with(1, node_models.NodeStatus.error, message="Start Xray / API readiness: Failed to connect to node's API")
        self.sync.assert_not_called()
        self.accounts.assert_not_called()

    def test_expired_session_reuses_transport_without_disconnect(self):
        self.runtime.nodes[1] = self.node
        self.run_connection()
        self.node.disconnect.assert_not_called()
        self.runtime.operations.add_node.assert_not_called()
        self.assertEqual(self.events, ['connect', 'health', 'start'])

    def test_restart_failure_does_not_disconnect_remote_core(self):
        self.node.connected = True
        self.runtime.nodes[1] = self.node
        self.node.restart.side_effect = TimeoutError('API port timed out')
        operations.restart_node(1, self.config)
        self.node.disconnect.assert_not_called()
        self.assertIn('Restart Xray / API readiness: API port timed out', self.status.call_args.kwargs['message'])
        self.assertNotIn(1, operations._connecting_nodes)

    def test_automatic_retry_waits_but_manual_reconnect_bypasses_delay(self):
        self.node.connect.side_effect = TimeoutError('offline')
        self.run_connection()
        self.node.connect.reset_mock()
        self.node.connect.side_effect = self.connect
        operations.connect_node(1, automatic=True)
        self.node.connect.assert_not_called()
        self.run_connection()
        self.node.start.assert_called_once()
        self.assertNotIn(1, operations._node_retry_after)

    def test_failed_transport_construction_records_reason_and_releases_lock(self):
        self.runtime.operations.add_node.side_effect = ValueError('bad certificate')
        self.run_connection()
        self.assertEqual(self.status.call_args.kwargs['message'], 'Create node transport: bad certificate')
        self.runtime.operations.add_node.side_effect = None
        self.run_connection()
        self.node.start.assert_called_once()

    def test_failed_db_lookup_records_reason_and_releases_lock(self):
        self.crud.get_node_by_id.side_effect = RuntimeError('DB unavailable')
        self.run_connection()
        self.assertEqual(self.status.call_args.kwargs['message'], 'Read node configuration: DB unavailable')
        self.crud.get_node_by_id.side_effect = None
        self.run_connection()
        self.node.start.assert_called_once()

    def test_disabled_node_is_not_started(self):
        self.crud.get_node_by_id.return_value.status = 'disabled'
        self.run_connection()
        self.node.start.assert_not_called()

    def test_rest_health_timeout_returns_restart_and_records_reason(self):
        self.runtime.nodes[1] = self.node
        self.node.connected = True
        type(self.node).started = property(lambda _: (_ for _ in ()).throw(TimeoutError('REST read timeout')))
        self.addCleanup(delattr, type(self.node), 'started')
        self.assertEqual(operations.check_node_health(1), 'restart')
        self.assertEqual(self.status.call_args.kwargs['message'], 'Health check: REST read timeout')

    def test_health_and_automatic_recovery_skip_failed_node_cooldown(self):
        operations._node_retry_after[1] = operations.monotonic() + 30
        self.assertIsNone(operations.check_node_health(1))
        self.status.assert_not_called()

    def test_node_lifecycle_serializes_restart_and_coalesces_reconnect(self):
        entered, release, restarted = threading.Event(), threading.Event(), threading.Event()
        self.runtime.nodes[1] = self.node
        def blocking_connect():
            entered.set()
            if not release.wait(3):
                raise TimeoutError('test release not signalled')
            self.connect()
        self.node.connect.side_effect = blocking_connect
        first = threading.Thread(target=operations.connect_node, args=(1, self.config))
        second = threading.Thread(target=lambda: (operations.restart_node(1, self.config), restarted.set()))
        try:
            first.start()
            self.assertTrue(entered.wait(2))
            operations.connect_node(1, self.config)
            self.assertIsNone(operations.check_node_health(1))
            second.start()
            self.assertFalse(restarted.wait(0.05))
        finally:
            release.set()
            first.join(3)
            if second.ident is not None:
                second.join(3)
        self.assertFalse(first.is_alive())
        self.assertFalse(second.is_alive())
        self.node.connect.assert_called_once()
        self.node.start.assert_called_once()
        self.node.restart.assert_called_once()
        self.node.disconnect.assert_not_called()

    def test_other_node_can_connect_while_first_is_busy(self):
        ready, release = threading.Event(), threading.Event()
        def hold_first():
            with operations._node_lock(1):
                ready.set()
                release.wait(3)
        worker = threading.Thread(target=hold_first)
        try:
            worker.start()
            self.assertTrue(ready.wait(2))
            operations.connect_node(2, self.config)
            self.node.start.assert_called_once()
        finally:
            release.set()
            worker.join(3)

    def test_account_reconciliation_runs_after_connection_lock_is_released(self):
        acquired = []
        def reconcile():
            self.assertNotIn(1, operations._connecting_nodes)
            def probe():
                lock = operations._node_lock(1)
                ok = lock.acquire(blocking=False)
                acquired.append(ok)
                if ok:
                    lock.release()
            worker = threading.Thread(target=probe)
            worker.start()
            worker.join(2)
            self.assertFalse(worker.is_alive())
        self.accounts.side_effect = reconcile
        self.run_connection()
        self.assertEqual(acquired, [True])

    def test_healthy_node_clears_stale_error_without_restarting(self):
        self.runtime.nodes[1] = self.node
        self.node.connected = self.node.started = True
        self.assertIsNone(operations.check_node_health(1))
        self.status.assert_called_once_with(1, 'connected', version='26.3.27')
        self.node.restart.assert_not_called()
        self.node.disconnect.assert_not_called()

    def test_already_healthy_node_does_not_rewrite_status_or_version(self):
        self.crud.get_node_by_id.return_value.status = 'connected'
        self.runtime.nodes[1] = self.node
        self.node.connected = self.node.started = True
        self.assertIsNone(operations.check_node_health(1))
        self.status.assert_not_called()
        self.node.get_version.assert_not_called()

    def test_health_recovery_keeps_last_version_when_response_has_no_version(self):
        self.crud.get_node_by_id.return_value.xray_version = '26.3.27'
        self.runtime.nodes[1] = self.node
        self.node.connected = self.node.started = True
        self.node.get_version.return_value = None
        self.assertIsNone(operations.check_node_health(1))
        self.status.assert_called_once_with(1, 'connected', version='26.3.27')
