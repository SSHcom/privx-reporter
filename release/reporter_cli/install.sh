#!/bin/sh
set -eu

# ------------------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------------------

fatal() { echo "FATAL: $1" >&2; exit 1; }

# ------------------------------------------------------------------------------
# File generation functions
# ------------------------------------------------------------------------------

write_info_file() {
  {
    echo "install=$install_type"
    echo "install_dir=/opt/reporter"
    echo "version=$version"
  } > "$INSTALL_DIR/.info"
}

write_pg_hba_conf() {
  {
    echo "# TYPE  DATABASE  USER  ADDRESS       METHOD"
    echo "hostssl all       all   0.0.0.0/0     scram-sha-256"
    echo "hostssl all       all   ::/0          scram-sha-256"
    echo "local   all       all                 trust"
  } > "$ssl_dir/pg_hba.conf"
}

# ------------------------------------------------------------------------------
# Copy functions
# ------------------------------------------------------------------------------

replace_dir_contents() {
  src_dir="$1"
  dst_dir="$2"
  rm -rf "$dst_dir"
  mkdir -p "$dst_dir"
  cp -a "$src_dir/." "$dst_dir/"
}

copy_core_files() {
  cp    "$REPORTER_HOME/pyproject.toml"  "$INSTALL_DIR/pyproject.toml"
  cp    "$REPORTER_HOME/uv.lock"         "$INSTALL_DIR/uv.lock"
  cp    "$REPORTER_HOME/security.sh"     "$INSTALL_DIR/security.sh"
  replace_dir_contents "$REPORTER_HOME/lib"            "$INSTALL_DIR/lib"
  replace_dir_contents "$REPORTER_HOME/reports"        "$INSTALL_DIR/reports"
  replace_dir_contents "$REPORTER_HOME/administration" "$INSTALL_DIR/administration"
  replace_dir_contents "$REPORTER_HOME/create_env"     "$INSTALL_DIR/create_env"
  replace_dir_contents "/installer/bin"                "$INSTALL_DIR/bin"

  chmod 755 "$INSTALL_DIR/security.sh"
}

copy_standalone_files() {
  cp    "$REPORTER_HOME/docker-compose.yml"      "$INSTALL_DIR/docker-compose.yml"
  cp    "$REPORTER_HOME/docker-compose-env.yml"  "$INSTALL_DIR/docker-compose-env.yml"
  cp    "$REPORTER_HOME/pg_ssl_entry_point.sh"   "$ssl_dir/pg_ssl_entry_point.sh"
  cp    "$REPORTER_HOME/Dockerfile-backup"       "$INSTALL_DIR/Dockerfile-backup"
  cp    "$instructions_file"                     "$INSTALL_DIR/post_install.txt"
  replace_dir_contents "$REPORTER_HOME/backup_server" "$INSTALL_DIR/backup_server"

  chmod 755 "$ssl_dir/pg_ssl_entry_point.sh"
  chmod +x "$INSTALL_DIR/bin/backup"
}

# ------------------------------------------------------------------------------
# Argument parsing
# ------------------------------------------------------------------------------

install_type="${INSTALL_TYPE:-standalone}"

for arg in "$@"; do
  case "$arg" in
    --install-type=*) install_type="${arg#--install-type=}" ;;
    *) fatal "unknown argument: $arg\nUsage: [--install-type=standalone|distributed]" ;;
  esac
done

case "$install_type" in
  standalone|distributed) ;;
  *) fatal "invalid INSTALL_TYPE: $install_type (valid: standalone, distributed)" ;;
esac

# ------------------------------------------------------------------------------
# Common setup
# ------------------------------------------------------------------------------

mkdir -p "$INSTALL_DIR" "$INSTALL_DIR/bin"

install_uid="${INSTALL_UID:-$(stat -c '%u' "$INSTALL_DIR")}"
install_gid="${INSTALL_GID:-$(stat -c '%g' "$INSTALL_DIR")}"

copy_core_files

# Installed layout is flat (lib/, reports/, …); rewrite hatch force-include paths.
sed -i 's|"apps/python/|"|g' "$INSTALL_DIR/pyproject.toml"

# sync_server runs in a docker container, not installed locally.
sed -i '/sync_server/d' "$INSTALL_DIR/pyproject.toml"

# Create .info file with install type and version.
version="$(awk -F'"' '/^version = / { print $2; exit }' "$REPORTER_HOME/pyproject.toml")"
[ -z "$version" ] && fatal "could not read version from $REPORTER_HOME/pyproject.toml"

write_info_file

# ------------------------------------------------------------------------------
# Mode-specific setup
# ------------------------------------------------------------------------------

if [ "$install_type" = "standalone" ]; then
  instructions_file="/installer/instructions-standalone.txt"
  env_example_source="$REPORTER_HOME/.env-example"

  # Standalone ships local DB compose assets with SSL bootstrap files.
  ssl_dir="$INSTALL_DIR/.pg-ssl"
  db_volumes_dir="$INSTALL_DIR/.volumes"
  mkdir -p "$ssl_dir" "$db_volumes_dir/data-db" "$db_volumes_dir/admin-db"

  command -v openssl >/dev/null 2>&1 || fatal "openssl is required for standalone install"

  openssl req -x509 -newkey rsa:2048 -nodes \
    -keyout "$ssl_dir/server.key" -out "$ssl_dir/server.crt" \
    -days 3650 -subj "/CN=localhost" >/dev/null 2>&1 \
    || fatal "failed to generate SSL certificate for standalone install"
  chmod 600 "$ssl_dir/server.key"

  write_pg_hba_conf
  copy_standalone_files

else
  # Distributed: CLI-only, no backup daemon or local database.
  instructions_file="/installer/instructions-distributed.txt"
  env_example_source="$REPORTER_HOME/.env-example-distributed"

  cp "$instructions_file"  "$INSTALL_DIR/post_install.txt"
  sed -i '/backup_server/d' "$INSTALL_DIR/pyproject.toml"
  rm -f "$INSTALL_DIR/bin/backup"
fi

# ------------------------------------------------------------------------------
# Finalize
# ------------------------------------------------------------------------------

cp "$env_example_source" "$INSTALL_DIR/.env-example"

chown -R "$install_uid:$install_gid" "$INSTALL_DIR"
chmod -R u+rwX,g+rwX "$INSTALL_DIR"

cat "$instructions_file"

echo "These instructions are also available in /opt/reporter/post_install.txt"
echo
