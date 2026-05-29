from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from ui.services import report_view_resolver
from ui.services.session import keys


def _make_streamlit_stub() -> SimpleNamespace:
    return SimpleNamespace(session_state={})


@pytest.mark.unit
def test_get_resolved_report_views_filters_non_admin_and_prunes_empty_nodes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st_stub = _make_streamlit_stub()
    monkeypatch.setattr(report_view_resolver, "st", st_stub)
    monkeypatch.setattr(report_view_resolver, "is_admin", lambda: False)
    monkeypatch.setattr(
        report_view_resolver,
        "get_report_config",
        lambda: {
            "events": {"subcommands": {"accounts": {}, "role_members": {}}},
            "access": {"subcommands": {"hosts": {}}},
        },
    )
    monkeypatch.setattr(
        report_view_resolver.report_service,
        "get_viewable_reports",
        lambda: [("events", "accounts")],
    )
    monkeypatch.setattr(
        report_view_resolver,
        "list_alt_group_views",
        lambda: [{"id": 1, "name": "Operations"}, {"id": 2, "name": "Empty"}],
    )

    def _groups_for_view(view_id: int) -> list[dict[str, str]]:
        if view_id == 1:
            return [
                {
                    "group_name": "Ops",
                    "report_group_name": "events",
                    "report_name": "accounts",
                },
                {
                    "group_name": "Ops",
                    "report_group_name": "events",
                    "report_name": "role_members",
                },
                {
                    "group_name": "Restricted",
                    "report_group_name": "access",
                    "report_name": "hosts",
                },
            ]
        return [
            {
                "group_name": "Nobody",
                "report_group_name": "access",
                "report_name": "hosts",
            }
        ]

    monkeypatch.setattr(report_view_resolver, "get_groups_for_view", _groups_for_view)

    resolved = report_view_resolver.get_resolved_report_views()

    assert resolved == [
        {
            "id": None,
            "name": "Default",
            "groups": [
                {
                    "name": "events",
                    "reports": [{"primary": "events", "subcommand": "accounts"}],
                }
            ],
        },
        {
            "id": 1,
            "name": "Operations",
            "groups": [
                {
                    "name": "Ops",
                    "reports": [{"primary": "events", "subcommand": "accounts"}],
                }
            ],
        },
    ]


@pytest.mark.unit
def test_get_resolved_report_views_keeps_all_reports_for_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    st_stub = _make_streamlit_stub()
    monkeypatch.setattr(report_view_resolver, "st", st_stub)
    monkeypatch.setattr(report_view_resolver, "is_admin", lambda: True)
    monkeypatch.setattr(
        report_view_resolver,
        "get_report_config",
        lambda: {
            "events": {"subcommands": {"accounts": {}, "role_members": {}}},
        },
    )
    monkeypatch.setattr(report_view_resolver.report_service, "get_viewable_reports", lambda: [])
    monkeypatch.setattr(
        report_view_resolver,
        "list_alt_group_views",
        lambda: [{"id": 7, "name": "Admin View"}],
    )
    monkeypatch.setattr(
        report_view_resolver,
        "get_groups_for_view",
        lambda _view_id: [
            {
                "group_name": "Everything",
                "report_group_name": "events",
                "report_name": "accounts",
            },
            {
                "group_name": "Everything",
                "report_group_name": "events",
                "report_name": "role_members",
            },
        ],
    )

    resolved = report_view_resolver.get_resolved_report_views()

    assert len(resolved) == 2
    assert resolved[0]["name"] == "Default"
    assert len(resolved[0]["groups"][0]["reports"]) == 2
    assert resolved[1]["name"] == "Admin View"
    assert len(resolved[1]["groups"][0]["reports"]) == 2


@pytest.mark.unit
def test_get_resolved_report_views_uses_session_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    st_stub = _make_streamlit_stub()
    monkeypatch.setattr(report_view_resolver, "st", st_stub)
    monkeypatch.setattr(report_view_resolver, "is_admin", lambda: False)

    get_report_config = MagicMock(return_value={"events": {"subcommands": {"accounts": {}}}})
    list_alt_group_views = MagicMock(return_value=[])
    get_viewable_reports = MagicMock(return_value=[("events", "accounts")])

    monkeypatch.setattr(report_view_resolver, "get_report_config", get_report_config)
    monkeypatch.setattr(report_view_resolver, "list_alt_group_views", list_alt_group_views)
    monkeypatch.setattr(report_view_resolver.report_service, "get_viewable_reports", get_viewable_reports)

    first = report_view_resolver.get_resolved_report_views()
    second = report_view_resolver.get_resolved_report_views()

    assert first == second
    get_report_config.assert_called_once()
    list_alt_group_views.assert_called_once()
    get_viewable_reports.assert_called_once()


@pytest.mark.unit
def test_invalidate_report_view_cache_clears_session_value(monkeypatch: pytest.MonkeyPatch) -> None:
    st_stub = _make_streamlit_stub()
    st_stub.session_state[keys.RESOLVED_REPORT_VIEWS] = [{"name": "Default", "id": None, "groups": []}]
    monkeypatch.setattr(report_view_resolver, "st", st_stub)

    report_view_resolver.invalidate_report_view_cache()

    assert st_stub.session_state[keys.RESOLVED_REPORT_VIEWS] is None
