from __future__ import annotations

import math

import streamlit as st

from ui.components.sidebar import render_sidebar
from ui.components.widgets.sync_status import data as sync_status_data
from ui.services.page_bootstrap import setup_page
from ui.services.permissions import is_admin

setup_page(page_title="Sync Status", show_sidebar=False)

if not is_admin():
    st.error("Access denied. This page is restricted to administrators.")
    st.stop()

render_sidebar()

st.title("Sync Status")
st.caption("Data source: TimescaleDB sync tables")

if st.button("Refresh", key="admin_sync_status_refresh"):
    st.rerun()

payload = sync_status_data.fetch_data()
rows = list(payload.get("sources", []))
sync_configured = bool(payload.get("sync_configured", False))


def _normalize_cell(value: object) -> object:
    if value is None:
        return "N/A"
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "" or stripped.lower() in {"none", "nan", "nat", "-"}:
            return "N/A"
        return value
    if isinstance(value, float) and math.isnan(value):
        return "N/A"
    return value


if sync_configured:
    table_columns = [
        "source",
        "record_count",
        "earliest_record",
        "latest_record",
        "sync_interval_minutes",
        "retention_days",
    ]
else:
    table_columns = [
        "source",
        "record_count",
        "earliest_record",
        "latest_record",
    ]

if not rows:
    st.info("No sync status rows available.")
else:
    display_rows = [{key: _normalize_cell(row.get(key)) for key in table_columns} for row in rows]
    st.dataframe(
        display_rows,
        width="stretch",
        hide_index=True,
        column_order=table_columns,
    )

with st.expander("Column descriptions", expanded=False):
    if sync_configured:
        st.markdown(
            """
- `record_count`: Total rows currently stored in the source table.
- `earliest_record`: Oldest timestamp currently stored.
- `latest_record`: Newest timestamp currently stored.
- `sync_interval_minutes`: Source sync frequency from `SYNC_CONNECTION` / `SYNC_AUDIT`
  (the configured gap in minutes between consecutive sync run starts).
- `sync_hour_utc`: Daily trend refresh target hour from `SYNC_TREND_HOUR` (UTC).
  Actual run can occur shortly after, depending on previous sync runs.
- `retention_days`: Expected retention window for that source.
"""
        )
    else:
        st.markdown(
            """
- `record_count`: Total rows currently stored in the source table.
- `earliest_record`: Oldest timestamp currently stored.
- `latest_record`: Newest timestamp currently stored.
"""
        )

st.caption(f"Last updated: {payload.get('updated_at', '-')}")
