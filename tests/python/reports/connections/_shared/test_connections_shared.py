"""Tests for shared connections report utilities."""

import pytest

from reports.connections._shared import extract_target_ips


@pytest.mark.unit
@pytest.mark.parametrize(
    ("dst_list", "expected"),
    [
        (None, ""),
        ([], ""),
        ([{"selector": {"ip": {"start": "192.168.0.1"}}}], "192.168.0.1"),
        (
            [
                {"selector": {"ip": {"start": "10.0.0.1", "end": "10.0.0.10"}}},
                {"selector": {"ip": {"start": "10.0.0.1"}}},
                {"selector": {"ip": {"start": "10.0.0.10"}}},
            ],
            "10.0.0.1-10.0.0.10",
        ),
    ],
)
def test_extract_target_ips_basic_cases(dst_list: list[dict] | None, expected: str) -> None:
    assert extract_target_ips(dst_list) == expected


@pytest.mark.unit
@pytest.mark.parametrize(
    ("dst_list", "expected"),
    [
        (
            [
                {"selector": {"ip": {"start": "10.0.0.1", "end": "10.0.0.20"}}},
                {"selector": {"ip": {"start": "10.0.0.1", "end": "10.0.0.20"}}},
                {"selector": {"ip": {"start": "30.0.0.1", "end": "30.0.0.40"}}},
                {"selector": {"ip": {"start": "50.0.0.5"}}},
                {"selector": {"ip": {"start": "10.0.0.1"}}},
            ],
            "10.0.0.1-10.0.0.20, 30.0.0.1-30.0.0.40, 50.0.0.5",
        ),
        (
            [
                {},
                {"selector": {}},
                {"selector": {"ip": {}}},
                {"selector": {"ip": {"start": ""}}},
                {"selector": {"ip": {"start": "192.168.1.10"}}},
                {"selector": {"ip": {"start": "172.16.0.1", "end": "172.16.0.1"}}},
            ],
            "192.168.1.10, 172.16.0.1",
        ),
    ],
)
def test_extract_target_ips_complex_cases(dst_list: list[dict], expected: str) -> None:
    assert extract_target_ips(dst_list) == expected
