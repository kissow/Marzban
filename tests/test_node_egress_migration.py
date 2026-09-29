"""The new outbound table must not replace or rewrite existing Node/user rows."""

import importlib.util
import unittest
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION = Path(__file__).resolve().parents[1] / "app/db/migrations/versions/3d1184b99029_add_node_egress.py"


class NodeEgressMigrationTests(unittest.TestCase):
    def test_upgrade_and_downgrade_preserve_existing_data(self):
        engine = sa.create_engine("sqlite:///:memory:")
        with engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE nodes (id INTEGER PRIMARY KEY, name TEXT NOT NULL)")
            connection.exec_driver_sql("CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL)")
            connection.exec_driver_sql("INSERT INTO nodes VALUES (7, 'existing-node')")
            connection.exec_driver_sql("INSERT INTO users VALUES (19, 'paid-user')")

            spec = importlib.util.spec_from_file_location("egress_migration", MIGRATION)
            migration = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(migration)
            migration.op = Operations(MigrationContext.configure(connection))

            migration.upgrade()
            tables = set(sa.inspect(connection).get_table_names())
            self.assertIn("node_egress", tables)
            self.assertNotIn("node_egress_profiles", tables)
            connection.exec_driver_sql(
                "INSERT INTO node_egress (node_id, protocol, server, port) "
                "VALUES (7, 'socks', 'proxy.example.net', 1080)"
            )
            with self.assertRaises(sa.exc.IntegrityError):
                connection.exec_driver_sql(
                    "INSERT INTO node_egress (node_id, protocol, server, port) "
                    "VALUES (7, 'http', 'another.example.net', 8080)"
                )
            self.assertEqual(connection.exec_driver_sql("SELECT name FROM nodes WHERE id=7").scalar(), "existing-node")
            self.assertEqual(connection.exec_driver_sql("SELECT username FROM users WHERE id=19").scalar(), "paid-user")

            migration.downgrade()
            self.assertNotIn("node_egress", set(sa.inspect(connection).get_table_names()))
            self.assertEqual(connection.exec_driver_sql("SELECT username FROM users WHERE id=19").scalar(), "paid-user")


if __name__ == "__main__":
    unittest.main()
