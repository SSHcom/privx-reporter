# Operation Guides

This directory contains operational guides for running and administering PrivX Reporter components.

## Documents at a Glance

| Document                                          | Covers                                                                                                                                         |
| ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| [Installation](install/README.md)                 | Instructions for single host or distributed installation                                                                                       |
| [OIDC UI Authentication](OIDC_UI_AUTH_GUIDE.md)   | OIDC UI authentication operations: provider setup, required variables, user mapping, session behavior, and troubleshooting                     |
| [UI Administration](UI_ADMIN_GUIDE.md)            | UI operations: login/session behavior, user and group administration, report group views, host filtering by access groups, and troubleshooting |
| [CLI Reporting](CLI_GUIDE.md)                     | Using the CLI `report` command for creating reports                                                                                            |
| [CLI Administration](CLI_ADMIN_GUIDE.md)          | Using the CLI `admin` command for database migrations and audit event sync management                                                          |
| [Sync Server](SYNC_SERVER_GUIDE.md)               | Sync server runtime behavior, ingestion flow, source-specific logic (audit/connection), idempotency/integrity model, and range clamp behavior  |
| [Environment Variables](ENVIRONMENT_VARIABLES.md) | Environment variable reference for database, sync server, reporter, UI, and PrivX API configuration                                            |

## Suggested Reading Paths

| Task or Issue                              | Reading Path                                                                                                                                           |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **Installation**                           | [`SYSTEM_REQUIREMENTS.md`](SYSTEM_REQUIREMENTS.md) -> [`install/README.md`](install/README.md)                                                         |
| **Operate reports via CLI**                | [`CLI_GUIDE.md`](CLI_GUIDE.md) -> [`ENVIRONMENT_VARIABLES.md`](ENVIRONMENT_VARIABLES.md)                                                               |
| **Administer users and permissions in UI** | [`UI_ADMIN_GUIDE.md`](UI_ADMIN_GUIDE.md) -> [`ENVIRONMENT_VARIABLES.md`](ENVIRONMENT_VARIABLES.md)                                                     |
| **Operate OIDC login for UI**              | [`OIDC_UI_AUTH_GUIDE.md`](OIDC_UI_AUTH_GUIDE.md) -> [`ENVIRONMENT_VARIABLES.md`](ENVIRONMENT_VARIABLES.md)                                             |
| **Operate and troubleshoot data sync**     | [`SYNC_SERVER_GUIDE.md`](SYNC_SERVER_GUIDE.md) -> [`CLI_ADMIN_GUIDE.md`](CLI_ADMIN_GUIDE.md) -> [`ENVIRONMENT_VARIABLES.md`](ENVIRONMENT_VARIABLES.md) |
| **Run admin/database migrations**          | [`CLI_ADMIN_GUIDE.md`](CLI_ADMIN_GUIDE.md)                                                                                                             |
| **Manage audit event sync allowlist**      | [`CLI_ADMIN_GUIDE.md`](CLI_ADMIN_GUIDE.md)                                                                                                             |
