"""Tests for filesystem cache utilities."""

import io
import json
import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from reports.access._shared.cache import (
    CACHE_MAX_AGE_SECONDS,
    _cache_access_group,
    _get_cache_dir,
    _get_cached_access_group,
    fetch_access_group_details_cached,
)

# ---- Unit tests (no real filesystem) ----


@pytest.mark.unit
def test_get_cached_access_group_returns_none_when_file_missing() -> None:
    """When cache file does not exist, get_cached_access_group returns None."""
    mock_dir = MagicMock(spec=Path)
    mock_file = MagicMock()
    mock_file.exists.return_value = False
    mock_dir.__truediv__.return_value = mock_file

    with patch("reports.access._shared.cache._get_cache_dir", return_value=mock_dir):
        result = _get_cached_access_group("ag-123")

    assert result is None
    mock_file.stat.assert_not_called()


@pytest.mark.unit
def test_get_cached_access_group_returns_none_and_deletes_when_stale() -> None:
    """When cache file is older than CACHE_MAX_AGE_SECONDS, file is removed and None returned."""
    mock_dir = MagicMock(spec=Path)
    mock_file = MagicMock()
    mock_file.exists.return_value = True
    # st_mtime 2 hours ago
    mock_file.stat.return_value.st_mtime = time.time() - (2 * 3600)
    mock_dir.__truediv__.return_value = mock_file

    with patch("reports.access._shared.cache._get_cache_dir", return_value=mock_dir):
        result = _get_cached_access_group("ag-456")

    assert result is None
    mock_file.unlink.assert_called_once()


@pytest.mark.unit
def test_get_cached_access_group_returns_data_when_fresh() -> None:
    """When cache file exists and is fresh, cached data is returned."""
    mock_dir = MagicMock(spec=Path)
    mock_file = MagicMock()
    mock_file.exists.return_value = True
    mock_file.stat.return_value.st_mtime = time.time() - 60  # 1 minute ago
    mock_dir.__truediv__.return_value = mock_file
    expected = {"access_group_name": "Foo", "access_group_comment": "Bar", "access_group_default": False}

    with patch("reports.access._shared.cache._get_cache_dir", return_value=mock_dir):
        with patch("builtins.open", create=True) as m_open:
            m_open.return_value.__enter__.return_value = io.StringIO(json.dumps(expected))
            result = _get_cached_access_group("ag-789")

    assert result == expected


@pytest.mark.unit
def test_fetch_access_group_details_cached_empty_id_returns_default() -> None:
    """Empty access_group_id returns default dict without hitting cache or API."""
    result = fetch_access_group_details_cached(MagicMock(), "")

    assert result == {
        "access_group_name": "",
        "access_group_comment": "",
        "access_group_default": False,
    }


@pytest.mark.unit
def test_fetch_access_group_details_cached_uses_cache_when_hit() -> None:
    """When cache has data, it is returned and API is not called."""
    cached = {"access_group_name": "Cached", "access_group_comment": "Comment", "access_group_default": True}
    mock_api = MagicMock()

    with patch("reports.access._shared.cache._get_cached_access_group", return_value=cached) as mock_get_cached:
        with patch("reports.access._shared.cache.get_access_group_by_id") as mock_api_fetch:
            result = fetch_access_group_details_cached(mock_api, "ag-1")

    assert result == cached
    mock_get_cached.assert_called_once_with("ag-1")
    mock_api_fetch.assert_not_called()


@pytest.mark.unit
def test_fetch_access_group_details_cached_calls_api_on_cache_miss() -> None:
    """When cache misses, API is called and result is cached and returned."""
    mock_api = MagicMock()
    api_response = {"name": "From API", "comment": "API comment", "default": False}
    expected = {
        "access_group_name": "From API",
        "access_group_comment": "API comment",
        "access_group_default": False,
    }

    with patch("reports.access._shared.cache._get_cached_access_group", return_value=None):
        with patch("reports.access._shared.cache.get_access_group_by_id", return_value=api_response) as mock_fetch:
            with patch("reports.access._shared.cache._cache_access_group") as mock_cache:
                result = fetch_access_group_details_cached(mock_api, "ag-api")

    assert result == expected
    mock_fetch.assert_called_once_with(mock_api, "ag-api")
    mock_cache.assert_called_once_with("ag-api", expected)


@pytest.mark.unit
def test_fetch_access_group_details_cached_returns_default_when_api_returns_none() -> None:
    """When API returns None, default dict is returned and nothing is cached."""
    mock_api = MagicMock()

    with patch("reports.access._shared.cache._get_cached_access_group", return_value=None):
        with patch("reports.access._shared.cache.get_access_group_by_id", return_value=None):
            with patch("reports.access._shared.cache._cache_access_group") as mock_cache:
                result = fetch_access_group_details_cached(mock_api, "ag-missing")

    assert result == {
        "access_group_name": "",
        "access_group_comment": "",
        "access_group_default": False,
    }
    mock_cache.assert_not_called()


# ---- Integration tests (real filesystem) ----


@pytest.mark.integration
def test_get_cache_dir_creates_dir_and_returns_path(tmp_path: Path) -> None:
    """_get_cache_dir creates .tmp/access_groups under report out dir and returns it."""
    from lib.env import EnvConfig

    with patch.object(EnvConfig, "get_report_out_dir", return_value=str(tmp_path)):
        cache_dir = _get_cache_dir()

    assert cache_dir == tmp_path / ".tmp" / "access_groups"
    assert cache_dir.is_dir()


@pytest.mark.integration
def test_cache_and_get_cached_access_group_roundtrip(tmp_path: Path) -> None:
    """_cache_access_group writes a file; _get_cached_access_group reads it back when fresh."""
    from lib.env import EnvConfig

    with patch.object(EnvConfig, "get_report_out_dir", return_value=str(tmp_path)):
        data = {"access_group_name": "Test AG", "access_group_comment": "A comment", "access_group_default": True}
        _cache_access_group("ag-roundtrip", data)

        result = _get_cached_access_group("ag-roundtrip")

    assert result == data
    cache_file = tmp_path / ".tmp" / "access_groups" / "ag-roundtrip.json"
    assert cache_file.exists()
    assert json.loads(cache_file.read_text()) == data


@pytest.mark.integration
def test_get_cached_access_group_returns_none_when_file_does_not_exist(tmp_path: Path) -> None:
    """_get_cached_access_group returns None when no cache file exists."""
    from lib.env import EnvConfig

    with patch.object(EnvConfig, "get_report_out_dir", return_value=str(tmp_path)):
        result = _get_cached_access_group("ag-nonexistent")

    assert result is None


@pytest.mark.integration
def test_get_cached_access_group_discards_stale_file(tmp_path: Path) -> None:
    """When cache file is older than CACHE_MAX_AGE_SECONDS, it is deleted and None returned."""
    from lib.env import EnvConfig

    with patch.object(EnvConfig, "get_report_out_dir", return_value=str(tmp_path)):
        _get_cache_dir()  # ensure dir exists
        cache_file = tmp_path / ".tmp" / "access_groups" / "ag-stale.json"
        cache_file.write_text('{"access_group_name": "Old"}')

        # Set mtime to more than CACHE_MAX_AGE_SECONDS ago
        old_mtime = time.time() - CACHE_MAX_AGE_SECONDS - 60
        cache_file.touch()
        os.utime(cache_file, (old_mtime, old_mtime))

        result = _get_cached_access_group("ag-stale")

    assert result is None
    assert not cache_file.exists()
