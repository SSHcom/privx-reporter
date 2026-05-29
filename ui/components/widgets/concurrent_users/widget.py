from __future__ import annotations

from typing import TYPE_CHECKING

import altair as alt
import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable


def _to_int(value: object, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def _normalize_protocol(value: str) -> str:
    if not value:
        return ""
    return value.split(":", 1)[0].upper()


def _join_unique(values: pd.Series, *, limit: int = 10) -> str:
    unique_values = [str(value).strip() for value in values if str(value).strip()]
    seen: set[str] = set()
    ordered: list[str] = []
    for value in unique_values:
        if value in seen:
            continue
        seen.add(value)
        ordered.append(value)
        if len(ordered) >= limit:
            break
    return ", ".join(ordered)


def _render_kpi_cards(concurrent_users: int, active_sessions: int) -> None:
    st.markdown(
        """
        <style>
        .cu-kpi-card {
            border: 1px solid rgba(120, 120, 120, 0.35);
            border-radius: 12px;
            padding: 0.8rem 0.9rem;
            background: linear-gradient(180deg, rgba(250, 250, 250, 0.06), rgba(250, 250, 250, 0.02));
            min-height: 96px;
        }
        .cu-kpi-label {
            font-size: 0.8rem;
            color: rgba(120, 120, 120, 0.95);
            text-transform: uppercase;
            letter-spacing: 0.04em;
            margin-bottom: 0.35rem;
        }
        .cu-kpi-value {
            font-size: 2rem;
            font-weight: 400;
            line-height: 1.05;
            color: inherit;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="medium")
    with col1:
        st.markdown(
            (
                '<div class="cu-kpi-card">'
                '<div class="cu-kpi-label">Concurrent Users</div>'
                f'<div class="cu-kpi-value">{concurrent_users:,}</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            (
                '<div class="cu-kpi-card">'
                '<div class="cu-kpi-label">Active Sessions</div>'
                f'<div class="cu-kpi-value">{active_sessions:,}</div>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )


def render(fetch_data: Callable[[], dict[str, object]]) -> None:
    data = fetch_data()

    st.subheader(str(data.get("label", "")))
    st.caption(str(data.get("description", "")))

    error_message = str(data.get("error", "")).strip()
    if error_message:
        st.error(error_message)
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    concurrent_users = _to_int(data.get("concurrent_users", 0))
    active_sessions = _to_int(data.get("active_sessions", 0))
    _render_kpi_cards(concurrent_users, active_sessions)

    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

    raw_protocol_counts = data.get("protocol_counts")
    protocol_counts = raw_protocol_counts if isinstance(raw_protocol_counts, dict) else {}
    normalized_protocol_counts = {str(key).strip().upper(): _to_int(value) for key, value in protocol_counts.items()}

    protocol_cols = st.columns(5)
    with protocol_cols[0]:
        st.metric("RDP", normalized_protocol_counts.get("RDP", 0))
    with protocol_cols[1]:
        st.metric("SSH", normalized_protocol_counts.get("SSH", 0))
    with protocol_cols[2]:
        st.metric("Web", normalized_protocol_counts.get("WEB", 0))
    with protocol_cols[3]:
        st.metric("DB", normalized_protocol_counts.get("DB", 0))
    with protocol_cols[4]:
        st.metric("VNC", normalized_protocol_counts.get("VNC", 0))

    raw_rows = data.get("session_timeline")
    rows = raw_rows if isinstance(raw_rows, list) else []
    if len(rows) == 0:
        st.info("No active PrivX session timeline available right now.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    chart_data = pd.DataFrame(rows)
    if "Sessions" not in chart_data.columns or "Time" not in chart_data.columns:
        st.info("No data available for chart.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    chart_data["Time"] = pd.to_datetime(chart_data["Time"], errors="coerce")
    session_series = pd.to_numeric(chart_data["Sessions"], errors="coerce")
    session_series = session_series.replace([float("inf"), float("-inf")], pd.NA)

    valid_mask = chart_data["Time"].notna() & session_series.notna()
    if not bool(valid_mask.any()):
        st.info("No finite values available for chart.")
        st.caption(f"Last Updated: {data.get('updated_at', '-')}")
        return

    plot_data = chart_data.loc[valid_mask, ["Time"]].copy()
    plot_data["Sessions"] = session_series.loc[valid_mask].astype(int)

    user_column = None
    for candidate in ("Users", "User"):
        if candidate in chart_data.columns:
            user_column = candidate
            break

    if user_column is not None:
        plot_data["User"] = chart_data.loc[valid_mask, user_column].fillna("").astype(str)
    else:
        plot_data["User"] = ""

    protocol_column = None
    for candidate in ("Protocol", "Type", "Session Type"):
        if candidate in chart_data.columns:
            protocol_column = candidate
            break

    has_protocol_values = False
    if protocol_column is not None:
        protocol_values = chart_data.loc[valid_mask, protocol_column].fillna("").astype(str).apply(_normalize_protocol)
        plot_data["Protocol"] = protocol_values
        has_protocol_values = bool(protocol_values.str.strip().ne("").any())
    else:
        plot_data["Protocol"] = ""

    account_column = None
    for candidate in ("Target Account", "TargetAccount", "Account"):
        if candidate in chart_data.columns:
            account_column = candidate
            break

    has_account_values = False
    if account_column is not None:
        account_values = chart_data.loc[valid_mask, account_column].fillna("").astype(str)
        plot_data["Target Account"] = account_values
        has_account_values = bool(account_values.str.strip().ne("").any())
    else:
        plot_data["Target Account"] = ""

    plot_data = plot_data.sort_values("Time")

    bucket_minutes = st.selectbox(
        "Timeline bucket",
        options=[1, 5, 15, 30, 60],
        index=0,
        format_func=lambda value: f"{value} min",
        key="concurrent_users_timeline_bucket_minutes",
    )

    if int(bucket_minutes) > 1:
        frequency = f"{int(bucket_minutes)}min"
        plot_data["Time"] = plot_data["Time"].dt.floor(frequency)
        group_columns: dict[str, str | tuple[str, callable]] = {"Sessions": "sum"}
        group_columns["User"] = lambda values: _join_unique(values, limit=10)
        if has_protocol_values:
            group_columns["Protocol"] = lambda values: _join_unique(values, limit=5)
        if has_account_values:
            group_columns["Target Account"] = lambda values: _join_unique(values, limit=5)
        plot_data = plot_data.groupby("Time", as_index=False).agg(group_columns).sort_values("Time")

    tooltips: list[alt.Tooltip] = [
        alt.Tooltip("Time:T", title="Time"),
        alt.Tooltip("Sessions:Q", title="Sessions"),
        alt.Tooltip("User:N", title="User"),
    ]
    if has_protocol_values:
        tooltips.append(alt.Tooltip("Protocol:N", title="Protocol"))
    if has_account_values:
        tooltips.append(alt.Tooltip("Target Account:N", title="Target Account"))

    st.caption(f"Concurrent session timeline ({int(bucket_minutes)}-minute buckets)")
    line_chart = (
        alt.Chart(plot_data)
        .mark_line(point=True)
        .encode(
            x=alt.X("Time:T", title="Time"),
            y=alt.Y("Sessions:Q", title="Sessions"),
            tooltip=tooltips,
        )
        .properties(height=280)
    )
    st.altair_chart(line_chart, width="stretch")

    with st.expander("Timeline details"):
        table_columns = ["Time", "Sessions", "User"]
        if has_protocol_values:
            table_columns.append("Protocol")
        if has_account_values:
            table_columns.append("Target Account")

        table_data = plot_data[table_columns].copy()
        st.dataframe(table_data, width="stretch")

    raw_top_user_rows = data.get("top_users")
    top_user_rows = raw_top_user_rows if isinstance(raw_top_user_rows, list) else []
    if len(top_user_rows) > 0:
        top_user_data = pd.DataFrame(top_user_rows)
        if "Sessions" in top_user_data.columns and "User" in top_user_data.columns:
            top_user_series = pd.to_numeric(top_user_data["Sessions"], errors="coerce")
            top_user_series = top_user_series.replace([float("inf"), float("-inf")], pd.NA)

            valid_top_user_mask = top_user_series.notna()
            if bool(valid_top_user_mask.any()):
                top_plot_data = top_user_data.loc[valid_top_user_mask, ["User"]].copy()
                top_plot_data["Sessions"] = top_user_series.loc[valid_top_user_mask].astype(int).to_numpy()
                top_plot_data = top_plot_data.set_index("User").sort_values(
                    "Sessions",
                    ascending=False,
                )

                st.caption("Top users by active session count")
                st.bar_chart(top_plot_data["Sessions"], width="stretch", height=240)

    st.caption(f"Last Updated: {data.get('updated_at', '-')}")
