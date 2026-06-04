#!/bin/bash

set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: ./connection.sh <records> <api-delay-ms>"
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"
"$SCRIPT_DIR/verify_test_db.sh"

uv run --no-env-file sync-server-live-test \
  --source connection \
  --records "$1" \
  --api-delay-ms "$2"
