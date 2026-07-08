# Standalone Installation

In a standalone deployment, all components — Reporter CLI, Sync Server, UI and two PostgreSQL databases — run on a single host. Docker Compose manages the Sync Server, UI, and database containers, while the CLI runs directly on the host.

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


No external database provisioning is needed — the standalone compose files include local PostgreSQL containers.

## Document contents

**Quick Start**

1. [Installation](#installation)
2. [Configuration](#configuration)
3. [Startup](#startup)

**Reference**

- [Database migrations](#database-migrations)
- [How to handle OIDC environment variables](#how-to-handle-oidc-environment-variables)
- [Backups](#backups)
  - [Database backup](#database-backup)
  - [Create a portable backup archive](#create-a-portable-backup-archive)
- [Alternative configurations](#alternative-configurations)
  - [UI TLS certificate](#ui-tls-certificate)
  - [Using external database(s)](#using-external-databases)

---

## Installation

### 1 ) Verify prerequisites:

```sh
 python3 -V
 uv -V
 docker compose version
 git --version
```

### 2 ) Create the installation directory `/opt/reporter`:
  - `sudo mkdir -p /opt/reporter`
  - `sudo chown $(id -u):$(id -g) /opt/reporter`

### 3 ) Run the installer:
  ```sh
   # Use INSTALL_UID and INSTALL_GID to prevent installed files from being owned by root.
   docker run --rm \
     -e INSTALL_UID=$(id -u) \
     -e INSTALL_GID=$(id -g) \
     -v /opt/reporter:/install \
     privxsshcom/privx-reporter-cli:latest
  ```

After the installation, follow the on-screen instructions (also available in `/opt/reporter/post_install.txt`). This document covers the same instructions but with more details.

The installer deploys the following to `/opt/reporter`:

- CLI tools to `bin/`: `**report, admin, backup, post_install, create_env**`
- Docker and Compose files 
  - `docker-compose.yml` — Sync Server, UI, and two local PostgreSQL containers when `ENV_SOURCE=db`.
  - `docker-compose-env.yml` — same services when `ENV_SOURCE=env` (all settings read from `.env`).
  - `Dockerfile-backup` — used by both compose files for the database backup service.
- `.env-example` — template for all required environment variables.
- `.info` — install metadata used by `post_install`
- `.pg-ssl/` — self-signed TLS certificate and `pg_hba.conf` for the local database containers.
- Various directories containing code used for commands and servers

### 4 ) Add the reporter binaries to your PATH:
  ```sh
   echo 'export REPORTER_HOME=/opt/reporter' >> ~/.bashrc
   echo 'export PATH="/opt/reporter/bin:$PATH"' >> ~/.bashrc
   source ~/.bashrc
  ```
### 5 ) Run post-install validations and updates:
  ```sh
   post_install --secure
  ```
   Using the `--secure` option will make the command update Python dependencies having potential security issues.

## Configuration

### 1 ) Generate the `.env` file

Use the interactive configuration tool. We skip configuring the database as we want the default connection setup.

```sh
create_env --skip db
```

You can also apply defaults for the UI and Sync Server: `create_env --skip db ui sync`).

If you decide to store configuration in the database (recommended), you can do modifications later in the UI configuration page.

**Key prompts**

**Note**: The following environment values are **always** written to `.env`, regardless of where other configuration is stored: `DB_*`, `ENV_SOURCE`, `REPORT_OUT_DIR`, and `BACKUP_DIR`.

The table below shows the most important prompts for a standalone installation.

| Prompt                      | Notes                                                                                                                                |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| **Output `.env` path**      | Use the default: `/opt/reporter/.env`                                                                                                |
| **Configuration source**    | `database` (recommended) or `.env file` — sets `ENV_SOURCE`                                                                          |
| **Standalone installation** | Answer **Yes** — this configures CLI, Sync Server, UI, and databases to be run on a single host                                      |
| **Report output directory** | `REPORT_OUT_DIR` — Select where to store generated reports                                                                           |
| **Backup directory**        | `BACKUP_DIR` — Select where backups are stored. See [Database backup](#database-backup)                                              |
| **Other prompts**           | If you picked `.env` as the configuration source, you will be prompted for details about the PrivX connection, Sync Server, UI, etc. |

### 2 ) Create required host directories

```sh
mkdir -p /opt/reporter/.volumes/data-db /opt/reporter/.volumes/admin-db
mkdir -p <REPORT_OUT_DIR>   # value from .env
mkdir -p <BACKUP_DIR>       # value from .env (standalone installs)
```

## Startup

### 1 ) Start Docker containers

Change directory to `/opt/reporter` 

Determine the correct `docker compose` command:

| `/opt/reporter/.env -> ENV_SOURCE` | File                     | Start command                                    |
| ---------------------------------- | ------------------------ | ------------------------------------------------ |
| `db`                               | `docker-compose.yml`     | `docker compose up -d`                           |
| `env`                              | `docker-compose-env.yml` | `docker compose -f docker-compose-env.yml up -d` |


### 2 ) Verify that containers are running

Running `docker ps` should show something like this:

```
CONTAINER ID   IMAGE   COMMAND       CREATED          STATUS                   PORTS      NAMES
270e95ea49ba   aed…    "reporter…"   15 seconds ago   Up 15 seconds            0.0.0.0…   reporter-ui
409affbb5677   7ce…    "reporter…"   15 seconds ago   Up 15 seconds                       reporter-sync
71fe7281bb08   rep…    "python3…"    15 seconds ago   Up 15 seconds            5432/tc…   reporter-backup
9cb47664374f   tim…    "/bin/sh…     15 seconds ago   Up 15 seconds (healthy)  0.0.0.0…   reporter-data-db
e89aa6bc109c   pos…    "/bin/sh…"    15 seconds ago   Up 15 seconds (healthy)  0.0.0.0…   reporter-admin-db
```

### 3 ) Set UI super-admin password

On first install the UI bootstrap creates a super `admin` user with a random password hash that is not stored anywhere. Set a known password before the first login:

```sh
docker exec -it reporter-ui /opt/reporter/bin/admin_passwd
```

Enter and confirm the new password when prompted.

This is not necessary on subsequent installs provided the admin database is intact

### 4 ) Access the UI

Open `https://<host>:8501` and sign in as `admin` with the password you just set.

### 5 ) App Configuration

Changing the configuration differs depending on the storage medium:

| `/opt/reporter/.env -> ENV_SOURCE` | Where to make the changes                                                                                           |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `db`                               | Log in as super _admin_ and apply changes on the _App Configuration_ page.                                          |
| `env`                              | Modify the `/opt/reporter/.env` file followed by: `docker compose -f docker-compose-env.yml up -d --force-recreate` |

### 6 ) Post installation notes

If the configuration medium is the database, go through the following in the App Configuration page:
  - Configure the Sync Server to make it start collecting PrivX records
  - Configure OIDC providers (if used)

If the configuration medium is the `.env` file:
  - ALWAYS add `-f docker-compose-env.yml` as extra argument if you need to run `docker compose` 

**IMPORTANT**:

- Never change database connection environment variables (`DB_DATA_*`, `DB_ADMIN_*`) in `.env` unless you are intentionally switching to external databases. In standalone deployments these values are expected to point to the local compose services (`reporter-data-db`, `reporter-admin-db`) and their initialized data volumes.
 
- When enabling backup, take number of records being inserted to the data database into account. If the number is very high (in the millions), consider using a different backup solution.


## Database migrations

Migrations are applied automatically when the Sync Server or UI starts for the first time. To run them manually:

```sh
admin migration up
```

## How to handle OIDC environment variables

The `create_env` script does not create OIDC-related variables.

**If `ENV_SOURCE=db`**:
- Configure OIDC provider settings in **App Configuration**.

**If `ENV_SOURCE=env`**
- Set `OIDC_1_ENABLED=true` / `OIDC_2_ENABLED=true` in `.env`
- Add OIDC provider variables to the file
- Uncomment required OIDC entries in `docker-compose-env.yml` under `reporter-ui -> environment`:
  - Enable flags (`OIDC_1_ENABLED`, `OIDC_2_ENABLED`)
  - Active provider slot variables (`OIDC_1_*` and/or `OIDC_2_*`)
  - Optional global OIDC variables (`OIDC_AUTO_PROVISION*`, `OIDC_GROUP_*`) only when used
  - Keep unused provider slot variables commented (for example keep `OIDC_2_*` commented when only provider 1 is used)

Referencs:
- [OIDC Auth guide](../OIDC_UI_AUTH_GUIDE.md) for more OIDC details.
- [Environment variables](../ENVIRONMENT_VARIABLES.md)

## Backups

### Database backup

The `reporter-backup` service (run as a Docker container) periodically dumps the database tables according to:

- `BACKUP_DIR` - dump file location
- `BACKUP_CONFIG` - backup configuration

`BACKUP_DIR` is environment-based in both modes. `BACKUP_CONFIG` source depends on `ENV_SOURCE`:
- `ENV_SOURCE=env`: configure both `BACKUP_DIR` and `BACKUP_CONFIG` in `.env`.
- `ENV_SOURCE=db`: configure `BACKUP_DIR` in `.env` and `BACKUP_CONFIG` in App Config.

When `ENV_SOURCE=db`, backup is disabled until `BACKUP_CONFIG` is enabled in App Config. The running backup service checks for enablement every 5 minutes, so it starts automatically within up to 5 minutes after enabling.

Example:

```text
BACKUP_DIR=/home/<privx-user>/db-backups
BACKUP_CONFIG=<enabled>,<target>,<interval-minutes>,<snapshots>
```

| Field              | Values               | Default | Notes                                    |
| ------------------ | -------------------- | ------- | ---------------------------------------- |
| `enabled`          | `true`, `false`      | `false` |                                          |
| `target`           | `admin`,`data`,`all` | `all`   | Which databases to dump                  |
| `interval-minutes` | number (min 60)      | `720`   | Dump frequency; `1440` = every 24 h.     |
| `snapshots`        | number (min 1)       | `5`     | Dumps kept per database (oldest pruned). |


Dumps are written as `<target>-<UTC-timestamp>.dump` using `pg_dump -Fc` and are restorable with `pg_restore`.

**Note**: The latest database dump can be archived together with other important files. See the *Create a portable backup archive* section for details.

**Restoring the databases**

The  typical steps would be

- Make a clean reporter installation
  - Do not run the full stack immediately. The restore will fail if you do.
- Create the `.env` file
- Start the PostgreSQL databases (use the [compose file](#compose-file) for your `ENV_SOURCE`):
  ```sh
  cd /opt/reporter

  # If ENV_SOURCE=db
  docker compose up reporter-admin-db reporter-data-db -d

  # If ENV_SOURCE=env
  docker compose -f docker-compose-env.yml up reporter-admin-db reporter-data-db -d
  ```
- Restore tables
  - `pg_restore -h localhost -p <port> -U <user> -d report_admin <backup-dir>/admin-<timestamp>.dump`
  - `pg_restore -h localhost -p <port> -U <user> -d report_data <backup-dir>/admin-<timestamp>.dump`
- Start the remaining containers:
  ```sh
  # If ENV_SOURCE=db (default)
  docker compose up -d

  # If ENV_SOURCE=env
  docker compose -f docker-compose-env.yml up -d
  ```

### Create a portable backup archive

The `backup` command bundles the **latest** database dump(s) from `BACKUP_DIR` together with restore-critical configuration (`.env`, `docker-compose.yml`, `.pg-ssl/`, etc.) into a single `tar.gz` archive. If you use `ENV_SOURCE=env`, keep a copy of `docker-compose-env.yml` separately — the archive does not include it.

> **Precondition:** all Reporter containers must be stopped. The script refuses to run while any of `reporter-ui`, `reporter-sync`, `reporter-data-db`, `reporter-admin-db`, or `reporter-backup` is up.

```sh
cd /opt/reporter

# ENV_SOURCE=db (default)
docker compose down

# ENV_SOURCE=env
docker compose -f docker-compose-env.yml down

backup /path/to/destination
```

This writes `/path/to/destination/reporter-backup-<UTC-timestamp>.tar.gz`. Restart with the matching [compose file](#compose-file):

```sh
# ENV_SOURCE=db (default)
docker compose up -d

# ENV_SOURCE=env
docker compose -f docker-compose-env.yml up -d
```

See the previous section on how to restore the databases using `pg_restore`.

## Alternative configurations

### UI TLS certificate

The `reporter-ui` container starts with HTTPS enabled by default, using a self-signed certificate bundled in the image at `/opt/reporter/certs/fullchain.pem` and `/opt/reporter/certs/privatekey.pem`.

`/opt/reporter/certs/` is a path inside the `reporter-ui` container image.

To replace the UI certificate, place certificate files in a host directory (for example `/opt/reporter/ui-certs`) and mount that host directory to `/opt/reporter/certs/` in the `reporter-ui` service of your [compose file](#compose-file) (`docker-compose.yml` or `docker-compose-env.yml`):

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

If you want to have the data and/or admin databases elsewhere (e.g. a managed PostgreSQL service):

- run `create_env` without `--skip db` to provide your own DB connection details
- Skip creating the local DB volume directories (`/opt/reporter/.volumes/data-db`, `/opt/reporter/.volumes/admin-db`).
- Remove the database service sections from your [compose file](#compose-file) before starting:
  - Remove the `reporter-data-db` service
  - Remove the `reporter-admin-db` services 
  - Also remove any `depends_on` references to those services.

