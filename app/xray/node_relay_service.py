"""Persistence, sudo-only control and subscription publication for TCP relays."""
import threading

from app import logger, xray
from app.db import GetDB
from app.db.models import Node, NodeRelay
from app.models.node import NodeStatus
from app.xray.node_relay import (
    RelayProcess, business_inbounds, choose_port, clean_address, config_ports, host_target, rewrite_hosts,
)
from config import UVICORN_PORT, XRAY_ASSETS_PATH, XRAY_EXECUTABLE_PATH

runtime = RelayProcess(XRAY_EXECUTABLE_PATH, XRAY_ASSETS_PATH)
lock = threading.RLock()
_published = []
_errors = {}
_remote_live = {}
CAPABILITY = "managed-node-relay-v1"


def _profile(row, node, config):
    inbound = business_inbounds(config).get(row.inbound_tag)
    if inbound is None:
        raise ValueError("The selected VLESS TCP REALITY inbound is missing or incompatible")
    target = clean_address(node.address)
    entry = clean_address(row.entry_address)
    source = row.source or "main"
    source_id = row.source_node_id if source == "node" else None
    if source == "node":
        origin = row.source_node
        if origin is None or origin.status == NodeStatus.disabled:
            raise ValueError("Source Node is missing or disabled")
        if origin.id == node.id or clean_address(origin.address) == target:
            raise ValueError("A Node cannot relay to itself or another Node on the same address")
    if ":" in entry:
        raise ValueError("IPv6 relay entry is not supported; use the selected source IPv4 or DNS-only hostname")
    if row.listen_port in config_ports(config) | {UVICORN_PORT, node.port, node.api_port}:
        raise ValueError("Relay port conflicts with a proxy/control/API/panel port")
    if target == entry and row.listen_port == inbound["port"]:
        raise ValueError("Relay would forward back to itself")
    if not any(host_target(host, inbound["port"]) == (target, inbound["port"])
               for host in xray.hosts.get(row.inbound_tag, [])):
        raise ValueError("No matching original Host: use this Node address and business port in Hosts; mixed-address entries are not rewritten")
    return {"node_id": node.id, "name": node.name, "entry_address": entry,
            "listen_port": row.listen_port, "inbound_tag": row.inbound_tag,
            "target_address": target, "target_port": inbound["port"],
            "source": source, "source_node_id": source_id}


def _plans(db, override_id=None, override=None):
    profiles, errors = [], {}
    nodes = {node.id: node for node in db.query(Node).all()}
    rows = {row.node_id: row for row in db.query(NodeRelay).all()}
    if override_id is not None:
        rows.pop(override_id, None)
        if override is not None:
            rows[override_id] = override
    # Each target has at most one source. Reject cycles, including old persisted
    # records, without depending on subscription names or network DNS guesses.
    for seed in rows:
        seen, current = set(), seed
        while current in rows and (rows[current].source or "main") == "node":
            if current in seen:
                errors[seed] = "Node relay cycle is not allowed"
                break
            seen.add(current)
            current = rows[current].source_node_id
    for node_id, row in rows.items():
        node = nodes.get(node_id)
        if node is None or node.status == NodeStatus.disabled or node_id in errors:
            continue
        try:
            profiles.append(_profile(row, node, xray.config))
        except ValueError as exc:
            errors[node_id] = str(exc)
    # Old relay rows may already share one business destination. Do not guess
    # which source port should replace an original subscription Host.
    destinations = {}
    for item in profiles:
        key = (item["inbound_tag"], item["target_address"], item["target_port"])
        destinations.setdefault(key, []).append(item["node_id"])
    for node_ids in destinations.values():
        if len(node_ids) > 1:
            for node_id in node_ids:
                errors[node_id] = "Multiple Nodes share this business destination; cannot rewrite the original Host unambiguously"
    profiles = [item for item in profiles if item["node_id"] not in errors]
    return profiles, errors


def _wire(profiles):
    return sorted([{key: item[key] for key in ("node_id", "listen_port", "target_address", "target_port")}
                   for item in profiles], key=lambda item: item["node_id"])


def _source_state(source_id, require_started=True):
    client = xray.nodes.get(source_id)
    if client is None:
        raise ValueError("Source Node is not connected")
    try:
        state = client.get_relay_status()
    except Exception as exc:
        raise ValueError(f"Source Node relay capability unavailable: {exc}") from exc
    if not isinstance(state, dict) or state.get("capability") != CAPABILITY:
        raise ValueError("Update the source Node: managed-node-relay-v1 is required")
    if require_started and state.get("core_started") is not True:
        raise ValueError("Source Node core is not started")
    return client, state


def _apply(profiles, recover=False, sources=None):
    """Apply source snapshots; strict saves compensate every changed source.

    Recovery isolates source failures. Remote publication requires an exact ACK,
    never merely successful delivery or a still-open control session.
    """
    groups = {0: []}
    for item in profiles:
        groups.setdefault(item["source_node_id"] or 0, []).append(item)
    for source_id in list(_remote_live):
        groups.setdefault(source_id, [])
    previous_main = [dict(item) for item in runtime.profiles]
    changed, errors = [], {}
    for source_id, items in groups.items():
        if sources is not None and source_id not in sources:
            continue
        try:
            if source_id == 0:
                runtime.apply(items)
                continue
            if not items and source_id not in xray.nodes:
                _remote_live.pop(source_id, None)
                continue
            client, state = _source_state(source_id, require_started=bool(items))
            wire = _wire(items)
            if state.get("profiles") == wire and (not wire or state.get("running") is True):
                _remote_live[source_id] = (client, wire)
                continue
            changed.append((source_id, client, state.get("profiles", [])))
            _remote_live.pop(source_id, None)
            ack = client.set_relays(wire)
            if not isinstance(ack, dict) or ack.get("capability") != CAPABILITY or ack.get("profiles") != wire or (wire and ack.get("running") is not True):
                raise RuntimeError("Source Node relay acknowledgement does not match the requested snapshot")
            _remote_live[source_id] = (client, wire)
        except Exception as exc:
            if source_id:
                _remote_live.pop(source_id, None)
            for item in items:
                errors[item["node_id"]] = f"Relay source {source_id or 'main'}: {exc}"
            if recover:
                logger.warning("Managed relay source %s failed: %s", source_id or "main", exc)
                continue
            rollback_errors = []
            for origin_id, origin, previous in reversed(changed):
                try:
                    ack = origin.set_relays(previous)
                    if not isinstance(ack, dict) or ack.get("capability") != CAPABILITY or ack.get("profiles") != previous or (previous and ack.get("running") is not True):
                        raise RuntimeError("rollback acknowledgement mismatch")
                    _remote_live[origin_id] = (origin, previous)
                except Exception as restore:
                    _remote_live.pop(origin_id, None)
                    rollback_errors.append(str(restore))
            try:
                runtime.apply(previous_main)
            except Exception as restore:
                rollback_errors.append(str(restore))
            detail = str(exc) + ("; rollback failed: " + "; ".join(rollback_errors) if rollback_errors else "")
            raise RuntimeError(detail) from exc
    return errors


def _publish(profiles):
    global _published
    live = {item["node_id"]: item for item in runtime.snapshot()}
    for source_id, (client, items) in _remote_live.items():
        if xray.nodes.get(source_id) is client:
            for item in items:
                live[item["node_id"]] = {**item, "source_node_id": source_id}
    # Never advertise a new destination until the actual listener matches it.
    fields = ("listen_port", "target_address", "target_port", "source_node_id")
    _published = [item for item in profiles if item["node_id"] in live
                  and all(item[key] == live[item["node_id"]][key] for key in fields)]


def refresh():
    global _errors
    with lock:
        with GetDB() as db:
            profiles, _errors = _plans(db)
        _errors.update(_apply(profiles, recover=True))
        _publish(profiles)


def stop():
    global _published
    with lock:
        _published = []
        _apply([], recover=True)
        _remote_live.clear()
        runtime.stop()


def relay_profiles(tag):
    with lock:
        # A stopped process cannot replace a usable original direct endpoint.
        main_ids = {item["node_id"] for item in runtime.snapshot()}
        return [dict(item) for item in _published if item["inbound_tag"] == tag
                and ((item["source"] == "main" and item["node_id"] in main_ids)
                     or (item["source"] == "node" and item["source_node_id"] in _remote_live
                         and xray.nodes.get(item["source_node_id"]) is _remote_live[item["source_node_id"]][0]))]


def subscription_hosts(tag):
    with lock:
        inbound = xray.config.inbounds_by_tag.get(tag, {})
        return rewrite_hosts(xray.hosts.get(tag, []), relay_profiles(tag), inbound.get("port"))


def options(db):
    first = db.query(NodeRelay).filter(NodeRelay.source == "main").order_by(NodeRelay.node_id).first()
    return {"source": "main", "sources": ["main", "node"],
            "source_nodes": [{"id": node.id, "name": node.name, "address": node.address,
                              "connected": node.status == NodeStatus.connected} for node in db.query(Node).all()],
            "required_node_capability": CAPABILITY,
            "default_entry_address": first.entry_address if first else "",
            "inbounds": [{"tag": tag, "port": item["port"], "network": item["network"],
                          "protocol": item["protocol"], "tls": item["tls"]}
                         for tag, item in business_inbounds(xray.config).items()],
            "automatic_port_start": 18443, "transport": "tcp",
            "original_direct_hosts_preserved": True}


def public(node):
    with lock:
        row = node.relay
        if row is None:
            return {"configured": False, "mode": "direct", "status": "inactive"}
        result = {"configured": True, "mode": "relay", "source": row.source or "main", "source_node_id": row.source_node_id,
                  "entry_address": row.entry_address, "allocation": row.allocation,
                  "listen_port": row.listen_port, "inbound_tag": row.inbound_tag,
                  "target_address": node.address, "target_port": None}
        try:
            candidate = _profile(row, node, xray.config)
            result["target_port"] = candidate["target_port"]
        except ValueError as exc:
            return {**result, "status": "error", "error": str(exc)}
        if node.status == NodeStatus.disabled:
            return {**result, "status": "inactive", "error": "Node is disabled"}
        if node.id in _errors:
            return {**result, "status": "error", "error": _errors[node.id]}
        if candidate in relay_profiles(row.inbound_tag):
            return {**result, "status": "running", "error": None}
        error = _errors.get(node.id) or (runtime.last_error if candidate["source"] == "main" else None)
        return {**result, "status": "error" if error else "pending", "error": error}


def save(db, node, settings):
    """Apply then commit, restoring the old runtime on DB failure.

    Global lock + unique port constraint serialize allocation in the supported
    single-panel-worker deployment. A direct switch deletes only this relay row.
    """
    global _errors
    from types import SimpleNamespace
    with lock:
        old_profiles, old_errors = _plans(db)
        row = node.relay
        new = None
        if settings.mode == "relay":
            if not settings.inbound_tag or not settings.entry_address:
                raise ValueError("Select a target inbound and enter the relay source address")
            if node.status == NodeStatus.disabled:
                raise ValueError("Enable the Node before configuring a relay")
            if settings.allocation == "manual" and settings.listen_port is None:
                raise ValueError("Manual allocation requires listen_port")
            reserved = config_ports(xray.config) | {UVICORN_PORT}
            for other in db.query(Node).all():
                reserved.update((other.port, other.api_port))
            allocated = {other.listen_port for other in db.query(NodeRelay).all() if other.node_id != node.id}
            port = choose_port(settings.listen_port if settings.allocation == "manual" else None,
                               row.listen_port if row else None, reserved, allocated,
                               runtime.occupied_ports() if settings.source == "main" else set())
            new = SimpleNamespace(node_id=node.id, entry_address=clean_address(settings.entry_address),
                                  allocation=settings.allocation, listen_port=port, inbound_tag=settings.inbound_tag,
                                  source=settings.source, source_node_id=settings.source_node_id,
                                  source_node=db.get(Node, settings.source_node_id) if settings.source_node_id else None)
            if new.source == "node":
                if new.source_node is None or new.source_node.status != NodeStatus.connected:
                    raise ValueError("Source Node must exist and be connected")
                _, state = _source_state(new.source_node_id)
                port = choose_port(settings.listen_port if settings.allocation == "manual" else None,
                                   row.listen_port if row else None, reserved, allocated, state.get("occupied_ports", []))
                new.listen_port = port
            candidate = _profile(new, node, xray.config)
            if any(item["node_id"] != node.id and item["inbound_tag"] == candidate["inbound_tag"]
                   and (item["target_address"], item["target_port"]) ==
                       (candidate["target_address"], candidate["target_port"]) for item in old_profiles):
                raise ValueError("Multiple Nodes share this business destination; cannot rewrite the original Host unambiguously")
        profiles, errors = _plans(db, node.id, new)
        if node.id in errors and new is not None:
            raise ValueError(errors[node.id])
        # Saving one target must not probe/rewrite unrelated source processes.
        # Periodic refresh still reconciles every source and isolates failures.
        affected = {item.source_node_id if (item.source or "main") == "node" else 0
                    for item in (row, new) if item is not None}
        _apply(profiles, sources=affected)
        try:
            if new is None:
                if row is not None:
                    db.delete(row)
            else:
                if row is None:
                    row = NodeRelay(node=node)
                    db.add(row)
                for key in ("entry_address", "allocation", "listen_port", "inbound_tag", "source", "source_node_id"):
                    setattr(row, key, getattr(new, key))
            db.commit()
            db.refresh(node)
        except Exception:
            db.rollback()
            try:
                _apply(old_profiles, sources=affected)
            finally:
                _errors = old_errors
                _publish(old_profiles)
            raise
        _errors = errors
        _publish(profiles)
        return public(node)
