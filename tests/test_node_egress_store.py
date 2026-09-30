import importlib.util
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
egress_spec = importlib.util.spec_from_file_location("test_egress_validation", ROOT / "app/xray/node_egress.py")
egress_validation = importlib.util.module_from_spec(egress_spec)
egress_spec.loader.exec_module(egress_validation)


class FakeNodeEgress:
    def __init__(self, node):
        self.node = node
        node.egress = self


crud = types.ModuleType("app.db.crud")
crud.get_jwt_secret_key = lambda db: db.secret
models = types.ModuleType("app.db.models")
models.NodeEgress = FakeNodeEgress
db_module = types.ModuleType("app.db")
db_module.crud = crud
xray_module = types.ModuleType("app.xray")
stubs = {
    "app": types.ModuleType("app"), "app.db": db_module,
    "app.db.crud": crud, "app.db.models": models,
    "app.xray": xray_module, "app.xray.node_egress": egress_validation,
}
previous = {name: sys.modules.get(name) for name in stubs}
sys.modules.update(stubs)
try:
    store_spec = importlib.util.spec_from_file_location("test_egress_store", ROOT / "app/xray/node_egress_store.py")
    store = importlib.util.module_from_spec(store_spec)
    store_spec.loader.exec_module(store)
finally:
    for name, old in previous.items():
        if old is None:
            sys.modules.pop(name, None)
        else:
            sys.modules[name] = old


class FakeDB:
    secret = "persistent-test-jwt-secret"

    def add(self, row):
        self.row = row

    def commit(self):
        pass


class NodeEgressStoreTests(unittest.TestCase):
    def test_password_is_encrypted_and_not_returned_to_admin(self):
        db = FakeDB()
        node = types.SimpleNamespace(egress=None)
        store.save_egress(db, node, {
            "protocol": "socks", "server": "proxy.example.net", "port": 1080,
            "username": "alice", "password": "secret-password", "default": True,
        })
        self.assertNotIn("secret-password", node.egress.encrypted_password)
        self.assertTrue(store.public_egress(db, node)["has_password"])
        self.assertNotIn("password", store.public_egress(db, node))
        self.assertEqual(store.read_egress(db, node)["password"], "secret-password")

    def test_missing_persistent_secret_is_rejected(self):
        db = FakeDB()
        db.secret = None
        with self.assertRaisesRegex(RuntimeError, "JWT secret is not initialized"):
            store._cipher(db)

    def test_updating_a_node_keeps_one_row_and_existing_password(self):
        db = FakeDB()
        node = types.SimpleNamespace(egress=None)
        store.save_egress(db, node, {
            "protocol": "socks",
            "server": "proxy.example.net", "port": 1080, "username": "alice",
            "password": "secret-password",
        })
        row = node.egress
        encrypted = row.encrypted_password
        store.save_egress(db, node, {
            "protocol": "http", "server": "new.example.net", "port": 8080,
            "username": "alice", "password": None,
        })
        self.assertIs(node.egress, row)
        self.assertEqual(row.encrypted_password, encrypted)
        self.assertEqual(store.read_egress(db, node)["server"], "new.example.net")
        self.assertTrue(store.public_egress(db, node)["has_password"])

    def test_two_nodes_keep_independent_proxy_settings(self):
        db = FakeDB()
        first = types.SimpleNamespace(egress=None)
        second = types.SimpleNamespace(egress=None)
        store.save_egress(db, first, {
            "protocol": "http", "server": "us.example.net", "port": 8080,
            "username": None, "password": None,
        })
        store.save_egress(db, second, {
            "protocol": "socks", "server": "jp.example.net", "port": 1080,
            "username": None, "password": None,
        })
        self.assertEqual(store.read_egress(db, first)["server"], "us.example.net")
        self.assertEqual(store.read_egress(db, second)["server"], "jp.example.net")


if __name__ == "__main__":
    unittest.main()
