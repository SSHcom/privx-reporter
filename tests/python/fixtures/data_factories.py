"""Factory functions for creating test data structures."""

from __future__ import annotations

from typing import Any


def create_role(role_id: str = "role1", name: str = "admin", **overrides: Any) -> dict[str, Any]:  # noqa: ANN401
    """Factory for creating test role data.

    Args:
        role_id: The role ID
        name: The role name
        **overrides: Additional fields to override

    Returns:
        A role dictionary
    """
    base = {
        "id": role_id,
        "name": name,
    }
    base.update(overrides)
    return base


def create_role_member(
    principal: str = "user1",
    full_name: str = "User One",
    email: str | None = None,
    source_type: str = "LDAP",
    **overrides: Any,  # noqa: ANN401
) -> dict[str, Any]:
    """Factory for creating test role member data.

    Args:
        principal: The principal/username
        full_name: The user's full name
        email: The user's email (defaults to principal@example.com)
        source_type: The source type (LDAP, LOCAL, etc.)
        **overrides: Additional fields to override

    Returns:
        A role member dictionary
    """
    if email is None:
        email = f"{principal}@example.com"

    base = {
        "principal": principal,
        "full_name": full_name,
        "email": email,
        "samaccountname": principal,
        "windows_account": principal,
        "unix_account": principal,
        "source_type": source_type,
    }
    base.update(overrides)
    return base


def create_connection(
    conn_id: str = "conn-1",
    user_id: str = "user-1",
    user_display_name: str = "John Doe",
    host_id: str = "host-1",
    host_name: str = "server1.example.com",
    host_address: str = "192.168.1.10",
    host_account: str = "root",
    conn_type: str = "SSH",
    status: str = "TERMINATED",
    duration: int = 870,
    **overrides: Any,  # noqa: ANN401
) -> dict[str, Any]:
    """Factory for creating test connection data.

    Args:
        conn_id: Connection ID
        user_id: User ID
        user_display_name: User display name
        host_id: Target host ID
        host_name: Target host common name
        host_address: Target host IP address
        host_account: Target host account
        conn_type: Connection type (SSH, RDP, etc.)
        status: Connection status
        duration: Connection duration in seconds
        **overrides: Additional fields to override

    Returns:
        A connection dictionary
    """
    base = {
        "id": conn_id,
        "created": "2026-01-02T10:00:00Z",
        "connected": "2026-01-02T10:00:30Z",
        "disconnected": "2026-01-02T10:15:00Z",
        "duration": duration,
        "status": status,
        "type": conn_type,
        "user": {"id": user_id, "display_name": user_display_name},
        "target_host": {"id": host_id, "common_name": host_name},
        "target_host_address": host_address,
        "target_host_account": host_account,
    }
    base.update(overrides)
    return base


def create_host(
    host_id: str = "host-1",
    common_name: str = "server1.example.com",
    addresses: list[str] | None = None,
    **overrides: Any,  # noqa: ANN401
) -> dict[str, Any]:
    """Factory for creating test host data.

    Args:
        host_id: Host ID
        common_name: Host common name
        addresses: List of IP addresses
        **overrides: Additional fields to override

    Returns:
        A host dictionary
    """
    if addresses is None:
        addresses = ["192.168.1.10"]

    base = {
        "id": host_id,
        "common_name": common_name,
        "addresses": addresses,
    }
    base.update(overrides)
    return base


def create_user(
    user_id: str = "user-1",
    principal: str = "user1",
    full_name: str = "User One",
    email: str | None = None,
    **overrides: Any,  # noqa: ANN401
) -> dict[str, Any]:
    """Factory for creating test user data.

    Args:
        user_id: User ID
        principal: User principal/username
        full_name: User's full name
        email: User's email (defaults to principal@example.com)
        **overrides: Additional fields to override

    Returns:
        A user dictionary
    """
    if email is None:
        email = f"{principal}@example.com"

    base = {
        "id": user_id,
        "principal": principal,
        "full_name": full_name,
        "email": email,
    }
    base.update(overrides)
    return base


def create_audit_event(
    event_id: str = "event-1",
    event_code: str = "CONNECT",
    user_id: str = "user-1",
    timestamp: str = "2026-01-02T10:00:00Z",
    **overrides: Any,  # noqa: ANN401
) -> dict[str, Any]:
    """Factory for creating test audit event data.

    Args:
        event_id: Event ID
        event_code: Event code
        user_id: User ID
        timestamp: Event timestamp
        **overrides: Additional fields to override

    Returns:
        An audit event dictionary
    """
    base = {
        "id": event_id,
        "code": event_code,
        "user_id": user_id,
        "timestamp": timestamp,
    }
    base.update(overrides)
    return base
