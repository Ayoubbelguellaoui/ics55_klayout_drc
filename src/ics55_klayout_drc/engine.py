"""Run the KLayout full-mask DRC deck in batch mode."""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ics55_klayout_drc.pdk import PACKAGE_ROOT, PdkConfig

DECK_PATH = PACKAGE_ROOT / "klayout" / "drc" / "ics55_full_mask.drc"

SWITCH_KEYS = (
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


class EngineError(RuntimeError):
    """The KLayout engine could not be located or the deck failed."""


@dataclass
class RunResult:
    status: str
    exit_code: int
    command: list[str]
    report: Path
    summary: Path
    violations: Path
    log: Path
    summary_data: dict = field(default_factory=dict)
    stdout: str = ""
    stderr: str = ""

    @property
    def violation_count(self) -> int:
        return int(self.summary_data.get("violations") or 0)

    @property
    def rules_with_violations(self) -> int:
        return int(self.summary_data.get("rules_with_violations") or 0)


def find_klayout(explicit: str | Path | None = None) -> str:
    candidates = [explicit, os.environ.get("KLAYOUT"), shutil.which("klayout")]
    for candidate in candidates:
        if not candidate:
            continue
        path = Path(str(candidate)).expanduser()
        if path.is_file():
            return str(path)
    raise EngineError(
        "klayout executable not found; set KLAYOUT or install KLayout (>= 0.28)"
    )


def _tool_version(executable: str) -> str:
    try:
        proc = subprocess.run(
            [executable, "-v"], capture_output=True, text=True, check=False
        )
        text = (proc.stdout or proc.stderr).strip()
        return text.splitlines()[0] if text else "unknown"
    except OSError:
        return "unknown"


def deck_options(cfg: PdkConfig, overrides: dict | None = None) -> dict:
    options: dict = {
        "total_metal": cfg.stack["total_metal"],
        "top_metal": cfg.stack["top_metal"],
        "T2V1_T2M1": cfg.stack["T2V1_T2M1"],
        "T2V2_T2M2": cfg.stack["T2V2_T2M2"],
        "T4V1_T4M1": cfg.stack["T4V1_T4M1"],
        "T4V2_T4M2": cfg.stack["T4V2_T4M2"],
        "T8V1_T8M1": cfg.stack["T8V1_T8M1"],
        "T8V2_T8M2": cfg.stack["T8V2_T8M2"],
        "io": cfg.io,
    }
    for key in SWITCH_KEYS:
        if key in cfg.switches:
            options[key] = bool(cfg.switches[key])
    if overrides:
        options.update(overrides)
    return options


def run_drc(
    input_path: str | Path,
    out_dir: str | Path,
    cfg: PdkConfig,
    *,
    top: str | None = None,
    klayout: str | Path | None = None,
    overrides: dict | None = None,
) -> RunResult:
    input_path = Path(input_path).expanduser().resolve()
    if not input_path.is_file():
        raise EngineError(f"input layout not found: {input_path}")
    if not DECK_PATH.is_file():
        raise EngineError(
            f"DRC deck not found: {DECK_PATH} (run 'ics55-drc generate-tech' first)"
        )

    out_dir = Path(out_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    report = out_dir / "drc.lyrdb"
    summary = out_dir / "drc_summary.json"
    violations = out_dir / "drc_violations.jsonl"
    log = out_dir / "drc.log"
    for stale in (report, summary, violations, log):
        stale.unlink(missing_ok=True)

    executable = find_klayout(klayout)
    command = [
        executable,
        "-b",
        "-r",
        str(DECK_PATH),
        "-rd",
        f"input={input_path}",
        "-rd",
        f"report={report}",
        "-rd",
        f"summary={summary}",
        "-rd",
        f"violations={violations}",
    ]
    if top:
        command += ["-rd", f"top={top}"]
    for key, value in deck_options(cfg, overrides).items():
        if isinstance(value, bool):
            value = "true" if value else "false"
        command += ["-rd", f"{key}={value}"]

    proc = subprocess.run(command, capture_output=True, text=True, check=False)
    version = _tool_version(executable)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log.write_text(
        f"# ics55-drc run {started}\n"
        f"# klayout: {version}\n"
        f"$ {' '.join(command)}\n\n"
        + proc.stdout
        + proc.stderr,
        encoding="utf-8",
    )

    summary_data: dict = {}
    if summary.is_file():
        try:
            loaded = json.loads(summary.read_text(encoding="utf-8"))
            summary_data = loaded if isinstance(loaded, dict) else {}
        except (OSError, json.JSONDecodeError):
            summary_data = {}

    failed = proc.returncode != 0 or not summary_data
    if failed:
        detail = (proc.stderr or proc.stdout).strip().splitlines()
        tail = detail[-1] if detail else "no engine output"
        raise EngineError(f"KLayout DRC failed: {tail} (see {log})")

    if summary_data.get("violations"):
        status, exit_code = "violations", 1
    else:
        status, exit_code = "clean", 0

    return RunResult(
        status=status,
        exit_code=exit_code,
        command=command,
        report=report,
        summary=summary,
        violations=violations,
        log=log,
        summary_data=summary_data,
        stdout=proc.stdout,
        stderr=proc.stderr,
    )
