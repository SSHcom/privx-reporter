from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import streamlit as st
from streamlit.logger import get_logger

import ui.constants as constants
from lib import report_api
from lib.env import EnvConfig
from ui.services.cache_service import get_cached_privx_client
from ui.services.page_bootstrap import setup_page
from ui.services.permissions import is_privx_user
from ui.services.session import keys
from ui.services.user_service import get_privx_user_matches

logger = get_logger(__name__)


def _normalize(value: object) -> str:
    return str(value or "").strip().casefold()


def _is_active_connection(connection: dict[str, Any]) -> bool:
    disconnected_raw = connection.get("disconnected")
    if disconnected_raw is None:
        return True
    if isinstance(disconnected_raw, str):
        return disconnected_raw.strip() == ""
    return False


def _fetch_host_connections(api: object, host_id: str) -> list[dict[str, Any]]:
    batch_size = EnvConfig.get_api_batchsize()
    offset = 0
    rows: list[dict[str, Any]] = []
    now_utc = datetime.now(UTC)
    connected_start = (now_utc - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    connected_end = now_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    search_payload = {
        "status": ["CONNECTED"],
        "connected": {"start": connected_start, "end": connected_end},
    }

    while True:
        response = report_api.search_connections(
            api,
            offset=offset,
            limit=batch_size,
            search_payload=search_payload,
        )
        items = list(response.get("items", []))
        if not items:
            break

        for connection in items:
            connection_host_id = str((connection.get("target_host") or {}).get("id", "")).strip()
            if connection_host_id == host_id:
                rows.append(connection)

        total_count = int(response.get("count", 0) or 0)
        if offset + len(items) >= total_count:
            break
        offset += batch_size

    return rows


def _role_has_member(api: object, role_id: str, user_id: str, cache: dict[tuple[str, str], bool]) -> bool:
    cache_key = (role_id, user_id)
    if cache_key in cache:
        return cache[cache_key]

    has_member = False
    batch_size = EnvConfig.get_api_batchsize()
    offset = 0

    while True:
        members_response = report_api.get_role_members(api, role_id=role_id, offset=offset, limit=batch_size)
        members = list(members_response.get("items", []))
        if not members:
            break

        for member in members:
            member_id = str(member.get("id", "")).strip()
            if member_id == user_id:
                has_member = True
                break

        if has_member:
            break

        total_count = int(members_response.get("count", 0) or 0)
        if offset + len(members) >= total_count:
            break
        offset += batch_size

    cache[cache_key] = has_member
    return has_member


def _resolve_services_csv(host: dict[str, Any]) -> str:
    service_names = {
        str((service or {}).get("service", "")).strip()
        for service in (host.get("services", []) or [])
        if str((service or {}).get("service", "")).strip()
    }
    return ", ".join(sorted(service_names))


def _build_rows_for_user(
    *,
    api: object,
    user_id: str,
    host: dict[str, Any],
    active_accounts: set[str],
    role_membership_cache: dict[tuple[str, str], bool],
) -> list[dict[str, str]]:
    target_host = ",".join(sorted(host.get("addresses", []) or []))
    services_csv = _resolve_services_csv(host)
    rows_by_key: dict[tuple[str, str, str], set[str]] = {}

    for principal in host.get("principals", []) or []:
        account = str((principal or {}).get("principal", "")).strip()
        if not account:
            continue
        if _normalize(account) in active_accounts:
            continue

        matching_role_names: set[str] = set()
        for role in (principal or {}).get("roles", []) or []:
            role_id = str((role or {}).get("id", "")).strip()
            if not role_id:
                continue
            if _role_has_member(api, role_id, user_id, role_membership_cache):
                role_name = str((role or {}).get("name", "")).strip() or role_id
                matching_role_names.add(role_name)

        if not matching_role_names:
            continue

        row_key = (target_host, account, services_csv)
        if row_key not in rows_by_key:
            rows_by_key[row_key] = set()
        rows_by_key[row_key].update(matching_role_names)

    rows: list[dict[str, str]] = []
    for (row_target_host, row_account, row_services), role_names in rows_by_key.items():
        rows.append(
            {
                "target_host": row_target_host,
                "account": row_account,
                "services": row_services,
                "roles": ", ".join(sorted(role_names)),
            }
        )

    return rows


def _search_hosts_for_user(target_address: str) -> list[dict[str, Any]]:
    api = get_cached_privx_client()
    username = str(st.session_state.get(keys.USERNAME) or "").strip()
    if not username:
        raise RuntimeError("Could not resolve your session username.")
    matched_users = get_privx_user_matches(username)
    if not matched_users:
        raise RuntimeError("Could not resolve your PrivX user ids for this session.")

    batch_size = EnvConfig.get_api_batchsize()
    offset = 0
    hosts: list[dict[str, Any]] = []

    while True:
        hosts_response = report_api.hosts.search_hosts(
            api,
            search_payload={"address": [target_address]},
            offset=offset,
            limit=batch_size,
        )
        items = list(hosts_response.get("items", [])) if hosts_response else []
        if not items:
            break
        hosts.extend(items)

        total_count = int(hosts_response.get("count", 0) or 0)
        if offset + len(items) >= total_count:
            break
        offset += batch_size

    if not hosts:
        return []

    role_membership_cache: dict[tuple[str, str], bool] = {}
    grouped_rows: list[dict[str, Any]] = []
    for matched_user in matched_users:
        user_id = str(matched_user.get("id", "")).strip()
        user_principal = str(matched_user.get("principal", "")).strip()
        user_source_type = str(matched_user.get("source_type", "")).strip() or "Unknown"
        if not user_id:
            continue

        user_rows: list[dict[str, str]] = []
        for host in hosts:
            host_id = str(host.get("id", "")).strip()
            if not host_id:
                continue

            host_connections = _fetch_host_connections(api, host_id)
            active_accounts = {
                _normalize(connection.get("target_host_account", ""))
                for connection in host_connections
                if _is_active_connection(connection) and _normalize(connection.get("target_host_account", ""))
            }

            user_rows.extend(
                _build_rows_for_user(
                    api=api,
                    user_id=user_id,
                    host=host,
                    active_accounts=active_accounts,
                    role_membership_cache=role_membership_cache,
                )
            )

        user_rows.sort(
            key=lambda row: (
                row["target_host"],
                row["account"],
                row["services"],
            )
        )
        grouped_rows.append(
            {
                "user_id": user_id,
                "principal": user_principal,
                "source_type": user_source_type,
                "rows": user_rows,
            }
        )

    grouped_rows.sort(
        key=lambda group: (
            str(group.get("principal", "")).casefold(),
            str(group.get("source_type", "")).casefold(),
            str(group.get("user_id", "")),
        )
    )
    return grouped_rows


def main() -> None:
    setup_page(page_title=constants.USER_PAGE_TITLE, show_sidebar=True)

    can_view_my_page = is_privx_user()
    logger.info("My Page route guard evaluated allowed=%s", can_view_my_page)
    if not can_view_my_page:
        st.warning("This page is available only for users found in PrivX.")
        st.switch_page("pages/_1_Home.py")
        return

    st.title("My Page")
    st.subheader("Available Host Accounts")
    st.caption("Find unused host accounts available to you.")

    with st.form("my_page_target_search"):
        target_address = st.text_input("Target address", value="", help="Example: host FQDN or IP address")
        submitted = st.form_submit_button("Search")

    if not submitted:
        return

    normalized_target = target_address.strip()
    if not normalized_target:
        st.warning("Provide a target address first.")
        return

    with st.spinner("Searching available accounts..."):
        try:
            grouped_results = _search_hosts_for_user(normalized_target)
        except Exception as exc:
            st.error(f"Failed to load free accounts: {exc}")
            return

    total_rows = sum(len(group.get("rows", [])) for group in grouped_results)
    if total_rows == 0:
        st.info("No available accounts found for your user and target address.")
        return

    for group in grouped_results:
        principal = str(group.get("principal", "")).strip() or "(missing principal)"
        source_type = str(group.get("source_type", "")).strip() or "Unknown"
        user_rows = group.get("rows", [])
        if not user_rows:
            continue

        st.markdown(f"**Principal:** `{principal}`  \n**Source type:** `{source_type}`")
        st.dataframe(
            user_rows,
            width="stretch",
            hide_index=True,
            column_order=["target_host", "account", "services", "roles"],
        )

    st.caption(f"Found {total_rows} available account row(s).")

main()
