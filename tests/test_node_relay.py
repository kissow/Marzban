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
from urllib.parse import parse_qs, urlsplit, unquote

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
    make_config, host_target, rewrite_hosts,
)

TAG = "VLESS TCP REALITY"
UUID = "35e4e39c-7d5c-4f4b-8b71-558e4f37ff53"


def original_host(remark, address, port=None, **overrides):
    return {"remark": remark, "address": [address], "port": port,
            "path": None, "sni": [], "host": [], "tls": None,
            "alpn": "", "fingerprint": "", "allowinsecure": False,
            "mux_enable": False, "fragment_setting": None, "noise_setting": None,
            "random_user_agent": False, "use_sni_as_host": False, **overrides}


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

    def test_rewrite_preserves_original_alias_templates_and_all_host_overrides(self):
        host = original_host("Original-{USERNAME}", "node.test", sni=["custom.example.com"],
                             fingerprint="edge", alpn="h2", mux_enable=True)
        profile = {"name": "Different-admin-name", "target_address": "node.test", "target_port": 8443,
                   "entry_address": "main.test", "listen_port": 18443}
        result = rewrite_hosts([host], [profile], 8443)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0], {**host, "address": ["main.test"], "port": 18443})
        self.assertEqual(result[0]["remark"].format_map({"USERNAME": "client"}), "Original-client")
        self.assertEqual(host["address"], ["node.test"])
        self.assertIsNone(host["port"])

    def test_host_matching_is_normalized_exact_and_never_resolves_or_splits_addresses(self):
        self.assertEqual(host_target(original_host("Name", " NODE.TEST. "), 8443), ("node.test", 8443))
        for addresses in (["node.test", "other.test"], ["{SERVER_IP}"], [], ["*.node.test"]):
            self.assertIsNone(host_target({"address": addresses}, 8443))
        host = original_host("Node", "node.test")
        profile = {"target_address": "node.test", "target_port": 8443,
                   "entry_address": "main.test", "listen_port": 18443}
        self.assertEqual(rewrite_hosts([host], [profile, {**profile, "listen_port": 18444}], 8443), [host])
        self.assertEqual(rewrite_hosts([host], [{**profile, "target_port": 8444}], 8443), [host])

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
        self.remotes = {}
        self.conf = config()
        self.hosts = {TAG: [original_host("Main direct", "main-direct.example.com", 8443),
                           original_host("🚀 Node 01 original", "us01.example.com", 8443),
                           original_host("🚀 Node 02 original", "us02.example.com", 8443)]}
        self.patches = [patch.object(service, "runtime", self.runtime),
                        patch.object(service, "_published", []), patch.object(service, "_errors", {}),
                        patch.object(service.xray, "config", self.conf),
                        patch.object(service.xray, "nodes", self.remotes), patch.object(service, "_remote_live", {}),
                        patch.object(service.xray, "hosts", self.hosts)]
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

    def remote(self, source=None):
        source = source or self.node
        class Remote:
            def __init__(self):
                self.profiles, self.fail, self.bad_ack, self.started, self.supported = [], False, False, True, True
                self.occupied, self.calls = set(), []
            def get_relay_status(self):
                return {"capability": service.CAPABILITY if self.supported else "old-node",
                        "core_started": self.started, "running": bool(self.profiles),
                        "profiles": copy.deepcopy(self.profiles), "occupied_ports": sorted(self.occupied)}
            def set_relays(self, profiles):
                self.calls.append(copy.deepcopy(profiles))
                if self.fail:
                    raise RuntimeError("remote source unreachable")
                self.profiles = copy.deepcopy(profiles)
                result = self.get_relay_status()
                if self.bad_ack:
                    result["profiles"] = []
                return result
        remote = Remote()
        self.remotes[source.id] = remote
        return remote

    def via_node(self, target=None, source=None, **changes):
        values = {"source": "node", "source_node_id": (source or self.node).id,
                  "entry_address": "relay-node.example.com", **changes}
        return self.enable(target or self.second, **values)

    def test_node_source_applies_only_source_and_keeps_original_subscription_alias(self):
        remote = self.remote()
        result = self.via_node()
        self.assertEqual(result["source_node_id"], self.node.id)
        self.assertEqual(result["status"], "running")
        self.assertEqual(self.runtime.profiles, [])
        self.assertEqual(remote.profiles, [{"node_id": self.second.id, "listen_port": 18443,
                                         "target_address": self.second.address, "target_port": 8443}])
        hosts = service.subscription_hosts(TAG)
        self.assertEqual(len(hosts), 3)
        self.assertEqual(hosts[2]["remark"], self.hosts[TAG][2]["remark"])
        self.assertEqual(hosts[2]["address"], ["relay-node.example.com"])
        self.assertEqual(hosts[:2], self.hosts[TAG][:2])
        self.assertEqual(self.node.port, 62050)

    def test_switch_node_to_main_to_direct_cleans_old_source(self):
        remote = self.remote()
        self.via_node()
        self.enable(self.second)
        self.assertEqual(remote.profiles, [])
        self.assertEqual(len(self.runtime.profiles), 1)
        self.assertEqual(service.public(self.second)["source"], "main")
        service.save(self.db, self.second, NodeRelayModify(mode="direct"))
        self.assertEqual(self.runtime.profiles, [])
        self.assertEqual(service.subscription_hosts(TAG), self.hosts[TAG])

    def test_source_local_port_scan_and_current_port_reuse(self):
        remote = self.remote()
        remote.occupied = {18443, 18444}
        self.runtime.occupied = {18445}
        self.assertEqual(self.via_node()["listen_port"], 18445)
        self.assertEqual(self.via_node()["listen_port"], 18445)
        with self.assertRaises(ValueError):
            self.via_node(allocation="manual", listen_port=18443)

    def test_self_missing_disabled_old_and_offline_sources_rejected(self):
        remote = self.remote()
        with self.assertRaisesRegex(ValueError, "itself"):
            self.via_node(target=self.node)
        remote.supported = False
        with self.assertRaisesRegex(ValueError, "Update"):
            self.via_node()
        remote.supported = True
        remote.started = False
        with self.assertRaisesRegex(ValueError, "not started"):
            self.via_node()
        remote.started = True
        self.node.status = NodeStatus.disabled
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "connected"):
            self.via_node()
        self.assertEqual(self.db.query(NodeRelay).count(), 0)

    def test_node_cycle_rejected_before_applying_any_snapshot(self):
        first, second = self.remote(), self.remote(self.second)
        self.via_node()
        previous = copy.deepcopy(first.profiles)
        with self.assertRaisesRegex(ValueError, "cycle"):
            self.via_node(target=self.node, source=self.second)
        self.assertEqual(first.profiles, previous)
        self.assertEqual(second.calls, [])
        self.assertEqual(self.db.query(NodeRelay).count(), 1)

    def test_bad_ack_and_db_failure_do_not_publish_new_remote_endpoint(self):
        remote = self.remote()
        remote.bad_ack = True
        with self.assertRaisesRegex(RuntimeError, "acknowledgement"):
            self.via_node()
        self.assertEqual(service.relay_profiles(TAG), [])
        self.assertEqual(self.db.query(NodeRelay).count(), 0)
        remote.bad_ack = False
        with patch.object(self.db, "commit", side_effect=RuntimeError("database unavailable")):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                self.via_node()
        self.assertEqual(remote.profiles, [])
        self.assertEqual(self.db.query(NodeRelay).count(), 0)
        self.assertEqual(service.relay_profiles(TAG), [])

    def test_periodic_node_recovery_and_failure_isolation(self):
        remote = self.remote()
        self.via_node()
        remote.profiles = []
        with patch.object(service, "GetDB") as context:
            context.return_value.__enter__.return_value = self.db
            service.refresh()
            self.assertEqual(service.public(self.second)["status"], "running")
            remote.fail = True
            remote.profiles = []
            service.refresh()
        self.assertEqual(service.public(self.second)["status"], "error")
        self.assertEqual(service.subscription_hosts(TAG), self.hosts[TAG])

    def test_remote_configuration_is_cleared_when_target_disabled_or_deleted(self):
        remote = self.remote()
        self.via_node()
        self.second.status = NodeStatus.disabled
        self.db.commit()
        with patch.object(service, "GetDB") as context:
            context.return_value.__enter__.return_value = self.db
            service.refresh()
        self.assertEqual(remote.profiles, [])
        self.assertEqual(service.public(self.second)["status"], "inactive")

    def test_node_to_another_node_source_switch_cleans_previous_source(self):
        third = Node(name="Node-03", address="node3.test", port=3050, api_port=3051, status=NodeStatus.connected)
        self.db.add(third)
        self.db.commit()
        first, other = self.remote(), self.remote(third)
        self.via_node()
        self.via_node(source=third, entry_address="node3.test")
        self.assertEqual(first.profiles, [])
        self.assertEqual(other.profiles[0]['node_id'], self.second.id)
        self.assertEqual(service.subscription_hosts(TAG)[2]['remark'], self.hosts[TAG][2]['remark'])
        self.assertEqual(service.subscription_hosts(TAG)[2]['address'], ['node3.test'])

    def test_deleted_source_fails_explicitly_without_publishing_stale_endpoint(self):
        self.remote()
        self.via_node()
        source_id = self.node.id
        self.db.delete(self.node)
        self.db.commit()
        self.db.expire_all()
        self.remotes.pop(source_id)
        with patch.object(service, "GetDB") as context:
            context.return_value.__enter__.return_value = self.db
            service.refresh()
        self.assertEqual(service.public(self.second)['status'], 'error')
        self.assertIn('missing', service.public(self.second)['error'])
        self.assertEqual(service.subscription_hosts(TAG), self.hosts[TAG])

    def test_existing_listeners_and_proxy_control_ports_are_not_overwritten(self):
        self.runtime.occupied = {18443}
        self.assertEqual(self.enable()["listen_port"], 18444)
        for port in (8443, 62050, 62051, 2050, 2051, 18443):
            with self.subTest(port=port), self.assertRaises(ValueError):
                self.enable(allocation="manual", listen_port=port)

    def test_unrelated_failed_source_does_not_block_another_targets_save(self):
        remote = self.remote()
        self.via_node()
        remote.fail = True
        remote.get_relay_status = lambda: (_ for _ in ()).throw(RuntimeError('offline unrelated source'))
        third = Node(name="Third", address="third.test", port=4050, api_port=4051, status=NodeStatus.connected)
        self.db.add(third)
        self.db.commit()
        self.hosts[TAG].append(original_host('Third original alias', 'third.test', 8443))
        self.assertEqual(self.enable(third)['status'], 'running')
        self.assertEqual(len(remote.calls), 1)
        self.assertEqual(self.db.query(NodeRelay).count(), 2)

    def test_switch_direct_only_removes_that_nodes_relay(self):
        self.enable()
        self.enable(self.second)
        result = service.save(self.db, self.node, NodeRelayModify(mode="direct"))
        self.assertEqual(result["mode"], "direct")
        self.assertEqual(self.db.query(Node).count(), 2)
        self.assertEqual(self.db.query(NodeRelay).one().node_id, self.second.id)
        self.assertEqual(len(service.relay_profiles(TAG)), 1)

    def test_disable_delete_and_invalid_inbound_remove_virtual_host(self):
        self.enable()
        self.enable(self.second)
        self.node.status = NodeStatus.disabled
        self.db.commit()
        profiles, errors = service._plans(self.db)
        self.runtime.apply(profiles)
        service._publish(profiles)
        self.assertEqual(service.public(self.node)["status"], "inactive")
        self.assertEqual(len(service.relay_profiles(TAG)), 1)
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
        self.assertEqual(service.relay_profiles(TAG)[0]["listen_port"], old["listen_port"])

    def test_failed_db_commit_restores_previous_runtime_and_settings(self):
        old = self.enable()
        with patch.object(self.db, "commit", side_effect=RuntimeError("database unavailable")):
            with self.assertRaisesRegex(RuntimeError, "database unavailable"):
                self.enable(allocation="manual", listen_port=20001)
        self.assertEqual(self.node.relay.listen_port, old["listen_port"])
        self.assertEqual(self.runtime.profiles[0]["listen_port"], old["listen_port"])
        self.assertEqual(service.relay_profiles(TAG)[0]["listen_port"], old["listen_port"])

    def test_stopped_process_is_not_advertised(self):
        self.enable()
        self.runtime.stop()
        self.assertEqual(service.relay_profiles(TAG), [])

    def test_runtime_rollback_cannot_advertise_an_unapplied_new_destination(self):
        self.enable()
        profiles, _ = service._plans(self.db)
        service._publish([{**profiles[0], "target_address": "changed.example.com"}])
        self.assertEqual(service.relay_profiles(TAG), [])

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
        for fmt in ("v2ray", "v2ray-json", "clash-meta", "sing-box"):
            with self.subTest(fmt=fmt):
                rendered = generate_subscription(user, fmt, False, False)
                self.assertIn(private, rendered)
                self.assertNotIn(UUID, rendered)
                self.assertIn("xtls-rprx-vision", rendered)
                self.assertNotIn("(Relay)", rendered)

    def test_repeated_manual_save_and_direct_toggle_never_duplicates_virtual_hosts(self):
        for _ in range(10):
            result = self.enable(allocation="manual", listen_port=21001)
            self.assertEqual(result["listen_port"], 21001)
            self.assertEqual(len(service.relay_profiles(TAG)), 1)
            self.assertEqual(self.db.query(NodeRelay).count(), 1)
            service.save(self.db, self.node, NodeRelayModify(mode="direct"))
            self.assertEqual(service.relay_profiles(TAG), [])
            self.assertEqual(self.db.query(NodeRelay).count(), 0)

    def test_subscription_keeps_direct_host_credentials_reality_keys_and_sni(self):
        self.hosts[TAG][1].update(sni=["www.example.com"], fingerprint="edge")
        original = copy.deepcopy(self.hosts)
        user = SimpleNamespace(username="client", used_traffic=0, status="active", proxies={ProxyTypes.VLESS: VLESSSettings(id=UUID, flow="")}, inbounds={ProxyTypes.VLESS: [TAG]})
        before = [urlsplit(link) for link in generate_subscription(user, "v2ray", False, False).splitlines()]
        self.enable()
        urls = [urlsplit(link) for link in generate_subscription(user, "v2ray", False, False).splitlines()]
        self.assertEqual(len(urls), 3)
        self.assertEqual([(url.hostname, url.port) for url in urls], [("main-direct.example.com", 8443), ("hk.example.com", 18443), ("us02.example.com", 8443)])
        self.assertEqual([unquote(url.fragment) for url in urls], [host["remark"] for host in original[TAG]])
        for old, url in zip(before, urls):
            self.assertEqual(url.username, UUID)
            self.assertEqual(parse_qs(url.query), parse_qs(old.query))
            params = parse_qs(url.query)
            self.assertEqual(params["security"], ["reality"])
            self.assertEqual(params["sni"], ["www.example.com"])
            self.assertEqual(params["pbk"], ["public-test-key"])
            self.assertEqual(params["sid"], ["1234"])
        self.assertEqual(parse_qs(urls[1].query)["fp"], ["edge"])
        for fmt in ("v2ray-json", "clash-meta", "sing-box"):
            with self.subTest(fmt=fmt):
                rendered = generate_subscription(user, fmt, False, False)
                for value in ("main-direct.example.com", "hk.example.com", "us02.example.com", UUID, "public-test-key", "www.example.com"):
                    self.assertIn(value, rendered)
                self.assertNotIn("us01.example.com", rendered)
                self.assertNotIn("(Relay)", rendered)
                self.assertNotIn("private-test-key", rendered)
        for fmt in ("clash", "outline"):
            generate_subscription(user, fmt, False, False)
        self.assertEqual(self.hosts, original)
        self.assertNotIn("sid", self.conf.inbounds_by_tag[TAG])

    def test_original_count_and_aliases_survive_two_relays_and_direct_restore(self):
        baseline = copy.deepcopy(self.hosts[TAG])
        self.enable(self.second)
        hosts = service.subscription_hosts(TAG)
        self.assertEqual(len(hosts), 3)
        self.assertEqual(hosts[:2], baseline[:2])
        self.assertEqual(hosts[2], {**baseline[2], "address": ["hk.example.com"], "port": 18443})
        self.enable()
        hosts = service.subscription_hosts(TAG)
        self.assertEqual([host["remark"] for host in hosts], [host["remark"] for host in baseline])
        self.assertEqual([host["port"] for host in hosts], [8443, 18444, 18443])
        service.save(self.db, self.second, NodeRelayModify(mode="direct"))
        self.assertEqual(service.subscription_hosts(TAG)[2], baseline[2])
        self.runtime.stop()
        self.assertEqual(service.subscription_hosts(TAG), baseline)
        self.assertEqual(self.hosts[TAG], baseline)

    def test_multiple_original_aliases_are_preserved_without_new_entries(self):
        self.hosts[TAG].append(original_host("Second alias {USERNAME}", "us01.example.com"))
        self.enable()
        hosts = service.subscription_hosts(TAG)
        self.assertEqual(len(hosts), 4)
        self.assertEqual(hosts[1]["address"], hosts[3]["address"])
        self.assertEqual(hosts[3]["remark"], "Second alias {USERNAME}")

    def test_unmatched_original_host_rejected_without_db_or_runtime_mutation(self):
        for host in (original_host("Alternate", "alternate.example.com"),
                     original_host("Wrong port", "us01.example.com", 8444),
                     {**original_host("Mixed", "us01.example.com"), "address": ["us01.example.com", "us02.example.com"]}):
            with self.subTest(host=host):
                self.hosts[TAG][1] = host
                status, _ = self.request("PUT", f"/api/node/{self.node.id}/relay", {"mode": "relay", "entry_address": "main.example.com", "inbound_tag": TAG})
                self.assertEqual(status, 422)
                self.assertEqual(self.db.query(NodeRelay).count(), 0)
                self.assertEqual(self.runtime.profiles, [])

    def test_ambiguous_nodes_rejected_before_overwriting_original_endpoint(self):
        self.enable()
        baseline = self.runtime.snapshot()
        self.second.address = self.node.address
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "Multiple Nodes"):
            self.enable(self.second)
        self.assertEqual(self.db.query(NodeRelay).count(), 1)
        self.assertEqual(self.runtime.snapshot(), baseline)

    def test_removed_original_host_is_not_recreated_by_periodic_recovery(self):
        self.enable()
        self.hosts[TAG].pop(1)
        with patch.object(service, "GetDB") as context:
            context.return_value.__enter__.return_value = self.db
            service.refresh()
        self.assertEqual(service.public(self.node)["status"], "error")
        self.assertEqual(service.relay_profiles(TAG), [])
        self.assertEqual(service.subscription_hosts(TAG), self.hosts[TAG])
        self.assertEqual(len(service.subscription_hosts(TAG)), 2)

    def test_old_ambiguous_relay_rows_fail_closed_with_explicit_reason(self):
        self.enable()
        self.enable(self.second)
        self.second.address = self.node.address
        self.db.commit()
        with patch.object(service, "GetDB") as context:
            context.return_value.__enter__.return_value = self.db
            service.refresh()
        self.assertEqual(service.subscription_hosts(TAG), self.hosts[TAG])
        for node in (self.node, self.second):
            self.assertEqual(service.public(node)["status"], "error")
            self.assertIn("Multiple Nodes", service.public(node)["error"])

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
    def test_source_migration_preserves_existing_main_relay_and_user_data(self):
        root = Path(__file__).resolve().parents[1]
        spec = importlib.util.spec_from_file_location("relay_source_migration", root / "app/db/migrations/versions/9012ab34cd56_add_relay_source.py")
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT)"))
            conn.execute(text("INSERT INTO nodes VALUES (1, 'keep-source')"))
            conn.execute(text("CREATE TABLE node_relays (node_id INTEGER PRIMARY KEY REFERENCES nodes(id), entry_address VARCHAR(253) NOT NULL, listen_port INTEGER NOT NULL UNIQUE, inbound_tag VARCHAR(256) NOT NULL, allocation VARCHAR(8) NOT NULL)"))
            conn.execute(text("INSERT INTO node_relays VALUES (1, 'main.test', 18443, 'REALITY', 'auto')"))
            with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
                migration.upgrade()
                self.assertEqual(conn.execute(text("SELECT source, source_node_id FROM node_relays")).one(), ("main", None))
                migration.downgrade()
            self.assertEqual(conn.execute(text("SELECT entry_address FROM node_relays")).scalar(), "main.test")
            self.assertEqual(conn.execute(text("SELECT name FROM nodes")).scalar(), "keep-source")
        engine.dispose()

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
        self.assertEqual(script.get_heads(), ["a123bc45de67"])
        self.assertEqual(script.get_revision("a123bc45de67").down_revision, "9012ab34cd56")
        self.assertEqual(script.get_revision("9012ab34cd56").down_revision, "8f9012ab34cd")
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
