"""Encrypted storage for one optional outbound proxy per Marzban-Node."""

import base64
import hashlib

from cryptography.fernet import Fernet

from app.db import crud
from app.db.models import NodeEgress
from app.xray.node_egress import validate_egress


def _cipher(db):
    secret = crud.get_jwt_secret_key(db)
    if not secret:
        raise RuntimeError("JWT secret is not initialized; cannot protect node egress credentials")
    key = base64.urlsafe_b64encode(
        hashlib.sha256(b"marzban-node-egress-v1:" + secret.encode("utf-8")).digest()
    )
    return Fernet(key)


def _encrypt(db, value):
    return _cipher(db).encrypt(value.encode("utf-8")).decode("ascii") if value else None


def _decrypt(db, value):
    return _cipher(db).decrypt(value.encode("ascii")).decode("utf-8") if value else None


def read_egress(db, dbnode):
    """Return this Node's sole proxy for internal config generation."""
    row = dbnode.egress
    if row is None:
        return None
    return {
        "tag": "managed-residential-egress",
        "protocol": row.protocol,
        "udp_mode": row.udp_mode,
        "server": row.server,
        "port": row.port,
        "username": row.username,
        "password": _decrypt(db, row.encrypted_password),
    }


def public_egress(db, dbnode):
    """Return the saved connection details without exposing the password."""
    row = dbnode.egress
    if row is None:
        return {"configured": False}
    return {
        "configured": True,
        "protocol": row.protocol,
        "udp_mode": row.udp_mode,
        "server": row.server,
        "port": row.port,
        "username": row.username,
        "has_password": bool(row.encrypted_password),
    }


def save_egress(db, dbnode, profile):
    """Create or update the row whose primary key is the Node ID."""
    row = dbnode.egress
    candidate = dict(profile)
    preserve_password = bool(
        row is not None
        and candidate.get("username")
        and candidate.get("username") == row.username
        and not candidate.get("password")
        and row.encrypted_password
    )
    if preserve_password:
        candidate["password"] = _decrypt(db, row.encrypted_password)
    value = validate_egress(candidate)

    if row is None:
        row = NodeEgress(node=dbnode)
        db.add(row)
    row.protocol = value["protocol"]
    row.udp_mode = value["udp_mode"]
    row.server = value["server"]
    row.port = value["port"]
    row.username = value["username"]
    if not preserve_password:
        row.encrypted_password = _encrypt(db, value["password"])
    db.commit()
