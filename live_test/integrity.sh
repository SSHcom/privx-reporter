#!/bin/bash

set -euo pipefail

if [ "$#" -ne 0 ]; then
  echo "Usage: ./integrity.sh"
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"
"$SCRIPT_DIR/verify_test_db.sh"

uv run --no-env-file python -m live_test.integrity
