"""Helper builders for list report tests."""

from lib.utils.config.report_ids import ReportIds


def report_ids(sub_command: str) -> ReportIds:
    return ReportIds(
        command="list",
        sub_command=sub_command,
        report_prefix=f"list-{sub_command}",
        config_key=f"list.subcommands.{sub_command}",
    )


def output_config(sub_command: str, fields: dict[str, str]) -> dict:
    return {"list": {"subcommands": {sub_command: {"fields": fields}}}}
