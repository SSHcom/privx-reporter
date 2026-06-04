# `apps/` — language-isolated components

Application code lives under `apps/<language>/`, not at the repository root. This keeps Python and future Go trees separate and avoids naming clashes (`lib/`, `sync_server/`, etc.).

## Layout

| Path                 | Contents                                                                              |
| -------------------- | ------------------------------------------------------------------------------------- |
| [`python/`](python/) | Shared library, reports, administration, sync server, UI, backup daemon               |
| `go/` (planned)      | Go commands and `internal/` packages — see [`../Golang-notes.md`](../Golang-notes.md) |

All Python source is under `apps/python/`; there are no root-level `lib/` or `reports/` directories in the repository checkout.

## Production install (flat Python)

Installed environments use a **flat** layout under `/opt/reporter/` (e.g. `lib/`, `reports/`, `sync_server/`), not `apps/python/…`. That matches Hatch package names and existing config paths (`reports/config.toml`).

Go services ship as **binaries** (or containers), typically under `/opt/reporter/bin/`, not as a second `lib/` tree on the install root. Details: [`Golang-notes.md`](../Golang-notes.md).

## Tests

Python tests mirror this tree under [`tests/python/`](../tests/python/) (see [`docs/development/TESTING.md`](../docs/development/TESTING.md)).

## Developer entrypoints

Stable commands stay at repository root [`bin/`](../bin/); they forward to `apps/python/…/run` scripts. Install-only scripts are under [`release/common/bin/`](../release/common/bin/).
