from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReportIds:
    command: str = ""
    sub_command: str = ""
    report_prefix: str = ""
    config_key: str = ""


def make_report_ids(command: str, sub_command: str) -> ReportIds:
    """Compute common report identifiers from command/subcommand.

    Returns a dict containing:
    - command: top-level command (e.g. "access")
    - sub_command: subcommand (e.g. "host-map")
    - report_prefix: report filename prefix (e.g. "access-host-map")
    - config_key: output config key path (e.g. "access.subcommands.host-map")
    """
    return ReportIds(
        command=command,
        sub_command=sub_command,
        report_prefix=f"{command}.{sub_command}",
        config_key=f"{command}.subcommands.{sub_command}",
    )
