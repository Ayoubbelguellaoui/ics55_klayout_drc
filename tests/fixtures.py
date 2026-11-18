"""Pass/fail DRC fixtures rendered to GDS with KLayout.

Each fixture isolates one rule: ``fail_*`` shapes sit just outside the
foundry limit (>= 1 hit with the exact rule ID), ``pass_*`` shapes sit
just inside it (0 hits on that rule). Coordinates are in database units
(1 nm), matching the deck's 1 nm grid.
"""

from pathlib import Path

from ics55_klayout_drc.engine import DECK_PATH, EngineError, find_klayout, run_drc
from ics55_klayout_drc.pdk import load_pdk_config

# (datatype, purpose) GDS layer numbers for the drawn shapes.
ACT = (2, 1)
POLY = (41, 1)
NP = (52, 1)
PP = (53, 1)
CT = (72, 1)
MET1 = (81, 1)
SRAMALL = (171, 12)

# name -> (Ruby layer setup, Ruby shape statements)
FIXTURES: dict[str, tuple[str, str]] = {
    # ACT width 0.08 um
    "fail_aa_width": (
        f"ACT = ly.layer({ACT[0]}, {ACT[1]})",
        "top.shapes(ACT).insert(RBA::Box.new(0, 0, 50, 1000))",
    ),
    "pass_aa_width": (
        f"ACT = ly.layer({ACT[0]}, {ACT[1]})",
        "top.shapes(ACT).insert(RBA::Box.new(0, 0, 80, 1000))",
    ),
    # PO width 0.06 um
    "fail_po_width": (
        f"POLY = ly.layer({POLY[0]}, {POLY[1]})",
        "top.shapes(POLY).insert(RBA::Box.new(0, 0, 40, 1000))",
    ),
    # CT fixed 0.09 um square
    "fail_ct_size": (
        f"CT = ly.layer({CT[0]}, {CT[1]})",
        "top.shapes(CT).insert(RBA::Box.new(0, 0, 70, 70))",
    ),
    # MET1 width 0.09 um
    "fail_m1_width": (
        f"MET1 = ly.layer({MET1[0]}, {MET1[1]})",
        "top.shapes(MET1).insert(RBA::Box.new(0, 0, 50, 1000))",
    ),
    # MET1 area 0.042 um2 (0.1 x 0.1 = 0.01 um2, width is fine)
    "fail_m1_area": (
        f"MET1 = ly.layer({MET1[0]}, {MET1[1]})",
        "top.shapes(MET1).insert(RBA::Box.new(0, 0, 100, 100))",
    ),
    # PP and NP may not overlap
    "fail_np_pp_overlap": (
        f"NP = ly.layer({NP[0]}, {NP[1]})\nPP = ly.layer({PP[0]}, {PP[1]})",
        "top.shapes(NP).insert(RBA::Box.new(0, 0, 1000, 1000))\n"
        "top.shapes(PP).insert(RBA::Box.new(500, 0, 1500, 1000))",
    ),
    # CT landing on GATE (PO crossing AA) is forbidden
    "fail_ct_on_gate": (
        f"ACT = ly.layer({ACT[0]}, {ACT[1]})\n"
        f"POLY = ly.layer({POLY[0]}, {POLY[1]})\n"
        f"CT = ly.layer({CT[0]}, {CT[1]})",
        "top.shapes(ACT).insert(RBA::Box.new(0, 0, 1000, 1000))\n"
        "top.shapes(POLY).insert(RBA::Box.new(400, -200, 600, 1200))\n"
        "top.shapes(CT).insert(RBA::Box.new(450, 450, 540, 540))",
    ),
    # AA-to-contact-on-POLY spacing is 5 nm (< 65 nm).
    "fail_ct_poly_to_aa_space": (
        f"ACT = ly.layer({ACT[0]}, {ACT[1]})\n"
        f"POLY = ly.layer({POLY[0]}, {POLY[1]})\n"
        f"CT = ly.layer({CT[0]}, {CT[1]})\n"
        f"MET1 = ly.layer({MET1[0]}, {MET1[1]})",
        "top.shapes(ACT).insert(RBA::Box.new(0, 0, 1000, 1000))\n"
        "top.shapes(POLY).insert(RBA::Box.new(800, 450, 1200, 550))\n"
        "top.shapes(CT).insert(RBA::Box.new(1005, 455, 1095, 545))\n"
        "top.shapes(MET1).insert(RBA::Box.new(1000, 450, 1100, 550))",
    ),
    # 45-degree CT edge: GEO.ANG.CT allows 45, but CT must be rectilinear
    "fail_ct_45_angle": (
        f"CT = ly.layer({CT[0]}, {CT[1]})",
        "top.shapes(CT).insert(RBA::Polygon.new("
        "[RBA::Point.new(0, 0), RBA::Point.new(60, 0), "
        "RBA::Point.new(100, 40), RBA::Point.new(100, 100), "
        "RBA::Point.new(0, 100)]))",
    ),
    # 30-degree edge on MET1 (only 0/45/90 allowed)
    "fail_45_angle": (
        f"MET1 = ly.layer({MET1[0]}, {MET1[1]})",
        "top.shapes(MET1).insert(RBA::Polygon.new("
        "[RBA::Point.new(0, 0), RBA::Point.new(2000, 0), "
        "RBA::Point.new(2000, 1000), RBA::Point.new(1154, 2000), "
        "RBA::Point.new(0, 2000)]))",
    ),
    # Non-square CT inside SRAMALL is waived
    "waive_sram_ct": (
        f"CT = ly.layer({CT[0]}, {CT[1]})\n"
        f"SRAMALL = ly.layer({SRAMALL[0]}, {SRAMALL[1]})",
        "top.shapes(SRAMALL).insert(RBA::Box.new(0, 0, 5000, 5000))\n"
        "top.shapes(CT).insert(RBA::Box.new(1000, 1000, 1070, 1070))",
    ),
}

# Rules that each fail fixture must hit (and pass fixtures must not).
EXPECTED_RULES = {
    "fail_aa_width": "ACT.W.1",
    "pass_aa_width": "ACT.W.1",
    "fail_po_width": "PO.W.1",
    "fail_ct_size": "CT.W.1",
    "fail_m1_width": "MET1.W.1",
    "fail_m1_area": "MET1.A.1",
    "fail_ct_poly_to_aa_space": "CT.S.3",
    "fail_np_pp_overlap": "PP.O.1",
    "fail_ct_on_gate": "CT.R.1",
    "fail_ct_45_angle": "CT.R.3",
    "fail_45_angle": "GEO.ANG.MET1",
}

_results: dict[str, dict[str, int]] = {}


def build_fixture_gds(klayout: str, path: Path, name: str) -> None:
    """Render one fixture cell to GDS using a KLayout batch script."""
    setup, shapes = FIXTURES[name]
    script = path.with_suffix(".rb")
    script.write_text(
        "ly = RBA::Layout.new\n"
        'top = ly.create_cell("TOP")\n'
        f"{setup}\n{shapes}\n"
        f"ly.write('{path.as_posix()}')\n",
        encoding="utf-8",
    )
    import subprocess

    proc = subprocess.run(
        [klayout, "-b", "-r", str(script)], capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)


def fixture_rule_counts(name: str) -> dict[str, int]:
    """Run the deck once per fixture and cache its per-rule counts."""
    if name in _results:
        return _results[name]
    try:
        klayout = find_klayout()
    except EngineError as exc:
        raise unittest_skip(exc) from exc
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        gds = tmp_path / f"{name}.gds"
        build_fixture_gds(klayout, gds, name)
        result = run_drc(gds, tmp_path / "out", load_pdk_config(), klayout=klayout)
    counts = {row["rule"]: row["count"] for row in result.summary_data["rules"]}
    _results[name] = counts
    return counts


def unittest_skip(exc: Exception):
    import unittest

    return unittest.SkipTest(str(exc))
