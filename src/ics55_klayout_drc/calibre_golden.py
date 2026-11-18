"""Ingest the foundry Calibre deck as a golden rule reference.

Two sources, checked in order:

1. ``drc_CAL.OUT`` / ``*.SUM`` run output — rule IDs with violation
   counts from a real Calibre run.
2. The TVF deck (``ICsprout_CalDRC_*.drc``) — ``RULECHECK <ID> { @ ... }``
   blocks give every active rule ID and its description.

Calibre IDs use underscores where the ICS55 KLayout deck uses dots
(``ACT_W_1`` vs ``ACT.W.1``); :func:`normalize_rule_id` maps between
them so rule-presence comparison is spelling-independent.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from ics55_klayout_drc.compare import RuleResult, load_summary_rules

DECK_RULE_RE = re.compile(
    r"^\s*(?:RULECHECK\s+)?(?P<name>\$\{\w+\}_\w+|[A-Z][A-Za-z0-9_$\{\}]*_\w+)\s*\{\s*$"
    r"(?P<body>(?:.*\n)*?)^\s*\}",
    re.MULTILINE,
)
DESC_RE = re.compile(r"^\s*@\s?(?P<desc>.+?)\s*$", re.MULTILINE)

# Template expansions for the deck's per-metal / per-via RULECHECK loops.
TEMPLATE_LISTS = {
    "via_layer": ("V1", "V2", "V3", "V4", "V5", "V6", "V7"),
    "metal_layer": ("M2", "M3", "M4", "M5", "M6", "M7", "M8"),
    "bottom_metal": ("M1", "M2", "M3", "M4", "M5", "M6", "M7"),
}
TEMPLATE_RE = re.compile(r"\$\{(?P<key>\w+)\}")

# Count tokens in Calibre run output. Two accepted shapes per rule:
#   "RULECHECK ACT_W_1 ... Total Count: 2"   (standard Calibre .OUT)
#   "ACT_W_1: 2" / "ACT_W_1 Total violations: 2"  (abbreviated summaries)
OUT_RULE_RE = re.compile(
    r"RULECHECK\s+(?P<name>[A-Za-z0-9_]+).*?Total\s+Count\s*:\s*(?P<count>\d+)",
    re.IGNORECASE | re.DOTALL,
)
TOTAL_WORD_RE = re.compile(
    r"^\s*(?P<name>[A-Z][A-Za-z0-9]*_[A-Za-z0-9_]*\d)\s+"
    r"Total\s+violations?\s*[:=]?\s*(?P<count>\d+)",
    re.MULTILINE,
)
SHORT_RULE_RE = re.compile(
    r"^\s*(?P<name>[A-Z][A-Za-z0-9]*_[A-Za-z0-9_]*\d)\s*[:=]\s*(?P<count>\d+)"
    r"\s*(?:violations?|errors?)?\s*$",
    re.MULTILINE,
)
LOOSE_RULE_RE = re.compile(
    r"^\s*(?P<name>[A-Z][A-Za-z0-9]*_[A-Za-z0-9_]*\d)\s+(?P<count>\d+)\s+violations",
    re.MULTILINE,
)


@dataclass
class GoldenRules:
    rules: dict[str, RuleResult]
    source: str


def normalize_rule_id(rule: str) -> str:
    """Map a Calibre underscore ID to the KLayout dot spelling (or back).

    Also aliases Calibre's short layer names to the deck's spellings:
    ``M2`` -> ``MET2``, ``V1`` -> ``VIA1`` (T2M*/T4M*/T8M* keep their name).
    """
    dotted = rule.replace("_", ".")
    if "${" in dotted:
        return dotted
    if re.match(r"^M(\d)\.", dotted):
        return "MET" + dotted[1:]
    if re.match(r"^V(\d)\.", dotted):
        return "VIA" + dotted[1:]
    return dotted


def golden_id(rule: str) -> str:
    """Map a KLayout dot ID to the Calibre underscore spelling."""
    return rule.replace(".", "_")


def _expand_template_name(name: str) -> list[str]:
    """Expand ``${via_layer}`` style template names to concrete rule IDs.

    Calibre instantiates templated RULECHECKs per metal/via inside
    ``foreach`` loops; the golden reference treats every instantiation
    whose layer is on the selected stack as active.
    """
    match = TEMPLATE_RE.search(name)
    if not match:
        return [name]
    key = match.group("key")
    values = TEMPLATE_LISTS.get(key)
    if values is None:
        return [name]
    expanded = []
    for value in values:
        candidate = TEMPLATE_RE.sub(value, name)
        expanded.append(candidate)
    return expanded


def parse_deck(path: str | Path, *, stack_layers: set[str] | None = None) -> dict[str, RuleResult]:
    """Extract active rule IDs and descriptions from a TVF deck.

    Handles both ``RULECHECK NAME { ... }`` and the deck's implicit
    ``NAME { ... }`` blocks (CT/SAB section), plus the per-metal/per-via
    ``${via_layer}`` template loops. Commented-out checks (``#RULECHECK``)
    are skipped. ``stack_layers`` restricts template expansion to the
    configured metal stack (default: M1..M5 plus V1..V4).
    """
    if stack_layers is None:
        stack_layers = {"M1", "M2", "M3", "M4", "M5", "V1", "V2", "V3", "V4"}
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    rules: dict[str, RuleResult] = {}
    for match in DECK_RULE_RE.finditer(text):
        line_start = text.rfind("\n", 0, match.start()) + 1
        prefix = text[line_start : match.start()]
        if prefix.lstrip().startswith("#"):
            continue
        name = match.group("name")
        if "${" in _expand_template_name(name)[0]:
            continue  # template key not in TEMPLATE_LISTS (e.g. ${j} in SRCK loops)
        desc_match = DESC_RE.search(match.group("body"))
        description = desc_match.group("desc") if desc_match else ""
        for expanded in _expand_template_name(name):
            layer = expanded.split("_", 1)[0]
            if expanded != name and layer not in stack_layers and not expanded.startswith("T"):
                continue
            rules[expanded] = RuleResult(count=0, layer="", description=description)
    if not rules:
        raise ValueError(f"no RULECHECK blocks found in {path}")
    return rules


def parse_run_output(path: str | Path) -> dict[str, RuleResult]:
    """Read per-rule violation counts from Calibre run output."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    rules: dict[str, RuleResult] = {}

    def add(name: str, count: int) -> None:
        if name in rules:
            rules[name].count += count
        else:
            rules[name] = RuleResult(count=count)

    for match in OUT_RULE_RE.finditer(text):
        add(match.group("name"), int(match.group("count")))
    for pattern in (TOTAL_WORD_RE, SHORT_RULE_RE, LOOSE_RULE_RE):
        for match in pattern.finditer(text):
            add(match.group("name"), int(match.group("count")))
    if not rules:
        raise ValueError(f"no rule counts found in {path}")
    return rules


def load_golden(path: str | Path) -> GoldenRules:
    """Load a golden reference from a deck, run output, or summary JSON."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".out", ".sum"}:
        return GoldenRules(parse_run_output(path), f"calibre-run:{path.name}")
    if suffix == ".json":
        return GoldenRules(load_summary_rules(path), f"summary:{path.name}")
    return GoldenRules(parse_deck(path), f"calibre-deck:{path.name}")


def _expand_patterns(patterns: set[str], names: set[str]) -> set[str]:
    """Expand ``PREFIX*`` entries to every matching rule name."""
    expanded = set()
    for pattern in patterns:
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            expanded.update(name for name in names if name.startswith(prefix))
        else:
            expanded.add(pattern)
    return expanded


def compare_with_golden(
    klayout_rules: dict[str, RuleResult],
    golden: GoldenRules,
    *,
    known_rule_deltas: set[str] | None = None,
    known_count_deltas: set[str] | None = None,
):
    """Compare KLayout results against golden on normalized rule IDs.

    Known-delta entries may end in ``*`` to waive a whole rule family
    (e.g. ``AADUM*`` or ``LATCHUP*``).
    """
    from ics55_klayout_drc.compare import compare_summaries

    golden_normalized = {
        normalize_rule_id(name): result for name, result in golden.rules.items()
    }
    all_names = set(klayout_rules) | set(golden_normalized)
    comparison = compare_summaries(
        klayout_rules,
        golden_normalized,
        known_rule_deltas=_expand_patterns(known_rule_deltas or set(), all_names),
        known_count_deltas=_expand_patterns(known_count_deltas or set(), all_names),
    )
    comparison.source = golden.source
    return comparison


def save_known_deltas(path: str | Path, *, rule_deltas: set[str], count_deltas: set[str]) -> None:
    payload = {
        "known_rule_deltas": sorted(rule_deltas),
        "known_count_deltas": sorted(count_deltas),
    }
    Path(path).write_text(
        json.dumps(payload, indent=2) + "\n", encoding="utf-8"
    )


def load_known_deltas(path: str | Path) -> tuple[set[str], set[str]]:
    """Read tests/expected/known_deltas.yml (or a JSON equivalent)."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        data = json.loads(text)
    else:
        from ics55_klayout_drc.pdk import _read_yaml

        data = _read_yaml(path)
    rule_deltas = {str(item) for item in (data or {}).get("known_rule_deltas") or []}
    count_deltas = {str(item) for item in (data or {}).get("known_count_deltas") or []}
    return rule_deltas, count_deltas
