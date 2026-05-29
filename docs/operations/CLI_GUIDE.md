# CLI Operational Guide

This operational guide documents reporter CLI commands, options, output behavior, and usage patterns.

#### Note:
Commands in this guide assume Reporter binaries are available in your PATH. If you run directly from a cloned repository, use `bin/report` instead of `report`.

## Connections

### Query command

Command: `report connections query [options] [--to-json|--to-stdout|--fields <csv>]`

Example filename: `connections-query.20260123_125421.csv`

### Example output

| Username                 | Target Host Address | Target Host Account | Created                     | Connected                   | Disconnected                | Duration | Status       | Type |
| ------------------------ | ------------------- | ------------------- | --------------------------- | --------------------------- | --------------------------- | -------- | ------------ | ---- |
| alex.rivera@example.test | 198.51.100.44:22    | opsuser             | 2026-01-05T07:51:37.248072Z | 2026-01-05T07:51:37.222085Z | 2026-01-05T07:52:27.258636Z | 50       | DISCONNECTED | SSH  |
| dana.kim@example.test    | 203.0.113.25:22     | sysadmin            | 2026-01-07T07:19:55.723468Z | 2026-01-07T07:19:55.713156Z | 2026-01-07T07:20:15.480686Z | 20       | DISCONNECTED | SSH  |

### Options

**Note:** If omitted, `--from-date` and `--to-date` default to a 7-day range.

| Option (example)                              |                                                                                    |
| --------------------------------------------- | ---------------------------------------------------------------------------------- |
| `--from-date 2026-01-01 --to-date 2026-01-10` | Date range in YYYY-MM-DD or ISO8601 format (defaults to last 7 days when omitted). |
| `--target-account sysadmin`                   | Filter by target host account                                                      |
| `--user-name dana.kim@example.test`           | Filter by user name                                                                |
| `--target-address 203.0.113.25`               | Filter by target host address                                                      |
| `--connection-type SSH`                       | Filter by connection type (for example SSH, RDP, API)                              |

### Details command

Example command: `report connections details --connection-id 11111111-2222-4333-8444-555555555555`

Example filename: `connection-11111111-2222-4333-8444-555555555555.20260123_125642.csv`

Output: Same as the `query` command but with a single line

| Option (example)       |                                                          |
| ---------------------- | -------------------------------------------------------- |
| `--connection-id <id>` | Connection ID (required)                                 |
| `--json-source`        | Output as original JSON. Overrides '--to-json' CLI flag. |

## Access

### Role map

Command: `report access role-map --target-address <address>`

Example filename: `role-map.20260123_130527.csv`

Example output:

| Role Name   | User Name                                                                             | Target Hosts                    | Target Accounts |
| ----------- | ------------------------------------------------------------------------------------- | ------------------------------- | --------------- |
| linux-admin | eli.hart@example.test                                                                 | ip-198-51-100-120.test.internal | rockyuser       |
| privx-admin | u-alpha,u-bravo,u-charlie,u-delta,u-echo,admin-demo                                   | 192.0.2.11                      | sandbox         |
| privx-admin | u-alpha,u-bravo,u-charlie,u-delta,u-echo,admin-demo,sec-admin,203.0.113.200,AdminUser | 203.0.113.200                   | AdminUser       |

| Option (example)              |                                 |
| ----------------------------- | ------------------------------- |
| `--target-address 192.0.2.11` | Target host address or hostname |

### Account access

Example command: `report access account --target-address 203.0.113.200 --target-account AdminUser`

Example filename: `account.20260123_130606.csv`

Example output:

| User Name | Role Name   | Target Host   | Target Account |
| --------- | ----------- | ------------- | -------------- |
| u-alpha   | privx-admin | 203.0.113.200 | AdminUser      |
| u-bravo   | privx-admin | 203.0.113.200 | AdminUser      |
| u-charlie | privx-admin | 203.0.113.200 | AdminUser      |

| Option (example)                 |                                    |
| -------------------------------- | ---------------------------------- |
| `--target-address 203.0.113.200` | Target host address or hostname    |
| `--target-account AdminUser`     | Target account to check access for |

### Hosts accessible by user

Example command: `report access hosts --user-name report.bot@example.test`

Example filename: `hosts.20260123_130640.csv`

Example output:

| Username                | Role Name   | Target Hosts  | Target Accounts |
| ----------------------- | ----------- | ------------- | --------------- |
| report.bot@example.test | privx-admin | 192.0.2.11    | sandbox         |
| report.bot@example.test | privx-admin | 203.0.113.200 | AdminUser       |

| Option (example)                      |                         |
| ------------------------------------- | ----------------------- |
| `--user-name report.bot@example.test` | User name to search for |

### Account restrictions

Example command: `report access account-restrictions --target-address 192.0.2.11`

Example filename: `account-restrictions.20260123_130720.csv`

Example output:

| Target Host | Account Name | Default Whitelist Name | Whitelist Names                          | Allow No Match | Audit Match | Audit No Match |
| ----------- | ------------ | ---------------------- | ---------------------------------------- | -------------- | ----------- | -------------- |
| 192.0.2.11  | sandbox      | SandboxWhitelist       | "SandboxWhitelist-2, SandboxWhitelist-3" | True           | True        | True           |

| Option (example)              |                                 |
| ----------------------------- | ------------------------------- |
| `--target-address 192.0.2.11` | Target host address or hostname |

### Query host access

Command: `report access query [options] [--to-json|--to-stdout|--fields <csv>]`

At least one API-level filter must be provided. User name cannot be used alone (use the `hosts` report to filter by user only).

**Note:** This report uses cached access group data; the cache lives for one hour and is refreshed automatically when you run reports after it has expired.

Example filename: `access-query.20260123_130527.csv`

| Option (example)                       |                                                                         |
| -------------------------------------- | ----------------------------------------------------------------------- |
| `--target-address 203.0.113`           | Filter by host address (substring match)                                |
| `--common-name bastion-sandbox-01`     | Filter by host common name (substring match)                            |
| `--access-group-name Sandbox`          | Filter by access group name (case-insensitive substring)                |
| `--access-group-comment "sandbox env"` | Filter by access group comment (case-insensitive substring)             |
| `--service-type SSH`                   | Filter by service type (exact match, e.g. SSH, RDP, VNC, HTTP)          |
| `--role-name linux-admin`              | Filter by role name (case-insensitive substring)                        |
| `--user-name report.bot@example.test`  | Filter by user name (cannot be used alone; combine with another filter) |

## Roles

### Query roles

Command: `report roles query`

Example filename: `roles-query.20260123_130752.csv`

Example output:

| Role Name   | Access Group Name | Block Role | Validity              | Start Time | End Time | Timezone        | IP Masks  |
| ----------- | ----------------- | ---------- | --------------------- | ---------- | -------- | --------------- | --------- |
| DummyRole   | default           | True       | "MON,TUE,WED,THU,FRI" | 00:00      | 23:00    | Europe/Helsinki | 0.0.0.0/0 |
| linux-admin | default           | False      |                       |            |          |                 |           |
| privx-admin | default           | False      |                       |            |          |                 |           |

| Option (example)                      |                                |
| ------------------------------------- | ------------------------------ |
| `--role-name linux-admin`             | Filter by role name            |
| `--access-group-name default`         | Filter by access group name    |
| `--access-group-comment "My comment"` | Filter by access group comment |

### User roles

Example command: `report roles user --user-name report.bot@example.test`

Example filename: `roles-user-report.bot@example.test.20260123_130828.csv`

Example output:

| Role Name   | User Name               | Access Group Name | Block Role | Validity | Start Time | End Time | Timezone | IP Masks |
| ----------- | ----------------------- | ----------------- | ---------- | -------- | ---------- | -------- | -------- | -------- |
| privx-admin | report.bot@example.test | default           | False      |          |            |          |          |          |
| privx-user  | report.bot@example.test | default           | False      |          |            |          |          |          |

| Option (example)                      |                         |
| ------------------------------------- | ----------------------- |
| `--user-name report.bot@example.test` | User name to search for |

### Role members

Example command: `report roles members --role-name linux-admin`

Example filename: `role-members-linux-admin.20260123_124517.csv`

Example output:

| Role Name   | Principal             | Full Name | Email                      | Access Group Name | SAM Account Name | Windows Account       | Unix Account | Source Type    |
| ----------- | --------------------- | --------- | -------------------------- | ----------------- | ---------------- | --------------------- | ------------ | -------------- |
| linux-admin | eli.hart@example.test | Eli Hart  |                            | default           |                  | eli.hart@example.test |              | MICROSOFTGRAPH |
| linux-admin | ehart                 | Eli Hart  | eli.hart@corp.example.test | default           | ehart            | ehart@ad.example.test | ehart        | AD             |

| Option (example)          |           |
| ------------------------- | --------- |
| `--role-name linux-admin` | Role name |

### Roles with contextual restrictions

Command: `report roles restrictions`

Report filename: `restrictions.20260123_123758.csv`

Example output:

| Role Name | Block Role | Validity              | Start Time | End Time | Timezone        | IP Masks  |
| --------- | ---------- | --------------------- | ---------- | -------- | --------------- | --------- |
| DummyRole | True       | "MON,TUE,WED,THU,FRI" | 00:00      | 23:00    | Europe/Helsinki | 0.0.0.0/0 |

## Reporter options and arguments

The options and arguments shape of the reporter is as follows:

`report <command> <sub-command> [options and arguments]`

### Help

Here is an example that shows the three levels of help that is available:

1. `report --help`

   ```sh
   usage: report [-h] {access,connections,roles} ...

   options:
   -h, --help            show this help message and exit
   ```

2. `report access --help`

   ```sh
   usage: report access [-h] {account,account-restrictions,hosts,query,role-map} ...

   Reports about user and role access to target hosts and accounts.

   Subcommands:
     account               List who can access a specified account on a target
     account-restrictions  List target accounts having command restrictions
     hosts                 List all target hosts a specified user can access
     query                 Query host access by various filters
     role-map              List roles that can access a target host

   options:
     -h, --help            show this help message and exit
   ```

3. `report access hosts --help`

   ```sh
   usage: report access hosts [-h] [--fields [FIELDS]] [--to-json] [--to-stdout] --user-name USER_NAME

   List all target hosts a specified user can access

   options:
     -h, --help            show this help message and exit
     --fields [FIELDS]     Override field selection. Use --fields to list available fields, or --fields field1,field2,... to select specific fields in the specified order.
     --to-json             Output results as JSON instead of CSV.
     --to-stdout           Output results to stdout instead of writing to a file.
     --user-name USER_NAME
                           User name to search for
   ```

### Fields

Report output fields can be overridden. To see available fields use the `--fields` option on a sub-command as in the following example, which also shows how to supply the fields.

```sh
report access hosts --fields

Default fields (included by default):
  role_name            - Role Name
  target_accounts      - Target Accounts
  target_host          - Target Host
  user_name            - Username

Optional fields (use --fields to include):
  role_id              - Role ID
  target_host_id       - Target Host ID
  user_id              - User ID

Usage examples:
  report access hosts --fields role_name,target_accounts,target_host
  report access hosts --fields role_name,role_id
  report access hosts --fields *,role_id  # All defaults + optional

Note: Use '*' to include all default fields, e.g., --fields *,user_id
```

**Field selection options:**

* `--fields` (no value) - Lists all available fields for the report
* `--fields field1,field2` - Select specific fields in the specified order
* `--fields *` - Select all default fields
* `--fields *,optional_field` - Select all default fields plus additional optional fields

### Output options

**Output directory:**

* By default reports are generated in `report_out/`. This can be overridden by setting the `REPORT_OUT_DIR` environment variable.

**Output format:**

* `CSV` is the default output format
* Use the `--to-json` option for `JSON` output. This outputs the exact same data as when using `CSV`

**Print to STDOUT**

* Use `--to-stdout` to print to STDOUT. No file will be created.
