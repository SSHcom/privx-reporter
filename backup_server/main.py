"""Scheduled backup service.

Reads BACKUP_CONFIG, then dumps the configured database(s) to BACKUP_DIR on the
configured interval. Tests are not necessary for this module; the testable logic
lives in lib/env_backup.py and backup_server/dump.py.
"""

import logging
import os
import time

from backup_server.dump import run_dump_cycle
from lib.env_backup import parse_backup_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

BACKUP_DIR_ENV = "BACKUP_DIR"
DEFAULT_BACKUP_DIR = "/opt/reporter/.backup"

# When disabled, sleep in long chunks to stay alive without busy-looping.
DISABLED_SLEEP_SECONDS = 3600


def main() -> None:
    config = parse_backup_config()
    backup_dir = os.getenv(BACKUP_DIR_ENV, DEFAULT_BACKUP_DIR)

    if not config.enabled:
        logger.info("Backups disabled via BACKUP_CONFIG; idling.")
        while True:
            time.sleep(DISABLED_SLEEP_SECONDS)

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
