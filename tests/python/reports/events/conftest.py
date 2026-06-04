"""Shared fixtures for events report tests."""

import pytest

from lib.utils.config.report_ids import ReportIds


@pytest.fixture
def events_query_output_config() -> dict:
    return {
        "events": {
            "subcommands": {
                "query": {
                    "fields": {
                        "event_id": "true|Event ID",
                        "event_name": "true|Event Name",
                        "timestamp": "true|Timestamp",
                    }
                }
            }
        }
    }


@pytest.fixture
def events_accounts_output_config() -> dict:
    return {
        "events": {
            "subcommands": {
                "accounts": {
                    "fields": {
                        "event_id": "true|Event ID",
                        "action": "true|Action",
                        "principal": "true|Principal",
                        "timestamp": "true|Timestamp",
                    }
                }
            }
        }
    }


@pytest.fixture
def events_role_members_output_config() -> dict:
    return {
        "events": {
            "subcommands": {
                "role-members": {
                    "fields": {
                        "event_id": "true|Event ID",
                        "action": "true|Action",
                        "role_id": "true|Role ID",
                        "user_id": "true|User ID",
                    }
                }
            }
        }
    }


@pytest.fixture
def report_ids_events_query() -> ReportIds:
    return ReportIds(
        command="events",
        sub_command="query",
        report_prefix="events-query",
        config_key="events.subcommands.query",
    )


@pytest.fixture
def report_ids_events_accounts() -> ReportIds:
    return ReportIds(
        command="events",
        sub_command="accounts",
        report_prefix="events-accounts",
        config_key="events.subcommands.accounts",
    )


@pytest.fixture
def report_ids_events_role_members() -> ReportIds:
    return ReportIds(
        command="events",
        sub_command="role-members",
        report_prefix="events-role-members",
        config_key="events.subcommands.role-members",
    )
