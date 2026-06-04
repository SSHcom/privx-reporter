from lib.clients.postgresql import Database, use_database


def use_admin_database() -> Database:
    """Return the shared admin database connection for event commands."""
    return use_database(name="admin")
