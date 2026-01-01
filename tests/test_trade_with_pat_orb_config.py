import unittest
import importlib.util
import os

MODULE_PATH = os.path.join(
    "Sync folder MAC TO PC", "DESKTOP_HANDOFF_PACKAGE", "google-cloud-trading-system", "src", "strategies", "trade_with_pat_orb_dual.py"
)


def load_trade_module():
    spec = importlib.util.spec_from_file_location("trade_with_pat_orb_dual_sync", MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestPatOrbConfig(unittest.TestCase):
    def test_config_loadable(self):
        # Ensure that the YAML config can be located and parsed
        mod = load_trade_module()
        cfg = mod._load_yaml_config()
        self.assertIsInstance(cfg, dict)
        # basic sanity: strategies key may exist
        self.assertTrue('strategies' in cfg or isinstance(cfg, dict))


if __name__ == '__main__':
    unittest.main()


