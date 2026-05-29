"""Synchronize admin report metadata tables from reports config."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import toml
from sqlalchemy import delete, insert, select
from streamlit.logger import get_logger

if TYPE_CHECKING:
    from sqlalchemy.engine import Connection

from lib.clients.postgresql import use_database
from lib.database.models.admin.alt_group import AltGroupTable
from lib.database.models.admin.report import ReportTable
from lib.database.models.admin.user_group import UserGroupTable
from lib.database.models.admin.user_group_report import UserGroupReportTable

logger = get_logger(__name__)
ADMIN_GROUP_NAME = "admin"
DEFAULT_OIDC_GROUP_NAME = "viewer"
DEFAULT_OIDC_GROUP_ACCESS_GROUPS = "Default"


def _default_config_path() -> Path:
    """Return the default reports config path."""
    return Path(__file__).resolve().parents[3] / "reports" / "config.toml"


def _extract_report_pairs(config: dict[str, Any]) -> set[tuple[str, str]]:
    """Extract (group_name, report_name) pairs from report config."""
    pairs: set[tuple[str, str]] = set()

    for group_name, group_cfg in config.items():
        if not isinstance(group_cfg, dict):
            continue
        subcommands = group_cfg.get("subcommands", {})
        if not isinstance(subcommands, dict):
            continue

        for report_name in subcommands.keys():
            pairs.add((group_name, report_name))

    return pairs


def _prune_orphaned_user_group_report_mappings() -> int:
    """Delete mappings that reference reports no longer present in report table.

    This is a safety net that cleans up orphaned mappings (dangling foreign key
    references) that shouldn't exist in normal operation.
    """
    db = use_database("admin")

    orphaned_mapping_stmt = delete(UserGroupReportTable).where(
        ~UserGroupReportTable.c.report_id.in_(select(ReportTable.c.id))
    )

    with db.connection.begin():
        result = db.connection.execute(orphaned_mapping_stmt)

    removed_mappings = int(result.rowcount or 0)
    if removed_mappings > 0:
        logger.warning("Removed %d orphaned user_group_report mapping(s).", removed_mappings)

    return removed_mappings


def _prune_orphaned_alt_group_mappings() -> int:
    """Delete alt_group rows that reference reports no longer present in report table.

    This is a safety net that cleans up orphaned alt group assignments (dangling
    foreign key references) that shouldn't exist in normal operation.
    """
    db = use_database("admin")

    orphaned_mapping_stmt = delete(AltGroupTable).where(~AltGroupTable.c.report_id.in_(select(ReportTable.c.id)))

    with db.connection.begin():
        result = db.connection.execute(orphaned_mapping_stmt)

    removed_mappings = int(result.rowcount or 0)
    if removed_mappings > 0:
        logger.warning("Removed %d orphaned alt_group mapping(s).", removed_mappings)

    return removed_mappings


def _prune_stale_user_group_report_mappings(connection: Connection, stale_report_ids: list[int]) -> int:
    """Delete mappings for reports that are being removed from the config.

    Args:
        connection: Active database connection within a transaction.
        stale_report_ids: IDs of reports that will be removed.

    Returns:
        Number of mappings removed.
    """
    if not stale_report_ids:
        return 0

    result = connection.execute(
        delete(UserGroupReportTable).where(UserGroupReportTable.c.report_id.in_(stale_report_ids))
    )
    removed = int(result.rowcount or 0)
    if removed > 0:
        logger.warning("Removed %d stale user_group_report mapping(s).", removed)

    return removed


def _prune_stale_alt_group_mappings(connection: Connection, stale_report_ids: list[int]) -> int:
    """Delete alt_group assignments for reports that are being removed from the config.

    Args:
        connection: Active database connection within a transaction.
        stale_report_ids: IDs of reports that will be removed.

    Returns:
        Number of assignments removed.
    """
    if not stale_report_ids:
        return 0

    result = connection.execute(delete(AltGroupTable).where(AltGroupTable.c.report_id.in_(stale_report_ids)))
    removed = int(result.rowcount or 0)
    if removed > 0:
        logger.warning("Removed %d stale alt_group mapping(s).", removed)

    return removed


def sync_reports_from_config(config_path: Path | str | None = None) -> dict[str, int]:
    """Sync report table rows from ``reports/config.toml``.

    This keeps ``report`` aligned to declared groups/subcommands and also removes
    stale ``user_group_report`` mappings for removed reports.
    """
    # First, clean up any orphaned mappings (references to non-existent reports)
    removed_mappings = _prune_orphaned_user_group_report_mappings()
    removed_mappings += _prune_orphaned_alt_group_mappings()

    path = Path(config_path) if config_path is not None else _default_config_path()
    with path.open(encoding="utf-8") as fh:
        config = toml.load(fh)

    desired_pairs = _extract_report_pairs(config)
    db = use_database("admin")

    removed_reports = 0
    inserted_reports = 0

    with db.connection.begin():
        existing_rows = db.connection.execute(
            select(
                ReportTable.c.id,
                ReportTable.c.group_name,
                ReportTable.c.report_name,
            )
        ).fetchall()

        existing_by_pair = {(row.group_name, row.report_name): row.id for row in existing_rows}
        existing_pairs = set(existing_by_pair.keys())

        pairs_to_insert = sorted(desired_pairs - existing_pairs)
        stale_pairs = existing_pairs - desired_pairs
        stale_report_ids = [existing_by_pair[pair] for pair in stale_pairs]

        if stale_report_ids:
            # Delete mappings for reports being removed
            removed_mappings += _prune_stale_user_group_report_mappings(db.connection, stale_report_ids)
            removed_mappings += _prune_stale_alt_group_mappings(db.connection, stale_report_ids)

            # Delete the stale reports
            report_delete_result = db.connection.execute(
                delete(ReportTable).where(ReportTable.c.id.in_(stale_report_ids))
            )
            removed_reports = int(report_delete_result.rowcount or 0)
            if removed_reports > 0:
                logger.warning("Removed %d report row(s) not found in config.", removed_reports)

        if pairs_to_insert:
            rows = [
                {"group_name": group_name, "report_name": report_name} for group_name, report_name in pairs_to_insert
            ]
            insert_result = db.connection.execute(insert(ReportTable), rows)
            inserted_reports = int(insert_result.rowcount or 0)

    return {
        "inserted_reports": inserted_reports,
        "removed_reports": removed_reports,
        "removed_user_group_mappings": removed_mappings,
        "total_reports": len(desired_pairs),
    }


def sync_admin_group() -> dict[str, int]:
    """Ensure admin group exists with access to all reports.

    Creates an 'admin' user group if it doesn't exist and grants it
    access to all reports in the report table.
    """
    db = use_database("admin")

    with db.connection.begin():
        # Get or create admin group
        admin_group = db.connection.execute(
            select(UserGroupTable.c.id).where(UserGroupTable.c.name == ADMIN_GROUP_NAME)
        ).fetchone()

        if admin_group is None:
            insert_result = db.connection.execute(
                insert(UserGroupTable),
                {"name": ADMIN_GROUP_NAME, "access_groups": None},
            )
            admin_group_id = int(insert_result.inserted_primary_key[0])
            inserted_group = 1
        else:
            admin_group_id = admin_group.id
            inserted_group = 0

        # Get all report IDs
        all_reports = db.connection.execute(select(ReportTable.c.id)).fetchall()
        all_report_ids = {row.id for row in all_reports}

        # Get existing mappings for admin group
        existing_mappings = db.connection.execute(
            select(UserGroupReportTable.c.report_id).where(UserGroupReportTable.c.user_group_id == admin_group_id)
        ).fetchall()
        existing_report_ids = {row.report_id for row in existing_mappings}

        # Insert missing mappings
        missing_report_ids = all_report_ids - existing_report_ids
        inserted_mappings = 0

        if missing_report_ids:
            rows = [
                {"user_group_id": admin_group_id, "report_id": report_id} for report_id in sorted(missing_report_ids)
            ]
            insert_result = db.connection.execute(insert(UserGroupReportTable), rows)
            inserted_mappings = int(insert_result.rowcount or 0)

    return {
        "inserted_group": inserted_group,
        "inserted_mappings": inserted_mappings,
        "total_reports": len(all_report_ids),
    }


def sync_default_oidc_group() -> dict[str, int]:
    """Ensure a non-privileged default user group exists for OIDC auto-provisioning."""
    db = use_database("admin")

    with db.connection.begin():
        default_group = db.connection.execute(
            select(UserGroupTable.c.id).where(UserGroupTable.c.name == DEFAULT_OIDC_GROUP_NAME)
        ).fetchone()

        if default_group is None:
            insert_result = db.connection.execute(
                insert(UserGroupTable),
                {"name": DEFAULT_OIDC_GROUP_NAME, "access_groups": DEFAULT_OIDC_GROUP_ACCESS_GROUPS},
            )
            default_group_id = int(insert_result.inserted_primary_key[0])
            inserted_group = 1
        else:
            default_group_id = int(default_group.id)
            inserted_group = 0

    return {"inserted_group": inserted_group, "group_id": default_group_id}
