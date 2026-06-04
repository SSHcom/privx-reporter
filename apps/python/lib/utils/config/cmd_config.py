"""Configuration reading from config.toml."""

from typing import Any

from lib._report.error import ConfigError


def get_subcommand_config(config: dict[str, Any], group: str, subcommand: str) -> dict[str, Any]:
    """
    Get output configuration for a report subcommand.

    Args:
        config: Global configuration dictionary
        group: Report group name (e.g., "access", "connections", "roles")
        subcommand: Subcommand name (e.g., "map", "details", "query")

    Returns:
        Full config dict containing output configuration

    Raises:
        ConfigError: If output configuration is not found
    """
    try:
        config[group]["subcommands"][subcommand]
        return config
    except KeyError as e:
        raise ConfigError(
            f"Output configuration not found for {group} {subcommand}",
            "Check your configuration file for the required output settings",
        ) from e
