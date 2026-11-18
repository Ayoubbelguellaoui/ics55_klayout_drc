import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from ics55_klayout_drc.cli import main, parse_stack


class StackParserTest(unittest.TestCase):
    def test_default_1p6m1tm(self):
        stack = parse_stack("1P6M1TM")
        self.assertEqual(stack["total_metal"], 6)
        self.assertEqual(stack["top_metal"], 1)
        self.assertEqual(stack["T4V2_T4M2"], 1)
        self.assertEqual(stack["T4V1_T4M1"], 0)

    def test_two_top_metals_use_t4_pair(self):
        stack = parse_stack("1P6M2TM")
        self.assertEqual(stack["top_metal"], 2)
        self.assertEqual(stack["T4V1_T4M1"], 1)
        self.assertEqual(stack["T4V2_T4M2"], 1)

    def test_key_value_form(self):
        stack = parse_stack("total_metal=6,top_metal=1,T4V2_T4M2=1")
        self.assertEqual(stack["total_metal"], 6)
        self.assertEqual(stack["T4V2_T4M2"], 1)

    def test_invalid_combinations_rejected(self):
        for text in (
            "3M1TM",
            "1P6M3TM",
            "total_metal=6,oops=1",
            "total_metal=6,top_metal=1,T4V2_T4M2=0",
        ):
            with self.assertRaises(ValueError):
                parse_stack(text)


class CliTest(unittest.TestCase):
    def test_run_missing_input_exits_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            code = main(
                [
                    "run",
                    "--input",
                    str(Path(tmp) / "missing.gds"),
                    "--out",
                    str(Path(tmp) / "out"),
                ]
            )
            self.assertEqual(code, 2)

    def test_compare_without_golden_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            summary = Path(tmp) / "summary.json"
            summary.write_text(
                json.dumps({"rules": [{"rule": "A", "count": 0}]}),
                encoding="utf-8",
            )
            buffer = StringIO()
            with redirect_stdout(buffer):
                code = main(["compare", "--klayout", str(summary)])
            self.assertEqual(code, 0)
            self.assertIn("golden=skipped", buffer.getvalue())

    def test_compare_rule_delta_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            klayout = tmp_path / "klayout.json"
            golden = tmp_path / "golden.json"
            klayout.write_text(
                json.dumps({"rules": [{"rule": "A", "count": 1}]}),
                encoding="utf-8",
            )
            golden.write_text(
                json.dumps({"rules": [{"rule": "B", "count": 1}]}),
                encoding="utf-8",
            )
            out = tmp_path / "comparison.json"
            with redirect_stdout(StringIO()):
                code = main(
                    [
                        "compare",
                        "--klayout",
                        str(klayout),
                        "--calibre",
                        str(golden),
                        "--json",
                        str(out),
                    ]
                )
            self.assertEqual(code, 1)
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(payload["only_klayout"], ["A"])
            self.assertEqual(payload["only_golden"], ["B"])
            self.assertTrue(payload["failed"])

    def test_compare_identical_summaries_exits_0(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            summary = tmp_path / "summary.json"
            summary.write_text(
                json.dumps(
                    {
                        "rules": [
                            {"rule": "A", "count": 2, "layer": "ACT"},
                            {"rule": "B", "count": 0},
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with redirect_stdout(StringIO()):
                code = main(
                    [
                        "compare",
                        "--klayout",
                        str(summary),
                        "--calibre",
                        str(summary),
                    ]
                )
            self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
