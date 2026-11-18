"""Phase 5 tests: golden reference ingestion from the foundry Calibre deck."""

import unittest
from pathlib import Path

from ics55_klayout_drc.calibre_golden import (
    GoldenRules,
    compare_with_golden,
    golden_id,
    load_golden,
    load_known_deltas,
    normalize_rule_id,
    parse_deck,
    parse_layer_aliases,
    parse_run_output,
)
from ics55_klayout_drc.compare import RuleResult, load_summary_rules
from ics55_klayout_drc.pdk import DEFAULT_CONFIG, PACKAGE_ROOT, load_pdk_config

DECK = PACKAGE_ROOT.parent.parent / "icsprout55-pdk" / "pv" / "DRC" / (
    "ICsprout_CalDRC_55LLULP1233_REV1_0_OS.drc"
)

SAMPLE_OUT = """
ICS55 Calibre DRC Summary
RULECHECK ACT_W_1 {
AA width >= 0.08um
} Total Count: 2
MET1_W_1: 1
PO_W_1 3 violations
RULECHECK MET1_A_1 { MET1 area } Total Count: 4
"""

SAMPLE_SUMMARY = {
    "rules": [
        {"rule": "ACT.W.1", "count": 2, "layer": "ACT"},
        {"rule": "MET1.W.1", "count": 1, "layer": "MET1"},
    ]
}


class DeckParsingTest(unittest.TestCase):
    def setUp(self):
        if not DECK.is_file():
            raise unittest.SkipTest(f"Calibre deck not found: {DECK}")

    def test_deck_yields_rule_ids(self):
        rules = parse_deck(DECK)
        self.assertGreater(len(rules), 100)
        self.assertIn("ACT_W_1", rules)
        self.assertIn("MET1_W_1", rules)
        self.assertTrue(rules["ACT_W_1"].description)

    def test_commented_checks_are_skipped(self):
        rules = parse_deck(DECK)
        self.assertNotIn("DNW_R_2", rules)  # '#RULECHECK DNW_R_2' in the deck


class RunOutputTest(unittest.TestCase):
    def test_counts_are_collected(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "drc_CAL.OUT"
            out.write_text(SAMPLE_OUT, encoding="utf-8")
            rules = parse_run_output(out)
        self.assertEqual(rules["ACT_W_1"].count, 2)
        self.assertEqual(rules["MET1_W_1"].count, 1)
        self.assertEqual(rules["PO_W_1"].count, 3)
        self.assertEqual(rules["MET1_A_1"].count, 4)


class NormalizationTest(unittest.TestCase):
    def test_underscore_to_dot(self):
        self.assertEqual(normalize_rule_id("ACT_W_1"), "ACT.W.1")
        self.assertEqual(normalize_rule_id("M2_W_1"), "MET2.W.1")
        self.assertEqual(normalize_rule_id("V1_W_1"), "VIA1.W.1")
        self.assertEqual(normalize_rule_id("T4M2_W_1"), "T4M2.W.1")
        self.assertEqual(golden_id("MET1.W.1"), "MET1_W_1")

    def test_compare_matches_across_spellings(self):
        golden = GoldenRules(
            {"ACT_W_1": RuleResult(count=2), "MET1_W_1": RuleResult(count=1)},
            source="calibre-run:test",
        )
        klayout = load_summary_rules_path()
        comparison = compare_with_golden(klayout, golden)
        self.assertFalse(comparison.has_rule_deltas)
        self.assertEqual(comparison.matched, 2)


class KnownDeltasTest(unittest.TestCase):
    def test_load_expected_file(self):
        path = Path(__file__).parent / "expected" / "known_deltas.yml"
        rules, counts = load_known_deltas(path)
        self.assertGreater(len(rules), 0)
        self.assertTrue(all(isinstance(r, str) for r in rules))
        self.assertEqual(counts, set())

    def test_deltas_suppress_reported_differences(self):
        golden = GoldenRules(
            {"ACT_W_1": RuleResult(count=5)}, source="calibre-run:test"
        )
        klayout = {"ACT.W.1": RuleResult(count=9)}
        comparison = compare_with_golden(
            klayout, golden, known_count_deltas={"ACT.W.1"}
        )
        self.assertFalse(comparison.has_deltas)

    def test_prefix_wildcards_expand_to_family(self):
        golden = GoldenRules(
            {
                "ACT_W_1": RuleResult(),
                "ACT_W_2": RuleResult(),
                "ACT_S_1": RuleResult(),
            },
            source="calibre-run:test",
        )
        comparison = compare_with_golden({"ACT.W.1": RuleResult()}, golden)
        self.assertTrue(comparison.has_rule_deltas)
        waived = compare_with_golden(
            {"ACT.W.1": RuleResult()}, golden, known_rule_deltas={"ACT*"}
        )
        self.assertFalse(waived.has_rule_deltas)


def load_summary_rules_path():
    import json
    import tempfile

    tmp = tempfile.NamedTemporaryFile(
        "w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(SAMPLE_SUMMARY, tmp)
    tmp.close()
    return load_summary_rules(tmp.name)


class LayerAliasTest(unittest.TestCase):
    """The cross-reference needs a clean Calibre name per GDS layer."""

    @classmethod
    def setUpClass(cls):
        if not Path(DECK).is_file():
            raise unittest.SkipTest(f"Calibre deck not found: {DECK}")
        cls.aliases = parse_layer_aliases(DECK)

    def _display(self, gds_layer, gds_datatype):
        layer = self.aliases.get((gds_layer, gds_datatype))
        self.assertIsNotNone(layer, (gds_layer, gds_datatype))
        return layer.display

    def test_working_layer_aliases(self):
        self.assertIn("AA", self._display(2, 1))
        self.assertIn("PO", self._display(41, 1))
        self.assertIn("M1", self._display(81, 1))

    def test_input_bindings_are_surfaced(self):
        self.assertTrue(self._display(2, 1).startswith("ACTi"))
        self.assertTrue(self._display(41, 1).startswith("POLYi"))
        self.assertTrue(self._display(81, 1).startswith("MET1o"))

    def test_copy_alias_is_preferred_over_variants(self):
        # ACTi has AA, AA_CP, AA_all, ...; the plain COPY rename wins.
        self.assertEqual(self._display(2, 1), "ACTi / AA")
        self.assertEqual(self._display(41, 1), "POLYi / PO")

    def test_not_operands_do_not_leak_the_alias(self):
        # M1 = MET1o NOT MET1sloti: M1 belongs to 81/1 only, not the slot layer.
        self.assertIn("M1", self.aliases[(81, 1)].aliases)
        self.assertNotIn("M1", self.aliases[(81, 8)].aliases)
        self.assertIn("M1slot", self.aliases[(81, 8)].aliases)
        self.assertEqual(self._display(81, 8), "MET1sloti / M1slot")

    def test_derived_boolean_layers(self):
        self.assertIn("SDN", self._display(52, 1))
        self.assertIn("SDP", self._display(53, 1))
        self.assertIn("CT", self._display(72, 1))
        self.assertIn("CT", self._display(72, 7))

    def test_purpose_layers_keep_their_own_name(self):
        self.assertEqual(self._display(41, 6), "POLYtext")


if __name__ == "__main__":
    unittest.main()
