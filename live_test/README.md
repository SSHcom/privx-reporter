# Sync Server Test Harness

This directory contains local test scripts for `sync_server` insert paths.

- `audit_event.sh` runs audit-event sync load tests.
- `connection.sh` runs connection sync load tests.
- `integrity.sh` runs deterministic integrity checks (including duplicate source records) for both sources.
- Test data is generated from sanitized templates in `samples/`.
- All scripts tag inserted rows with a run id and clean up those rows at the end of the run.

## Quick Start

Before running live tests, start the test database: `docker compose -f docker-compose-test.yml up -d`.

The harness uses **one** Postgres database (`reporter_test` on port `5446`) for both logical `admin` and `data` connections. Those settings are hardcoded in `live_test/_shared/db_env.py` (not read from `.env`). Shell scripts run `uv` with `--no-env-file` so project `.env` cannot override them.

If the container was created before `POSTGRES_DB: reporter_test` was set, create the database once:

```bash
./setup_test_db.sh
```

Run from `live_test/`:

```bash
./audit_event.sh 1000 50
./connection.sh 1000 50
./integrity.sh
```

Arguments for `audit_event.sh` and `connection.sh`:

- First arg: number of records to generate.
- Second arg: simulated API delay per request, in milliseconds.
 
`integrity.sh` takes no arguments. It uses hard-coded scenarios with forced pagination and intentional duplicates.

Example:

```bash
./connection.sh 3000 110
```

- `3000` = generate and sync 3000 connection records for this run.
- `110` = add 110 ms simulated API delay per page/request to mimic slower API response.

## Example Output

Connection load example (`./connection.sh 3000 110`):

```text
============================================================================
AUDIT-EVENT - LOAD TEST RUN SUMMARY
----------------------------------------------------------------------------
Begin:            2026-04-16T06:17:16.747713Z
End:              2026-04-16T06:17:17.586796Z
Duration:         0.824 s (generation excluded)
Generation time:  0.015 s
API wait time:    0.660 s
DB time:          0.094 s
API delay:        110 ms
Wall time:        0.839 s
Batch size:       600
API/DB split:     API 80.1% | DB 11.4%
Records / second: 3640.88
Total records:    3000
============================================================================
```

Integrity example (`./integrity.sh`):

```text
============================================================================
AUDIT-EVENT - INTEGRITY TEST SUMMARY
----------------------------------------------------------------------------
Source records:    56
Expected inserted: 43
Inserted rows:     43
Filtered duplicates: 13
Duplicate groups:  0
Batch size:        17
Duration:          0.019 s

Expectations (PASS):
  [PASS] Insert count matches expected unique records (43 == 43)
  [PASS] No duplicate recordId groups persisted (0 == 0)
  [PASS] Duplicate source records were filtered (43 < 56)
============================================================================


============================================================================
CONNECTION - INTEGRITY TEST SUMMARY
----------------------------------------------------------------------------
Source records:    66
Expected inserted: 47
Inserted rows:     47
Filtered duplicates: 19
Duplicate groups:  0
Batch size:        16
Duration:          0.020 s

Expectations (PASS):
  [PASS] Insert count matches expected unique records (47 == 47)
  [PASS] No duplicate recordId groups persisted (0 == 0)
  [PASS] Duplicate source records were filtered (47 < 66)
============================================================================

============================================================================
INTEGRITY TEST RUN SUMMARY
----------------------------------------------------------------------------
Begin:             2026-04-16T06:10:26.813507Z
End:               2026-04-16T06:10:26.859954Z
Wall time:         0.046 s
Result:            PASS
============================================================================
```

**Note**: Wall time is end-to-end elapsed runtime for the whole command, including generation + sync + cleanup.

## Integrity Check Behavior

`./integrity.sh` validates deduplication and non-skipping behavior for both audit events and connections.

Per source, it:

- Generates a deterministic set of unique source records.
- Injects duplicate copies of some records across pages.
- Runs the real sync implementation with offset pagination.
- Verifies PASS expectations:
  - inserted rows match expected unique record count
  - duplicate `record_id` groups in DB are `0`
  - inserted rows are fewer than source rows (duplicates were filtered)

The script prints boxed summary sections per source, followed by an overall run summary with begin/end time and PASS/FAIL result.

Scripts source `live_test/env.sh` for sync tuning only. Database connection settings come from `live_test/_shared/db_env.py` and match in `../docker-compose-test.yml`.

## How Input Data Works

Templates:

- `samples/audit_event.json`
- `samples/connection.json`

Each run clones the template record and generates records page-by-page (per requested batch),
not as one huge in-memory list. Timestamps and run metadata are rewritten automatically.

### Timestamp isolation (dev DB safety)

- Generated test records are timestamped about 5 years in the past.
- This keeps test rows outside normal current-time sync windows and reduces interference with active development data.

### Safe fields to tweak for scenarios

- **Audit**: `event_name`, `event_id`, nested `message` content.
- **Connection**: nested payload sections (`user_data`, `target_host_data`, roles, tags, etc.) to test JSON payload size/shape.

### Required fields (do not remove)

- **Audit**: `created`, `event_id`.
- **Connection**: `id`, `connected`, `created`, `updated`.

If these are missing, sync logic may skip or fail records.

## Environment Variables for Test Scenarios

Sync-related defaults are in `live_test/env.sh`. Database host/port/name are fixed in `live_test/_shared/db_env.py` (aligned with `docker-compose-test.yml`). Useful sync knobs:

- `SYNC_BATCH_SIZE`: records fetched per simulated API page.
- `SYNC_MAX_RANGE_HOURS`: sync range clamp (mainly affects sync window behavior/logging).
- `SYNC_CONNECTION`: `<interval>,<range_minutes>,<retention_days>`.
- `SYNC_AUDIT`: `<interval>,<range_minutes>,<retention_days>`.

Example scenario tuning in `live_test/env.sh`:

- Throughput focus: larger `SYNC_BATCH_SIZE` (for example `500`).
- Pagination pressure: smaller `SYNC_BATCH_SIZE` (for example `25`).
- Keep default source configs unless you specifically want to test range behavior.

## Latency Recommendation

Use `api-delay-ms` to model API responsiveness.

Practical presets:

- `20-80 ms`: healthy internal API latency (typical baseline).
- `100-300 ms`: moderate/slower backend conditions.
- `500-1500 ms`: degraded API or high-load incident simulation.

Suggested starting point for routine testing: **`50 ms`**.

## Notes

- The runner prints a run summary block with begin/end time, duration, RPS, total records,
  API wait time, and measured DB time.
- Summary duration and RPS are adjusted to exclude record-generation overhead, and wall time is also shown.
- Cleanup for every script is scoped to run-tagged rows, so non-test DB data is preserved.
