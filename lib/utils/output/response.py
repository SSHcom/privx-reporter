from typing import Any


def report_response(
    report_path: str = "",
    error_message: str | None = None,
    info_message: str | None = None,
) -> dict[str, Any]:
    """Create a response dictionary for report operations."""
    return {
        "report_path": report_path,
        "error_message": error_message,
        "info_message": info_message,
    }
