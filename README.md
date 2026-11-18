# ics55_klayout_drc

Open-source KLayout native DRC for the ICS55 55nm PDK: full-mask physical
verification, foundry-rule mapping, independent regression tests, and a native
ECC (ECOS Chip Compiler) `mask_drc` stage.

The existing ECC `drc` step (ecc-tools / tech LEF) is **not** replaced.

## Status

Phases 1-3 are implemented; ECC integration and Calibre golden ingestion follow.

- Reads `icsprout55.layermap` and generates `klayout/drc/01_layers.rb`,
  `klayout/tech/icsprout55.lyp`, and `icsprout55.lyt`
- 185 rule checks on the default stack (front-end, thin metal, via, thick
  metal, pad/RDL, density, slot, chip-edge, eFuse)
- Python CLI `ics55-drc run` with RDB, JSON, CSV, HTML, and ECC-compatible
  `violation_map.json` outputs
- Default stack: 1P6M + T4M2 (`total_metal=6`, `top_metal=1`, `T4V2_T4M2=1`)

Latch-up, MOM, ESD, and dummy-fill families are gated and currently recorded as
notes; they need connectivity/marker semantics from later phases.

## Setup

Point `pdk_root` at a checkout of
[icsprout55-pdk](https://github.com/openecos-projects/icsprout55-pdk)
(`config/ics55.pdk.yml`, `--pdk-root`, or `CHIPCOMPILER_ICS55_PDK_ROOT`).

```bash
python3 -m pip install -e .
make generate-tech PDK_ROOT=/path/to/icsprout55-pdk
make test
```

Without installing, prefix commands with `PYTHONPATH=src`.

```bash
ics55-drc generate-tech --pdk-root /path/to/icsprout55-pdk
```

## Run full-mask DRC

```bash
ics55-drc run \
  --input chip.gds \
  --top TOP \
  --out reports/chip \
  --config config/ics55.pdk.yml
```

Options:

- `--stack 1P6M1TM` or `--stack total_metal=6,top_metal=1,T4V2_T4M2=1`
- `--klayout /path/to/klayout` (or `KLAYOUT`)
- `--recommended on|off`, `--density on|off` / `--no-density`
- `--latchup`, `--dup`, `--metal-slot`, `--mom`, `--esd`, `--poly-efuse`,
  `--chipedge`, `--allow-v01`

Exit codes: `0` clean, `1` mandatory violations, `2` engine/input/config error.

## Outputs

| File | Role |
|---|---|
| `drc.lyrdb` | KLayout Marker Browser database |
| `drc_summary.json` | Counts by rule / class |
| `drc_summary.csv` | Spreadsheet summary |
| `drc_report.html` | Human-readable report |
| `violation_map.json` | ECC list schema (`type`, `shape[4]=layer`, `bbox`) |
| `drc_violations.jsonl` | Streaming markers, one JSON object per line |
| `drc.log` | Command, KLayout version, engine output |

## Golden comparison

`compare` diffs rule-ID presence between a KLayout summary and a golden JSON
summary; count deltas are reported separately. Missing/unavailable golden files
exit `0` with `golden=skipped`.

```bash
ics55-drc compare \
  --klayout reports/chip/drc_summary.json \
  --calibre calibre_summary.json \
  --json reports/chip/compare.json
```

Calibre RDB/TVF ingestion and documented known deltas land in Phase 5.

## Layout

```text
config/ics55.pdk.yml       PDK paths, stack, switches
klayout/drc/               KLayout Ruby deck
klayout/tech/              generated LYP/LYT
docs/layer_crossref.md     PDK ↔ GDS ↔ Ruby names
src/ics55_klayout_drc/     CLI, engine, reports, compare
tests/                     stdlib unittest suite
```

The PDK checkout stays read-only; this repository references it instead of
copying proprietary rule files.
