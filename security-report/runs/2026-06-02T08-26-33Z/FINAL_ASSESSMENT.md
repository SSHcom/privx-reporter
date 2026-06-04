# PrivX Reporter security assessment

- Run ID: 2026-06-02T08-26-33Z
- Generated: 2026-06-02T08:27:11Z
- Assessor: automated pilot run (bandit/semgrep/pip-audit/gitleaks); human review required before release sign-off

## 1. Scope and assumptions

- Deployment model: standalone and distributed (see `docs/operations/install/`)
- UI exposed to: operators on the corporate network; port 8501 (TLS when `SSL_CERT` / `SSL_KEY` set in UI container)
- Auth: local username/password and optional OIDC (`UI_AUTH_MODE`)
- CLI trust: trusted operators with shell on the Reporter host and access to `/opt/reporter` and `.env`

## 2. Attack surfaces considered

### UI (in scope)

- Entry: Streamlit on `0.0.0.0:8501` via `bin/prod/ui`
- Auth/session: DB-backed sessions, cookie `ui_session_token`, JWT idle timeout; browser writes via `ui/custom/cookie` using committed `frontend/build` only (not `node_modules/`; `COOKIE_COMPONENT_DEV_URL` must be unset in prod)
- Data access: admin DB (users/groups), data DB (report data), filesystem output under `REPORT_OUT_DIR` per user/group

### CLI (trusted-operator boundary)

- Entry: `report`, `admin`, `create_env`, `backup` after `install.sh`
- PrivX and DB credentials in host `.env`
- Misuse by a malicious operator is out of scope for external attacker modelling

### Excluded from external threat model

- Sync server: no end-user HTTP API; PrivX + DB on internal Docker network only
- Backup container: operational, same trust as host operators

## 3. Findings summary

| Severity | Count (raw) | Count (production-relevant)                      |
| -------- | ----------- | ------------------------------------------------ |
| critical | 0           | 0                                                |
| high     | 0           | 0                                                |
| medium   | 2           | 0 for remote UI users (see migration note below) |
| low      | 18          | 0 pending manual UI/auth review                  |
| info     | 0           | 0                                                |

Supply chain: pip-audit reported **0** vulnerabilities on locked dependencies at scan time. Production pins in `release/common/security.sh` should remain the source of truth for image builds.

## 4. Production-relevant issues (fix recommendations)

None identified automatically in this pilot run that are both **reachable from an unauthenticated HTTP request** and **exploitable without deploy-time access**. Manual review of UI auth and report authorization (section 8 checklist in `docs/llm/REPORTER_SECURITY_SCAN.md`) is still required.

### Migration SQL (bandit medium) — UI startup path, not `app.py` per request

Production and dev UI startup runs migrations **before** Streamlit serves pages:

```text
bin/prod/ui | bin/serve_ui
  -> python -c "from ui.bootstrap import main; main()"
       -> configure_database() -> init_databases() -> apply_migrations()
  -> streamlit run ui/app.py   # does NOT call init_databases()
```

`ui/app.py` only configures logging, session state, and login/home routing. Any user hitting the UI over HTTP does **not** re-trigger `apply_migrations()` on each request; migrations run on **process start** and only apply entries still marked pending in `migration_history`.

The flagged statements in `administration/migration/_files/2026-04-17-create-all-tables.py` interpolate retention days from `parse_retention_days(SYNC_AUDIT)` / `parse_retention_days(SYNC_CONNECTION)`, which parse env config and return a validated **integer** (not request parameters). Residual risk is **misconfiguration or compromise of container/host env** (or supply-chain change to migration files), not a typical authenticated UI user crafting SQL via the browser.

**Recommendation (hardening, not emergency):** parameterize retention policy SQL (`text()` + bind params) to satisfy static analysis and avoid future migrations copying the f-string pattern; document that UI and sync containers must not grant untrusted parties control over `SYNC_AUDIT` / `SYNC_CONNECTION`.

## 5. Accepted risks / false positives

| Finding / pattern                                                                         | Reason                                                                                                                                                    |
| ----------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Bandit B105 on `ui/views/login/oidc.py`, `ui/services/session/keys.py`                    | Streamlit state key names, not stored passwords                                                                                                           |
| Bandit B105 on `lib/interactive/env/*.py`                                                 | Environment variable names in interactive setup                                                                                                           |
| Bandit SQL injection in `administration/migration/_files/2026-04-17-create-all-tables.py` | Runs at UI/sync **process startup** via `init_databases()`, not via `ui/app.py` per HTTP request; retention values are parsed ints from env, not UI input |
| Gitleaks on `release/reporter_ui/certs/privatekey.pem`                                    | Bundled cert material for image layout; replace with site certs in production                                                                             |
| Bandit subprocess warnings in `lib/_backup/backup.py`                                     | CLI/backup path; trusted operator context                                                                                                                 |

## 6. Supply chain and images

- **security.sh** pins: urllib3, gitpython, pillow, tornado, protobuf, pyarrow, idna, python-dotenv (verified at image build)
- **Base images**: `python:3.14-alpine` for cli/ui/sync builder and runtime
- **SBOM**: `security-report/runs/<RUN_ID>/sbom/` (gitignored); see this run's `summary.json` for SHA-256
- **Hadolint**: run on `release/reporter_cli/Dockerfile-cli`, `release/reporter_ui/Dockerfile-ui`, `release/reporter_sync/Dockerfile-sync` for image hygiene; treat as deploy hardening, not UI RCE unless coupled to runtime exposure

## 7. Hardening backlog (optional)

- Review Streamlit and dependency CVEs when `pip-audit` / `trivy` begin reporting issues; bump `security.sh` pins and rebuild images
- Ensure standalone deployments do not expose PostgreSQL host ports beyond trusted admin networks (`DB_DATA_PORT`, `DB_ADMIN_PORT` in compose)
- Confirm production UI replaces bundled certs under `release/reporter_ui/certs/`
- Extend `normalize_findings.py` to ingest gitleaks/trivy SARIF into `findings.json` for a single agent-readable file

## 8. Next run

- Re-run: execute `docs/llm/REPORTER_SECURITY_SCAN.md`
- Compare runs: `security-report/index.json` and `runs/<RUN_ID>/summary.json` (`delta` field)
- Update this file with any new **production-relevant** items and assigned owners
