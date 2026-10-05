"""Exercise production connection timeouts, mTLS and health-job isolation."""

import socket
import ast
import ssl
import tempfile
import threading
import time
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from contextlib import contextmanager
from unittest.mock import MagicMock, Mock, patch

import rpyc
from rpyc.utils.authenticators import SSLAuthenticator
from rpyc.utils.server import ThreadedServer
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

import test_device_policy_sync as orchestration
import test_node_device_protocol as protocol


class NodeTransportRecoveryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='node-recovery-')
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        self.cert, self.key = self.identity('node')

    def identity(self, prefix):
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'Gozargah')])
        now = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                       .public_key(key.public_key()).serial_number(x509.random_serial_number())
                       .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
                       .sign(key, hashes.SHA256()))
        cert_path, key_path = self.directory / f'{prefix}.pem', self.directory / f'{prefix}.key'
        cert_path.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_path.write_bytes(key.private_bytes(serialization.Encoding.PEM,
                             serialization.PrivateFormat.TraditionalOpenSSL, serialization.NoEncryption()))
        return str(cert_path), str(key_path)

    def client(self, port):
        client = object.__new__(protocol.node.RPyCXRayNode)
        client.address, client.port = '127.0.0.1', port
        client._service = rpyc.Service
        client._node_certfile = types.SimpleNamespace(name=self.cert)
        client._certfile = types.SimpleNamespace(name=self.cert)
        client._keyfile = types.SimpleNamespace(name=self.key)
        return client

    def stall_server(self):
        listener = socket.socket()
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(2)
        release = threading.Event()
        def serve():
            try:
                with listener.accept()[0]:
                    release.wait(2)
            finally:
                listener.close()
        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        def cleanup():
            release.set()
            worker.join(3)
        self.addCleanup(cleanup)
        return listener.getsockname()[1]

    def tls_server(self, service):
        auth = SSLAuthenticator(self.key, self.cert, ca_certs=self.cert,
                                cert_reqs=ssl.CERT_REQUIRED)
        server = ThreadedServer(service, hostname='127.0.0.1', port=0,
                                auto_register=False, authenticator=auth)
        worker = threading.Thread(target=server.start, daemon=True)
        worker.start()
        self.addCleanup(server.close)
        return server

    def test_real_rest_certificate_handshake_times_out(self):
        client = object.__new__(protocol.node.ReSTXRayNode)
        client.address, client.port = '127.0.0.1', self.stall_server()
        client.make_request = Mock()
        began = time.monotonic()
        with patch.object(protocol.node, 'NODE_CONNECT_TIMEOUT', 0.15):
            with self.assertRaises(TimeoutError):
                client.connect()
        self.assertLess(time.monotonic() - began, 1.5)
        client.make_request.assert_not_called()

    def test_real_rpyc_tls_handshake_times_out(self):
        client = self.client(self.stall_server())
        began = time.monotonic()
        with patch.object(protocol.node, 'NODE_CONNECT_TIMEOUT', 0.15):
            with self.assertRaises(TimeoutError):
                client._connect_transport()
        self.assertLess(time.monotonic() - began, 1.5)

    def test_real_mtls_new_service_uses_bounded_rpc_and_existing_contract(self):
        server = self.tls_server(protocol.NewService)
        client = self.client(server.port)
        client.connection = client._connect_transport()
        self.addCleanup(client.connection.close)
        client.connection.ping()
        self.assertEqual(client.connection._config['sync_request_timeout'], 10)
        self.assertEqual(client.get_health()['source'], 'node-runtime')
        self.assertEqual(client.set_device_policies([])['policy_count'], 0)

    def test_real_mtls_old_service_remains_compatible(self):
        server = self.tls_server(rpyc.Service)
        client = self.client(server.port)
        client.connection = client._connect_transport()
        self.addCleanup(client.connection.close)
        self.assertTrue(client.connected)
        self.assertIsNone(client.set_device_policies([]))

    def test_mtls_rejects_untrusted_server_certificate(self):
        server = self.tls_server(rpyc.Service)
        client = self.client(server.port)
        wrong_cert, _ = self.identity('untrusted')
        client._node_certfile.name = wrong_cert
        with self.assertRaises(ssl.SSLCertVerificationError):
            client._connect_transport()

    def test_rpyc_failed_ping_closes_partial_connection(self):
        client = self.client(12345)
        client.disconnect = Mock()
        conn = Mock()
        conn.ping.side_effect = TimeoutError('ping timeout')
        client._connect_transport = Mock(return_value=conn)
        with patch.object(protocol.node.ssl, 'get_server_certificate', return_value='test-cert'), \
                patch.object(protocol.node, 'string_to_temp_file', return_value=Mock()):
            with self.assertRaises(TimeoutError):
                client.connect()
        conn.close.assert_called_once()
        self.assertFalse(hasattr(client, 'connection'))

    def test_rpyc_eof_retries_close_each_failed_connection(self):
        client = self.client(12345)
        client.disconnect = Mock()
        conns = [Mock() for _ in range(4)]
        for conn in conns:
            conn.ping.side_effect = EOFError('closed')
        client._connect_transport = Mock(side_effect=conns)
        with patch.object(protocol.node.ssl, 'get_server_certificate', return_value='test-cert'), \
                patch.object(protocol.node, 'string_to_temp_file', return_value=Mock()):
            with self.assertRaises(EOFError):
                client.connect()
        for conn in conns:
            conn.close.assert_called_once()

    def test_rest_api_timeout_reports_the_actual_api_port(self):
        client = object.__new__(protocol.node.ReSTXRayNode)
        client._session_id, client.api_port, client.address = 'session', 62051, '127.0.0.1'
        client._node_cert = 'test-cert'
        client.make_request = Mock(return_value={})
        client._prepare_config = lambda config: config
        config = Mock()
        with patch.object(protocol.node.grpc, 'channel_ready_future') as ready:
            ready.return_value.result.side_effect = protocol.node.grpc.FutureTimeoutError()
            for operation in (client.start, client.restart):
                with self.assertRaisesRegex(ConnectionError, '62051.*5s'):
                    operation(config)


class NodeHealthJobRecoveryTests(unittest.TestCase):
    def test_main_core_failure_does_not_abort_node_recovery(self):
        runtime = types.SimpleNamespace(core=Mock(started=False), config=Mock(), operations=Mock())
        runtime.core.restart.side_effect = RuntimeError('main core unavailable')
        runtime.operations.check_node_health.return_value = 'connect'
        crud = Mock()
        crud.get_nodes.return_value = [types.SimpleNamespace(id=1)]
        app = types.ModuleType('app')
        app.app, app.logger, app.scheduler, app.xray = Mock(), Mock(), Mock(), runtime
        db = types.ModuleType('app.db')
        db.GetDB, db.crud = MagicMock(), crud
        config = types.ModuleType('config')
        config.JOB_CORE_HEALTH_CHECK_INTERVAL = 10
        with patch.dict('sys.modules', {'app': app, 'app.db': db, 'config': config,
                                       'app.models.node': orchestration.node_models}):
            job = orchestration.load('isolated_main_failure_job', 'app/jobs/0_xray_core.py')
        job.core_health_check()
        runtime.operations.connect_node.assert_called_once_with(
            1, runtime.config.include_db_users.return_value, automatic=True)
        app.logger.exception.assert_called_once()

    def test_one_node_failure_does_not_abort_other_nodes(self):
        runtime = types.SimpleNamespace(core=Mock(started=True), config=Mock(), operations=Mock())
        runtime.operations.check_node_health.side_effect = [RuntimeError('unavailable'), 'connect']
        crud = Mock()
        crud.get_nodes.return_value = [types.SimpleNamespace(id=1), types.SimpleNamespace(id=2)]
        app = types.ModuleType('app')
        app.app, app.logger, app.scheduler, app.xray = Mock(), Mock(), Mock(), runtime
        db = types.ModuleType('app.db')
        db.GetDB, db.crud = MagicMock(), crud
        config = types.ModuleType('config')
        config.JOB_CORE_HEALTH_CHECK_INTERVAL = 10
        with patch.dict('sys.modules', {'app': app, 'app.db': db, 'config': config,
                                       'app.models.node': orchestration.node_models}):
            job = orchestration.load('isolated_health_job', 'app/jobs/0_xray_core.py')
        job.core_health_check()
        runtime.operations.connect_node.assert_called_once_with(
            2, runtime.config.include_db_users.return_value, automatic=True)
        app.logger.exception.assert_called_once()

    def test_busy_nodes_do_not_trigger_configuration_or_recovery(self):
        runtime = types.SimpleNamespace(core=Mock(started=True), config=Mock(), operations=Mock())
        runtime.operations.check_node_health.return_value = None
        crud = Mock()
        crud.get_nodes.return_value = [types.SimpleNamespace(id=1)]
        app = types.ModuleType('app')
        app.app, app.logger, app.scheduler, app.xray = Mock(), Mock(), Mock(), runtime
        db = types.ModuleType('app.db')
        db.GetDB, db.crud = MagicMock(), crud
        config = types.ModuleType('config')
        config.JOB_CORE_HEALTH_CHECK_INTERVAL = 10
        with patch.dict('sys.modules', {'app': app, 'app.db': db, 'config': config,
                                       'app.models.node': orchestration.node_models}):
            job = orchestration.load('isolated_busy_health_job', 'app/jobs/0_xray_core.py')
        job.core_health_check()
        runtime.config.include_db_users.assert_not_called()
        runtime.operations.connect_node.assert_not_called()
        runtime.operations.restart_node.assert_not_called()


class NodeAdminLifecycleTests(unittest.TestCase):
    def test_modify_and_delete_lock_before_changing_database_and_transport(self):
        # Execute the actual route bodies without starting FastAPI or Xray.
        path = orchestration.ROOT / 'app/routers/node.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for name in ('modify_node', 'remove_node'):
            with self.subTest(route=name):
                events = []
                @contextmanager
                def lifecycle_lock(node_id):
                    self.assertEqual(node_id, 1)
                    events.append('lock')
                    try:
                        yield
                    finally:
                        events.append('unlock')
                row = types.SimpleNamespace(id=1, name='test-node', status='connected')
                crud = Mock()
                crud.update_node.side_effect = lambda *a: (events.append('db'), row)[1]
                crud.remove_node.side_effect = lambda *a: events.append('db')
                operations = Mock()
                operations.node_lifecycle_lock = lifecycle_lock
                operations.remove_node.side_effect = lambda *a: events.append('transport')
                function = next(item for item in tree.body if isinstance(item, ast.FunctionDef) and item.name == name)
                function.decorator_list = []
                function.args.defaults = []
                module = ast.Module(body=[ast.ImportFrom(module='__future__',
                                    names=[ast.alias(name='annotations')], level=0), function], type_ignores=[])
                namespace = {'crud': crud, 'xray': types.SimpleNamespace(operations=operations),
                             'NodeStatus': orchestration.node_models.NodeStatus, 'logger': Mock()}
                exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)
                if name == 'modify_node':
                    namespace[name](Mock(), Mock(), row, Mock(), Mock())
                else:
                    namespace[name](row, Mock(), Mock())
                self.assertEqual(events, ['lock', 'db', 'transport', 'unlock'])
