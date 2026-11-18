"""Parse ICS55 layermap and generate KLayout bindings."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from xml.sax.saxutils import escape

from ics55_klayout_drc.pdk import PdkConfig

PURPOSE_DATATYPE = {
    "drawing": 1,
    "dm": 2,
    "dmblk": 3,
    "res": 4,
    "opcblk": 5,
    "text": 6,
    "bar": 7,
    "slot": 8,
    "slotblk": 9,
    "mom": 10,
    "mark": 12,
}

RUBY_RESERVED = frozenset(
    {
        "BEGIN",
        "END",
        "alias",
        "and",
        "begin",
        "break",
        "case",
        "class",
        "def",
        "defined?",
        "do",
        "else",
        "elsif",
        "end",
        "ensure",
        "false",
        "for",
        "if",
        "in",
        "module",
        "next",
        "nil",
        "not",
        "or",
        "redo",
        "rescue",
        "retry",
        "return",
        "self",
        "super",
        "then",
        "true",
        "undef",
        "unless",
        "until",
        "when",
        "while",
        "yield",
        "COVER",
        "IO",
    }
)

GROUP_ORDER = (
    "Front-end",
    "Metal",
    "Via",
    "Thick metal",
    "Pad / RDL",
    "MIM",
    "Markers",
    "Other",
)


@dataclass(frozen=True)
class LayerEntry:
    name: str
    purpose: str
    gds_layer: int
    gds_datatype: int

    @property
    def ruby_name(self) -> str:
        # Marker layers are independent logical layers in ICS55 (NODRC,
        # SRAMALL, ...), not alternate purposes of a drawn layer. Keeping the
        # bare name matches the Calibre deck and avoids *_mark bindings.
        if self.purpose in {"drawing", "mark"}:
            base = self.name
        else:
            base = f"{self.name}_{self.purpose}"
        ident = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in base)
        if ident[0].isdigit() or ident in RUBY_RESERVED:
            ident = f"L_{ident}"
        return ident

    @property
    def display_name(self) -> str:
        return f"{self.name}.{self.purpose}"


def parse_layermap(path: Path) -> list[LayerEntry]:
    entries: list[LayerEntry] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) != 4:
            raise ValueError(f"bad layermap line: {raw!r}")
        name, purpose, layer, datatype = parts
        entries.append(
            LayerEntry(name, purpose, int(layer), int(datatype))
        )
    return entries


def layer_group(entry: LayerEntry) -> str:
    name = entry.name
    if name.startswith("MET"):
        return "Metal"
    if name.startswith("VIA") or name in {"RV"} or name.startswith(("T2V", "T4V", "T8V")):
        return "Via"
    if name.startswith(("T2M", "T4M", "T8M")):
        return "Thick metal"
    if name in {"CB", "ALPAD", "RDL", "COVER"}:
        return "Pad / RDL"
    if name in {"BMIM", "TMIM"}:
        return "MIM"
    if entry.purpose == "mark" or name in {
        "ZERO",
        "IO",
        "CORE",
        "ULLD",
        "UD",
        "OD",
        "CHIPBLK",
        "NODRC",
    }:
        return "Markers"
    feol = {
        "ACT",
        "DNW",
        "DNW6t",
        "NW1",
        "NVT1",
        "PVT1",
        "NVT3",
        "PVT3",
        "DGOX",
        "TGOX",
        "POLY",
        "NPD",
        "NP",
        "PP",
        "HRP",
        "ESD",
        "SAB",
        "CT",
    }
    if name in feol:
        return "Front-end"
    return "Other"


def generate_layers_rb(entries: Iterable[LayerEntry]) -> str:
    lines = [
        "# Generated from icsprout55.layermap — do not edit by hand.",
        "",
    ]
    for entry in entries:
        lines.append(
            f"{entry.ruby_name} = input({entry.gds_layer}, {entry.gds_datatype})"
        )
    lines.append("")
    return "\n".join(lines)


def generate_lyp(entries: Iterable[LayerEntry]) -> str:
    grouped: dict[str, list[LayerEntry]] = {name: [] for name in GROUP_ORDER}
    for entry in entries:
        grouped.setdefault(layer_group(entry), []).append(entry)

    parts = ['<?xml version="1.0" encoding="utf-8"?>', "<layer-properties>"]
    for group in GROUP_ORDER:
        items = grouped.get(group) or []
        if not items:
            continue
        parts.append(" <properties>")
        parts.append(f"  <name>{escape(group)}</name>")
        for entry in items:
            visible = entry.purpose == "drawing"
            r, g, b = _color(entry)
            dither = 1 if entry.purpose == "drawing" else 5
            parts.append("  <properties>")
            parts.append(f"   <frame-color>#{r:02x}{g:02x}{b:02x}</frame-color>")
            parts.append(f"   <fill-color>#{r:02x}{g:02x}{b:02x}</fill-color>")
            parts.append(f"   <dither-pattern>{dither}</dither-pattern>")
            parts.append(f"   <visible>{'true' if visible else 'false'}</visible>")
            parts.append("   <transparent>false</transparent>")
            parts.append("   <width>1</width>")
            parts.append(f"   <name>{escape(entry.display_name)}</name>")
            parts.append(
                f"   <source>{entry.gds_layer}/{entry.gds_datatype}@1</source>"
            )
            parts.append("  </properties>")
        parts.append(" </properties>")
    parts.append("</layer-properties>")
    parts.append("")
    return "\n".join(parts)


def generate_lm(entries: Iterable[LayerEntry]) -> str:
    """KLayout layer-map file (``.lm``): one ``<ld> : <name>`` line per layer.

    This is the format ``RBA::LayerMap.from_string`` parses and the format the
    technology reader options reference through ``<layer-map>``. Comments use
    ``#``.
    """
    lines = [
        "# Generated from the ICS55 layermap; do not edit by hand.",
        "# Format: <gds layer>/<gds datatype> : <KLayout layer name>",
    ]
    for entry in entries:
        lines.append(
            f"{entry.gds_layer}/{entry.gds_datatype} : {entry.ruby_name}"
        )
    lines.append("")
    return "\n".join(lines)


def generate_lyt(
    lyp_name: str = "icsprout55.lyp", lm_name: str = "icsprout55.lm"
) -> str:
    return f"""<?xml version="1.0" encoding="utf-8"?>
<technology>
 <name>icsprout55</name>
 <description>ICsprout 55nm LL/ULP</description>
 <dbu>0.001</dbu>
 <layer-properties_file>{escape(lyp_name)}</layer-properties_file>
 <reader-options>
  <common>
   <layer-map>{escape(lm_name)}</layer-map>
  </common>
 </reader-options>
</technology>
"""


def generate_crossref_md(
    entries: Iterable[LayerEntry],
    aliases: dict[tuple[int, int], object] | None = None,
) -> str:
    lines = [
        "# ICS55 layer cross-reference",
        "",
        "| PDK name | Purpose | GDS L/D | KLayout / Ruby | Calibre |",
        "|---|---|---|---|---|",
    ]
    for entry in entries:
        calibre = ""
        if aliases:
            layer = aliases.get((entry.gds_layer, entry.gds_datatype))
            if layer is not None:
                calibre = getattr(layer, "display", "")
        lines.append(
            f"| {entry.name} | {entry.purpose} | "
            f"{entry.gds_layer}/{entry.gds_datatype} | `{entry.ruby_name}` | "
            f"{calibre or '—'} |"
        )
    lines.append("")
    lines.append(
        "`Calibre` lists the foundry-deck names for that stream layer: the "
        "input binding from the TVF `LAYER MAP` (`ACTi`) and the derived "
        "working-layer alias (`AA`). `—` means the deck has no name for it."
    )
    lines.append("")
    return "\n".join(lines)


def write_tech_files(cfg: PdkConfig, out_dir: Path) -> dict[str, Path]:
    entries = parse_layermap(cfg.layermap)
    out_dir.mkdir(parents=True, exist_ok=True)
    if out_dir.name == "tech":
        layers_rb = out_dir.parent / "drc" / "01_layers.rb"
        docs_dir = out_dir.parent.parent / "docs"
    else:
        layers_rb = out_dir / "01_layers.rb"
        docs_dir = out_dir / "docs"
    layers_rb.parent.mkdir(parents=True, exist_ok=True)
    docs_dir.mkdir(parents=True, exist_ok=True)
    aliases = _calibre_aliases(cfg)
    paths = {
        "layers_rb": layers_rb,
        "lyp": out_dir / "icsprout55.lyp",
        "lyt": out_dir / "icsprout55.lyt",
        "lm": out_dir / "icsprout55.lm",
        "crossref": docs_dir / "layer_crossref.md",
    }
    layers_rb.write_text(generate_layers_rb(entries), encoding="utf-8")
    paths["lyp"].write_text(generate_lyp(entries), encoding="utf-8")
    paths["lyt"].write_text(generate_lyt(), encoding="utf-8")
    paths["lm"].write_text(generate_lm(entries), encoding="utf-8")
    paths["crossref"].write_text(
        generate_crossref_md(entries, aliases), encoding="utf-8"
    )
    return paths


def _calibre_aliases(cfg: PdkConfig) -> dict[tuple[int, int], object]:
    """Calibre layer names for the cross-reference; empty if the deck is absent."""
    from ics55_klayout_drc.calibre_golden import parse_layer_aliases

    deck = getattr(cfg, "calibre_drc", None)
    if not deck or not Path(deck).is_file():
        return {}
    try:
        return parse_layer_aliases(deck)
    except OSError:
        return {}


def _color(entry: LayerEntry) -> tuple[int, int, int]:
    digest = hashlib.md5(f"{entry.name}:{entry.purpose}".encode()).digest()
    return digest[0], digest[1], digest[2]
