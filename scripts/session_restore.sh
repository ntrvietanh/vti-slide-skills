#!/usr/bin/env bash
# Restore a saved session: wipe current tests/inputs/, work/, and per-session
# driver scripts, then unzip sessions/<name>.zip back into place.
#
# Usage:
#   scripts/session_restore.sh <session-name> [-y|--yes]
#
# <session-name> can be passed with or without the .zip suffix.

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

usage() {
  echo "Usage: scripts/session_restore.sh <session-name> [-y|--yes]" >&2
  exit 2
}

list_sessions() {
  echo "Available sessions in sessions/:" >&2
  shopt -s nullglob
  local found=0
  for z in sessions/*.zip; do
    echo "  - $(basename "$z" .zip)" >&2
    found=1
  done
  shopt -u nullglob
  if [ "$found" -eq 0 ]; then
    echo "  (none)" >&2
  fi
}

NAME=""
ASSUME_YES=0

for arg in "$@"; do
  case "$arg" in
    -y|--yes) ASSUME_YES=1 ;;
    -h|--help) usage ;;
    -*) echo "Unknown flag: $arg" >&2; usage ;;
    *)
      if [ -z "$NAME" ]; then
        NAME="$arg"
      else
        echo "Multiple session names supplied: '$NAME' and '$arg'" >&2
        usage
      fi
      ;;
  esac
done

if [ -z "$NAME" ]; then
  echo "Error: session name is required." >&2
  usage
fi

# Strip optional .zip suffix for the validation check
NAME_BARE="${NAME%.zip}"

if [[ "$NAME_BARE" == *"/"* ]] || [[ "$NAME_BARE" == .* ]] || [ "$NAME_BARE" = ".." ]; then
  echo "Error: invalid session name '$NAME' (no slashes, no leading dots)." >&2
  exit 1
fi

ZIP="sessions/${NAME_BARE}.zip"

if [ ! -f "$ZIP" ]; then
  echo "Error: $ZIP not found." >&2
  list_sessions
  exit 1
fi

echo "About to restore session '$NAME_BARE' from $ZIP."
echo "This will WIPE the following before extracting:"
echo "  - tests/inputs/ (all contents)"
echo "  - work/ (all contents, preserving .gitkeep)"
echo "  - scripts/build_phase_*.py and scripts/ingest_*.py"

if [ "$ASSUME_YES" -ne 1 ]; then
  printf "Continue? [y/N] "
  read -r REPLY
  case "$REPLY" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; exit 1 ;;
  esac
fi

echo
echo "Wiping work/ (preserving .gitkeep)..."
if [ -d work ]; then
  find work -mindepth 1 -not -path 'work/.gitkeep' -depth -exec rm -rf {} +
fi

echo "Wiping tests/inputs/..."
if [ -d tests/inputs ]; then
  find tests/inputs -mindepth 1 -depth -exec rm -rf {} +
fi

echo "Removing per-session driver scripts..."
rm -f scripts/build_phase_*.py scripts/ingest_*.py 2>/dev/null || true

echo
echo "Extracting $ZIP..."
unzip -o -q "$ZIP" -d .

ENTRY_COUNT="$(unzip -l "$ZIP" | tail -1 | awk '{print $2}')"

echo
echo "✅ Restored session '$NAME_BARE' (${ENTRY_COUNT} entries extracted)"
