"""Refresh metadata after scheduled user changes or transient sync failures."""

from app import scheduler, xray


scheduler.add_job(xray.operations.sync_all_node_device_policies, 'interval',
                  seconds=60, coalesce=True, max_instances=1)
scheduler.add_job(xray.operations.sync_all_node_device_accounts, 'interval',
                  seconds=60, coalesce=True, max_instances=1)
