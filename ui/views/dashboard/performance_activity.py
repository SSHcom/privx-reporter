"""Performance and activity dashboard view.

Displays concurrent session and connection stats from the concurrent_stats
TimescaleDB table (populated every minute by the sync server).
Uses time_bucket aggregation for larger windows to keep charts readable.
"""

from __future__ import annotations

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import text

from lib.clients.postgresql import use_database
from ui.views.dashboard import (
    get_refresh_cooldown_state,
    mark_refresh,
    render_data_age_caption,
    render_refresh_warning,
    set_refresh_warning_state,
    should_bounce_refresh,
)

# Window options: label -> (minutes, bucket_interval for TimescaleDB)
_WINDOW_OPTIONS = {
    "Last 1 hour": (60, "1 minute"),
    "Last 6 hours": (360, "5 minutes"),
    "Last 24 hours": (1440, "15 minutes"),
    "Last 7 days": (10080, "1 hour"),
    "Last 30 days": (43200, "4 hours"),
}

_NUMERIC_COLS = [
    "sessions",
    "connections_total",
    "connections_ssh",
    "connections_rdp",
    "connections_db",
    "connections_web",
    "connections_vnc",
    "connections_net",
    "connections_mode_ui",
    "connections_mode_mitm",
    "connections_mode_other",
]


def _fetch_concurrent_stats(minutes: int, bucket: str) -> pd.DataFrame:
    """Query concurrent_stats with time_bucket aggregation."""
    db = use_database("data")
    stmt = text(
        """
        SELECT
            time_bucket(:bucket, "timestamp") AS bucket_time,
            MAX((data->>'sessions')::int) AS sessions,
            MAX((data->>'connections_total')::int) AS connections_total,
            MAX((data->>'connections_ssh')::int) AS connections_ssh,
            MAX((data->>'connections_rdp')::int) AS connections_rdp,
            MAX((data->>'connections_db')::int) AS connections_db,
            MAX((data->>'connections_web')::int) AS connections_web,
            MAX((data->>'connections_vnc')::int) AS connections_vnc,
            MAX((data->>'connections_net')::int) AS connections_net,
            MAX((data->>'connections_mode_ui')::int) AS connections_mode_ui,
            MAX((data->>'connections_mode_mitm')::int) AS connections_mode_mitm,
            MAX((data->>'connections_mode_other')::int) AS connections_mode_other
        FROM concurrent_stats
        WHERE "timestamp" >= now() - make_interval(mins => :minutes)
        GROUP BY bucket_time
        ORDER BY bucket_time ASC
        """
    )
    with db.engine.connect() as conn:
        rows = conn.execute(stmt, {"minutes": minutes, "bucket": bucket}).mappings().all()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([dict(r) for r in rows])
    df.rename(columns={"bucket_time": "timestamp"}, inplace=True)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    for col in _NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)
    return df


def _render_kpi_row(df: pd.DataFrame) -> None:
    """Render current (latest) KPI values."""
    if df.empty:
        return

    latest = df.iloc[-1]
    metrics = [
        ("Active Sessions", int(latest.get("sessions", 0))),
        ("Total Connections", int(latest.get("connections_total", 0))),
        ("SSH", int(latest.get("connections_ssh", 0))),
        ("RDP", int(latest.get("connections_rdp", 0))),
        ("Web", int(latest.get("connections_web", 0))),
        ("DB", int(latest.get("connections_db", 0))),
        ("VNC", int(latest.get("connections_vnc", 0))),
        ("NET", int(latest.get("connections_net", 0))),
    ]

    cols = st.columns(len(metrics), gap="small")
    for col, (label, value) in zip(cols, metrics):
        with col:
            with st.container(border=True):
                st.metric(label, f"{value:,}")


def _time_format_for_window(minutes: int) -> str:
    """Return appropriate time axis format based on window size."""
    if minutes <= 360:
        return "%H:%M"
    if minutes <= 1440:
        return "%b %d %H:%M"
    return "%b %d"


def _render_timeline_chart(
    df: pd.DataFrame,
    metrics: list[tuple[str, str]],
    title: str,
    minutes: int,
    height: int = 280,
) -> None:
    """Render a multi-line time series chart with proper formatting."""
    if df.empty:
        st.info(f"No data for {title}")
        return

    time_format = _time_format_for_window(minutes)
    plot_cols = [m[0] for m in metrics if m[0] in df.columns]
    if not plot_cols:
        st.info(f"No data for {title}")
        return

    plot_df = df[["timestamp"] + plot_cols].copy()
    melted = plot_df.melt(id_vars=["timestamp"], var_name="metric", value_name="count")

    label_map = {m[0]: m[1] for m in metrics}
    melted["metric"] = melted["metric"].map(label_map)

    base = alt.Chart(melted).encode(
        x=alt.X(
            "timestamp:T",
            title=None,
            axis=alt.Axis(format=time_format, labelAngle=-45, grid=False),
        ),
        y=alt.Y(
            "count:Q",
            title=None,
            axis=alt.Axis(tickMinStep=1, grid=True, gridDash=[2, 2]),
        ),
        color=alt.Color(
            "metric:N",
            title=None,
            legend=alt.Legend(orient="top"),
        ),
        tooltip=[
            alt.Tooltip("timestamp:T", title="Time", format="%Y-%m-%d %H:%M"),
            alt.Tooltip("metric:N", title="Type"),
            alt.Tooltip("count:Q", title="Count", format=","),
        ],
    )

    chart = (base.mark_area(opacity=0.15) + base.mark_line(strokeWidth=2)).properties(height=height)
    st.altair_chart(chart, width="stretch")


def render() -> None:
    """Render the Performance and activity dashboard view."""
    cooldown_key = "dashboard_performance_activity_refresh_last_click"

    col_refresh, col_window = st.columns([1, 3])
    with col_refresh:
        refresh_clicked = st.button("Refresh", key="dashboard_performance_activity_refresh")
    with col_window:
        window_label = st.selectbox(
            "Time window",
            options=list(_WINDOW_OPTIONS.keys()),
            index=2,
            key="dashboard_performance_activity_window",
        )

    if refresh_clicked:
        if not should_bounce_refresh(cooldown_key):
            can_refresh, _ = get_refresh_cooldown_state(cooldown_key, cooldown_seconds=10)
            if can_refresh:
                set_refresh_warning_state(cooldown_key, visible=False)
                mark_refresh(cooldown_key)
                st.rerun()
            else:
                set_refresh_warning_state(cooldown_key, visible=True)
        else:
            set_refresh_warning_state(cooldown_key, visible=False)

    render_refresh_warning(cooldown_key, cooldown_seconds=10)

    minutes, bucket = _WINDOW_OPTIONS[window_label]

    try:
        df = _fetch_concurrent_stats(minutes, bucket)
    except Exception as exc:
        st.error(f"Failed to load concurrent stats: {exc}")
        return

    if df.empty:
        st.info(
            "No concurrent stats data available yet. "
            "Make sure 'concurrent' is in SYNC_SOURCES and the sync server is running."
        )
        render_data_age_caption(None)
        return

    # KPI cards — latest values
    _render_kpi_row(df)

    # Summary — average concurrent counts over the selected window
    st.subheader("Average (over selected window)")
    avg_metrics = [
        ("sessions", "Sessions"),
        ("connections_total", "Connections"),
        ("connections_ssh", "SSH"),
        ("connections_rdp", "RDP"),
        ("connections_web", "Web"),
        ("connections_db", "DB"),
        ("connections_vnc", "VNC"),
        ("connections_net", "NET"),
    ]
    avg_cols = st.columns(len(avg_metrics), gap="small")
    for col, (key, label) in zip(avg_cols, avg_metrics):
        with col:
            avg_val = df[key].mean() if key in df.columns else 0
            st.metric(label, f"{avg_val:.1f}")

    # Sessions & Total Connections
    st.subheader("Sessions & Connections")
    _render_timeline_chart(
        df,
        [("sessions", "Sessions"), ("connections_total", "Connections")],
        "Sessions & Connections",
        minutes,
    )

    # Connection type breakdown
    st.subheader("Connections by Type")
    type_metrics = [
        ("connections_ssh", "SSH"),
        ("connections_rdp", "RDP"),
        ("connections_db", "DB"),
        ("connections_web", "Web"),
        ("connections_vnc", "VNC"),
        ("connections_net", "NET"),
    ]
    active_types = [(k, label) for k, label in type_metrics if k in df.columns and df[k].sum() > 0]
    if active_types:
        _render_timeline_chart(df, active_types, "Connection Types", minutes)
    else:
        st.info("No active connections in this window.")

    # Connection mode breakdown
    st.subheader("Connections by Mode")
    mode_metrics = [
        ("connections_mode_ui", "UI"),
        ("connections_mode_mitm", "MITM"),
        ("connections_mode_other", "Other"),
    ]
    active_modes = [(k, label) for k, label in mode_metrics if k in df.columns and df[k].sum() > 0]
    if active_modes:
        _render_timeline_chart(df, active_modes, "Connection Modes", minutes)
    else:
        st.info("No connection mode data in this window.")

    render_data_age_caption(None)

    # Footer
    if not df.empty:
        last_ts = df["timestamp"].iloc[-1]
        points = len(df)
        st.caption(f"Showing {points} data points. Last: {last_ts.strftime('%Y-%m-%d %H:%M UTC')}")
