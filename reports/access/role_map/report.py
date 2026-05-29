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
from reports.access._shared.helpers import fetch_all_role_members
from reports.access._shared.models import RoleMapReportInputs

logger = logging.getLogger(__name__)


def _get_roles_from_host(host_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """
    Extract roles and their associated accounts from a host's principals.

    Args:
        host_data: Host data dictionary containing principals.

    Returns:
        dict mapping role_id to dict with role name and account list.
    """
    role_accounts: dict[str, dict[str, Any]] = {}

    for principal in host_data.get("principals", []):
        account_name = principal.get("principal", "")
        if not account_name:
            continue

        for role in principal.get("roles", []):
            role_id = role.get("id")
            role_name = role.get("name", "")
            if not role_id:
                continue

            if role_id not in role_accounts:
                role_accounts[role_id] = {"name": role_name, "accounts": []}
            role_accounts[role_id]["accounts"].append(account_name)

    return role_accounts


def report_user_role_access_map(
    api: "privx_api.PrivXAPI",
    inputs: RoleMapReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """Generate a user role access map report for a specific target host.

    Lists all users who can access the specified host, with one row per user.

    Args:
        api: PrivX API client instance
        inputs: Role map report inputs containing target_address, to_json, to_stdout
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Precomputed report identifiers (prefix and config key).
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """
    logger.info(f"Searching for host with address '{inputs.target_address}'")

    hosts_response = report_api.hosts.search_hosts(api, search_payload={"keywords": inputs.target_address})
    hosts_data = hosts_response.get("items", []) if hosts_response else []

    if not hosts_data:
        info_message = f"No hosts found matching address '{inputs.target_address}'"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    logger.info(f"Found {len(hosts_data)} matching host(s)")

    allowed_access_group_ids: set[str] | None = None
    if user_group_id is not None:
        allowed_access_group_ids, resolution_error = resolve_allowed_access_group_ids(api, user_group_id)
        if resolution_error:
            return {"report_path": None, "error_message": resolution_error, "info_message": None}
        if allowed_access_group_ids is None:
            return {
                "report_path": None,
                "error_message": "Failed to resolve allowed access groups",
                "info_message": None,
            }

        hosts_data = [
            host
            for host in hosts_data
            if isinstance(host.get("access_group_id"), str) and host["access_group_id"] in allowed_access_group_ids
        ]
        logger.info("Access group filter applied: %s host(s) remain", len(hosts_data))

        if not hosts_data:
            info_message = "No hosts found for your allowed access groups"
            logger.info(info_message)
            return {"report_path": None, "error_message": None, "info_message": info_message}

    all_access_data: list[dict[str, Any]] = []

    for host in hosts_data:
        host_addresses = host.get("addresses", [])
        target_host_str = ",".join(sorted(host_addresses))

        role_accounts = _get_roles_from_host(host)

        if not role_accounts:
            continue

        for role_id, role_info in role_accounts.items():
            role_name = role_info["name"]
            accounts = role_info["accounts"]
            target_accounts_str = ",".join(sorted(accounts))

            logger.info(f"Processing role: {role_name}")

            all_members = fetch_all_role_members(api, role_id)

            for member in all_members:
                all_access_data.append(
                    {
                        "user_id": member.get("id", ""),
                        "user_name": member.get("full_name", ""),
                        "samaccountname": member.get("samaccountname", ""),
                        "windows_account": member.get("windows_account", ""),
                        "unix_account": member.get("unix_account", ""),
                        "role_id": role_id,
                        "role_name": role_name,
                        "target_host": target_host_str,
                        "target_accounts": target_accounts_str,
                    }
                )

    logger.info(f"Found {len(all_access_data)} access map entries")

    if not all_access_data:
        info_message = f"No users found who can access host '{inputs.target_address}'"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    for idx, data_item in enumerate(all_access_data):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            user_name = data_item.get("user_name", "unknown")
            role_name = data_item.get("role_name", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for access map entry {idx + 1} "
                f"(user: {user_name}, role: {role_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    output_data = [{field: data_item[field] for field in field_names} for data_item in all_access_data]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
