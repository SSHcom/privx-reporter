from __future__ import annotations

import json
import re
import threading
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import streamlit as st
from streamlit.logger import get_logger

JsonDict = dict[str, Any]
logger = get_logger(__name__)

if TYPE_CHECKING:
    from collections.abc import Callable


def format_data_age(seconds: float) -> str:
    """Format a duration in seconds as a compact age label."""
    total_seconds = max(0, int(seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, remaining_seconds = divmod(remainder, 60)
    parts: list[str] = []

    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if remaining_seconds > 0 or not parts:
        parts.append(f"{remaining_seconds}s")

    return " ".join(parts)


class DataFetchManager:
    """Coordinate serialized widget data fetches with a JSON file cache."""

    def __init__(self, cache_dir: Path) -> None:
        """Initialize manager state and ensure cache directory exists."""
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._worker_lock = threading.Lock()
        self._status_lock = threading.Lock()
        self._active_page_id: str | None = None
        self._active_page_label: str | None = None

    def load_page_data(
        self,
        page_id: str,
        sources: dict[str, Callable[[], JsonDict]],
        *,
        page_label: str | None = None,
        force_refresh: bool = False,
        auto_refresh_stale: bool = True,
        data_ttl_seconds: int = 300,  # 5 minutes - This is how long the data "lives" before being auto-refreshed
        on_progress: Callable[[int, int], None] | None = None,
    ) -> dict[str, Callable[[], JsonDict]]:
        """Fetch stale sources for a page and return cache reader callbacks."""
        if data_ttl_seconds < 0:
            raise ValueError("data_ttl_seconds must be >= 0")

        if not sources:
            return {}

        refresh_queue: list[tuple[str, Callable[[], JsonDict]]] = []

        for source_id, callback in sources.items():
            source_has_cache = self.has_cache(source_id)
            if force_refresh or (auto_refresh_stale and self._is_source_stale(source_id, data_ttl_seconds)):
                refresh_queue.append((source_id, callback))
            else:
                logger.info(
                    "data_fetch_manager.source page_id=%s source_id=%s source=%s force_refresh=%s",
                    page_id,
                    source_id,
                    "manager_cache" if source_has_cache else "cache_miss",
                    force_refresh,
                )

        total_refresh = len(refresh_queue)

        for index, (source_id, callback) in enumerate(refresh_queue, start=1):
            source = self._fetch_and_store(
                page_id=page_id,
                page_label=page_label,
                source_id=source_id,
                callback=callback,
                force_refresh=force_refresh,
                data_ttl_seconds=data_ttl_seconds,
            )
            logger.info(
                "data_fetch_manager.source page_id=%s source_id=%s source=%s force_refresh=%s",
                page_id,
                source_id,
                source,
                force_refresh,
            )

            if on_progress is not None:
                on_progress(index, total_refresh)

        return {source_id: self._make_reader(source_id) for source_id in sources}

    def get_cache_age(self, source_id: str) -> float | None:
        """Return cache age in seconds for a source, or None if missing."""
        payload = self._read_cache_payload(source_id)

        if payload is None:
            return None

        fetched_at = payload.get("_meta", {}).get("fetched_at")

        if not isinstance(fetched_at, int | float):
            return None

        return max(0.0, time.time() - float(fetched_at))

    def has_cache(self, source_id: str) -> bool:
        """Return True when current cache payload exists for a source."""
        return self._read_cache_payload(source_id) is not None

    def clear_cache(self, source_id: str) -> None:
        """Delete cached files for a source."""
        source_dir = self._source_dir(source_id)

        for file_name in ("current.json", "previous.json"):
            target = source_dir / file_name
            if target.exists():
                target.unlink()

    def is_fetch_in_progress(self) -> bool:
        """Return True when any managed fetch is currently running."""
        return self._worker_lock.locked()

    def get_active_fetch_view_label(self) -> str | None:
        """Return active dashboard view label during an in-progress fetch."""
        if not self.is_fetch_in_progress():
            return None

        with self._status_lock:
            return self._active_page_label

    def _fetch_and_store(
        self,
        *,
        page_id: str,
        page_label: str | None,
        source_id: str,
        callback: Callable[[], JsonDict],
        force_refresh: bool,
        data_ttl_seconds: int,
    ) -> str:
        """Fetch one source under lock and persist it to disk."""
        with self._worker_lock:
            self._set_active_fetch_view(page_id=page_id, page_label=page_label)
            try:
                if not force_refresh and not self._is_source_stale(source_id, data_ttl_seconds):
                    return "manager_cache"

                if force_refresh and hasattr(callback, "clear"):
                    callback.clear()

                data = callback()

                if not isinstance(data, dict):
                    raise TypeError(f"Data source {source_id!r} returned non-dict value")

                self._write_cache_payload(page_id=page_id, source_id=source_id, data=data)
                return "backend_fetch"
            finally:
                self._clear_active_fetch_view()

    def _set_active_fetch_view(self, *, page_id: str, page_label: str | None) -> None:
        """Store current page metadata while a fetch operation runs."""
        normalized_label = page_label.strip() if isinstance(page_label, str) else ""
        with self._status_lock:
            self._active_page_id = page_id
            self._active_page_label = normalized_label or page_id

    def _clear_active_fetch_view(self) -> None:
        """Clear current page metadata after fetch operation completes."""
        with self._status_lock:
            self._active_page_id = None
            self._active_page_label = None

    def _is_source_stale(self, source_id: str, data_ttl_seconds: int) -> bool:
        """Return True when cache is missing, invalid, or older than TTL."""
        payload = self._read_cache_payload(source_id)

        if payload is None:
            return True

        fetched_at = payload.get("_meta", {}).get("fetched_at")

        if not isinstance(fetched_at, int | float):
            return True

        return (time.time() - float(fetched_at)) >= data_ttl_seconds

    def _make_reader(self, source_id: str) -> Callable[[], JsonDict]:
        """Build a callback that reads sanitized cached data for a source."""

        def _reader() -> JsonDict:
            """Return current payload content without internal metadata."""
            payload = self._read_cache_payload(source_id)

            if payload is None:
                raise RuntimeError(f"Missing cached payload for source {source_id!r}")

            data = dict(payload)
            data.pop("_meta", None)
            return data

        return _reader

    def _source_dir(self, source_id: str) -> Path:
        """Resolve and create the cache directory for a source id."""
        safe_source_id = re.sub(r"[^a-zA-Z0-9_.-]+", "_", source_id).strip("._")

        if not safe_source_id:
            raise ValueError("source_id must contain at least one valid character")

        source_dir = self._cache_dir / safe_source_id
        source_dir.mkdir(parents=True, exist_ok=True)
        return source_dir

    def _read_cache_payload(self, source_id: str) -> JsonDict | None:
        """Read a source payload from current cache file, if available."""
        current_path = self._source_dir(source_id) / "current.json"

        if not current_path.exists():
            return None
        try:
            with current_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError):
            return None

        if not isinstance(payload, dict):
            return None

        return payload

    def _write_cache_payload(self, *, page_id: str, source_id: str, data: JsonDict) -> None:
        """Write payload metadata to cache and rotate previous snapshot."""
        source_dir = self._source_dir(source_id)
        current_path = source_dir / "current.json"
        previous_path = source_dir / "previous.json"
        temporary_path = source_dir / "current.json.tmp"

        if current_path.exists():
            current_path.replace(previous_path)

        payload = dict(data)

        payload["_meta"] = {
            "page_id": page_id,
            "source_id": source_id,
            "fetched_at": time.time(),
            "fetched_at_iso": datetime.now(UTC).isoformat(),
        }

        with temporary_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=True, indent=2, sort_keys=True)

        temporary_path.replace(current_path)


@st.cache_resource
def get_data_fetch_manager() -> DataFetchManager:
    """Return shared manager instance across Streamlit sessions."""
    cache_dir = Path.home() / ".reporter" / "widget-data"
    return DataFetchManager(cache_dir=cache_dir)
