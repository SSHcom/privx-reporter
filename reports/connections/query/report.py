"""Query-based connections report module.

This report allows querying connections using various filters.
Output: One row per connection.

This module uses a batch-based processing approach similar to access/query:
1. Resolve filter names where applicable
2. Build API search payload (excluding user_name which is post-filtered)
3. Fetch and process connections in batches
4. Apply post-filtering for user_name
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
from lib.utils.date import validate_date
from lib.utils.dict import validate_dict_contains
from reports._shared.access_group import resolve_allowed_access_group_ids
from reports._shared.output import write_report_output
from reports.connections._shared.models import QueryReportInputs
from reports.connections._shared.query_reports_helpers import extract_connection_fields

logger = logging.getLogger(__name__)


# ============================================================================
# Helper Functions
# ============================================================================


def _apply_user_filter(
    connections: list[dict[str, Any]],
    user_name: str,
) -> list[dict[str, Any]]:
    """
    Apply user_name filter to connections.

    This is a post-filter that checks if the user's full_name matches.
    The user_name filter is resolved to user IDs first, then we check
    which connections belong to those users.

    Args:
        connections: List of connection dictionaries
        user_name: User name filter (substring match, case-insensitive)

    Returns:
        list: Filtered connections
    """
    if not user_name:
        return connections

    filter_lower = user_name.lower()
    return [conn for conn in connections if filter_lower in conn.get("user_name", "").lower()]


def _merge_and_deduplicate_connections(
    connections_list1: list[dict[str, Any]], connections_list2: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """
    Merge two lists of connections and remove duplicates by connection id.

    Args:
        connections_list1: First list of connection dictionaries
        connections_list2: Second list of connection dictionaries

    Returns:
        Merged list with duplicates removed (based on 'id' field)
    """
    # Use a dict to track unique connections by id
    unique_connections = {}

    # Add connections from first list
    for conn in connections_list1:
        conn_id = conn.get("id")
        if conn_id:
            unique_connections[conn_id] = conn

    # Add connections from second list (duplicates will be skipped)
    for conn in connections_list2:
        conn_id = conn.get("id")
        if conn_id and conn_id not in unique_connections:
            unique_connections[conn_id] = conn

    merged = list(unique_connections.values())

    logger.debug(
        f"Merged {len(connections_list1)} + {len(connections_list2)} connections -> {len(merged)} unique connections"
    )

    return merged


def _fetch_all_connections(api: "privx_api.PrivXAPI", batch_size: int, search_payload: dict) -> list:
    """
    Fetch all connections with pagination.

    Args:
        api: PrivX API client instance
        batch_size: Number of items per batch
        search_payload: Search parameters

    Returns:
        List of all fetched connections
    """
    offset = 0
    connections = []

    while True:
        response = report_api.search_connections(api, offset=offset, limit=batch_size, search_payload=search_payload)

        items = response.get("items", [])
        if not items:
            logger.info("No connections found")
            break

        connections.extend(items)

        # Check if we've fetched all connections
        total_count = response.get("count", 0)
        if len(connections) >= total_count:
            break

        offset += batch_size

    logger.debug(f"Fetched {len(connections)} connections from query")
    return connections


# ============================================================================
# Output Validation
# ============================================================================


def _validate_output_records(
    all_connection_data: list[dict[str, Any]],
    field_names: list[str],
) -> str | None:
    """
    Validate that all records contain required fields.

    Args:
        all_connection_data: List of connection records
        field_names: Required field names from output config

    Returns:
        Optional[str]: Error message if validation fails, None otherwise
    """
    for idx, data_item in enumerate(all_connection_data):
        try:
            validate_dict_contains(data_item, field_names)
        except ValueError as e:
            connection_id = data_item.get("connection_id", "unknown")
            available_fields = list(data_item.keys())
            error_message = handle_error(
                f"Output configuration validation failed for connection {idx + 1} (id: {connection_id}): {str(e)}",
                f"Available fields in data: {available_fields}\n"
                f"Required fields from config: {field_names}\n\n"
                "Please check your output configuration file to ensure field names match the data structure.",
            )
            return error_message
    return None


# ============================================================================
# Main Report Function
# ============================================================================
# Note: Tag and user_role filtering for connections is not working in the
# PrivX API. "tags" and "user_roles" parameters exist in the API documentation
# but return 0 results or all results regardless of the filter value.


def report_connections_query(
    api: "privx_api.PrivXAPI",
    inputs: QueryReportInputs,
    output_config: dict[str, Any],
    report_ids: ReportIds,
    requested_fields: list[str] | None = None,
    user_group_id: str | None = None,
) -> dict[str, Any]:
    """
    Generate filtered connections report using batch-based processing.

    This function processes connections in batches, applying filters and
    generating connection records incrementally.

    Args:
        api: PrivX API client instance
        inputs: Query report inputs containing filter options and output settings
        output_config: Output configuration dictionary for field selection (from out.toml)
        report_ids: Precomputed report identifiers (prefix and config key)
        requested_fields: Optional list of field names from CLI --fields option

    Returns:
        dict with keys: report_path, error_message, info_message
    """
    from_date = inputs.from_date
    to_date = inputs.to_date

    # Default to last 7 days if no dates supplied
    if not from_date or not to_date:
        from lib.utils.date import get_date_range

        default_from, default_to = get_date_range(7)
        from_date = from_date or default_from
        to_date = to_date or default_to
        logger.info(f"No date range specified, defaulting to last 7 days: {from_date} to {to_date}")

    target_address = inputs.target_address if inputs.target_address else None
    # target_host_common_name = inputs.target_host_common_name if inputs.target_host_common_name else None
    target_account = inputs.target_account if inputs.target_account else None
    user_name = inputs.user_name if inputs.user_name else None
    connection_type = inputs.connection_type if inputs.connection_type else None

    allowed_access_group_ids: set[str] | None = None
    if user_group_id is not None:
        allowed_access_group_ids, resolution_error = resolve_allowed_access_group_ids(api, user_group_id)
        if resolution_error:
            return {
                "report_path": None,
                "error_message": resolution_error,
                "info_message": None,
            }

    batch_size = EnvConfig.get_api_batchsize()
    logger.info("Building search criteria...")

    # Validate and normalize date formats
    from_date_validated = validate_date(from_date, "from_date")
    to_date_validated = validate_date(to_date, "to_date", end_of_day=True)

    # Build search payload incrementally
    search_payload: dict[str, Any] = {}

    # Add type, address, and account filters
    if connection_type:
        search_payload["type"] = [connection_type]

    if target_account:
        search_payload["target_host_account"] = [target_account]

    # target_host_address in the API stores IP:port (e.g. "172.31.3.170:22"),
    # but users typically query by DNS hostname. Address filtering is done
    # as a post-filter to match against multiple host fields.

    # Fetch connections that connected within the range
    logger.debug("Query 1: Fetching connections where 'connected' is within range")
    search_payload_connected = {"connected": {"start": from_date_validated, "end": to_date_validated}}

    if search_payload:
        search_payload_connected.update(search_payload)

    logger.debug(f"Search payload (connected): {list(search_payload_connected.keys())}")
    connections_by_connected = _fetch_all_connections(api, batch_size, search_payload_connected)

    # Fetch connections that disconnected within the range (catches long-running ones)
    logger.debug("Query 2: Fetching connections where 'disconnected' is within range")
    search_payload_disconnected = {"disconnected": {"start": from_date_validated, "end": to_date_validated}}

    if search_payload:
        search_payload_disconnected.update(search_payload)

    logger.debug(f"Search payload (disconnected): {list(search_payload_disconnected.keys())}")
    connections_by_disconnected = _fetch_all_connections(api, batch_size, search_payload_disconnected)

    # Combine connected and disconnected connections
    all_connections = _merge_and_deduplicate_connections(connections_by_connected, connections_by_disconnected)

    if allowed_access_group_ids is not None:
        all_connections = [conn for conn in all_connections if conn.get("access_group_id") in allowed_access_group_ids]
        logger.info("Connections after access group filter: %s", len(all_connections))

    logger.info(f"Total connections fetched: {len(all_connections)}")

    # Extract fields from all connections (needed for user_name filtering)
    all_connection_data = [extract_connection_fields(conn) for conn in all_connections]

    # Apply target_address post-filter (checks address, common name, and host addresses)
    if target_address:
        logger.info(f"Applying target address filter: '{target_address}'")
        filter_lower = target_address.lower()

        def _matches_address(conn_raw: dict, conn_extracted: dict) -> bool:
            # Check extracted target_host_address (IP:port)
            if filter_lower in conn_extracted.get("target_host_address", "").lower():
                return True
            # Check target host common name
            if filter_lower in conn_extracted.get("target_host_common_name", "").lower():
                return True
            # Check host addresses from target_host_data
            for addr in conn_raw.get("target_host_data", {}).get("addresses", []) or []:
                if filter_lower in addr.lower():
                    return True
            # Check service addresses from target_host_data
            for svc in conn_raw.get("target_host_data", {}).get("services", []) or []:
                if filter_lower in svc.get("address", "").lower():
                    return True
            return False

        filtered_pairs = [
            extracted
            for raw, extracted in zip(all_connections, all_connection_data)
            if _matches_address(raw, extracted)
        ]
        logger.info(f"Connections after address filter: {len(filtered_pairs)}")
        all_connection_data = filtered_pairs

    # Apply user_name post-filter
    if user_name:
        logger.info(f"Applying user name filter: '{user_name}'")
        filtered_connections = _apply_user_filter(all_connection_data, user_name)
        logger.info(f"Connections after user filter: {len(filtered_connections)}")
        all_connection_data = filtered_connections

    # Handle empty results
    if not all_connection_data:
        info_message = "No connections found matching the specified filters"
        logger.info(info_message)
        return {
            "report_path": None,
            "error_message": None,
            "info_message": info_message,
        }

    # Phase 4: Validate and prepare output
    field_names, header_labels = get_field_names_and_headers(
        output_config, report_ids.config_key, requested_fields=requested_fields
    )

    # Validate all records contain required fields
    validation_error = _validate_output_records(all_connection_data, field_names)
    if validation_error:
        return {
            "report_path": None,
            "error_message": validation_error,
            "info_message": None,
        }

    # Extract data in the correct field order
    output_data = [{field: data_item[field] for field in field_names} for data_item in all_connection_data]

    # Write output
    return write_report_output(report_ids.report_prefix, inputs, field_names, header_labels, output_data)
