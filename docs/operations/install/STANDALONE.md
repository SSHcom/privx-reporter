# Standalone Installation

In a standalone deployment, all components — Reporter CLI, Sync Server, UI and two PostgreSQL databases — run on a single host. A Docker Compose file manages the Sync Server, UI, and database containers, while the CLI runs directly on the host.

```text
+------------------------------------------------------------+
|                   Standalone host (single node)            |
|                                                            |
|  Install path: /opt/reporter                               |
|                                                            |
|  CLI on host:                                              |
|    - report command                                        |
|    - admin command                                         |
|                                                            |
|  Docker Engine / docker compose                            |
|        +-------------+             +---------------+       |
|        | reporter-ui |             | reporter-sync |       |
|        | (container) |             | (container)   |       |
|        +------+------+             +------+--------+       |
|               |                           |                |
|               +---------------------------+                |
|                            |                               |
|          +-----------------+-----------------+             |
|          |                                   |             |
|   +------+----------------+        +---------+-----------+ |
|   | reporter-admin-db     |        | reporter-data-db    | |
|   | PostgreSQL container  |        | PostgreSQL container| |
|   +-----------------------+        +---------------------+ |
+------------------------------------------------------------+
```

## Supported platforms

SSH supports the standalone model on a single **Rocky Linux** or **Red Hat Enterprise Linux** host with Docker Engine. All components (CLI, Sync Server, UI, and local databases) run on that host.

The CLI can also be installed on macOS, but this is not a supported production configuration.

## Prerequisites

- **Host:**
  - [Docker](https://www.docker.com/) engine with `docker compose`
  - [Python](https://www.python.org/) 3.13 or newer
  - [UV](https://docs.astral.sh/uv/)
  - [Git](https://git-scm.com/)

- **Docker images** available in the local Docker registry or on Docker Hub:

  | Image                                    | Purpose       |
  | ---------------------------------------- | ------------- |
  | `privxsshcom/privx-reporter-cli:latest`  | CLI installer |
  | `privxsshcom/privx-reporter-sync:latest` | Sync Server   |
  | `privxsshcom/privx-reporter-ui:latest`   | UI            |

No external database provisioning is needed — the standalone compose file includes local PostgreSQL containers.

## Install

1. Verify prerequisites:

```sh
python3 -V
uv -V
docker compose version
git --version
```

2. Create the installation directory `/opt/reporter`:
   - `sudo mkdir -p /opt/reporter`
   - `sudo chown $(id -u):$(id -g) /opt/reporter`

3. Run the installer:

```sh
# Use INSTALL_UID and INSTALL_GID to prevent installed files from being owned by root.
docker run --rm \
  -e INSTALL_UID=$(id -u) \
  -e INSTALL_GID=$(id -g) \
  -v /opt/reporter:/install \
  privxsshcom/privx-reporter-cli:latest
```

4. Add the reporter binaries to your PATH:

```sh
echo 'export REPORTER_HOME=/opt/reporter' >> ~/.bashrc
echo 'export PATH="/opt/reporter/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

5. Run post-install validation:

```sh
post_install --secure
```

The installer deploys:

- CLI tools (`bin/report`, `bin/admin`, `bin/create_env`, `bin/backup`, `bin/post_install`).
- `docker-compose.yml` — defines the Sync Server, UI, and two local PostgreSQL containers (data with TimescaleDB, admin).
- `Dockerfile-backup` — used by `docker-compose.yml` for running the database backup service.
- `.env-example` — template for all required environment variables.
- `.info` — install metadata used by `post_install` (for example `install=standalone`).
- `.pg-ssl/` — self-signed TLS certificate and `pg_hba.conf` for the local database containers.
- Various directories containing code used for commands and servers: `administration`, `backup_server`, `reports`, and `lib`.

## Configure

Generate the `.env` file using the interactive configuration tool.

```sh
create_env --db defaults --sync defaults --ui defaults
```

This populates `.env` with some defaults before prompting for other configuration values.

To customize Sync Server and UI behavior, omit `--sync defaults` and/or `--ui defaults`, or edit `.env` manually afterwards. Always use defaults for the database.

If you want to enable running backups of the databases (configured by `BACKUP_CONFIG`), refer to the _Backups -> Database backups_ section below.

Before starting Docker Compose, create the required host directories:

```sh
mkdir -p /opt/reporter/.volumes/data-db /opt/reporter/.volumes/admin-db
mkdir -p <REPORT_OUT_DIR>   # use the value of REPORT_OUT_DIR from .env
mkdir -p <BACKUP_DIR>   # use the value of BACKUP_DIR from .env
```

## Start

From the installation directory:

```sh
cd /opt/reporter
docker compose up -d
```

This starts:

- Two PostgreSQL containers (`reporter-data-db`, `reporter-admin-db`) with health checks.
- The Sync Server (`reporter-sync`), which waits for both databases to become healthy.
- The UI (`reporter-ui`), accessible on port `8501`.
- The backup service (`reporter-backup`), which dumps the database(s) to `/opt/reporter/.backup/` on the schedule set by `BACKUP_CONFIG`.

`docker ps` should show the following running containers:
- `privxsshcom/privx-reporter-ui:latest`
- `privxsshcom/privx-reporter-sync:latest`
- `reporter-backup` (built locally from `Dockerfile-backup`)
- `timescale/timescaledb:latest-pg18`
- `postgres:18`

Access the UI at `https://<host>:8501`. Log in with the admin password set in `.env` and change it immediately.

## Database migrations

Migrations are applied automatically when the Sync Server or UI starts for the first time. To run them manually:

```sh
admin migration up
```

### Apply environment variable changes

After editing `.env`, recreate the containers so the new values are loaded:

```sh
cd /opt/reporter
docker compose up -d --force-recreate
```

You can also run `docker compose down` and then `docker compose up -d`, but that is typically unnecessary for environment changes.

Do not change database connection environment variables (`DB_DATA_*`, `DB_ADMIN_*`) unless you are intentionally switching to external databases. In standalone deployments these values are expected to point to the local compose services (`reporter-data-db`, `reporter-admin-db`) and their initialized data volumes. Changing them can cause sync/ui startup failures or authentication/connection mismatches.

### How to handle OIDC  environment variables


Since the `create_env` script does not create OIDC related variables, you must manually add them to the `.env` file:

- You can copy from the example below and modify as needed.
- Replace `ENTRA_` with the OIDC provider you want to use (multiple providers are supported)
- Remember to modify `UI_AUTH_MODE` accordingly

- OIDC example configuration:
  ```
  # OIDC providers (uncomment and adjust when UI_AUTH_MODE includes these provider ids)
  #
  # IMPORTANT: Also uncomment the corresponding variables in the docker-compose.yml file.
  ##
  # Entra ID (public cloud)
  # ENTRA_OIDC_ISSUER=https://login.microsoftonline.com/<tenant-id>/v2.0
  # ENTRA_OIDC_CLIENT_ID=<app-client-id>
  # ENTRA_OIDC_CLIENT_SECRET=<client-secret>
  # ENTRA_OIDC_REDIRECT_URI=http://localhost:8501/0_Login
  # ENTRA_OIDC_POST_LOGOUT_REDIRECT_URI=http://localhost:8501/
  # ENTRA_OIDC_SCOPES="openid profile email offline_access"
  # ENTRA_OIDC_PROMPT=select_account
  # ENTRA_OIDC_STATE_SECRET=<long-random-secret>
  #
  # Optional: OIDC auto-provisioning (creates Reporter local users on first successful IdP login)
  # OIDC_AUTO_PROVISION=false
  # OIDC_AUTO_PROVISION_DEFAULT_ROLE=viewer
  # OIDC_AUTO_PROVISION_REQUIRE_EMAIL=false
  # OIDC_AUTO_PROVISION_ALLOWED_EMAIL_DOMAINS=example.com,example.org
  #
  # Optional: map IdP group/role claims to Reporter user groups.
  # Claim path can be simple (groups) or dotted (realm_access.roles).
  # Mapping applies to auto-provisioned users. Existing local users are not altered.
  # OIDC_GROUP_CLAIM=groups
  # OIDC_GROUP_MAPPING='{"idp-admin":"admin","idp-viewer":"viewer","idp-viewer2":"viewer"}'
  ```
- You must also expose the variables in `/opt/reporter/docker-compose.yml`.
- For an _Entra_ configuration add the following to `reporter-ui -> environment`:
   ```
  ENTRA_OIDC_ISSUER: ${ENTRA_OIDC_ISSUER}
  ENTRA_OIDC_CLIENT_ID: ${ENTRA_OIDC_CLIENT_ID}
  ENTRA_OIDC_CLIENT_SECRET: ${ENTRA_OIDC_CLIENT_SECRET}
  ENTRA_OIDC_REDIRECT_URI: ${ENTRA_OIDC_REDIRECT_URI}
  ENTRA_OIDC_POST_LOGOUT_REDIRECT_URI: ${ENTRA_OIDC_POST_LOGOUT_REDIRECT_URI}
  ENTRA_OIDC_SCOPES: ${ENTRA_OIDC_SCOPES}
  ENTRA_OIDC_PROMPT: ${ENTRA_OIDC_PROMPT}
  ENTRA_OIDC_STATE_SECRET: ${ENTRA_OIDC_STATE_SECRET}
  ```
- For other providers replace `ENTRA_` with actual provider.

- If you want to use auto provisioning of users, also add:
  ```
  OIDC_AUTO_PROVISION: ${OIDC_AUTO_PROVISION}
  OIDC_AUTO_PROVISION_DEFAULT_ROLE: ${OIDC_AUTO_PROVISION_DEFAULT_ROLE}
  OIDC_AUTO_PROVISION_REQUIRE_EMAIL: ${OIDC_AUTO_PROVISION_REQUIRE_EMAIL}
  OIDC_AUTO_PROVISION_ALLOWED_EMAIL_DOMAINS:${OIDC_AUTO_PROVISION_ALLOWED_EMAIL_DOMAINS}
  OIDC_GROUP_CLAIM: ${OIDC_GROUP_CLAIM}
  OIDC_GROUP_MAPPING: ${OIDC_GROUP_MAPPING}
  ```

Reference [OIDC Auth guide](../OIDC_UI_AUTH_GUIDE.md) for more OIDC details.


## Backups

### Database backup

The `reporter-backup` service (run as a Docker container) periodically dumps the database tables according to:
- `BACKUP_DIR` - dump file location
- `BACKUP_CONFIG` - backup configuration

Example:

```text
BACKUP_DIR=/home/<privx-user>/db-backups
BACKUP_CONFIG=<enabled>,<target>,<interval-minutes>,<snapshots>
```

| Field              | Values                     | Default | Notes                                    |
| ------------------ | -------------------------- | ------- | ---------------------------------------- |
| `enabled`          | `true` \| `false`          | `true`  | Set `false` to disable scheduled dumps.  |
| `target`           | `admin` \| `data` \| `all` | `all`   | Which database(s) to dump.               |
| `interval-minutes` | number (min 60)            | `720`   | Dump frequency; `1440` = every 24 h.     |
| `snapshots`        | number (min 1)             | `5`     | Dumps kept per database (oldest pruned). |

Dumps are written as `<target>-<UTC-timestamp>.dump` using `pg_dump -Fc` and are restorable with `pg_restore`.

**Note**: The latest database dump can be archived together with other important files. See the _Create a portable backup archive_ section for details.

#### Restoring the databases

The  typical steps would be

- Make a clean reporter installation
  - Do not run `docker compose up -d` immediately. The restore will fail if you do.
- Create the `.env` file
- Start the PostgreSQL databases
  -  `docker compose up reporter-admin-db -d`
  -  `docker compose up reporter-data-db -d`
- Restore tables
  - `pg_restore -h localhost -p <port> -U <user> -d report_admin <backup-dir>/admin-<timestamp>.dump`
  - `pg_restore -h localhost -p <port> -U <user> -d report_data <backup-dir>/admin-<timestamp>.dump`
- Now you can run the rest of the Docker containers
  - `docker compose up -d`


### Create a portable backup archive

The `backup` command bundles the **latest** database dump(s) from the configured backup directory (`BACKUP_DIR` or default `/opt/reporter/.backup/`) together with the restore-critical configuration (`.env`, `docker-compose.yml`, `.pg-ssl/`, etc) into a single `tar.gz` archive.

> **Precondition:** all Reporter containers must be stopped. The script refuses to run while any of `reporter-ui`, `reporter-sync`, `reporter-data-db`, `reporter-admin-db`, or `reporter-backup` is up.

```sh
cd /opt/reporter
docker compose down
backup /path/to/destination
```

This writes `/path/to/destination/reporter-backup-<UTC-timestamp>.tar.gz`. Restart the deployment afterwards with `docker compose up -d`.

See the previous section on how to restore the databases using `pg_restore`.

## Alternative configurations

### UI TLS certificate

The `reporter-ui` container starts with HTTPS enabled by default, using a self-signed certificate bundled in the image at `/opt/reporter/certs/fullchain.pem` and `/opt/reporter/certs/privatekey.pem`.

`/opt/reporter/certs/` is a path inside the `reporter-ui` container image.

To replace the UI certificate, place certificate files in a host directory (for example `/opt/reporter/ui-certs`) and mount that host directory to `/opt/reporter/certs/` in the `reporter-ui` service (`/opt/reporter/docker-compose.yml`):

- `fullchain.pem`
- `privatekey.pem`

Example:

```yaml
services:
  reporter-ui:
    volumes:
      - <REPORT_OUT_DIR>:/root/reports
      - /opt/reporter/ui-certs:/opt/reporter/certs:ro
```

Mounting `/opt/reporter/certs/` overrides the directory from the image for that container, so the UI will use only the files from the mounted host path.

If you remove `SSL_CERT` and `SSL_KEY` from the `reporter-ui` service, the UI starts without SSL. This is useful when TLS is terminated by a secure reverse proxy or load balancer in front of the UI.

### Using external database(s)

If you want to manage the data and/or admin database(s) elsewhere (e.g. a managed PostgreSQL service), adjust the setup as follows:

1. Run `create_env` without `--db defaults` so you can provide your own DB connection details:

```sh
create_env --sync defaults --ui defaults
```

2. Skip creating the local DB volume directories (`/opt/reporter/.volumes/data-db`, `/opt/reporter/.volumes/admin-db`).

3. Remove the database service sections from `docker-compose.yml` before starting (the `reporter-data-db` and `reporter-admin-db` services and their volume definitions). Also remove any `depends_on` references to those services.

