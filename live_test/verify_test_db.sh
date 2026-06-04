#!/bin/bash

set -euo pipefail

CONTAINER_NAME="${REPORTER_TEST_DB_CONTAINER:-reporter-test-db}"
DB_NAME=reporter_test

if ! docker inspect "$CONTAINER_NAME" >/dev/null 2>&1; then
  echo "Container '$CONTAINER_NAME' is not running. Start it with:"
  echo "  docker compose -f docker-compose-test.yml up -d"
  exit 1
fi

exists="$(docker exec "$CONTAINER_NAME" psql -U postgres -tAc "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | tr -d '[:space:]')"
if [ "$exists" != "1" ]; then
  echo "Creating database '${DB_NAME}' in ${CONTAINER_NAME}..."
  docker exec "$CONTAINER_NAME" psql -U postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE \"${DB_NAME}\";"
fi

docker exec "$CONTAINER_NAME" psql -U postgres -d "$DB_NAME" -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
echo "Test database '${DB_NAME}' is ready on port 5446."
