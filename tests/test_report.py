import csv
import json
import tempfile
import unittest
from pathlib import Path

from ics55_klayout_drc.report import (
    read_violations,
    to_ecc_violations,
    write_reports,
)

SUMMARY = {
    "tool": "ics55_klayout_drc",
    "input": "chip.gds",
    "top": "TOP",
    "options": {"total_metal": 6, "top_metal": 1},
    "violations": 3,
    "rules_checked": 2,
    "rules_with_violations": 1,
    "skipped": ["RULE.X: API unavailable"],
    "notes": ["LATCHUP deferred"],
    "rules": [
        {
            "rule": "ACT.W.1",
            "layer": "ACT",
            "count": 3,
            "class": "error",
            "description": "AA width >= 0.08um",
        },
        {
            "rule": "PO.W.1",
            "layer": "POLY",
            "count": 0,
            "class": "error",
            "description": "PO width >= 0.06um",
        },
    ],
}


class ReportTest(unittest.TestCase):
    def test_writes_csv_html_and_ecc_map(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            violations = out / "drc_violations.jsonl"
            lines = [
                {"type": "ACT.W.1", "layer": "ACT", "bbox": [0, 0, 1, 1]},
                {"type": "ACT.W.1", "bbox": [2, 0, 3, 1]},
                '{"type": "", "layer": "ACT"}',
                "not json",
            ]
            violations.write_text(
                "\n".join(
                    line if isinstance(line, str) else json.dumps(line)
                    for line in lines
                )
                + "\n",
                encoding="utf-8",
            )

            paths = write_reports(out, SUMMARY, violations)

            with paths["csv"].open(encoding="utf-8") as handle:
                rows = list(csv.DictReader(handle))
            self.assertEqual(len(rows), 2)
            self.assertEqual(
                sum(int(row["count"]) for row in rows),
                SUMMARY["violations"],
            )

            html = paths["html"].read_text(encoding="utf-8")
            self.assertIn("ICS55 KLayout DRC report", html)
            self.assertIn("ACT.W.1", html)
            self.assertIn(">3<", html)
            self.assertIn(">2<", html)
            self.assertIn("LATCHUP deferred", html)

            ecc = json.loads(paths["violation_map"].read_text(encoding="utf-8"))
            self.assertEqual(len(ecc), 2)
            for item in ecc:
                self.assertEqual(len(item["shape"]), 5)
            self.assertEqual(ecc[0]["shape"][4], "ACT")
            # Missing per-record layer falls back to the summary rule layer.
            self.assertEqual(ecc[1]["shape"][4], "ACT")
            self.assertEqual(ecc[1]["shape"][:4], [2.0, 0.0, 3.0, 1.0])

    def test_read_violations_skips_bad_lines(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "violations.jsonl"
            path.write_text(
                '{"type":"A"}\n\nnot json\n{"type":""}\n{"type":"B"}\n',
                encoding="utf-8",
            )
            self.assertEqual(
                read_violations(path),
                [{"type": "A"}, {"type": "B"}],
            )

    def test_to_ecc_violations_shape_contract(self):
        records = [{"type": "M1.W.1", "layer": "MET1", "bbox": [1, 2, 3, 4]}]
        violations = to_ecc_violations(records)
        self.assertEqual(
            violations,
            [
                {
                    "type": "M1.W.1",
                    "shape": [1.0, 2.0, 3.0, 4.0, "MET1"],
                    "bbox": [1.0, 2.0, 3.0, 4.0],
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
