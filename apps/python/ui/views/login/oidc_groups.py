"""OIDC claim-to-local-group resolution helpers.

This module only maps to existing local groups; it never creates new group rows.
"""

from __future__ import annotations

from sqlalchemy import func, select
from streamlit.logger import get_logger

from lib import env_oidc
from lib.clients.postgresql import use_database
from lib.database.models.admin.user_group import UserGroupTable


log = get_logger(__name__)


def claim_values(claims: dict, claim_path: str) -> list[str]:
    """Extract normalized string values from dotted claim path."""
    current: object = claims
    for part in [p for p in claim_path.split(".") if p.strip()]:
        if not isinstance(current, dict):
            return []
        current = current.get(part)

    if current is None:
        return []
    if isinstance(current, list):
        return [str(item).strip() for item in current if str(item).strip()]
    if isinstance(current, str):
        value = current.strip()
        return [value] if value else []
    if isinstance(current, (int, float, bool)):
        return [str(current)]
    return []


def resolve_group_by_ref(group_ref: str) -> tuple[int, str] | None:
    """Resolve local group by id or case-insensitive name."""
    db = use_database("admin")
    with db.engine.connect() as connection:
        if group_ref.isdigit():
            row = connection.execute(
                select(UserGroupTable.c.id, UserGroupTable.c.name).where(UserGroupTable.c.id == int(group_ref))
            ).fetchone()
        else:
            row = connection.execute(
                select(UserGroupTable.c.id, UserGroupTable.c.name).where(
                    func.lower(UserGroupTable.c.name) == group_ref.lower()
                )
            ).fetchone()
    if row is None:
        return None
    return int(row[0]), str(row[1]).strip()


def resolve_mapped_user_group(provider_name: str, claims: dict) -> tuple[int, str] | None:
    """Find first mapped local group for claim values from current login."""
    claim_name = env_oidc.group_claim_name()
    mapping = env_oidc.group_mapping()
    values = claim_values(claims, claim_name)
    log.info(
        "OIDC claim path evaluation provider=%s claim_path=%s resolved_values=%s",
        provider_name,
        claim_name,
        values,
    )
    log.info(
        "OIDC group mapping probe provider=%s claim=%s claim_values=%s mapping_keys=%s",
        provider_name,
        claim_name,
        values,
        sorted(mapping.keys()),
    )
    if not mapping:
        log.info("OIDC group mapping disabled: OIDC_GROUP_MAPPING not set")
        return None
    if not values:
        log.info("OIDC group mapping: no claim values found for claim=%s", claim_name)
        return None
    mapping_ci = {k.lower(): v for k, v in mapping.items()}
    for source_group in values:
        target_ref = mapping.get(source_group) or mapping_ci.get(source_group.lower())
        if not target_ref:
            continue
        resolved = resolve_group_by_ref(str(target_ref))
        if resolved is None:
            log.warning(
                "OIDC group mapping matched source=%s but target group ref=%s was not found",
                source_group,
                target_ref,
            )
            continue
        log.info(
            "OIDC group mapping resolved source=%s -> target=%s(%s)",
            source_group,
            resolved[1],
            resolved[0],
        )
        return resolved
    log.info("OIDC group mapping: no matching source group found in claim values")
    return None


def resolve_default_user_group() -> tuple[int, str]:
    """Resolve fallback group for auto-provisioned users."""
    role_ref = env_oidc.auto_provision_default_role()
    role_ref_lower = role_ref.lower()
    candidate_names: list[str] = [role_ref]
    if role_ref_lower in {"reporter_viewer", "viewer", "users"}:
        candidate_names = [role_ref, "viewer", "users", "reporter_viewer"]

    db = use_database("admin")
    with db.engine.connect() as connection:
        if role_ref.isdigit():
            row = connection.execute(
                select(UserGroupTable.c.id, UserGroupTable.c.name).where(UserGroupTable.c.id == int(role_ref))
            ).fetchone()
        else:
            row = None
            for candidate_name in candidate_names:
                row = connection.execute(
                    select(UserGroupTable.c.id, UserGroupTable.c.name).where(
                        func.lower(UserGroupTable.c.name) == candidate_name.lower()
                    )
                ).fetchone()
                if row is not None:
                    break
            if row is None:
                non_privileged_groups = connection.execute(
                    select(UserGroupTable.c.id, UserGroupTable.c.name).where(
                        func.lower(UserGroupTable.c.name).notin_(("admin", "superadmin"))
                    )
                ).fetchall()
                if len(non_privileged_groups) == 1:
                    row = non_privileged_groups[0]
                    log.warning(
                        "Auto-provision default role %s not found; using only available non-privileged group %s(%s).",
                        role_ref,
                        row[1],
                        row[0],
                    )
    if row is None:
        raise ValueError(
            "Auto-provision default role not found: "
            f"{role_ref}. Set OIDC_AUTO_PROVISION_DEFAULT_ROLE to an existing user_group name/id "
            "or create a non-privileged user group."
        )
    group_id = int(row[0])
    group_name = str(row[1]).strip()
    if group_name.lower() in {"admin", "superadmin"}:
        raise ValueError("Auto-provision default role must not be privileged")
    return group_id, group_name


def resolve_display_name(claims: dict, username: str) -> str:
    """Pick best-effort display name from claims with username fallback."""
    display_name = (
        str(claims.get("name", "")).strip()
        or f"{str(claims.get('given_name', '')).strip()} {str(claims.get('family_name', '')).strip()}".strip()
        or username
    )
    return display_name[:255]
