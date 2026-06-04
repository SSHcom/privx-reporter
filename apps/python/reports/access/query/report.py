"""Query-based access report module.

This report allows querying host access using various filters.
Output: One row per user-role-host-account permutation.

This module uses a batch-based processing approach:
1. Resolve filter names to IDs
2. Build API search payload
3. Fetch and process hosts in batches
4. Apply post-filtering and accumulate results
"""

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import privx_api

from lib import report_api
from lib._report.error import handle_error
from lib.env import EnvConfig
from lib.utils.config import get_field_names_and_headers
from lib.utils.config.report_ids import ReportIds
from lib.utils.dict import validate_dict_contains
from reports._shared.access_group import resolve_allowed_access_group_ids
from reports._shared.output import write_report_output
from reports.access._shared.cache import fetch_access_group_details_cached
from reports.access._shared.helpers import fetch_all_role_members
from reports.access._shared.models import QueryReportInputs

logger = logging.getLogger(__name__)


def search_access_groups_by_filter(
    api: "privx_api.PrivXAPI",
    name_filter: str | None = None,
    comment_filter: str | None = None,
) -> list[str]:
    """
    Search access groups by name or comment and return matching IDs.

    Args:
        api: PrivX API client instance
        name_filter: Substring to match in access group name (case-insensitive)
        comment_filter: Substring to match in access group comment (case-insensitive)

    Returns:
        list: List of access group IDs matching the filters
    """
    if not name_filter and not comment_filter:
        return []

    response_data = report_api.search_access_groups(api, offset=0, limit=1000)

    if not response_data:
        logger.warning("Failed to search access groups")
        return []

    access_groups = response_data.get("items", [])
    matching_ids = []

    for group in access_groups:
        group_name = group.get("name", "").lower()
        group_comment = group.get("comment", "").lower()
        group_id = group.get("id")

        if name_filter and name_filter.lower() in group_name:
            if group_id and group_id not in matching_ids:
                matching_ids.append(group_id)
                logger.info(f"Found access group by name: {group.get('name')} (ID: {group_id})")
            continue

        if comment_filter and comment_filter.lower() in group_comment:
            if group_id and group_id not in matching_ids:
                matching_ids.append(group_id)
                logger.info(f"Found access group by comment: {group.get('name')} (ID: {group_id})")

    return matching_ids


def _create_access_record(
    member: dict[str, Any],
    role_id: str,
    role_name: str,
    host: dict[str, Any],
    account_name: str,
    service_type_str: str,
    access_group_details: dict[str, Any],
    tags: str,
) -> dict[str, Any]:
    host_addresses = host.get("addresses", [])
    host_id = host.get("id", "")
    host_common_name = host.get("common_name", "")
    access_group_id = host.get("access_group_id", "")

    return {
        "user_id": member.get("id"),
        "user_name": member.get("full_name"),
        "role_id": role_id,
        "role_name": role_name,
        "target_host": ",".join(sorted(host_addresses)),
        "target_host_id": host_id,
        "target_account": account_name,
        "host_common_name": host_common_name,
        "access_group_id": access_group_id,
        "service_type": service_type_str,
        **access_group_details,
        "tags": tags,
    }


def _apply_user_filter(
    members: list[dict[str, Any]],
    user_name: str | None,
) -> list[dict[str, Any]]:
    if not user_name:
        return members

    filter_lower = user_name.lower()
    return [m for m in members if filter_lower in m.get("full_name", "").lower()]


def _process_single_host(
    api: "privx_api.PrivXAPI",
    host: dict[str, Any],
    user_name: str | None,
    role_members_cache: dict[str, list[dict]],
    access_group_cache: dict[str, dict],
    filtered_role_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Process a single host and generate access records.

    Args:
        api: PrivX API client instance
        host: Host dictionary from API
        user_name: Optional user name filter
        role_members_cache: Cache for role members
        access_group_cache: Cache for access group details
        filtered_role_ids: Optional list of role IDs to filter by. If provided,
                          only roles in this list will be included in the output.
    """
    host_records: list[dict[str, Any]] = []

    access_group_id = host.get("access_group_id", "")

    if access_group_id and access_group_id not in access_group_cache:
        access_group_cache[access_group_id] = fetch_access_group_details_cached(api, access_group_id)

    access_group_details = access_group_cache.get(
        access_group_id,
        {
            "access_group_name": "",
            "access_group_comment": "",
            "access_group_default": False,
        },
    )

    services = host.get("services", [])
    service_types = sorted(set(s.get("service", "") for s in services))
    service_type_str = ",".join(service_types)

    for principal in host.get("principals", []):
        account_name = principal.get("principal", "")

        for role in principal.get("roles", []):
            role_id = role.get("id")
            role_name_value = role.get("name", "")

            # If role filtering is active, skip roles not in the filter list
            if filtered_role_ids is not None and role_id not in filtered_role_ids:
                continue

            tags = host.get("tags", [])

            if tags:
                tags = ",".join(tags)

            if role_id not in role_members_cache:
                logger.debug(f"Fetching members for role: {role_name_value}")
                try:
                    role_members_cache[role_id] = fetch_all_role_members(api, role_id)
                except Exception as e:
                    # Role might have been deleted or is inaccessible
                    logger.warning(f"Skipping role '{role_name_value}' (ID: {role_id}): {str(e)}")
                    role_members_cache[role_id] = []  # Cache empty list to avoid retrying

            members = role_members_cache[role_id]

            filtered_members = _apply_user_filter(members, user_name)

            for member in filtered_members:
                record = _create_access_record(
                    member, role_id, role_name_value, host, account_name, service_type_str, access_group_details, tags
                )
                host_records.append(record)

    return host_records


def _process_host_batch(
    api: "privx_api.PrivXAPI",
    hosts: list[dict[str, Any]],
    user_name: str | None,
    role_members_cache: dict[str, list[dict]],
    access_group_cache: dict[str, dict],
    filtered_role_ids: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Process a batch of hosts and generate access records.

    Args:
        api: PrivX API client instance
        hosts: List of host dictionaries from API
        user_name: Optional user name filter
        role_members_cache: Cache for role members
        access_group_cache: Cache for access group details
        filtered_role_ids: Optional list of role IDs to filter by
    """
    batch_records: list[dict[str, Any]] = []

    for host in hosts:
        host_records = _process_single_host(
            api,
            host,
            user_name,
            role_members_cache,
            access_group_cache,
            filtered_role_ids,
        )
        batch_records.extend(host_records)

    return batch_records


def _validate_output_records(
    all_access_data: list[dict[str, Any]],
    field_names: list[str],
) -> str | None:
    for idx, data_item in enumerate(all_access_data):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            user_name = data_item.get("user_name", "unknown")
            role_name = data_item.get("role_name", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for entry {idx + 1} "
                f"(user: {user_name}, role: {role_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file.",
            )
            return error_message
    return None


def search_roles_by_name(api: "privx_api.PrivXAPI", name_filter: str) -> list[str]:
    """Search roles by exact name and return matching IDs.

    Args:
        api: PrivX API client instance
        name_filter: Exact role name to match (case-insensitive)

    Returns:
        List of role IDs with exact name match
    """
    search_payload = {"keywords": name_filter}
    response_data = report_api.search_roles(api, search_payload)

    if not response_data:
        logger.warning("Failed to search roles")
        return []

    roles = response_data.get("items", [])
    matching_ids = []

    for role in roles:
        role_name = role.get("name", "")
        role_id = role.get("id")

        # Exact match (case-insensitive)
        if name_filter.lower() == role_name.lower():
            if role_id:
                matching_ids.append(role_id)
                logger.info(f"Found role by exact name: {role_name} (ID: {role_id})")

    return matching_ids


def report_access_query(
    api: "privx_api.PrivXAPI",
    inputs: QueryReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate filtered host access report using batch-based processing.

    This function processes hosts in batches, applying filters and generating
    access records incrementally to improve memory efficiency and provide
    progress feedback.

    Args:
        api: PrivX API client instance
        inputs: Query report inputs containing all filter options and output options
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Precomputed report identifiers (prefix and config key)
        requested_fields: Optional list of field names from CLI --fields option
    """
    target_address = inputs.target_address or None
    common_name = inputs.common_name or None
    target_account = inputs.target_account or None
    access_group_name = inputs.access_group_name or None
    access_group_comment = inputs.access_group_comment or None
    service_type = inputs.service_type or None
    role_name = inputs.role_name or None
    user_name = inputs.user_name or None
    tags_input = inputs.tags or None

    if not any(
        [
            target_address,
            common_name,
            target_account,
            access_group_name,
            access_group_comment,
            service_type,
            role_name,
            user_name,
            tags_input,
        ]
    ):
        error_message = "At least one filter is required."
        return {
            "report_path": None,
            "error_message": error_message,
            "info_message": None,
        }

    batch_size = EnvConfig.get_api_batchsize()
    logger.info("Building search criteria...")

    search_payload: dict[str, Any] = {}

    if target_address:
        search_payload["keywords"] = target_address
        logger.info(f"Filter: target address contains '{target_address}'")

    if common_name:
        search_payload["common_name"] = [common_name]
        logger.info(f"Filter: common_name = '{common_name}'")

    if access_group_name or access_group_comment:
        logger.info("Searching for access groups...")
        access_group_ids = search_access_groups_by_filter(api, access_group_name, access_group_comment)
        if not access_group_ids:
            info_message = (
                f"No access groups found matching "
                f"name='{access_group_name or 'N/A'}' "
                f"comment='{access_group_comment or 'N/A'}'"
            )
            logger.info(info_message)
            return {
                "report_path": None,
                "error_message": None,
                "info_message": info_message,
            }
        search_payload["access_group_ids"] = access_group_ids
        logger.info(f"Filter: {len(access_group_ids)} matching access groups")

    if role_name:
        logger.info(f"Searching for role with exact name '{role_name}'...")
        role_ids = search_roles_by_name(api, role_name)
        if not role_ids:
            info_message = f"No role found with exact name '{role_name}'"
            logger.info(info_message)
            return {
                "report_path": None,
                "error_message": None,
                "info_message": info_message,
            }
        search_payload["role"] = role_ids
        logger.info(f"Filter: {len(role_ids)} matching role(s)")
        # Store filtered role IDs for post-processing
        filtered_role_ids = role_ids
    else:
        filtered_role_ids = None

    if service_type:
        search_payload["service"] = [service_type]
        logger.info(f"Filter: service type = '{service_type}'")

    if tags_input:
        tags_list = [t.strip() for t in tags_input.split(",") if t.strip()]
        if tags_list:
            search_payload["tags"] = tags_list
            logger.info(f"Filter: tags = {tags_list}")

    if not search_payload:
        return {
            "report_path": None,
            "error_message": "At least one additional filter besides 'user-name' or 'target-account' is required.",
            "info_message": None,
        }

    logger.info(f"Search payload: {list(search_payload.keys())}")

    role_members_cache: dict[str, list[dict]] = {}
    access_group_cache: dict[str, dict] = {}
    all_access_data: list[dict[str, Any]] = []
    allowed_access_group_ids: set[str] | None = None

    if user_group_id is not None:
        allowed_access_group_ids, resolution_error = resolve_allowed_access_group_ids(api, user_group_id)
        if resolution_error:
            return {
                "report_path": None,
                "error_message": resolution_error,
                "info_message": None,
            }

    offset = 0
    batch_count = 0
    total_hosts = 0

    while True:
        data = report_api.hosts.search_hosts(api, search_payload, offset=offset, limit=batch_size)
        if not data:
            break
        hosts = data.get("items", [])
        api_returned_count = len(hosts)

        if api_returned_count == 0:
            break

        if allowed_access_group_ids is not None:
            hosts = [
                host
                for host in hosts
                if isinstance(host.get("access_group_id"), str) and host["access_group_id"] in allowed_access_group_ids
            ]

        returned_count = len(hosts)
        batch_count += 1
        total_hosts += returned_count

        logger.info(
            f"Processing batch {batch_count}: {returned_count} hosts (offset {offset}, total processed: {total_hosts})"
        )

        batch_records = _process_host_batch(
            api,
            hosts,
            user_name,
            role_members_cache,
            access_group_cache,
            filtered_role_ids,
        )

        all_access_data.extend(batch_records)
        logger.info(
            f"Batch {batch_count} generated {len(batch_records)} access entries (total: {len(all_access_data)})"
        )

        if api_returned_count < batch_size:
            break

        offset += batch_size

    logger.info(
        f"Completed processing {batch_count} batches, {total_hosts} hosts, {len(all_access_data)} access entries"
    )

    # Post-filter by target account if specified
    if target_account:
        filter_lower = target_account.lower()
        all_access_data = [r for r in all_access_data if filter_lower == r.get("target_account", "").lower()]
        logger.info(f"Filtered to {len(all_access_data)} entries matching target_account='{target_account}'")

    if not all_access_data:
        if total_hosts == 0:
            info_message = "No hosts found matching the specified search criteria"
        else:
            info_message = "No access entries found matching the specified filters"
        logger.info(info_message)
        return {
            "report_path": None,
            "error_message": None,
            "info_message": info_message,
        }

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    validation_error = _validate_output_records(all_access_data, field_names)
    if validation_error:
        return {
            "report_path": None,
            "error_message": validation_error,
            "info_message": None,
        }

    output_data = [{field: data_item[field] for field in field_names} for data_item in all_access_data]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
