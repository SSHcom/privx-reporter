from pathlib import Path

APP_TITLE = "PrivX Reporter"
APP_LAYOUT = "wide"
APP_FAVICON = str(Path(__file__).resolve().parent / "components" / "favicon.png")
SIDEBAR_THEME_COLOR = "#072433"
SIDEBAR_SELECTOR_COLOR = "#0b3044"
SIDEBAR_SELECTOR_HOVER_COLOR = "rgba(255, 255, 255, 0.15)"
SIDEBAR_TEXT_COLOR = "#ffffff"
SIDEBAR_SELECTOR_BORDER_COLOR = "rgba(255, 255, 255, 0.2)"

HOME_PAGE_TITLE = "PrivX Reporter - Home"
HOME_PAGE_DESCRIPTION = "Select a report from the sidebar to view details"

REPORTS_PAGE_TITLE = "PrivX Reporter - Reports"
REPORTS_PAGE_DESCRIPTION = "No report selected. Please select a report from the sidebar."

REPORT_FILES_PAGE_TITLE = "PrivX Reporter - Report Files"

USERS_PAGE_TITLE = "PrivX Reporter - Users"
USER_PROFILE_PAGE_TITLE = "PrivX Reporter - User Profile"
USER_GROUPS_PAGE_TITLE = "PrivX Reporter - User Groups"
REPORT_GROUPS_PAGE_TITLE = "PrivX Reporter - Report Groups"


PAGE_STYLE = (
    """
  <style>
    [data-testid="stAppDeployButton"] {display:none !important;}
    [data-testid="stAppViewContainer"] {
      color: %(theme_color)s;
    }
    [data-testid="stMainMenu"] {display:none !important;}
    [data-testid="stSidebarNav"] { display: none !important; }
    [data-testid="stSidebarContent"] {
      margin-top: -60px;
    }
    [data-testid="stSidebarCollapseButton"] {
      margin-top: 100px;
    }
    [data-testid="stMain"] {
      margin-top: -50px;
    }
    /* Keep help icons next to widget labels instead of right edge. */
    label[data-testid="stWidgetLabel"] {
      display: inline-flex !important;
      align-items: center !important;
      justify-content: flex-start !important;
      gap: 0.35rem !important;
      width: fit-content !important;
    }
    label[data-testid="stWidgetLabel"] > div:has(.stTooltipIcon) {
      display: inline-flex !important;
      flex: 0 0 auto !important;
      width: auto !important;
      min-width: 0 !important;
      margin-left: 0 !important;
    }
    label[data-testid="stWidgetLabel"] [data-testid="stTooltipHoverTarget"] {
      justify-content: flex-start !important;
    }
    button {
      padding-top: -14px;
      padding-bottom: -14px;
    }
    /* Target only the report view picker (key="report_group_view_picker"). */
    .st-key-report_group_view_picker div[data-baseweb="select"] > div {
      background-color: %(selector_color)s !important;
      border: 1px solid %(selector_border_color)s !important;
    }
    .st-key-report_group_view_picker div[data-baseweb="select"] > div:hover,
    .st-key-report_group_view_picker div[data-baseweb="select"] > div:focus-within,
    .st-key-report_group_view_picker div[data-baseweb="select"]:has(
      input[role="combobox"][aria-expanded="true"]
    ) > div {
      background-color: %(selector_hover_color)s !important;
      border-color: %(selector_border_color)s !important;
      box-shadow: none !important;
    }
    .st-key-report_group_view_picker div[data-baseweb="select"] div[value] {
      color: %(text_color)s !important;
    }
    .st-key-report_group_view_picker div[data-baseweb="select"] svg {
      fill: %(text_color)s !important;
      color: %(text_color)s !important;
    }
    .st-key-report_group_view_picker div[data-baseweb="select"] input[role="combobox"] {
      color: %(text_color)s !important;
      caret-color: %(text_color)s !important;
      background-color: transparent !important;
    }
    /* Style the portal listbox only while this picker is open. */
    body:has(.st-key-report_group_view_picker input[role="combobox"][aria-expanded="true"]) [role="listbox"] {
      background-color: %(selector_color)s !important;
      color: %(text_color)s !important;
      border: 1px solid %(selector_border_color)s !important;
    }
    body:has(.st-key-report_group_view_picker input[role="combobox"][aria-expanded="true"]) [role="option"] {
      background-color: %(selector_color)s !important;
      color: %(text_color)s !important;
    }
    body:has(
      .st-key-report_group_view_picker input[role="combobox"][aria-expanded="true"]
    ) [role="option"][aria-selected="true"],
    body:has(
      .st-key-report_group_view_picker input[role="combobox"][aria-expanded="true"]
    ) [role="option"]:hover {
      background-color: %(theme_color)s !important;
      color: %(text_color)s !important;
    }
  </style>
""".replace("%(theme_color)s", SIDEBAR_THEME_COLOR)
    .replace("%(selector_color)s", SIDEBAR_SELECTOR_COLOR)
    .replace("%(selector_hover_color)s", SIDEBAR_SELECTOR_HOVER_COLOR)
    .replace("%(selector_border_color)s", SIDEBAR_SELECTOR_BORDER_COLOR)
    .replace("%(text_color)s", SIDEBAR_TEXT_COLOR)
)
