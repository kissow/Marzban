"""Persistence, sudo-only control and subscription publication for TCP relays."""
import threading

from app import logger, xray
from app.db import GetDB
from app.db.models import Node, NodeRelay
from app.models.node import NodeStatus
from app.xray.node_relay import (
    RelayProcess, business_inbounds, choose_port, clean_address, config_ports, subscription_host,
)
from config import UVICORN_PORT, XRAY_ASSETS_PATH, XRAY_EXECUTABLE_PATH

runtime = RelayProcess(XRAY_EXECUTABLE_PATH, XRAY_ASSETS_PATH)
lock = threading.RLock()
_published = []
_errors = {}


def _profile(row, node, config):
    inbound = business_inbounds(config).get(row.inbound_tag)
    if inbound is None:
        raise ValueError("The selected VLESS TCP REALITY inbound is missing or incompatible")
    target = clean_address(node.address)
    entry = clean_address(row.entry_address)
    if ":" in entry:
        raise ValueError("IPv6 relay entry is not supported; use the main-server IPv4 or DNS-only hostname")
    if row.listen_port in config_ports(config) | {UVICORN_PORT, node.port, node.api_port}:
        raise ValueError("Relay port conflicts with a proxy/control/API/panel port")
    if target == entry and row.listen_port == inbound["port"]:
        raise ValueError("Relay would forward back to itself")
    return {"node_id": node.id, "name": node.name, "entry_address": entry,
            "listen_port": row.listen_port, "inbound_tag": row.inbound_tag,
            "target_address": target, "target_port": inbound["port"]}


def _plans(db, override_id=None, override=None):
    profiles, errors = [], {}
    nodes = {node.id: node for node in db.query(Node).all()}
    rows = {row.node_id: row for row in db.query(NodeRelay).all()}
    if override_id is not None:
        rows.pop(override_id, None)
        if override is not None:
            rows[override_id] = override
    for node_id, row in rows.items():
        node = nodes.get(node_id)
        if node is None or node.status == NodeStatus.disabled:
            continue
        try:
            profiles.append(_profile(row, node, xray.config))
        except ValueError as exc:
            errors[node_id] = str(exc)
    return profiles, errors


def _publish(profiles):
    global _published
    live = {item["node_id"]: item for item in runtime.snapshot()}
    # Never advertise a new destination until the actual listener matches it.
    fields = ("listen_port", "target_address", "target_port")
    _published = [item for item in profiles if item["node_id"] in live
                  and all(item[key] == live[item["node_id"]][key] for key in fields)]


def refresh():
    global _errors
    with lock:
        with GetDB() as db:
            profiles, _errors = _plans(db)
        try:
            runtime.apply(profiles)
        except Exception as exc:
            logger.warning("Managed Node relay recovery failed: %s", exc)
        _publish(profiles)


def stop():
    global _published
    with lock:
        _published = []
        runtime.stop()


def subscription_hosts(tag):
    with lock:
        # A stopped process is not a usable subscription endpoint.
        if not runtime.running:
            return []
        return [subscription_host(item) for item in _published if item["inbound_tag"] == tag]


def options(db):
    first = db.query(NodeRelay).order_by(NodeRelay.node_id).first()
    return {"source": "main", "default_entry_address": first.entry_address if first else "",
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
        result = {"configured": True, "mode": "relay", "source": "main",
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
        if candidate in _published and runtime.running:
            return {**result, "status": "running", "error": None}
        error = _errors.get(node.id) or runtime.last_error
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
                raise ValueError("Select a target inbound and enter the main-server relay address")
            if node.status == NodeStatus.disabled:
                raise ValueError("Enable the Node before configuring a relay")
            if settings.allocation == "manual" and settings.listen_port is None:
                raise ValueError("Manual allocation requires listen_port")
            reserved = config_ports(xray.config) | {UVICORN_PORT}
            for other in db.query(Node).all():
                reserved.update((other.port, other.api_port))
            allocated = {other.listen_port for other in db.query(NodeRelay).all() if other.node_id != node.id}
            port = choose_port(settings.listen_port if settings.allocation == "manual" else None,
                               row.listen_port if row else None, reserved, allocated, runtime.occupied_ports())
            new = SimpleNamespace(node_id=node.id, entry_address=clean_address(settings.entry_address),
                                  allocation=settings.allocation, listen_port=port, inbound_tag=settings.inbound_tag)
            _profile(new, node, xray.config)
        profiles, errors = _plans(db, node.id, new)
        runtime.apply(profiles)
        try:
            if new is None:
                if row is not None:
                    db.delete(row)
            else:
                if row is None:
                    row = NodeRelay(node=node)
                    db.add(row)
                for key in ("entry_address", "allocation", "listen_port", "inbound_tag"):
                    setattr(row, key, getattr(new, key))
            db.commit()
            db.refresh(node)
        except Exception:
            db.rollback()
            try:
                runtime.apply(old_profiles)
            finally:
                _errors = old_errors
                _publish(old_profiles)
            raise
        _errors = errors
        _publish(profiles)
        return public(node)
