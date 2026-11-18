import tempfile
import unittest
from pathlib import Path

from ics55_klayout_drc.pdk import load_pdk_config

CONFIG = Path(__file__).resolve().parents[1] / "config" / "ics55.pdk.yml"
PDK_ROOT = Path(__file__).resolve().parents[2] / "icsprout55-pdk"


class PdkConfigTest(unittest.TestCase):
    def test_default_stack_is_1p6m_t4m2(self):
        cfg = load_pdk_config(CONFIG, pdk_root=PDK_ROOT)
        self.assertEqual(cfg.stack["total_metal"], 6)
        self.assertEqual(cfg.stack["top_metal"], 1)
        self.assertEqual(cfg.stack["T4V2_T4M2"], 1)
        self.assertEqual(cfg.io, 1833)
        cfg.validate_stack()

    def test_invalid_stack_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            bad = tmp_path / "bad.yml"
            bad.write_text(
                "pdk_root: .\n"
                "stack:\n"
                "  total_metal: 3\n"
                "  top_metal: 1\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "invalid ICS55 metal"):
                load_pdk_config(bad, pdk_root=tmp_path)


if __name__ == "__main__":
    unittest.main()
