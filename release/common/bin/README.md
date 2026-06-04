# Install-only scripts (`release/common/bin`)

This directory is the packaging home for **install-only** command scripts. These scripts are copied into installed/container environments and are **not** the developer entrypoints for a repository checkout.

## Contract

- **Repository checkout (dev/CI):** use root [`bin/`](../../bin/) wrappers (`bin/report`, `bin/serve_ui`, etc.).
- **Installed/container environments:** use scripts from this directory (copied to `$REPORTER_HOME/bin/` or `/installer/bin/` during image build).
- Root `bin/` stays limited to thin forwarders for dev-facing commands; install scripts do not live there.

## Scripts

| Script         | Role                                          |
| -------------- | --------------------------------------------- |
| `admin`        | Admin CLI in installed environments           |
| `backup`       | Backup CLI in installed environments          |
| `create_env`   | Interactive `.env` creation for installs      |
| `post_install` | Post-install validation (`--secure` optional) |
| `report`       | Report CLI in installed environments          |
| `sync`         | Sync server entrypoint (container images)     |
| `ui`           | UI server entrypoint (container images)       |

Dockerfiles, installers, and [`release/`](../) build references use paths under `release/common/bin/*`.

## Related

- Dev command contract: [`docs/development/README.md`](../../docs/development/README.md#command-entrypoints-and-bin-contract)
- Production packaging: [`release/README.md`](../README.md)
