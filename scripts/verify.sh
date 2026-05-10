#!/usr/bin/env bash
# Smoke test: import 3 skills và in version. Fail fast nếu không load được.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "$SCRIPT_DIR/setup.sh"

python3 - <<'PY'
import importlib, sys

failures = []

try:
    creator = importlib.import_module('creator')
    print(f"creator:      {creator.info()['version']}")
except Exception as e:
    failures.append(f"creator: {e}")
    print(f"❌ creator: {e}")

try:
    composer = importlib.import_module('composer_grid')
    print(f"page-builder: {composer.catalog()['version']}")
except Exception as e:
    failures.append(f"page-builder: {e}")
    print(f"❌ page-builder: {e}")

try:
    import decorator
    print(f"decorator:    {decorator.__version__}")
except Exception as e:
    failures.append(f"decorator: {e}")
    print(f"❌ decorator: {e}")

if failures:
    sys.exit(1)
print("\n✅ All 3 skills loaded successfully")
PY
