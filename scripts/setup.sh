#!/usr/bin/env bash
# Source this file (don't execute): `source scripts/setup.sh`
# Sets PYTHONPATH so the 6 VTI slide skills can import from each other.

# Resolve repo root (works whether sourced from repo root or scripts/)
if [ -n "${BASH_SOURCE[0]}" ]; then
  SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
else
  SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
fi
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
SKILLS_DIR="$REPO_ROOT/.claude/skills"

export PYTHONPATH="\
$SKILLS_DIR/vti-slide-creator:\
$SKILLS_DIR/vti-slide-page-builder:\
$SKILLS_DIR/vti-slide-decorator:\
$SKILLS_DIR/vti-slide-decorator/strategies:\
$SKILLS_DIR/vti-slide-diagram-builder:\
$SKILLS_DIR/vti-slide-pptx-exporter:\
$SKILLS_DIR/vti-slide-figma-mockup${PYTHONPATH:+:$PYTHONPATH}"

# Activate venv if exists and not already active
if [ -z "${VIRTUAL_ENV:-}" ] && [ -f "$REPO_ROOT/.venv/bin/activate" ]; then
  # shellcheck source=/dev/null
  source "$REPO_ROOT/.venv/bin/activate"
fi

# Warn about API key trap (Claude Code will use API instead of subscription if set)
if [ -n "${ANTHROPIC_API_KEY:-}" ]; then
  echo "⚠️  ANTHROPIC_API_KEY is set — Claude Code will charge API usage, not your Pro/Max sub."
  echo "    Run: unset ANTHROPIC_API_KEY"
fi

echo "✅ PYTHONPATH set to include 6 skill dirs"
echo "   Repo: $REPO_ROOT"
[ -n "$VIRTUAL_ENV" ] && echo "   venv: $VIRTUAL_ENV"
