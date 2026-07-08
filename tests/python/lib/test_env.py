"""Tests for lib/env.py helpers."""

from pathlib import Path
from unittest.mock import patch

import pytest

from lib.env import (
    REPORT_OUT_DIR_BASENAME,
    EnvConfig,
    default_report_out_dir,
)


@pytest.mark.unit
def test_default_report_out_dir_uses_resolved_home() -> None:
    with patch.object(Path, "home", return_value=Path("/home/testuser")):
        assert default_report_out_dir() == f"/home/testuser/{REPORT_OUT_DIR_BASENAME}"


@pytest.mark.unit
@patch.dict("os.environ", {}, clear=True)
def test_get_report_out_dir_falls_back_to_default() -> None:
    with patch.object(Path, "home", return_value=Path("/home/testuser")):
        assert EnvConfig.get_report_out_dir() == f"/home/testuser/{REPORT_OUT_DIR_BASENAME}"


@pytest.mark.unit
@patch.dict("os.environ", {"REPORT_OUT_DIR": "/custom/reports"}, clear=True)
def test_get_report_out_dir_uses_environment() -> None:
    assert EnvConfig.get_report_out_dir() == "/custom/reports"
