import tempfile
import unittest
from pathlib import Path

from ics55_klayout_drc.layers import (
    generate_layers_rb,
    parse_layermap,
    write_tech_files,
)
from ics55_klayout_drc.pdk import load_pdk_config

CONFIG = Path(__file__).resolve().parents[1] / "config" / "ics55.pdk.yml"
PDK_ROOT = Path(__file__).resolve().parents[2] / "icsprout55-pdk"
LAYERMAP = PDK_ROOT / "techfile" / "icsprout55.layermap"


class LayermapTest(unittest.TestCase):
    def test_parse_ics55_layermap(self):
        entries = parse_layermap(LAYERMAP)
        by_key = {(entry.name, entry.purpose): entry for entry in entries}
        self.assertEqual(by_key[("ACT", "drawing")].gds_layer, 2)
        self.assertEqual(by_key[("MET1", "drawing")].gds_layer, 81)
        self.assertEqual(by_key[("NODRC", "mark")].gds_layer, 357)
        self.assertEqual(by_key[("NODRC", "mark")].gds_datatype, 12)
        self.assertGreaterEqual(len(entries), 250)

    def test_ruby_names_are_unique(self):
        entries = parse_layermap(LAYERMAP)
        names = [entry.ruby_name for entry in entries]
        self.assertEqual(len(names), len(set(names)))
        rb = generate_layers_rb(entries)
        self.assertIn("ACT = input(2, 1)", rb)
        self.assertIn("MET1 = input(81, 1)", rb)
        self.assertIn("NODRC = input(357, 12)", rb)
        self.assertNotIn("NODRC_mark", rb)

    def test_write_tech_files(self):
        cfg = load_pdk_config(CONFIG, pdk_root=PDK_ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tech = tmp_path / "klayout" / "tech"
            tech.mkdir(parents=True)
            (tmp_path / "klayout" / "drc").mkdir(parents=True)
            paths = write_tech_files(cfg, tech)
            self.assertTrue(paths["lyp"].is_file())
            self.assertTrue(paths["lyt"].is_file())
            self.assertTrue(paths["layers_rb"].is_file())
            self.assertIn(
                "icsprout55", paths["lyt"].read_text(encoding="utf-8")
            )
            self.assertIn(
                "MET1.drawing", paths["lyp"].read_text(encoding="utf-8")
            )


if __name__ == "__main__":
    unittest.main()
