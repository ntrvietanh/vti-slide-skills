#!/usr/bin/env bash
# Snapshot current session state into sessions/<name>.zip.
#
# Includes:
#   - tests/inputs/                 (source files)
#   - work/                         (generated artifacts)
#   - scripts/build_phase_*.py      (per-session phase drivers, if present)
#   - scripts/ingest_*.py           (per-session ingest drivers, if present)
#
# Excludes: .DS_Store, __pycache__/, *.pyc
#
# Usage:
#   scripts/session_save.sh <session-name> [-f|--force]

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

usage() {
  echo "Usage: scripts/session_save.sh <session-name> [-f|--force]" >&2
  exit 2
}

NAME=""
FORCE=0

for arg in "$@"; do
  case "$arg" in
    -f|--force) FORCE=1 ;;
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

# Path traversal / sanity guard: no slashes, no leading dot, not ".." or "."
if [[ "$NAME" == *"/"* ]] || [[ "$NAME" == .* ]] || [ "$NAME" = ".." ]; then
  echo "Error: invalid session name '$NAME' (no slashes, no leading dots)." >&2
  exit 1
fi

mkdir -p sessions
TARGET="sessions/${NAME}.zip"

if [ -e "$TARGET" ] && [ "$FORCE" -ne 1 ]; then
  echo "Error: $TARGET already exists. Pass --force to overwrite." >&2
  exit 1
fi

# Collect existing paths to zip
PATHS=()
[ -d "tests/inputs" ] && PATHS+=("tests/inputs")
[ -d "work" ] && PATHS+=("work")
# Per-session driver scripts — use shopt nullglob so missing matches don't error
shopt -s nullglob
for f in scripts/build_phase_*.py scripts/ingest_*.py; do
  PATHS+=("$f")
done
shopt -u nullglob

if [ "${#PATHS[@]}" -eq 0 ]; then
  echo "Error: nothing to save — tests/inputs/ and work/ are both missing." >&2
  exit 1
fi

# Remove existing target if forcing (zip -r would otherwise append)
if [ -e "$TARGET" ]; then
  rm -f "$TARGET"
fi

echo "Saving session '$NAME' → $TARGET"
echo "Including:"
for p in "${PATHS[@]}"; do
  echo "  - $p"
done

zip -r -q "$TARGET" "${PATHS[@]}" \
  -x "*.DS_Store" "*/__pycache__/*" "*.pyc"

SIZE_HUMAN="$(du -h "$TARGET" | awk '{print $1}')"
ENTRY_COUNT="$(unzip -l "$TARGET" | tail -1 | awk '{print $2}')"

echo
echo "✅ Saved $TARGET (${SIZE_HUMAN}, ${ENTRY_COUNT} entries)"
