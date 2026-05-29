#!/bin/bash

set -euo pipefail

if [ "$#" -ne 2 ]; then
  echo "Usage: ./audit_event.sh <records> <api-delay-ms>"
  exit 1
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/env.sh"

uv run sync-server-live-test \
  --source audit \
  --records "$1" \
  --api-delay-ms "$2"
