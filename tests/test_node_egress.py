import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("node_egress", ROOT / "app/xray/node_egress.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class NodeEgressTests(unittest.TestCase):
    def setUp(self):
        self.config = {
            "outbounds": [{"protocol": "freedom", "tag": "direct"}],
            "routing": {"rules": [{"type": "field", "outboundTag": "direct"}]},
        }

    def profile(self, **overrides):
        data = {"protocol": "http", "server": "proxy.example.com", "port": 8080,
                "username": None, "password": None, "default": False}
        data.update(overrides)
        return data

    def test_none_profile_returns_original_config(self):
        self.assertIs(module.for_node(self.config, None), self.config)

    def test_http_profile_does_not_mutate_source(self):
        result = module.for_node(self.config, self.profile(username="alice", password="secret"))
        self.assertNotIn("marzban_node_extensions", self.config)
        self.assertEqual(len(self.config["outbounds"]), 1)
        self.assertEqual(result["marzban_node_extensions"]["outbounds"][0]["protocol"], "http")
        self.assertEqual(result["marzban_node_extensions"]["outbounds"][0]["password"], "secret")

    def test_socks_default(self):
        result = module.for_node(self.config, self.profile(protocol="socks", default=True))
        self.assertEqual(result["marzban_node_extensions"]["default_outbound_tag"], "managed-residential-egress")

    def test_one_node_cannot_receive_two_outbounds(self):
        with self.assertRaises(ValueError):
            module.for_node(self.config, [self.profile(), self.profile()])

    def test_bad_port_is_rejected(self):
        with self.assertRaises(ValueError):
            module.for_node(self.config, self.profile(port=0))

    def test_existing_extension_is_rejected(self):
        config = {"outbounds": [], "marzban_node_extensions": {"outbounds": []}}
        with self.assertRaises(ValueError):
            module.for_node(config, self.profile())

    def test_requires_a_paired_custom_node_capability(self):
        self.assertFalse(module.supports_egress(None))
        self.assertFalse(module.supports_egress({"source": "node-runtime"}))
        self.assertTrue(module.supports_egress({
            "source": "node-runtime", "capabilities": ["managed-outbounds-v1"]
        }))


if __name__ == "__main__":
    unittest.main()
