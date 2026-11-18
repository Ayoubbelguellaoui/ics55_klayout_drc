"""Phase 6 regression suite: one isolated rule per fixture.

Skipped automatically when KLayout is unavailable; every fixture runs the
real deck against a tiny GDS rendered just for it.
"""

import unittest

from ics55_klayout_drc.engine import EngineError, find_klayout

from fixtures import EXPECTED_RULES, FIXTURES, fixture_rule_counts


@unittest.skipUnless(True, "")
class _KLayoutCase(unittest.TestCase):
    pass


def _klayout_available() -> bool:
    try:
        find_klayout()
        return True
    except EngineError:
        return False


@unittest.skipUnless(_klayout_available(), "KLayout executable required")
class FixturePolarityTest(unittest.TestCase):
    """fail_* -> >= 1 hit on the exact rule; pass_* -> 0 hits on that rule."""

    def test_every_fixture_has_a_known_polarity(self):
        for name in FIXTURES:
            if name.startswith("fail_"):
                self.assertIn(name, EXPECTED_RULES, name)
            elif not name.startswith(("pass_", "waive_")):
                self.fail(f"fixture {name} has no declared polarity")

    def test_fail_fixtures_hit_their_rule(self):
        for name, rule in sorted(EXPECTED_RULES.items()):
            if not name.startswith("fail_"):
                continue
            with self.subTest(fixture=name):
                counts = fixture_rule_counts(name)
                self.assertGreater(counts.get(rule, 0), 0, f"{rule} not hit")

    def test_pass_fixture_is_clean_on_its_rule(self):
        counts = fixture_rule_counts("pass_aa_width")
        self.assertEqual(counts.get("ACT.W.1", 0), 0)

    def test_waive_sram_ct_suppresses_ct_size(self):
        counts = fixture_rule_counts("waive_sram_ct")
        self.assertEqual(counts.get("CT.W.1", 0), 0)
        self.assertEqual(counts.get("CT.W.2", 0), 0)


if __name__ == "__main__":
    unittest.main()
