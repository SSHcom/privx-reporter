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
from reports.access._shared.models import AccountRestrictionsReportInputs

logger = logging.getLogger(__name__)

PAGE_SIZE = 100


def _check_host_has_restrictions(principals: list[dict[str, Any]]) -> bool:
    for principal in principals:
        command_restrictions = principal.get("command_restrictions", {})
        if command_restrictions and command_restrictions.get("enabled", False):
            return True
    return False


def _extract_restrictions_from_host(
    host_id: str, addresses: list[str], principals: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    restrictions = []

    for principal in principals:
        principal_name = principal.get("principal", "")
        command_restrictions = principal.get("command_restrictions", {})

        if not command_restrictions or not command_restrictions.get("enabled", False):
            continue

        default_whitelist = command_restrictions.get("default_whitelist", {})
        default_whitelist_name = default_whitelist.get("name", "") if default_whitelist else ""

        whitelists = command_restrictions.get("whitelists", [])
        whitelist_names = []
        for wl in whitelists:
            whitelist_obj = wl.get("whitelist", {})
            if whitelist_obj and whitelist_obj.get("name"):
                whitelist_names.append(whitelist_obj["name"])

        allow_no_match = command_restrictions.get("allow_no_match", False)
        audit_match = command_restrictions.get("audit_match", False)
        audit_no_match = command_restrictions.get("audit_no_match", False)

        restrictions.append(
            {
                "target_host_id": host_id,
                "target_host": ", ".join(addresses),
                "account_name": principal_name,
                "default_whitelist_name": default_whitelist_name,
                "whitelist_names": ",".join(whitelist_names),
                "allow_no_match": str(allow_no_match),
                "audit_match": str(audit_match),
                "audit_no_match": str(audit_no_match),
            }
        )

    return restrictions


def _search_hosts_with_restrictions(
    api: "privx_api.PrivXAPI",
    target_address: str | None,
    allowed_access_group_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    all_restrictions: list[dict[str, Any]] = []
    offset = 0
    total_processed = 0

    search_payload = {"keywords": target_address} if target_address else {}

    while True:
        hosts_response = report_api.hosts.search_hosts(
            api, search_payload=search_payload, offset=offset, limit=PAGE_SIZE
        )

        if not hosts_response:
            break

        hosts_data = hosts_response.get("items", [])
        hosts_count = hosts_response.get("count", 0)

        if not hosts_data:
            break

        if allowed_access_group_ids is not None:
            hosts_data = [
                host
                for host in hosts_data
                if isinstance(host.get("access_group_id"), str) and host["access_group_id"] in allowed_access_group_ids
            ]

        for host_data in hosts_data:
            host_id = host_data.get("id", "")
            addresses = host_data.get("addresses", [])

            try:
                full_host = report_api.hosts.get_host(api, host_id)
            except Exception as e:
                logger.error(f"Failed to get host details for {host_id}: {e}")
                continue

            principals = full_host.get("principals", [])

            if _check_host_has_restrictions(principals):
                restrictions = _extract_restrictions_from_host(host_id, addresses, principals)
                all_restrictions.extend(restrictions)

        total_processed += len(hosts_data)

        if total_processed >= hosts_count:
            break

        offset += PAGE_SIZE

    return all_restrictions


def report_account_restrictions(
    api: "privx_api.PrivXAPI",
    inputs: AccountRestrictionsReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """
    List users having command restrictions on specified target host.

    Args:
        api: PrivX API client instance
        inputs: Account restrictions report inputs containing target_address, to_json, to_stdout
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Precomputed report identifiers (prefix and config key).
        requested_fields: Optional list of field names from CLI --fields option.
                         If None, uses default field selection from config.
                         If provided, only these fields are included in the specified order.
    """
    if inputs.target_address:
        logger.info(f"Searching for command restrictions on host '{inputs.target_address}'")
    else:
        logger.info("Searching for command restrictions on all hosts")

    allowed_access_group_ids: set[str] | None = None
    if user_group_id is not None:
        allowed_access_group_ids, resolution_error = resolve_allowed_access_group_ids(api, user_group_id)
        if resolution_error:
            return {"report_path": None, "error_message": resolution_error, "info_message": None}

    all_restriction_data = _search_hosts_with_restrictions(
        api,
        inputs.target_address or None,
        allowed_access_group_ids=allowed_access_group_ids,
    )

    if inputs.target_address:
        logger.info(f"Found {len(all_restriction_data)} principals with command restrictions")

    if not all_restriction_data:
        if inputs.target_address:
            info_message = f"No users with command restrictions found on host '{inputs.target_address}'"
        else:
            info_message = "No users with command restrictions found"
        logger.info(info_message)
        return {"report_path": None, "error_message": None, "info_message": info_message}

    logger.info(f"Found {len(all_restriction_data)} principals with command restrictions")

    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    for idx, data_item in enumerate(all_restriction_data):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            host_id = data_item.get("target_host_id", "unknown")
            account_name = data_item.get("account_name", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for host-user-restrict entry {idx + 1} "
                f"(host: {host_id}, account: {account_name}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return {"report_path": None, "error_message": error_message, "info_message": None}

    output_data = [{field: data_item[field] for field in field_names} for data_item in all_restriction_data]

    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
