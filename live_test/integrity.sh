#!/bin/bash

set -euo pipefail

if [ "$#" -ne 0 ]; then
  echo "Usage: ./integrity.sh"
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"

uv run python -m live_test.integrity
