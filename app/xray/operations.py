from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, RLock
from time import monotonic
from typing import TYPE_CHECKING

from sqlalchemy.exc import SQLAlchemyError

from app import logger, xray
from app.db import GetDB, crud
from app.models.node import NodeStatus
from app.models.user import UserResponse, UserStatus
from app.utils.concurrency import threaded_function
from app.xray.node import XRayNode
from app.xray.device_policy import build_device_policy_snapshot
from app.xray.node_egress import for_node
from app.xray.node_egress_store import read_egress
from xray_api import XRay as XRayAPI
from xray_api.types.account import Account, XTLSFlows

if TYPE_CHECKING:
    from app.db import User as DBUser
    from app.db.models import Node as DBNode


@lru_cache(maxsize=None)
def get_tls():
    from app.db import GetDB, get_tls_certificate
    with GetDB() as db:
        tls = get_tls_certificate(db)
        return {
            "key": tls.key,
            "certificate": tls.certificate
        }


@threaded_function
def _add_user_to_inbound(api: XRayAPI, inbound_tag: str, account: Account):
    try:
        api.add_inbound_user(tag=inbound_tag, user=account, timeout=30)
    except (xray.exc.EmailExistsError, xray.exc.ConnectionError):
        pass


@threaded_function
def _remove_user_from_inbound(api: XRayAPI, inbound_tag: str, email: str):
    try:
        api.remove_inbound_user(tag=inbound_tag, email=email, timeout=30)
    except (xray.exc.EmailNotFoundError, xray.exc.ConnectionError):
        pass


@threaded_function
def _alter_inbound_user(api: XRayAPI, inbound_tag: str, account: Account):
    try:
        api.remove_inbound_user(tag=inbound_tag, email=account.email, timeout=30)
    except (xray.exc.EmailNotFoundError, xray.exc.ConnectionError):
        pass
    try:
        api.add_inbound_user(tag=inbound_tag, user=account, timeout=30)
    except (xray.exc.EmailExistsError, xray.exc.ConnectionError):
        pass


def add_user(dbuser: "DBUser"):
    user = UserResponse.model_validate(dbuser)
    email = f"{dbuser.id}.{dbuser.username}"
    action = getattr(getattr(dbuser, "device_limit_action", None), "value",
                     getattr(dbuser, "device_limit_action", None))

    # Reconcile shared compatibility and device-specific accounts together.
    if action == "reject_new":
        sync_user_device_accounts(dbuser)
        return
    targets = _device_account_targets()

    for proxy_type, inbound_tags in user.inbounds.items():
        for inbound_tag in inbound_tags:
            inbound = xray.config.inbounds_by_tag.get(inbound_tag, {})

            try:
                proxy_settings = user.proxies[proxy_type].dict(no_obj=True)
            except KeyError:
                pass
            account = proxy_type.account_model(email=email, **proxy_settings)

            # XTLS currently only supports transmission methods of TCP and mKCP
            if getattr(account, 'flow', None) and (
                inbound.get('network', 'tcp') not in ('tcp', 'kcp')
                or
                (
                    inbound.get('network', 'tcp') in ('tcp', 'kcp')
                    and
                    inbound.get('tls') not in ('tls', 'reality')
                )
                or
                inbound.get('header_type') == 'http'
            ):
                account.flow = XTLSFlows.NONE

            for api, _ in targets:
                _add_user_to_inbound(api, inbound_tag, account)

    sync_user_device_accounts(dbuser, targets=targets)


def remove_user(dbuser: "DBUser", device_emails=None):
    email = f"{dbuser.id}.{dbuser.username}"
    device_emails = device_emails or []
    targets = _device_account_targets()

    for inbound_tag in xray.config.inbounds_by_tag:
        for api, _ in targets:
            _remove_user_from_inbound(api, inbound_tag, email)
        for device_email in device_emails:
            for api, _ in targets:
                _remove_user_from_inbound(api, inbound_tag, f"{dbuser.id}.{dbuser.username}.{device_email}")


def update_user(dbuser: "DBUser"):
    user = UserResponse.model_validate(dbuser)
    email = f"{dbuser.id}.{dbuser.username}"
    action = getattr(getattr(dbuser, "device_limit_action", None), "value",
                     getattr(dbuser, "device_limit_action", None))

    targets = _device_account_targets()
    active_inbounds = []
    for proxy_type, inbound_tags in user.inbounds.items():
        for inbound_tag in inbound_tags:
            active_inbounds.append(inbound_tag)
            inbound = xray.config.inbounds_by_tag.get(inbound_tag, {})

            try:
                proxy_settings = user.proxies[proxy_type].dict(no_obj=True)
            except KeyError:
                pass
            if action == "reject_new":
                continue
            account = proxy_type.account_model(email=email, **proxy_settings)

            # XTLS currently only supports transmission methods of TCP and mKCP
            if getattr(account, 'flow', None) and (
                inbound.get('network', 'tcp') not in ('tcp', 'kcp')
                or
                (
                    inbound.get('network', 'tcp') in ('tcp', 'kcp')
                    and
                    inbound.get('tls') not in ('tls', 'reality')
                )
                or
                inbound.get('header_type') == 'http'
            ):
                account.flow = XTLSFlows.NONE

            for api, _ in targets:
                _alter_inbound_user(api, inbound_tag, account)

    for inbound_tag in xray.config.inbounds_by_tag:
        if inbound_tag in active_inbounds:
            continue
        # remove disabled inbounds
        for api, _ in targets:
            _remove_user_from_inbound(api, inbound_tag, email)

    sync_user_device_accounts(dbuser, targets=targets)


def _device_account_targets():
    """Probe each Node once, isolating unavailable peers from healthy cores."""
    targets = [(xray.api, "main")]
    for node_id, node in list(xray.nodes.items()):
        try:
            if node.connected and node.started:
                targets.append((node.api, "node"))
        except Exception as exc:
            logger.warning("Skipping node %s account reconciliation: %s", node_id, exc)
    return targets


def sync_user_device_accounts(dbuser: "DBUser", targets=None):
    """Sync shared compatibility accounts and registered HWID credentials."""
    user = UserResponse.model_validate(dbuser)
    base_email = f"{dbuser.id}.{dbuser.username}"
    action = getattr(getattr(dbuser, "device_limit_action", None), "value",
                     getattr(dbuser, "device_limit_action", None))
    devices = [device for device in getattr(dbuser, "devices", [])
               if device.revoked_at is None and device.credentials]
    if targets is None:
        targets = _device_account_targets()

    for proxy_type, inbound_tags in user.inbounds.items():
        base_settings = user.proxies.get(proxy_type)
        if base_settings is None:
            continue
        for inbound_tag in inbound_tags:
            inbound = xray.config.inbounds_by_tag.get(inbound_tag, {})
            for api, _ in targets:
                if action == "reject_new":
                    # Clients without X-HWID keep the original shared account
                    # on the main core and every connected Node.
                    settings = base_settings.dict(no_obj=True)
                    account = proxy_type.account_model(email=base_email, **settings)
                    if getattr(account, "flow", None) and (
                        inbound.get("network", "tcp") not in ("tcp", "raw", "kcp")
                        or inbound.get("tls") not in ("tls", "reality")
                        or inbound.get("header_type") == "http"
                    ):
                        account.flow = XTLSFlows.NONE
                    _alter_inbound_user(api, inbound_tag, account)
                    for device in devices:
                        fields = (device.credentials or {}).get(
                            getattr(proxy_type, "value", proxy_type), {})
                        if not fields:
                            continue
                        settings = base_settings.dict(no_obj=True)
                        settings.update(fields)
                        account = proxy_type.account_model(
                            email=f"{base_email}.device-{device.hwid_hash[:16]}",
                            **settings,
                        )
                        if getattr(account, "flow", None) and (
                            inbound.get("network", "tcp") not in ("tcp", "raw", "kcp")
                            or inbound.get("tls") not in ("tls", "reality")
                            or inbound.get("header_type") == "http"
                        ):
                            account.flow = XTLSFlows.NONE
                        _alter_inbound_user(api, inbound_tag, account)
                else:
                    # A user may be switched back from reject_new to the
                    # legacy shared-account mode. Remove all device-specific
                    # labels before restoring the shared account so stale
                    # credentials cannot remain usable on a Node.
                    for device in getattr(dbuser, "devices", []):
                        _remove_user_from_inbound(
                            api, inbound_tag,
                            f"{base_email}.device-{device.hwid_hash[:16]}"
                        )
                    settings = base_settings.dict(no_obj=True)
                    account = proxy_type.account_model(email=base_email, **settings)
                    _alter_inbound_user(api, inbound_tag, account)


def remove_node(node_id: int):
    with _node_lock(node_id):
        _remove_node(node_id)


def _remove_node(node_id: int):
    if node_id in xray.nodes:
        try:
            xray.nodes[node_id].disconnect()
        except Exception:
            pass
        finally:
            try:
                del xray.nodes[node_id]
            except KeyError:
                pass


def add_node(dbnode: "DBNode"):
    with _node_lock(dbnode.id):
        return _add_node(dbnode)


def _add_node(dbnode: "DBNode"):
    remove_node(dbnode.id)

    tls = get_tls()
    xray.nodes[dbnode.id] = XRayNode(address=dbnode.address,
                                     port=dbnode.port,
                                     api_port=dbnode.api_port,
                                     ssl_key=tls['key'],
                                     ssl_cert=tls['certificate'],
                                     usage_coefficient=dbnode.usage_coefficient)

    return xray.nodes[dbnode.id]


_policy_sync_lock = Lock()


def _read_device_policies():
    from app.db.models import User
    with GetDB() as db:
        rows = db.query(User.id, User.username, User.status, User.device_limit,
                        User.device_limit_mode, User.device_limit_action).filter(
                            User.status.in_([UserStatus.active, UserStatus.on_hold, UserStatus.limited])
                        ).all()
        return build_device_policy_snapshot(rows)


def _send_node_device_policies(node_id, policies):
    """Replace a connected Node's policy snapshot without breaking old Nodes."""
    node = xray.nodes.get(node_id)
    if node is None:
        return None
    try:
        if not node.connected or not node.started:
            return None
        setter = getattr(node, "set_device_policies", None)
        if setter is None:
            node.device_policy_sync = {"policy_sync_status": "unsupported"}
            return None
        result = setter(policies)
        if result is None:
            node.device_policy_sync = {"policy_sync_status": "unsupported"}
        elif (result.get("accepted") is not True or isinstance(result.get("policy_count"), bool)
              or result.get("policy_count") != len(policies)
              or result.get("policy_enforcement") != "subscription_request_and_node_credentials"
              or result.get("direct_connection_enforced") is not True):
            raise ValueError("Invalid device policy acknowledgement")
        else:
            node.device_policy_sync = {"policy_sync_status": "synced"}
        return result
    except NotImplementedError:
        node.device_policy_sync = {"policy_sync_status": "unsupported"}
        return None
    except Exception:
        node.device_policy_sync = {"policy_sync_status": "failed"}
        logger.warning("Unable to sync device policies to node %s", node_id, exc_info=True)
        return None


def sync_node_device_policies(node_id, policies=None):
    """Serialize snapshots so an older request cannot overwrite a newer one."""
    with _policy_sync_lock:
        try:
            return _send_node_device_policies(node_id, policies if policies is not None else _read_device_policies())
        except Exception:
            logger.warning("Unable to build node device policy snapshot", exc_info=True)
            return None


def sync_all_node_device_policies():
    """Synchronize the complete policy snapshot to every connected Node."""
    with _policy_sync_lock:
        node_ids = list(xray.nodes)
        if not node_ids:
            return
        try:
            policies = _read_device_policies()
            with ThreadPoolExecutor(max_workers=min(10, len(node_ids))) as executor:
                list(executor.map(lambda node_id: _send_node_device_policies(node_id, policies), node_ids))
        except Exception:
            logger.warning("Unable to build node device policy snapshot", exc_info=True)


_account_sync_lock = Lock()


def sync_all_node_device_accounts():
    """Retry per-device Xray account reconciliation after transient failures."""
    if not _account_sync_lock.acquire(blocking=False):
        return
    try:
        targets = _device_account_targets()
        with GetDB() as db:
            users = crud.get_users(db, status=[UserStatus.active, UserStatus.on_hold])
            for user in users:
                try:
                    sync_user_device_accounts(user, targets=targets)
                except Exception:
                    logger.warning("Unable to reconcile device accounts for user %s", user.id, exc_info=True)
    except Exception:
        logger.warning("Unable to reconcile device accounts", exc_info=True)
    finally:
        _account_sync_lock.release()


def _change_node_status(node_id: int, status: NodeStatus, message: str = None, version: str = None):
    with GetDB() as db:
        try:
            dbnode = crud.get_node_by_id(db, node_id)
            if not dbnode:
                return

            if dbnode.status == NodeStatus.disabled:
                remove_node(dbnode.id)
                return

            crud.update_node_status(db, dbnode, status, message, version)
        except SQLAlchemyError:
            db.rollback()


_connecting_nodes = {}
_node_locks = {}
_node_locks_guard = Lock()
_node_retry_after = {}
NODE_RETRY_DELAY = 30


def _node_lock(node_id):
    # Construct exactly one reentrant lifecycle lock for each node.
    with _node_locks_guard:
        if node_id not in _node_locks:
            _node_locks[node_id] = RLock()
        return _node_locks[node_id]


def node_lifecycle_lock(node_id):
    """Serialize admin configuration/deletion with in-flight node recovery."""
    return _node_lock(node_id)


def _node_failure(node_id, stage, exc):
    message = f"{stage}: {exc}"[:2000]
    _node_retry_after[node_id] = monotonic() + NODE_RETRY_DELAY
    _change_node_status(node_id, NodeStatus.error, message=message)
    logger.warning("Node %s failed: %s", node_id, message)


def _operate_node(node_id, config, restart, automatic):
    lock = _node_lock(node_id)
    # Explicit configuration restarts must not be lost. Reconnect clicks and
    # periodic recovery coalesce instead of queuing duplicate sessions.
    if not lock.acquire(blocking=restart and not automatic):
        return
    stage = "Read node configuration"
    reconcile_accounts = False
    try:
        if automatic and monotonic() < _node_retry_after.get(node_id, 0):
            return
        _connecting_nodes[node_id] = True
        with GetDB() as db:
            dbnode = crud.get_node_by_id(db, node_id)
            if not dbnode:
                return
            if dbnode.status == NodeStatus.disabled:
                remove_node(node_id)
                return
            egress = read_egress(db, dbnode)

        _change_node_status(node_id, NodeStatus.connecting)
        logger.info("%s node %s", "Restarting" if restart else "Connecting to", node_id)
        stage = "Create node transport"
        node = xray.nodes.get(node_id)
        if node is None:
            node = xray.operations.add_node(dbnode)

        # Reuse an expired transport instead of disconnecting (which stops the
        # remote core). Refresh its authenticated session only when necessary.
        stage = "Control session / TLS"
        if not node.connected:
            node.connect()

        stage = "Prepare node configuration / health"
        if config is None:
            config = xray.config.include_db_users()
        config = for_node(config, egress, node.get_health()
                          if egress and egress.get("udp_mode", "legacy") != "legacy" else None)

        stage = "Restart Xray / API readiness" if restart else "Start Xray / API readiness"
        if restart:
            node.restart(config)
        else:
            node.start(config)
        stage = "Read Xray version"
        version = node.get_version()
        # Connection readiness is independent of the best-effort, potentially
        # lengthy reconciliation of every user's existing device accounts.
        _change_node_status(node_id, NodeStatus.connected, version=version)
        _node_retry_after.pop(node_id, None)
        stage = "Synchronize device policies / accounts"
        sync_node_device_policies(node_id)
        reconcile_accounts = True
        logger.info("Connected to node %s, Xray version %s", node_id, version)
    except Exception as exc:
        # A failed readiness check must not stop a core serving other users.
        _node_failure(node_id, stage, exc)
    finally:
        _connecting_nodes.pop(node_id, None)
        lock.release()
    # Global account reconciliation is best effort and may cover many users.
    # Do not hold this node's lifecycle lock throughout that unrelated work.
    if reconcile_accounts:
        sync_all_node_device_accounts()


@threaded_function
def connect_node(node_id, config=None, automatic=False):
    _operate_node(node_id, config, restart=False, automatic=automatic)


@threaded_function
def restart_node(node_id, config=None, automatic=False):
    _operate_node(node_id, config, restart=True, automatic=automatic)


def check_node_health(node_id):
    """Check one idle node; return a recovery action without holding its lock."""
    lock = _node_lock(node_id)
    if not lock.acquire(blocking=False):
        return None
    try:
        if monotonic() < _node_retry_after.get(node_id, 0):
            return None
        node = xray.nodes.get(node_id)
        if node is None or not node.connected:
            return "connect"
        if not node.started:
            return "connect"
        node.api.get_sys_stats(timeout=5)
        # A late-ready API can recover without another restart. Clear only a
        # stale failure/connecting state; do not rewrite healthy rows each tick.
        with GetDB() as db:
            dbnode = crud.get_node_by_id(db, node_id)
            if dbnode and dbnode.status in (NodeStatus.error, NodeStatus.connecting):
                version = node.get_version() or dbnode.xray_version
                _change_node_status(node_id, NodeStatus.connected, version=version)
        _node_retry_after.pop(node_id, None)
    except Exception as exc:
        _change_node_status(node_id, NodeStatus.error, message=f"Health check: {exc}"[:2000])
        logger.warning("Node %s health check failed: %s", node_id, exc)
        # A control/API timeout is not evidence that Xray has stopped. Keep
        # serving users, back off, and re-probe; a confirmed stopped core or
        # invalid session takes the explicit connect path on the next check.
        _node_retry_after[node_id] = monotonic() + NODE_RETRY_DELAY
        return None
    finally:
        lock.release()


__all__ = [
    "add_user",
    "remove_user",
    "add_node",
    "remove_node",
    "connect_node",
    "restart_node",
    "check_node_health",
    "node_lifecycle_lock",
    "sync_node_device_policies",
    "sync_all_node_device_policies",
    "sync_all_node_device_accounts",
]
