"""Independent relay recovery; never restart the main or Node Xray cores."""
from app import app, scheduler
from app.xray.node_relay_service import refresh, stop


@app.on_event("startup")
def start_node_relays():
    refresh()
    scheduler.add_job(refresh, "interval", seconds=15, coalesce=True, max_instances=1)


@app.on_event("shutdown")
def stop_node_relays():
    stop()
