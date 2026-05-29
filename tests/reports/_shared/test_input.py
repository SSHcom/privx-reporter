"""Tests for shared report input parsing and validation."""

from argparse import Namespace
from dataclasses import dataclass, field

import pytest

from reports._shared.input import BaseReportInputs, get_report_inputs


@dataclass
class _DemoInputs(BaseReportInputs):
    _mandatory: list[str] = field(default_factory=lambda: ["user_name", "target_host"])
    user_name: str = ""
    target_host: str = ""
    optional_flag: bool = False


@pytest.mark.unit
def test_get_report_inputs_accepts_valid_values() -> None:
    args = Namespace(user_name="alice", target_host="host-1", optional_flag=True)
    parsed = get_report_inputs(_DemoInputs, args)

    assert isinstance(parsed, _DemoInputs)
    assert parsed.user_name == "alice"
    assert parsed.target_host == "host-1"
    assert parsed.optional_flag is True


@pytest.mark.unit
def test_get_report_inputs_rejects_missing_mandatory_fields() -> None:
    args = Namespace(user_name="", target_host="")
    parsed = get_report_inputs(_DemoInputs, args)

    assert isinstance(parsed, BaseReportInputs)
    assert parsed._error_message == "'user-name', 'target-host' are required"


@pytest.mark.unit
def test_get_report_inputs_ignores_unknown_namespace_fields() -> None:
    args = Namespace(user_name="alice", target_host="host-1", unknown_field="ignored")
    parsed = get_report_inputs(_DemoInputs, args)

    assert isinstance(parsed, _DemoInputs)
    assert not hasattr(parsed, "unknown_field")


@pytest.mark.unit
def test_get_report_inputs_none_is_treated_as_missing() -> None:
    args = Namespace(user_name=None, target_host="host-1")
    parsed = get_report_inputs(_DemoInputs, args)

    assert isinstance(parsed, BaseReportInputs)
    assert parsed._error_message == "'user-name' is required"
