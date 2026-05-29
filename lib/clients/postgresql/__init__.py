"""Tests are not necessary for this module."""

import logging
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine

from lib.env import EnvConfig

logger = logging.getLogger(__name__)

_engines: dict[str, Engine] = {}
_connections: dict[str, Connection] = {}
_ENGINE_LABELS = {
    "data": "PostgreSQL w/TimescaleDB",
    "admin": "PostgreSQL",
}


@dataclass
class Database:
    connection: Connection
    engine: Engine


def use_database(name: str) -> Database:
    """Get or create a cached database connection by logical name."""
    if name not in ("data", "admin"):
        raise ValueError(f"Unsupported database name: {name}. Expected 'data' or 'admin'.")

    engine = _engines.get(name)
    connection = _connections.get(name)

    if engine is None or connection is None:
        config_by_name = EnvConfig.get_db_config()
        config = config_by_name[name]
        ssl_mode = "require" if config["ssl"] else "disable"
        ssl_args = f"?sslmode={ssl_mode}"
        logger.info(f"Client SSL mode: {ssl_mode}")

        db_url = (
            f"postgresql://{config['user']}:{config['password']}"
            f"@{config['host']}:{config['port']}/{config['name']}{ssl_args}"
        )

        masked_url = db_url.replace(f":{config['password']}", ":****")
        engine_label = _ENGINE_LABELS[name]
        logger.info(f"Creating {engine_label} engine '{name}' with URL: {masked_url}")
        engine = create_engine(db_url)
        connection = engine.connect()

        ssl_row = connection.execute(text("SELECT ssl FROM pg_stat_ssl WHERE pid = pg_backend_pid()")).fetchone()

        # The probe query can trigger SQLAlchemy auto-begin on this cached
        # connection; commit it so later explicit begin() calls can succeed.
        if connection.in_transaction():
            connection.commit()

        ssl_active = ssl_row is not None and ssl_row[0]
        logger.info(f"{engine_label} '{name}' connection established (SSL: {'on' if ssl_active else 'off'})")

        _engines[name] = engine
        _connections[name] = connection
    elif connection.in_transaction():
        # Cached shared connections may retain an auto-begun transaction from a
        # prior read. Reset it before handing the connection to callers that
        # use explicit begin() blocks.
        logger.debug("Resetting stale open transaction on cached '%s' connection", name)
        connection.rollback()

    return Database(connection=connection, engine=engine)


def db_execute(queries: list[str], name: str) -> None:
    db = use_database(name=name)

    with db.connection.begin():
        for query in queries:
            db.connection.execute(text(query))
