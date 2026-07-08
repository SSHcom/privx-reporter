"""Set the UI super-admin password in the admin database."""

from __future__ import annotations

import getpass
import logging
import sys

from sqlalchemy import update

from lib.clients.postgresql import use_database
from lib.database.models.admin.user import UserTable
from ui.utils.password import hash_password, validate_password_policy

logger = logging.getLogger(__name__)

ADMIN_USERNAME = "admin"


def set_admin_password(password: str) -> tuple[bool, str]:
    """Hash and store the password for the super-admin user."""
    policy_ok, policy_error = validate_password_policy(password)
    if not policy_ok:
        return False, policy_error

    db = use_database("admin")
    password_hash = hash_password(password)

    try:
        with db.connection.begin():
            result = db.connection.execute(
                update(UserTable).where(UserTable.c.name == ADMIN_USERNAME).values(encrypted_password=password_hash)
            )
            if result.rowcount == 0:
                return False, f"User '{ADMIN_USERNAME}' does not exist. Run UI bootstrap first."
    except Exception as exc:
        logger.exception("Failed to set admin password")
        return False, f"Failed to set admin password: {exc}"

    return True, f"Password updated for user '{ADMIN_USERNAME}'."


def _prompt_password() -> str | None:
    password = getpass.getpass("New admin password: ")
    if not password:
        print("Password cannot be empty.", file=sys.stderr)
        return None

    confirm = getpass.getpass("Confirm admin password: ")
    if password != confirm:
        print("Passwords do not match.", file=sys.stderr)
        return None

    return password


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        stream=sys.stderr,
    )

    password = _prompt_password()
    if password is None:
        return 1

    ok, message = set_admin_password(password)
    if ok:
        print(message)
        return 0

    print(message, file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
