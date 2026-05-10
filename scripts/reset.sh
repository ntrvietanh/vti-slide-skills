#!/usr/bin/env bash
# Reset working state — wipes generated artifacts so you can re-run the
# pipeline from tests/inputs/ on a clean slate.
#
# Removes:
#   - work/*                       (preserves work/.gitkeep)
#   - scripts/build_phase_*.py     (per-session phase driver scripts)
#   - scripts/ingest_*.py          (per-session ingest driver scripts)
#
# Does NOT touch:
#   - tests/inputs/                (original source files)
#   - tests/expected/              (regression references)
#   - .claude/skills/              (skill code)
#   - scripts/setup.sh, scripts/verify.sh, scripts/reset.sh

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "Wiping work/ (preserving .gitkeep)..."
find work -mindepth 1 -not -path 'work/.gitkeep' -depth -exec rm -rf {} +

echo "Removing per-session driver scripts..."
rm -fv scripts/build_phase_*.py scripts/ingest_*.py 2>/dev/null || true

echo
echo "Reset complete. tests/inputs/ untouched. Ready to start over."
