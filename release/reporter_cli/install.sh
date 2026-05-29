#!/bin/sh
set -eu

# Install mode defaults to standalone unless explicitly overridden.
install_type="${INSTALL_TYPE:-standalone}"

for arg in "$@"; do
  case "$arg" in
    --install-type=*)
      install_type="${arg#--install-type=}"
      ;;
    *)
      echo "FATAL: unknown argument: $arg" >&2
      echo "Usage: [--install-type=standalone|distributed]" >&2
      exit 1
      ;;
  esac
done

case "$install_type" in
  standalone|distributed)
    ;;
  *)
    echo "FATAL: invalid INSTALL_TYPE: $install_type" >&2
    echo "Valid values: standalone, distributed" >&2
    exit 1
    ;;
esac

mkdir -p "$INSTALL_DIR" "$INSTALL_DIR/bin"

install_uid="${INSTALL_UID:-$(stat -c '%u' "$INSTALL_DIR")}"
install_gid="${INSTALL_GID:-$(stat -c '%g' "$INSTALL_DIR")}"

cp "$REPORTER_HOME/pyproject.toml" "$INSTALL_DIR/pyproject.toml"
cp "$REPORTER_HOME/uv.lock" "$INSTALL_DIR/uv.lock"
cp -a "$REPORTER_HOME/lib" "$INSTALL_DIR/lib"
cp -a "$REPORTER_HOME/reports" "$INSTALL_DIR/reports"
cp -a "$REPORTER_HOME/administration" "$INSTALL_DIR/administration"
cp -a /installer/bin/. "$INSTALL_DIR/bin/"
chmod +x "$INSTALL_DIR/bin/backup"

{
  echo "install=$install_type"
  echo "install_dir=/opt/reporter"
} > "$INSTALL_DIR/.info"

if [ "$install_type" = "standalone" ]; then
  instructions_file="/installer/instructions-standalone.txt"
  env_example_source="$REPORTER_HOME/.env-example"
  # Standalone mode ships local DB compose assets with SSL bootstrap files.
  ssl_dir="$INSTALL_DIR/.pg-ssl"
  db_volumes_dir="$INSTALL_DIR/.volumes"
  data_db_volume_dir="$db_volumes_dir/data-db"
  admin_db_volume_dir="$db_volumes_dir/admin-db"
  mkdir -p "$ssl_dir"
  mkdir -p "$data_db_volume_dir" "$admin_db_volume_dir"

  if ! command -v openssl >/dev/null 2>&1; then
    echo "FATAL: openssl is required for standalone install" >&2
    exit 1
  fi

  # Generate a self-signed certificate for local use.
  if ! openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$ssl_dir/server.key" \
    -out "$ssl_dir/server.crt" \
    -days 3650 \
    -subj "/CN=localhost" \
    >/dev/null 2>&1; then
    echo "FATAL: failed to generate SSL certificate for standalone install" >&2
    exit 1
  fi

  chmod 600 "$ssl_dir/server.key"

  # pg_hba.conf file that enforces SSL for all TCP connections.
  {
    echo "# TYPE  DATABASE  USER  ADDRESS       METHOD"
    echo "hostssl all       all   0.0.0.0/0     scram-sha-256"
    echo "hostssl all       all   ::/0          scram-sha-256"
    echo "local   all       all                 trust"
  } > "$ssl_dir/pg_hba.conf"

  cp "$REPORTER_HOME/docker-compose.yml" "$INSTALL_DIR/docker-compose.yml"
  cp "$REPORTER_HOME/pg_ssl_entry_point.sh" "$ssl_dir/pg_ssl_entry_point.sh"
  chmod 755 "$ssl_dir/pg_ssl_entry_point.sh"

  # Backup service assets (standalone only): Dockerfile, daemon source, dump target dir.
  # lib/ (including lib/env_backup.py) is already copied above.
  cp "$REPORTER_HOME/Dockerfile-backup" "$INSTALL_DIR/Dockerfile-backup"
  cp -a "$REPORTER_HOME/backup_server" "$INSTALL_DIR/backup_server"
  mkdir -p "$INSTALL_DIR/.backup"
else
  instructions_file="/installer/instructions-distributed.txt"
  env_example_source="$REPORTER_HOME/.env-example-distributed"
  # Distributed mode intentionally excludes local compose/database artifacts.
  rm -f "$INSTALL_DIR/docker-compose.yml" "$INSTALL_DIR/.pg-ssl/pg_ssl_entry_point.sh"
  rm -rf "$INSTALL_DIR/.pg-ssl"
fi

cp "$env_example_source" "$INSTALL_DIR/.env-example"

chown -R "$install_uid:$install_gid" "$INSTALL_DIR"
chmod -R u+rwX,g+rwX "$INSTALL_DIR"

cat "$instructions_file"
