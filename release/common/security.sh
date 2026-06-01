#!/bin/sh
set -eu

REPORTER_HOME="${REPORTER_HOME:-$(pwd)}"
cd "$REPORTER_HOME"

if [ ! -x ".venv/bin/python" ]; then
  echo "FATAL: missing virtualenv at $REPORTER_HOME/.venv" >&2
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "FATAL: uv is required to apply security package pins" >&2
  exit 1
fi

# PyPI security pins applied after uv sync --frozen.
uv pip install --python .venv/bin/python \
  "urllib3==2.7.0" \
  "gitpython==3.1.50" \
  "pillow==12.2.0" \
  "tornado==6.5.5" \
  "protobuf==6.33.5" \
  "pyarrow==23.0.1" \
  "idna==3.15" \
  "python-dotenv==1.2.2"

.venv/bin/python - <<'PY'
import importlib.metadata as md

expected = {
    "urllib3": "2.7.0",
    "gitpython": "3.1.50",
    "pillow": "12.2.0",
    "tornado": "6.5.5",
    "protobuf": "6.33.5",
    "pyarrow": "23.0.1",
    "idna": "3.15",
    "python-dotenv": "1.2.2",
}

for name, version in expected.items():
    installed = md.version(name)
    if installed != version:
        raise SystemExit(f"security pin mismatch for {name}: expected {version}, got {installed}")

print("security package pins verified")
PY
