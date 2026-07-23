# Baseline audit — company founding thanks event

Recorded before changing allocation logic on 2026-07-23.

## Claim

`会社設立記念 感謝イベント Sự kiện tri ân ngày thành lập công ty`
must post in October using October total headcount. Adding this event must not
remove or overwrite any previously exported cost row.

## Code baseline

- Git commit: `9f25f5b`
- Branch: `main`
- Working tree was clean before the audit.

## Existing local output snapshot

Business-row counting uses the repository's canonical
`src.engine.mp_saisan_complete_export.business_row_present` definition.

| Workbook | Business rows | Founding thanks event rows |
|---|---:|---:|
| `MP_CC_1412000004.xlsx` | 72 | 0 |
| `MP_CC_1412000006.xlsx` | 62 | 0 |
| `MP_CC_1412000036.xlsx` | 64 | 0 |
| `MP_CC_1412000040.xlsx` | 63 | 0 |
| **Total** | **261** | **0** |

These files predate the current-code reproduction below, so they are recorded
as an operational snapshot and are not used as the regression oracle.

## Isolated current-code reproduction

The pipeline was run for CC `1412000006` with copies of `mp2027.db` and
`raw/FY2027/manual_inputs.db`. Production databases, output, and run history
were not modified.

- Current-code business rows: **66**
- Current-code dynamic `Alloc:` rows: **13**
- Founding thanks event rows: **0**
- Allocation stage: **PASS**
- Export workbook was created before the diagnostic command timeout.

## Post-fix acceptance criteria

Using the same isolated inputs and the same counting definition:

1. All 66 pre-fix business-row identities remain present.
2. All 13 pre-fix dynamic allocation identities remain present.
3. Exactly one additional founding thanks event row is exported.
4. The event is posted only in October.
5. Its formula uses October `headcount_all × unit price`.
6. Expected totals for CC `1412000006`: **67 business rows** and
   **14 dynamic allocation rows**.
7. Regression tests must also prove that unrelated existing allocation rows
   remain present when this new event is added.

## Post-fix result

The pre-fix behavior and post-fix behavior were run to completion in separate
sandboxes with identical source files, copied databases, CC, fiscal year, and
exchange rate.

| Measure | Pre-fix | Post-fix | Delta |
|---|---:|---:|---:|
| Business rows | 66 | 67 | +1 |
| Removed pre-fix row instances | — | 0 | 0 |
| Added row instances | — | 1 | +1 |

The exact added identity is:

- Account: `5004086291`
- Description:
  `会社設立記念 感謝イベント Sự kiện tri ân ngày thành lập công ty`
- April–March vector:
  `blank, blank, blank, blank, blank, blank, =27*100000, blank, blank, blank, blank, blank`
- Posting month: October 2026
- Driver: October total headcount `27`
- Unit price: `100000`

The comparison used a multiset of `(account, description, 12-month vector)`,
not row positions. Result: **all 66 pre-fix row instances are present
unchanged, and the founding thanks event is the only added row**.

## Regression result

- `tests/test_posting_month_logic.py`: 18 passed.
- `tests/test_complete_v1_source_order_writer.py` plus posting-month tests:
  43 passed.
- Targeted output/manual-event compatibility tests:
  3 passed.
