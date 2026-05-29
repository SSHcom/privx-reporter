from administration.migration._shared.runner import DATA_DB


def up() -> dict[str, list[str]]:
    data_statements = [
        """
        CREATE TABLE IF NOT EXISTS system_trend (
            timestamp TIMESTAMP PRIMARY KEY,
            data JSONB NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_system_trend_data ON system_trend USING GIN (data)",
        (
            "SELECT create_hypertable('system_trend', 'timestamp', if_not_exists => TRUE, "
            "chunk_time_interval => INTERVAL '1 day', migrate_data => TRUE);"
        ),
        "SELECT remove_retention_policy('system_trend', if_exists => TRUE)",
        "SELECT add_retention_policy('system_trend', INTERVAL '91 days')",
        """
        INSERT INTO system_trend ("timestamp", data)
        SELECT
          date_trunc('day', now()) - (g * interval '1 day') AS "timestamp",
          jsonb_build_object(
            'roles', 0,
            'local_users', 0,
            'hosts', 0,
            'network_targets', 0,
            'api_targets', 0,
            'access_groups', 0,
            'workflows', 0,
            'secrets', 0,
            'sources', 0,
            'api_clients', 0,
            'hosts_ssh', 0,
            'hosts_rdp', 0,
            'hosts_vnc', 0,
            'hosts_web', 0,
            'hosts_db', 0
          ) AS data
        FROM generate_series(0, 89) AS g
        ON CONFLICT ("timestamp") DO NOTHING
        """,
    ]
    return {DATA_DB: data_statements}


def down() -> dict[str, list[str]]:
    return {DATA_DB: ["DROP TABLE IF EXISTS system_trend"]}
