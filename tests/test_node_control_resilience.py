"""Regression of real transport orchestration; never reboot cores on uncertainty."""
import ast
import threading
import types
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import MagicMock, Mock, PropertyMock, patch

import requests

import test_device_policy_sync as orchestration
import test_node_device_protocol as protocol


class RestControlResilienceTests(unittest.TestCase):
    def client(self, session="existing"):
        client = object.__new__(protocol.node.ReSTXRayNode)
        client._session_id = session
        client._rest_api_url = "https://node.example:62050"
        client.address, client.port, client.api_port = "node.example", 62050, 62051
        client._api, client._started = None, False
        client.session = Mock()
        client.session.post.return_value = self.response(200, {})
        return client

    @staticmethod
    def response(status, data):
        response = Mock(status_code=status)
        response.json.return_value = data
        return response

    def test_read_timeout_is_retried_once_with_separate_deadlines(self):
        for path in protocol.node.NODE_READ_ONLY_PATHS:
            with self.subTest(path=path):
                client = self.client()
                client.session.post.side_effect = [requests.ReadTimeout("slow read"), self.response(200, {"ok": True})]
                self.assertEqual(client.make_request(path), {"ok": True})
                self.assertEqual(client.session.post.call_count, 2)
                for call in client.session.post.call_args_list:
                    self.assertEqual(call.kwargs["timeout"], (10, 10))
                    self.assertEqual(call.kwargs["json"]["session_id"], "existing")

    def test_mutations_are_not_replayed_after_response_timeout(self):
        for path in ("/connect", "/disconnect", "/start", "/restart", "/stop", "/device-policies"):
            with self.subTest(path=path):
                client = self.client()
                failure = requests.ReadTimeout("ambiguous remote result")
                client.session.post.side_effect = failure
                with self.assertRaises(protocol.node.NodeAPIError) as raised:
                    client.make_request(path)
                self.assertIs(raised.exception.__cause__, failure)
                self.assertIn(path, raised.exception.detail)
                client.session.post.assert_called_once()

    def test_retry_exhaustion_is_bounded_and_does_not_clear_session(self):
        client = self.client()
        client.session.post.side_effect = requests.ConnectTimeout("network unavailable")
        self.assertFalse(client.connected)
        self.assertEqual(client.session.post.call_count, 2)
        self.assertEqual(client._session_id, "existing")

    def test_certificate_verification_error_is_not_retried(self):
        client = self.client()
        client.session.post.side_effect = requests.exceptions.SSLError("untrusted cert")
        with self.assertRaises(protocol.node.NodeAPIError) as raised:
            client.make_request("/ping")
        self.assertIn("TLS", raised.exception.detail)
        client.session.post.assert_called_once()

    def test_invalid_json_is_not_retried_or_accepted_as_healthy(self):
        client = self.client()
        client.session.post.return_value.json.side_effect = ValueError("bad JSON")
        self.assertFalse(client.connected)
        client.session.post.assert_called_once()
        self.assertEqual(client._session_id, "existing")

    def test_ping_timeout_does_not_take_over_session_on_connect(self):
        client = self.client()
        client.session.post.side_effect = requests.ReadTimeout("slow ping")
        with patch.object(protocol.node.ssl, "get_server_certificate") as certificate:
            self.assertFalse(client.connected)
            with self.assertRaises(protocol.node.NodeAPIError):
                client.connect()
            certificate.assert_not_called()
        self.assertTrue(all(call.args[0].endswith("/ping") for call in client.session.post.call_args_list))
        self.assertEqual(client._session_id, "existing")

    def test_connect_reuses_authenticated_session(self):
        client = self.client()
        with patch.object(protocol.node.ssl, "get_server_certificate") as certificate:
            client.connect()
            certificate.assert_not_called()
        client.session.post.assert_called_once()
        self.assertEqual(client._session_id, "existing")

    def test_only_explicit_session_mismatch_allows_a_new_session(self):
        client = self.client()
        client.session.post.side_effect = [self.response(403, {"detail": "Session ID mismatch."}),
                                           self.response(200, {"session_id": "new"})]
        with patch.object(protocol.node.ssl, "get_server_certificate", return_value="node-cert") as certificate, \
                patch.object(protocol.node, "string_to_temp_file", return_value=types.SimpleNamespace(name="pinned-cert")):
            client.connect()
            certificate.assert_called_once_with(("node.example", 62050), timeout=15)
        self.assertEqual(client._session_id, "new")
        self.assertEqual(client.session.verify, "pinned-cert")
        self.assertEqual([call.args[0].rsplit("/", 1)[1] for call in client.session.post.call_args_list], ["ping", "connect"])

    def test_other_forbidden_errors_do_not_discard_session_or_retry_auth(self):
        client = self.client()
        client.session.post.return_value = self.response(403, {"detail": "Forbidden"})
        with self.assertRaises(protocol.node.NodeAPIError):
            client.connect()
        self.assertEqual(client._session_id, "existing")
        client.session.post.assert_called_once()

    def test_already_started_response_waits_for_api_without_restart(self):
        client = self.client()
        client._node_cert = "node-cert"
        client._prepare_config = lambda config: config
        client.restart = Mock()
        client.session.post.side_effect = [self.response(200, {}),
                                           self.response(400, {"detail": "Xray is started already"})]
        with patch.object(protocol.node.grpc, "channel_ready_future") as ready:
            client.start(Mock())
            ready.return_value.result.assert_called_once_with(timeout=10)
        client.restart.assert_not_called()
        self.assertTrue(client._started)

    def test_rpyc_temporary_ping_timeout_keeps_transport(self):
        client = object.__new__(protocol.node.RPyCXRayNode)
        connection = client.connection = Mock()
        connection.ping.side_effect = TimeoutError("slow RPC")
        with self.assertRaises(TimeoutError):
            _ = client.connected
        connection.close.assert_not_called()
        self.assertIs(client.connection, connection)


class HealthBackoffTests(unittest.TestCase):
    setUp = orchestration.NodeConnectionOrderTests.setUp
    connect = orchestration.NodeConnectionOrderTests.connect
    health = orchestration.NodeConnectionOrderTests.health
    start = orchestration.NodeConnectionOrderTests.start
    def test_api_deadline_never_requests_core_restart(self):
        self.runtime.nodes[1] = self.node
        self.node.connected = self.node.started = True
        self.node.api.get_sys_stats.side_effect = TimeoutError("API Deadline Exceeded")
        self.assertIsNone(orchestration.operations.check_node_health(1))
        self.assertIn("API Deadline Exceeded", self.status.call_args.kwargs["message"])
        self.assertGreater(orchestration.operations._node_retry_after[1], orchestration.operations.monotonic())
        self.node.api.get_sys_stats.assert_called_once_with(timeout=5)
        self.node.restart.assert_not_called()
        self.node.disconnect.assert_not_called()
        self.node.api.get_sys_stats.reset_mock()
        self.assertIsNone(orchestration.operations.check_node_health(1))
        self.node.api.get_sys_stats.assert_not_called()

    def test_late_api_recovers_after_backoff_without_restarting(self):
        self.runtime.nodes[1] = self.node
        self.node.connected = self.node.started = True
        self.node.api.get_sys_stats.side_effect = TimeoutError("API not ready")
        self.assertIsNone(orchestration.operations.check_node_health(1))
        orchestration.operations._node_retry_after[1] = 0
        self.node.api.get_sys_stats.side_effect = None
        self.status.reset_mock()
        self.assertIsNone(orchestration.operations.check_node_health(1))
        self.status.assert_called_once_with(1, "connected", version="26.3.27")
        self.assertNotIn(1, orchestration.operations._node_retry_after)
        self.node.restart.assert_not_called()

    def test_confirmed_stopped_core_requests_start_not_restart(self):
        self.runtime.nodes[1] = self.node
        self.node.connected, self.node.started = True, False
        self.assertEqual(orchestration.operations.check_node_health(1), "connect")
        self.node.api.get_sys_stats.assert_not_called()


class AccountBatchResilienceTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.operations = orchestration.operations
        self.runtime = types.SimpleNamespace(api=Mock(), nodes={})
        self.stack.enter_context(patch.object(self.operations, "xray", self.runtime))
        self.stack.enter_context(patch.object(self.operations, "GetDB", MagicMock()))
        self.crud = self.stack.enter_context(patch.object(self.operations, "crud"))
        self.sync = self.stack.enter_context(patch.object(self.operations, "sync_user_device_accounts"))
        self.stack.enter_context(patch.object(self.operations, "logger"))

    def test_batch_probes_once_and_isolates_a_failing_node(self):
        bad, good = Mock(), Mock()
        type(bad).started = PropertyMock(side_effect=TimeoutError("control read timeout"))
        connected = type(good).connected = PropertyMock(return_value=True)
        started = type(good).started = PropertyMock(return_value=True)
        self.runtime.nodes = {1: bad, 2: good}
        self.crud.get_users.return_value = [Mock(id=index) for index in range(100)]
        self.operations.sync_all_node_device_accounts()
        self.assertEqual(self.sync.call_count, 100)
        connected.assert_called_once()
        started.assert_called_once()
        expected = [(self.runtime.api, "main"), (good.api, "node")]
        self.assertTrue(all(call.kwargs["targets"] == expected for call in self.sync.call_args_list))

    def test_batch_continues_after_one_user_error(self):
        self.crud.get_users.return_value = [Mock(id=1), Mock(id=2)]
        self.sync.side_effect = [ValueError("bad account"), None]
        self.operations.sync_all_node_device_accounts()
        self.assertEqual(self.sync.call_count, 2)
        self.assertTrue(self.operations._account_sync_lock.acquire(blocking=False))
        self.operations._account_sync_lock.release()

    def test_parallel_batch_calls_coalesce_and_release_lock(self):
        self.assertTrue(self.operations._account_sync_lock.acquire(blocking=False))
        try:
            self.operations.sync_all_node_device_accounts()
            self.crud.get_users.assert_not_called()
        finally:
            self.operations._account_sync_lock.release()
        self.crud.get_users.return_value = []
        self.operations.sync_all_node_device_accounts()
        self.crud.get_users.assert_called_once()


class ConcurrentHealthJobTests(unittest.TestCase):
    def test_slow_peer_does_not_delay_another_peers_recovery(self):
        entered, recovered, release = threading.Event(), threading.Event(), threading.Event()
        runtime = types.SimpleNamespace(core=Mock(started=True), config=Mock(), operations=Mock())
        def probe(node_id):
            if node_id == 1:
                entered.set()
                release.wait(2)
                return None
            return "connect"
        runtime.operations.check_node_health.side_effect = probe
        runtime.operations.connect_node.side_effect = lambda *a, **k: recovered.set()
        app = types.ModuleType("app")
        app.app, app.logger, app.scheduler, app.xray = Mock(), Mock(), Mock(), runtime
        db = types.ModuleType("app.db")
        db.GetDB, db.crud = MagicMock(), Mock()
        db.crud.get_nodes.return_value = [types.SimpleNamespace(id=1), types.SimpleNamespace(id=2)]
        config = types.ModuleType("config")
        config.JOB_CORE_HEALTH_CHECK_INTERVAL = 10
        with patch.dict("sys.modules", {"app": app, "app.db": db, "config": config,
                                        "app.models.node": orchestration.node_models}):
            job = orchestration.load("isolated_parallel_health_job", "app/jobs/0_xray_core.py")
        worker = threading.Thread(target=job.core_health_check)
        worker.start()
        try:
            self.assertTrue(entered.wait(1))
            self.assertTrue(recovered.wait(1))
        finally:
            release.set()
            worker.join(3)
        self.assertFalse(worker.is_alive())
        runtime.operations.connect_node.assert_called_once_with(2, runtime.config.include_db_users.return_value, automatic=True)


class UsageProbeIsolationTests(unittest.TestCase):
    def test_unavailable_control_peer_does_not_abort_other_usage_probes(self):
        path = Path(__file__).resolve().parents[1] / "app/jobs/record_usages.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        # The isolated loader below supplies mocks; still check production
        # imports so a missing logger cannot hide behind the test namespace.
        app_imports = [alias.name for item in tree.body if isinstance(item, ast.ImportFrom)
                       and item.module == "app" for alias in item.names]
        self.assertIn("logger", app_imports)
        for name, stats_name in (("record_user_usages", "get_users_stats"),
                                 ("record_node_usages", "get_outbounds_stats")):
            with self.subTest(job=name):
                bad, good = Mock(), Mock(connected=True, started=True, usage_coefficient=2)
                type(bad).started = PropertyMock(side_effect=TimeoutError("Node control timeout"))
                runtime = types.SimpleNamespace(api=Mock(), nodes={1: bad, 2: good})
                stats = Mock(return_value=[])
                log = Mock()
                namespace = {"xray": runtime, "logger": log, "ThreadPoolExecutor": ThreadPoolExecutor,
                             stats_name: stats, "defaultdict": __import__("collections").defaultdict,
                             "DISABLE_RECORDING_NODE_USAGE": False}
                function = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == name)
                module = ast.Module(body=[function], type_ignores=[])
                exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
                namespace[name]()
                self.assertEqual(stats.call_count, 2)
                self.assertEqual({call.args[0] for call in stats.call_args_list}, {runtime.api, good.api})
                log.warning.assert_called_once()


class NodeLogProbeTests(unittest.TestCase):
    def test_rpyc_control_timeout_closes_logs_with_actionable_reason(self):
        import asyncio
        path = Path(__file__).resolve().parents[1] / "app/routers/node.py"
        tree = ast.parse(path.read_text(encoding="utf-8"))
        function = next(item for item in tree.body if isinstance(item, ast.AsyncFunctionDef) and item.name == "node_logs")
        function.decorator_list = []
        function.args.defaults = []
        module = ast.Module(body=[ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0), function], type_ignores=[])
        node = Mock()
        type(node).connected = PropertyMock(side_effect=TimeoutError("slow RPC ping"))
        admin = Mock()
        namespace = {"xray": types.SimpleNamespace(nodes={1: node}), "Admin": admin, "logger": Mock()}
        exec(compile(ast.fix_missing_locations(module), str(path), "exec"), namespace)
        from unittest.mock import AsyncMock
        websocket = Mock(query_params={}, headers={})
        websocket.close = AsyncMock()
        asyncio.run(namespace["node_logs"](1, websocket, Mock()))
        websocket.close.assert_awaited_once_with(reason="Node control channel is unavailable", code=4400)
        websocket.accept.assert_not_called()
