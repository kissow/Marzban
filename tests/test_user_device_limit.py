import atexit
import asyncio
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Importing the full database model graph initializes the application's Xray
# object. Backend CI installs Python dependencies only; it does not start or
# install an Xray service just to import a unit test. Keep this test isolated
# with a temporary version command and test config, without changing production
# defaults.
ROOT = Path(__file__).resolve().parents[1]
_TEST_RUNTIME = tempfile.TemporaryDirectory(prefix="marzban-device-test-")
_TEST_PREVIOUS_CWD = os.getcwd()
(_TEST_VERSION_FILE := Path(_TEST_RUNTIME.name) / "version").write_text(
    "print('Xray 26.3.27')\n", encoding="utf-8"
)
os.environ["XRAY_EXECUTABLE_PATH"] = sys.executable
os.environ["XRAY_JSON"] = str(ROOT / "xray_config.json")
os.chdir(_TEST_RUNTIME.name)
try:
    from app.db.base import Base
    from app.db import crud
    from app.db.models import NodeUserUsage, Proxy, User, UserDevice
    from app.models.proxy import ProxyTypes
    from app.models.user import DeviceLimitAction, UserResponse, UserStatus
    from app.routers import subscription
    from app import xray
    from app.xray.config import XRayConfig
    from app.xray import operations
finally:
    os.chdir(_TEST_PREVIOUS_CWD)


def _cleanup_test_runtime():
    _TEST_RUNTIME.cleanup()


atexit.register(_cleanup_test_runtime)


class UserDeviceLimitTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def make_user(self, limit=0, action=DeviceLimitAction.log_only):
        user = User(
            username="device_test_user",
            device_limit=limit,
            device_limit_action=action,
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def test_same_public_ip_counts_distinct_hwid_and_same_hwid_does_not_duplicate(self):
        user = self.make_user(10, DeviceLimitAction.reject_new)
        results = [
            crud.register_user_device(
                self.db, user, f"device-{index}", client_ip="198.51.100.10"
            )
            for index in range(10)
        ]
        self.assertTrue(all(item["accepted"] for item in results))
        self.assertEqual(results[-1]["registered_devices"], 10)

        duplicate = crud.register_user_device(
            self.db, user, "device-0", client_ip="203.0.113.4"
        )
        self.assertTrue(duplicate["accepted"])
        self.assertFalse(duplicate["is_new_device"])
        self.assertEqual(duplicate["registered_devices"], 10)

        rejected = crud.register_user_device(
            self.db, user, "device-10", client_ip="198.51.100.10"
        )
        self.assertFalse(rejected["accepted"])
        self.assertTrue(rejected["is_new_device"])
        self.assertEqual(
            crud.get_user_device_status(self.db, user)["registered_devices"], 10
        )

    def test_status_does_not_expose_hwid_and_reports_remaining_slots(self):
        user = self.make_user(3, DeviceLimitAction.reject_new)
        crud.register_user_device(
            self.db, user, "device-a", client_ip="203.0.113.10"
        )
        status = crud.get_user_device_status(self.db, user)
        self.assertEqual(
            status,
            {
                "device_limit": 3,
                "registered_devices": 1,
                "remaining_devices": 2,
                "device_limit_mode": "hwid",
                "device_limit_action": "reject_new",
                "hwid_supported": True,
                "enforcement_scope": "subscription_requests_with_hwid",
            },
        )
        self.assertTrue(
            all("hwid" not in key.lower() or key == "hwid_supported" for key in status)
        )

    def test_log_only_records_over_limit_without_rejecting(self):
        user = self.make_user(2, DeviceLimitAction.log_only)
        results = [
            crud.register_user_device(self.db, user, f"device-{index}")
            for index in range(3)
        ]
        self.assertTrue(all(item["accepted"] for item in results))
        self.assertEqual(results[-1]["remaining_devices"], 0)
        self.assertEqual(
            crud.get_user_device_status(self.db, user)["registered_devices"], 3
        )

    def test_hwid_is_hashed_and_user_delete_cascades_devices(self):
        user = self.make_user()
        crud.register_user_device(
            self.db, user, "secret-hardware-id", client_ip="192.0.2.10"
        )
        stored = user.devices[0]
        self.assertNotEqual(stored.hwid_hash, "secret-hardware-id")
        self.assertEqual(len(stored.hwid_hash), 64)

        crud.remove_user(self.db, user)
        self.assertEqual(self.db.query(type(stored)).count(), 0)

    def test_revoked_hwid_can_be_registered_again_and_counts_as_active(self):
        user = self.make_user(1, DeviceLimitAction.reject_new)
        crud.register_user_device(self.db, user, "reusable-device")
        device = user.devices[0]
        device.revoked_at = datetime.utcnow()
        self.db.commit()

        restored = crud.register_user_device(self.db, user, "reusable-device")
        self.assertTrue(restored["accepted"])
        self.assertTrue(restored["is_new_device"])
        self.assertEqual(restored["registered_devices"], 1)

    def test_reject_new_generates_private_protocol_credentials_per_hwid(self):
        user = self.make_user(2, DeviceLimitAction.reject_new)
        user.proxies.append(Proxy(type=ProxyTypes.VLESS, settings={"id": "shared-id", "flow": ""}))
        user.proxies.append(Proxy(type=ProxyTypes.Trojan, settings={"password": "shared-password", "flow": ""}))
        self.db.commit()

        first = crud.register_user_device(self.db, user, "phone")
        second = crud.register_user_device(self.db, user, "laptop")
        self.assertTrue(first["accepted"] and second["accepted"])
        first_credentials = crud.get_user_device_credentials(self.db, user, "phone")
        second_credentials = crud.get_user_device_credentials(self.db, user, "laptop")
        self.assertNotEqual(first_credentials["vless"]["id"], second_credentials["vless"]["id"])
        self.assertNotEqual(first_credentials["trojan"]["password"], second_credentials["trojan"]["password"])
        self.assertNotIn("phone", str(first_credentials))
        self.assertNotIn("shared-password", str(first_credentials))

        rejected = crud.register_user_device(self.db, user, "tablet")
        self.assertFalse(rejected["accepted"])
        self.assertIsNone(crud.get_user_device_credentials(self.db, user, "tablet"))

    def test_include_db_users_keeps_shared_and_registered_credentials_for_reject_new(self):
        user = self.make_user(2, DeviceLimitAction.reject_new)
        user.username = "reject-user"
        user.proxies.append(Proxy(type=ProxyTypes.VLESS, settings={"id": "shared-id", "flow": ""}))
        self.db.commit()
        crud.register_user_device(self.db, user, "phone")
        crud.register_user_device(self.db, user, "laptop")

        config = XRayConfig({
            "inbounds": [
                {"tag": "VLESS", "protocol": "vless", "port": 443,
                 "settings": {"clients": []}},
            ],
            "outbounds": [{"tag": "DIRECT", "protocol": "freedom"}],
        })

        class _DBContext:
            def __enter__(inner_self):
                return self.db

            def __exit__(inner_self, *args):
                return False

        with patch("app.xray.config.GetDB", return_value=_DBContext()):
            generated = config.include_db_users()

        clients = generated.get_inbound("VLESS")["settings"]["clients"]
        self.assertEqual(len(clients), 3)
        self.assertEqual({client["email"] for client in clients}, {f"{user.id}.{user.username}"} | {
            f"{user.id}.{user.username}.device-{device.hwid_hash[:16]}"
            for device in user.devices
        })
        self.assertIn("shared-id", {client["id"] for client in clients})
        for device in user.devices:
            self.assertIn(device.credentials["vless"]["id"], {client["id"] for client in clients})

    def subscription_response(self, user):
        return UserResponse.model_construct(
            username=user.username, status=UserStatus.active, used_traffic=0,
            created_at=user.created_at, device_limit=user.device_limit,
            device_limit_action=user.device_limit_action,
            proxies={proxy.type: proxy.type.settings_model.model_validate(proxy.settings)
                     for proxy in user.proxies},
            inbounds={proxy.type: [proxy.type.value.upper()] for proxy in user.proxies},
        )

    def fetch_subscription(self, user, path, headers=None):
        # Exercise the real ASGI router/header extraction without TestClient's
        # undeclared httpx dependency or a production JWT/inbounds database.
        from fastapi import FastAPI
        from config import XRAY_SUBSCRIPTION_PATH

        app = FastAPI()
        app.include_router(subscription.router)
        app.dependency_overrides[subscription.get_db] = lambda: self.db
        app.dependency_overrides[subscription.get_validated_sub] = lambda: user
        url = f"/{XRAY_SUBSCRIPTION_PATH}/test-token{path}"
        scope = {
            "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
            "method": "GET", "scheme": "https", "path": url,
            "raw_path": url.encode(), "query_string": b"", "root_path": "",
            "server": ("test.local", 443), "client": ("198.51.100.10", 1234),
            "headers": [(key.lower().encode(), value.encode())
                        for key, value in (headers or {}).items()],
        }
        messages = []

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            messages.append(message)

        response = self.subscription_response(user)
        def generate(*, user, **kwargs):
            return str(user.proxies[ProxyTypes.VLESS].id)

        with patch.object(subscription.UserResponse, "model_validate", return_value=response), \
                patch.object(subscription, "generate_subscription", side_effect=generate) as generated, \
                patch.object(subscription.crud, "update_user_sub"), \
                patch.object(subscription.xray.operations, "sync_user_device_accounts") as synced:
            asyncio.run(app(scope, receive, send))
        status = next(msg["status"] for msg in messages if msg["type"] == "http.response.start")
        body = b"".join(msg.get("body", b"") for msg in messages).decode()
        return status, body, response, generated, synced

    def test_no_hwid_subscriptions_are_generated_without_registering_devices(self):
        user = self.make_user(1, DeviceLimitAction.reject_new)
        shared = "35e4e39c-7d5c-4f4b-8b71-558e4f37ff53"
        user.proxies.append(Proxy(type=ProxyTypes.VLESS, settings={"id": shared}))
        self.db.commit()
        # Include a full device table: compatibility must not depend on slots.
        crud.register_user_device(self.db, user, "existing-phone")
        for limit in (0, 1, 10):
            user.device_limit = limit
            self.db.commit()
            for client_type in subscription.client_config:
                with self.subTest(limit=limit, client_type=client_type):
                    status, body, response, generated, synced = self.fetch_subscription(
                        user, f"/{client_type}")
                    self.assertEqual(status, 200)
                    self.assertEqual(body, shared)
                    generated.assert_called_once()
                    self.assertIs(generated.call_args.kwargs["user"], response)
                    self.assertEqual(self.db.query(UserDevice).count(), 1)
                    synced.assert_not_called()
        for agent, format_name in (("Clash/1", "clash"), ("Clash.Meta/1", "clash-meta"),
                                   ("HiddifyNext/1", "sing-box"), ("v2rayN/6.0", "v2ray")):
            with self.subTest(user_agent=agent):
                status, body, _, generated, _ = self.fetch_subscription(
                    user, "/", {"User-Agent": agent})
                self.assertEqual(status, 200)
                self.assertEqual(body, shared)
                self.assertEqual(generated.call_args.kwargs["config_format"], format_name)

    def test_hwid_subscriptions_register_reuse_private_credentials_and_reject_excess(self):
        user = self.make_user(1, DeviceLimitAction.reject_new)
        shared = "35e4e39c-7d5c-4f4b-8b71-558e4f37ff53"
        user.proxies.append(Proxy(type=ProxyTypes.VLESS, settings={"id": shared}))
        self.db.commit()
        status, body, response, generated, synced = self.fetch_subscription(
            user, "/clash-meta", {"X-HWID": "phone"})
        self.assertEqual(status, 200)
        private = crud.get_user_device_credentials(self.db, user, "phone")["vless"]["id"]
        self.assertEqual(body, private)
        self.assertNotEqual(body, shared)
        self.assertEqual(str(response.proxies[ProxyTypes.VLESS].id), shared)
        self.assertIsNot(generated.call_args.kwargs["user"], response)
        synced.assert_called_once_with(user)
        for client_type in subscription.client_config:
            with self.subTest(client_type=client_type):
                status, body, _, generated, synced = self.fetch_subscription(
                    user, f"/{client_type}", {"X-HWID": "phone"})
                self.assertEqual((status, body), (200, private))
                generated.assert_called_once()
                synced.assert_called_once_with(user)
                status, _, _, generated, synced = self.fetch_subscription(
                    user, f"/{client_type}", {"X-HWID": "second-phone"})
                self.assertEqual(status, 429)
                generated.assert_not_called()
                synced.assert_not_called()
        self.assertEqual(self.db.query(UserDevice).count(), 1)

    def test_zero_limit_accepts_multiple_hwid_clients(self):
        user = self.make_user(0, DeviceLimitAction.reject_new)
        user.proxies.append(Proxy(type=ProxyTypes.VLESS, settings={
            "id": "35e4e39c-7d5c-4f4b-8b71-558e4f37ff53"}))
        self.db.commit()
        ids = []
        for hwid in ("phone", "laptop", "tablet"):
            status, body, _, _, _ = self.fetch_subscription(user, "/v2ray", {"X-HWID": hwid})
            self.assertEqual(status, 200)
            ids.append(body)
        self.assertEqual(len(set(ids)), 3)
        self.assertEqual(self.db.query(UserDevice).count(), 3)

    def test_shared_and_private_credentials_sync_to_main_and_connected_nodes(self):
        user = self.make_user(1, DeviceLimitAction.reject_new)
        shared = "35e4e39c-7d5c-4f4b-8b71-558e4f37ff53"
        user.proxies.append(Proxy(type=ProxyTypes.VLESS, settings={"id": shared}))
        self.db.commit()
        crud.register_user_device(self.db, user, "phone")
        private = crud.get_user_device_credentials(self.db, user, "phone")["vless"]["id"]
        main_api, node_api, offline_api = Mock(), Mock(), Mock()
        nodes = {1: SimpleNamespace(connected=True, started=True, api=node_api),
                 2: SimpleNamespace(connected=False, started=True, api=offline_api)}
        response = self.subscription_response(user)
        with patch.object(operations.UserResponse, "model_validate", return_value=response), \
                patch.object(xray, "api", main_api), patch.object(xray, "nodes", nodes), \
                patch.object(operations, "_alter_inbound_user") as alter, \
                patch.object(operations, "_remove_user_from_inbound") as remove:
            operations.sync_user_device_accounts(user)
            remove.assert_not_called()
            self.assertEqual(alter.call_count, 4)
            for api in (main_api, node_api):
                accounts = [call.args[2] for call in alter.call_args_list if call.args[0] is api]
                self.assertEqual({str(account.id) for account in accounts}, {shared, private})
                self.assertEqual({account.email for account in accounts}, {
                    f"{user.id}.{user.username}",
                    f"{user.id}.{user.username}.device-{user.devices[0].hwid_hash[:16]}"})
            self.assertFalse(any(call.args[0] is offline_api for call in alter.call_args_list))
            # Switching back to log_only retains the shared account and removes
            # private labels from both the main core and the same Node.
            user.device_limit_action = DeviceLimitAction.log_only
            alter.reset_mock()
            operations.sync_user_device_accounts(user)
            self.assertEqual(alter.call_count, 2)
            self.assertEqual(remove.call_count, 2)
            self.assertTrue(all(str(call.args[2].id) == shared for call in alter.call_args_list))

    def test_reject_new_config_keeps_shared_account_before_any_device_registers(self):
        user = self.make_user(1, DeviceLimitAction.reject_new)
        user.proxies.append(Proxy(type=ProxyTypes.VLESS, settings={"id": "shared-id"}))
        self.db.commit()
        config = XRayConfig({"inbounds": [{"tag": "VLESS", "protocol": "vless", "port": 443,
                                         "settings": {"clients": []}}],
                            "outbounds": [{"tag": "DIRECT", "protocol": "freedom"}]})
        with patch("app.xray.config.GetDB") as context:
            context.return_value.__enter__.return_value = self.db
            generated = config.include_db_users()
        self.assertEqual(generated.get_inbound("VLESS")["settings"]["clients"],
                         [{"email": f"{user.id}.{user.username}", "id": "shared-id"}])

    def test_shared_and_private_accounts_keep_identical_xtls_transport_rules(self):
        from xray_api.types.account import XTLSFlows

        user = self.make_user(1, DeviceLimitAction.reject_new)
        user.proxies.append(Proxy(type=ProxyTypes.VLESS, settings={
            "id": "35e4e39c-7d5c-4f4b-8b71-558e4f37ff53",
            "flow": "xtls-rprx-vision",
        }))
        self.db.commit()
        crud.register_user_device(self.db, user, "phone")
        for network, tls, header, keep_flow in (
            ("tcp", "tls", "", True), ("raw", "reality", "", True),
            ("kcp", "tls", "", True), ("ws", "tls", "", False),
            ("grpc", "tls", "", False), ("tcp", "none", "", False),
            ("tcp", "tls", "http", False),
        ):
            with self.subTest(network=network, tls=tls, header=header):
                config = XRayConfig({"inbounds": [{
                    "tag": "VLESS", "protocol": "vless", "port": 443,
                    "settings": {"clients": []},
                }], "outbounds": [{"tag": "DIRECT", "protocol": "freedom"}]})
                config.inbounds_by_tag["VLESS"].update(
                    network=network, tls=tls, header_type=header)
                with patch("app.xray.config.GetDB") as context:
                    context.return_value.__enter__.return_value = self.db
                    generated = config.include_db_users()
                clients = generated.get_inbound("VLESS")["settings"]["clients"]
                self.assertEqual(len(clients), 2)
                self.assertTrue(all(bool(client.get("flow")) == keep_flow for client in clients))
                with patch.object(operations.UserResponse, "model_validate",
                                  return_value=self.subscription_response(user)), \
                        patch.object(xray, "config", config), patch.object(xray, "nodes", {}), \
                        patch.object(operations, "_alter_inbound_user") as alter:
                    operations.sync_user_device_accounts(user)
                self.assertEqual(alter.call_count, 2)
                expected = XTLSFlows.VISION if keep_flow else XTLSFlows.NONE
                self.assertTrue(all(call.args[2].flow == expected for call in alter.call_args_list))

    def test_include_db_users_restores_shared_credential_for_log_only(self):
        user = self.make_user(1, DeviceLimitAction.log_only)
        user.username = "log-only-user"
        user.proxies.append(Proxy(type=ProxyTypes.VLESS, settings={"id": "shared-id", "flow": ""}))
        self.db.commit()
        crud.register_user_device(self.db, user, "phone")

        config = XRayConfig({
            "inbounds": [
                {"tag": "VLESS", "protocol": "vless", "port": 443,
                 "settings": {"clients": []}},
            ],
            "outbounds": [{"tag": "DIRECT", "protocol": "freedom"}],
        })

        class _DBContext:
            def __enter__(inner_self):
                return self.db

            def __exit__(inner_self, *args):
                return False

        with patch("app.xray.config.GetDB", return_value=_DBContext()):
            generated = config.include_db_users()

        clients = generated.get_inbound("VLESS")["settings"]["clients"]
        self.assertEqual(len(clients), 1)
        self.assertEqual(clients[0]["email"], f"{user.id}.{user.username}")
        self.assertEqual(clients[0]["id"], "shared-id")

    def test_node_active_users_uses_recent_distinct_positive_traffic(self):
        first = self.make_user()
        second = User(username="device_test_user_second", status=UserStatus.active)
        expired = User(username="device_test_user_expired", status=UserStatus.expired)
        self.db.add_all([second, expired])
        self.db.commit()
        now = datetime.utcnow()
        self.db.add_all([
            NodeUserUsage(node_id=42, user_id=first.id, created_at=now, used_traffic=10),
            NodeUserUsage(node_id=42, user_id=first.id, created_at=now - timedelta(hours=1), used_traffic=20),
            NodeUserUsage(node_id=42, user_id=second.id, created_at=now, used_traffic=0),
            NodeUserUsage(node_id=42, user_id=expired.id, created_at=now, used_traffic=50),
        ])
        self.db.commit()

        summary = crud.get_node_active_users(self.db, 42)

        self.assertEqual(summary["active_users"], 1)
        self.assertEqual(summary["active_users_window_hours"], 2)
        self.assertIsNone(summary["active_users_reason"])

    def test_node_active_users_distinguishes_no_sample_from_zero(self):
        self.assertIsNone(crud.get_node_active_users(self.db, 404)["active_users"])
        now = datetime.utcnow()
        user = self.make_user()
        self.db.add(NodeUserUsage(
            node_id=405,
            user_id=user.id,
            created_at=now - timedelta(minutes=5),
            used_traffic=0,
        ))
        self.db.commit()

        summary = crud.get_node_active_users(self.db, 405)

        self.assertEqual(summary["active_users"], 0)
        self.assertIsNone(summary["active_users_reason"])


if __name__ == "__main__":
    unittest.main()
