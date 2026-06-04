import argparse

from administration.migration._shared import rollback_migrations


def _format_target_tables(target_dbs: list[str]) -> str:
    db_order = {"admin": 0, "data": 1}
    ordered_target_dbs = sorted(dict.fromkeys(target_dbs), key=lambda db: (db_order.get(db, 99), db))
    labels = [f"{target_db} tables" for target_db in ordered_target_dbs]
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return f"{', '.join(labels[:-1])}, and {labels[-1]}"


def _parse_rolled_back_entry(entry: str) -> tuple[str, str | None]:
    if not entry.endswith(")"):
        return entry, None

    migration_name, separator, db_with_paren = entry.rpartition(" (")
    if not separator:
        return entry, None

    target_db = db_with_paren[:-1]
    if not migration_name or not target_db:
        return entry, None

    return migration_name, target_db


def handle_down_migration(args: argparse.Namespace) -> dict[str, str | None]:
    """Rollback latest applied migration(s)."""
    steps_raw = getattr(args, "steps", None) or "1"

    try:
        steps = int(steps_raw)
    except ValueError:
        return {"error_message": "--steps must be an integer.", "info_message": None}

    try:
        rolled_back = rollback_migrations(steps)
    except ValueError as error:
        return {"error_message": str(error), "info_message": None}

    if not rolled_back:
        return {"error_message": None, "info_message": "No applied migrations to roll back."}

    for migration_name in rolled_back:
        print(f"Rolled back migration: {migration_name}")

    grouped_targets_by_migration_name: dict[str, list[str]] = {}
    for entry in rolled_back:
        migration_name, target_db = _parse_rolled_back_entry(entry)
        grouped_targets_by_migration_name.setdefault(migration_name, [])
        if target_db and target_db not in grouped_targets_by_migration_name[migration_name]:
            grouped_targets_by_migration_name[migration_name].append(target_db)

    if len(grouped_targets_by_migration_name) == 1:
        migration_name = next(iter(grouped_targets_by_migration_name))
        target_dbs = grouped_targets_by_migration_name[migration_name]
        if target_dbs:
            target_tables = _format_target_tables(target_dbs)
            return {
                "error_message": None,
                "info_message": f"Rolled back migration '{migration_name}' for {target_tables}.",
            }
        return {
            "error_message": None,
            "info_message": f"Rolled back migration '{migration_name}'.",
        }

    summaries = []
    for migration_name, target_dbs in grouped_targets_by_migration_name.items():
        if target_dbs:
            summaries.append(f"'{migration_name}' for {_format_target_tables(target_dbs)}")
        else:
            summaries.append(f"'{migration_name}'")
    return {"error_message": None, "info_message": f"Rolled back migrations: {'; '.join(summaries)}."}
