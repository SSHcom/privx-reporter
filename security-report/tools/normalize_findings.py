#!/usr/bin/env python3
"""Normalize per-run scanner outputs into LLM-friendly JSON for PrivX Reporter."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

RUNS_ROOT = Path("security-report/runs")
INDEX_PATH = Path("security-report/index.json")


def classify_surface(path: str) -> str:
    p = path.replace("\\", "/")
    if "apps/python/ui/" in p or p.startswith("ui/"):
        return "ui"
    if "apps/python/lib/" in p or p.startswith("lib/") or "apps/python/administration/" in p:
        return "cli+ui-shared"
    if "apps/python/sync_server/" in p or p.startswith("sync_server/"):
        return "sync-internal"
    if p.startswith("release/"):
        return "deploy"
    return "other"


def norm_sev(value: str | None) -> str:
    s = (value or "info").lower()
    mapping = {"error": "high", "warning": "medium", "note": "low", "none": "info"}
    if s in mapping:
        return mapping[s]
    if s in {"critical", "high", "medium", "low", "info"}:
        return s
    return "info"


def stable_id(*parts: object) -> str:
    digest = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()[:16]
    return f"rep-{digest}"


def load_bandit(run_dir: Path, run_id: str) -> list[dict]:
    path = run_dir / "sast/bandit.json"
    if not path.exists() or path.stat().st_size <= 2:
        return []
    findings: list[dict] = []
    for row in json.loads(path.read_text()).get("results", []):
        file_path = row.get("filename", "")
        findings.append(
            {
                "id": stable_id("bandit", row.get("test_id"), file_path, row.get("line_number")),
                "tool": "bandit",
                "rule_id": row.get("test_id", ""),
                "title": (row.get("issue_text") or "")[:120],
                "description": row.get("issue_text", ""),
                "severity": norm_sev(row.get("issue_severity")),
                "category": "sast",
                "surface": classify_surface(file_path),
                "location": {
                    "path": file_path,
                    "line_start": row.get("line_number"),
                    "line_end": row.get("line_number"),
                    "snippet": (row.get("code") or "")[:200],
                },
                "first_seen_run": run_id,
                "last_seen_run": run_id,
                "status": "open",
            }
        )
    return findings


def load_semgrep(run_dir: Path, run_id: str) -> list[dict]:
    path = run_dir / "sast/semgrep.sarif"
    if not path.exists() or path.stat().st_size <= 10:
        return []
    findings: list[dict] = []
    sarif = json.loads(path.read_text())
    for run in sarif.get("runs", []):
        for result in run.get("results", []):
            physical = (result.get("locations") or [{}])[0].get("physicalLocation", {})
            file_path = physical.get("artifactLocation", {}).get("uri", "")
            region = physical.get("region", {})
            message = (result.get("message") or {}).get("text", "")
            rule_id = result.get("ruleId", "")
            level = (result.get("level") or "note").lower()
            severity = {"error": "high", "warning": "medium", "note": "low"}.get(level, "info")
            findings.append(
                {
                    "id": stable_id("semgrep", rule_id, file_path, region.get("startLine")),
                    "tool": "semgrep",
                    "rule_id": rule_id,
                    "title": message[:120],
                    "description": message,
                    "severity": severity,
                    "category": "sast",
                    "surface": classify_surface(file_path),
                    "location": {
                        "path": file_path,
                        "line_start": region.get("startLine"),
                        "line_end": region.get("endLine"),
                        "snippet": "",
                    },
                    "first_seen_run": run_id,
                    "last_seen_run": run_id,
                    "status": "open",
                }
            )
    return findings


def load_pip_audit(run_dir: Path, run_id: str) -> list[dict]:
    path = run_dir / "sca/pip-audit.json"
    if not path.exists() or path.stat().st_size <= 2:
        return []
    findings: list[dict] = []
    data = json.loads(path.read_text())
    for dep in data.get("dependencies", []):
        for vuln in dep.get("vulns", []):
            vuln_id = vuln.get("id", "")
            findings.append(
                {
                    "id": stable_id("pip-audit", dep.get("name"), vuln_id),
                    "tool": "pip-audit",
                    "rule_id": vuln_id,
                    "title": f"{dep.get('name')} {vuln_id}",
                    "description": (vuln.get("description") or "")[:500],
                    "severity": norm_sev(vuln.get("severity") or "medium"),
                    "cve": [vuln_id] if str(vuln_id).startswith("CVE") else [],
                    "category": "sca",
                    "surface": "supply-chain",
                    "package": {
                        "ecosystem": "pypi",
                        "name": dep.get("name"),
                        "version": dep.get("version"),
                        "fixed_versions": vuln.get("fix_versions", []),
                    },
                    "first_seen_run": run_id,
                    "last_seen_run": run_id,
                    "status": "open",
                }
            )
    return findings


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sbom_metadata(run_dir: Path, run_id: str) -> dict[str, str] | None:
    sbom_dir = run_dir / "sbom"
    cyclonedx = sbom_dir / "cyclonedx.json"
    spdx = sbom_dir / "spdx.json"
    if not cyclonedx.is_file() and not spdx.is_file():
        return None
    meta: dict[str, str] = {"run_id": run_id}
    if cyclonedx.is_file():
        meta["cyclonedx"] = cyclonedx.as_posix()
        if digest := _file_sha256(cyclonedx):
            meta["cyclonedx_sha256"] = digest
    if spdx.is_file():
        meta["spdx"] = spdx.as_posix()
        if digest := _file_sha256(spdx):
            meta["spdx_sha256"] = digest
    return meta


def _compute_delta(current: list[dict], previous: list[dict]) -> dict[str, int]:
    prev_ids = {item["id"] for item in previous}
    curr_ids = {item["id"] for item in current}
    prev_by_id = {item["id"]: item for item in previous}
    regressed = 0
    for item in current:
        prev = prev_by_id.get(item["id"])
        if prev is None:
            continue
        order = ["info", "low", "medium", "high", "critical"]
        if order.index(item["severity"]) > order.index(prev.get("severity", "info")):
            regressed += 1
    return {
        "new": len(curr_ids - prev_ids),
        "resolved": len(prev_ids - curr_ids),
        "persisting": len(curr_ids & prev_ids) - regressed,
        "regressed": regressed,
    }


def write_llm_brief(run_dir: Path, run_id: str, findings: list[dict]) -> None:
    severity = Counter(item["severity"] for item in findings)
    surface = Counter(item.get("surface", "?") for item in findings)
    lines = [
        f"# Security scan brief ({run_id})",
        "",
        f"Total findings: {len(findings)}",
        "",
        "## By severity",
        "",
    ]
    order = ["critical", "high", "medium", "low", "info"]
    for key in order:
        if severity.get(key):
            lines.append(f"- {key}: {severity[key]}")
    lines.extend(["", "## By surface", ""])
    for key, count in surface.most_common():
        lines.append(f"- {key}: {count}")
    lines.extend(["", "## Findings", ""])
    ranked = sorted(
        findings,
        key=lambda item: order.index(item["severity"]) if item["severity"] in order else 99,
    )
    for item in ranked[:50]:
        loc = item.get("location", {})
        lines.append(
            f"- [{item['severity']}] {item['tool']}/{item['rule_id']}: "
            f"{item['title'][:80]} @ {loc.get('path')}:{loc.get('line_start')} "
            f"(surface={item.get('surface')})"
        )
    (run_dir / "llm-brief.md").write_text("\n".join(lines) + "\n")


def _update_index(run_id: str, summary: dict[str, object]) -> None:
    run_dir = RUNS_ROOT / run_id
    rel = run_dir.as_posix()
    entry = {
        "run_id": run_id,
        "generated_at": summary.get("generated_at"),
        "finding_count": summary.get("finding_count"),
        "totals": summary.get("totals"),
        "by_surface": summary.get("by_surface"),
        "delta": summary.get("delta"),
        "dir": rel,
        "final_assessment": f"{rel}/FINAL_ASSESSMENT.md",
        "summary": f"{rel}/summary.json",
        "llm_brief": f"{rel}/llm-brief.md",
    }
    index: dict[str, object] = {"latest_run_id": run_id, "runs": []}
    if INDEX_PATH.exists():
        index = json.loads(INDEX_PATH.read_text())
    runs: list[dict] = [r for r in index.get("runs", []) if r.get("run_id") != run_id]
    runs.insert(0, entry)
    index["runs"] = runs
    index["latest_run_id"] = run_id
    INDEX_PATH.write_text(json.dumps(index, indent=2) + "\n")


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: normalize_findings.py <RUN_ID>", file=sys.stderr)
        return 2
    run_id = sys.argv[1]
    run_dir = RUNS_ROOT / run_id
    if not run_dir.is_dir():
        print(f"missing run dir: {run_dir}", file=sys.stderr)
        return 2

    findings = load_bandit(run_dir, run_id) + load_semgrep(run_dir, run_id) + load_pip_audit(run_dir, run_id)
    deduped = {item["id"]: item for item in findings}
    findings = list(deduped.values())

    generated_at = datetime.now(timezone.utc).isoformat()
    (run_dir / "findings.json").write_text(
        json.dumps({"run_id": run_id, "findings": findings}, indent=2) + "\n"
    )

    previous: list[dict] = []
    prev_path = run_dir / "baseline.previous.json"
    if prev_path.exists():
        previous = json.loads(prev_path.read_text()).get("findings", [])
    elif INDEX_PATH.exists():
        index = json.loads(INDEX_PATH.read_text())
        prior_run_id = index.get("latest_run_id")
        if isinstance(prior_run_id, str) and prior_run_id and prior_run_id != run_id:
            prior_baseline = RUNS_ROOT / prior_run_id / "baseline.json"
            if prior_baseline.is_file():
                previous = json.loads(prior_baseline.read_text()).get("findings", [])

    summary: dict[str, object] = {
        "run_id": run_id,
        "generated_at": generated_at,
        "project": "reporter-privx-dev",
        "totals": dict(Counter(item["severity"] for item in findings)),
        "by_surface": dict(Counter(item.get("surface", "?") for item in findings)),
        "finding_count": len(findings),
        "delta": _compute_delta(findings, previous),
    }
    if sbom := _sbom_metadata(run_dir, run_id):
        summary["sbom"] = sbom

    (run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    (run_dir / "baseline.json").write_text(
        json.dumps({"generated_at": generated_at, "findings": findings}, indent=2) + "\n"
    )
    write_llm_brief(run_dir, run_id, findings)
    _update_index(run_id, summary)
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
