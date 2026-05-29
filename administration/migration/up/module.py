from administration.migration._shared import apply_pending_migrations


def _format_target_tables(target_dbs: list[str]) -> str:
    db_order = {"admin": 0, "data": 1}
    ordered_target_dbs = sorted(dict.fromkeys(target_dbs), key=lambda db: (db_order.get(db, 99), db))
    labels = [f"{target_db} tables" for target_db in ordered_target_dbs]
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def handle_up_migration() -> dict[str, str | None]:
    """Apply all pending migrations."""
    applied_migrations = apply_pending_migrations()
    if not applied_migrations:
        return {"error_message": None, "info_message": "No pending migrations."}

    for migration in applied_migrations:
        print(f"Applied migration: {migration.name} ({migration.target_db})")

    grouped_targets_by_migration_name: dict[str, list[str]] = {}
    for migration in applied_migrations:
        grouped_targets_by_migration_name.setdefault(migration.name, []).append(migration.target_db)

    if len(grouped_targets_by_migration_name) == 1:
        migration_name = next(iter(grouped_targets_by_migration_name))
        target_tables = _format_target_tables(grouped_targets_by_migration_name[migration_name])
        return {
            "error_message": None,
            "info_message": f"Applied migration '{migration_name}' for {target_tables}.",
        }

    summaries = [
        f"'{migration_name}' for {_format_target_tables(target_dbs)}"
        for migration_name, target_dbs in grouped_targets_by_migration_name.items()
    ]
    return {"error_message": None, "info_message": f"Applied migrations: {'; '.join(summaries)}."}
