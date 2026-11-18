import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ics55_klayout_drc.engine import EngineError, find_klayout, run_drc
from ics55_klayout_drc.pdk import load_pdk_config
from ics55_klayout_drc.report import write_reports


def _make_gds(klayout: str, path: Path, body: str) -> None:
    script = path.with_suffix(".rb")
    script.write_text(
        "ly = RBA::Layout.new\n"
        'top = ly.create_cell("TOP")\n'
        f"{body}\n"
        f"ly.write('{path.as_posix()}')\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [klayout, "-b", "-r", str(script)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)


class EngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            cls.klayout = find_klayout()
        except EngineError as exc:
            raise unittest.SkipTest(str(exc)) from exc
        cls.cfg = load_pdk_config()

    def test_clean_layout(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            gds = tmp_path / "clean.gds"
            _make_gds(self.klayout, gds, "")
            result = run_drc(gds, tmp_path / "out", self.cfg, klayout=self.klayout)
            self.assertEqual(result.status, "clean")
            self.assertEqual(result.exit_code, 0)
            self.assertEqual(result.violation_count, 0)
            self.assertGreater(result.summary_data["rules_checked"], 100)
            self.assertTrue(result.report.is_file())
            self.assertTrue(result.log.is_file())
            self.assertIn("KLayout", result.log.read_text(encoding="utf-8"))

            reports = write_reports(
                tmp_path / "out", result.summary_data, result.violations
            )
            self.assertEqual(
                json.loads(reports["violation_map"].read_text(encoding="utf-8")),
                [],
            )

    def test_violation_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            gds = tmp_path / "bad.gds"
            _make_gds(
                self.klayout,
                gds,
                "m1 = ly.layer(81, 1)\n"
                "top.shapes(m1).insert(RBA::Box.new(0, 0, 50, 1000))",
            )
            result = run_drc(gds, tmp_path / "out", self.cfg, klayout=self.klayout)
            self.assertEqual(result.status, "violations")
            self.assertEqual(result.exit_code, 1)
            self.assertGreaterEqual(result.violation_count, 1)

            rules = {
                row["rule"]: row["count"]
                for row in result.summary_data["rules"]
            }
            self.assertIn("MET1.W.1", rules)
            self.assertGreater(rules["MET1.W.1"], 0)

            records = [
                json.loads(line)
                for line in result.violations.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            self.assertTrue(any(item["type"] == "MET1.W.1" for item in records))

    def test_missing_deck_input_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(EngineError):
                run_drc(
                    Path(tmp) / "missing.gds",
                    Path(tmp) / "out",
                    self.cfg,
                    klayout=self.klayout,
                )


if __name__ == "__main__":
    unittest.main()
