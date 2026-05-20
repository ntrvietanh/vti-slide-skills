#!/usr/bin/env bash
# Reset working state — wipes generated artifacts so you can re-run the
# pipeline from tests/inputs/ on a clean slate.
#
# Removes:
#   - work/*                       (preserves work/.gitkeep)
#   - scripts/*.py                 (all per-deck Python drivers)
#   - scripts/*.mjs                (per-deck JS helpers, if any)
#   - scripts/patches/*.py         (all per-deck patches)
#
# Patches + drivers are deck-specific (their content references the current
# deck's slides/topics/text). A reset is starting fresh on a new deck.
# Within ONE deck's lifecycle, don't reset — patches persist across Claude
# sessions because the files stay on disk.
#
# Does NOT touch (durable infra):
#   - scripts/*.sh                 (setup/verify/reset/session shell tools)
#   - scripts/patches/README.md    (patches contract doc)
#   - tests/inputs/                (original source files)
#   - tests/expected/              (regression references)
#   - .claude/skills/              (skill code, incl. render_mermaid.mjs)

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "Wiping work/ (preserving .gitkeep)..."
find work -mindepth 1 -not -path 'work/.gitkeep' -depth -exec rm -rf {} +

echo "Removing per-deck driver scripts..."
rm -fv scripts/*.py scripts/*.mjs 2>/dev/null || true

echo "Removing per-deck patches..."
rm -fv scripts/patches/*.py 2>/dev/null || true

echo
echo "Reset complete. tests/inputs/ untouched. Ready to start over."
