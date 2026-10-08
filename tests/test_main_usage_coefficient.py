"""Persisted local billing settings and real SQLite accounting regressions."""
import asyncio
import importlib.util
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_user_device_limit as bootstrap
from alembic.migration import MigrationContext
from alembic.operations import Operations
from fastapi import FastAPI
from pydantic import ValidationError
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app import scheduler
from app.db import GetDB
from app.db.base import Base
from app.db.models import Admin as DBAdmin, Node, NodeUserUsage, System, User
from app.models.admin import Admin
from app.models.main_usage import MainUsageSettings
from app.routers import node as routes

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("isolated_main_usage_jobs", ROOT / "app/jobs/record_usages.py")
jobs = importlib.util.module_from_spec(spec)
with patch.object(scheduler, "add_job"):
    spec.loader.exec_module(jobs)


class MainUsageTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
        Base.metadata.create_all(self.engine)
        self.sessions = sessionmaker(bind=self.engine)
        self.db = self.sessions()
        self.admin = DBAdmin(username="owner", hashed_password="test", users_usage=20)
        self.db.add(self.admin)
        self.db.flush()
        self.user = User(username="billable", admin_id=self.admin.id, used_traffic=50)
        self.system = System(uplink=30, downlink=40)
        self.node = Node(name="remote", address="node.example.test", port=62050, api_port=62051, usage_coefficient=3)
        self.db.add_all([self.user, self.system, self.node])
        self.db.commit()
        self.main_api, self.remote_api = Mock(), Mock()
        self.runtime = SimpleNamespace(api=self.main_api, nodes={self.node.id: SimpleNamespace(
            connected=True, started=True, api=self.remote_api, usage_coefficient=3)},
            relay=SimpleNamespace(api=Mock()))

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def request(self, method, body=None, authorized=True):
        app = FastAPI()
        app.include_router(routes.router)
        app.dependency_overrides[routes.get_db] = lambda: self.db
        if authorized:
            app.dependency_overrides[Admin.check_sudo_admin] = lambda: Admin(username="test", is_sudo=True)
        raw = json.dumps(body).encode() if body is not None else b""
        path = "/api/node/main/usage"
        messages = []
        scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method,
                 "scheme": "https", "path": path, "raw_path": path.encode(), "query_string": b"", "root_path": "",
                 "server": ("test.local", 443), "client": ("198.51.100.1", 1234),
                 "headers": [(b"content-type", b"application/json")] + ([(b"authorization", b"Bearer test")] if not authorized else [])}
        async def receive():
            return {"type": "http.request", "body": raw, "more_body": False}
        async def send(message):
            messages.append(message)
        asyncio.run(app(scope, receive, send))
        status = next(msg["status"] for msg in messages if msg["type"] == "http.response.start")
        payload = json.loads(b"".join(msg.get("body", b"") for msg in messages))
        return status, payload

    def test_api_default_save_persistence_without_rescaling_history(self):
        self.assertEqual(self.request("GET"), (200, {"usage_coefficient": 1.0}))
        self.assertEqual(self.request("PUT", {"usage_coefficient": 2.5}), (200, {"usage_coefficient": 2.5}))
        with self.sessions() as reopened:
            self.assertEqual(reopened.query(System).one().usage_coefficient, 2.5)
            self.assertEqual(reopened.query(User).one().used_traffic, 50)
            self.assertEqual(reopened.query(DBAdmin).one().users_usage, 20)
            self.assertEqual(reopened.query(Node).one().usage_coefficient, 3)
            self.assertEqual((reopened.query(System).one().uplink, reopened.query(System).one().downlink), (30, 40))
        self.assertEqual(self.request("GET")[1]["usage_coefficient"], 2.5)

    def test_schema_bounds_precision_and_nonfinite(self):
        for value in (0, -1, 1001, 0.000001, 1.123456, True, None, "NaN", "Infinity", float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(ValidationError):
                MainUsageSettings(usage_coefficient=value)
        for value in (0.00001, 0.1, 0.29, 1, 1.00000, 1000):
            self.assertEqual(MainUsageSettings(usage_coefficient=value).usage_coefficient, value)

    def test_api_rejects_invalid_and_missing_body_without_changing_value(self):
        for body in ({}, {"usage_coefficient": 0}, {"usage_coefficient": True}, {"usage_coefficient": "NaN"}, {"usage_coefficient": 1.123456}):
            self.assertEqual(self.request("PUT", body)[0], 422)
        self.assertEqual(self.request("GET")[1]["usage_coefficient"], 1)

    def test_api_requires_sudo_for_read_and_write(self):
        for admin, status in ((None, 401), (Admin(username="ordinary", is_sudo=False), 403)):
            with patch.object(Admin, "get_admin", return_value=admin):
                for method in ("GET", "PUT"):
                    self.assertEqual(self.request(method, {"usage_coefficient": 2} if method == "PUT" else None, False)[0], status)

    def test_missing_system_returns_503_not_an_implicit_default(self):
        self.db.delete(self.system)
        self.db.commit()
        for method in ("GET", "PUT"):
            self.assertEqual(self.request(method, {"usage_coefficient": 2} if method == "PUT" else None)[0], 503)

    def collect(self, main_value=100, remote_value=10, disabled=False):
        uid = str(self.user.id)
        def stats(api):
            return [{"uid": uid, "value": main_value if api is self.main_api else remote_value}]
        with patch("app.db.SessionLocal", self.sessions), patch.object(jobs, "xray", self.runtime), \
             patch.object(jobs, "get_users_stats", side_effect=stats) as probe, \
             patch.object(jobs, "DISABLE_RECORDING_NODE_USAGE", disabled):
            jobs.record_user_usages()
        self.db.expire_all()
        return probe

    def test_main_and_remote_ledgers_scale_independently_and_no_relay_probe(self):
        self.system.usage_coefficient = 2
        self.db.commit()
        probe = self.collect()
        self.assertEqual(self.user.used_traffic, 50 + 200 + 30)
        self.assertEqual(self.admin.users_usage, 20 + 200 + 30)
        entries = {row.node_id: row.used_traffic for row in self.db.query(NodeUserUsage).all()}
        self.assertEqual(entries, {None: 200, self.node.id: 30})
        self.assertEqual(probe.call_count, 2)
        self.assertEqual({call.args[0] for call in probe.call_args_list}, {self.main_api, self.remote_api})
        self.assertEqual(self.system.uplink, 30)

    def test_default_one_preserves_existing_charge(self):
        self.collect()
        self.assertEqual(self.user.used_traffic, 180)

    def test_decimal_rounding_is_identical_in_all_main_ledgers(self):
        self.system.usage_coefficient = 0.29
        self.db.commit()
        self.runtime.nodes = {}
        self.collect(main_value=100)
        self.assertEqual(self.user.used_traffic, 79)
        self.assertEqual(self.admin.users_usage, 49)
        self.assertEqual(self.db.query(NodeUserUsage).one().used_traffic, 29)
        self.assertEqual(jobs.charge_main_usage([{"uid": "1", "value": 3}], 0.5), [{"uid": "1", "value": 1}])

    def test_setting_change_affects_only_subsequent_collections(self):
        self.collect()
        self.request("PUT", {"usage_coefficient": 2})
        self.collect()
        self.assertEqual(self.user.used_traffic, 50 + 130 + 230)
        self.assertEqual(self.admin.users_usage, 20 + 130 + 230)
        self.assertEqual(self.db.query(NodeUserUsage).filter_by(node_id=None).one().used_traffic, 300)

    def test_disabled_hourly_recording_still_scales_user_and_admin(self):
        self.system.usage_coefficient = 2
        self.db.commit()
        self.collect(disabled=True)
        self.assertEqual(self.user.used_traffic, 280)
        self.assertEqual(self.db.query(NodeUserUsage).count(), 0)

    def test_db_read_failure_occurs_before_any_reset_probe(self):
        with patch.object(jobs, "get_main_usage_coefficient", side_effect=RuntimeError("DB unavailable")), \
             patch.object(jobs, "get_users_stats") as probe:
            with self.assertRaisesRegex(RuntimeError, "DB unavailable"):
                jobs.record_user_usages()
        probe.assert_not_called()

    def test_invalid_persisted_value_fails_before_reset(self):
        self.system.usage_coefficient = 0
        self.db.commit()
        with patch("app.db.SessionLocal", self.sessions), patch.object(jobs, "get_users_stats") as probe:
            with self.assertRaises(ValidationError):
                jobs.record_user_usages()
        probe.assert_not_called()

    def test_snapshot_is_taken_once_before_collection(self):
        with patch.object(jobs, "get_main_usage_coefficient", return_value=2) as setting:
            self.collect()
        setting.assert_called_once()
        self.assertEqual(self.user.used_traffic, 280)

    def test_save_during_probe_does_not_mix_coefficients_within_batch(self):
        self.runtime.nodes = {}
        def stats(api):
            self.assertEqual(self.request("PUT", {"usage_coefficient": 2})[0], 200)
            return [{"uid": str(self.user.id), "value": 100}]
        with patch("app.db.SessionLocal", self.sessions), patch.object(jobs, "xray", self.runtime), \
             patch.object(jobs, "get_users_stats", side_effect=stats):
            jobs.record_user_usages()
        self.db.expire_all()
        self.assertEqual(self.user.used_traffic, 150)
        self.assertEqual(self.system.usage_coefficient, 2)
        self.collect()
        self.assertEqual(self.user.used_traffic, 350)

    def test_hwid_credentials_aggregate_before_scaling(self):
        uid = str(self.user.id)
        self.main_api.get_users_stats.return_value = [
            SimpleNamespace(name=f"{uid}.device-one", value=7),
            SimpleNamespace(name=f"{uid}.device-two", value=3),
        ]
        params = jobs.get_users_stats(self.main_api)
        self.assertEqual(params, [{"uid": uid, "value": 10}])
        self.assertEqual(jobs.charge_main_usage(params, 0.5), [{"uid": uid, "value": 5}])
        self.main_api.get_users_stats.assert_called_once_with(reset=True, timeout=30)

    def test_sub_byte_rounding_and_large_integer_precision(self):
        self.assertEqual(jobs.charge_main_usage([{"uid": "1", "value": 1}], 0.00001)[0]["value"], 0)
        value = 9007199254740993
        self.assertEqual(jobs.charge_main_usage([{"uid": "1", "value": value}], 1)[0]["value"], value)

    def test_node_network_counters_are_raw_not_multiplied(self):
        self.system.usage_coefficient = 5
        self.db.commit()
        with patch("app.db.SessionLocal", self.sessions), patch.object(jobs, "xray", self.runtime), \
             patch.object(jobs, "get_outbounds_stats", return_value=[{"up": 100, "down": 200}]):
            jobs.record_node_usages()
        self.db.expire_all()
        self.assertEqual((self.system.uplink, self.system.downlink), (230, 440))


class MainUsageMigrationTests(unittest.TestCase):
    def test_additive_migration_default_downgrade_preserve_data(self):
        spec = importlib.util.spec_from_file_location("main_usage_migration", ROOT / "app/db/migrations/versions/a123bc45de67_main_usage_coefficient.py")
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        self.assertEqual(migration.down_revision, "9012ab34cd56")
        engine = create_engine("sqlite:///:memory:")
        with engine.begin() as conn:
            conn.execute(text("CREATE TABLE system (id INTEGER PRIMARY KEY, uplink BIGINT, downlink BIGINT)"))
            conn.execute(text("INSERT INTO system VALUES (1, 123, 456)"))
            conn.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT, used_traffic BIGINT)"))
            conn.execute(text("INSERT INTO users VALUES (1, 'keep', 789)"))
            with patch.object(migration, "op", Operations(MigrationContext.configure(conn))):
                migration.upgrade()
                self.assertEqual(conn.execute(text("SELECT * FROM system")).one(), (1, 123, 456, 1.0))
                conn.execute(text("INSERT INTO system (id, uplink, downlink) VALUES (2, 0, 0)"))
                self.assertEqual(conn.execute(text("SELECT usage_coefficient FROM system WHERE id=2")).scalar(), 1.0)
                migration.downgrade()
            self.assertEqual(conn.execute(text("SELECT * FROM system WHERE id=1")).one(), (1, 123, 456))
            self.assertEqual(conn.execute(text("SELECT * FROM users")).one(), (1, "keep", 789))
        engine.dispose()
