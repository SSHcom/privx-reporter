#!/usr/bin/env python3
"""Create a run directory and seed baseline.previous.json from the prior run in index.json."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

RUNS_ROOT = Path("security-report/runs")
INDEX_PATH = Path("security-report/index.json")

SUBDIRS = ("sast", "sca", "secrets", "iac", "containers", "sbom")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: prepare_run.py <RUN_ID>", file=sys.stderr)
        return 2

    run_id = sys.argv[1]
    run_dir = RUNS_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    for name in SUBDIRS:
        (run_dir / name).mkdir(exist_ok=True)

    previous_path = run_dir / "baseline.previous.json"
    empty = {"findings": [], "generated_at": None}

    prior_run_id: str | None = None
    if INDEX_PATH.exists():
        index = json.loads(INDEX_PATH.read_text())
        candidate = index.get("latest_run_id")
        if isinstance(candidate, str) and candidate and candidate != run_id:
            prior_run_id = candidate

    if prior_run_id:
        prior_baseline = RUNS_ROOT / prior_run_id / "baseline.json"
        if prior_baseline.is_file():
            shutil.copy(prior_baseline, previous_path)
            print(f"[prepare-run] baseline.previous.json <= runs/{prior_run_id}/baseline.json")
            return 0

    previous_path.write_text(json.dumps(empty, indent=2) + "\n")
    print("[prepare-run] baseline.previous.json <= empty (first run)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
