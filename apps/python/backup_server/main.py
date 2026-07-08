"""Scheduled backup service.

Reads BACKUP_CONFIG, then dumps the configured database(s) to BACKUP_DIR on the
configured interval. Tests are not necessary for this module; the testable logic
lives in lib/env_backup.py and backup_server/dump.py.
"""

import logging
import os
import time

from backup_server.dump import run_dump_cycle
from lib.env_backup import BACKUP_DIR, default_backup_dir, parse_backup_config
from lib.service.env_source import reloadEnv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

CONFIG_CHECK_INTERVAL_SECONDS = 300


def main() -> None:
    config = parse_backup_config()
    backup_dir = os.getenv(BACKUP_DIR) or default_backup_dir()

    if not config.enabled:
        logger.info("Backups disabled via BACKUP_CONFIG; idling.")
        while True:
            time.sleep(CONFIG_CHECK_INTERVAL_SECONDS)
            reloadEnv()
            config = parse_backup_config()
            if config.enabled:
                break

    interval_seconds = config.interval_minutes * 60
    logger.info(
        "Backup service started: target=%s interval=%dm snapshots=%d backup_dir=%s",
        config.target,
        config.interval_minutes,
        config.snapshots,
        backup_dir,
    )

    while True:
        try:
            run_dump_cycle(config, backup_dir)
            logger.info("Backup cycle complete")
        except Exception as error:  # noqa: BLE001 - daemon must survive transient failures
            logger.error("Backup cycle failed: %s", error, exc_info=True)
        time.sleep(interval_seconds)


if __name__ == "__main__":
    main()
