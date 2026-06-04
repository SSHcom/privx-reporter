"""Dashboard view modules."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable


def get_refresh_cooldown_state(state_key: str, cooldown_seconds: int) -> tuple[bool, int]:
    """Return refresh availability and remaining cooldown time."""
    last_refresh = float(st.session_state.get(state_key, 0.0))
    elapsed = time.monotonic() - last_refresh
    remaining_seconds = max(0, int((cooldown_seconds - elapsed) + 0.999))
    if remaining_seconds > 0:
        return False, remaining_seconds
    return True, 0


def mark_refresh(state_key: str) -> None:
    """Record refresh trigger time for cooldown tracking."""
    st.session_state[state_key] = time.monotonic()


def set_refresh_warning_state(state_key: str, *, visible: bool) -> None:
    """Set whether refresh cooldown warning is visible for a dashboard."""
    st.session_state[f"{state_key}_warning_visible"] = bool(visible)
    counter_key = f"{state_key}_warning_count"
    if visible:
        st.session_state[counter_key] = int(st.session_state.get(counter_key, 0)) + 1
    else:
        st.session_state[counter_key] = 0


def set_data_operation_warning_state(state_key: str, *, visible: bool) -> None:
    """Set whether data-operation-in-progress warning is visible for a dashboard."""
    st.session_state[f"{state_key}_operation_warning_visible"] = bool(visible)
    counter_key = f"{state_key}_operation_warning_count"
    if visible:
        st.session_state[counter_key] = int(st.session_state.get(counter_key, 0)) + 1
    else:
        st.session_state[counter_key] = 0


def is_data_operation_in_progress() -> bool:
    """Return True when DataFetchManager is handling a fetch operation."""
    from ui.services.data_fetch_manager import get_data_fetch_manager

    return get_data_fetch_manager().is_fetch_in_progress()


def get_loading_view_message() -> str | None:
    """Return a dashboard loading message that includes the active view when known."""
    from ui.services.data_fetch_manager import get_data_fetch_manager

    manager = get_data_fetch_manager()
    if not manager.is_fetch_in_progress():
        return None

    active_label = manager.get_active_fetch_view_label()
    if active_label:
        return f'"{active_label}" view is currently loading.'
    return "This dashboard view is currently loading."


def render_data_age_caption(data_age_seconds: float | None) -> None:
    """Render data age caption with optional active loading status."""
    from ui.services.data_fetch_manager import format_data_age

    loading_view_message = get_loading_view_message()
    if data_age_seconds is None:
        if loading_view_message:
            st.caption(loading_view_message)
        return

    caption_text = f"Data age: {format_data_age(data_age_seconds)}"
    if loading_view_message:
        caption_text = f"{caption_text} | {loading_view_message}"
    st.caption(caption_text)


def should_bounce_refresh(state_key: str) -> bool:
    """Return True when refresh should be blocked due to active data operation."""
    if not is_data_operation_in_progress():
        return False

    set_data_operation_warning_state(state_key, visible=True)
    set_refresh_warning_state(state_key, visible=False)
    return True


def render_refresh_warning(
    state_key: str,
    cooldown_seconds: int,
    *,
    data_operation_in_progress: bool | None = None,
) -> None:
    """Render refresh cooldown warning on normal page reruns only."""

    def _counter_suffix(counter: int) -> str:
        if counter <= 1:
            return ""
        return f" ({counter})"

    if data_operation_in_progress is None:
        data_operation_in_progress = is_data_operation_in_progress()

    operation_warning_key = f"{state_key}_operation_warning_visible"
    operation_warning_count_key = f"{state_key}_operation_warning_count"
    if bool(st.session_state.get(operation_warning_key, False)):
        if data_operation_in_progress is False:
            set_data_operation_warning_state(state_key, visible=False)
        else:
            operation_warning_count = int(st.session_state.get(operation_warning_count_key, 1))
            st.warning(
                f"Data operation is already in progress. Please try again later."
                f"{_counter_suffix(operation_warning_count)}"
            )
            return

    warning_key = f"{state_key}_warning_visible"
    warning_count_key = f"{state_key}_warning_count"
    if not bool(st.session_state.get(warning_key, False)):
        return

    can_refresh, remaining_seconds = get_refresh_cooldown_state(state_key, cooldown_seconds)
    if can_refresh:
        set_refresh_warning_state(state_key, visible=False)
        return

    warning_count = int(st.session_state.get(warning_count_key, 1))
    st.warning(f"Refresh is rate-limited. Try again in {remaining_seconds}s.{_counter_suffix(warning_count)}")


def render_widget_rows(widgets: list[Callable[[], None]], max_per_row: int = 2) -> None:
    """Render widgets in rows with a fixed maximum columns per row."""
    if max_per_row <= 0:
        raise ValueError("max_per_row must be greater than 0")

    for row_start in range(0, len(widgets), max_per_row):
        row_widgets = widgets[row_start : row_start + max_per_row]
        columns = st.columns(max_per_row, gap="large")
        for column, widget in zip(columns, row_widgets, strict=False):
            with column:
                with st.container(border=True):
                    widget()


def render_realtime_widget(
    widget: Callable[[], None],
    *,
    auto_refresh_enabled: bool,
    refresh_seconds: int = 30,
) -> None:
    """Render widget with optional auto-refresh; default remains no auto-refresh."""
    if not auto_refresh_enabled:
        widget()
        return

    @st.fragment(run_every=refresh_seconds)
    def _render() -> None:
        widget()

    _render()
