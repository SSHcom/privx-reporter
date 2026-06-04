# Reports High-Level Architecture

This document explains the high-level execution flow of report development, from CLI entrypoint to report implementation.

It intentionally stays at architecture level and avoids code-level details.

## End-to-end flow

At runtime, report execution follows this path:

1. The user runs `bin/report` (or `release/common/bin/report` copied to `$INSTALL_DIR/bin/report` in packaged environments).
2. The CLI entrypoint invokes `apps/python/lib/_report/main.py`.
3. The main flow loads `apps/python/reports/config.toml` and parses CLI arguments against that combined configuration.
4. Based on the parsed command and subcommand, the reporter resolves the target report group and report module under `apps/python/reports/`.
5. The selected report implementation runs and produces output.

## Configuration model

Report definitions are distributed and then combined:

- `apps/python/reports/<report-group>/group.toml` provides group-level command metadata.
- `apps/python/reports/<report-group>/<report>/in.toml` provides input/CLI argument metadata for an individual report.
- `apps/python/reports/<report-group>/<report>/out.toml` provides output-field metadata for an individual report.

These files are combined into a single runtime configuration file:

- `apps/python/reports/config.toml`

The combine step is executed by:

- `task combine-configs` (defined in `Taskfile.yml`)

That combined file is the source used by the reporter for CLI argument parsing and argument collection before report execution.

## Topology diagram

```text
User
  |
  v
bin/report (dev) or install `bin/report` from packaging
  |
  v
apps/python/lib/_report/main.py
  |
  +--> load and parse apps/python/reports/config.toml
  |         ^
  |         |
  |   task combine-configs
  |         |
  |   +-----+------------------------------+
  |   |                                    |
  |   v                                    v
  | apps/python/reports/<group>/group.toml
  |     apps/python/reports/<group>/<report>/{in.toml,out.toml}
  |
  v
apps/python/reports/<group>/<report>/report.py
  |
  v
report output
```

## Links

- Next: [Reports bootstrapping](reports_bootstrapping.md)
- [Back to development guide](../DEVELOPMENT_GUIDE.md)
