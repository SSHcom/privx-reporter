from __future__ import annotations

import json
import threading
import time
from typing import TYPE_CHECKING

import pytest

from ui.services import data_fetch_manager

if TYPE_CHECKING:
    from pathlib import Path


def _read_current_payload(cache_dir: Path, source_id: str) -> dict[str, object]:
    current_path = cache_dir / source_id / "current.json"
    with current_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.mark.unit
def test_load_page_writes_cache_and_reader_returns_data(tmp_path: Path) -> None:
    manager = data_fetch_manager.DataFetchManager(cache_dir=tmp_path)
    call_count = 0

    def _source() -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        return {"label": "Demo 1", "value": 123}

    readers = manager.load_page_data("misc", {"demo1": _source})

    assert call_count == 1
    assert readers["demo1"]() == {"label": "Demo 1", "value": 123}
    payload = _read_current_payload(tmp_path, "demo1")
    assert payload["label"] == "Demo 1"
    assert payload["_meta"]["page_id"] == "misc"
    assert payload["_meta"]["source_id"] == "demo1"


@pytest.mark.unit
def test_load_page_uses_fresh_cache_without_refetch(tmp_path: Path) -> None:
    manager = data_fetch_manager.DataFetchManager(cache_dir=tmp_path)
    call_count = 0

    def _source() -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        return {"value": call_count}

    manager.load_page_data("misc", {"demo1": _source}, data_ttl_seconds=300)
    manager.load_page_data("misc", {"demo1": _source}, data_ttl_seconds=300)

    assert call_count == 1


@pytest.mark.unit
def test_load_page_refetches_when_stale_by_ttl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manager = data_fetch_manager.DataFetchManager(cache_dir=tmp_path)
    now_holder = {"value": 1_000.0}

    monkeypatch.setattr(data_fetch_manager.time, "time", lambda: float(now_holder["value"]))
    call_count = 0

    def _source() -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        return {"value": call_count}

    manager.load_page_data("misc", {"demo1": _source}, data_ttl_seconds=300)
    now_holder["value"] = 1_100.0
    manager.load_page_data("misc", {"demo1": _source}, data_ttl_seconds=300)

    assert call_count == 1

    now_holder["value"] = 1_400.0
    manager.load_page_data("misc", {"demo1": _source}, data_ttl_seconds=300)

    assert call_count == 2


@pytest.mark.unit
def test_load_page_reports_progress_for_each_refreshed_source(tmp_path: Path) -> None:
    manager = data_fetch_manager.DataFetchManager(cache_dir=tmp_path)
    updates: list[tuple[int, int]] = []

    manager.load_page_data(
        "misc",
        {
            "demo1": lambda: {"label": "A"},
            "demo2": lambda: {"label": "B"},
        },
        on_progress=lambda done, total: updates.append((done, total)),
    )

    assert updates == [(1, 2), (2, 2)]


@pytest.mark.unit
def test_force_refresh_clears_callback_cache_and_rotates_previous(tmp_path: Path) -> None:
    manager = data_fetch_manager.DataFetchManager(cache_dir=tmp_path)
    state = {"value": 1}
    cleared: list[bool] = []

    class Source:
        def __call__(self) -> dict[str, object]:
            return {"value": state["value"]}

        def clear(self) -> None:
            cleared.append(True)

    source = Source()

    manager.load_page_data("misc", {"demo1": source})
    first_payload = _read_current_payload(tmp_path, "demo1")
    assert first_payload["value"] == 1

    state["value"] = 2
    manager.load_page_data("misc", {"demo1": source}, force_refresh=True)

    second_payload = _read_current_payload(tmp_path, "demo1")
    previous_path = tmp_path / "demo1" / "previous.json"
    with previous_path.open("r", encoding="utf-8") as handle:
        previous_payload = json.load(handle)

    assert cleared == [True]
    assert second_payload["value"] == 2
    assert previous_payload["value"] == 1


@pytest.mark.unit
def test_get_cache_age_and_clear_cache(tmp_path: Path) -> None:
    manager = data_fetch_manager.DataFetchManager(cache_dir=tmp_path)
    manager.load_page_data("misc", {"demo1": lambda: {"label": "x"}})

    age = manager.get_cache_age("demo1")
    assert age is not None
    assert age >= 0

    manager.clear_cache("demo1")
    assert manager.get_cache_age("demo1") is None


@pytest.mark.unit
def test_format_data_age_renders_compact_hours_minutes_seconds() -> None:
    assert data_fetch_manager.format_data_age(0) == "0s"
    assert data_fetch_manager.format_data_age(59.9) == "59s"
    assert data_fetch_manager.format_data_age(60) == "1m"
    assert data_fetch_manager.format_data_age(154) == "2m 34s"
    assert data_fetch_manager.format_data_age(3600) == "1h"
    assert data_fetch_manager.format_data_age(3725) == "1h 2m 5s"
    assert data_fetch_manager.format_data_age(-1) == "0s"


@pytest.mark.unit
def test_load_page_can_skip_auto_refresh_and_require_cache(tmp_path: Path) -> None:
    manager = data_fetch_manager.DataFetchManager(cache_dir=tmp_path)
    call_count = 0

    def _source() -> dict[str, object]:
        nonlocal call_count
        call_count += 1
        return {"value": call_count}

    readers = manager.load_page_data(
        "misc",
        {"demo1": _source},
        auto_refresh_stale=False,
    )
    assert call_count == 0
    assert manager.has_cache("demo1") is False
    with pytest.raises(RuntimeError):
        readers["demo1"]()

    manager.load_page_data("misc", {"demo1": _source}, force_refresh=True)
    assert manager.has_cache("demo1") is True

    # With cache present and auto-refresh disabled, stale data is returned as-is.
    manager.load_page_data(
        "misc",
        {"demo1": _source},
        auto_refresh_stale=False,
        data_ttl_seconds=0,
    )
    assert call_count == 1


@pytest.mark.unit
def test_is_fetch_in_progress_tracks_active_fetch(tmp_path: Path) -> None:
    manager = data_fetch_manager.DataFetchManager(cache_dir=tmp_path)
    fetch_started = threading.Event()
    release_fetch = threading.Event()

    def _source() -> dict[str, object]:
        fetch_started.set()
        release_fetch.wait(timeout=5)
        return {"value": 1}

    worker = threading.Thread(
        target=lambda: manager.load_page_data("misc", {"demo1": _source}, force_refresh=True),
        daemon=True,
    )
    worker.start()
    assert fetch_started.wait(timeout=1)
    assert manager.is_fetch_in_progress() is True
    assert manager.get_active_fetch_view_label() == "misc"

    release_fetch.set()
    worker.join(timeout=2)
    assert not worker.is_alive()

    # Allow lock state visibility to settle after worker completion.
    time.sleep(0.01)
    assert manager.is_fetch_in_progress() is False
    assert manager.get_active_fetch_view_label() is None


@pytest.mark.unit
def test_get_active_fetch_view_label_returns_page_label_when_provided(tmp_path: Path) -> None:
    manager = data_fetch_manager.DataFetchManager(cache_dir=tmp_path)
    fetch_started = threading.Event()
    release_fetch = threading.Event()

    def _source() -> dict[str, object]:
        fetch_started.set()
        release_fetch.wait(timeout=5)
        return {"value": 1}

    worker = threading.Thread(
        target=lambda: manager.load_page_data(
            "behavior_risk",
            {"demo1": _source},
            page_label="Behavior & Risk Analytics",
            force_refresh=True,
        ),
        daemon=True,
    )
    worker.start()
    assert fetch_started.wait(timeout=1)
    assert manager.get_active_fetch_view_label() == "Behavior & Risk Analytics"

    release_fetch.set()
    worker.join(timeout=2)
    assert not worker.is_alive()
