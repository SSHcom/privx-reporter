# Security scan prompt

Universal security posture scan for the current repository. Detects languages and assets, runs SAST, SCA, secrets, IaC, container and SBOM tooling, normalizes findings, diffs against the last baseline, and renders Nordic Solarized HTML reports plus Jira-ready tickets.

This file is a coding-agent-agnostic task specification. Any agent that can execute shell commands, read and write files in the working tree, and hold a multi-turn conversation (required for the install gate in section 2 step 5) can run it. The workflow itself does not depend on any single agent, runtime, or operating system beyond a POSIX shell or PowerShell on Windows.

### Usage

Hand the contents of this file to the agent as a task instruction. Re-runs use the same file unchanged. Common placement conventions:

| Agent                                 | Suggested placement                                            | Invocation                          |
| ------------------------------------- | -------------------------------------------------------------- | ----------------------------------- |
| Generic / any chat-based coding agent | Project root as `SECURITY_SCAN.md` or `AGENTS.md` section      | "Execute the security scan prompt." |
| Claude Code                           | `.claude/commands/security-scan.md`                            | `/security-scan`                    |
| Cursor                                | `.cursor/rules/security-scan.md` or paste into the agent panel | "Execute SECURITY_SCAN.md."         |
| Windsurf                              | `.windsurf/workflows/security-scan.md`                         | `/security-scan`                    |
| Aider                                 | Project root; load with `/read SECURITY_SCAN.md`               | "Execute the security scan prompt." |
| Continue                              | `.continue/prompts/security-scan.md`                           | `@security-scan`                    |
| Cline / Roo Code                      | Paste into the task input                                      | n/a                                 |
| Codex CLI and similar                 | Pass as input or include from project root                     | n/a                                 |

The workflow is idempotent and produces deterministic deltas: re-running on an unchanged tree yields byte-identical normalized findings except for `last_seen_run`.

---

## 0. Operating principles

1. Read-only on source. Never edit application code. All artefacts live under `security-report/`.
2. No telemetry. No outbound calls except to package registries and vulnerability databases used by tools.
3. Do not fabricate findings. If a tool is missing and cannot be installed, mark its scan as `status: skipped` with a reason; do not synthesise output.
4. Do not introduce the word "AI" into any generated artefact.
5. Use ASCII punctuation. No em-dashes.
6. Prefer fail-soft. A failing scanner must not abort the run; mark it `failed`, capture stderr, continue.
7. Treat secret detection as advisory inside this run. Never print secret values into reports or terminal; only file path, line number, rule id and a redacted fingerprint.
8. Use the existing baseline at `security-report/baseline.json` if present, otherwise treat this as the first run.

---

## 1. Output layout

Produce exactly this structure inside the repo root:

```
security-report/
  baseline.json                   # canonical normalized findings for the latest run
  baseline.previous.json          # previous run's baseline (rotated on each run)
  summary.json                    # roll-up counts, deltas, scan metadata
  tickets.html                    # human-readable, severity-grouped fix board
  jira-tickets.html               # one card per finding, Jira description blocks ready to paste
  diff.html                       # delta view: new, resolved, persisting, regressed
  sbom/
    cyclonedx.json                # CycloneDX 1.5 SBOM
    spdx.json                     # SPDX 2.3 SBOM (best-effort)
  scans/
    <UTC-ISO8601>/                # full raw outputs for this run, e.g. 2026-05-19T10-22-31Z
      _meta.json                  # tool versions, exit codes, durations
      sast/
      sca/
      secrets/
      iac/
      containers/
      licenses/
      sbom/
    latest -> <UTC-ISO8601>       # symlink (or junction on Windows) to current run
  tools/
    bootstrap.sh                  # POSIX installer for missing tools
    bootstrap.ps1                 # Windows PowerShell installer for missing tools
    versions.json                 # tool name -> version pinning and install method
  templates/
    report.css                    # Nordic Solarized stylesheet (shared)
    ticket.html.tmpl              # per-ticket HTML fragment
    jira.txt.tmpl                 # Jira description body template (Atlassian wiki markup)
  README.md                       # how to re-run, how to read the reports
```

Add the following to the repository `.gitignore` if not already present:

```
security-report/scans/
security-report/baseline.previous.json
```

Keep `baseline.json`, `summary.json`, `tickets.html`, `jira-tickets.html`, `diff.html`, `sbom/`, `tools/`, `templates/`, and `README.md` tracked so history is auditable.

---

## 2. Workflow

Execute strictly in this order. After each step, write progress to stdout in the form `[security-scan] <step>: <result>`.

1. **Initialize.** Create `security-report/` and subdirectories. Compute the run id `RUN_ID=$(date -u +%Y-%m-%dT%H-%M-%SZ)`. Create `security-report/scans/$RUN_ID/`. Update the `latest` symlink.
2. **Rotate baseline.** If `security-report/baseline.json` exists, copy it to `security-report/baseline.previous.json`. Otherwise create an empty previous baseline `{"findings": [], "generated_at": null}`.
3. **Detect.** Run the detection phase from section 3. Persist the detection result to `scans/$RUN_ID/_meta.json` under the `detection` key.
4. **Tooling inventory.** Run the inventory phase from section 4. Persist to `_meta.json` under `tools`. Always (re)write `tools/bootstrap.sh`, `tools/bootstrap.ps1`, and `tools/versions.json` to reflect the current detection set.
5. **Gate: required tools present.** Compute the required-tool set from section 4. If any required tool is missing:
   1. Print the block below verbatim, then **stop and wait for a user reply**. Do not start step 6 until the user responds.
      ```
      [security-scan] HALT: required tools missing.
      [security-scan] missing: <comma-separated tool names>
      [security-scan] install: ./security-report/tools/bootstrap.sh        (Linux / macOS / WSL)
      [security-scan] install: powershell -File security-report\tools\bootstrap.ps1   (Windows)
      [security-scan] Install the listed tools manually, then reply:
      [security-scan]   "continue"          re-check tooling and proceed if all required tools are now present
      [security-scan]   "proceed anyway"    skip the missing tools and continue (each missing tool will be recorded as status=skipped:user-override)
      [security-scan]   "abort"             stop the run; no scans executed
      ```
   2. On `continue`: re-run the inventory phase. If anything required is still missing, repeat this step (print the same HALT block with the updated list and wait again). Do not enter an infinite loop without user input; one halt per user reply.
   3. On `proceed anyway`: record each still-missing required tool in `_meta.json.tools[*]` with `status: "skipped"`, `reason: "user-override"`, and proceed to step 6.
   4. On `abort`: write `_meta.json` with `run_status: "aborted_missing_tools"`, do not produce reports, exit 2.
   5. Never start the scan phase while the required-tool set has unresolved entries other than user-overrides.
6. **Scan.** Run every applicable tool from section 5. Capture stdout, stderr and exit code per tool into `scans/$RUN_ID/<category>/<tool>.{stdout,stderr,exit,json}`.
7. **Normalize.** Convert every tool output into the unified finding schema from section 7. Write `scans/$RUN_ID/findings.json`.
8. **SBOM.** Generate CycloneDX and SPDX SBOMs from section 8 into `sbom/`.
9. **Baseline write.** Write the new canonical `baseline.json` from the normalized findings. Compute the run summary and write `summary.json`.
10. **Diff.** Compute the delta from `baseline.previous.json` to `baseline.json` per section 9.
11. **Render.** Generate `tickets.html`, `jira-tickets.html`, `diff.html` per section 10. Generate `README.md` per section 12.
12. **Print summary.** Output a terse final block: totals by severity, deltas, scan duration, list of skipped tools with reasons.

---

## 3. Detection

Walk the working tree, ignoring `.git/`, `node_modules/`, `target/`, `build/`, `dist/`, `vendor/`, `.venv/`, `__pycache__/`, and any path listed in `.gitignore`. For each detection signal below, record the matching files into `_meta.json.detection.signals[]` as `{language|asset, evidence: [paths], confidence: "high|low"}`.

Language and ecosystem signals:

| Language / ecosystem    | High-confidence files                                                                                    |
| ----------------------- | -------------------------------------------------------------------------------------------------------- |
| JavaScript / TypeScript | `package.json`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`, `tsconfig.json`                      |
| Python                  | `pyproject.toml`, `requirements*.txt`, `Pipfile`, `Pipfile.lock`, `poetry.lock`, `setup.py`, `setup.cfg` |
| Go                      | `go.mod`, `go.sum`                                                                                       |
| Rust                    | `Cargo.toml`, `Cargo.lock`                                                                               |
| Java / Kotlin           | `pom.xml`, `build.gradle`, `build.gradle.kts`, `settings.gradle*`                                        |
| C# / .NET               | `*.csproj`, `*.fsproj`, `*.sln`, `packages.lock.json`                                                    |
| Ruby                    | `Gemfile`, `Gemfile.lock`, `*.gemspec`                                                                   |
| PHP                     | `composer.json`, `composer.lock`                                                                         |
| C / C++                 | `CMakeLists.txt`, `Makefile`, `meson.build`, `conanfile.*`, `*.c`, `*.cc`, `*.cpp`, `*.h`, `*.hpp`       |
| Swift                   | `Package.swift`, `*.xcodeproj`, `*.xcworkspace`                                                          |
| Shell                   | `*.sh`, `*.bash`, `*.zsh`                                                                                |
| Elixir                  | `mix.exs`, `mix.lock`                                                                                    |

Asset signals:

| Asset               | Evidence                                                                                         |
| ------------------- | ------------------------------------------------------------------------------------------------ |
| Container           | `Dockerfile*`, `Containerfile*`, `docker-compose*.y?ml`, `compose.y?ml`                          |
| Kubernetes          | `*.yaml` containing `apiVersion:` and `kind:` at top level, `kustomization.y?ml`, `helm/` charts |
| Terraform           | `*.tf`, `*.tf.json`                                                                              |
| OpenTofu            | `*.tofu`                                                                                         |
| Ansible             | `playbook*.y?ml`, `roles/*/tasks/main.y?ml`                                                      |
| Pulumi              | `Pulumi.yaml`                                                                                    |
| CloudFormation      | `*.yaml` / `*.json` with `AWSTemplateFormatVersion`                                              |
| GitHub Actions      | `.github/workflows/*.y?ml`                                                                       |
| GitLab CI           | `.gitlab-ci.yml`                                                                                 |
| Secrets scan target | always on                                                                                        |
| Git history         | always on (last 365 commits, scoped)                                                             |

For YAML files that could be Kubernetes, parse and check for `apiVersion` + `kind`. Be conservative: false positives are cheaper than false negatives here.

Persist the languages and assets that fired with `confidence: high` (lockfile or manifest present) versus `confidence: low` (source files only, no manifest). Tools requiring a manifest are only run on high-confidence detections.

---

## 4. Tooling inventory

For each tool in the matrix below, probe with `which <tool>` (POSIX) or `Get-Command <tool>` (Windows). If absent, record `status: missing` and the install method. If present, capture `--version` output.

Write `tools/bootstrap.sh` and `tools/bootstrap.ps1` so a user can install everything missing in one go. Both scripts must:

- Be idempotent. Each install is wrapped in a `command -v X >/dev/null 2>&1 || install` check.
- Prefer official installers. Fall back to language package managers (`pipx`, `cargo install`, `go install`, `brew`, `apt-get`, `winget`).
- Document a Docker alternative in a comment for each tool, so users who refuse to install can run the containerized version.
- Echo each step so the user can copy individual lines.

Do not run `bootstrap.sh` automatically under any circumstance. Installation is the user's action, not the scanner's.

### Required vs optional classification

After the inventory probe completes, classify each tool:

- **Required.** Every universal tool from section 5 (`semgrep`, `gitleaks`, `trufflehog`, `osv-scanner`, `trivy`, `syft`) **plus** every per-ecosystem tool whose detection precondition matched with `confidence: high` (lockfile or manifest present). Required tools gate the scan.
- **Optional.** Per-ecosystem tools triggered only by source-file heuristics (`confidence: low`), and any tool with an environmental precondition that is not met on this host (for example `dockle` needs a Docker daemon; `dependency-check` needs a usable build; `brakeman` needs a Rails project). Optional tools that are missing or unrunnable are recorded with `status: "skipped"` and a precise `reason`, and do not block the run.
- **Pinned in `tools/versions.json`.** For each tool, record: `name`, `classification` (`required` | `optional`), `detected_version`, `target_version`, `install_method` (`native` | `package_manager` | `language_pm` | `docker`), and `install_command`. This file is the single source of truth read by the bootstrap scripts.

### Halt-and-wait behaviour

If the required set has any missing entry, the scan does not start. Step 5 of the workflow takes over:

1. Emit the HALT block defined in section 2 step 5. List every missing required tool by name, one per line under `missing:`. Group identical install commands in `bootstrap.sh` so the user can install several tools with one paste if they prefer.
2. Yield control. The next user message is the decision (`continue`, `proceed anyway`, `abort`). Treat any other reply as a request for clarification and re-print the HALT block without rerunning the inventory.
3. On `continue`, re-run the inventory phase end-to-end (do not cache the previous result). Update `_meta.json.tools` and re-emit the HALT block if anything is still missing. Loop only on explicit user replies.
4. On `proceed anyway`, set `_meta.json.run_status = "degraded_user_override"` and continue. The final summary and `tickets.html` show a banner listing the overridden tools so the gap is visible in the report itself.
5. On `abort`, set `_meta.json.run_status = "aborted_missing_tools"` and exit 2 with no reports written. The next invocation starts cleanly from step 1.

Optional tools never trigger the halt. They are listed in the HALT block (when one fires) under an `optional_missing:` line for awareness only.

---

## 5. Tool matrix

Run every tool whose detection precondition is satisfied. Always run the universal tools.

### Universal

| Category    | Tool          | Why                                              | Invocation hint                                                                                                                                           |
| ----------- | ------------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------- |
| SAST        | `semgrep`     | Multi-language rules, mature ecosystem           | `semgrep scan --config auto --sarif -o scans/$RUN_ID/sast/semgrep.sarif --metrics=off --error=false`                                                      |
| Secrets     | `gitleaks`    | Source + history secret detection                | `gitleaks detect --no-banner --redact --report-format sarif --report-path scans/$RUN_ID/secrets/gitleaks.sarif`                                           |
| Secrets     | `trufflehog`  | Verified-secret detection (complements gitleaks) | `trufflehog filesystem . --json --no-update > scans/$RUN_ID/secrets/trufflehog.jsonl`                                                                     |
| SBOM        | `syft`        | CycloneDX + SPDX SBOM                            | `syft . -o cyclonedx-json=sbom/cyclonedx.json -o spdx-json=sbom/spdx.json`                                                                                |
| SCA (multi) | `osv-scanner` | Lockfile-driven CVE scan across ecosystems       | `osv-scanner scan --recursive --format sarif --output scans/$RUN_ID/sca/osv.sarif .`                                                                      |
| Misc        | `trivy fs`    | Vulns + misconfig + license + secrets            | `trivy fs . --format sarif --output scans/$RUN_ID/sca/trivy-fs.sarif --scanners vuln,misconfig,license --skip-dirs node_modules,vendor,target,build,dist` |

### JavaScript / TypeScript (manifest present)

| Tool                                          | Invocation                                                                             |
| --------------------------------------------- | -------------------------------------------------------------------------------------- |
| `npm audit` / `pnpm audit` / `yarn npm audit` | Use whichever lockfile is present. JSON output.                                        |
| `retire`                                      | `retire --outputformat jsonsimple --outputpath scans/$RUN_ID/sca/retire.json --path .` |
| `eslint` with `eslint-plugin-security`        | Only if an eslint config already exists in repo; do not add config.                    |

### Python (manifest present)

| Tool        | Invocation                                                                                                                           |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| `pip-audit` | `pip-audit -f sarif -o scans/$RUN_ID/sca/pip-audit.sarif --strict                                                                    |  | true` (works against `pyproject.toml`, `requirements*.txt`, or current env) |
| `bandit`    | `bandit -r . -f sarif -o scans/$RUN_ID/sast/bandit.sarif --severity-level low --confidence-level low --exclude .venv,venv,build,dist |  | true`                                                                       |

### Go

| Tool          | Invocation                                                              |
| ------------- | ----------------------------------------------------------------------- |
| `govulncheck` | `govulncheck -format sarif ./... > scans/$RUN_ID/sca/govulncheck.sarif` |
| `gosec`       | `gosec -fmt sarif -out scans/$RUN_ID/sast/gosec.sarif ./...`            |

### Rust

| Tool           | Invocation                                                                                                                              |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `cargo audit`  | `cargo audit --json > scans/$RUN_ID/sca/cargo-audit.json`                                                                               |
| `cargo deny`   | `cargo deny --format json check > scans/$RUN_ID/sca/cargo-deny.json` (if `deny.toml` exists)                                            |
| `cargo clippy` | `cargo clippy --message-format=json -- -W clippy::all -W clippy::pedantic > scans/$RUN_ID/sast/clippy.jsonl` (advisory only, not fatal) |

### Java / Kotlin (manifest present)

| Tool                       | Invocation                                                                                                              |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `dependency-check` (OWASP) | `dependency-check --scan . --format SARIF --out scans/$RUN_ID/sca/depcheck.sarif --disableYarnAudit --disableNodeAudit` |
| `spotbugs` + `findsecbugs` | Only if a build is already configured (`mvn` or `gradle`); otherwise skip with reason `no build`.                       |

### C# / .NET

| Tool                                                                  | Invocation                                     |
| --------------------------------------------------------------------- | ---------------------------------------------- |
| `dotnet list package --vulnerable --include-transitive --format json` | Write to `scans/$RUN_ID/sca/dotnet-vuln.json`. |
| `security-code-scan`                                                  | Skip unless project is buildable.              |

### Ruby

| Tool           | Invocation                                                                        |
| -------------- | --------------------------------------------------------------------------------- |
| `bundle audit` | `bundle audit check --update --format json > scans/$RUN_ID/sca/bundle-audit.json` |
| `brakeman`     | `brakeman -f sarif -o scans/$RUN_ID/sast/brakeman.sarif` (Rails repos)            |

### PHP

| Tool                            | Invocation                                                             |
| ------------------------------- | ---------------------------------------------------------------------- |
| `composer audit`                | `composer audit --format json > scans/$RUN_ID/sca/composer-audit.json` |
| `psalm` with `--taint-analysis` | Only if `psalm.xml` exists.                                            |

### C / C++

| Tool         | Invocation                                                                                        |
| ------------ | ------------------------------------------------------------------------------------------------- |
| `cppcheck`   | `cppcheck --enable=all --inconclusive --xml --xml-version=2 . 2> scans/$RUN_ID/sast/cppcheck.xml` |
| `flawfinder` | `flawfinder --sarif . > scans/$RUN_ID/sast/flawfinder.sarif`                                      |

### Containers (Dockerfile or image references present)

| Tool          | Invocation                                                                                    |
| ------------- | --------------------------------------------------------------------------------------------- |
| `hadolint`    | `hadolint --format sarif <Dockerfile> > scans/$RUN_ID/containers/hadolint.sarif` per file     |
| `dockle`      | If Docker daemon is reachable and image is built locally; otherwise skip.                     |
| `trivy image` | Skip by default. Document the command in the report for the user to run against built images. |

### Kubernetes

| Tool           | Invocation                                                                |
| -------------- | ------------------------------------------------------------------------- |
| `kube-linter`  | `kube-linter lint . --format sarif > scans/$RUN_ID/iac/kube-linter.sarif` |
| `kubesec`      | Per manifest, JSON; aggregate.                                            |
| `trivy config` | Captured by the universal `trivy fs` pass.                                |

### IaC (Terraform / OpenTofu / CloudFormation / Pulumi / Ansible)

| Tool           | Invocation                                                               |
| -------------- | ------------------------------------------------------------------------ |
| `checkov`      | `checkov -d . -o sarif --output-file-path scans/$RUN_ID/iac --soft-fail` |
| `trivy config` | Already covered by universal `trivy fs`.                                 |

### GitHub Actions / GitLab CI

| Tool                               | Invocation                                                                             |
| ---------------------------------- | -------------------------------------------------------------------------------------- |
| `actionlint`                       | `actionlint -format '{{json .}}' > scans/$RUN_ID/iac/actionlint.json` (GitHub Actions) |
| `semgrep` rules `p/github-actions` | Already covered by universal semgrep.                                                  |

---

## 6. Run rules

- Every tool gets a hard timeout of 15 minutes. Kill and mark `failed: timeout` if exceeded.
- Run tools in parallel only within the same category, and only up to `min(4, nproc)`.
- Honour `--exclude` patterns: `node_modules`, `vendor`, `target`, `build`, `dist`, `.venv`, `venv`, `__pycache__`, `.next`, `.nuxt`, `coverage`, `security-report`.
- If the repo is larger than 2 GiB or has more than 250k files, print a warning and add `large_repo: true` to `_meta.json`. Continue.
- Do not exit non-zero on findings. Only exit non-zero on infrastructure failure (cannot create directories, no disk space).

---

## 7. Normalized finding schema

Every tool output is converted into records of this shape and merged into `baseline.json` and per-run `findings.json`:

```json
{
  "id": "stable-hash-of-tool+rule+path+line+fingerprint",
  "tool": "semgrep",
  "rule_id": "javascript.lang.security.audit.xss.direct-response-write",
  "title": "Direct user input written to HTTP response",
  "description": "Short, factual description. No marketing language.",
  "severity": "critical|high|medium|low|info",
  "cwe": ["CWE-79"],
  "cve": ["CVE-2024-12345"],
  "cvss": 7.5,
  "category": "sast|sca|secrets|iac|container|license|sbom",
  "location": {
    "path": "src/handlers/user.ts",
    "line_start": 42,
    "line_end": 42,
    "snippet": "res.write(req.query.name)"
  },
  "package": {
    "ecosystem": "npm",
    "name": "lodash",
    "version": "4.17.20",
    "fixed_versions": ["4.17.21"]
  },
  "references": ["https://nvd.nist.gov/vuln/detail/CVE-2024-12345"],
  "first_seen_run": "2026-04-12T08-00-01Z",
  "last_seen_run": "2026-05-19T10-22-31Z",
  "status": "open|resolved|regressed",
  "fingerprint": "sha256:..."
}
```

ID derivation rules so findings are stable across runs:

- For SAST: `sha256(tool + rule_id + path + line_start + normalized_snippet)` where the snippet is whitespace-collapsed.
- For SCA / containers: `sha256(tool + ecosystem + package + cve)`.
- For secrets: `sha256(tool + rule_id + path + line_start + redacted_fingerprint)`. Never include the secret value.
- For IaC: `sha256(tool + rule_id + path + resource_address)`.

Severity normalization: map each tool's severity to the five-level scale above. When CVSS is present, override with: `>=9.0 critical`, `>=7.0 high`, `>=4.0 medium`, `>0 low`, else `info`.

Carry `first_seen_run` from the previous baseline if the id matches; otherwise set to the current `RUN_ID`. Set `last_seen_run` to the current `RUN_ID` whenever an id appears.

---

## 8. SBOM generation

1. Primary: `syft . -o cyclonedx-json=security-report/sbom/cyclonedx.json -o spdx-json=security-report/sbom/spdx.json`.
2. If `syft` is missing, fall back to per-ecosystem SBOM:
   - npm: `npm sbom --sbom-format=cyclonedx`
   - Python: `cyclonedx-py environment` or `cyclonedx-py requirements`
   - Go: `cyclonedx-gomod mod`
   - Rust: `cargo cyclonedx`
   - Java: `cyclonedx-maven-plugin` / `cyclonedx-gradle-plugin` (only if build files exist)
3. Merge into a single CycloneDX 1.5 document if multiple ecosystems are present. Validate JSON structure. Record the SBOM SHA-256 in `summary.json`.

Do not run network-heavy enrichment (no `trivy sbom`) by default. Document the optional `trivy sbom` enrichment command in `README.md`.

---

## 9. Baseline diff

Compute four sets from `baseline.previous.json` and the current `baseline.json` keyed by finding `id`:

- `new`: in current, not in previous.
- `resolved`: in previous, not in current.
- `persisting`: in both, no severity change.
- `regressed`: in both, severity has increased.

Record counts and the full id lists in `summary.json` under `delta`. Mark resolved findings with `status: resolved` and write them, along with their last known data, into `baseline.json` under a separate `resolved` array (kept for one run for traceability, then dropped).

---

## 10. Rendering

All HTML files share a single stylesheet at `templates/report.css` and embed it inline at the top of each report (single-file HTML, no external assets, works offline). Use the following design tokens:

```
--bg:        #1b1f28
--bg-elev:   #232936
--bg-soft:   #2a3140
--border:    #3b4252
--text:      #d8dee9
--text-mute: #8892a6
--frost:     #5e81ac
--ice:       #88c0d0
--brand:     #3b8ef0
--ok:        #859900
--low:       #88c0d0
--medium:    #b58900
--high:      #cb4b16
--critical:  #dc322f
--info:      #6c71c4
```

Typography: system stack `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Inter", sans-serif`. Mono: `"JetBrains Mono", "Fira Code", ui-monospace, monospace`. Base size 14px, line-height 1.55. Headings: 600 weight, tight letter-spacing.

Layout: 1100px max content width, 32px gutters. Cards: `--bg-elev` background, 1px `--border` stroke, 8px radius, 16px padding. Severity is shown as a left border accent 4px wide in the severity color, plus a small pill chip.

### `tickets.html`

Severity-grouped board. Top bar: project name (from `package.json` / `pyproject.toml` / repo dir name), run timestamp, totals per severity, delta indicators (`+3 / -1` style). Below: five collapsible sections, one per severity, ordered critical to info. Each section lists finding cards with:

- Title, rule id, tool name, category chip.
- Location: clickable `path:line` (use `vscode://file/${absolutePath}:${line}` and a plain copy button).
- Code snippet (when present) in a mono block, truncated to 6 lines with a "show more" toggle.
- For SCA: package, current version, fixed versions.
- "Suggested fix" paragraph derived from the tool output. If none, omit; do not invent one.
- Action chips: `Copy as Jira`, `Mark false positive`, `Snooze 30d`. The latter two write to `security-report/triage.json` keyed by finding id; on subsequent runs, suppressed findings are filtered out of the headline counts but still listed in a "Suppressed" tab.

Top of page has a free-text filter and severity / category / tool toggles. Implement with vanilla JS, no frameworks. Data is embedded as a `<script type="application/json" id="findings">...</script>` block at the bottom; JS reads it once on load.

### `jira-tickets.html`

Same data, but one card per finding sized for Jira. Each card has:

- Suggested Jira summary: `[<severity>] <tool>: <short title> (<path>:<line>)`. Truncate to 200 chars.
- Suggested labels: `security`, `<category>`, `<tool>`, `<ecosystem-if-any>`.
- Suggested priority mapping: `critical -> Highest`, `high -> High`, `medium -> Medium`, `low -> Low`, `info -> Lowest`.
- A textarea preloaded with Atlassian wiki markup body:
  ```
  h3. Summary
  {{description}}

  h3. Location
  {{path}}:{{line_start}}-{{line_end}}

  {code}
  {{snippet}}
  {code}

  h3. Rule
  * Tool: {{tool}}
  * Rule: {{rule_id}}
  * CWE: {{cwe_joined}}
  * CVE: {{cve_joined}}
  * CVSS: {{cvss}}

  h3. Affected component
  * Ecosystem: {{ecosystem}}
  * Package: {{package_name}} {{package_version}}
  * Fixed in: {{fixed_versions_joined}}

  h3. References
  {{references_as_bullets}}

  h3. Acceptance
  * Finding does not reappear in the next security scan run.
  * No regression in dependent tests.

  h3. Provenance
  Generated by security-scan at {{generated_at}}, finding id {{id}}.
  ```
- A "Copy" button that copies summary, labels, priority and body to the clipboard as a JSON blob, plus a "Copy body only" button.
- Optional: if `~/.config/security-scan/jira.json` exists with `{base_url, project_key}`, render a "Create in Jira" deep link `<base_url>/secure/CreateIssueDetails!Init.jspa?pid=...&summary=...&description=...`. Otherwise omit.

### `diff.html`

Four columns: New, Regressed, Persisting, Resolved. Each column shows a count, a sparkline of the last 10 runs (read from `scans/*/findings.json` summary counts), and the list of finding ids with title and path. Top of page has a one-line headline:

```
+<new> new, <regressed> regressed, <persisting> persisting, -<resolved> resolved since <previous_run_id>
```

If this is the first run, show the headline `Baseline established. <total> findings recorded.`

---

## 11. Idempotency and re-run semantics

- Re-running the command without code changes must produce identical normalized `findings.json` byte-for-byte, except for `last_seen_run`.
- `RUN_ID` is the only authoritative timestamp. All other times come from tool outputs and are passed through unchanged.
- The `latest` symlink always points to the freshest scan directory.
- The first 12 historical scan directories are retained; older ones are deleted unless they are referenced by `summary.json.delta.history`. Print which directories were pruned.
- Suppressions (`triage.json`) are honoured across runs. A suppressed finding still appears in `baseline.json` with `suppressed: true` and a reason.

---

## 12. README.md inside `security-report/`

Generate a short README explaining:

- What the folder is.
- How to re-run: hand the security scan prompt back to the same coding agent (or any compatible one) and let it execute the workflow against the current tree. The prompt file itself is unchanged across runs.
- How to install missing tools: `./tools/bootstrap.sh` or `./tools/bootstrap.ps1`.
- How to read each HTML report.
- How to suppress a false positive (`triage.json` schema and example).
- How to enrich the SBOM with vulnerabilities offline:
  `trivy sbom security-report/sbom/cyclonedx.json --format sarif --output security-report/sbom/cyclonedx.vuln.sarif`
- A reminder that `security-report/scans/` is gitignored by design.

---

## 13. Failure modes

| Condition                            | Behaviour                                                                                                                                                                      |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| No language detected                 | Run universal scanners only. Write a note into `summary.json.warnings`.                                                                                                        |
| Tool present but errors on this repo | Mark `failed`, capture stderr (first 4 KiB), continue.                                                                                                                         |
| Required tool missing                | Halt before scanning. Print the HALT block from section 2 step 5 and wait for the user reply (`continue`, `proceed anyway`, `abort`). Never start scans until the gate clears. |
| Optional tool missing                | Mark `skipped: not installed`. List under `optional_missing:` in the HALT block when one fires; otherwise record silently in `_meta.json` and continue.                        |
| Tool times out                       | Mark `failed: timeout`.                                                                                                                                                        |
| Disk full / cannot write             | Abort with non-zero exit. Print the path that failed.                                                                                                                          |
| `git` not available                  | Skip history-based secrets scanning; filesystem-only secret scan still runs.                                                                                                   |
| Network blocked                      | Skip tools that require online vulnerability databases; record them as `degraded: offline` (e.g. `osv-scanner`, `dependency-check`).                                           |

---

## 14. Final stdout block

After rendering, print exactly:

```
[security-scan] run_id=<RUN_ID>
[security-scan] totals  critical=<n>  high=<n>  medium=<n>  low=<n>  info=<n>
[security-scan] delta   new=<n>  regressed=<n>  resolved=<n>  persisting=<n>
[security-scan] skipped tools=<csv>
[security-scan] reports security-report/tickets.html
[security-scan] reports security-report/jira-tickets.html
[security-scan] reports security-report/diff.html
[security-scan] sbom    security-report/sbom/cyclonedx.json
```

No additional commentary. Exit 0 if the scan completed (regardless of findings); exit 1 only on infrastructure failure.
