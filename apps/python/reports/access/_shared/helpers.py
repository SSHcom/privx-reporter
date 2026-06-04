# Default search order how to report user names in the output file.
# NOTE: Not all user records have "principal" field defined necessarily,
# hence the script will check samaccountname and DN fields as a backup
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import privx_api

from lib import report_api
from lib.env import EnvConfig

USERNAME_ATTRIBUTES_TO_CHECK = ["full_name", "principal", "samaccountname", "distinguished_name"]


def get_username_info(members_data: dict[str, Any]) -> list[str]:
    """
    Get usernames: check (configurable) list of fields to find usernames.

    Args:
        members_data: Dictionary containing role members with 'items' key.

    Returns:
        list[str]: List of found usernames.
    """
    app_members = []
    members = members_data.get("items", [])

    for member in members:
        username_found = False
        for attribute in USERNAME_ATTRIBUTES_TO_CHECK:
            if attribute in member and member[attribute]:
                app_members.append(member[attribute])
                username_found = True
                break

        if not username_found:
            # Did not find username, please configure script to
            # use correct fields for user name attributes
            app_members.append("UserID not found")

    return app_members


def fetch_all_role_members(api: "privx_api.PrivXAPI", role_id: str) -> list[dict[str, Any]]:
    """
    Fetch all members for a role using pagination.

    Args:
        api: PrivX API client instance
        role_id: Role ID to fetch members for

    Returns:
        list[dict]: List of member dictionaries.
    """
    batch_size = EnvConfig.get_api_batchsize()
    offset = 0
    all_members = []

    while True:
        members_response = report_api.get_role_members(api, role_id=role_id, offset=offset, limit=batch_size)
        members = members_response.get("items", [])
        if not members:
            break

        all_members.extend(members)

        total_count = members_response.get("count", 0)
        if len(all_members) >= total_count:
            break

        offset += batch_size

    return all_members


def group_hosts_by_account(hosts_data: list[dict[str, Any]]) -> dict[str, dict[str, list[str]]]:
    """
    Group hosts by their target accounts.

    Args:
        hosts_data: List of host dictionaries with 'id', 'addresses' and 'principals' keys.

    Returns:
        dict mapping account string to {"addresses": [host addresses], "ids": [host ids]}.
    """
    # Map hosts to accounts: (address_str, host_id) -> account_str
    hosts_accounts: dict[tuple[str, str], str] = {}
    for host_data in hosts_data:
        accounts = []
        for principal in host_data.get("principals", []):
            if principal.get("principal"):
                accounts.append(principal["principal"])

        addresses = host_data.get("addresses", [])
        address_str = ",".join(addresses)
        host_id = host_data.get("id", "")
        if address_str:
            hosts_accounts[(address_str, host_id)] = ",".join(accounts) if accounts else ""

    # Group hosts by account
    hosts_by_account: dict[str, dict[str, list[str]]] = {}
    for (host_addr, host_id), account in sorted(hosts_accounts.items()):
        if account not in hosts_by_account:
            hosts_by_account[account] = {"addresses": [], "ids": []}
        hosts_by_account[account]["addresses"].append(host_addr)
        if host_id:
            hosts_by_account[account]["ids"].append(host_id)

    return hosts_by_account
