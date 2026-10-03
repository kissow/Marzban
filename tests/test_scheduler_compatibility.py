"""Regression coverage for the APScheduler 3.x API used by the application."""

import subprocess
import sys
import threading
import unittest
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler


class SchedulerCompatibilityTests(unittest.TestCase):
    def make_scheduler(self):
        scheduler = BackgroundScheduler(
            {"apscheduler.job_defaults.max_instances": 20}, timezone="UTC"
        )
        self.addCleanup(lambda: scheduler.shutdown(wait=True) if scheduler.running else None)
        return scheduler

    def test_import_has_no_pkg_resources_warning(self):
        result = subprocess.run(
            [sys.executable, "-B", "-W", "error::UserWarning", "-c",
             "import sys; from apscheduler.schedulers.background import BackgroundScheduler; "
             "assert 'pkg_resources' not in sys.modules"],
            capture_output=True, text=True, timeout=15,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_utc_defaults_and_interval_options_are_preserved(self):
        scheduler = self.make_scheduler()
        job = scheduler.add_job(lambda: None, "interval", seconds=60,
                                coalesce=True, max_instances=1)
        scheduler.start(paused=True)
        self.assertEqual(str(scheduler.timezone), "UTC")
        self.assertEqual(job.trigger.interval, timedelta(seconds=60))
        self.assertEqual(job.max_instances, 1)
        self.assertTrue(job.coalesce)
        default_job = scheduler.add_job(lambda: None, "interval", hours=1)
        self.assertEqual(default_job.max_instances, 20)

    def test_scheduled_job_decorator_is_compatible(self):
        scheduler = self.make_scheduler()

        @scheduler.scheduled_job("interval", seconds=2, coalesce=True, max_instances=1)
        def scheduled():
            return None

        scheduler.start(paused=True)
        job, = scheduler.get_jobs()
        self.assertIs(job.func, scheduled)
        self.assertEqual(job.trigger.interval, timedelta(seconds=2))
        self.assertTrue(job.coalesce)
        self.assertEqual(job.max_instances, 1)

    def test_naive_utc_start_date_keeps_existing_job_semantics(self):
        scheduler = self.make_scheduler()
        start = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=1)
        job = scheduler.add_job(lambda: None, "interval", hours=2, start_date=start)
        scheduler.start(paused=True)
        self.assertEqual(job.trigger.start_date.replace(tzinfo=None), start)
        self.assertEqual(job.trigger.start_date.utcoffset(), timedelta(0))

    def test_interval_job_actually_executes_and_shutdown_stops_thread(self):
        scheduler = self.make_scheduler()
        executed = threading.Event()
        scheduler.add_job(executed.set, "interval", seconds=0.05,
                          coalesce=True, max_instances=1)
        scheduler.start()
        self.assertTrue(executed.wait(5), "Background interval job did not execute")
        scheduler.shutdown(wait=True)
        self.assertFalse(scheduler.running)

    def test_existing_job_controls_remain_available(self):
        scheduler = self.make_scheduler()
        job = scheduler.add_job(lambda: None, "interval", seconds=60, id="compat")
        scheduler.start(paused=True)
        scheduler.pause_job(job.id)
        self.assertIsNone(job.next_run_time)
        scheduler.resume_job(job.id)
        self.assertIsNotNone(job.next_run_time)
        scheduler.remove_job(job.id)
        self.assertIsNone(scheduler.get_job(job.id))
