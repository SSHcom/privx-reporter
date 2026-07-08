# PrivX Reporter v1.2.0

**Note**: This release introduces breaking changes to configuration

For the standalone installation the following upgrade steps are recommended:
- `cd /opt/reporter`
- `docker compose down`
- `cp .env <some backup directory>/`
- Clean up the installation directory
  - `cd /opt/reporter/`
  - `rm -rf * .env* .info .pg-ssl .venv`
  - **Note**: do not delete `/opt/reporter/.volumes` unless you want a blank slate
- Remove docker images having `latest` tag from your environment to ensure we pull latest images from [hub.docker.com](https://hub.docker.com)
  - `docker rmi privxsshcom/privx-reporter-cli:latest`
  - `docker rmi privxsshcom/privx-reporter-ui:latest`
  - `docker rmi privxsshcom/privx-reporter-sync:latest`
- Install according to `docs/operations/install/STANDALONE.md`
  - Recommended: Chose _database_ for configuration storage
  - Use values from your backed up `.env` file
  - Include _recreate_ option when starting containers: `docker compose up --force-recreate -d`

## Changes

- **New** _App Configuration_ UI admin page feature
  - Most configuration values can be configured via this page
  - For a standalone installation the database configuration still "lives" in `.env` as it should not be changed.
  - An `.env`-file only setup is still supported
  - Note that OIDC configuration has changed.
    - Environment variables have been renamed
    - A maximum of two providers is supported
  - See `docs/operations/install/STANDALONE.md` document for more details

- **New** UI super-admin password update feature
  - `UI_TMP_ADMIN_PASSWORD` environment variable is no longer used (can be removed from `.env` if present)
  - On the first startup (blank database) bootstrap creates `admin` user with an unknown random hash as password
  - To set set a password run `docker exec -it reporter-ui /opt/reporter/bin/admin_passwd`. It is not required for an existing database that already has admin credentials. The tool can be used at any time to change the password.

- **New** _My Page_ UI feature
  - A page for reports/tools specific to the logged in user
  - Only users matching PrivX username (principal) can see the page
  - The page has a single "Available Host Accounts" report generator. The user can see what accounts (available to the user) are are not in use on a host.

- Fixed: OIDC issuer URI bug
  - Issuer URIs ending with a slash were trimmed (slash removed) causing authentication flow to break