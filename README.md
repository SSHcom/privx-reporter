# PrivX Reporter

**A service for creating PrivX reports**

Developed by SSH Communications Security Oyj as a companion to PrivX — the just-in-time privileged access platform — the Reporter provides an easy-to-use reporting engine for common questions about the platform's state and usage. It covers most typical reporting needs out of the box, sparing you from writing custom scripts. For use cases beyond its scope, the official [Python](https://github.com/SSHcom/privx-sdk-for-python) and [Go](https://github.com/SSHcom/privx-sdk-go) SDKs remain available.

Real-time reports are fetched directly from PrivX APIs, while time-series reports use historical data stored in a local database that the sync server populates on a schedule.

Starting points:
- [Installation](docs/operations/install/README.md) - Install the Reporter. 
- [Quick Start](docs/development/QUICK_START.md) - Set up a local development environment.
- See more documentation [below](#documentation)

## Components

- **Reporter CLI** -  Runs report commands and generates report output.
  - Command: `bin/report`
  - Implementation: `apps/python/reports/`

- **UI** - Web interface for running available reports.
  - Command: `bin/serve_ui`
  - Implementation: `apps/python/ui/`

- **Sync Server** - Populates audit and connection data in the data database on a schedule.
  - Command: `bin/serve_sync`
  - Implementation: `apps/python/sync_server/`

- **Admin CLI** - Administrative commands for database migrations, sync server back-fills, etc.
  - Command:  `bin/admin`
  - Implementation: `apps/python/administration/`
  
- **Shared library** - Common functionality used by CLI, UI, and sync server.
  - Implementation: `apps/python/lib/`

> **Executing commands**: When running directly from the repository use `bin/<command>`. In production, `serve_ui` and `serve_sync` would typically be run as containerized services.

> **Developer notice:** It is strongly recommended to read the [Development Overview](docs/development/README.md) before making code or config changes as it covers easy-to-miss pitfalls. After reading it, continue with [Development Guide](docs/development/DEVELOPMENT_GUIDE.md).

## Documentation

### Operational Guides

- [System Requirements](docs/operations/SYSTEM_REQUIREMENTS.md)
- [Installation Guide](docs/operations/install/README.md)
- [CLI Operational Guide](docs/operations/CLI_GUIDE.md) - Operational CLI commands, options, and output behavior
- [UI Operational Guide](docs/operations/UI_ADMIN_GUIDE.md) - Operational UI behavior and access filtering
- [Sync Server Operational Guide](docs/operations/SYNC_SERVER_GUIDE.md) - Operational sync flow, stored data, and integrity behavior
- [Administration Operational Guide](docs/operations/CLI_ADMIN_GUIDE.md) - Operational administration CLI usage and module conventions
- [Environment variables](docs/operations/ENVIRONMENT_VARIABLES.md)

### Development

- [Development Overview](docs/development/README.md) - Project structure, tooling, and essential developer conventions
- [Development Guide](docs/development/DEVELOPMENT_GUIDE.md) 
- [Quick Start](docs/development/QUICK_START.md) - Local setup and how to run components
- [Testing Guide](docs/development/TESTING.md) - Test commands, scope selection, and database parity checks

### Deployment and Testing

- [Deployment](release/README.md) - Container build and runtime reference
- [Sync server live testing](live_test/README.md) - Load and integrity test harness

## Support & Commercial Services

This is a public open-source project licensed under Apache 2.0 and not covered by standard support SLA. Community feedback and contributions are welcome. Support is provided on a best-effort basis only. For dedicated support, customisations, or enterprise assistance, please raise a ticket via our support portal (https://care.ssh.com) or via your local support partner. Any requests would be assigned to your account manager.
