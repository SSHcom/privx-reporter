# Accounts report output flattening

This report emits one CSV row per event and flattens `message.modifications` into a consistent schema for account-explicit, directory, and user-defined variants.

## Flattening rules

- `action` is derived from modification direction:
  - `Added` when `old_value` is empty and `new_value` is set.
  - `Removed` when `new_value` is empty and `old_value` is set.
- `modified_by` maps to `message.username`.
- `principal` is resolved in order:
  - `Principals.<index>.Principal.new_value`
  - `Principals.<index>.UsernameAttribute.new_value`
  - empty value if neither exists.
- `role_names` is all `Principals.<index>.Roles.*.Name` values joined with `|`.
- `role_ids` is all `Principals.<index>.Roles.*.ID` values joined with `|`.
- `passphrase_set` is true only when `Principals.<index>.Passphrase.new_value` is not null.
- `source` maps from `Principals.<index>.Source.new_value`.
- `variant` indicates `account-explicit`, `directory`, or `user-defined`.

## Explicit exclusions

The following modification keys are ignored and not exported:

- `ServiceOptions`
- `CommandRestrictions`
