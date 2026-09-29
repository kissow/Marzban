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
