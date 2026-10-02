import importlib.util
import json
import sys
import threading
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import rpyc
from rpyc.utils.server import ThreadedServer


config = types.ModuleType("app.xray.config")
config.XRayConfig = dict
api = types.ModuleType("xray_api")
api.XRay = Mock()
with patch.dict(sys.modules, {"app": types.ModuleType("app"), "app.xray": types.ModuleType("app.xray"),
                             "app.xray.config": config, "xray_api": api}):
    spec = importlib.util.spec_from_file_location("test_node_protocol", Path(__file__).resolve().parents[1] / "app/xray/node.py")
    node = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(node)


class NewService(rpyc.Service):
    def exposed_set_device_policies(self, serialized):
        policies = json.loads(serialized)
        return {"accepted": True, "policy_count": len(policies), "policy_enforcement": "subscription_request_and_node_credentials",
                "direct_connection_enforced": True}

    def exposed_fetch_device_activity(self):
        return {"active_users": 2, "activity_source": "xray-online-users", "activity_scope": "online_users"}

    def exposed_fetch_health(self):
        return {"source": "node-runtime", "active_users": 2}


class NodeDeviceProtocolTests(unittest.TestCase):
    def rpyc_node(self, service):
        server = ThreadedServer(service, hostname="127.0.0.1", port=0, auto_register=False)
        thread = threading.Thread(target=server.start, daemon=True)
        thread.start()
        self.addCleanup(server.close)
        client = object.__new__(node.RPyCXRayNode)
        client.connection = rpyc.connect("127.0.0.1", server.port)
        self.addCleanup(client.connection.close)
        return client

    def test_real_rpyc_serialization_and_activity_response(self):
        client = self.rpyc_node(NewService)
        response = client.set_device_policies([{"user": "1.alice", "device_limit": 3}])
        self.assertEqual(response["policy_count"], 1)
        self.assertTrue(response["direct_connection_enforced"])
        self.assertEqual(client.get_device_activity()["active_users"], 2)
        self.assertEqual(client.get_health()["source"], "node-runtime")

    def test_real_old_rpyc_service_is_compatible(self):
        client = self.rpyc_node(rpyc.Service)
        self.assertIsNone(client.set_device_policies([]))
        self.assertIsNone(client.get_device_activity())
        self.assertTrue(client.connected)

    def test_old_rest_routes_are_compatible_but_auth_errors_propagate(self):
        client = object.__new__(node.ReSTXRayNode)
        client._session_id = "session"
        client.make_request = Mock(side_effect=node.NodeAPIError(404, "Not found"))
        self.assertIsNone(client.set_device_policies([]))
        self.assertIsNone(client.get_device_activity())
        client.make_request.side_effect = node.NodeAPIError(403, "Forbidden")
        with self.assertRaises(node.NodeAPIError):
            client.set_device_policies([])

    def test_rest_methods_use_the_existing_session_channel(self):
        client = object.__new__(node.ReSTXRayNode)
        client._session_id = "session"
        client.make_request = Mock(return_value={"accepted": True})
        client.set_device_policies([])
        client.make_request.assert_called_once_with("/device-policies", timeout=5, policies=[])
        client.make_request.reset_mock()
        client.get_device_activity()
        client.make_request.assert_called_once_with("/device-activity", timeout=3)
