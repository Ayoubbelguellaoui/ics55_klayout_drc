import re
import unittest
from pathlib import Path

from ics55_klayout_drc.pdk import PACKAGE_ROOT

DECK = PACKAGE_ROOT / "klayout" / "drc"
MODULES = (
    "00_options.rb",
    "01_layers.rb",
    "02_derived.rb",
    "10_geometry.rb",
    "20_front_end.rb",
    "30_back_end.rb",
    "40_density_slot.rb",
    "50_special.rb",
    "90_report.rb",
)


class DeckStructureTest(unittest.TestCase):
    def test_entry_deck_includes_every_module(self):
        text = (DECK / "ics55_full_mask.drc").read_text(encoding="utf-8")
        self.assertIn("eval(File.read(", text)
        for module in MODULES:
            self.assertTrue((DECK / module).is_file(), module)
        for module in (
            "01_layers.rb",
            "02_derived.rb",
            "10_geometry.rb",
            "20_front_end.rb",
            "30_back_end.rb",
            "40_density_slot.rb",
            "50_special.rb",
            "90_report.rb",
        ):
            self.assertIn(module, text)

    def test_generated_layers_are_bound(self):
        text = (DECK / "01_layers.rb").read_text(encoding="utf-8")
        self.assertIn("NODRC = input(357, 12)", text)
        self.assertIn("SRAMALL = input(171, 12)", text)
        self.assertIn("PSUB = input(261, 12)", text)
        self.assertNotIn("_mark = input(", text)

    def test_static_rule_ids_are_unique(self):
        rules = []
        for module in MODULES:
            if module in {"00_options.rb", "01_layers.rb", "02_derived.rb", "90_report.rb"}:
                continue
            text = (DECK / module).read_text(encoding="utf-8")
            rules.extend(re.findall(r'ics55_check\("([^"#]+)"', text))
        self.assertGreaterEqual(len(rules), 80)
        self.assertEqual(len(rules), len(set(rules)))

    def test_required_rule_families_are_present(self):
        text = "\n".join(
            (DECK / module).read_text(encoding="utf-8")
            for module in MODULES
        )
        for rule in (
            "ACT.W.1",
            "PO.W.1",
            "CT.W.1",
            "NP.EN.2",
            "T4M2.W.1",
            "METAL_LIMITS",
            '"#{name}.W.1"',
            '"#{name}.EN.1"',
            '"CHIPEDGE.#{name}"',
            'ics55_density("AA"',
            'ics55_density("PO"',
        ):
            self.assertIn(rule, text)
        self.assertIn("ics55_check", text)

    def test_marker_layers_are_not_redefined_in_rules(self):
        for module in ("30_back_end.rb", "50_special.rb"):
            text = (DECK / module).read_text(encoding="utf-8")
            self.assertNotIn("= input(", text, module)


if __name__ == "__main__":
    unittest.main()
