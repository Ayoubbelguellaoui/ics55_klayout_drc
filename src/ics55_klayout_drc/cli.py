"""ics55-drc command line: tech generation, full-mask DRC, golden compare."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ics55_klayout_drc.compare import (
    CompareError,
    compare_summaries,
    load_summary_rules,
)
from ics55_klayout_drc.engine import EngineError, run_drc
from ics55_klayout_drc.layers import write_tech_files
from ics55_klayout_drc.pdk import (
    DEFAULT_CONFIG,
    PACKAGE_ROOT,
    STACK_KEYS,
    VALID_METAL_COMBINATIONS,
    PdkConfig,
    load_pdk_config,
)
from ics55_klayout_drc.report import write_reports

STACK_PATTERN = re.compile(r"^(?:(\d+)P)?(\d+)M(?:(\d+)TM)?$", re.IGNORECASE)


def _bool(value: str) -> bool:
    lowered = value.strip().lower()
    if lowered in {"1", "true", "yes", "on"}:
        return True
    if lowered in {"0", "false", "no", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"expected on/off, got {value!r}")


def _default_combo(total: int, top: int) -> tuple[int, ...]:
    matches = [
        combo
        for combo in VALID_METAL_COMBINATIONS
        if combo[0] == total and combo[1] == top
    ]
    if not matches:
        raise ValueError(
            f"unsupported metal stack total_metal={total} top_metal={top}"
        )
    # Prefer the thick T4 options used by ICS55, then T2.
    return max(matches, key=lambda combo: (combo[5], combo[4], combo[3], combo[2]))


def parse_stack(text: str) -> dict[str, int]:
    """Parse ``1P6M1TM`` or ``total_metal=6,top_metal=1,T4V2_T4M2=1``."""
    text = text.strip()
    if not text:
        raise ValueError("empty stack")
    if "=" in text:
        stack = {key: 0 for key in STACK_KEYS}
        provided: set[str] = set()
        for item in text.replace(";", ",").split(","):
            key, sep, value = item.partition("=")
            key = key.strip()
            if not sep or key not in STACK_KEYS:
                raise ValueError(f"bad stack item: {item!r}")
            stack[key] = int(value)
            provided.add(key)
        total = stack["total_metal"]
        top = stack["top_metal"]
        if total <= 0 or top not in (1, 2):
            raise ValueError("stack needs total_metal > 0 and top_metal in {1,2}")
        if not provided.intersection(STACK_KEYS[2:]):
            stack.update(zip(STACK_KEYS, _default_combo(total, top), strict=True))
        combo = tuple(stack[key] for key in STACK_KEYS)
        if combo not in VALID_METAL_COMBINATIONS:
            raise ValueError(f"invalid ICS55 metal option combination: {stack}")
        return stack

    match = STACK_PATTERN.fullmatch(text)
    if not match:
        raise ValueError(
            f"cannot parse stack {text!r}; use 1P6M1TM or total_metal=6,..."
        )
    total = int(match.group(2))
    top = int(match.group(3) or 1)
    if top not in (1, 2):
        raise ValueError("top_metal must be 1 or 2")
    return dict(zip(STACK_KEYS, _default_combo(total, top), strict=True))


def _stack_arg(value: str) -> dict[str, int]:
    try:
        return parse_stack(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _switch_overrides(args: argparse.Namespace) -> dict[str, bool]:
    keys = (
        "recommended",
        "density",
        "latchup",
        "dup",
        "metal_slot",
        "mom",
        "esd",
        "poly_efuse",
        "allow_v01",
        "chipedge",
    )
    return {
        key: getattr(args, key)
        for key in keys
        if getattr(args, key, None) is not None
    }


def _load_config(args: argparse.Namespace) -> PdkConfig:
    cfg = load_pdk_config(args.config, pdk_root=args.pdk_root)
    if args.stack:
        cfg.stack = dict(args.stack)
        cfg.validate_stack()
    return cfg


def _cmd_generate_tech(args: argparse.Namespace) -> int:
    cfg = load_pdk_config(args.config, pdk_root=args.pdk_root)
    if not cfg.layermap.is_file():
        print(f"layermap not found: {cfg.layermap}", file=sys.stderr)
        return 2
    paths = write_tech_files(cfg, args.out)
    for name, path in paths.items():
        print(f"{name}: {path}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    try:
        cfg = _load_config(args)
        result = run_drc(
            args.input,
            args.out,
            cfg,
            top=args.top,
            klayout=args.klayout,
            overrides=_switch_overrides(args),
        )
        reports = write_reports(args.out, result.summary_data, result.violations)
    except (EngineError, ValueError, OSError) as exc:
        print(f"ics55-drc: {exc}", file=sys.stderr)
        return 2

    summary = result.summary_data
    print(f"status: {result.status}")
    print(f"violations: {result.violation_count}")
    print(f"rules checked: {summary.get('rules_checked', 0)}")
    print(f"rules with findings: {result.rules_with_violations}")
    print(f"report: {result.report}")
    print(f"violation map: {reports['violation_map']}")
    print(f"html: {reports['html']}")
    return result.exit_code


def _load_deltas(path) -> tuple[set[str], set[str]]:
    if not path:
        return set(), set()
    from ics55_klayout_drc.calibre_golden import load_known_deltas

    return load_known_deltas(path)


def _cmd_compare(args: argparse.Namespace) -> int:
    klayout_path = Path(args.klayout)
    if not klayout_path.is_file():
        print(f"ics55-drc: summary not found: {klayout_path}", file=sys.stderr)
        return 2

    if args.calibre is None:
        print("golden=skipped (no --calibre; rule IDs not compared)")
        return 0
    calibre_path = Path(args.calibre)
    if not calibre_path.is_file():
        print(f"golden=skipped (not found: {calibre_path})")
        return 0

    try:
        klayout_rules = load_summary_rules(klayout_path)
    except CompareError as exc:
        print(f"ics55-drc: {exc}", file=sys.stderr)
        return 2

    known_rules, known_counts = _load_deltas(args.known_deltas)
    golden_source = ""
    try:
        from ics55_klayout_drc.calibre_golden import compare_with_golden, load_golden

        golden = load_golden(calibre_path)
        golden_source = golden.source
        comparison = compare_with_golden(
            klayout_rules,
            golden,
            known_rule_deltas=known_rules,
            known_count_deltas=known_counts,
        )
        golden_rules = comparison.golden
    except (ImportError, ValueError, OSError) as exc:
        print(f"ics55-drc: golden load failed: {exc}", file=sys.stderr)
        return 2
    print(f"klayout rules: {len(klayout_rules)}")
    print(f"golden rules: {len(golden_rules)}")
    print(f"matched rules: {comparison.matched}")
    print(f"only in klayout: {len(comparison.only_klayout)}")
    for rule in comparison.only_klayout:
        print(f"  + {rule}")
    print(f"only in golden: {len(comparison.only_golden)}")
    for rule in comparison.only_golden:
        print(f"  - {rule}")
    print(f"count deltas: {len(comparison.count_deltas)}")
    for rule, (kcount, gcount) in comparison.count_deltas.items():
        print(f"  ~ {rule}: klayout={kcount} golden={gcount}")

    failed = comparison.has_rule_deltas or (
        args.strict_counts and bool(comparison.count_deltas)
    )
    if args.json:
        payload = {
            "klayout": str(klayout_path),
            "golden": str(calibre_path),
            "golden_source": golden_source,
            "matched": comparison.matched,
            "only_klayout": comparison.only_klayout,
            "only_golden": comparison.only_golden,
            "count_deltas": {
                rule: {"klayout": k, "golden": g}
                for rule, (k, g) in comparison.count_deltas.items()
            },
            "failed": failed,
        }
        out = Path(args.json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(f"comparison: {out}")
    return 1 if failed else 0


def _add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--pdk-root", type=Path, default=None)


def _add_switch_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--recommended", type=_bool, default=None)
    parser.add_argument("--density", type=_bool, default=None)
    parser.add_argument(
        "--no-density", dest="density", action="store_false", default=None
    )
    parser.add_argument("--latchup", type=_bool, default=None)
    parser.add_argument("--dup", type=_bool, default=None)
    parser.add_argument("--metal-slot", dest="metal_slot", type=_bool, default=None)
    parser.add_argument("--mom", type=_bool, default=None)
    parser.add_argument("--esd", type=_bool, default=None)
    parser.add_argument("--poly-efuse", dest="poly_efuse", type=_bool, default=None)
    parser.add_argument("--chipedge", type=_bool, default=None)
    parser.add_argument("--allow-v01", dest="allow_v01", type=_bool, default=None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ics55-drc")
    sub = parser.add_subparsers(dest="cmd", required=True)

    gen = sub.add_parser(
        "generate-tech",
        help="Generate LYP/LYT/layers.rb from the PDK layermap",
    )
    _add_common_args(gen)
    gen.add_argument(
        "--out",
        type=Path,
        default=PACKAGE_ROOT / "klayout" / "tech",
        help="Directory for icsprout55.lyp / .lyt",
    )
    gen.set_defaults(func=_cmd_generate_tech)

    run = sub.add_parser("run", help="Run full-mask DRC on a GDS/OASIS layout")
    _add_common_args(run)
    run.add_argument("--input", type=Path, required=True, help="GDS/OASIS layout")
    run.add_argument(
        "--out",
        type=Path,
        default=Path("reports"),
        help="Output directory (default: reports)",
    )
    run.add_argument("--top", default=None, help="Top cell name (default: auto)")
    run.add_argument("--klayout", default=None, help="KLayout executable")
    run.add_argument(
        "--stack",
        type=_stack_arg,
        default=None,
        help="Metal stack, e.g. 1P6M1TM or total_metal=6,top_metal=1,T4V2_T4M2=1",
    )
    _add_switch_args(run)
    run.set_defaults(func=_cmd_run)

    compare = sub.add_parser(
        "compare",
        help="Compare KLayout rule IDs with a golden (Calibre) summary",
    )
    compare.add_argument("--klayout", type=Path, required=True)
    compare.add_argument("--calibre", type=Path, default=None)
    compare.add_argument("--json", type=Path, default=None)
    compare.add_argument(
        "--known-deltas",
        type=Path,
        default=None,
        help="YAML/JSON file with known_rule_deltas / known_count_deltas",
    )
    compare.add_argument(
        "--strict-counts",
        action="store_true",
        help="Fail on per-rule count differences, not only rule-ID deltas",
    )
    compare.set_defaults(func=_cmd_compare)

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
