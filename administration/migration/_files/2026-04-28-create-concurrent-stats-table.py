from administration.migration._shared.runner import DATA_DB


def up() -> dict[str, list[str]]:
    data_statements = [
        """
        CREATE TABLE IF NOT EXISTS concurrent_stats (
            timestamp TIMESTAMP PRIMARY KEY,
            data JSONB NOT NULL
        )
        """,
        "CREATE INDEX IF NOT EXISTS idx_concurrent_stats_data ON concurrent_stats USING GIN (data)",
        (
            "SELECT create_hypertable('concurrent_stats', 'timestamp', if_not_exists => TRUE, "
            "chunk_time_interval => INTERVAL '1 hour', migrate_data => TRUE);"
        ),
        "SELECT remove_retention_policy('concurrent_stats', if_exists => TRUE)",
        "SELECT add_retention_policy('concurrent_stats', INTERVAL '30 days')",
    ]
    return {DATA_DB: data_statements}


def down() -> dict[str, list[str]]:
    return {DATA_DB: ["DROP TABLE IF EXISTS concurrent_stats"]}
