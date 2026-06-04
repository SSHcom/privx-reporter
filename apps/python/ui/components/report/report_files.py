import re

import streamlit as st

from ui.services.report_service import get_user_output_dir
from ui.services.session import keys


def render_report_files(primary: str, subcommand: str, subcommand_key: str) -> None:
    """Render an expander listing generated files for the given report type."""

    report_out_dir = get_user_output_dir()
    file_pattern = re.compile(
        rf"^{re.escape(primary)}\.{re.escape(subcommand)}(\.[^.]+)*\.\d{{8}}_\d{{6}}\.(csv|json)$"
    )

    # Check if we should expand the expander (report just created)
    expand_key = keys.expand_files_key(subcommand_key)
    should_expand = st.session_state.get(expand_key, False)

    # Clear the flag after reading it
    if expand_key in st.session_state:
        del st.session_state[expand_key]

    with st.expander("Files generated for this report", expanded=should_expand):
        if not report_out_dir.exists():
            st.info("No reports found.")
            return

        matching_files = sorted(
            [path for path in report_out_dir.iterdir() if path.is_file() and file_pattern.match(path.name)],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        if not matching_files:
            st.info("No files have been generated for this report.")
            return

        for file_path in matching_files:
            suffix = file_path.suffix.lower()
            if suffix == ".csv":
                mime_type = "text/csv"
            elif suffix == ".json":
                mime_type = "application/json"
            else:
                mime_type = "application/octet-stream"

            download_col, delete_col = st.columns([5, 3])

            with download_col, open(file_path, "rb") as f:
                st.download_button(
                    label=file_path.name,
                    data=f,
                    file_name=file_path.name,
                    mime=mime_type,
                    key=f"download_{file_path.name}",
                    icon="📄",
                )

            with delete_col:
                if st.button(
                    label="Delete",
                    key=f"delete_{file_path.name}",
                    help=f"Delete {file_path.name}",
                    type="tertiary",
                ):
                    try:
                        file_path.unlink()
                        st.session_state[expand_key] = True
                        st.rerun()
                    except OSError as exc:
                        st.error(f"Could not delete {file_path.name}: {exc}")
