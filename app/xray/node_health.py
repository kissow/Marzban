"""Validate fresh, scoped Node telemetry before returning it to admins."""

import math
from datetime import datetime, timezone


_BYTE_FIELDS = (
    "memory_total_bytes", "memory_used_bytes", "disk_total_bytes", "disk_used_bytes"
)


def normalize_node_health(raw, now=None):
    """Return a safe snapshot, or None when data is invalid or older than 15s."""
    try:
        data = dict(raw)
        sampled_at = datetime.fromisoformat(data["sampled_at"])
        if sampled_at.tzinfo is None:
            return None
        age = ((now or datetime.now(timezone.utc)) - sampled_at).total_seconds()
        if age < -5 or age > 15 or data.get("source") != "node-runtime":
            return None
        result = {
            "sampled_at": sampled_at.isoformat(),
            "source": "node-runtime",
            "disk_path": data.get("disk_path"),
            "cpu_scope": data.get("cpu_scope"),
            "memory_scope": data.get("memory_scope"),
            "disk_scope": data.get("disk_scope"),
            "uptime_scope": data.get("uptime_scope"),
        }
        if any(not isinstance(result[key], str) or not result[key] for key in
               ("disk_path", "cpu_scope", "memory_scope", "disk_scope", "uptime_scope")):
            return None
        for field in _BYTE_FIELDS + ("uptime_seconds",):
            value = data.get(field)
            if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 0):
                return None
            result[field] = value
        cpu = data.get("cpu_percent")
        if cpu is not None and (isinstance(cpu, bool) or not isinstance(cpu, (int, float))
                                or not math.isfinite(cpu) or not 0 <= cpu <= 100):
            return None
        result["cpu_percent"] = cpu
        # Never substitute host TCP sockets or the panel-wide 24h count.
        result["active_users"] = None
        for prefix in ("memory", "disk"):
            total, used = result[f"{prefix}_total_bytes"], result[f"{prefix}_used_bytes"]
            if (total is None) != (used is None) or (total is not None and used > total):
                return None
        if all(result[key] is None for key in _BYTE_FIELDS + ("uptime_seconds", "cpu_percent")):
            return None
        return result
    except (TypeError, ValueError, KeyError, OverflowError):
        return None
