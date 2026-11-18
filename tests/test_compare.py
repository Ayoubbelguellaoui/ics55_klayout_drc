import json
import tempfile
import unittest
from pathlib import Path

from ics55_klayout_drc.compare import (
    CompareError,
    RuleResult,
    compare_summaries,
    load_summary_rules,
)


class CompareTest(unittest.TestCase):
    def test_rule_id_deltas_and_count_deltas(self):
        klayout = {
            "A": RuleResult(count=2, layer="ACT"),
            "B": RuleResult(count=1, layer="MET1"),
        }
        golden = {
            "A": RuleResult(count=1, layer="ACT"),
            "C": RuleResult(count=4, layer="POLY"),
        }
        result = compare_summaries(klayout, golden)
        self.assertEqual(result.matched, 1)
        self.assertEqual(result.only_klayout, ["B"])
        self.assertEqual(result.only_golden, ["C"])
        self.assertEqual(result.count_deltas, {"A": (2, 1)})
        self.assertTrue(result.has_rule_deltas)
        self.assertTrue(result.has_deltas)

    def test_known_deltas_are_suppressed(self):
        result = compare_summaries(
            {"A": RuleResult(count=1), "B": RuleResult(count=0)},
            {"A": RuleResult(count=1)},
            known_rule_deltas={"B"},
            known_count_deltas={"A"},
        )
        self.assertEqual(result.only_klayout, [])
        self.assertEqual(result.only_golden, [])
        self.assertEqual(result.count_deltas, {})
        self.assertFalse(result.has_deltas)

    def test_load_list_and_mapping_summaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            list_summary = tmp_path / "list.json"
            list_summary.write_text(
                json.dumps(
                    {
                        "rules": [
                            {"rule": "A", "count": 3, "layer": "ACT"},
                            {"rule": "B", "count": 0},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            self.assertEqual(
                load_summary_rules(list_summary),
                {
                    "A": RuleResult(count=3, layer="ACT"),
                    "B": RuleResult(count=0, layer=""),
                },
            )

            mapping_summary = tmp_path / "mapping.json"
            mapping_summary.write_text(
                json.dumps({"rules": {"A": 2, "B": {"count": 1, "layer": "M1"}}}),
                encoding="utf-8",
            )
            self.assertEqual(
                load_summary_rules(mapping_summary),
                {
                    "A": RuleResult(count=2, layer=""),
                    "B": RuleResult(count=1, layer="M1"),
                },
            )

    def test_bad_summaries_raise(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            empty = tmp_path / "empty.json"
            empty.write_text('{"rules": []}', encoding="utf-8")
            with self.assertRaises(CompareError):
                load_summary_rules(empty)

            broken = tmp_path / "broken.json"
            broken.write_text("not json", encoding="utf-8")
            with self.assertRaises(CompareError):
                load_summary_rules(broken)


if __name__ == "__main__":
    unittest.main()
