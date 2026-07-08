from administration.migration._shared.runner import ADMIN_DB


def up() -> dict[str, list[str]]:
    admin_statements = [
        """
        CREATE TABLE IF NOT EXISTS app_config (
            setting_key VARCHAR NOT NULL,
            value TEXT NOT NULL DEFAULT '',
            updated TIMESTAMP NOT NULL DEFAULT NOW()
        )
        """,
        "CREATE UNIQUE INDEX IF NOT EXISTS idx_app_config_key_unique ON app_config (setting_key)",
    ]
    return {ADMIN_DB: admin_statements}


def down() -> dict[str, list[str]]:
    return {ADMIN_DB: ["DROP TABLE IF EXISTS app_config"]}
