# scripts/patches/

Durable hand-edits to phase outputs.

## Why

`scripts/build_phase_N.py` regenerates `work/phase_N.json` deterministically
from the previous phase. Any hand-edits to `phase_N.json` are lost on the
next re-run. Patches live here so they survive re-runs.

## Contract

- File naming: `phase{N}_{NN}_{slug}.py` (sorted lexically → execution order).
- Each patch is a standalone Python script that mutates
  `work/phase_{N}.json` in place.
- **Patches must be idempotent** — running them twice must equal once.
  Use sentinel checks like `kind_hint` on appended rows, or `if cell.component != "X"` guards on replaced cells.
- Patches receive PYTHONPATH set by `scripts/setup.sh` (skill modules importable).
- `scripts/build_phase_{N}.py` auto-runs `phase{N}_*.py` at the end of the build.

## Editing slides without losing work

1. Do not edit `work/phase_N.json` directly.
2. Author a patch script here (or extend an existing one).
3. Re-run `scripts/build_phase_{N}.py` — patches re-apply.
4. Run `scripts/build_phase_{N+1}.py` … through to `build_phase_6.py` to compose.

## Current patches

- `phase5_01_slides_7_18_19.py` — slide 7 (4 `practice-card-leveled`),
  slide 18 (bottom kpi-row + callout), slide 19 (bottom quote + tags).
