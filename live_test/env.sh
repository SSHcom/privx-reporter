#!/bin/bash

# Keep DB valuesin sync with docker-compose-test.yml

export DB_DATA_HOST="${DB_DATA_HOST:-localhost}"
export DB_DATA_PORT="${DB_DATA_PORT:-5446}"
export DB_DATA_USER="${DB_DATA_USER:-postgres}"
export DB_DATA_PASSWORD="${DB_DATA_PASSWORD:-postgres}"
export DB_DATA_NAME="${DB_DATA_NAME:-reporter_test}"
export DB_DATA_SSL_MODE="${DB_DATA_SSL_MODE:-off}"

export DB_ADMIN_HOST="${DB_ADMIN_HOST:-localhost}"
export DB_ADMIN_PORT="${DB_ADMIN_PORT:-5446}"
export DB_ADMIN_USER="${DB_ADMIN_USER:-postgres}"
export DB_ADMIN_PASSWORD="${DB_ADMIN_PASSWORD:-postgres}"
export DB_ADMIN_NAME="${DB_ADMIN_NAME:-reporter_test}"
export DB_ADMIN_SSL_MODE="${DB_ADMIN_SSL_MODE:-off}"

# You can override all sync related variables here (see ../.env.example).
export SYNC_SOURCES="${SYNC_SOURCES:-audit,connection}"
export SYNC_AUDIT="${SYNC_AUDIT:-5,7,15}"
export SYNC_CONNECTION="${SYNC_CONNECTION:-5,7,15}"
export SYNC_BATCH_SIZE="${SYNC_BATCH_SIZE:-500}"