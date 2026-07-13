# Phase 42N2K - Real Source-Derived Coverage Check

## Classification

`WARNING_PHASE_42N2K_SPEC_AHEAD_OF_CODE`

## Scope

Read-only verification of the current implementation. No code was changed. No full
pytest was run. No commit/stage was performed.

Inputs reviewed:

- `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026.xlsx`
- `raw/Cải tiến nhập dữ liệu chung vào file MPnew 04.06.2026_ảnh.xlsx`
- `docs/knowledge/mp_saisan_business_knowledge_base_v2.md`
- `scripts/run_e2e.py`
- `src/engine/`
- `raw/source_file_order.csv`
- `raw/source_file_order.xlsx`
- `raw/FORM.xlsx`
- `raw/*.xlsx`, `raw/*.xls`, `raw/*.csv`

## Executive finding

The requirement exists in the business specification, and parts of it are
implemented. However, the full generic rule:

> Cost Center -> 原価センタ -> 原価区分 -> 勘定科目 column 製造/一般/販売 -> account_code

is **not implemented as a universal resolver for every source-derived module**.
It is implemented in specific places only, especially manual event drivers and
some hard-coded/export logic. Therefore the correct status is:

`PARTIAL`, not full `IMPLEMENTED`.

## Evidence summary

### Cost center / department loading

Implemented in [loader.py](file:///D:/Sandbox/MP2027/src/db/loader.py#L169-L225):

- Reads `FORM.xlsx` cost center sheet.
- Stores code, Japanese name, saisan type, and cost type in `dim_cost_centers`.
- Uses columns by position:
  - code from first column,
  - department/name from second column,
  - saisan type from fourth column,
  - cost type / 原価区分 from fifth column.

Schema exists in [schema.py](file:///D:/Sandbox/MP2027/src/db/schema.py#L49-L60):

- `dim_cost_centers(code, name_jp, seq_no, saisan_type, cost_type, ...)`
- `dim_accounts(code, name_jp, ..., mfg_code, ga_code, sales_code, ...)`

### Account master loading

Implemented in [loader.py](file:///D:/Sandbox/MP2027/src/db/loader.py#L228-L305):

- Reads `FORM.xlsx` account sheet (`勘定科目`).
- Stores the base account code and three category-specific account columns:
  - `mfg_code` for 製造,
  - `ga_code` for 一般,
  - `sales_code` for 販売.

### Generic account lookup rule

Partially implemented.

Concrete implementation exists in
[manual_event_drivers.py](file:///D:/Sandbox/MP2027/src/parsers/manual_event_drivers.py#L167-L200):

- `_resolve_account_code(conn, cc_code, account_jp_name)`:
  1. Finds the CC in `dim_cost_centers`.
  2. Reads `cost_type`.
  3. Finds exactly one `dim_accounts` row by Japanese account name.
  4. Selects `mfg_code`, `ga_code`, or `sales_code` by cost type.

But this resolver is local to manual event drivers. It is not a shared resolver
used by all parsers/export writers.

### FORM lookup formulas

Implemented for appended output rows in
[hub_builder.py](file:///D:/Sandbox/MP2027/src/engine/hub_builder.py#L214-L233):

- Writes formulas using `勘定科目` and `HLOOKUP($E$5, 勘定科目!$F$1:$H$2, ...)`.
- This helps Excel display lookup data after export.
- It is not the same as a Python-side universal source-derived account resolver.

### Source file discovery/order

Implemented via manifest logic in
[source_manifest.py](file:///D:/Sandbox/MP2027/src/utils/source_manifest.py#L11-L24) and
[source_manifest.py](file:///D:/Sandbox/MP2027/src/utils/source_manifest.py#L193-L220).

Explicit source order is present in
[source_file_order.csv](file:///D:/Sandbox/MP2027/raw/source_file_order.csv):

| Order | Category | File |
|---:|---|---|
| 1 | facility | `施設課　MPFY2027.xlsx` |
| 2 | fixed_assets | `固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx` |
| 3 | it_simulation | `システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls` |
| 4 | it_simulation | `システム課金金額(Simulation)_FY2027_July.2026 ~ Dec.2026(Change AMS & PLM price).xls` |
| 5 | it_simulation | `システム課金金額(Simulation)_FY2027_Jan.2027 ~ March.2027(Change SAP price).xls` |
| 6 | ga | `総務課 FY2027 MP 振替予定.xlsx` |
| 7 | birthday | `Sinh nhật MP FY2027.xlsx` |
| 8 | allocation_rules | `FY2027配賦額一覧 (2025.12.29).xlsx` |
| 9 | nnn_paperwork | `Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx` |

The pipeline logs the configured source order in
[run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L186-L193).

## Trace for target CC 1412000040

### Where `target_cc` enters

`target_cc` enters the CLI pipeline through
[run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L115-L133), then is used
for single-CC export in
[run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L272-L321).

In single-CC mode:

1. Base template export:
   - `builder.export_to_template(template_path, out_path, cc_code=target_cc)`
2. Optional v1/v2 row writers:
   - Facility file-order export
   - Admin consumables export
   - System Cost export
   - Reference-assisted primary fill

### Which source files are selected automatically

Parsers use `source_dir` plus `raw/source_file_order.csv` or
`raw/source_file_order.xlsx` through `resolve_manifest_file(s)`.

However, some export writers still receive hard-coded file names in
[run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L264-L271):

- `施設課　MPFY2027.xlsx`
- `総務課 FY2027 MP 振替予定.xlsx`
- `FY2027配賦額一覧 (2025.12.29).xlsx`
- three System Cost simulation files

So source selection is **manifest-backed for parsers**, but **still partly
hard-coded for v1/v2 export writers**.

### Source-derived modules currently present

| Module | Source-derived status | Evidence |
|---|---|---|
| Facility parser/base facts | Implemented | `parse_facility(conn, source_dir=source_dir)` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L194-L195) |
| Fixed assets parser/base facts | Implemented | `parse_fixed_assets(...)` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L196-L197) |
| IT/System Cost parser | Implemented | `parse_it_simulation(...)` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L198-L199) |
| GA parser | Implemented | `parse_ga(...)` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L200-L202) |
| Birthday workbook parser | Implemented, but coverage must be verified by data result | `parse_birthday_workbook(...)` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L203-L212) |
| Manual headcount | Manual source-derived when CSV exists | `parse_manual_headcount(...)` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L213-L222) |
| Manual special costs | Manual source-derived when CSV exists | `parse_manual_special_costs(...)` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L223-L232) |
| Manual event drivers | Manual source-derived when CSV exists; account lookup partial implemented | [manual_event_drivers.py](file:///D:/Sandbox/MP2027/src/parsers/manual_event_drivers.py#L181-L200) |
| NNN paperwork | Implemented parser, coverage must be verified by data result | `parse_nnn_paperwork(...)` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L243-L252) |
| Allocation | Implemented allocation engine | `AllocationEngine(conn).run_allocation()` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L254-L259) |

### Reference-assisted modules

| Module | Reference-assisted status | Evidence |
|---|---|---|
| Hybrid v2 primary reference fill | Implemented and explicit opt-in | `--file-order-export-v2` enables `primary_reference_fill` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L141-L144) |
| Primary reference scope guard | Implemented for CC 1412000040 / explicit map/path | `_resolve_primary_reference_path(...)` in [run_e2e.py](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L84-L113) |
| Reference provenance | Implemented as not source-derived | [reference_assisted_fill.py](file:///D:/Sandbox/MP2027/src/engine/reference_assisted_fill.py) |

### Unhandled / not proven as universal

| Area | Status | Reason |
|---|---|---|
| Universal account lookup across all modules | PARTIAL | Resolver is local to manual event drivers; other parsers use their own logic or explicit source account codes. |
| Universal department-to-source file matching | PARTIAL | Manifest gives ordered source categories; it does not map every source row/file to a target department universally. |
| v1/v2 export writer source selection | PARTIAL | Some paths are still hard-coded by filename in `run_e2e.py`. |
| Claiming all 1412000040 costs are source-derived | NOT SAFE | Hybrid v2 includes reference-assisted rows explicitly labelled as not source-derived. |
| Other CCs with Hybrid v2 | Guarded, not universal | Requires `--primary-reference-path` or map row for the target CC. |

## Requirement capability table

| Requirement capability | Spec exists | Code exists | Test exists | Status | Evidence |
|---|---|---|---|---|---|
| Load cost centers from `原価センタ` | Yes | Yes | Likely indirect | IMPLEMENTED | [loader.py:L169-L225](file:///D:/Sandbox/MP2027/src/db/loader.py#L169-L225) |
| Load `原価区分` / cost type | Yes | Yes | Seeded in tests | IMPLEMENTED | [loader.py:L208-L220](file:///D:/Sandbox/MP2027/src/db/loader.py#L208-L220) |
| Load account master `勘定科目` | Yes | Yes | Likely indirect | IMPLEMENTED | [loader.py:L228-L305](file:///D:/Sandbox/MP2027/src/db/loader.py#L228-L305) |
| Store 製造/一般/販売 account columns | Yes | Yes | Some parser tests | IMPLEMENTED | [schema.py:L56-L60](file:///D:/Sandbox/MP2027/src/db/schema.py#L56-L60), [loader.py:L271-L300](file:///D:/Sandbox/MP2027/src/db/loader.py#L271-L300) |
| Resolve account_code by CC cost type and account Japanese name | Yes | Yes, local only | Yes for manual event cases | PARTIAL | [manual_event_drivers.py:L167-L200](file:///D:/Sandbox/MP2027/src/parsers/manual_event_drivers.py#L167-L200) |
| Use the resolver across every source parser | Yes | No | No | SPEC_ONLY_NOT_IMPLEMENTED | No shared resolver in `src/engine`; grep found only local manual resolver. |
| Select source files by explicit order | Yes | Yes for parsers | Yes/indirect | IMPLEMENTED | [source_manifest.py:L193-L220](file:///D:/Sandbox/MP2027/src/utils/source_manifest.py#L193-L220), [source_file_order.csv](file:///D:/Sandbox/MP2027/raw/source_file_order.csv) |
| Select v1/v2 writer sources by manifest | Yes | Partial | Unknown | PARTIAL | [run_e2e.py:L264-L271](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L264-L271) still hard-codes filenames. |
| Source-derived Facility/System/Admin exports | Yes | Yes with explicit flags | Yes targeted | IMPLEMENTED/PARTIAL | v1 flags call file-order/admin/system writers in [run_e2e.py:L277-L301](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L277-L301). |
| Reference-assisted Hybrid v2 | Yes | Yes | Yes targeted | IMPLEMENTED | [run_e2e.py:L302-L320](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L302-L320) |
| Avoid wrong reference workbook for other CC | Yes | Yes | Yes targeted | IMPLEMENTED | [run_e2e.py:L84-L113](file:///D:/Sandbox/MP2027/scripts/run_e2e.py#L84-L113) |
| Claim every generated row is source-derived | No | No | Yes policy | CORRECTLY_NOT_IMPLEMENTED | Hybrid v2 keeps reference-assisted provenance. |

## Non-tech conclusion

### Can the user run safely?

Yes, for the proven CC `1412000040`, if the user understands the mode boundaries.
The safest current run is explicit Hybrid v2:

```powershell
py scripts/run_e2e.py --target-cc 1412000040 --file-order-export-v2
```

This is safe in the sense that:

- Default export remains unchanged unless the explicit flag is used.
- v2 is scoped to the known primary reference for `1412000040`.
- Reference-assisted rows are not claimed as source-derived.
- The remaining physical 2-row delta has been identified as false-gap aliases
  (`電気代` / `水道代` already generated as Facility electricity/water).

### What is safe to claim?

Safe claims:

- The program can load cost centers and account master tables from `FORM.xlsx`.
- The program stores cost type (`製造` / `一般` / `販売`) and category-specific
  account codes.
- The program has a working account resolver for manual event driver rows.
- The program can use source manifest order for parser source selection.
- Hybrid v2 for CC `1412000040` is reference-assisted and scope-guarded.

### What is not safe to claim?

Do **not** claim yet:

- “All account lookup is implemented universally.”
- “Every module derives account_code through the same Cost Center -> 原価区分 ->
  勘定科目 rule.”
- “Every generated row in Hybrid v2 is source-derived.”
- “Hybrid v2 is proven for all departments.”
- “All source files are automatically mapped to a department/CC.”

### Which flags must be used?

For current proven Hybrid v2 on CC `1412000040`:

```powershell
--target-cc 1412000040 --file-order-export-v2
```

For any other CC, a correct reference workbook must be provided or mapped:

```powershell
--target-cc <other_cc> --file-order-export-v2 --primary-reference-path <correct_MP_FY2027_reference.xlsx>
```

Without that, reference-assisted fill should fail clearly.

### What still requires manual/reference-assisted provenance?

- Rows filled from primary reference skeletons remain `REFERENCE_ASSISTED`, not
  source-derived.
- Manual CSV modules remain manual source-derived only when user-provided CSV
  rows exist and validate.
- Any module whose row exists only because the reference skeleton had it must keep
  reference-assisted provenance.

## Final answer

`WARNING_PHASE_42N2K_SPEC_AHEAD_OF_CODE`
