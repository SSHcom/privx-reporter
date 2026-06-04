import streamlit as st
import pandas as pd

import ui.constants as constants
from ui.services.config_service import get_report_config
from ui.services.page_bootstrap import setup_page
from ui.services.permissions import is_admin
from ui.services.report_service import can_access_report, get_all_report_files, get_user_report_files
from ui.services.session import keys
from ui.utils.string import normalize_name


def main() -> None:
    setup_page(page_title=constants.REPORT_FILES_PAGE_TITLE, show_sidebar=True)

    st.title("Report Files")

    permissions = st.session_state.get(keys.USER_PERMISSIONS)
    report_config = get_report_config()

    if is_admin():
        files_by_command = get_all_report_files(report_config, permissions)
    else:
        files_by_command = get_user_report_files(report_config, permissions)

    if not files_by_command:
        st.warning("No reports found.")
        st.stop()

    for primary, subcommands in sorted(files_by_command.items()):
        if primary not in report_config:
            continue

        st.header(normalize_name(primary))

        for subcommand, files in sorted(subcommands.items()):
            if subcommand not in report_config[primary].get("subcommands", {}):
                continue
            if not can_access_report(primary, subcommand):
                continue

            expand_key = keys.expand_files_key(f"{primary}_{subcommand}")
            expanded = st.session_state.get(expand_key, False)
            expander_label = f"{normalize_name(subcommand)} - {len(files)} file{'s' if len(files) != 1 else ''}"
            expander = st.expander(expander_label, expanded=expanded)

            with expander:
                sorted_files = sorted(files, key=lambda r: r.path.stat().st_mtime, reverse=True)
                all_paths = {str(rf.path) for rf in sorted_files}
                selection_state_key = f"selected_paths_{primary}_{subcommand}"
                stored_selected_paths = set(st.session_state.get(selection_state_key, []))
                selected_paths_for_render = stored_selected_paths & all_paths
                rows = []

                for rf in sorted_files:
                    rows.append(
                        {
                            "Delete": str(rf.path) in selected_paths_for_render,
                            "File Name": rf.path.name,
                            "Owner": rf.username or "-",
                            "Group": rf.group or "-",
                            "_path": str(rf.path),
                        }
                    )

                table_df = pd.DataFrame(rows)
                table_version_key = f"files_table_version_{primary}_{subcommand}"
                table_version = st.session_state.get(table_version_key, 0)
                table_key = f"files_table_{primary}_{subcommand}_{table_version}"
                widget_state = st.session_state.get(table_key, {})
                edited_rows = widget_state.get("edited_rows", {})
                if edited_rows:
                    # Apply pending widget edits before rendering to avoid losing first-click changes.
                    for row_index, row_changes in edited_rows.items():
                        if "Delete" not in row_changes:
                            continue
                        row_path = str(sorted_files[int(row_index)].path)
                        if row_changes["Delete"]:
                            selected_paths_for_render.add(row_path)
                        else:
                            selected_paths_for_render.discard(row_path)
                    table_df["Delete"] = table_df["_path"].isin(selected_paths_for_render)

                edited_df = st.data_editor(
                    table_df,
                    hide_index=True,
                    key=table_key,
                    use_container_width=True,
                    disabled=["File Name", "Owner", "Group", "_path"],
                    column_order=["Delete", "File Name", "Owner", "Group"],
                    column_config={
                        "Delete": st.column_config.CheckboxColumn(help="Select files to delete"),
                        "File Name": st.column_config.TextColumn(),
                        "Owner": st.column_config.TextColumn(),
                        "Group": st.column_config.TextColumn(),
                        "_path": None,
                    },
                )
                selected_paths = set(edited_df.loc[edited_df["Delete"], "_path"])
                st.session_state[selection_state_key] = sorted(selected_paths)
                selected_file = None
                if len(selected_paths) == 1:
                    selected_path = next(iter(selected_paths))
                    selected_file = next((rf for rf in sorted_files if str(rf.path) == selected_path), None)

                button_row_col, _ = st.columns([4, 6])
                with button_row_col:
                    select_all_col, delete_col, download_col, button_col = st.columns(4, gap="small")

                with select_all_col:
                    toggle_all_label = "Select All" if not selected_paths else "Clear All"
                    toggle_all_help = (
                        "Select all rows"
                        if not selected_paths
                        else f"Clear all selected rows ({len(selected_paths)} selected)"
                    )
                    if st.button(
                        label=toggle_all_label,
                        key=f"select_all_button_{primary}_{subcommand}",
                        help=toggle_all_help,
                        type="secondary",
                        disabled=len(sorted_files) == 0,
                    ):
                        if selected_paths:
                            st.session_state[selection_state_key] = []
                        else:
                            st.session_state[selection_state_key] = sorted(all_paths)
                        st.session_state[table_version_key] = table_version + 1
                        st.rerun()

                with delete_col:
                    delete_selection_key = f"delete_selection_{primary}_{subcommand}"

                    if st.button(
                        label="Delete",
                        key=delete_selection_key,
                        help=f"Delete selected report files ({len(selected_paths)} selected)",
                        type="primary",
                        disabled=not selected_paths,
                    ):
                        deleted_count = 0
                        failed_count = 0
                        for rf in sorted_files:
                            if str(rf.path) not in selected_paths:
                                continue
                            try:
                                rf.path.unlink()
                                deleted_count += 1
                            except OSError as exc:
                                failed_count += 1
                                st.error(f"Could not delete {rf.path.name}: {exc}")

                        if deleted_count > 0:
                            st.success(f"Deleted {deleted_count} files")
                        if failed_count > 0:
                            st.error(f"Failed to delete {failed_count} files")

                        if deleted_count > 0:
                            st.session_state[selection_state_key] = []
                            st.session_state[table_version_key] = table_version + 1
                            st.session_state[expand_key] = True
                            st.rerun()

                with download_col:
                    selected_mime = "application/octet-stream"
                    selected_name = "report.file"
                    selected_data = b""
                    download_help = "Select exactly one row to download"

                    if selected_file:
                        selected_name = selected_file.path.name
                        suffix = selected_file.path.suffix.lower()
                        if suffix == ".csv":
                            selected_mime = "text/csv"
                        elif suffix == ".json":
                            selected_mime = "application/json"
                        with open(selected_file.path, "rb") as f:
                            selected_data = f.read()
                        download_help = f"Download {selected_name}"

                    st.download_button(
                        label="Download",
                        data=selected_data,
                        file_name=selected_name,
                        mime=selected_mime,
                        key=f"download_selection_{primary}_{subcommand}",
                        help=download_help,
                        type="secondary",
                        disabled=selected_file is None,
                    )

                with button_col:
                    if st.button(label="New Report", key=f"create_{primary}_{subcommand}"):
                        st.session_state[keys.SELECTED_PRIMARY] = primary
                        st.session_state[keys.SELECTED_SUBCOMMAND] = subcommand
                        st.switch_page("pages/_2_Reports.py")


main()
