# Distributed Installation

In a distributed deployment the databases are provisioned externally and the Sync Server, UI, and CLI each run independently. This model suits production environments where database management, networking, and scaling are handled outside of Reporter.

```text
    +------------------------------+     +----------------------------+
    |         CLI host             |     |          UI host           |
    |                              |     |                            |
    | Install path: /opt/reporter  |     | Docker Engine / compose    |
    | CLI on host (not container): |     | +------------------------+ |
    |   - report command           |     | | reporter-ui container  | |
    |   - admin command            |     | +------------------------+ |
    +---------------+--------------+     +---------+------------------+
                     ^                              ^
                      \                            /
                       \                          /
                        \                        /
                         v                      v
                   +------+---------------------+----+
                   |     Remote PostgreSQL DBs       |
                   | (external, deployment-agnostic) |
                   |                                 |
                   | - admin database                |
                   | - data database (TimescaleDB)   |
                   +---------------+-----------------+
                                   ^
                                   |
                                   v
                    +--------------+--------------+
                    |      Sync Server host       |
                    |                             |
                    |  Docker Engine / compose    |
                    | +-------------------------+ |
                    | | reporter-sync container | |
                    | +-------------------------+ |
                    +-----------------------------+
```

## Databases

PrivX Reporter uses two PostgreSQL databases:

- A **data** database for synchronized report data (requires the **TimescaleDB** extension).
- An **admin** database for administration metadata.

They can run as separate instances or share a single combined instance. When sharing, TimescaleDB must be enabled on that instance. Both databases must be provisioned and reachable before installing any component. Have their connection details ready (host, port, database name, user, password, SSL mode). On a first-time installation the databases should be empty.

Database migrations are applied automatically when the Sync Server or UI starts. They can also be run explicitly from a CLI host with `admin migration up`.

## Supported platforms

SSH supports the distributed model on **Rocky Linux** or **Red Hat Enterprise Linux** hosts with Docker Engine:

- The CLI runs directly on a host of the supported type.
- The Sync Server and UI run as Docker containers on the same or separate hosts of the supported type.

Container orchestrators (ECS, Cloud Run, Kubernetes, etc.) are **not supported** — see [Running on a container orchestrator](#running-on-a-container-orchestrator) for technical guidance only.

## CLI

### Prerequisites

- **Host**:
  - [Docker](https://www.docker.com/) engine with `docker compose`
  - [Python](https://www.python.org/) 3.13 or newer
  - [UV](https://docs.astral.sh/uv/)
  - [Git](https://git-scm.com/)  

- Other
  - The `privxsshcom/privx-reporter-cli:latest` image available in the local Docker registry or on Docker Hub.

### Install

1. Verify prerequisites:

```sh
python3 -V
uv -V
docker compose version
git -v
```

2. Create the installation directory `/opt/reporter`:
   - `sudo mkdir -p /opt/reporter`
   - `chown $(id -u):$(id -g) /opt/reporter`

3. Run the installer:

```sh
docker run --rm \
  -e INSTALL_UID=$(id -u) \    # We use INSTALL_UID and INSTALL_GID to
  -e INSTALL_GID=$(id -g) \    # prevent installed files being owned by root.
  -e INSTALL_TYPE=distributed \
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

- CLI tools (`bin/report`, `bin/admin`, `bin/create_env`, `bin/post_install`).
- `.env-example` — template for database and PrivX connection variables.
- `.info` — install metadata used by `post_install` (for example `install=distributed`).

### Configure

Generate the `.env` file:

```sh
create_env --skip sync ui
```

You will be prompted for PrivX and database connection details and other configuration values.

## Sync Server

### Prerequisites

- Docker Engine with `docker compose`.
- The `privxsshcom/privx-reporter-sync:latest` image available in the local Docker registry or on Docker Hub.
- The data and admin databases are reachable from inside the container.

### Deploy

The Sync Server runs as a single Docker container. Supply environment variables via an `.env` file or the platform's env-var mechanism. See [Environment Variables](../ENVIRONMENT_VARIABLES.md) for the full variable reference.

Use [`release/reporter_sync/docker-compose-sync.yml`](../../../release/reporter_sync/docker-compose-sync.yml). Place the compose file on the target host, provide the required environment variables, and start:

```sh
docker compose -f docker-compose-sync.yml up -d
```

The Sync Server does not expose any ports — it connects outward to PrivX and to the databases.

## UI

### Prerequisites

- Docker Engine with `docker compose`.
- The `privxsshcom/privx-reporter-ui:latest` image available in the local Docker registry or on Docker Hub.
- The data and admin databases are reachable from inside the container.

### Deploy

The UI runs as a single Docker container, listening on port `8501`. There are two Docker Compose options:

#### Option 1 — Named volume

Use [`release/reporter_ui/docker-compose-ui.yml`](../../../release/reporter_ui/docker-compose-ui.yml). Reports are written to a Docker-managed named volume (`ui-reports`). Use this when you do not need direct host access to report files.

```sh
docker compose -f docker-compose-ui.yml up -d
```

#### Option 2 — Host-mapped volume

Use [`release/reporter_ui/docker-compose-ui-mapped.yml`](../../../release/reporter_ui/docker-compose-ui-mapped.yml). The container's report directory is mapped to a host directory set by `REPORT_OUT_DIR`. The directory must exist and be writable. Use this when report files need to be accessible on the host (backups, external processing, etc.).

```sh
docker compose -f docker-compose-ui-mapped.yml up -d
```

### Set UI super-admin password

On first install the UI bootstrap creates an `admin` user with a random password hash that is not stored anywhere. Before the first login, log in to the **UI host** (SSH or equivalent) and run:

```sh
docker exec -it reporter-ui /opt/reporter/bin/admin_passwd
```

The container name is `reporter-ui` when using the compose files linked above. Enter and confirm the new password when prompted (must meet the UI password policy).

### Accessing the UI

Once the container is running and the admin password is set, open `http://<host>:8501` and sign in as `admin`.

## Running on a container orchestrator

> This deployment model is **outside SSH's supported production environments** (Docker Engine on Rocky Linux or Red Hat Enterprise Linux). It is documented here as a technical option; it uses the same images and configuration surface as the compose options.

ECS, Cloud Run, Kubernetes and similar runtimes consume the images directly without `docker compose`. Push the SSH-distributed images into your registry and reference them from your deployment manifests.

If you need to build the images yourself, `release/build.sh sync|ui|cli` builds and inserts them into the local Docker registry.

Use the standalone compose files and [Environment Variables](../ENVIRONMENT_VARIABLES.md) as reference for the required environment variables. All `environment:` keys must be supplied via the platform's env-var mechanism (ECS task definition, Cloud Run environment variables, Kubernetes Secret/ConfigMap, etc.).

| Component   | Image                                    | Reference compose file                                                              |
| ----------- | ---------------------------------------- | ----------------------------------------------------------------------------------- |
| Sync Server | `privxsshcom/privx-reporter-sync:latest` | [`docker-compose-sync.yml`](../../../release/reporter_sync/docker-compose-sync.yml) |
| UI          | `privxsshcom/privx-reporter-ui:latest`   | [`docker-compose-ui.yml`](../../../release/reporter_ui/docker-compose-ui.yml)       |

The Sync Server does not expose any ports. The UI exposes port `8501`. If report files must persist or be accessible outside the container, attach a persistent volume to the container path set by `REPORT_OUT_DIR` (the compose files use `/root/reports`).
