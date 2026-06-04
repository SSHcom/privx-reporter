#!/bin/bash

# Sync tuning for live tests (see ../.env.example). DB connection settings are
# hardcoded in live_test/_shared/db_env.py, not loaded from .env.

export SYNC_SOURCES="${SYNC_SOURCES:-audit,connection}"
export SYNC_AUDIT="${SYNC_AUDIT:-5,7,15}"
export SYNC_CONNECTION="${SYNC_CONNECTION:-5,7,15}"
export SYNC_BATCH_SIZE="${SYNC_BATCH_SIZE:-500}"
