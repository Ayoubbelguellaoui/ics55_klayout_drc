"""Load ICS55 PDK-aware configuration."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PACKAGE_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = PACKAGE_ROOT / "config" / "ics55.pdk.yml"

VALID_METAL_COMBINATIONS = frozenset(
    {
        (4, 1, 0, 1, 0, 0, 0, 0),
        (4, 1, 0, 0, 0, 1, 0, 0),
        (4, 1, 0, 0, 0, 0, 0, 1),
        (5, 1, 0, 1, 0, 0, 0, 0),
        (5, 1, 0, 0, 0, 1, 0, 0),
        (5, 1, 0, 0, 0, 0, 0, 1),
        (6, 1, 0, 1, 0, 0, 0, 0),
        (6, 1, 0, 0, 0, 1, 0, 0),
        (6, 1, 0, 0, 0, 0, 0, 1),
        (7, 1, 0, 1, 0, 0, 0, 0),
        (7, 1, 0, 0, 0, 1, 0, 0),
        (7, 1, 0, 0, 0, 0, 0, 1),
        (8, 1, 0, 1, 0, 0, 0, 0),
        (8, 1, 0, 0, 0, 1, 0, 0),
        (8, 1, 0, 0, 0, 0, 0, 1),
        (9, 1, 0, 1, 0, 0, 0, 0),
        (9, 1, 0, 0, 0, 1, 0, 0),
        (9, 1, 0, 0, 0, 0, 0, 1),
        (5, 2, 1, 1, 0, 0, 0, 0),
        (5, 2, 1, 0, 0, 1, 0, 0),
        (5, 2, 1, 0, 0, 0, 0, 1),
        (5, 2, 0, 0, 1, 1, 0, 0),
        (5, 2, 0, 0, 1, 0, 0, 1),
        (5, 2, 0, 0, 0, 0, 1, 1),
        (6, 2, 1, 1, 0, 0, 0, 0),
        (6, 2, 1, 0, 0, 1, 0, 0),
        (6, 2, 1, 0, 0, 0, 0, 1),
        (6, 2, 0, 0, 1, 1, 0, 0),
        (6, 2, 0, 0, 1, 0, 0, 1),
        (6, 2, 0, 0, 0, 0, 1, 1),
        (7, 2, 1, 1, 0, 0, 0, 0),
        (7, 2, 1, 0, 0, 1, 0, 0),
        (7, 2, 1, 0, 0, 0, 0, 1),
        (7, 2, 0, 0, 1, 1, 0, 0),
        (7, 2, 0, 0, 1, 0, 0, 1),
        (7, 2, 0, 0, 0, 0, 1, 1),
        (8, 2, 1, 1, 0, 0, 0, 0),
        (8, 2, 1, 0, 0, 1, 0, 0),
        (8, 2, 1, 0, 0, 0, 0, 1),
        (8, 2, 0, 0, 1, 1, 0, 0),
        (8, 2, 0, 0, 1, 0, 0, 1),
        (8, 2, 0, 0, 0, 0, 1, 1),
        (9, 2, 1, 1, 0, 0, 0, 0),
        (9, 2, 1, 0, 0, 1, 0, 0),
        (9, 2, 1, 0, 0, 0, 0, 1),
        (9, 2, 0, 0, 1, 1, 0, 0),
        (9, 2, 0, 0, 1, 0, 0, 1),
        (9, 2, 0, 0, 0, 0, 1, 1),
        (10, 2, 1, 1, 0, 0, 0, 0),
        (10, 2, 1, 0, 0, 1, 0, 0),
        (10, 2, 1, 0, 0, 0, 0, 1),
        (10, 2, 0, 0, 1, 1, 0, 0),
        (10, 2, 0, 0, 1, 0, 0, 1),
        (10, 2, 0, 0, 0, 0, 1, 1),
    }
)

STACK_KEYS = (
    "total_metal",
    "top_metal",
    "T2V1_T2M1",
    "T2V2_T2M2",
    "T4V1_T4M1",
    "T4V2_T4M2",
    "T8V1_T8M1",
    "T8V2_T8M2",
)


@dataclass
class PdkConfig:
    pdk_root: Path
    layermap: Path
    calibre_drc: Path
    drm: Path
    techlef: Path
    dbu_nm: int = 1
    io: int = 1833
    stack: dict[str, int] = field(default_factory=dict)
    switches: dict[str, bool] = field(default_factory=dict)
    source: Path | None = None

    def stack_tuple(self) -> tuple[int, ...]:
        return tuple(int(self.stack[key]) for key in STACK_KEYS)

    def validate_stack(self) -> None:
        combo = self.stack_tuple()
        if combo not in VALID_METAL_COMBINATIONS:
            raise ValueError(
                "invalid ICS55 metal option combination "
                f"{dict(zip(STACK_KEYS, combo, strict=True))}"
            )


def load_pdk_config(
    path: str | Path | None = None,
    *,
    pdk_root: str | Path | None = None,
) -> PdkConfig:
    config_path = Path(path) if path else DEFAULT_CONFIG
    data = _read_yaml(config_path)
    root = _resolve_pdk_root(pdk_root, data.get("pdk_root"), config_path)
    cfg = PdkConfig(
        pdk_root=root,
        layermap=_resolve_under(root, data.get("layermap", "techfile/icsprout55.layermap")),
        calibre_drc=_resolve_under(
            root, data.get("calibre_drc", "pv/DRC/ICsprout_CalDRC_55LLULP1233_REV1_0_OS.drc")
        ),
        drm=_resolve_under(root, data.get("drm", "docs/ZJCX 55nm Design Rule Manual_V1.1.9.pdf")),
        techlef=_resolve_under(root, data.get("techlef", "prtech/techLEF/N551P6M.lef")),
        dbu_nm=int(data.get("dbu_nm", 1)),
        io=int(data.get("io", 1833)),
        stack={key: int(data.get("stack", {}).get(key, 0)) for key in STACK_KEYS},
        switches={str(k): bool(v) for k, v in dict(data.get("switches") or {}).items()},
        source=config_path,
    )
    if not cfg.stack.get("total_metal"):
        cfg.stack["total_metal"] = 6
    if "top_metal" not in cfg.stack or cfg.stack["top_metal"] not in (1, 2):
        cfg.stack["top_metal"] = 1
    if not any(cfg.stack[k] for k in STACK_KEYS[2:]):
        cfg.stack["T4V2_T4M2"] = 1
    cfg.validate_stack()
    return cfg


def _resolve_pdk_root(
    override: str | Path | None,
    configured: Any,
    config_path: Path,
) -> Path:
    env = os.environ.get("CHIPCOMPILER_ICS55_PDK_ROOT")
    if override is not None:
        path = Path(str(override)).expanduser()
        return path if path.is_absolute() else path.resolve()
    if env:
        path = Path(env).expanduser()
        return path if path.is_absolute() else path.resolve()
    if not configured:
        raise ValueError("pdk_root is required")
    path = Path(str(configured)).expanduser()
    if not path.is_absolute():
        path = (config_path.parent / path).resolve()
    return path


def _resolve_under(root: Path, rel: Any) -> Path:
    path = Path(str(rel))
    return path if path.is_absolute() else root / path


def _read_yaml(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore

        data = yaml.safe_load(text) or {}
        if not isinstance(data, dict):
            raise ValueError(f"{path} is not a mapping")
        return data
    except ImportError:
        return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    """Minimal YAML subset used by config/ics55.pdk.yml (no extra dependency)."""
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(0, root)]
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        key, _, rest = line.strip().partition(":")
        value = rest.strip()
        while stack and indent < stack[-1][0]:
            stack.pop()
        current = stack[-1][1]
        if value == "":
            nested: dict[str, Any] = {}
            current[key] = nested
            stack.append((indent + 2, nested))
        else:
            current[key] = _coerce(value)
    return root


def _coerce(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    try:
        return int(value)
    except ValueError:
        return value
