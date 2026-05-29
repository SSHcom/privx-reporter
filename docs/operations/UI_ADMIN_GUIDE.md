# UI Operational Guide

This operational guide describes day-to-day operation of the Reporter UI, with emphasis on authentication and administration workflows.

For implementation structure and report execution flow, see [UI high-level architecture](../development/guide/ui_hl_architecture.md) and [UI report execution](../development/guide/ui_report_execution.md).

## UI Access and Authentication

### Start and Access the UI

1. Start the UI service (for local development: `bin/serve_ui`).
2. Open `http://localhost:8501`.
3. Sign in with a UI account from the admin database.

### First Login on a Fresh Admin Database

When the admin database is new, the UI bootstraps an `admin` account automatically at startup.

- Username: `admin`
- Initial password: `UI_TMP_ADMIN_PASSWORD`

Operational requirement:

- Change the `admin` account password immediately after first successful login.
- Treat `UI_TMP_ADMIN_PASSWORD` as bootstrap-only; do not keep it as a long-lived credential.

### Login Behavior

- Login requires both username and password.
- Unknown username and wrong password both return the same error (`Invalid username or password`).
- Authentication supports local username/password and optional OIDC providers based on `UI_AUTH_MODE`.
- If already authenticated, opening the login route redirects to Home.

For OIDC-based UI login setup and troubleshooting, see [OIDC UI Authentication Operational Guide](OIDC_UI_AUTH_GUIDE.md).

### Session Behavior

- UI authentication is session-based.
- Session lifetime is controlled by `UI_JWT_EXPIRATION_MINUTES` (inactivity timeout).
- `UI_JWT_EXPIRATION_MINUTES` is a sliding idle timeout: active authenticated requests refresh the timeout window.
- Cookie lifetime is controlled by `UI_COOKIE_MAX_AGE_MINUTES`.
- Session Debug panel visibility is controlled by `UI_ENABLE_SESSION_DEBUG` (default disabled).
- Active sessions are extended automatically as users continue interacting with the UI.
- Logout ends the server-side session and clears the browser session cookie.

Operational notes:

- If users are unexpectedly redirected to login, verify session-related environment variables first.
- If environment values are changed, restart the UI service.

### Cookie Mismatch Warnings (Operational Note)

During long-running Streamlit sessions, the app can continue using a cached cookie view after browser cookie expiry/rotation. In that state, logs may show cookie mismatch warnings until the UI service is restarted.

This is expected and acceptable:

- Cookie mismatch warnings alone do not indicate a broken or insecure login state.
- The cookie primarily protects/anchors session continuity between requests; a page refresh does not necessarily require immediate re-login.
- User authentication still happens against the admin database at login time.

## Access Group Filtering for Host Reports

### What This Filtering Means

When a non-admin user runs host-related reports in the Reporter UI, results are automatically limited to hosts (and host-based connection records) that belong to the access groups allowed for that user's **User Group**.

In practice, this means:

- Users only see host information from approved access groups.
- Hosts outside those access groups are hidden from report output.
- Some reports may return fewer rows than expected, or no rows, if nothing matches the allowed groups.

This filtering is applied server-side when the report is generated.

### Which Reports Apply It

The following reports apply User Group access-group filtering when returning host information:

- **access**
    - `account`
    - `account-restrictions`
    - `hosts`
    - `role-map`
    - `query`
- **connections**
    - `details`
    - `query`
    - `query-db`
- **list**
    - `list hosts`

### How It Is Configured in User Groups

In the UI:

1. Open **Admin -> User Groups**.
2. Select a user group.
3. In **Access group filters**, enter a CSV list of allowed access group names.
    - Note: newly created non-admin user groups include **Default** automatically.
4. Click **Update**.

Important behavior:

- Matching is done by **access group name** (not ID).
- Name matching is case-insensitive, and extra spaces are ignored.
- Unknown names cause a permission error for filtered reports.
- Empty or invalid configuration means no host data can be returned for filtered reports.

### Notes for Admins

- This is separate from report visibility. A user group may be allowed to open a report, but still see only hosts from its configured access groups.
- Access group filtering is only relevant for non-admin UI access to reports. No filtering is applied when using the CLI.

## Admin Area Overview

The **Administration** section appears in the sidebar only for users in the admin group.

- **Dashboard**: available only to the `admin` account.
- **Users**: create users and open user profiles for updates.
- **User Groups**: control report access and access-group filters per group.
- **Report Groups**: create alternate report view groupings for sidebar navigation.

## User Administration

### Create Users

In **Admin -> Users -> Create User**:

- Required fields: Username, Display Name, Password, User Group.
- Username must be unique.
- For non-superadmin admins, the `admin` group is not assignable.
- `Can edit profile` controls whether a user can change their own display name/password.
  - If a user is created in the `admin` group, profile editing is always enabled.

### Edit User Profile

In **Admin -> Users -> Edit** (or **Account -> My Profile**):

- Update Display Name.
- Update Password.
- (Admin only) Move user to another user group.
- (Admin only) Toggle profile edit permission for non-admin-group users.

Permission constraints:

- Non-admin users can edit only their own profile (and only when profile editing is enabled).
- Non-superadmin admins cannot modify the `admin` account.
- Admin users cannot change their own user group.

### Delete Users

Delete is available in a profile page under **Delete User**.

Rules:

- Users cannot delete their own account.
- Only the `admin` account can delete users in the admin group.
- Deletion is confirmed in a modal dialog.

## User Group Administration

In **Admin -> User Groups**:

- Create new user groups.
- Assign which reports are visible to each user group.
- Maintain **Access group filters** (CSV) for host-based report filtering.

Important behavior:

- The `admin` group is protected:
  - It keeps full report access.
  - It is not managed through normal report-membership toggles.
- User groups cannot be deleted while users are still assigned to them.
- Updating report membership applies immediately for subsequent page loads/report access checks.

## Report Group Views (Navigation Grouping)

In **Admin -> Report Groups** you can build alternate sidebar groupings for reports.

- Create a named report-group view.
- Add one or more reports under a custom group label.
- Remove assignments or delete an entire view.

Use this to present reports by operational function (for example, SOC, audit, operations) without changing underlying report permissions.

## Authorization Model (Operational)

- Authentication answers: "Who is the user?"
- Authorization answers: "What can the user open and run?"

In practice:

- Non-admin users can only open reports assigned to their user group.
- Admin-group users can access all reports.
- A user may have report access but still receive reduced/no host rows due to access-group filtering.

## Auth and Admin Troubleshooting

### Invalid Login for Known User

Check:

- Correct username spelling.
- Password reset need (use **Admin -> Users -> Edit -> Change Password**).
- UI connected to the expected admin database instance.

### Session Expires Too Quickly or Lasts Too Long

Check:

- `UI_JWT_EXPIRATION_MINUTES`
- `UI_COOKIE_MAX_AGE_MINUTES`
- UI service restart after environment changes

### Admin Controls Not Visible

Check:

- User is assigned to admin user group.
- User logged out and back in after group changes.
- Profile is not being viewed with stale session credentials.

### Cannot Delete a User Group

Likely cause:

- One or more users are still assigned to that group.

Action:

- Reassign or delete those users first, then delete the group.
