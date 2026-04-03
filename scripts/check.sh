#!/usr/bin/env bash
# Run all code quality checks.
# Usage:
#   ./scripts/check.sh          # check + test
#   ./scripts/check.sh --fix    # auto-format then check + test

set -euo pipefail

FIX=false
for arg in "$@"; do
  [[ "$arg" == "--fix" ]] && FIX=true
done

echo "=== black ==="
if $FIX; then
  uv run black backend/ main.py
else
  uv run black --check backend/ main.py
fi

echo ""
echo "=== pytest ==="
uv run pytest

echo ""
echo "All checks passed."
