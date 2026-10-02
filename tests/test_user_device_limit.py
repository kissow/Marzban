import atexit
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

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
    from app.db.models import NodeUserUsage, Proxy, User
    from app.models.proxy import ProxyTypes
    from app.models.user import DeviceLimitAction, UserStatus
    from app.xray.config import XRayConfig
finally:
    os.chdir(_TEST_PREVIOUS_CWD)


def _cleanup_test_runtime():
    _TEST_RUNTIME.cleanup()


atexit.register(_cleanup_test_runtime)


class UserDeviceLimitTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
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

    def test_include_db_users_loads_only_registered_credentials_for_reject_new(self):
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
        self.assertEqual(len(clients), 2)
        self.assertEqual({client["email"] for client in clients}, {
            f"{user.id}.{user.username}.device-{device.hwid_hash[:16]}"
            for device in user.devices
        })
        self.assertNotIn("shared-id", {client["id"] for client in clients})

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
