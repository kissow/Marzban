"""Build the small, non-sensitive device policy contract sent to Nodes."""

from typing import Iterable, List, Mapping

_SYNCED_STATUSES = {"active", "on_hold", "limited"}


def _value(value, default):
    return getattr(value, "value", value) if value is not None else default


def _get(user, key, default=None):
    if isinstance(user, Mapping):
        return user.get(key, default)
    return getattr(user, key, default)


def build_device_policy_snapshot(users: Iterable[object]) -> List[dict]:
    """Return a complete replacement snapshot for the supplied users.

    Only the stable user identity and the configured policy are sent.  Raw
    subscription tokens, passwords, HWIDs, IP addresses, and device records
    are intentionally excluded from this contract.
    """
    policies = []
    for user in users:
        status = _value(_get(user, "status"), None)
        if status not in _SYNCED_STATUSES:
            continue
        user_id = _get(user, "id")
        username = _get(user, "username")
        if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
            raise ValueError("Invalid device policy user ID")
        if not isinstance(username, str) or not 1 <= len(username) <= 34:
            raise ValueError("Invalid device policy username")
        limit = _get(user, "device_limit", 0) or 0
        if isinstance(limit, bool) or not isinstance(limit, int) or not 0 <= limit <= 100000:
            raise ValueError("Invalid device limit")
        mode = _value(_get(user, "device_limit_mode"), "hwid")
        action = _value(_get(user, "device_limit_action"), "log_only")
        if mode != "hwid" or action not in {"log_only", "reject_new"}:
            raise ValueError("Invalid device policy mode or action")
        policies.append({
            "user": f"{user_id}.{username}",
            "device_limit": limit,
            "device_limit_mode": mode,
            "device_limit_action": action,
        })
    return sorted(policies, key=lambda policy: policy["user"])


def build_device_policy_from_rows(rows: Iterable[Mapping]) -> List[dict]:
    """Build a snapshot from mapping-like rows for jobs and tests."""
    return build_device_policy_snapshot(rows)


__all__ = ["build_device_policy_snapshot", "build_device_policy_from_rows"]
