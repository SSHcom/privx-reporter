#!/bin/sh

set -eu

CERT_SRC_DIR="/certs-src"
CERT_DST_DIR="/var/lib/postgresql/certs"

if [ "${*#*ssl=on*}" != "$*" ]; then
  for cert_file in pg_hba.conf server.crt server.key; do
    if [ ! -f "${CERT_SRC_DIR}/${cert_file}" ]; then
      echo "Missing SSL file: ${CERT_SRC_DIR}/${cert_file}" >&2
      exit 1
    fi
  done

  mkdir -p "${CERT_DST_DIR}"

  cp "${CERT_SRC_DIR}/pg_hba.conf" "${CERT_DST_DIR}/pg_hba.conf"
  cp "${CERT_SRC_DIR}/server.crt" "${CERT_DST_DIR}/server.crt"
  cp "${CERT_SRC_DIR}/server.key" "${CERT_DST_DIR}/server.key"

  chown postgres:postgres "${CERT_DST_DIR}/server.key" "${CERT_DST_DIR}/server.crt"
  chmod 600 "${CERT_DST_DIR}/server.key"
  chmod 644 "${CERT_DST_DIR}/server.crt" "${CERT_DST_DIR}/pg_hba.conf"
fi

exec docker-entrypoint.sh "$@"
