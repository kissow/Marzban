import asyncio
import time
from typing import List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, WebSocket
from sqlalchemy.exc import IntegrityError
from starlette.websockets import WebSocketDisconnect

from app import logger, xray
from app.db import Session, crud, get_db
from app.dependencies import get_dbnode, validate_dates
from app.models.admin import Admin
from app.models.node import (
    NodeCreate,
    NodeModify,
    NodeResponse,
    NodeSettings,
    NodeStatus,
    NodesUsageResponse,
    NodeEgressModify,
    NodeEgressResponse,
)
from app.models.proxy import ProxyHost
from app.utils import responses
from app.xray.node_health import normalize_node_health
from app.xray.node_egress import supports_egress
from app.xray.node_egress_store import public_egress, save_egress

router = APIRouter(
    tags=["Node"], prefix="/api", responses={401: responses._401, 403: responses._403}
)


def require_managed_egress(dbnode):
    """Ensure the connected Node understands managed outbound profiles."""
    node = xray.nodes.get(dbnode.id)
    try:
        health = node.get_health() if node is not None else None
    except Exception:
        health = None
    if not supports_egress(health):
        raise HTTPException(
            status_code=409,
            detail="Upgrade and connect the paired Marzban-Node before setting egress",
        )


def add_host_if_needed(new_node: NodeCreate, db: Session):
    """Add a host if specified in the new node settings."""
    if new_node.add_as_new_host:
        host = ProxyHost(
            remark=f"{new_node.name} ({{USERNAME}}) [{{PROTOCOL}} - {{TRANSPORT}}]",
            address=new_node.address,
        )
        for inbound_tag in xray.config.inbounds_by_tag:
            crud.add_host(db, inbound_tag, host)
        xray.hosts.update()


@router.get("/node/settings", response_model=NodeSettings)
def get_node_settings(
    db: Session = Depends(get_db), admin: Admin = Depends(Admin.check_sudo_admin)
):
    """Retrieve the current node settings, including TLS certificate."""
    tls = crud.get_tls_certificate(db)
    return NodeSettings(certificate=tls.certificate)


@router.post("/node", response_model=NodeResponse, responses={409: responses._409})
def add_node(
    new_node: NodeCreate,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    """Add a new node to the database and optionally add it as a host."""
    try:
        dbnode = crud.create_node(db, new_node)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail=f'Node "{new_node.name}" already exists'
        )

    bg.add_task(xray.operations.connect_node, node_id=dbnode.id)
    bg.add_task(add_host_if_needed, new_node, db)

    logger.info(f'New node "{dbnode.name}" added')
    return dbnode


@router.get("/node/{node_id}", response_model=NodeResponse)
def get_node(
    dbnode: NodeResponse = Depends(get_dbnode),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    """Retrieve details of a specific node by its ID."""
    return dbnode


@router.get("/node/{node_id}/health")
def get_node_health(
    dbnode: NodeResponse = Depends(get_node),
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    """Read fresh Node metrics over the existing authenticated channel."""
    unknown = {"node_id": dbnode.id, "status": "unknown", "metrics": None}
    if dbnode.status == NodeStatus.disabled:
        return {**unknown, "reason": "disabled"}
    node = xray.nodes.get(dbnode.id)
    if node is None:
        return {**unknown, "reason": "offline"}
    try:
        if not node.connected:
            return {**unknown, "reason": "offline"}
        metrics = normalize_node_health(node.get_health())
    except (AttributeError, NotImplementedError):
        return {**unknown, "reason": "unsupported"}
    except Exception:
        logger.warning("Node %s health request failed", dbnode.id, exc_info=True)
        return {**unknown, "reason": "unavailable"}
    if metrics is None:
        return {**unknown, "reason": "invalid_or_stale"}
    sync = getattr(node, "device_policy_sync", {})
    metrics["policy_sync_status"] = sync.get("policy_sync_status", "pending")
    # Prefer the Node's own Xray counter-delta sample. Older Nodes do not
    # expose that optional contract, so keep the existing panel sample as a
    # clearly labelled compatibility fallback instead of overwriting a valid
    # Node-originated value.
    if metrics.get("activity_source") is None:
        fallback = crud.get_node_active_users(db, dbnode.id)
        metrics.update({
            "active_users": fallback.get("active_users"),
            "active_users_window_hours": fallback.get("active_users_window_hours"),
            "active_users_sampled_at": fallback.get("active_users_sampled_at"),
            "active_users_reason": fallback.get("active_users_reason"),
            "activity_source": "panel-node-usage",
            "activity_scope": "recent_traffic",
            "activity_reason": fallback.get("active_users_reason"),
        })
    return {"node_id": dbnode.id, "status": "online", "reason": None, "metrics": metrics}


@router.get("/node/{node_id}/egress", response_model=NodeEgressResponse)
def get_node_egress(
    dbnode = Depends(get_dbnode),
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    return public_egress(db, dbnode)


@router.put("/node/{node_id}/egress", response_model=NodeEgressResponse)
def update_node_egress(
    settings: NodeEgressModify,
    bg: BackgroundTasks,
    dbnode = Depends(get_dbnode),
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    require_managed_egress(dbnode)
    try:
        save_egress(db, dbnode, settings.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    bg.add_task(xray.operations.restart_node, node_id=dbnode.id)
    return public_egress(db, dbnode)


@router.delete("/node/{node_id}/egress")
def remove_node_egress(
    bg: BackgroundTasks,
    dbnode = Depends(get_dbnode),
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    if dbnode.egress is not None:
        db.delete(dbnode.egress)
        db.commit()
        bg.add_task(xray.operations.restart_node, node_id=dbnode.id)
    return {"configured": False}


@router.websocket("/node/{node_id}/logs")
async def node_logs(node_id: int, websocket: WebSocket, db: Session = Depends(get_db)):
    token = websocket.query_params.get("token") or websocket.headers.get(
        "Authorization", ""
    ).removeprefix("Bearer ")
    admin = Admin.get_admin(token, db)
    if not admin:
        return await websocket.close(reason="Unauthorized", code=4401)

    if not admin.is_sudo:
        return await websocket.close(reason="You're not allowed", code=4403)

    if not xray.nodes.get(node_id):
        return await websocket.close(reason="Node not found", code=4404)

    if not xray.nodes[node_id].connected:
        return await websocket.close(reason="Node is not connected", code=4400)

    interval = websocket.query_params.get("interval")
    if interval:
        try:
            interval = float(interval)
        except ValueError:
            return await websocket.close(reason="Invalid interval value", code=4400)
        if interval > 10:
            return await websocket.close(
                reason="Interval must be more than 0 and at most 10 seconds", code=4400
            )

    await websocket.accept()

    cache = ""
    last_sent_ts = 0
    node = xray.nodes[node_id]
    with node.get_logs() as logs:
        while True:
            if not node == xray.nodes[node_id]:
                break

            if interval and time.time() - last_sent_ts >= interval and cache:
                try:
                    await websocket.send_text(cache)
                except (WebSocketDisconnect, RuntimeError):
                    break
                cache = ""
                last_sent_ts = time.time()

            if not logs:
                try:
                    await asyncio.wait_for(websocket.receive(), timeout=0.2)
                    continue
                except asyncio.TimeoutError:
                    continue
                except (WebSocketDisconnect, RuntimeError):
                    break

            log = logs.popleft()

            if interval:
                cache += f"{log}\n"
                continue

            try:
                await websocket.send_text(log)
            except (WebSocketDisconnect, RuntimeError):
                break


@router.get("/nodes", response_model=List[NodeResponse])
def get_nodes(
    db: Session = Depends(get_db), _: Admin = Depends(Admin.check_sudo_admin)
):
    """Retrieve a list of all nodes. Accessible only to sudo admins."""
    return crud.get_nodes(db)


@router.put("/node/{node_id}", response_model=NodeResponse)
def modify_node(
    modified_node: NodeModify,
    bg: BackgroundTasks,
    dbnode: NodeResponse = Depends(get_node),
    db: Session = Depends(get_db),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    """Update a node's details. Only accessible to sudo admins."""
    updated_node = crud.update_node(db, dbnode, modified_node)
    xray.operations.remove_node(updated_node.id)
    if updated_node.status != NodeStatus.disabled:
        bg.add_task(xray.operations.connect_node, node_id=updated_node.id)

    logger.info(f'Node "{dbnode.name}" modified')
    return dbnode


@router.post("/node/{node_id}/reconnect")
def reconnect_node(
    bg: BackgroundTasks,
    dbnode: NodeResponse = Depends(get_node),
    _: Admin = Depends(Admin.check_sudo_admin),
):
    """Trigger a reconnection for the specified node. Only accessible to sudo admins."""
    bg.add_task(xray.operations.connect_node, node_id=dbnode.id)
    return {"detail": "Reconnection task scheduled"}


@router.delete("/node/{node_id}")
def remove_node(
    dbnode: NodeResponse = Depends(get_node),
    db: Session = Depends(get_db),
    admin: Admin = Depends(Admin.check_sudo_admin),
):
    """Delete a node and remove it from xray in the background."""
    crud.remove_node(db, dbnode)
    xray.operations.remove_node(dbnode.id)

    logger.info(f'Node "{dbnode.name}" deleted')
    return {}


@router.get("/nodes/usage", response_model=NodesUsageResponse)
def get_usage(
    db: Session = Depends(get_db),
    start: str = "",
    end: str = "",
    _: Admin = Depends(Admin.check_sudo_admin),
):
    """Retrieve usage statistics for nodes within a specified date range."""
    start, end = validate_dates(start, end)

    usages = crud.get_nodes_usage(db, start, end)

    return {"usages": usages}
