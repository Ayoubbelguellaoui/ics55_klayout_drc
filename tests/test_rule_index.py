"""RULE_INDEX.md must stay in sync with the deck and the foundry Calibre deck."""

import re
import unittest
from pathlib import Path

from ics55_klayout_drc.calibre_golden import normalize_rule_id, parse_deck
from ics55_klayout_drc.engine import EngineError, find_klayout
from ics55_klayout_drc.pdk import PACKAGE_ROOT, load_pdk_config

INDEX = PACKAGE_ROOT / "klayout" / "drc" / "RULE_INDEX.md"
CALIBRE_DECK = (
    PACKAGE_ROOT.parent
    / "icsprout55-pdk"
    / "pv"
    / "DRC"
    / "ICsprout_CalDRC_55LLULP1233_REV1_0_OS.drc"
)
ROW_RE = re.compile(r"^\| `(?P<rule>[^`]+)` \| (?P<layer>[^|]+) \| (?P<class>[^|]+) \| (?P<desc>.*) "
                    r"\| (?P<calibre>[^|]+) \|$", re.MULTILINE)


def _rows() -> list[dict[str, str]]:
    return [match.groupdict() for match in ROW_RE.finditer(INDEX.read_text(encoding="utf-8"))]


class RuleIndexTest(unittest.TestCase):
    def test_index_exists_and_lists_rules(self):
        self.assertTrue(INDEX.is_file())
        rows = _rows()
        self.assertGreater(len(rows), 150)

    def test_rule_ids_are_unique(self):
        rules = [row["rule"] for row in _rows()]
        self.assertEqual(len(rules), len(set(rules)))

    def test_core_families_are_present(self):
        rules = {row["rule"] for row in _rows()}
        for rule in (
            "ACT.W.1",
            "PO.W.1",
            "CT.W.1",
            "MET1.W.1",
            "VIA1.EN.1",
            "GEO.ANG.MET1",
            "GEO.OFFGRID.CT",
            "AA.D.min",
        ):
            self.assertIn(rule, rules)

    def test_calibre_ids_exist_in_the_foundry_deck(self):
        if not CALIBRE_DECK.is_file():
            raise unittest.SkipTest(f"Calibre deck not found: {CALIBRE_DECK}")
        golden = {normalize_rule_id(name) for name in parse_deck(CALIBRE_DECK)}
        for row in _rows():
            if row["calibre"].strip() == "—":
                continue
            calibre = row["calibre"].strip().strip("`")
            self.assertIn(normalize_rule_id(calibre), golden, row["rule"])


class RuleIndexSyncTest(unittest.TestCase):
    """The index must equal what the deck actually runs (needs KLayout)."""

    @classmethod
    def setUpClass(cls):
        try:
            cls.klayout = find_klayout()
        except EngineError as exc:
            raise unittest.SkipTest(str(exc)) from exc

    def test_index_matches_a_real_run(self):
        import subprocess
        import tempfile

        from ics55_klayout_drc.engine import run_drc

        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            gds = tmp / "empty.gds"
            script = tmp / "empty.rb"
            script.write_text(
                "ly = RBA::Layout.new\n"
                'ly.create_cell("TOP")\n'
                f"ly.write('{gds.as_posix()}')\n",
                encoding="utf-8",
            )
            subprocess.run(
                [self.klayout, "-b", "-r", str(script)], check=True, capture_output=True
            )
            result = run_drc(
                gds, tmp / "out", load_pdk_config(), klayout=self.klayout
            )
        checked = {row["rule"] for row in result.summary_data["rules"]}
        documented = {row["rule"] for row in _rows()}
        self.assertEqual(checked - documented, set(), "rules missing from RULE_INDEX.md")
        self.assertEqual(documented - checked, set(), "stale rules in RULE_INDEX.md")


if __name__ == "__main__":
    unittest.main()
