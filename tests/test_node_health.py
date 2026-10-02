import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


spec = importlib.util.spec_from_file_location(
    "node_health", Path(__file__).resolve().parents[1] / "app" / "xray" / "node_health.py"
)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
normalize_node_health = module.normalize_node_health


class NodeHealthTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.raw = {
            "sampled_at": self.now.isoformat(), "source": "node-runtime",
            "disk_path": "/", "cpu_scope": "host-kernel-procfs",
            "memory_scope": "host-kernel-procfs",
            "disk_scope": "runtime-rootfs", "uptime_scope": "host-kernel-procfs",
            "cpu_percent": 25.0, "memory_total_bytes": 100,
            "memory_used_bytes": 40, "disk_total_bytes": 200,
            "disk_used_bytes": 50, "uptime_seconds": 60,
        }

    def test_fresh_metrics_are_returned(self):
        self.assertEqual(normalize_node_health(self.raw, self.now)["cpu_percent"], 25.0)

    def test_online_users_are_not_inferred_from_host_connections(self):
        self.raw["active_users"] = 999
        self.assertIsNone(normalize_node_health(self.raw, self.now)["active_users"])

    def activity(self, **overrides):
        self.raw.update(active_users=3, active_users_window_seconds=120,
                        active_users_sampled_at=self.now.isoformat(),
                        activity_source="xray-user-stats-delta",
                        activity_scope="recent_traffic", activity_reason=None)
        self.raw.update(overrides)
        return normalize_node_health(self.raw, self.now)

    def test_valid_node_activity_is_preserved(self):
        result = self.activity()
        self.assertEqual(result["active_users"], 3)
        self.assertEqual(result["activity_source"], "xray-user-stats-delta")
        self.assertEqual(result["active_users_window_seconds"], 120)

    def test_online_user_scope_is_preserved(self):
        result = self.activity(activity_source="xray-online-users", activity_scope="online_users",
                               active_users_window_seconds=None)
        self.assertEqual(result["active_users"], 3)
        self.assertEqual(result["activity_scope"], "online_users")

    def test_unsupported_policy_is_not_reported_as_synced(self):
        result = normalize_node_health(self.raw, self.now)
        self.assertIsNone(result["policy_count"])
        self.assertEqual(result["policy_enforcement"], "unsupported")
        self.assertFalse(result["direct_connection_enforced"])

    def test_invalid_activity_is_rejected(self):
        for overrides in ({"active_users": True}, {"active_users": -1},
                          {"active_users_window_seconds": 0}, {"activity_source": "host-sockets"},
                          {"active_users_sampled_at": None},
                          {"active_users_sampled_at": (self.now-timedelta(seconds=20)).isoformat()},
                          {"active_users_sampled_at": (self.now+timedelta(seconds=20)).isoformat()},
                          {"activity_scope": "device_count"}):
            with self.subTest(overrides=overrides):
                self.activity()  # reset the optional contract
                self.assertIsNone(self.activity(**overrides))

    def test_policy_contract_preserves_direct_credential_enforcement_claim(self):
        self.raw.update(policy_count=3, policy_enforcement="subscription_request_and_node_credentials",
                        policy_synced_at=self.now.isoformat(), policy_revision="a" * 64,
                        direct_connection_enforced=True)
        result = normalize_node_health(self.raw, self.now)
        self.assertEqual(result["policy_count"], 3)
        self.assertEqual(result["policy_revision"], "a" * 64)
        self.assertEqual(result["policy_enforcement"], "subscription_request_and_node_credentials")
        self.assertTrue(result["direct_connection_enforced"])

    def test_stale_or_future_sample_is_unknown(self):
        self.raw["sampled_at"] = (self.now - timedelta(seconds=16)).isoformat()
        self.assertIsNone(normalize_node_health(self.raw, self.now))
        self.raw["sampled_at"] = (self.now + timedelta(seconds=6)).isoformat()
        self.assertIsNone(normalize_node_health(self.raw, self.now))

    def test_invalid_metrics_are_unknown(self):
        self.raw["memory_used_bytes"] = 101
        self.assertIsNone(normalize_node_health(self.raw, self.now))
        self.raw["memory_used_bytes"] = 40
        self.raw["cpu_percent"] = float("nan")
        self.assertIsNone(normalize_node_health(self.raw, self.now))

    def test_missing_or_naive_timestamp_is_unknown(self):
        self.raw["sampled_at"] = self.now.replace(tzinfo=None).isoformat()
        self.assertIsNone(normalize_node_health(self.raw, self.now))
        self.raw.pop("sampled_at")
        self.assertIsNone(normalize_node_health(self.raw, self.now))


if __name__ == "__main__":
    unittest.main()
