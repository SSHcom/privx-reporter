"""Protocol and shared types for sync sources."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from sqlalchemy import Table


@dataclass
class FetchResult:
    items: list[dict[str, Any]]
    count: int
    total_count: int | None = None


class SyncSource(Protocol):
    """Interface implemented by each sync source."""

    @property
    def table(self) -> Table: ...

    @property
    def timestamp_key(self) -> str: ...

    @property
    def name(self) -> str: ...

    def prepare(self, api: object) -> object: ...

    def fetch_batch(
        self,
        api: object,
        start_time: str,
        end_time: str,
        offset: int,
        limit: int,
    ) -> FetchResult: ...

    def filter_item(self, item: dict[str, Any], context: object) -> bool: ...

    def normalize_item(self, item: dict[str, Any]) -> None: ...

    def build_record_id(self, item: dict[str, Any]) -> str | None: ...

    def build_row_extras(self, item: dict[str, Any]) -> dict[str, Any]: ...
