"""Bootstrap Logging and UI-owned database metadata before serving Streamlit."""

from __future__ import annotations

import logging
import sys

from lib.database import init_databases
from streamlit.logger import get_logger
from ui.db.init.admin_sync import sync_admin_user
from ui.db.init.report_sync import sync_admin_group, sync_default_oidc_group, sync_reports_from_config

logger = get_logger(__name__)


def configure_logging(*, force: bool = False) -> None:
    """Configure process-wide logging for UI bootstrap and app runtime."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
        force=force,
    )


def configure_database() -> None:
    """Configure the database: Auto-create admin tables and sync report metadata."""
    init_databases()
    sync_result = sync_reports_from_config()

    logger.info(
        "Synced report metadata from config (total=%d, inserted=%d, removed=%d, removed_mappings=%d).",
        sync_result["total_reports"],
        sync_result["inserted_reports"],
        sync_result["removed_reports"],
        sync_result["removed_user_group_mappings"],
    )

    admin_result = sync_admin_group()

    logger.info(
        "Synced admin group (inserted_group=%d, inserted_mappings=%d, total_reports=%d).",
        admin_result["inserted_group"],
        admin_result["inserted_mappings"],
        admin_result["total_reports"],
    )

    default_oidc_group_result = sync_default_oidc_group()

    logger.info(
        "Synced default OIDC group (inserted_group=%d, group_id=%d).",
        default_oidc_group_result["inserted_group"],
        default_oidc_group_result["group_id"],
    )

    admin_user_result = sync_admin_user()

    logger.info(
        "Synced admin user (inserted_admin_user=%d).",
        admin_user_result["inserted_admin_user"],
    )


def main() -> None:
    """Create required admin tables and sync report metadata."""
    configure_logging()
    configure_database()


if __name__ == "__main__":
    main()
