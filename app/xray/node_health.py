"""Validate fresh, scoped Node telemetry before returning it to admins."""

import math
from datetime import datetime, timezone


_BYTE_FIELDS = (
    "memory_total_bytes", "memory_used_bytes", "disk_total_bytes", "disk_used_bytes"
)

_ACTIVITY_FIELDS = (
    "active_users",
    "active_users_window_seconds",
    "active_users_sampled_at",
    "activity_source",
    "activity_scope",
    "activity_reason",
)


def _optional_non_negative_int(value):
    return (value is None or
            (isinstance(value, int) and not isinstance(value, bool) and value >= 0))


def _optional_timestamp(value, now=None, max_age=None):
    if value is None:
        return True
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return False
    if parsed.tzinfo is None:
        return False
    age = ((now or datetime.now(timezone.utc)) - parsed).total_seconds()
    return age >= -5 and (max_age is None or age <= max_age)


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
        # Core online users and observed recent traffic have separate scopes.
        # Neither value represents physical devices or TCP sockets.
        if not _optional_non_negative_int(data.get("active_users")):
            return None
        window_seconds = data.get("active_users_window_seconds")
        if (window_seconds is not None and
                (isinstance(window_seconds, bool) or not isinstance(window_seconds, int)
                 or not 10 <= window_seconds <= 86400)):
            return None
        if not _optional_timestamp(data.get("active_users_sampled_at"), now, 15):
            return None
        for field in ("activity_source", "activity_scope", "activity_reason"):
            value = data.get(field)
            if value is not None and (not isinstance(value, str) or len(value) > 128):
                return None
        if data.get("activity_source") not in (None, "xray-user-stats-delta", "xray-online-users"):
            return None
        if data.get("activity_scope") not in (None, "recent_traffic", "online_users"):
            return None
        source, scope = data.get("activity_source"), data.get("activity_scope")
        if source == "xray-online-users" and (scope != "online_users" or window_seconds is not None):
            return None
        if source == "xray-user-stats-delta" and (scope != "recent_traffic" or window_seconds is None):
            return None
        if source and data.get("active_users") is not None and data.get("active_users_sampled_at") is None:
            return None
        result["active_users"] = data.get("active_users") if source else None
        for field in _ACTIVITY_FIELDS[1:]:
            result[field] = data.get(field)

        policy_count = data.get("policy_count")
        if policy_count is not None and (isinstance(policy_count, bool) or not isinstance(policy_count, int)
                or not 0 <= policy_count <= 10000):
            return None
        policy_enforcement = data.get("policy_enforcement", "unsupported")
        if policy_enforcement not in ("subscription_request_only",
                                      "subscription_request_and_node_credentials", "unsupported"):
            return None
        result["policy_count"] = policy_count
        result["policy_enforcement"] = policy_enforcement
        if not _optional_timestamp(data.get("policy_synced_at"), now):
            return None
        revision = data.get("policy_revision")
        if revision is not None and (not isinstance(revision, str) or len(revision) != 64
                                     or any(c not in "0123456789abcdef" for c in revision)):
            return None
        direct_enforced = data.get("direct_connection_enforced", False)
        if direct_enforced not in (False, True):
            return None
        result.update(policy_synced_at=data.get("policy_synced_at"), policy_revision=revision,
                      direct_connection_enforced=direct_enforced)
        for prefix in ("memory", "disk"):
            total, used = result[f"{prefix}_total_bytes"], result[f"{prefix}_used_bytes"]
            if (total is None) != (used is None) or (total is not None and used > total):
                return None
        if all(result[key] is None for key in _BYTE_FIELDS + ("uptime_seconds", "cpu_percent")):
            return None
        return result
    except (TypeError, ValueError, KeyError, OverflowError):
        return None
