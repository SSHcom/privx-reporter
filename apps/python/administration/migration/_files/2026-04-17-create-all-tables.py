from administration.migration._shared.runner import ADMIN_DB, DATA_DB
from lib.env_sync import SYNC_AUDIT, SYNC_CONNECTION, parse_retention_days


def up() -> dict[str, list[str]]:
    audit_retention_days = parse_retention_days(SYNC_AUDIT)
    connection_retention_days = parse_retention_days(SYNC_CONNECTION)

    admin_statements = [
        # user_group
        """
        CREATE TABLE IF NOT EXISTS user_group (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL,
            access_groups VARCHAR
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_user_group_name_unique ON user_group (name)",
        # report
        """
        CREATE TABLE IF NOT EXISTS report (
            id SERIAL PRIMARY KEY,
            group_name VARCHAR NOT NULL,
            report_name VARCHAR NOT NULL
        )
        """,
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_report_group_name_report_name_unique "
            "ON report (group_name, report_name)"
        ),
        # alt_group_view
        """
        CREATE TABLE IF NOT EXISTS alt_group_view (
            id SERIAL PRIMARY KEY,
            name VARCHAR NOT NULL
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_alt_group_view_name_unique ON alt_group_view (name)",
        # alt_group
        """
        CREATE TABLE IF NOT EXISTS alt_group (
            id SERIAL PRIMARY KEY,
            alt_group_view_id INTEGER NOT NULL REFERENCES alt_group_view (id),
            group_name VARCHAR NOT NULL,
            report_id INTEGER NOT NULL REFERENCES report (id),
            sort_order INTEGER NOT NULL DEFAULT 0
        )
        """,
        # audit_event_sync
        """
        CREATE TABLE IF NOT EXISTS audit_event_sync (
            id SERIAL PRIMARY KEY,
            code INTEGER NOT NULL,
            enabled BOOLEAN NOT NULL,
            name VARCHAR NOT NULL,
            severity VARCHAR NOT NULL,
            description VARCHAR NOT NULL
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_audit_event_sync_code_unique ON audit_event_sync (code)",
        # user
        """
        CREATE TABLE IF NOT EXISTS "user" (
            id SERIAL PRIMARY KEY,
            is_admin BOOLEAN NOT NULL,
            has_profile BOOLEAN NOT NULL,
            name VARCHAR NOT NULL,
            display_name VARCHAR NOT NULL,
            user_group_id INTEGER NOT NULL REFERENCES user_group (id),
            encrypted_password VARCHAR NOT NULL
        )
        """,
        'CREATE UNIQUE INDEX IF NOT EXISTS idx_user_name_unique ON "user" (name)',
        # user_group_report
        """
        CREATE TABLE IF NOT EXISTS user_group_report (
            id SERIAL PRIMARY KEY,
            user_group_id INTEGER NOT NULL REFERENCES user_group (id),
            report_id INTEGER NOT NULL REFERENCES report (id)
        )
        """,
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "idx_user_group_report_user_group_id_report_id_unique "
            "ON user_group_report (user_group_id, report_id)"
        ),
        # session
        """
        CREATE TABLE IF NOT EXISTS session (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES "user" (id),
            token_jti VARCHAR NOT NULL,
            oidc_access_token TEXT,
            oidc_refresh_token TEXT,
            oidc_id_token TEXT,
            oidc_access_expires_at TIMESTAMP,
            oidc_refresh_expires_at TIMESTAMP,
            created TIMESTAMP NOT NULL DEFAULT NOW(),
            updated TIMESTAMP NOT NULL DEFAULT NOW(),
            auth_source VARCHAR NOT NULL DEFAULT 'local',
            ip_address VARCHAR,
            user_agent VARCHAR
        )
        """,
        "ALTER TABLE session ADD COLUMN IF NOT EXISTS oidc_access_token TEXT",
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_session_token_jti_unique ON session (token_jti)",
        "CREATE INDEX IF NOT EXISTS idx_session_user_id ON session (user_id)",
        # alt_group
        """
        CREATE TABLE IF NOT EXISTS alt_group (
            id SERIAL PRIMARY KEY,
            alt_group_view_id INTEGER NOT NULL REFERENCES alt_group_view (id),
            group_name VARCHAR NOT NULL,
            report_id INTEGER NOT NULL REFERENCES report (id),
            sort_order INTEGER NOT NULL DEFAULT 0
        )
        """,
        (
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "idx_alt_group_view_id_group_name_report_id_unique "
            "ON alt_group (alt_group_view_id, group_name, report_id)"
        ),
        "CREATE INDEX IF NOT EXISTS idx_alt_group_view_id_sort_order ON alt_group (alt_group_view_id, sort_order)",
    ]

    data_statements = [
        # audit_event
        """
        CREATE TABLE IF NOT EXISTS audit_event (
            timestamp TIMESTAMP NOT NULL,
            record_id VARCHAR NOT NULL,
            event_id VARCHAR,
            event_name VARCHAR,
            data JSONB NOT NULL,
            PRIMARY KEY (timestamp, record_id)
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_audit_event_event_id_event_name ON audit_event (event_id, event_name)",
        "CREATE INDEX IF NOT EXISTS idx_audit_event_data ON audit_event USING GIN (data)",
        (
            "SELECT create_hypertable('audit_event', 'timestamp', if_not_exists => TRUE, "
            "chunk_time_interval => INTERVAL '1 day', migrate_data => TRUE);"
        ),
        (
            f"SELECT add_retention_policy('audit_event', INTERVAL '{audit_retention_days} days') "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM timescaledb_information.jobs "
            "  WHERE hypertable_name = 'audit_event' AND proc_name = 'policy_retention');"
        ),
        # connection
        """
        CREATE TABLE IF NOT EXISTS connection (
            timestamp TIMESTAMP NOT NULL,
            record_id VARCHAR NOT NULL,
            data JSONB NOT NULL,
            PRIMARY KEY (timestamp, record_id)
        )
        """,
        (
            "SELECT create_hypertable('connection', 'timestamp', if_not_exists => TRUE, "
            "chunk_time_interval => INTERVAL '1 day', migrate_data => TRUE);"
        ),
        (
            f"SELECT add_retention_policy('connection', INTERVAL '{connection_retention_days} days') "
            "WHERE NOT EXISTS ("
            "  SELECT 1 FROM timescaledb_information.jobs "
            "  WHERE hypertable_name = 'connection' AND proc_name = 'policy_retention');"
        ),
        "CREATE INDEX IF NOT EXISTS idx_connection_data ON connection USING GIN (data)",
    ]

    return {
        ADMIN_DB: admin_statements,
        DATA_DB: data_statements,
    }


def down() -> dict[str, list[str]]:
    admin_statements = [
        "DROP TABLE IF EXISTS alt_group",
        "DROP TABLE IF EXISTS session",
        "DROP TABLE IF EXISTS user_group_report",
        'DROP TABLE IF EXISTS "user"',
        "DROP TABLE IF EXISTS audit_event_sync",
        "DROP TABLE IF EXISTS alt_group_view",
        "DROP TABLE IF EXISTS report",
        "DROP TABLE IF EXISTS user_group",
    ]

    data_statements = [
        "DROP TABLE IF EXISTS connection",
        "DROP TABLE IF EXISTS audit_event",
    ]

    return {
        ADMIN_DB: admin_statements,
        DATA_DB: data_statements,
    }
