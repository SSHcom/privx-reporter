# PrivX API Permissions Required by Reporter

This document lists the PrivX role permissions required for the Reporter API client to function correctly. The API client needs a role with these permissions assigned.

## Minimum Required Permissions

| Permission | Required For |
|---|---|
| `hosts-view` | Host reports, access reports, dashboard host counts, host service breakdown |
| `roles-view` | Role reports, access reports, dashboard role counts |
| `users-view` | User reports, dashboard local user counts, auth method distribution |
| `connections-view` | Connection reports, sync server connection sync |
| `logs-view` | Audit event sync, event reports |
| `vault-add` | Secrets report (search_secrets requires vault access) |
| `sources-view` | Dashboard directory sources, source counts |
| `workflows-view` | Dashboard workflow counts |
| `network-targets-view` | Network targets report, dashboard counts |
| `access-groups-manage` | Access group reports, access query report |

## Optional Permissions

| Permission | Required For |
|---|---|
| `connections-playback` | Connection details report (full connection data) |
| `api-clients-manage` | Dashboard API client counts |
| `settings-view` | Certificate status dashboard (get_certificates_list) |

---

## API Endpoints by Service

### Host Store (`/host-store/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/hosts/search` | POST | `search_hosts()` | `hosts-view` | Access reports, host counts, host service breakdown |
| `/hosts` | GET | `get_hosts()` | `hosts-view` | Get all hosts (certificate scanning, trend sync) |
| `/hosts/{host_id}` | GET | `get_host()` | `hosts-view` | Single host lookup |

### Role Store (`/role-store/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/roles` | GET | `get_roles()` | `roles-view` | List all roles |
| `/roles/{role_id}` | GET | `get_role()` | `roles-view` | Get role by ID |
| `/roles/search` | POST | `search_roles()` | `roles-view` | Search roles, dashboard counts |
| `/roles/{role_id}/members` | GET | `get_role_members()` | `roles-view` | Access reports (who has access) |
| `/users/{user_id}/roles` | GET | `get_user_roles()` | `roles-view` | User role reports |
| `/sources` | GET | `get_sources()` | `sources-view` | Dashboard directory sources, source counts |

### Local User Store (`/local-user-store/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/users` | GET | `get_users()` | `users-view` | Local user counts, user listing |
| `/users/{user_id}` | GET | `get_user()` | `users-view` | User lookup by ID |
| `/users/search` | POST | `search_users()` | `users-view` | User search |
| `/api-clients` | GET | `get_api_clients()` | `api-clients-manage` | Dashboard API client counts |

### Connection Manager (`/connection-manager/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/connections/search` | POST | `search_connections()` | `connections-view` | Connection reports, sync server, concurrent stats |
| `/connections/{id}` | GET | `get_connection()` | `connections-view` | Connection details report |

### Monitor Service (`/monitor-service/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/auditevents/search` | POST | `search_audit_events()` | `logs-view` | Audit event sync server |

### Auth (`/auth/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/sessionstorage/sessions/search` | POST | `search_sessions()` | `users-view` | Concurrent stats (active session count) |

### Vault (`/vault/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/secrets` | GET | `get_secrets()` | `vault-add` | Secrets report (legacy) |
| `/secrets/search` | POST | `search_secrets()` | `vault-add` | Secrets report, dashboard counts |

### Authorizer (`/authorizer/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/cas` | GET | `get_certificates_list()` | `settings-view` | Certificate status dashboard |

### Workflow Engine (`/workflow-engine/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/workflows` | GET | `get_workflows()` | `workflows-view` | Dashboard workflow counts |

### Network Access Manager (`/network-access-manager/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/targets` | GET | `get_network_targets()` | `network-targets-view` | Network targets report, dashboard counts |
| `/targets` | GET | `get_api_targets()` | `network-targets-view` | API targets report, dashboard counts |

### Access Groups (`/host-store/api/v1/`)

| Endpoint | Method | SDK Method | Permission | Used By |
|---|---|---|---|---|
| `/access_groups/search` | POST | `search_access_groups()` | `access-groups-manage` | Access reports, dashboard counts |
| `/access_groups/{id}` | GET | `get_access_group()` | `access-groups-manage` | Access group detail lookup |

---

## Recommended Role Configuration

Create a dedicated PrivX role for the Reporter API client with these permissions:

```
hosts-view
roles-view
users-view
connections-view
logs-view
vault-add
sources-view
workflows-view
network-targets-view
access-groups-manage
api-clients-manage
settings-view
```

This provides read-only access to all data needed for reporting and dashboard functionality. No `*-manage` permissions are needed except `access-groups-manage` (required for searching access groups) and `api-clients-manage` (for listing API clients).

---

## Access Group Scoping (Important)

The `hosts-view` and `connections-view` permissions are **access-group-specific**. A role only grants visibility into hosts and connections that belong to the access group assigned to that role.

If your PrivX environment has **multiple access groups**, a single role with `hosts-view` and `connections-view` will only see data for its own access group. To give the Reporter full visibility across all access groups:

### Setup for multiple access groups

1. **Create the base Reporter role** with all permissions listed above. Assign it to Default access group.

2. **For each additional access group**, create a new role with:
   - `hosts-view`
   - `connections-view`
   - Access group set to the target access group

3. **Add all created roles** to the Reporter API client.

### Example

If your environment has 3 access groups (Default, Production, Staging):

| Role | Permissions | Access Group |
|---|---|---|
| `reporter-base` | All permissions listed above | Default |
| `reporter-production` | `hosts-view`, `connections-view` | Production |
| `reporter-staging` | `hosts-view`, `connections-view` | Staging |

All three roles must be assigned to the Reporter API client for complete data coverage.

### Symptoms of missing access group roles

- Host reports return fewer hosts than expected
- Connection reports/sync miss connections from certain access groups
- Access query report shows incomplete results
- Dashboard host counts are lower than actual
