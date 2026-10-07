"""Relay configuration, persistence, migration, API and subscription regressions.

No production service or extra test dependencies are needed. Application imports
reuse the existing isolated version-command bootstrap, never a real database.
"""
import asyncio
import copy
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import test_user_device_limit as bootstrap
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.db.models import Node, NodeRelay, TLS, User
from app.models.admin import Admin
from app.models.node import NodeRelayModify, NodeStatus
from app.models.proxy import ProxyTypes, VLESSSettings
from app.routers import node as routes
from app.subscription.share import generate_subscription
from app.xray import node_relay_service as service
from app.xray.config import XRayConfig
from app.xray.node_relay import (
    RelayProcess, business_inbounds, choose_port, clean_address, config_ports,
    make_config, subscription_host,
)

TAG = "VLESS TCP REALITY"
UUID = "35e4e39c-7d5c-4f4b-8b71-558e4f37ff53"


def config():
    return XRayConfig({
        "inbounds": [{"tag": TAG, "protocol": "vless", "port": 8443,
                      "settings": {"clients": [], "decryption": "none"},
                      "streamSettings": {"network": "tcp", "security": "reality",
                          "realitySettings": {"dest": "www.example.com:443",
                              "serverNames": ["www.example.com"], "publicKey": "public-test-key",
                              "privateKey": "private-test-key", "shortIds": ["1234"]}}}],
        "outbounds": [{"tag": "DIRECT", "protocol": "freedom"}],
    })


class FakeRuntime:
    def __init__(self):
        self.profiles, self.last_error, self.occupied = [], None, set()
        self.fail = False

    @property
    def running(self):
        return bool(self.profiles)

    def occupied_ports(self):
        return self.occupied

    def apply(self, profiles):
        if self.fail:
            raise RuntimeError("simulated bind failure")
        self.profiles = copy.deepcopy(profiles)

    def snapshot(self):
        return copy.deepcopy(self.profiles)

    def stop(self):
        self.profiles = []


class RelayHelpersTests(unittest.TestCase):
    def test_addresses_are_plain_hostnames_or_ips(self):
        for value, expected in ((" HK.EXAMPLE.COM. ", "hk.example.com"),
                                ("198.51.100.2", "198.51.100.2"),
                                ("2001:db8::2", "2001:db8::2")):
            self.assertEqual(clean_address(value), expected)
        for value in ("", "localhost", "127.0.0.1", "::1", "0.0.0.0", "169.254.1.1",
                      "https://node.test", "node.test:443", "user@node.test", "node/a",
                      "{SERVER_IP}", "*.node.test", "a..b", "-a.test", "a" * 64 + ".test"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                clean_address(value)

    def test_only_current_vless_tcp_reality_is_selectable(self):
        conf = config()
        baseline = conf.inbounds_by_tag[TAG]
        for index, changes in enumerate(({"protocol": "vmess"}, {"network": "quic"},
                                        {"tls": "tls"}, {"is_fallback": True}, {"port": "443-450"})):
            conf.inbounds_by_tag[str(index)] = {**baseline, **changes}
        self.assertEqual(list(business_inbounds(conf)), [TAG])

    def test_port_allocation_reserves_existing_ranges_and_all_nodes(self):
        self.assertEqual(config_ports({"inbounds": [{"port": "80,443,18443-18445"}]}),
                         {80, 443, 18443, 18444, 18445})
        self.assertEqual(choose_port(None, None, {18443}, {18444}, {18445}), 18446)
        self.assertEqual(choose_port(None, 20001, set(), set(), set()), 20001)
        self.assertEqual(choose_port(None, 12, set(), set(), set()), 18443)
        for value in (True, "20001", 0, 1023, 65536, 8443):
            with self.subTest(value=value), self.assertRaises(ValueError):
                choose_port(value, None, {8443}, set(), set())

    def test_hundred_nodes_have_fixed_tcp_destinations_not_shared_accounts(self):
        profiles = [{"node_id": n, "listen_port": 18443 + n, "target_address": f"node{n}.test",
                     "target_port": 8443} for n in range(100)]
        result = make_config(profiles)
        self.assertEqual(len(result["inbounds"]), 100)
        self.assertEqual(len({item["tag"] for item in result["inbounds"]}), 100)
        self.assertEqual(len({item["port"] for item in result["inbounds"]}), 100)
        for inbound in result["inbounds"]:
            self.assertEqual(inbound["settings"]["network"], "tcp")
            self.assertFalse(inbound["settings"]["followRedirect"])
            self.assertFalse(inbound["sniffing"]["enabled"])
            self.assertNotIn("clients", inbound["settings"])

    def test_node_name_is_not_interpreted_as_a_format_variable(self):
        host = subscription_host({"name": "US-{USERNAME}", "entry_address": "hk.test", "listen_port": 18443})
        self.assertEqual(host["remark"].format_map({"USERNAME": "secret"}), "US-{USERNAME} (Relay)")

    def test_invalid_config_leaves_existing_runtime_and_records_reason(self):
        runtime = RelayProcess("unused", ".")
        runtime.profiles = [{"node_id": 1, "listen_port": 18443, "target_address": "node.test", "target_port": 8443}]
        with patch.object(runtime, "validate", side_effect=RuntimeError("bad config")), \
                patch.object(runtime, "_stop") as stop:
            with self.assertRaisesRegex(RuntimeError, "bad config"):
                runtime.apply([{**runtime.profiles[0], "listen_port": 18444}])
            stop.assert_not_called()
        self.assertEqual(runtime.profiles[0]["listen_port"], 18443)
        self.assertEqual(runtime.last_error, "bad config")

    def test_listener_scan_reserves_unknown_pids_and_excludes_only_own_process(self):
        runtime = RelayProcess("unused", ".")
        runtime.process = SimpleNamespace(pid=123, poll=lambda: None)
        listeners = [SimpleNamespace(status="LISTEN", pid=pid, laddr=SimpleNamespace(port=port))
                     for pid, port in ((123, 18443), (999, 18444), (None, 18445))]
        with patch("app.xray.node_relay.psutil.net_connections", return_value=listeners):
            self.assertEqual(runtime.occupied_ports(), {18444, 18445})


class RelayStoreTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.runtime = FakeRuntime()
        self.conf = config()
        self.patches = [patch.object(service, "runtime", self.runtime),
                        patch.object(service, "_published", []), patch.object(service, "_errors", {}),
                        patch.object(service.xray, "config", self.conf)]
        for item in self.patches:
            item.start()
        self.node = Node(name="US-01", address="us01.example.com", port=62050, api_port=62051, status=NodeStatus.connected)
        self.second = Node(name="US-02", address="us02.example.com", port=2050, api_port=2051, status=NodeStatus.connected)
        self.db.add_all([self.node, self.second, User(username="existing-user"), TLS(key="existing-key", certificate="existing-cert")])
        self.db.commit()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def enable(self, node=None, **changes):
        values = {"mode": "relay", "entry_address": "hk.example.com", "inbound_tag": TAG, **changes}
        return service.save(self.db, node or self.node, NodeRelayModify(**values))

    def test_auto_allocation_persistence_and_different_node_destinations(self):
        first, second = self.enable(), self.enable(self.second)
        self.assertEqual((first["listen_port"], second["listen_port"]), (18443, 18444))
        self.assertEqual([row["target_address"] for row in self.runtime.profiles], [self.node.address, self.second.address])
        self.assertEqual(first["status"], "running")
        self.assertEqual(self.enable()["listen_port"], first["listen_port"])
        self.assertEqual(self.db.query(NodeRelay).count(), 2)
        self.assertEqual(self.db.query(User).one().username, "existing-user")
        self.assertEqual(self.db.query(TLS).one().certificate, "existing-cert")
        self.assertEqual((self.node.port, self.node.api_port), (62050, 62051))

    def test_existing_listeners_and_proxy_control_ports_are_not_overwritten(self):
        self.runtime.occupied = {18443}
        self.assertEqual(self.enable()["listen_port"], 18444)
        for port in (8443, 62050, 62051, 2050, 2051, 18443):
            with self.subTest(port=port), self.assertRaises(ValueError):
                self.enable(allocation="manual", listen_port=port)

    def test_switch_direct_only_removes_that_nodes_relay(self):
        self.enable()
        self.enable(self.second)
        result = service.save(self.db, self.node, NodeRelayModify(mode="direct"))
        self.assertEqual(result["mode"], "direct")
        self.assertEqual(self.db.query(Node).count(), 2)
        self.assertEqual(self.db.query(NodeRelay).one().node_id, self.second.id)
        self.assertEqual(len(service.subscription_hosts(TAG)), 1)

    def test_disable_delete_and_invalid_inbound_remove_virtual_host(self):
        self.enable()
        self.enable(self.second)
        self.node.status = NodeStatus.disabled
        self.db.commit()
        profiles, errors = service._plans(self.db)
        self.runtime.apply(profiles)
        service._publish(profiles)
        self.assertEqual(service.public(self.node)["status"], "inactive")
        self.assertEqual(len(service.subscription_hosts(TAG)), 1)
        self.db.delete(self.second)
        self.db.commit()
        self.assertEqual(self.db.query(NodeRelay).count(), 1)
        self.node.status = NodeStatus.connected
        self.db.commit()
        self.conf.inbounds_by_tag.clear()
        profiles, errors = service._plans(self.db)
        self.assertEqual(profiles, [])
        self.assertIn(self.node.id, errors)
        self.assertEqual(service.public(self.node)["status"], "error")

    def test_disabled_node_and_unsupported_server_are_not_configurable(self):
        self.node.status = NodeStatus.disabled
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "Enable"):
            self.enable()
        for values in ({"source": "node"}, {"listen_port": True}, {"unexpected": "value"}):
            with self.subTest(values=values), self.assertRaises(ValueError):
                NodeRelayModify(mode="relay", **values)

    def test_ipv6_entry_is_rejected_instead_of_advertising_an_ipv4_only_listener(self):
        with self.assertRaisesRegex(ValueError, "IPv6 relay entry"):
            self.enable(entry_address="2001:db8::2")
        self.assertEqual(self.db.query(NodeRelay).count(), 0)

    def test_failed_listener_does_not_write_settings_or_advertise_endpoint(self):
        old = self.enable()
        self.runtime.fail = True
        with self.assertRaisesRegex(RuntimeError, "bind failure"):
            self.enable(allocation="manual", listen_port=20001)
        self.assertEqual(self.node.relay.listen_port, old["listen_port"])
        self.assertEqual(service.subscription_hosts(TAG)[0]["port"], old["listen_port"])

    def test_failed_db_commit_restores_previous_runtime_and_settings(self):
        old = self.enable()
        with patch.object(self.db, "commit", side_effect=RuntimeError("database unavailable")):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                self.enable(allocation="manual", listen_port=20001)
        self.assertEqual(self.node.relay.listen_port, old["listen_port"])
        self.assertEqual(self.runtime.profiles[0]["listen_port"], old["listen_port"])
        self.assertEqual(service.subscription_hosts(TAG)[0]["port"], old["listen_port"])

    def test_stopped_process_is_not_advertised(self):
        self.enable()
        self.runtime.stop()
        self.assertEqual(service.subscription_hosts(TAG), [])

    def test_runtime_rollback_cannot_advertise_an_unapplied_new_destination(self):
        self.enable()
        profiles, _ = service._plans(self.db)
        service._publish([{**profiles[0], "target_address": "changed.example.com"}])
        self.assertEqual(service.subscription_hosts(TAG), [])

    def test_periodic_refresh_recovers_after_runtime_loss_and_isolates_invalid_node(self):
        self.enable()
        self.enable(self.second)
        self.runtime.stop()
        self.node.address = "https://invalid.example.com"
        self.db.commit()
        with patch.object(service, "GetDB") as context:
            context.return_value.__enter__.return_value = self.db
            service.refresh()
        self.assertEqual(service.public(self.node)["status"], "error")
        self.assertEqual(service.public(self.second)["status"], "running")
        self.assertEqual([row["node_id"] for row in self.runtime.profiles], [self.second.id])

    def test_private_hwid_credential_is_not_replaced_with_a_shared_relay_account(self):
        self.enable()
        private = "74bbf62e-0a44-4e75-832a-fb31f0ce9f64"
        user = SimpleNamespace(username="device-client", used_traffic=0, status="active",
                               proxies={ProxyTypes.VLESS: VLESSSettings(id=private, flow="xtls-rprx-vision")},
                               inbounds={ProxyTypes.VLESS: [TAG]})
        with patch.object(service.xray, "hosts", {TAG: []}):
            for fmt in ("v2ray", "v2ray-json", "clash-meta", "sing-box"):
                with self.subTest(fmt=fmt):
                    rendered = generate_subscription(user, fmt, False, False)
                    self.assertIn(private, rendered)
                    self.assertNotIn(UUID, rendered)
                    self.assertIn("xtls-rprx-vision", rendered)

    def test_repeated_manual_save_and_direct_toggle_never_duplicates_virtual_hosts(self):
        for _ in range(10):
            result = self.enable(allocation="manual", listen_port=21001)
            self.assertEqual(result["listen_port"], 21001)
            self.assertEqual(len(service.subscription_hosts(TAG)), 1)
            self.assertEqual(self.db.query(NodeRelay).count(), 1)
            service.save(self.db, self.node, NodeRelayModify(mode="direct"))
            self.assertEqual(service.subscription_hosts(TAG), [])
            self.assertEqual(self.db.query(NodeRelay).count(), 0)

    def test_subscription_keeps_direct_host_credentials_reality_keys_and_sni(self):
        self.enable()
        direct = {**subscription_host({"name": "Hong Kong", "entry_address": "hk-direct.example.com", "listen_port": 8443}), "remark": "Hong Kong direct"}
        user = SimpleNamespace(username="client", used_traffic=0, status="active", proxies={ProxyTypes.VLESS: VLESSSettings(id=UUID, flow="")}, inbounds={ProxyTypes.VLESS: [TAG]})
        with patch.object(service.xray, "hosts", {TAG: [direct]}):
            links = generate_subscription(user, "v2ray", False, False).splitlines()
            self.assertEqual(len(links), 2)
            urls = [urlsplit(link) for link in links]
            self.assertEqual([(url.hostname, url.port) for url in urls], [("hk-direct.example.com", 8443), ("hk.example.com", 18443)])
            for url in urls:
                self.assertEqual(url.username, UUID)
                params = parse_qs(url.query)
                self.assertEqual(params["security"], ["reality"])
                self.assertEqual(params["sni"], ["www.example.com"])
                self.assertEqual(params["pbk"], ["public-test-key"])
            for fmt in ("v2ray-json", "clash-meta", "sing-box"):
                with self.subTest(fmt=fmt):
                    rendered = generate_subscription(user, fmt, False, False)
                    self.assertIn("hk-direct.example.com", rendered)
                    self.assertIn("hk.example.com", rendered)
                    self.assertIn(UUID, rendered)
                    self.assertIn("public-test-key", rendered)
                    self.assertIn("www.example.com", rendered)
                    self.assertNotIn("private-test-key", rendered)
            # Existing formats which cannot express REALITY retain their prior
            # behavior, not a promise of protocol support in all clients.
            for fmt in ("clash", "outline"):
                generate_subscription(user, fmt, False, False)
        self.assertEqual(direct["port"], 8443)

    def request(self, method, url, body=None, authorized=True):
        app = FastAPI()
        app.include_router(routes.router)
        app.dependency_overrides[routes.get_db] = lambda: self.db
        if authorized:
            app.dependency_overrides[Admin.check_sudo_admin] = lambda: Admin(username="test", is_sudo=True)
        raw = json.dumps(body).encode() if body is not None else b""
        messages = []
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
                 "scheme": "https", "path": url, "raw_path": url.encode(), "query_string": b"", "root_path": "",
                 "server": ("test.local", 443), "client": ("198.51.100.1", 1234),
                 "headers": [(b"content-type", b"application/json")] + ([(b"authorization", b"Bearer test")] if not authorized else [])}
        async def receive():
            return {"type": "http.request", "body": raw, "more_body": False}
        async def send(message):
            messages.append(message)
        asyncio.run(app(scope, receive, send))
        status = next(msg["status"] for msg in messages if msg["type"] == "http.response.start")
        payload = json.loads(b"".join(msg.get("body", b"") for msg in messages))
        return status, payload

    def test_api_routes_authorization_validation_and_rollback_errors(self):
        url = f"/api/node/{self.node.id}/relay"
        self.assertEqual(self.request("GET", "/api/nodes/relay/options")[0], 200)
        self.assertEqual(self.request("GET", url)[1]["mode"], "direct")
        self.assertEqual(self.request("GET", "/api/node/999/relay")[0], 404)
        self.assertEqual(self.request("PUT", url, {"mode": "relay"})[0], 422)
        self.assertEqual(self.request("PUT", url, {"mode": "relay", "source": "node"})[0], 422)
        settings = {"mode": "relay", "entry_address": "hk.example.com", "inbound_tag": TAG}
        self.assertEqual(self.request("PUT", url, settings)[0], 200)
        self.runtime.fail = True
        self.assertEqual(self.request("PUT", url, {**settings, "allocation": "manual", "listen_port": 20001})[0], 409)
        self.runtime.fail = False
        self.assertEqual(self.request("DELETE", url)[0], 200)
        for admin, status in ((None, 401), (Admin(username="ordinary", is_sudo=False), 403)):
            with patch.object(Admin, "get_admin", return_value=admin):
                for method, path in (("GET", "/api/nodes/relay/options"), ("GET", url), ("PUT", url), ("DELETE", url)):
                    with self.subTest(method=method, status=status):
                        self.assertEqual(self.request(method, path, settings if method == "PUT" else None, authorized=False)[0], status)


class RelayMigrationTests(unittest.TestCase):
    def test_migration_chain_has_one_additive_head(self):
        # Use the already isolated application bootstrap: historical migration
        # modules import crypto through app and otherwise require a production
        # Xray executable even when merely reading revision metadata.
        from alembic.config import Config
        from alembic.script import ScriptDirectory
        root = Path(__file__).resolve().parents[1]
        settings = Config(str(root / "alembic.ini"))
        settings.set_main_option("script_location", str(root / "app/db/migrations"))
        script = ScriptDirectory.from_config(settings)
        self.assertEqual(script.get_heads(), ["8f9012ab34cd"])
        self.assertEqual(script.get_revision("8f9012ab34cd").down_revision, "7e8f9012ab34")

    def test_upgrade_downgrade_preserve_old_rows_and_enforce_unique_port(self):
        path = Path(__file__).resolve().parents[1] / "app/db/migrations/versions/8f9012ab34cd_add_node_relay.py"
        spec = importlib.util.spec_from_file_location("relay_migration", path)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.execute(text("CREATE TABLE tls (certificate TEXT)"))
            conn.execute(text("INSERT INTO nodes VALUES (1, 'existing-node')"))
            conn.execute(text("INSERT INTO users VALUES (1, 'existing-user')"))
            conn.execute(text("INSERT INTO tls VALUES ('existing-cert')"))
            with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
                migration.upgrade()
                self.assertIn("node_relays", inspect(conn).get_table_names())
                self.assertEqual(inspect(conn).get_unique_constraints("node_relays")[0]["column_names"], ["listen_port"])
                conn.execute(text("INSERT INTO node_relays VALUES (1, 'hk.example.com', 18443, 'REALITY', 'auto')"))
                migration.downgrade()
            self.assertNotIn("node_relays", inspect(conn).get_table_names())
            self.assertEqual(conn.execute(text("SELECT name FROM users")).scalar(), "existing-user")
            self.assertEqual(conn.execute(text("SELECT name FROM nodes")).scalar(), "existing-node")
            self.assertEqual(conn.execute(text("SELECT certificate FROM tls")).scalar(), "existing-cert")
        engine.dispose()


if __name__ == "__main__":
    unittest.main()
