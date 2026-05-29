"""Connection sync source implementation."""

from __future__ import annotations

from typing import Any

import lib.report_api as report_api
from lib.database.models.sync.connection import ConnectionTable
from lib.database.sync.time_series.protocol import FetchResult


def _build_connection_record_id(connection: dict[str, Any]) -> str | None:
    connection_id = connection.get("id")
    connected = connection.get("connected")
    if connection_id and connected:
        return f"{connection_id}|{connected}"
    return None


class ConnectionSync:
    """Sync source for PrivX connections."""

    table = ConnectionTable
    timestamp_key = "connected"
    name = "connections"

    def prepare(self, api: object) -> None:
        del api
        return None

    def fetch_batch(
        self,
        api: object,
        start_time: str,
        end_time: str,
        offset: int,
        limit: int,
    ) -> FetchResult:
        data = report_api.search_connections(
            api,
            offset=offset,
            limit=limit,
            search_payload={"connected": {"start": start_time, "end": end_time}},
            propagate_errors=True,
        )
        return FetchResult(items=data["items"], count=len(data["items"]), total_count=data.get("count"))

    def filter_item(self, item: dict[str, Any], context: object) -> bool:
        del item, context
        return True

    def normalize_item(self, item: dict[str, Any]) -> None:
        del item

    def build_record_id(self, item: dict[str, Any]) -> str | None:
        return _build_connection_record_id(item)

    def build_row_extras(self, item: dict[str, Any]) -> dict[str, Any]:
        del item
        return {}
