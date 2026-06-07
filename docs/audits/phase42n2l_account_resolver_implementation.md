# Phase 42N2L - Universal Account Resolver Implementation

## Classification

`PASS_PHASE_42N2L_ACCOUNT_RESOLVER_READY_TO_COMMIT`

## Implemented rule

The shared resolver now implements the business rule:

```text
Cost Center -> 原価センタ -> 原価区分 -> 勘定科目 column 製造/一般/販売 -> account_code
```

Implemented in:

- `src/engine/account_resolver.py`

## Functions added

- `resolve_cost_type_for_cc(db_path, target_cc)`
- `resolve_account_code(db_path, target_cc, account_key_or_name)`
- `resolve_account_column_by_cost_type(cost_type)`

Mapping:

| 原価区分 / cost type | dim_accounts column |
|---|---|
| `製造` | `mfg_code` |
| `一般` | `ga_code` |
| `販売` | `sales_code` |

## Safety behavior

The resolver uses only already-loaded DB tables:

- `dim_cost_centers`
- `dim_accounts`

It does not invent account codes and does not silently fall back to another
column. Missing CC, missing account, unsupported cost type, ambiguous account
name, or blank category-specific account code raises `AccountResolutionError`.

## Modules using it now

Directly used by tests as the shared implementation. Existing runtime modules
were not broadly rewritten in this phase to avoid changing production behavior.

Compatibility was verified against the current manual event-driver resolver:

- `src/parsers/manual_event_drivers.py::_resolve_account_code`

## Modules still needing migration

These modules should migrate in a later phase where behavior changes can be
verified module-by-module:

- `src/parsers/manual_event_drivers.py` can replace its local resolver with the
  shared resolver.
- Allocation/account selection can align with the same fail-closed shared
  mapping.
- Source-derived parsers/writers that currently carry explicit account codes can
  call the shared resolver where they accept account names or account keys.
- v1/v2 file-order writers still need manifest-based source path migration.

## Risk reduction

This reduces the risk of future source-derived modules selecting the wrong
account code because the cost-type-to-account-column rule now exists in one
shared location and fails closed instead of guessing.

## Verification

Targeted tests cover:

- `1412000040` cost type lookup.
- account name -> correct account column by cost type.
- missing CC failure.
- missing account failure.
- no fallback to wrong column.
- shared resolver parity with current manual event-driver behavior.

## Conclusion

`PASS_PHASE_42N2L_ACCOUNT_RESOLVER_READY_TO_COMMIT`
