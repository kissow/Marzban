import time
import traceback

from app import app, logger, scheduler, xray
from app.db import GetDB, crud
from app.models.node import NodeStatus
from config import JOB_CORE_HEALTH_CHECK_INTERVAL


def core_health_check():
    config = None

    # main core
    try:
        if not xray.core.started:
            if config is None:
                config = xray.config.include_db_users()
            xray.core.restart(config)
    except Exception:
        logger.exception("Unable to recover main Xray core")

    # nodes' core
    # Include failed transport construction too, not only existing objects.
    with GetDB() as db:
        node_ids = [row.id for row in crud.get_nodes(db=db, enabled=True)]
    for node_id in node_ids:
        try:
            action = xray.operations.check_node_health(node_id)
            if action:
                if config is None:
                    config = xray.config.include_db_users()
                operation = (xray.operations.restart_node if action == "restart"
                             else xray.operations.connect_node)
                operation(node_id, config, automatic=True)
        except Exception:
            logger.exception("Unable to check node %s", node_id)


@app.on_event("startup")
def start_core():
    logger.info("Generating Xray core config")

    start_time = time.time()
    config = xray.config.include_db_users()
    logger.info(f"Xray core config generated in {(time.time() - start_time):.2f} seconds")

    # main core
    logger.info("Starting main Xray core")
    try:
        xray.core.start(config)
    except Exception:
        traceback.print_exc()

    # nodes' core
    logger.info("Starting nodes Xray core")
    with GetDB() as db:
        dbnodes = crud.get_nodes(db=db, enabled=True)
        node_ids = [dbnode.id for dbnode in dbnodes]
        for dbnode in dbnodes:
            crud.update_node_status(db, dbnode, NodeStatus.connecting)

    for node_id in node_ids:
        xray.operations.connect_node(node_id, config)

    scheduler.add_job(core_health_check, 'interval',
                      seconds=JOB_CORE_HEALTH_CHECK_INTERVAL,
                      coalesce=True, max_instances=1)


@app.on_event("shutdown")
def app_shutdown():
    logger.info("Stopping main Xray core")
    xray.core.stop()

    logger.info("Stopping nodes Xray core")
    for node in list(xray.nodes.values()):
        try:
            node.disconnect()
        except Exception:
            pass
