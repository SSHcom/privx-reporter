# PrivX Reporter v1.1.1

Features implemented in Go has been planned for the near future, so some refactorings were made to give better support for multi-language isolation.

Minor installation and documentation changes were made.

No functional changes are included in this release.

## Changes

- Moved Python code
  - Existing Python implemention has moved to `apps/python/` 
  - Existing Python tests have moved to `tests/python`

- Installation related updates
  - Installed file changes
    - `/opt/reporter/.env-example` now has OIDC examples as comments
    - `/opt/reporter/docker-compose` also has OIDC examples as comments
  - `docs/operations/install/STANDALONE.md` has OIDC related instructions