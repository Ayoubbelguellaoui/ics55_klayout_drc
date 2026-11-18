"""Turn KLayout DRC output into CSV, HTML and ECC violation maps."""

import csv
import html
import json
from pathlib import Path


def load_summary(path: str | Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} is not a DRC summary object")
    return data


def read_violations(path: str | Path) -> list[dict]:
    path = Path(path)
    if not path.is_file():
        return []
    records = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict) and item.get("type"):
            records.append(item)
    return records


def _bbox(item: dict) -> list[float]:
    raw = item.get("bbox")
    values = [0.0, 0.0, 0.0, 0.0]
    if isinstance(raw, list | tuple) and len(raw) >= 4:
        try:
            values = [float(raw[i]) for i in range(4)]
        except (TypeError, ValueError):
            pass
    return values


def to_ecc_violations(
    records: list[dict],
    summary: dict | None = None,
) -> list[dict]:
    rule_layers = {}
    if summary:
        for rule in summary.get("rules", []):
            if isinstance(rule, dict) and rule.get("rule"):
                rule_layers[rule["rule"]] = rule.get("layer") or "UNKNOWN"

    violations = []
    for item in records:
        violation_type = item.get("type")
        if not isinstance(violation_type, str) or not violation_type:
            continue
        bbox = _bbox(item)
        layer = item.get("layer") or rule_layers.get(violation_type) or "UNKNOWN"
        violations.append(
            {
                "type": violation_type,
                "rule": violation_type,
                "layer": str(layer),
                "class": "error",
                "count": 1,
                "shape": [*bbox, str(layer)],
                "bbox": bbox,
            }
        )
    return violations


def write_violation_map(
    violations_path: str | Path,
    out_path: str | Path,
    summary: dict | None = None,
) -> Path:
    records = read_violations(violations_path)
    violations = to_ecc_violations(records, summary)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(violations, indent=2) + "\n", encoding="utf-8"
    )
    return out_path


def write_csv(summary: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = summary.get("rules", [])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rule", "layer", "count", "class", "description"])
        for row in rows:
            writer.writerow(
                [
                    row.get("rule", ""),
                    row.get("layer", ""),
                    row.get("count", 0),
                    row.get("class", "error"),
                    row.get("description", ""),
                ]
            )
    return path


def _metric(label: str, value: object) -> str:
    return (
        "<div class='metric'><span class='label'>"
        f"{html.escape(label)}</span><span class='value'>"
        f"{html.escape(str(value))}</span></div>"
    )


def write_html(summary: dict, path: str | Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    options = summary.get("options", {})
    rows = sorted(
        summary.get("rules", []),
        key=lambda item: (-int(item.get("count") or 0), str(item.get("rule"))),
    )

    body = [
        "<!doctype html>",
        "<html lang='en'><head><meta charset='utf-8'>",
        "<title>ICS55 KLayout DRC report</title>",
        "<style>",
        "body{font-family:system-ui,sans-serif;margin:2rem;color:#1d2430}",
        "h1{margin:0 0 .3rem}",
        ".sub{color:#5b6472;margin-bottom:1.5rem}",
        ".metrics{display:flex;gap:1rem;flex-wrap:wrap;margin:1rem 0 2rem}",
        ".metric{border:1px solid #d7dce3;border-radius:8px;padding:.7rem 1rem;"
        "min-width:150px}",
        ".metric .label{display:block;color:#5b6472;font-size:.8rem;"
        "text-transform:uppercase;letter-spacing:.04em}",
        ".metric .value{font-size:1.35rem;font-weight:600}",
        "table{border-collapse:collapse;width:100%}",
        "th,td{border-bottom:1px solid #e2e6ec;padding:.55rem .6rem;"
        "text-align:left;vertical-align:top}",
        "th{background:#f5f7fa;font-size:.85rem;text-transform:uppercase;"
        "letter-spacing:.03em;color:#48505c}",
        "tr.hit td{background:#fff5f5}",
        ".num{text-align:right;font-variant-numeric:tabular-nums}",
        "code{background:#f0f2f5;padding:.1rem .3rem;border-radius:4px}",
        "</style></head><body>",
        "<h1>ICS55 KLayout DRC report</h1>",
        f"<div class='sub'>{html.escape(str(summary.get('input', '')))}"
        f" &middot; top <code>{html.escape(str(summary.get('top') or 'auto'))}</code>"
        f" &middot; {html.escape(str(summary.get('tool', 'ics55_klayout_drc')))}",
        "</div>",
        "<div class='metrics'>",
        _metric("Violations", summary.get("violations", 0)),
        _metric("Rules checked", summary.get("rules_checked", 0)),
        _metric(
            "Rules with findings", summary.get("rules_with_violations", 0)
        ),
        _metric("Skipped checks", len(summary.get("skipped", []))),
        "</div>",
    ]

    if options:
        body.append("<h2>Options</h2><p>")
        body.append(
            " ".join(
                f"<code>{html.escape(str(k))}={html.escape(str(v))}</code>"
                for k, v in options.items()
            )
        )
        body.append("</p>")

    body.append("<h2>Rules</h2>")
    body.append("<table><thead><tr><th>Rule</th><th>Layer</th>")
    body.append("<th class='num'>Count</th><th>Description</th></tr></thead><tbody>")
    for row in rows:
        count = int(row.get("count") or 0)
        css = " class='hit'" if count else ""
        body.append(
            f"<tr{css}><td><code>{html.escape(str(row.get('rule', '')))}</code></td>"
            f"<td>{html.escape(str(row.get('layer', '')))}</td>"
            f"<td class='num'>{count}</td>"
            f"<td>{html.escape(str(row.get('description', '')))}</td></tr>"
        )
    body.append("</tbody></table>")

    notes = summary.get("notes") or []
    skipped = summary.get("skipped") or []
    if skipped:
        body.append("<h2>Skipped</h2><ul>")
        body.extend(f"<li>{html.escape(str(item))}</li>" for item in skipped)
        body.append("</ul>")
    if notes:
        body.append("<h2>Notes</h2><ul>")
        body.extend(f"<li>{html.escape(str(item))}</li>" for item in notes)
        body.append("</ul>")

    body.append("</body></html>")
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def write_reports(
    out_dir: str | Path,
    summary: dict,
    violations_path: str | Path | None = None,
) -> dict[str, Path]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "csv": write_csv(summary, out_dir / "drc_summary.csv"),
        "html": write_html(summary, out_dir / "drc_report.html"),
        "violation_map": write_violation_map(
            violations_path or (out_dir / "drc_violations.jsonl"),
            out_dir / "violation_map.json",
            summary,
        ),
    }
    return paths
