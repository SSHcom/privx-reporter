import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import privx_api

from lib import report_api
from lib._report.error import handle_error
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from reports._shared.access_group import resolve_allowed_access_group_ids
from reports._shared.output import write_report_output
from reports.access._shared.models import HostsReportInputs

logger = logging.getLogger(__name__)

PAGE_SIZE = 100

"""Report: hosts accessible by a user.
Given a user (by name, ID, or principal), resolves their roles and
cross-references them against all hosts to produce an access report.
Call graph
----------
report_hosts_access()                          ← entry point
├── _build_source_map()                        API: get_sources
├── _search_users()                            API: get_user / search_users
├── _apply_directory_filter()                  (optional)
├── get_user_group_by_id()                     (optional, if --user-group)
│   └── search_access_groups()                 API: access_groups
├── _collect_user_roles()                      API: get_user_roles
│                                              returns (user_roles_map, all_role_ids)
├── _collect_all_access_data()                 main loop over host pages
│   ├── _fetch_hosts_page()                    API: search_hosts (paginated)
│   └── _build_access_data_for_host_batch()    cross-join users × roles × hosts
│       ├── _host_has_role()
│       └── _build_access_entry()
├── _render_access_map()                       (optional, if --to-map)
├── _validate_access_data_fields()
└── write_report_output()
Each access entry is a flat dict with keys like user_id, user_name,
role_name, target_host, target_accounts, etc.
"""


def _build_report_result(
    *,
    report_path: str | None = None,
    error_message: str | None = None,
    info_message: str | None = None,
) -> dict[str, Any]:
    return {
        "report_path": report_path,
        "error_message": error_message,
        "info_message": info_message,
    }


def _build_source_map(api: "privx_api.PrivXAPI") -> dict[str, str]:
    """Fetch all sources and build a source_id -> source_name lookup."""
    source_map: dict[str, str] = {}
    try:
        response = api.get_sources()
        if response.ok:
            for source in response.data.get("items", []):
                source_map[source.get("id", "")] = source.get("name", "")
    except Exception as e:
        logger.warning("Failed to fetch sources: %s", e)
    return source_map


def _search_users(
    api: "privx_api.PrivXAPI",
    user_name: str | None = None,
    user_id: str | None = None,
    principal: str | None = None,
    source_map: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """Search for users by exact user_name, user_id, or exact principal.

    Returns list of user dicts with source_name resolved from source_map.
    """
    if source_map is None:
        source_map = {}

    if user_id:
        user = report_api.users.get_user_by_id(api, user_id)
        if user:
            user["source_name"] = source_map.get(user.get("source", ""), "")
            return [user]
        return []

    # Search by keyword (user_name or principal)
    keyword = user_name or principal or ""
    users_response = report_api.users.search_users(api, search_payload={"keywords": keyword})
    users = users_response.get("items", []) if users_response else []

    # Resolve source names
    for user in users:
        user["source_name"] = source_map.get(user.get("source", ""), "")

    # Apply exact match filtering
    if user_name:
        exact = [u for u in users if u.get("full_name", "").lower() == user_name.lower()]
        if not exact:
            return []  # Caller handles the "no exact match" message
        return exact

    if principal:
        exact = [u for u in users if u.get("principal", "").lower() == principal.lower()]
        if not exact:
            return []
        return exact

    return users


def _apply_directory_filter(users_data: list[dict[str, Any]], directory: str) -> list[dict[str, Any]]:
    directory_filter = directory.upper()
    return [user for user in users_data if user.get("source_type", "").upper() == directory_filter]


def _validate_access_data_fields(all_access_data: list[dict[str, Any]], field_names: list[str]) -> str | None:
    for idx, data_item in enumerate(all_access_data):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            user_id_item = data_item.get("user_id", "unknown")
            role_name = data_item.get("role_name", "unknown")
            available_fields = list(data_item.keys())
            return handle_error(
                f"Output configuration validation failed for user-hosts access entry {idx + 1} "
                f"(user: {user_id_item}, role: {role_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file.",
            )
    return None


def _collect_all_access_data(
    api: "privx_api.PrivXAPI",
    users_data: list[dict[str, Any]],
    user_roles_map: dict[str, list[dict[str, str]]],
    allowed_access_group_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    all_access_data: list[dict[str, Any]] = []
    offset = 0
    total_processed = 0
    total_hosts_count = 0

    while True:
        host_batch, hosts_count = _fetch_hosts_page(api, offset, PAGE_SIZE)
        if not host_batch:
            break

        if allowed_access_group_ids is not None:
            hosts_before_filter = len(host_batch)
            filtered_host_batch: list[dict[str, Any]] = []

            for host in host_batch:
                host_access_group_id = host.get("access_group_id")
                if isinstance(host_access_group_id, str) and host_access_group_id in allowed_access_group_ids:
                    filtered_host_batch.append(host)
                    continue

            logger.info("Filtered host batch size=%s", len(filtered_host_batch))

            host_batch = filtered_host_batch
            logger.info(
                "Access group filter applied for host batch (offset=%s): before=%s after=%s",
                offset,
                hosts_before_filter,
                len(host_batch),
            )

        if total_hosts_count == 0:
            total_hosts_count = hosts_count
            logger.info("Total hosts to process: %s", total_hosts_count)

        batch_access_data = _build_access_data_for_host_batch(users_data, user_roles_map, host_batch)
        all_access_data.extend(batch_access_data)

        total_processed += len(host_batch)
        logger.info("Processed %s/%s hosts", total_processed, total_hosts_count)

        if total_processed >= hosts_count:
            break

        offset += PAGE_SIZE

    return all_access_data


def _collect_user_roles(
    api: "privx_api.PrivXAPI",
    users_data: list[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, str]]], set[str]]:
    """Collect roles for all users.

    Returns:
        Tuple of (user_roles_map, all_role_ids)
    """
    user_roles_map: dict[str, list[dict[str, str]]] = {}
    all_role_ids: set[str] = set()

    for user in users_data:
        user_id = user.get("id", "")
        user_full_name = user.get("full_name", "")
        source_name = user.get("source_name", "")
        logger.info("Getting roles for user: %s (id: %s, source: %s)", user_full_name, user_id, source_name)

        user_roles = report_api.get_user_roles(api, user_id)

        if user_roles:
            role_names = [role["name"] for role in user_roles]
            user_roles_map[user_id] = user_roles
            for role in user_roles:
                all_role_ids.add(role["id"])
            logger.info("Roles for '%s' [%s]: %s", user_full_name, source_name, ", ".join(role_names))
        else:
            logger.warning("No roles found for user '%s' (id: %s)", user_full_name, user_id)

    return user_roles_map, all_role_ids


def _fetch_hosts_page(api: "privx_api.PrivXAPI", offset: int, limit: int) -> tuple[list[dict[str, Any]], int]:
    """Fetch a single page of hosts."""
    logger.info("Fetching hosts page (offset=%s, limit=%s)", offset, limit)
    hosts_response = report_api.hosts.search_hosts(api, search_payload={}, offset=offset, limit=limit)

    if not hosts_response:
        return [], 0

    hosts_data = hosts_response.get("items", [])
    total_count = hosts_response.get("count", 0)
    logger.info("Fetched %s hosts (total available: %s)", len(hosts_data), total_count)
    return hosts_data, total_count


def _host_has_role(host: dict[str, Any], role_id: str) -> bool:
    for principal in host.get("principals", []):
        for role in principal.get("roles", []):
            if role.get("id") == role_id:
                return True
    return False


def _build_access_entry(
    user_id: str,
    user_full_name: str,
    principal: str,
    source_name: str,
    role_id: str,
    role_name: str,
    host: dict[str, Any],
) -> dict[str, Any]:
    host_id = host.get("id", "")
    host_name = host.get("distinguished_name") or host.get("common_name") or "N/A"
    host_addresses = host.get("addresses", [])
    target_host_str = ",".join(sorted(host_addresses)) if host_addresses else "N/A"

    accounts = []
    for host_principal in host.get("principals", []):
        if host_principal.get("principal"):
            accounts.append(host_principal["principal"])

    target_accounts_str = ",".join(sorted(set(accounts)))

    return {
        "user_id": user_id,
        "user_name": user_full_name,
        "principal": principal,
        "source_name": source_name,
        "role_id": role_id,
        "role_name": role_name,
        "target_host": target_host_str,
        "target_host_name": host_name,
        "target_host_id": host_id,
        "target_accounts": target_accounts_str,
    }


def _build_access_data_for_host_batch(
    users_data: list[dict[str, Any]],
    user_roles_map: dict[str, list[dict[str, str]]],
    host_batch: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    access_data: list[dict[str, Any]] = []

    for user in users_data:
        user_id = user.get("id", "")
        user_full_name = user.get("full_name", "")
        principal = user.get("principal", "")
        source_name = user.get("source_name", "")
        user_roles = user_roles_map.get(user_id, [])

        for role in user_roles:
            role_id = role["id"]
            role_name = role["name"]
            filtered_hosts = [h for h in host_batch if _host_has_role(h, role_id)]

            for host in filtered_hosts:
                access_data.append(
                    _build_access_entry(
                        user_id=user_id,
                        user_full_name=user_full_name,
                        principal=principal,
                        source_name=source_name,
                        role_id=role_id,
                        role_name=role_name,
                        host=host,
                    )
                )

    return access_data


def _render_access_map(all_access_data: list[dict[str, Any]]) -> str:
    """Render access data as an ASCII tree map: User -> Role -> Host (target accounts)."""
    from collections import OrderedDict

    # Store hosts as list of tuples: (host_name, target_accounts_str)
    user_roles: OrderedDict[str, OrderedDict[str, list[tuple[str, str]]]] = OrderedDict()

    for entry in all_access_data:
        user_label = f"{entry.get('user_name', '')} ({entry.get('principal', '')})"
        role_name = entry.get("role_name", "")
        host_name = entry.get("target_host_name", "") or entry.get("target_host", "")
        target_accounts = entry.get("target_accounts", "")

        if user_label not in user_roles:
            user_roles[user_label] = OrderedDict()
        if role_name not in user_roles[user_label]:
            user_roles[user_label][role_name] = []

        # Avoid duplicate hosts within the same role
        existing_hosts = [h[0] for h in user_roles[user_label][role_name]]
        if host_name not in existing_hosts:
            user_roles[user_label][role_name].append((host_name, target_accounts))

    # Count totals
    total_roles = sum(len(roles) for roles in user_roles.values())
    total_hosts = sum(len(hosts) for roles in user_roles.values() for hosts in roles.values())

    lines: list[str] = []

    # Header
    lines.append("Access Map: User -> Roles -> Hosts")
    lines.append(f"  Roles: {total_roles}  |  Hosts: {total_hosts}")
    lines.append("")

    for user_idx, (user_label, roles) in enumerate(user_roles.items()):
        lines.append(f"{user_label}")
        role_items = list(roles.items())

        for role_idx, (role_name, hosts) in enumerate(role_items):
            is_last_role = role_idx == len(role_items) - 1
            role_branch = "└── " if is_last_role else "├── "
            role_continuation = "    " if is_last_role else "│   "

            lines.append(f"{role_branch}{role_name} ({len(hosts)} host{'s' if len(hosts) != 1 else ''})")

            for host_idx, (host, target_accounts) in enumerate(hosts):
                is_last_host = host_idx == len(hosts) - 1
                host_branch = "└── " if is_last_host else "├── "

                # Format target accounts: show names if ≤4, count if >4
                accounts_suffix = ""
                if target_accounts:
                    account_list = [a.strip() for a in target_accounts.split(",") if a.strip()]
                    if account_list:
                        if len(account_list) <= 4:
                            accounts_suffix = f" ({', '.join(account_list)})"
                        else:
                            accounts_suffix = f" ({len(account_list)} accounts)"

                lines.append(f"{role_continuation}{host_branch}{host}{accounts_suffix}")

        if user_idx < len(user_roles) - 1:
            lines.append("")

    return "\n".join(lines)


def report_hosts_access(
    api: "privx_api.PrivXAPI",
    inputs: HostsReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """List all target hosts a specified user can access."""

    # Suppress logging for --to-map so only the tree is printed to stdout
    if inputs.to_map:
        logging.getLogger("reports").setLevel(logging.WARNING)
        logging.getLogger("lib").setLevel(logging.WARNING)

    # Validate at least one search option is provided
    if not inputs.user_name and not inputs.user_id and not inputs.principal:
        input_error = "At least one of --user-name, --user-id, or --principal is required"
        return _build_report_result(error_message=input_error)

    # Build source lookup map
    source_map = _build_source_map(api)

    # Determine search type for logging
    if inputs.user_id:
        logger.info("Searching for user by ID '%s'", inputs.user_id)
    elif inputs.user_name:
        logger.info("Searching for user with exact name '%s'", inputs.user_name)
    elif inputs.principal:
        logger.info("Searching for user with exact principal '%s'", inputs.principal)

    users_data = _search_users(
        api,
        user_name=inputs.user_name or None,
        user_id=inputs.user_id or None,
        principal=inputs.principal or None,
        source_map=source_map,
    )

    if not users_data:
        if inputs.user_name:
            info_message = (
                f"No exact match found for user name '{inputs.user_name}'. "
                "Please try with the complete username or use --principal instead."
            )
        elif inputs.principal:
            info_message = (
                f"No exact match found for principal '{inputs.principal}'. "
                "Please try with the complete principal or use --user-name instead."
            )
        else:
            info_message = f"No user found with ID '{inputs.user_id}'"
        logger.info(info_message)
        return _build_report_result(info_message=info_message)

    # Log found users grouped by source
    for user in users_data:
        logger.info(
            "Found user: %s (principal: %s, source: %s)",
            user.get("full_name", ""),
            user.get("principal", ""),
            user.get("source_name", ""),
        )

    if inputs.directory:
        users_data = _apply_directory_filter(users_data, inputs.directory)
        logger.info("After directory filter '%s': %s user(s) remaining", inputs.directory, len(users_data))

        if not users_data:
            info_message = f"No users found with directory '{inputs.directory}'"
            logger.info(info_message)
            return _build_report_result(info_message=info_message)

    allowed_access_group_ids: set[str] | None = None
    if user_group_id is not None:
        allowed_access_group_ids, resolution_error = resolve_allowed_access_group_ids(api, user_group_id)
        if resolution_error:
            return _build_report_result(error_message=resolution_error)

    user_roles_map, all_role_ids = _collect_user_roles(api, users_data)

    if not all_role_ids:
        info_message = "No roles found for any of the matched users."
        logger.warning(info_message)
        return _build_report_result(info_message=info_message)

    logger.info("Found %s unique role(s) across %s user(s)", len(all_role_ids), len(users_data))

    all_access_data = _collect_all_access_data(
        api,
        users_data,
        user_roles_map,
        allowed_access_group_ids=allowed_access_group_ids,
    )

    logger.info("Found %s access entries", len(all_access_data))

    if not all_access_data:
        info_message = f"No hosts found for any of the {len(users_data)} matched user(s)"
        logger.info(info_message)
        return _build_report_result(info_message=info_message)

    # Handle --to-map output
    if inputs.to_map:
        if not inputs.user_id:
            return _build_report_result(error_message="--to-map can only be used with --user-id")
        map_output = _render_access_map(all_access_data)
        print(map_output)
        return _build_report_result()

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    error_message = _validate_access_data_fields(all_access_data, field_names)
    if error_message:
        return _build_report_result(error_message=error_message)

    output_data = [{field: data_item[field] for field in field_names} for data_item in all_access_data]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
