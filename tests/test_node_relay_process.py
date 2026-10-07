"""Optional real pinned-Xray TCP/TLS forwarding on loopback only.

Set MR_SHAW_RELAY_TEST_XRAY to an existing v26.3.27 binary to run this suite.
CI without that explicit binary skips it; unit/API/migration tests still run.
"""
import importlib.util
import os
import socket
import ssl
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

# Import only the pure process module, without initializing application services.
spec = importlib.util.spec_from_file_location("relay_process_under_test", Path(__file__).resolve().parents[1] / "app/xray/node_relay.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
RelayProcess = module.RelayProcess

BINARY = os.environ.get("MR_SHAW_RELAY_TEST_XRAY", "")


@unittest.skipUnless(BINARY, "explicit pinned Xray integration binary not configured")
class RelayProcessTests(unittest.TestCase):
    def setUp(self):
        version = subprocess.run([BINARY, "version"], capture_output=True, text=True, check=True)
        self.assertIn("26.3.27", version.stdout)
        self.runtime = RelayProcess(BINARY, str(Path(BINARY).parent), listen="127.0.0.1")
        self.addCleanup(self.runtime.stop)

    def free_port(self):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return sock.getsockname()[1]

    def profile(self, node_id, entry, target):
        return {"node_id": node_id, "name": f"Node-{node_id}", "entry_address": "127.0.0.1",
                "listen_port": entry, "target_address": "127.0.0.1", "target_port": target,
                "inbound_tag": "TEST"}

    def tls_server(self, reply):
        directory = tempfile.TemporaryDirectory(prefix="relay-tls-")
        self.addCleanup(directory.cleanup)
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "relay-test")])
        now = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                       .public_key(key.public_key()).serial_number(x509.random_serial_number())
                       .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(days=1))
                       .sign(key, hashes.SHA256()))
        certpath, keypath = Path(directory.name) / "cert.pem", Path(directory.name) / "key.pem"
        certpath.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        keypath.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certpath, keypath)
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen()
        sock.settimeout(.2)
        stop = threading.Event()
        failures = []
        def serve():
            while not stop.is_set():
                try:
                    conn, _ = sock.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                try:
                    with conn, context.wrap_socket(conn, server_side=True) as tls:
                        tls.settimeout(3)
                        data = tls.recv(4096)
                        tls.sendall(reply + data)
                except Exception as exc:
                    failures.append(exc)
        worker = threading.Thread(target=serve, daemon=True)
        worker.start()
        def cleanup():
            stop.set()
            sock.close()
            worker.join(3)
        self.addCleanup(cleanup)
        return sock.getsockname()[1], certificate, failures

    def exchange(self, entry, cert):
        context = ssl.create_default_context(cadata=cert.public_bytes(serialization.Encoding.PEM).decode())
        with socket.create_connection(("127.0.0.1", entry), timeout=3) as raw:
            with context.wrap_socket(raw, server_hostname="relay-test") as tls:
                self.assertEqual(tls.getpeercert(binary_form=True), cert.public_bytes(serialization.Encoding.DER))
                tls.sendall(b"opaque-client-payload")
                return tls.recv(4096)

    def test_two_destinations_preserve_end_to_end_tls_and_recover_after_crash(self):
        first, cert1, failures1 = self.tls_server(b"US:")
        second, cert2, failures2 = self.tls_server(b"JP:")
        port1, port2 = self.free_port(), self.free_port()
        while port2 == port1:
            port2 = self.free_port()
        profiles = [self.profile(1, port1, first), self.profile(2, port2, second)]
        self.runtime.apply(profiles)
        self.assertEqual(self.exchange(port1, cert1), b"US:opaque-client-payload")
        self.assertEqual(self.exchange(port2, cert2), b"JP:opaque-client-payload")
        pid = self.runtime.process.pid
        self.runtime.apply([{**profiles[0], "name": "Renamed"}, profiles[1]])
        self.assertEqual(self.runtime.process.pid, pid, "metadata-only change must not restart listeners")
        self.runtime.process.kill()
        self.runtime.process.wait(timeout=3)
        self.assertEqual(self.runtime.snapshot(), [])
        self.runtime.apply(profiles)
        self.assertNotEqual(self.runtime.process.pid, pid)
        self.assertEqual(self.exchange(port1, cert1), b"US:opaque-client-payload")
        self.assertEqual(failures1 + failures2, [])
        self.runtime.stop()
        self.assertFalse(self.runtime.running)
        with self.assertRaises(OSError):
            socket.create_connection(("127.0.0.1", port1), timeout=.3)

    def test_bind_failure_restores_previous_listener_without_touching_target(self):
        target, cert, failures = self.tls_server(b"US:")
        profile = self.profile(1, self.free_port(), target)
        self.runtime.apply([profile])
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            blocked = occupied.getsockname()[1]
            with self.assertRaises(RuntimeError):
                self.runtime.apply([{**profile, "listen_port": blocked}])
        self.assertTrue(self.runtime.running)
        self.assertEqual(self.runtime.snapshot()[0]["listen_port"], profile["listen_port"])
        self.assertEqual(self.exchange(profile["listen_port"], cert), b"US:opaque-client-payload")
        self.assertEqual(failures, [])


if __name__ == "__main__":
    unittest.main()
