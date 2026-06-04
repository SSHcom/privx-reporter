# PrivX Reporter security scan (production-focused)

Task specification for scanning **this repository** with emphasis on how Reporter runs in production. It is derived from [GENERIC_SECURITY_SCAN.md](./GENERIC_SECURITY_SCAN.md) but narrows scope, tooling, and triage to PrivX Reporter deployment surfaces.

Use this file instead of the generic prompt when assessing Reporter. Keep the generic file as a reference for full multi-language baselines elsewhere.

### Usage

Hand this file to a coding agent as the task instruction:

> Execute `docs/llm/REPORTER_SECURITY_SCAN.md` for the current tree, then draft or update `security-report/runs/<RUN_ID>/FINAL_ASSESSMENT.md` per section 8.

Re-runs are idempotent except for timestamps and `last_seen_run`.

---

## 0. Production threat model (read first)

Reporter in production has **two user-facing surfaces** and several **internal** components.

### In scope for security assessment

| Surface | How it is deployed                                                                                                                                                                                                                                                                                       | Trust model                                                                                                                      | Primary risks                                                                                                                                                                                                                             |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **UI**  | Image `privxsshcom/privx-reporter-ui` built from `release/reporter_ui/Dockerfile-ui`; started via `release/common/bin/ui` (symlinked as `reporter-ui`, Streamlit on `0.0.0.0:8501`, optional TLS via `SSL_CERT` / `SSL_KEY`). Compose: `release/reporter_ui/docker-compose-ui.yml` or UI service in `release/reporter_cli/docker-compose.yml`. Session cookies use the Streamlit custom component at `ui/custom/cookie/` (bundled JS only in prod; see below). | **Untrusted network users** may reach the UI if the port is exposed. Authenticated users run reports with DB-scoped permissions. | Auth bypass, session fixation, OIDC misconfiguration, IDOR on report output paths, SQL injection via UI inputs, secrets in env/volumes, dependency CVEs in the UI image, **browser-side cookie component** (`frontend/build` bundle served to clients). |
| **CLI** | Installer image `privxsshcom/privx-reporter-cli` (`release/reporter_cli/Dockerfile-cli` + `release/reporter_cli/install.sh`); host commands `report`, `admin`, `create_env`, `backup` under `/opt/reporter`. Security pins: `release/common/security.sh` after `uv sync`.                                | **Trusted operators** only. Misuse via CLI is treated as an organisational control issue, not an external attacker model.        | Supply-chain (deps, installer), credential handling on disk, backup/subprocess safety, PrivX API credential exposure in `.env`. Still scan for accidental foot-guns, but **deprioritize** findings that require shell access on the host. |

Shared code paths: `lib/`, `reports/`, `administration/` (used by CLI and UI). Tag findings on these as `cli+ui-shared`; only count as **UI-reachable** if the same code is invoked from `ui/services/` without an additional trusted gate.

### Database bootstrap and migrations (UI + sync)

Migrations are **in scope for the UI deployment** even though end users never call them from the browser. They are **not** part of the per-request Streamlit path.

**Startup sequence (production and dev)**

```text
release/common/bin/ui  |  bin/serve_ui
  |
  +-- python -c "from ui.bootstrap import main; main()"
  |     configure_logging()
  |     configure_database()
  |       init_databases()                    # lib/database/db_init.py
  |         apply_migrations()                # administration/migration
  |         seed audit_event_sync (CSV)
  |       sync_reports_from_config()          # ui/db/init/*
  |       sync_admin_group / sync_default_oidc_group / sync_admin_user
  |
  +-- streamlit run ui/app.py
        configure_logging(force=True) only
        init_session_state() -> login or home pages
        (does NOT call init_databases() or apply_migrations())
```

**Also runs `init_databases()` (same migration chain)**

- `sync_server/main.py` on sync container start
- Some `administration/sync/*` modules when invoked from CLI/admin workflows

**When migrations execute**

- Once per **process start** of UI or sync, before serving traffic (UI) or entering the sync loop.
- Only **pending** scripts (tracked in admin DB `migration_history`) are applied; already-applied files are skipped.
- Restarting the UI container re-runs bootstrap; it does not re-apply completed migrations unless history is reset or new migration files ship.

**How to triage SAST on `administration/migration/`**

| Question | Guidance |
| -------- | -------- |
| Can an unauthenticated HTTP client trigger this SQL? | No, unless code is later wired from Streamlit pages into `apply_migrations()`. |
| Can an authenticated UI user trigger it per click? | No; not via `ui/app.py` or page handlers today. |
| Who can influence migration SQL content? | Deploy-time: env (e.g. `SYNC_AUDIT`, `SYNC_CONNECTION` parsed by `parse_retention_days()` in `lib/env_sync.py`), new migration files in releases, compromise of UI/sync image or host. |
| Example: Bandit SQLi in `2026-04-17-create-all-tables.py` | f-strings embed **int** retention days from env parsing, not request parameters. Classify as **deploy/config trust** or hardening (parameterized SQL), not as login-form SQLi. |
| Tag in `findings.json` | `surface`: `cli+ui-shared` or `sync-internal`; set `production_relevance` in `FINAL_ASSESSMENT.md` using the table above. |

Document this bootstrap boundary in `FINAL_ASSESSMENT.md` section 2 (attack surfaces) so migration findings are not dismissed as "CLI install only" or overstated as "every UI request runs migrations."

### UI session cookie component (`ui/custom/cookie/`)

The UI writes session cookies through a small Streamlit custom component (Vite + TypeScript). This is the **only** JavaScript/npm subtree in the repo.

| Path | Role |
| ---- | ---- |
| `ui/custom/cookie/__init__.py` | Python wrapper; loads component from `frontend/build` in production |
| `ui/custom/cookie/frontend/build/` | **Production runtime assets** (committed bundle: `index.html`, hashed `assets/*.js`) shipped in the UI image via `COPY apps/python/ui/ ui/` |
| `ui/custom/cookie/frontend/src/` | Dev/build source; not executed in production unless rebuilt into `build/` |
| `ui/custom/cookie/frontend/package.json`, `package-lock.json` | Lockfile for building the bundle; use for **optional** `npm audit` |
| `ui/custom/cookie/frontend/node_modules/` | **Gitignored** (`frontend/.gitignore`); not in the repo; exclude from filesystem scans |

**Production behavior** (`ui/custom/cookie/__init__.py`):

- Default: `components.declare_component(..., path=frontend/build)` — no Node runtime in the container.
- Dev only: if `COOKIE_COMPONENT_DEV_URL` is set, Streamlit loads the component from that URL (Vite dev server); must not be set in production images.

**Scan implications**

- Treat **`frontend/build/**/*.js`** as user-facing UI attack surface (cookie read/write in the browser).
- Do not expect `node_modules/` to exist; do not fail scans because it is missing.
- Rebuild and commit `frontend/build` after changing `src/` or npm deps before release; assess supply chain via `package-lock.json`, not via installed `node_modules`.
- Optional: `npm audit --package-lock-only` in `ui/custom/cookie/frontend/` (no install required).

### Out of scope for external attack surface (still scan lightly for supply chain)

| Component          | Notes                                                                                                                                                                                                                                                                                        |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Sync server**    | `release/reporter_sync/Dockerfile-sync`, `apps/python/sync_server/`. No HTTP/API surface for end users; pulls from PrivX and writes to DB on an internal Docker network. Do not open Jira tickets for "remote unauthenticated RCE on sync" unless you prove network exposure beyond the compose network. |
| **Backup sidecar** | `Dockerfile-backup` in standalone compose; operational, not user-facing.                                                                                                                                                                                                                     |
| **Dev-only**       | `bin/serve_ui`, tests, `live_test/`, local `.venv`. Exclude from SAST paths unless checking for committed secrets.                                                                                                                                                                           |

Operational docs to cross-check while writing `FINAL_ASSESSMENT.md`:

- [Standalone installation](../operations/install/STANDALONE.md)
- [UI admin guide](../operations/UI_ADMIN_GUIDE.md)
- [OIDC UI auth](../operations/OIDC_UI_AUTH_GUIDE.md)
- [Environment variables](../operations/ENVIRONMENT_VARIABLES.md)
- [PrivX API permissions](../operations/PRIVX_PERMISSIONS.md)

---

## 1. Operating principles

Same as the generic scan, with Reporter-specific additions:

1. **Read-only on source.** Artefacts only under `security-report/`.
2. **No telemetry** beyond what vulnerability scanners need (registries, OSV, NVD).
3. **Do not fabricate findings.**
4. **Prefer LLM-readable outputs** (`findings.json`, `summary.json`, `llm-brief.md`). HTML reports (`tickets.html`, `diff.html`) are optional human views; agents should read JSON/Markdown first.
5. **Tag every normalized finding** with `surface`: `ui` | `cli+ui-shared` | `sync-internal` | `deploy` | `supply-chain` | `other`.
6. **Apply production relevance** in `FINAL_ASSESSMENT.md` (section 8), not in raw scanner output.

---

## 2. Output layout

Only `tools/` is shared across runs. **Every scan run** gets its own directory under `runs/<RUN_ID>/` so you can compare multiple assessments on disk.

```
security-report/
  index.json                    # catalogue of all runs (tracked)
  tools/
    prepare_run.py              # mkdir run tree; seed baseline.previous.json
    normalize_findings.py       # merge tool output; update index.json
  triage.json                   # optional cross-run suppressions (tracked if used)
  runs/
    .gitignore                  # intermediate artefacts only (date wildcards)
    <RUN_ID>/                   # UTC ISO8601, e.g. 2026-06-02T08-26-33Z
      FINAL_ASSESSMENT.md       # tracked (main verdict)
      summary.json              # tracked (counts, delta, sbom SHA-256)
      llm-brief.md              # tracked (short agent-oriented scan summary)
      baseline.json             # gitignored (intermediate)
      baseline.previous.json    # gitignored
      findings.json, _meta.json, sbom/, sast/, ...
```

Git ignore:

- **`security-report/runs/.gitignore`** — ignores intermediate paths under `20[0-9][0-9]-*/` (RUN_ID prefix). **Tracked per run:** `FINAL_ASSESSMENT.md`, `summary.json`, `llm-brief.md`.
- **Root `.gitignore`** — legacy `security-report/scans/`, `security-report/sbom/` only.

**No `latest` symlink.** Use `index.json` field `latest_run_id` and the `runs[]` list to find the newest run.

**Do not commit SBOM JSON** (gitignored under `runs/<RUN_ID>/sbom/`). SHA-256 lives in tracked `summary.json`.

**Compare runs:** `security-report/index.json`, then open each `runs/<RUN_ID>/FINAL_ASSESSMENT.md`.

Optional HTML (generic spec): `tickets.html`, `jira-tickets.html`, `diff.html` — generate only if a human asked for a browser report; agents must not depend on them.

---

## 3. Workflow

Progress lines: `[reporter-scan] <step>: <result>`.

1. **Initialize** — `python3 security-report/tools/prepare_run.py $RUN_ID` (creates `runs/$RUN_ID/` subdirs and `baseline.previous.json` from `index.json` `latest_run_id`, or empty on first run).
2. **Rotate baseline** — handled by `prepare_run.py` (do not use a `latest` symlink).
3. **Detect** — Python (`pyproject.toml`, `uv.lock`), optional npm lock at `ui/custom/cookie/frontend/package-lock.json`, containers under `release/`, GitHub Actions under `.github/workflows/`. Record in `_meta.json`.
4. **Tool inventory** — required set in section 5. HALT if missing (same `continue` / `proceed anyway` / `abort` pattern as generic doc).
5. **Scan** — section 5 only.
6. **Normalize** — run `python3 security-report/tools/normalize_findings.py $RUN_ID` (writes `runs/$RUN_ID/{findings,baseline,summary}.json`, `llm-brief.md`, updates `index.json`).
7. **SBOM** — `syft` into `runs/$RUN_ID/sbom/` (section 5); re-run normalize or merge SHA-256 into `summary.json`.
8. **Baseline** — ensured by normalize step inside `runs/$RUN_ID/`.
9. **LLM brief** — ensured by normalize script (`llm-brief.md`).
10. **Diff** — `summary.json` `delta` field (normalize compares `baseline.previous.json` in the same run dir).
11. **FINAL_ASSESSMENT** — write `runs/$RUN_ID/FINAL_ASSESSMENT.md` per section 8 (mandatory deliverable).
12. **Print summary** — severity totals, `by_surface`, path to `FINAL_ASSESSMENT.md`.

Exit 0 when the workflow completes; exit 1 only on infrastructure failure.

---

## 4. Scan scope (paths)

### Include

- `lib/`, `ui/`, `administration/`, `reports/` (handlers)
- `ui/custom/cookie/frontend/build/` — **production** browser bundle (primary JS surface)
- `ui/custom/cookie/frontend/package-lock.json` — npm supply chain (lockfile only)
- `release/common/bin/` (production entrypoints)
- `release/reporter_cli/`, `release/reporter_ui/`, `release/common/`
- `.github/workflows/`
- `pyproject.toml`, `uv.lock`

### Exclude from SAST (still allow secrets scan with care)

- `tests/`, `live_test/`
- `.venv/`, `venv/`, `__pycache__/`, `security-report/`
- `ui/custom/cookie/frontend/node_modules/` — gitignored; not present in CI/checkout
- `apps/python/sync_server/` — optional separate pass; tag `sync-internal`

### Cookie frontend: dev-only paths (lower production relevance)

- `ui/custom/cookie/frontend/src/`, `vite.config.ts`, `index.html` (source) — relevant when reviewing **build pipeline** or before cutting a release; production serves only `build/`

### Container lint targets (production images only)

| Dockerfile                               | Purpose                                    |
| ---------------------------------------- | ------------------------------------------ |
| `release/reporter_cli/Dockerfile-cli`    | CLI installer image                        |
| `release/reporter_ui/Dockerfile-ui`      | UI runtime image                           |
| `release/reporter_sync/Dockerfile-sync`  | Sync image (supply chain / hardening only) |
| `release/reporter_cli/Dockerfile-backup` | Backup sidecar                             |

Do **not** treat hadolint on sync as a "user-facing" finding unless it affects image integrity (e.g. running as root) that also applies to published images.

---

## 5. Tool matrix (Reporter)

Primary stack is Python (`pyproject.toml` / `uv.lock`). The UI also ships a **prebuilt** npm bundle for the cookie component (lockfile at `ui/custom/cookie/frontend/package-lock.json`; `node_modules/` is gitignored). Required tools:

| Category   | Tool          | Command (run from repo root)                                                                                                                                       |
| ---------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| SAST       | `bandit`      | `bandit -r lib ui administration -f json -o security-report/runs/$RUN_ID/sast/bandit.json --severity-level low --confidence-level low --exclude .venv,venv,tests,security-report` |
| SAST       | `semgrep`     | `semgrep scan --config auto --sarif -o security-report/runs/$RUN_ID/sast/semgrep.sarif --metrics=off --error=false lib ui administration release`                                 |
| SCA        | `pip-audit`   | `pip-audit -f json -o security-report/runs/$RUN_ID/sca/pip-audit.json` (uses `pyproject.toml` / lock)                                                                             |
| SCA        | `osv-scanner` | `osv-scanner scan --recursive --format sarif --output security-report/runs/$RUN_ID/sca/osv.sarif .`                                                                               |
| SCA        | `trivy fs`    | `trivy fs . --format sarif --output security-report/runs/$RUN_ID/sca/trivy-fs.sarif --scanners vuln,misconfig --skip-dirs .venv,security-report,tests,ui/custom/cookie/frontend/node_modules` |
| SCA (opt.) | `npm audit`   | `cd ui/custom/cookie/frontend && npm audit --package-lock-only --json > ../../../../security-report/runs/$RUN_ID/sca/npm-cookie-audit.json` (no `npm install`; uses committed lockfile) |
| Secrets    | `gitleaks`    | `gitleaks detect --no-banner --redact --report-format sarif --report-path security-report/runs/$RUN_ID/secrets/gitleaks.sarif`                                                    |
| Secrets    | `trufflehog`  | `trufflehog filesystem . --json --no-update > security-report/runs/$RUN_ID/secrets/trufflehog.jsonl`                                                                              |
| IaC        | `actionlint`  | `actionlint -format '{{json .}}' > security-report/runs/$RUN_ID/iac/actionlint.json`                                                                                              |
| Containers | `hadolint`    | Per production Dockerfile under `release/`                                                                                                                         |
| SBOM       | `syft`        | `syft . -o cyclonedx-json=security-report/runs/$RUN_ID/sbom/cyclonedx.json -o spdx-json=security-report/runs/$RUN_ID/sbom/spdx.json` (create `sbom/` under the run dir first) |

**Not required** for this repo: repo-root `npm audit`, `govulncheck`, `kube-linter`, `checkov` (no Terraform/K8s app manifests), `brakeman`, etc.

**Optional** for cookie component only: `npm audit --package-lock-only` under `ui/custom/cookie/frontend/`; semgrep on `frontend/build` if investigating bundled JS issues.

Compare SCA results with **production pins** in `release/common/security.sh` (urllib3, gitpython, pillow, tornado, protobuf, pyarrow, idna, python-dotenv). If `pip-audit` flags a package that `security.sh` already pins, note the pin version in `FINAL_ASSESSMENT.md`.

---

## 6. Normalized finding schema

Same fields as [GENERIC_SECURITY_SCAN.md](./GENERIC_SECURITY_SCAN.md) section 7, plus:

```json
"surface": "ui|cli+ui-shared|sync-internal|deploy|supply-chain|other",
"production_relevance": "in_scope|out_of_scope|needs_review"
```

Set `production_relevance` during `FINAL_ASSESSMENT.md` authoring, not in raw scanner output.

Use `security-report/tools/normalize_findings.py` after scans to produce `findings.json`, `baseline.json`, `summary.json`, and `llm-brief.md`.

---

## 7. LLM-friendly artefacts (prefer over HTML)

| Artefact                                 | Format   | Use                                   |
| ---------------------------------------- | -------- | ------------------------------------- |
| `index.json`                             | JSON     | All runs: ids, counts, paths (tracked) |
| `runs/<RUN_ID>/findings.json`            | JSON     | Machine merge, delta, agent reasoning |
| `runs/<RUN_ID>/summary.json`             | JSON     | Counts, `by_surface`, delta, sbom SHA   |
| `runs/<RUN_ID>/FINAL_ASSESSMENT.md`      | Markdown | Verdict for that run                  |
| `runs/<RUN_ID>/llm-brief.md`             | Markdown | Fast orientation (~50 lines; tracked) |
| `runs/<RUN_ID>/sast/bandit.json`         | JSON     | Detailed SAST                         |
| `runs/<RUN_ID>/sbom/cyclonedx.json`      | JSON     | Supply chain inventory (gitignored)   |

Avoid asking agents to parse large SARIF or HTML unless necessary. If you extend normalization, add SARIF-to-JSON converters into `findings.json` rather than pointing agents at `trivy-fs.sarif`.

**Known false-positive patterns in this repo**

- Bandit `B105` on Streamlit session keys in `ui/` (e.g. `oidc_access_token`) — key names, not secrets.
- Bandit `B105` on env var names like `DB_DATA_PASSWORD` in `lib/interactive/env/`.
- Gitleaks on `release/reporter_ui/certs/privatekey.pem` — bundled placeholder/demo cert for image layout; verify it is replaced in real deployments (document in assessment, do not treat as leaked production key without evidence).
- Bandit SQL injection in `administration/migration/_files/*` — migrations run at **UI/sync process startup** (`release/common/bin/ui` / `bin/serve_ui` call `ui.bootstrap.main()` → `init_databases()` → `apply_migrations()` before `streamlit run ui/app.py`). They are **not** invoked from `ui/app.py` on each browser request. Retention SQL uses `parse_retention_days()` (int from env), not Streamlit session input; still review env/config injection if attackers can alter container env.

---

## 8. `FINAL_ASSESSMENT.md` (required deliverable)

After automated scans, write or update `security-report/runs/<RUN_ID>/FINAL_ASSESSMENT.md`. This is the **only** per-run artefact that should recommend fixes. Raw scanner output is input, not the conclusion. `index.json` is updated when normalize runs.

### Structure (copy and fill)

```markdown
# PrivX Reporter security assessment

- Run ID: <RUN_ID>
- Generated: <ISO8601>
- Assessor: <name or agent run>

## 1. Scope and assumptions

- Deployment model: standalone | distributed
- UI exposed to: <network description>
- Auth: local | OIDC providers: <list>
- CLI trust: trusted operators on <hosts>

## 2. Attack surfaces considered

### UI (in scope)
- Entry: Streamlit :8501, TLS: yes/no
- Auth/session: <brief>
- Data access: admin DB + data DB, report output dir

### CLI (trusted-operator boundary)
- Entry: /opt/reporter bin scripts, PrivX credentials in .env
- Not treating hostile local user as in-scope unless stated

### Excluded from external threat model
- Sync server (internal only)
- ...

### DB bootstrap (UI/sync process start)
- Migrations: `ui/bootstrap.py` -> `init_databases()` -> `apply_migrations()` before Streamlit; not per HTTP request via `ui/app.py`
- Trust: container/host env and shipped migration files; see section 0 "Database bootstrap and migrations"

### Session cookie component (browser)
- Production: `ui/custom/cookie/frontend/build` (not `src/`, not `node_modules/`)
- Dev override: `COOKIE_COMPONENT_DEV_URL` must be absent in production

## 3. Findings summary

| Severity | Count (raw) | Count (production-relevant) |
| -------- | ----------- | --------------------------- |
| critical |             |                             |
| high     |             |                             |
| medium   |             |                             |
| low      |             |                             |

## 4. Production-relevant issues (fix recommendations)

For each issue:

### <title>
- Severity: ...
- Surface: ui | cli+ui-shared | supply-chain | deploy
- Attack vector: <who can exploit, preconditions>
- Evidence: <tool, rule, path:line, finding id>
- Why it matters in production: ...
- Recommended fix: ...
- Acceptance: <how to verify>

## 5. Accepted risks / false positives

- <finding id>: reason, owner, review date

## 6. Supply chain and images

- pip-audit / osv / trivy vs security.sh pins
- Base images: python:3.14-alpine
- SBOM: paths under `runs/<RUN_ID>/sbom/`; SHA-256 from that run's `summary.json` (not committed in git)

## 7. Hardening backlog (optional, not blocking)

- Items that are good practice but not reachable by assumed attackers

## 8. Next run

- Re-run command: execute docs/llm/REPORTER_SECURITY_SCAN.md
- Compare runs via `index.json` and `runs/<RUN_ID>/summary.json` (`delta` vs `baseline.previous.json`)
```

### Attack vectors to explicitly evaluate (UI)

Use code and docs; do not rely on scanners alone.

1. **Authentication** — local password policy, `UI_TMP_ADMIN_PASSWORD` bootstrap, OIDC state/nonce, session cookie flags, idle timeout (`UI_JWT_EXPIRATION_MINUTES`).
2. **Authorization** — report visibility (`can_access_report`), admin pages, group-scoped output paths under `REPORT_OUT_DIR`.
3. **Session management** — cookie vs `st.session_state`, logout, session fixation (see `ui/services/session/IMPORTANT.md`). Include **`ui/custom/cookie`**: production uses `frontend/build` only; verify `COOKIE_COMPONENT_DEV_URL` is unset in prod; review bundled JS for cookie flags (`secure`, `sameSite`, path).
4. **Injection** — SQLAlchemy/raw SQL in UI-facing queries; report parameter handling into `lib._report.generator`.
5. **Exposure** — Streamlit `server.address 0.0.0.0`, TLS termination, DB ports published in standalone compose (`DB_DATA_PORT`, `DB_ADMIN_PORT`).
6. **Secrets** — `.env`, compose env, PrivX API secrets, OIDC client secret in container env.
7. **Dependency CVEs** — production venv vs `security.sh` pins.

### Attack vectors to deprioritize (CLI)

- Operator-run `report` / `admin` abuse, host filesystem access, editing `.env`.

### Migrations

See **section 0 — Database bootstrap and migrations**. When reviewing injection findings under `administration/migration/`, always trace whether the path is bootstrap vs Streamlit request handling.

---

## 9. Example run (2026-06-02)

A pilot run (`2026-06-02T08-26-33Z`) on this tree produced:

- **20** normalized SAST findings (bandit + semgrep): 2 medium, 18 low.
- **0** pip-audit vulns on locked deps at scan time.
- **Surfaces**: 11 `cli+ui-shared`, 7 `ui`, 2 `sync-internal`.
- **Gitleaks**: hits on bundled UI cert material under `release/reporter_ui/certs/` (triage as deploy placeholder, not production leak).

Medium bandit items pointed at migration SQL string formatting (`administration/migration/_files/2026-04-17-create-all-tables.py`) — migrations are in the **UI server startup chain** (`ui/bootstrap.py` → `lib/database/db_init.py`), not the login/report request path. Treat as **deploy/config trust** (env vars `SYNC_AUDIT`, `SYNC_CONNECTION`), not as unauthenticated HTTP SQLi unless you prove request-driven migration triggers.

Use `index.json` (`latest_run_id`) then `runs/<RUN_ID>/llm-brief.md` after your own run for current numbers.

---

## 10. Final stdout block

```
[reporter-scan] run_id=<RUN_ID>
[reporter-scan] totals  critical=<n>  high=<n>  medium=<n>  low=<n>  info=<n>
[reporter-scan] by_surface ui=<n> cli+ui-shared=<n> sync-internal=<n> supply-chain=<n>
[reporter-scan] llm     security-report/runs/<RUN_ID>/llm-brief.md
[reporter-scan] json    security-report/runs/<RUN_ID>/summary.json
[reporter-scan] index   security-report/index.json
[reporter-scan] verdict security-report/runs/<RUN_ID>/FINAL_ASSESSMENT.md
[reporter-scan] sbom    security-report/runs/<RUN_ID>/sbom/cyclonedx.json (gitignored)
```

---

## 11. Relation to generic scan

| Topic       | Generic         | This document                                |
| ----------- | --------------- | -------------------------------------------- |
| Languages   | Many ecosystems | Python + Docker + GitHub Actions only        |
| Surfaces    | All code        | UI + shared libs; CLI trusted; sync internal |
| Reports     | HTML-first      | JSON/Markdown-first                          |
| Deliverable | tickets.html    | **FINAL_ASSESSMENT.md** with attack vectors  |
| Jira HTML   | Required        | Optional                                     |

Run the generic prompt only when you need a language-agnostic baseline or full HTML ticket boards for audit archives.
