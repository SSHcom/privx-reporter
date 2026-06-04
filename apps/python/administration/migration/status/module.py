from administration.migration._shared import get_migration_status


def handle_status_migration(*_args: object, **_kwargs: object) -> dict[str, str | None]:
    """Show applied and pending migration status."""
    status = get_migration_status()

    print("Applied migrations:")
    if status.applied:
        for migration in status.applied:
            print(f"- {migration.migration_name} ({migration.target_db}) at {migration.applied_at.isoformat()}")
    else:
        print("- none")

    print("\nPending migrations:")
    if status.pending:
        for migration in status.pending:
            print(f"- {migration.name} ({migration.target_db})")
    else:
        print("- none")

    return {
        "error_message": None,
        "info_message": f"Applied: {len(status.applied)}. Pending: {len(status.pending)}.",
    }
