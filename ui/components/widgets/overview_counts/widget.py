"""Render overview entity count metrics using native Streamlit components."""

from __future__ import annotations

from typing import TYPE_CHECKING

import altair as alt
import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable

_ROW_1 = [
    ("roles", "Roles"),
    ("local_users", "Local Users"),
    ("hosts", "Hosts"),
    ("network_targets", "Network Targets"),
    ("api_targets", "API Targets"),
]

_ROW_2 = [
    ("access_groups", "Access Groups"),
    ("workflows", "Workflows"),
    ("secrets", "Secrets"),
    ("sources", "Sources"),
    ("api_clients", "API Clients"),
]

_ROW_3 = [
    ("hosts_ssh", "SSH Hosts"),
    ("hosts_rdp", "RDP Hosts"),
    ("hosts_vnc", "VNC Hosts"),
    ("hosts_web", "Web Hosts"),
    ("hosts_db", "DB Hosts"),
]

# All metrics with trend data
_TREND_METRICS = [
    ("roles", "Roles"),
    ("local_users", "Local Users"),
    ("hosts", "Hosts"),
    ("network_targets", "Network Targets"),
    ("api_targets", "API Targets"),
    ("access_groups", "Access Groups"),
    ("workflows", "Workflows"),
    ("secrets", "Secrets"),
    ("sources", "Sources"),
    ("api_clients", "API Clients"),
]

_TREND_COLS_PER_ROW = 3


def _render_row(items: list[tuple[str, str]], data: dict[str, object]) -> None:
    label_style = "font-size:1rem; font-weight:700; color:#666666; margin:0 0 0.3rem 0;"
    value_style = "font-size:2.2rem; font-weight:500; line-height:1.1; margin:0 0 0.8rem 0;"

    cols = st.columns(len(items), gap="medium")
    for col, (key, label) in zip(cols, items):
        with col:
            with st.container(border=True):
                value = int(data.get(key, 0))
                st.markdown(
                    f'<div style="width:100%; text-align:center; margin:0 auto;">'
                    f'<div style="{label_style}">{label}</div>'
                    f'<div style="{value_style}">{value:,}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )


def _to_trend_df(data: dict[str, object], trend_key: str, metric: str) -> pd.DataFrame:
    rows = data.get(trend_key, [])
    if not isinstance(rows, list) or not rows:
        return pd.DataFrame(columns=["timestamp", metric])

    df = pd.DataFrame(rows)
    if "timestamp" not in df.columns or metric not in df.columns:
        return pd.DataFrame(columns=["timestamp", metric])

    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df[metric] = pd.to_numeric(df[metric], errors="coerce").fillna(0).astype(int)
    df = df.dropna(subset=["timestamp"]).sort_values("timestamp")
    return df


def _render_sparkline(df: pd.DataFrame, metric: str, label: str) -> None:
    """Render a compact trend chart with axes and date markers."""
    if df.empty:
        st.markdown(
            '<div style="text-align:center; color:#999; font-size:0.8rem; padding:1rem 0;">No data</div>',
            unsafe_allow_html=True,
        )
        return

    plot_df = df[["timestamp", metric]].copy()
    plot_df["timestamp"] = pd.to_datetime(plot_df["timestamp"], errors="coerce")
    plot_df[metric] = pd.to_numeric(plot_df[metric], errors="coerce")
    plot_df = plot_df.dropna(subset=["timestamp", metric]).sort_values("timestamp")
    if plot_df.empty:
        st.markdown(
            '<div style="text-align:center; color:#999; font-size:0.8rem; padding:1rem 0;">No data</div>',
            unsafe_allow_html=True,
        )
        return

    latest_val = int(plot_df[metric].iloc[-1])
    label_style = "width:100%; text-align:center; margin:0 auto; font-size:0.85rem; font-weight:700; color:#666;"
    value_style = "width:100%; text-align:center; margin:0 0 0.45rem 0; font-size:1.4rem; font-weight:500;"
    st.markdown(
        (
            '<div style="padding:0.45rem 0;">'
            f'<div style="{label_style}">{label}</div>'
            f'<div style="{value_style}">{latest_val:,}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    chart = (
        alt.Chart(plot_df)
        .mark_area(
            line={"color": "#4A90D9", "strokeWidth": 1.5},
            point=alt.OverlayMarkDef(color="#4A90D9", size=20),
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="rgba(74,144,217,0.3)", offset=0),
                    alt.GradientStop(color="rgba(74,144,217,0.02)", offset=1),
                ],
                x1=1,
                x2=1,
                y1=1,
                y2=0,
            ),
        )
        .encode(
            x=alt.X(
                "timestamp:T",
                title=None,
                axis=alt.Axis(format="%b %d", labelAngle=-45, tickCount="day", grid=False),
            ),
            y=alt.Y(
                f"{metric}:Q",
                title=None,
                axis=alt.Axis(tickMinStep=1, grid=True, gridDash=[2, 2]),
                scale=alt.Scale(zero=True),
            ),
            tooltip=[
                alt.Tooltip("timestamp:T", title="Date", format="%Y-%m-%d"),
                alt.Tooltip(f"{metric}:Q", title=label, format=","),
            ],
        )
        .properties(height=150)
        .configure_view(strokeWidth=0)
    )
    st.altair_chart(chart, width="stretch")


def _has_any_trend_data(data: dict[str, object]) -> bool:
    """Check if any trend rows exist at all (sync enabled and has run)."""
    for metric, _ in _TREND_METRICS:
        rows = data.get(f"{metric}_trend", [])
        if isinstance(rows, list) and len(rows) > 0:
            return True
    return False


def _render_all_trends(data: dict[str, object]) -> None:
    """Render compact sparkline trend charts in a 5-column grid."""
    if not _has_any_trend_data(data):
        st.info("No trend data available. Trend sync may be disabled or has not run yet.")
        return

    window_days = st.selectbox(
        "Trend window",
        options=[7, 30, 90],
        index=1,
        format_func=lambda d: f"Last {d} days",
        key="dashboard_overview_trend_window",
    )

    # Build filtered DataFrames — only include metrics that have non-zero data
    trend_items: list[tuple[str, str, pd.DataFrame]] = []
    for metric, label in _TREND_METRICS:
        df = _to_trend_df(data, f"{metric}_trend", metric)
        if df.empty:
            continue
        latest_ts = df["timestamp"].max()
        cutoff = latest_ts - pd.Timedelta(days=int(window_days) - 1)
        df = df.loc[df["timestamp"] >= cutoff].copy()
        if df[metric].sum() == 0:
            continue
        trend_items.append((metric, label, df))

    if not trend_items:
        st.info("No trend data available for the selected window.")
        return

    # Render in compact grid
    for row_start in range(0, len(trend_items), _TREND_COLS_PER_ROW):
        row_items = trend_items[row_start : row_start + _TREND_COLS_PER_ROW]
        cols = st.columns(_TREND_COLS_PER_ROW, gap="small")
        for col, (metric, label, df) in zip(cols, row_items):
            with col:
                with st.container(border=True):
                    _render_sparkline(df, metric, label)


def render(fetch_data: Callable[[], dict[str, object]]) -> None:
    """Render entity count metric cards and trend charts."""
    data = fetch_data()

    error = str(data.get("error", "")).strip()
    if error:
        st.error(error)
        return

    _render_row(_ROW_1, data)
    _render_row(_ROW_2, data)
    st.divider()
    st.subheader("Host counts by service type")
    _render_row(_ROW_3, data)
    st.divider()
    st.subheader("System Trends")
    _render_all_trends(data)

    st.caption(f"Last updated: {data.get('updated_at', '-')}")
