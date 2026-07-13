# Phase 42N2M - Manual Event Drivers Resolver Migration

## Classification

`PASS_PHASE_42N2M_MANUAL_EVENT_DRIVERS_RESOLVER_READY_TO_COMMIT`

## Change summary

`manual_event_drivers` now delegates account-name lookup to the shared account
resolver instead of maintaining its own Cost Center / 原価区分 / 勘定科目 logic.

Changed files:

- `src/engine/account_resolver.py`
- `src/parsers/manual_event_drivers.py`
- `tests/test_account_resolver.py`

## Implemented behavior

The shared resolver path used by manual event drivers is:

```text
manual_event_drivers
  -> resolve_account_code_for_connection(conn, cc_code, account_jp_name)
  -> dim_cost_centers.cost_type
  -> dim_accounts.mfg_code / ga_code / sales_code
```

This preserves valid behavior while changing failures to explicit
`AccountResolutionError` messages inside parser error reporting.

## Safety guarantees

- No silent fallback to another account column.
- Missing CC fails clearly.
- Missing account fails clearly.
- Missing category-specific account code fails clearly.
- Existing `_resolve_account_code(...)` wrapper remains for compatibility and
  returns `None` when shared resolution fails.

## Tests

Updated `tests/test_account_resolver.py` to verify:

- Account code selected by cost type.
- Wrong-column fallback does not happen.
- Manual event drivers call the shared connection resolver.

## Modules now using shared resolver

- `src/parsers/manual_event_drivers.py`

## Modules still needing migration

- Allocation account selection still has its own `_get_account_for_cc` behavior.
- Other source-derived parsers/writers that accept account names can migrate
  module-by-module later.

## Conclusion

`PASS_PHASE_42N2M_MANUAL_EVENT_DRIVERS_RESOLVER_READY_TO_COMMIT`
