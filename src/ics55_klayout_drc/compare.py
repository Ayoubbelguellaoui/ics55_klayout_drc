"""Compare KLayout DRC rule results against a golden summary."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


class CompareError(ValueError):
    """A summary file is missing or not in a supported format."""


@dataclass
class RuleResult:
    count: int = 0
    layer: str = ""


@dataclass
class Comparison:
    klayout: dict[str, RuleResult] = field(default_factory=dict)
    golden: dict[str, RuleResult] = field(default_factory=dict)
    only_klayout: list[str] = field(default_factory=list)
    only_golden: list[str] = field(default_factory=list)
    count_deltas: dict[str, tuple[int, int]] = field(default_factory=dict)

    @property
    def matched(self) -> int:
        return len(set(self.klayout) & set(self.golden))

    @property
    def has_rule_deltas(self) -> bool:
        return bool(self.only_klayout or self.only_golden)

    @property
    def has_deltas(self) -> bool:
        return self.has_rule_deltas or bool(self.count_deltas)


def load_summary_rules(path: str | Path) -> dict[str, RuleResult]:
    """Read rule counts from a KLayout/ICS55 summary JSON.

    Supported shapes::

        {"rules": [{"rule": "ACT.W.1", "count": 3, "layer": "ACT"}]}
        {"rules": {"ACT.W.1": 3}}
    """
    path = Path(path)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CompareError(f"cannot read summary {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise CompareError(f"{path} is not a rule-summary object")

    rules = data.get("rules", {})
    result: dict[str, RuleResult] = {}
    if isinstance(rules, list):
        for row in rules:
            if not isinstance(row, dict):
                continue
            name = row.get("rule")
            if not isinstance(name, str) or not name:
                continue
            result[name] = RuleResult(
                count=int(row.get("count") or 0),
                layer=str(row.get("layer") or ""),
            )
    elif isinstance(rules, dict):
        for name, value in rules.items():
            if not isinstance(name, str) or not name:
                continue
            if isinstance(value, dict):
                result[name] = RuleResult(
                    count=int(value.get("count") or 0),
                    layer=str(value.get("layer") or ""),
                )
            else:
                result[name] = RuleResult(count=int(value or 0))
    else:
        raise CompareError(f"{path}: unsupported 'rules' value")

    if not result:
        raise CompareError(f"{path}: no rules found")
    return result


def compare_summaries(
    klayout: dict[str, RuleResult],
    golden: dict[str, RuleResult],
    *,
    known_rule_deltas: set[str] | None = None,
    known_count_deltas: set[str] | None = None,
) -> Comparison:
    """Compare rule presence and per-rule counts.

    Rule-ID presence is the pass/fail criterion; count deltas are recorded for
    review because KLayout and Calibre may merge marker shapes differently.
    """
    known_rules = known_rule_deltas or set()
    known_counts = known_count_deltas or set()

    only_klayout = sorted(set(klayout) - set(golden) - known_rules)
    only_golden = sorted(set(golden) - set(klayout) - known_rules)
    count_deltas = {
        name: (klayout[name].count, golden[name].count)
        for name in sorted(set(klayout) & set(golden))
        if name not in known_counts and klayout[name].count != golden[name].count
    }
    return Comparison(
        klayout=klayout,
        golden=golden,
        only_klayout=only_klayout,
        only_golden=only_golden,
        count_deltas=count_deltas,
    )
