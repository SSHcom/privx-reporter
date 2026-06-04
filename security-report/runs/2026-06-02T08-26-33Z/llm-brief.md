# Security scan brief (2026-06-02T08-26-33Z)

Total findings: 20

## By severity

- medium: 2
- low: 18

## By surface

- cli+ui-shared: 11
- ui: 7
- sync-internal: 2

## Findings

- [medium] bandit/B608: Possible SQL injection vector through string-based query construction. @ administration/migration/_files/2026-04-17-create-all-tables.py:145 (surface=cli+ui-shared)
- [medium] bandit/B608: Possible SQL injection vector through string-based query construction. @ administration/migration/_files/2026-04-17-create-all-tables.py:164 (surface=cli+ui-shared)
- [low] bandit/B404: Consider possible security implications associated with the subprocess module. @ lib/_backup/backup.py:18 (surface=cli+ui-shared)
- [low] bandit/B607: Starting a process with a partial executable path @ lib/_backup/backup.py:37 (surface=cli+ui-shared)
- [low] bandit/B603: subprocess call - check for execution of untrusted input. @ lib/_backup/backup.py:37 (surface=cli+ui-shared)
- [low] bandit/B101: Use of assert detected. The enclosed code will be removed when compiling to opti @ lib/database/sync/time_series/helpers.py:106 (surface=cli+ui-shared)
- [low] bandit/B101: Use of assert detected. The enclosed code will be removed when compiling to opti @ lib/env_sync.py:135 (surface=cli+ui-shared)
- [low] bandit/B101: Use of assert detected. The enclosed code will be removed when compiling to opti @ lib/env_sync.py:142 (surface=cli+ui-shared)
- [low] bandit/B105: Possible hardcoded password: 'DB_DATA_PASSWORD' @ lib/interactive/env/database.py:137 (surface=cli+ui-shared)
- [low] bandit/B105: Possible hardcoded password: '' @ lib/interactive/env/ui.py:81 (surface=cli+ui-shared)
- [low] bandit/B105: Possible hardcoded password: '' @ lib/interactive/env/ui.py:92 (surface=cli+ui-shared)
- [low] bandit/B101: Use of assert detected. The enclosed code will be removed when compiling to opti @ sync_server/main.py:77 (surface=sync-internal)
- [low] bandit/B101: Use of assert detected. The enclosed code will be removed when compiling to opti @ sync_server/main.py:78 (surface=sync-internal)
- [low] bandit/B105: Possible hardcoded password: 'OIDC' @ ui/db/user_queries.py:15 (surface=ui)
- [low] bandit/B105: Possible hardcoded password: 'session_token' @ ui/services/session/keys.py:19 (surface=ui)
- [low] bandit/B105: Possible hardcoded password: 'oidc_pending_token_response' @ ui/views/login/oidc.py:30 (surface=ui)
- [low] bandit/B105: Possible hardcoded password: 'oidc_id_token' @ ui/views/login/oidc.py:33 (surface=ui)
- [low] bandit/B105: Possible hardcoded password: 'oidc_access_token' @ ui/views/login/oidc.py:34 (surface=ui)
- [low] bandit/B105: Possible hardcoded password: 'oidc_refresh_token' @ ui/views/login/oidc.py:35 (surface=ui)
- [low] bandit/B105: Possible hardcoded password: 'oidc_id_token_exp' @ ui/views/login/oidc.py:38 (surface=ui)
