"""Render directory source counts as a table."""

from __future__ import annotations

from html import escape
from typing import TYPE_CHECKING

import pandas as pd
import streamlit as st

if TYPE_CHECKING:
    from collections.abc import Callable

# Friendly labels for connection types
_TYPE_LABELS = {
    "AD": "Active Directory",
    "LDAP": "LDAP",
    "MICROSOFTGRAPH": "Microsoft Graph",
    "OIDC": "OpenID Connect",
    "SCIM": "SCIM",
    "AWS": "AWS",
    "AZURE": "Azure",
    "GCP": "Google Cloud",
    "GOOGLE": "Google Workspace",
    "VMWARE": "VMware",
    "OCI": "Oracle Cloud",
    "OPENSTACK": "OpenStack",
    "PROXMOX": "Proxmox",
}


def _format_count(value: int | None, processing: bool) -> str:
    if value is None:
        return "-"
    text = f"{value:,}"
    if processing:
        text += " ⟳"
    return text


def render(fetch_data: Callable[[], dict[str, object]]) -> None:
    """Render directory sources table."""
    data = fetch_data()

    error = str(data.get("error", "")).strip()
    if error:
        st.error(error)
        return

    directories = data.get("directories", [])
    if not directories:
        st.info("No external directories configured (Local users, Local hosts, and API clients are shown above).")
        return

    rows = []
    for d in directories:
        processing = d.get("processing", False)
        rows.append(
            {
                "Name": d.get("name", ""),
                "Type": _TYPE_LABELS.get(d.get("type", ""), d.get("type", "")),
                "Users": _format_count(d.get("users"), processing),
                "Hosts": _format_count(d.get("hosts"), processing),
            }
        )

    df = pd.DataFrame(rows)

    # Build HTML table for full style control
    header_html = "".join(
        f'<th style="font-size:1.15rem; font-weight:800; padding:0.6rem 1rem; text-align:left;">{col}</th>'
        for col in df.columns
    )
    rows_html = ""
    for _, row in df.iterrows():
        cells = "".join(
            f'<td style="font-size:1.05rem; padding:0.5rem 1rem;">{escape(str(row[col]))}</td>' for col in df.columns
        )
        rows_html += f"<tr>{cells}</tr>"

    st.markdown(
        f"""
        <table style="width:100%; border-collapse:collapse;">
            <thead><tr style="border-bottom:2px solid rgba(100,100,100,0.3);">{header_html}</tr></thead>
            <tbody>{rows_html}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )

    st.caption(f"⟳ = directory refresh in progress. Last updated: {data.get('updated_at', '-')}")
