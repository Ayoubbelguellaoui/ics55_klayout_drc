import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from ics55_klayout_drc.layers import (
    generate_layers_rb,
    generate_lm,
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
            self.assertTrue(paths["lm"].is_file())
            self.assertTrue(paths["layers_rb"].is_file())
            self.assertIn(
                "icsprout55", paths["lyt"].read_text(encoding="utf-8")
            )
            self.assertIn(
                "MET1.drawing", paths["lyp"].read_text(encoding="utf-8")
            )

    def test_layer_map_covers_every_drawing_layer(self):
        entries = parse_layermap(LAYERMAP)
        lm_lines = set(generate_lm(entries).splitlines())
        for entry in entries:
            if entry.purpose != "drawing":
                continue
            self.assertIn(
                f"{entry.gds_layer}/{entry.gds_datatype} : {entry.ruby_name}",
                lm_lines,
                entry.name,
            )

    def test_layer_map_names_match_layers_rb(self):
        entries = parse_layermap(LAYERMAP)
        lm = generate_lm(entries)
        rb = generate_layers_rb(entries)
        for entry in entries:
            if entry.purpose != "drawing":
                continue
            self.assertIn(f"{entry.ruby_name} = input(", rb, entry.name)
            self.assertIn(f": {entry.ruby_name}", lm, entry.name)

    def test_lyt_references_layer_map(self):
        cfg = load_pdk_config(CONFIG, pdk_root=PDK_ROOT)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tech = tmp_path / "klayout" / "tech"
            tech.mkdir(parents=True)
            (tmp_path / "klayout" / "drc").mkdir(parents=True)
            paths = write_tech_files(cfg, tech)
            lyt = paths["lyt"].read_text(encoding="utf-8")
            self.assertIn("<layer-map>icsprout55.lm</layer-map>", lyt)
            self.assertIn("<common>", lyt)

    @unittest.skipUnless(
        Path("/usr/bin/klayout").exists() or shutil.which("klayout"),
        "KLayout not installed",
    )
    def test_klayout_parses_the_generated_layer_map(self):
        """A real KLayout must accept the generated .lm (guards format drift)."""
        entries = parse_layermap(LAYERMAP)
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            lm_path = tmp_path / "icsprout55.lm"
            lm_path.write_text(generate_lm(entries), encoding="utf-8")
            script = tmp_path / "check.rb"
            script.write_text(
                "lm = RBA::LayerMap.from_string(File.read("
                f"{str(lm_path)!r}))\n"
                "abort 'empty layer map' if lm.to_string.empty?\n"
                "raise 'missing ACT' unless lm.to_string.include?('ACT')\n"
                "exit 0\n",
                encoding="utf-8",
            )
            exe = shutil.which("klayout") or "/usr/bin/klayout"
            proc = subprocess.run(
                [exe, "-b", "-r", str(script)], capture_output=True, text=True
            )
            self.assertEqual(
                proc.returncode, 0, proc.stdout + proc.stderr
            )


if __name__ == "__main__":
    unittest.main()
