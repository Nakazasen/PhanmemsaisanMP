# Graph Report - .  (2026-08-04)

## Corpus Check
- 358 files · ~367,989 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 2859 nodes · 7849 edges · 144 communities (121 shown, 23 thin omitted)
- Extraction: 98% EXTRACTED · 2% INFERRED · 0% AMBIGUOUS · INFERRED: 134 edges (avg confidence: 0.56)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- Fixed Assets Policy Tests
- Fixed Assets Audit Trace
- Source Order Workbook Writer
- Output Placement Compatibility
- Fiscal Calendar and Drivers
- Hub Workbook Construction
- End-to-End Pipeline Runner
- Cost Allocation Engine
- Fiscal Run Resolution
- Admin Consumables Preview
- Run History and Workspaces
- Application Update Installation
- Desktop Application Controls
- Preflight and Source Validation
- Headcount Source Import
- Focused Component 15
- Manual Staffing Overrides
- Portable Runtime Startup
- Focused Component 18
- Focused Component 19
- Focused Component 20
- Update Discovery Delivery
- Account Resolution Rules
- Focused Component 23
- Focused Component 24
- Focused Component 25
- Focused Component 26
- Focused Component 27
- Focused Component 28
- Focused Component 29
- Focused Component 30
- Focused Component 31
- Focused Component 32
- Focused Component 33
- Focused Component 34
- Focused Component 35
- Focused Component 36
- Focused Component 37
- Focused Component 38
- Focused Component 39
- Focused Component 40
- Focused Component 41
- Focused Component 42
- Focused Component 43
- Focused Component 44
- Focused Component 45
- Focused Component 46
- Focused Component 47
- Focused Component 48
- Focused Component 49
- Focused Component 50
- Focused Component 51
- Focused Component 52
- Focused Component 53
- Focused Component 54
- Focused Component 55
- Focused Component 56
- Focused Component 57
- Focused Component 58
- Focused Component 59
- Focused Component 60
- Focused Component 61
- Focused Component 62
- Focused Component 63
- Focused Component 64
- Focused Component 65
- Focused Component 66
- Focused Component 67
- Focused Component 68
- Focused Component 69
- Focused Component 70
- Focused Component 71
- Focused Component 72
- Focused Component 73
- Focused Component 74
- Focused Component 75
- Focused Component 76
- Focused Component 77
- Focused Component 78
- Focused Component 79
- Focused Component 80
- Focused Component 81
- Focused Component 82
- Focused Component 83
- Focused Component 84
- Focused Component 85
- Focused Component 86
- Focused Component 87
- Focused Component 88
- Focused Component 89
- Focused Component 90
- Focused Component 91
- Focused Component 92
- Focused Component 93
- Focused Component 94
- Focused Component 95
- Focused Component 96
- Focused Component 97
- Focused Component 99
- Focused Component 100
- Focused Component 101
- Focused Component 103
- Focused Component 104
- Focused Component 105
- Focused Component 106
- Focused Component 107
- Focused Component 108
- Focused Component 109
- Focused Component 110
- Focused Component 111
- Focused Component 112
- Focused Component 113
- Focused Component 114
- Focused Component 115
- Focused Component 116
- Focused Component 117
- Focused Component 118
- Focused Component 121
- Focused Component 122
- Focused Component 123
- Focused Component 124
- Focused Component 125
- Focused Component 126
- Focused Component 127
- Focused Component 128
- Focused Component 129
- Focused Component 130
- Focused Component 131
- Focused Component 132
- Focused Component 133
- Focused Component 135

## God Nodes (most connected - your core abstractions)
1. `AllocationEngine` - 158 edges
2. `HubBuilder` - 146 edges
3. `get_fy_months()` - 118 edges
4. `_mk_conn()` - 107 edges
5. `MPManagerApp` - 88 edges
6. `create_schema()` - 80 edges
7. `run_universal_pipeline()` - 76 edges
8. `_mk_tmpdir()` - 75 edges
9. `find_hub_sheet_name()` - 72 edges
10. `apply_complete_v1_source_order_to_workbook()` - 55 edges

## Surprising Connections (you probably didn't know these)
- `test_cli_flag_default_off()` --indirect_call--> `run_universal_pipeline()`  [INFERRED]
  tests/test_fixed_assets_reference_skeleton.py → scripts/run_e2e.py
- `FYConfig` --uses--> `VietnameseArgumentParser`  [INFERRED]
  scripts/audit_fixed_assets_cross_trace.py → src/utils/cli.py
- `_NullTextIO` --uses--> `AllocationEngine`  [INFERRED]
  scripts/run_e2e.py → src/engine/allocator.py
- `_NullTextIO` --uses--> `HubBuilder`  [INFERRED]
  scripts/run_e2e.py → src/engine/hub_builder.py
- `_NullTextIO` --uses--> `PipelineStageEvidence`  [INFERRED]
  scripts/run_e2e.py → src/services/run_history.py

## Import Cycles
- None detected.

## Communities (144 total, 23 thin omitted)

### Community 0 - "Fixed Assets Policy Tests"
Cohesion: 0.06
Nodes (84): expected_values(), main(), modal_rate(), Connection, Verify parser-to-writer fixed-assets policy against FY2026/FY2027 audit truth.…, Ensure no production fact row survives past the audited P terminal month., read_csv(), rendered_values() (+76 more)

### Community 1 - "Fixed Assets Audit Trace"
Cohesion: 0.05
Nodes (75): datetime, _best_subset(), build_actual(), build_expected(), category_key(), classify_reference_rows(), compare_months(), excel_round() (+67 more)

### Community 2 - "Source Order Workbook Writer"
Cohesion: 0.06
Nodes (83): apply_complete_v1_source_order_to_workbook(), _business_row_present(), _clear_business_row(), _clear_metadata_note_for_cell(), _clear_rows(), _clear_unused_template_formula_tail(), _collect_dynamic_allocation_rows(), _collect_existing_source_order_rows() (+75 more)

### Community 3 - "Output Placement Compatibility"
Cohesion: 0.05
Nodes (79): performance, skipif, Explicit FY2027-only compatibility metadata. New fiscal-year runs receive their…, group_rows_by_canonical_source_order(), OutputRow, place_rows_by_source_file_order(), PlacedRow, Source-file-order output row placement helpers. This module is intentionally… (+71 more)

### Community 4 - "Fiscal Calendar and Drivers"
Cohesion: 0.12
Nodes (16): ensure_manual_event_drivers_template(), parse_manual_event_drivers(), Load manual event counts/amounts into fact_input_data. This is intentionally…, find_hub_sheet_name(), get_fy_months(), Returns a list of 12 YYYYMM strings for the given fiscal year., Find the hub sheet name in FORM.xlsx dynamically., _find_system_cost_rows() (+8 more)

### Community 5 - "Hub Workbook Construction"
Cohesion: 0.08
Nodes (13): _load_complete_v1_dynamic_allocation_rows(), ExportIntegrityError, HubBuilder, Connection, Row, RuntimeError, Raised when an export would create a malformed or empty MP workbook., Build auditable asset-level formulas in source order. Each term keeps the… (+5 more)

### Community 6 - "End-to-End Pipeline Runner"
Cohesion: 0.05
Nodes (47): BaseException, _annual_complete_v1_source_order(), _apply_complete_v1_source_order(), _close_pipeline_connection(), _create_allocation_engine(), _default_fixed_assets_skeleton_csv_path(), _default_reference_map_path(), _default_source_dir() (+39 more)

### Community 7 - "Cost Allocation Engine"
Cohesion: 0.08
Nodes (4): AllocationEngine, Connection, Return positive hires without allowing one personnel group to offset another. A…, Account code hợp lệ: not None, not empty, not 0, not '0'.

### Community 8 - "Fiscal Run Resolution"
Cohesion: 0.06
Nodes (55): _allocation_has_exact_sheet(), annual_default_paths(), _base_dir(), detect_fiscal_year(), _file_cache_key(), FiscalYearEvidence, _has_headcount_workbook(), inspect_fiscal_year_evidence() (+47 more)

### Community 9 - "Admin Consumables Preview"
Cohesion: 0.06
Nodes (46): AdminConsumablePreviewItem, AdminConsumablesFileOrderPreview, _find_row_containing(), _month_sample(), _normalize(), preview_admin_consumables_file_order(), Any, Path (+38 more)

### Community 10 - "Run History and Workspaces"
Cohesion: 0.10
Nodes (45): create_fiscal_run_context(), FiscalRunContext, sha256_file(), _catalog_connection(), _catalog_path(), create_run_workspace(), filter_runs(), list_runs() (+37 more)

### Community 11 - "Application Update Installation"
Cohesion: 0.13
Nodes (40): activate_staged_update(), application_install_root(), ApplicationUpdateError, backup_runtime_databases(), inspect_update_package(), install_runtime_application_update(), launch_activated_update(), Any (+32 more)

### Community 12 - "Desktop Application Controls"
Cohesion: 0.08
Nodes (4): Whether shared run prerequisites are safe, regardless of source count., MPManagerApp, Refresh the editable rate and never retain a stale value., Refresh available CCs while retaining every still-valid selection.

### Community 13 - "Preflight and Source Validation"
Cohesion: 0.10
Nodes (35): Human-readable companion to the JSON provenance report., Only source paths that passed validation; never rediscover rejected files., Compatibility metadata; subset runs no longer require acceptance flags., RunPreflightReport, cached_preflight_fiscal_run(), Return a valid cached report or run and persist a fresh deep check., discover_or_create_project(), launcher_config_path() (+27 more)

### Community 14 - "Headcount Source Import"
Cohesion: 0.10
Nodes (28): _exclude_incomplete_staffing_ccs_for_audit(), Remove incomplete CCs from allocation scope in an isolated audit database., cleanup_headcount_truth(), count_headcount_truth_rows(), fiscal_year_periods(), import_headcount_time_sources(), _is_department_plan(), _is_extracted_plan() (+20 more)

### Community 15 - "Focused Component 15"
Cohesion: 0.05
Nodes (37): channel, notes, package, additionalProperties, maxLength, minLength, type, $id (+29 more)

### Community 16 - "Manual Staffing Overrides"
Cohesion: 0.13
Nodes (36): _staffing_preflight(), apply_manual_baseline_overrides(), apply_manual_time_overrides(), _copy_manual_gender_rows(), _copy_manual_rows(), copy_missing_baselines_from_april(), find_missing_baseline_ccs(), normalize_manual_time_rows() (+28 more)

### Community 17 - "Portable Runtime Startup"
Cohesion: 0.12
Nodes (34): _consume_wait_for_pid(), main(), _process_is_running(), Lightweight entrypoint for the frozen MP2027 desktop application., _wait_for_process_exit(), PermissionError, _check_release_metadata(), _check_runtime_write() (+26 more)

### Community 18 - "Focused Component 18"
Cohesion: 0.07
Nodes (19): main(), main(), CLI trích xuất nguồn sự thật nhân sự theo bộ phận từ các tệp Excel tham chiếu…, configure_utf8_console(), _NullTextIO, Tiện ích console và argparse tiếng Việt dùng chung cho các CLI MP2027., Nhận output an toàn khi ứng dụng đóng gói kiểu windowed không có console., Giữ tiếng Việt đọc được trên các code page Windows và chế độ windowed. (+11 more)

### Community 19 - "Focused Component 19"
Cohesion: 0.11
Nodes (25): _column_exists(), _column_type(), create_schema(), _default_database_path(), get_connection(), Connection, MP2027 Manager - Database Schema (Refactored V4.5.0), copy_annual_manual_inputs() (+17 more)

### Community 20 - "Focused Component 20"
Cohesion: 0.13
Nodes (32): _account_column_for_connection(), _account_name_stem(), AccountResolutionError, _candidate_rows_for_group_name(), _connect(), _find_account_code_by_keywords(), _find_account_row_by_numeric_key(), get_source_account_policy() (+24 more)

### Community 21 - "Update Discovery Delivery"
Cohesion: 0.17
Nodes (35): check_update_source(), company_update_config_path(), default_update_config_path(), discover_available_update(), discover_folder_updates(), discover_https_update(), fetch_update_candidate(), load_update_config() (+27 more)

### Community 22 - "Account Resolution Rules"
Cohesion: 0.08
Nodes (20): _mk_conn(), Nếu account theo nhóm cần lấy bị thiếu, chương trình không đoán bừa sang…, cost_type=製造, mfg_acc="" → None, không fallback ga/sales., cost_type=製造, mfg_acc="0" → None, không fallback ga/sales., cost_type=製造, mfg_acc=0 → None, không fallback ga/sales., cost_type=一般, ga_acc=None → None, không fallback mfg/sales., cost_type=一般, ga_acc="" → None, không fallback mfg/sales., cost_type=一般, ga_acc="0" → None, không fallback mfg/sales. (+12 more)

### Community 23 - "Focused Component 23"
Cohesion: 0.07
Nodes (21): apply_audited_fy2027_reference_price(), _normalize(), Read-only FY2027 compatibility helpers, excluded from future-year loading., Legacy audit helper only; never call it from the annual rule loader., _parse_unit_price(), Parse numeric unit prices such as `145$`, `1,259,500`, or plain floats., ensure_manual_headcount_template(), Create template file if not found. Returns the template path. (+13 more)

### Community 24 - "Focused Component 24"
Cohesion: 0.15
Nodes (29): Popen, _atomic_write_json(), _backup_existing_truth_files(), _department_name(), evaluate_cell(), extract_reference_staffing_sources(), extract_reference_workbook(), ExtractedDepartment (+21 more)

### Community 25 - "Focused Component 25"
Cohesion: 0.11
Nodes (31): assert_exchange_rate_formulas_safe(), audit_exchange_rate_workbook(), normalize_exchange_rate_formula(), Any, Path, Guards for USD/VND formulas written into MP output workbooks., Ghi báo cáo tỷ giá ngắn gọn, dễ mở bằng Excel., Normalize copied output formulas to the hub-sheet `$B$2` rate cell. This is… (+23 more)

### Community 26 - "Focused Component 26"
Cohesion: 0.16
Nodes (30): _append_secondary_skeleton_deduped(), apply_mp_saisan_complete_v1(), business_row_present(), canonical_description(), collect_existing_identities(), count_business_rows(), count_provenance_rows(), logical_identity_prefix() (+22 more)

### Community 27 - "Focused Component 27"
Cohesion: 0.09
Nodes (29): _annual_manual_input_store(), _annual_source_dir(), _annual_template_path(), _copy_missing_tree(), _default_source_dir(), _default_template_path(), _external_source_dir(), _external_template_path() (+21 more)

### Community 28 - "Focused Component 28"
Cohesion: 0.16
Nodes (31): apply_reference_assisted_fill_to_workbook(), _business_row_present(), _copy_business_row(), count_business_rows(), _default_quarantine_path(), _existing_identity_keys(), identify_reference_assisted_rows(), _load_invariant_rows() (+23 more)

### Community 29 - "Focused Component 29"
Cohesion: 0.14
Nodes (30): Call, _classify_driver(), _is_footnote_unit_price(), load_allocation_rules(), Classify allocation driver from raw Japanese/Vietnamese text., Select the fiscal-year allocation sheet instead of blindly using the first…, Load workbook rules and append already verified content-pack rules., _select_allocation_rules_sheet() (+22 more)

### Community 30 - "Focused Component 30"
Cohesion: 0.15
Nodes (19): _evaluate_simple_formula(), find_nnn_paperwork_file(), _format_formula_number(), _matches_header(), month_map_for_fiscal_year(), _normalize_header(), parse_nnn_paperwork(), Connection (+11 more)

### Community 31 - "Focused Component 31"
Cohesion: 0.16
Nodes (30): ArtifactVerificationError, canonical_json_bytes(), _decode_key(), Any, Path, PathLike, ValueError, Signed artifact primitives shared by content packs and full releases. This… (+22 more)

### Community 32 - "Focused Component 32"
Cohesion: 0.15
Nodes (30): Cursor, _admin_format_number(), _admin_header_key(), _admin_insert_record(), _admin_match_form_row(), _admin_period_from_value(), _detect_category(), _extract_candidate_codes() (+22 more)

### Community 33 - "Focused Component 33"
Cohesion: 0.17
Nodes (21): _attach_summary_audit_metadata(), classify_it_summary_variance(), _find_header_index(), _find_header_index_any(), _find_header_row(), _find_matching_sheet(), _join_description(), _metadata_parts() (+13 more)

### Community 34 - "Focused Component 34"
Cohesion: 0.09
Nodes (13): AST, One auditable preflight decision, including successful sources., Compatibility alias for callers built before subset-run support., SourceCheck, SourceIssue, _source(), test_complete_v1_single_export_finalizes_source_order_after_reference_layer(), test_complete_v1_single_export_without_reference_still_finalizes_source_order() (+5 more)

### Community 35 - "Focused Component 35"
Cohesion: 0.15
Nodes (27): _apply_approved_unit_price_override(), find_allocation_rules_file(), load_accounts(), load_all(), load_cost_centers(), load_uniform_entitlements(), _looks_like_allocation_rules_workbook(), _normalize_text() (+19 more)

### Community 36 - "Focused Component 36"
Cohesion: 0.25
Nodes (28): _make_workbook(), _payload(), Path, test_ambiguous_candidates_are_not_forced_when_evidence_conflicts(), test_building_land_interest_disambiguates_to_building_land_candidate(), test_bus_jp_identity_prefers_expats_transport(), test_bus_rows_are_identity_aligned_not_fixed(), test_company_trip_identity_not_found_does_not_crash() (+20 more)

### Community 37 - "Focused Component 37"
Cohesion: 0.16
Nodes (26): Namespace, _build_parser(), _capture_path_fingerprints(), _catalog_candidates(), _immutable_connection(), main(), _path_fingerprint(), _prepare_approved_baseline() (+18 more)

### Community 38 - "Focused Component 38"
Cohesion: 0.33
Nodes (9): _alloc_periods(), _insert_rule(), _missing_areas(), _mk_conn(), 配布数 rules require manual distribution counts and are now skipped., _seed_cc(), _seed_hc(), _set_working_days() (+1 more)

### Community 39 - "Focused Component 39"
Cohesion: 0.20
Nodes (22): AcceptanceIssue, _catalog_row(), _load_json(), Any, Connection, Path, Read-only acceptance checks for one real fiscal pipeline run., Validate one completed real CLI run without mutating run artifacts. (+14 more)

### Community 40 - "Focused Component 40"
Cohesion: 0.22
Nodes (25): _merge_verified_content_rules(), Insert verified data-only rules without overriding workbook identities., activate_content_pack(), ContentPackError, inspect_content_pack(), install_content_pack(), install_runtime_content_pack(), load_active_content_rules() (+17 more)

### Community 41 - "Focused Component 41"
Cohesion: 0.18
Nodes (24): apply_fixed_assets_reference_skeleton_to_workbook(), _business_row_present(), _candidate_key(), _has_usable_skeleton(), _last_business_row(), load_fixed_assets_skeleton_candidates(), _next_empty_row(), _norm() (+16 more)

### Community 42 - "Focused Component 42"
Cohesion: 0.10
Nodes (13): Resolve the active manual headcount folder. New source-folder UX: when the user…, resolve_manual_headcount_source_dir(), Tests for packaged-runtime raw/headcount_manual.csv resolution parity. Gate 2C…, Guard: run_e2e.py must pass base_dir to parse_manual_headcount., IDE mode: base_dir is the repo root with raw/ as a sibling., Gate 2D: run_e2e.py defaults must handle _MEIPASS for packaged mode., Packaged mode: base_dir (exe dir) does NOT have raw/, but _MEIPASS does., Guard: MP2027_Portable.spec must include raw CSV input files. (+5 more)

### Community 43 - "Focused Component 43"
Cohesion: 0.10
Nodes (8): current_release_version(), _friendly_error_message(), Return the release version for a user-visible GUI label., Choose a usable initial size without extending beyond smaller screens., Disable calculation immediately when the selected source changes., Check configured sources after UI startup without blocking Tkinter., test_output_lock_error_keeps_actionable_vietnamese_guidance(), Tk

### Community 44 - "Focused Component 44"
Cohesion: 0.20
Nodes (22): apply_column_s_rule_to_workbook(), cell_has_month_cost(), _is_obvious_blank_or_zero_formula(), _label_from_value(), normalize_output_description_column_s(), _numeric_value(), Any, Path (+14 more)

### Community 45 - "Focused Component 45"
Cohesion: 0.18
Nodes (23): _default_period_for_fiscal_year(), _event_default_for_name(), _event_match_text(), _format_number(), _is_explicit_zero(), _is_next_month_rule(), _merged_value(), _next_calendar_month() (+15 more)

### Community 46 - "Focused Component 46"
Cohesion: 0.09
Nodes (22): audit_date, cells, classifications, CONSISTENT_REFERENCE_ADJUSTMENT, POST_TERMINAL_REFERENCE_CONTINUES, REFERENCE_ASSET_NOT_IN_SOURCE_SNAPSHOT, REFERENCE_EMBEDDED_USD_SNAPSHOT_FORMULA, REFERENCE_MIXED_STATIC_AND_FORMULA_INPUT (+14 more)

### Community 47 - "Focused Component 47"
Cohesion: 0.19
Nodes (6): parse_manual_headcount(), Load manual headcount from CSV and write to fact_monthly_headcount…, _seed_cc(), TestExportIntegrityGuard, TestManualHeadcountGenderSplit, TestPostingMonthOverride

### Community 48 - "Focused Component 48"
Cohesion: 0.21
Nodes (22): test_display_summary_localizes_nested_values_without_mutating_json_contract(), _alignment_classification(), _cell_value(), CellDiff, _compare_row(), _compare_workbooks_strict_exact(), _disambiguate_close_candidates(), _display_summary() (+14 more)

### Community 49 - "Focused Component 49"
Cohesion: 0.23
Nodes (21): _application_inventory(), assemble_install_bundle(), _build(), build_signed_update(), main(), package(), _parse_args(), publish_update() (+13 more)

### Community 50 - "Focused Component 50"
Cohesion: 0.16
Nodes (17): FacilityFileOrderPreview, FacilityPreviewItem, _find_cost_center_row(), preview_facility_file_order(), preview_to_markdown(), Any, Path, Read-only Facility file-order preview for MP2027. The preview scans the… (+9 more)

### Community 51 - "Focused Component 51"
Cohesion: 0.18
Nodes (17): _cc_text(), ExtractedPlanParseError, _number(), parse_extracted_headcount_time_plan(), Any, ValueError, Parser for extracted staffing truth workbooks in the company Master Plan form., Raised when an extracted file does not keep the required company form. (+9 more)

### Community 52 - "Focused Component 52"
Cohesion: 0.14
Nodes (18): get_month_mapping(), Returns a mapping of month Index (0-11) to Period String (YYYYMM)., fiscal_month_labels(), fiscal_period_for_month(), ValueError, Return YYYYMM period for a month in MP2027 fiscal year. MP2027 company fiscal…, Return tuples of (month, period, canonical Vietnamese GUI label)., _validate_fiscal_year() (+10 more)

### Community 53 - "Focused Component 53"
Cohesion: 0.20
Nodes (4): Một nhân viên mới vẫn cần bộ cấp phát dù tổng người của phòng giảm., Final source-order pass phải tự mang rule công nhân, không dựa vào dòng 98., 配布数 rules require manual distribution counts and must NOT auto-allocate. Photo-…, TestNewHireAllocationIdentityDedupe

### Community 54 - "Focused Component 54"
Cohesion: 0.21
Nodes (19): ensure_manual_bus_headcount_template(), _has_value(), _make_validation_error(), _normalize_period(), _parse_blank_zero_headcount_int(), _parse_non_negative_int(), _parse_optional_headcount_int(), Any (+11 more)

### Community 55 - "Focused Component 55"
Cohesion: 0.16
Nodes (18): _filename_period_coverage(), Return shared System Cost filename coverage for the audit table., _expand_system_period_range(), map_system_source_periods(), Path, Fiscal-year period helpers for MP2027. The company fiscal year starts in April…, Parse one filename into one month or an inclusive month range within FY., Return deterministic file-to-period assignments and reject overlap/gaps. (+10 more)

### Community 56 - "Focused Component 56"
Cohesion: 0.15
Nodes (11): _app_with_choices(), Root, test_parse_selected_cost_centers_requires_at_least_one_choice(), test_parse_selected_cost_centers_supports_multiple_rooms(), test_refresh_choices_keeps_valid_selections_and_removes_stale_values(), test_selecting_every_cost_center_sets_all_summary(), test_successful_pipeline_can_open_output(), Variable (+3 more)

### Community 57 - "Focused Component 57"
Cohesion: 0.22
Nodes (16): get_group_spec(), is_file_order_mode(), is_fixed_row_compatible(), Output mode definitions for MP2027 hub row placement. This module is…, Return the default output group spec for ``group_id``., Return whether a blank row should separate this completed group., Return whether the spec is intended for file-order placement., Return whether the spec carries fixed-row compatibility metadata. (+8 more)

### Community 58 - "Focused Component 58"
Cohesion: 0.19
Nodes (8): FiscalProjectPaths, _portable_path(), ProjectConfig, Any, Validate and atomically update shared and annual storage roles., Reject cross-FY manual-store reuse and operational/manual collisions., Resolved absolute paths used by one fiscal year., Read, resolve and safely update one project.json file.

### Community 59 - "Focused Component 59"
Cohesion: 0.24
Nodes (17): _backup_database(), _column_type(), _create_ledger(), current_schema_version(), _database_path(), MigrationResult, Connection, Path (+9 more)

### Community 60 - "Focused Component 60"
Cohesion: 0.22
Nodes (3): Resolve account_code using target CC cost type and dim_accounts.…, resolve_account_code(), TestSharedAccountResolver

### Community 61 - "Focused Component 61"
Cohesion: 0.18
Nodes (12): apply_facility_file_order_to_open_workbook(), apply_facility_file_order_to_workbook(), _clear_preview_row(), _preview_value(), Any, Path, Explicit Facility file-order preview/export workbook writer. This module is…, Apply Facility file-order rows to an explicit existing workbook path. (+4 more)

### Community 62 - "Focused Component 62"
Cohesion: 0.19
Nodes (16): OutputGroupSpec, OutputMode, Sort output groups by requirement file order., Canonical output placement modes from Phase 42N1L., Declarative output placement spec for one source-file group., Return the number of declared cost items for the group., sort_output_groups_by_file_order(), _file_order_group_row_count() (+8 more)

### Community 63 - "Focused Component 63"
Cohesion: 0.16
Nodes (10): _CompanyFormRenderer, _empty_zero(), _excel_column(), ExtractionError, ValueError, The official form represents user-entered zeroes as blank cells., Use desktop Excel to preserve the exact company workbook form., Populate the protected company form without removing its protection metadata. (+2 more)

### Community 64 - "Focused Component 64"
Cohesion: 0.24
Nodes (11): get_required_headcount_periods(), Return baseline previous March plus the fiscal Apr-Mar months., format_headcount_save_errors(), Validate GUI headcount inputs for an atomic full-series save., validate_headcount_save_period_rows(), _full_period_values(), test_headcount_save_blank_baseline_is_saved_as_zero_and_no_old_defaulting_source(), test_headcount_save_blank_worker_is_zero_and_invalid_numbers_are_exact_errors() (+3 more)

### Community 65 - "Focused Component 65"
Cohesion: 0.31
Nodes (16): _annual_source_snapshot(), default_preflight_cache_path(), _directory_snapshot(), _file_stat(), get_cached_preflight(), _normalized_path(), preflight_fingerprint(), preflight_fingerprint_payload() (+8 more)

### Community 66 - "Focused Component 66"
Cohesion: 0.19
Nodes (13): Return canonical output group specs for future row-placement planning., get_default_output_group_specs(), Return canonical default output group specs sorted by requirement order., test_default_output_group_order_matches_requirement_image(), test_sort_output_groups_by_file_order(), _planned_by_id(), test_birthday_and_nnn_plan_source_order_rows(), test_blank_row_after_each_file_order_group() (+5 more)

### Community 67 - "Focused Component 67"
Cohesion: 0.25
Nodes (12): Exception, audit_image(), capture_range_com(), audit_image(), capture_range_com(), get_sheet_drawings(), parse_range(), print_flush() (+4 more)

### Community 68 - "Focused Component 68"
Cohesion: 0.25
Nodes (14): default_app_root(), LauncherStateError, main(), Any, Path, PathLike, ValueError, Stable launcher for versioned MP2027 onedir releases. (+6 more)

### Community 69 - "Focused Component 69"
Cohesion: 0.23
Nodes (12): Write an explicit Facility file-order preview workbook to ``output_path``., write_facility_file_order_preview_workbook(), _hub_sheet(), test_writer_contains_six_facility_items(), test_writer_creates_preview_workbook_without_touching_template(), test_writer_leaves_blank_row_206(), test_writer_requires_explicit_output_path(), test_writer_writes_facility_rows_200_to_205() (+4 more)

### Community 70 - "Focused Component 70"
Cohesion: 0.18
Nodes (14): _is_missing_baseline_error(), _pipeline_failure_summary(), Return True for both current preflight and legacy baseline error formats., Keep full subprocess output in the log while returning its final error block., find_form_template_hygiene_issues(), Workbook, List concrete department data that must not ship in a reusable FORM. Structural…, Path (+6 more)

### Community 72 - "Focused Component 72"
Cohesion: 0.14
Nodes (14): const, const, const, pattern, type, const, properties, entrypoint (+6 more)

### Community 73 - "Focused Component 73"
Cohesion: 0.20
Nodes (12): Load staffing through the canonical field-level source policy., CanonicalHeadcount, HeadcountSourceError, load_canonical_headcount(), _number(), Connection, Row, ValueError (+4 more)

### Community 74 - "Focused Component 74"
Cohesion: 0.27
Nodes (12): sha256_bytes(), _build_update(), _config(), Path, test_folder_catalog_supplies_release_notes_and_verifies_its_package(), test_folder_discovery_ignores_partial_invalid_and_selects_newest(), test_https_catalog_requires_valid_fields_and_newer_version(), test_load_update_config_prefers_user_then_company_policy() (+4 more)

### Community 75 - "Focused Component 75"
Cohesion: 0.15
Nodes (13): const, pattern, type, pattern, type, const, properties, content_schema (+5 more)

### Community 76 - "Focused Component 76"
Cohesion: 0.22
Nodes (12): _birthday_unit_price(), find_birthday_file(), _formula_number(), parse_birthday_workbook(), Connection, Parser for FY2027 birthday-cost workbook., Resolve birthday price from the annual allocation-rules source., Load birthday workbook amounts into explicit FORM row 59. (+4 more)

### Community 77 - "Focused Component 77"
Cohesion: 0.23
Nodes (10): main(), _parse_args(), provision_update_key(), Path, PathLike, Provision an MP2027 update signing key without storing its private half in Git., Create a private key outside the repo and add only its public key to release…, _release() (+2 more)

### Community 78 - "Focused Component 78"
Cohesion: 0.18
Nodes (11): database_schema, entrypoint, health_check, files, id, key_id, kind, min_app_version (+3 more)

### Community 81 - "Focused Component 81"
Cohesion: 0.20
Nodes (10): content_schema, fiscal_year, files, id, key_id, kind, min_app_version, schema (+2 more)

### Community 82 - "Focused Component 82"
Cohesion: 0.20
Nodes (10): items, minItems, type, additionalProperties, required, type, path, sha256 (+2 more)

### Community 83 - "Focused Component 83"
Cohesion: 0.20
Nodes (10): items, minItems, type, additionalProperties, required, type, path, sha256 (+2 more)

### Community 84 - "Focused Component 84"
Cohesion: 0.20
Nodes (10): properties, minLength, type, path, sha256, size, pattern, type (+2 more)

### Community 85 - "Focused Component 85"
Cohesion: 0.33
Nodes (9): _cc_text(), _normalized_text(), _number(), parse_headcount_time_plan(), Any, Parse departmental FY headcount/time plan workbooks submitted as source truth., Return lookup status and the JP/VN pair relevant to CC + displayed B5., Parse one departmental plan layout without writing the database. (+1 more)

### Community 86 - "Focused Component 86"
Cohesion: 0.49
Nodes (9): _db_periods(), _period_rows(), Path, _read_csv(), _seed_runtime(), test_atomic_failure_does_not_change_csv_or_db(), test_temp_csv_db_save_load_fy2027_and_multi_cc(), test_temp_csv_db_save_load_fy2028() (+1 more)

### Community 87 - "Focused Component 87"
Cohesion: 0.22
Nodes (9): properties, const, path, sha256, size, pattern, type, minimum (+1 more)

### Community 88 - "Focused Component 88"
Cohesion: 0.36
Nodes (8): collect_test_count(), main(), markdown(), module_kind(), Path, python_files(), Tạo đường cơ sở chất lượng kỹ thuật MP2027 nhanh và có thể tái lập., scan()

### Community 89 - "Focused Component 89"
Cohesion: 0.42
Nodes (8): _atomic_write_json(), main(), Any, Path, Isolated Excel COM worker for reference staffing workbook rendering. Business-…, Render all requested workbooks and write a fail-closed response., run_worker(), _write_status()

### Community 90 - "Focused Component 90"
Cohesion: 0.42
Nodes (8): _find_system_row(), _format_number(), _formula_terms(), _load_expected_from_db(), main(), _parse_component_term(), Path, verify()

### Community 91 - "Focused Component 91"
Cohesion: 0.50
Nodes (6): main(), markdown(), Xuất schema SQLite hiện hành thành JSON và từ điển dữ liệu dễ đọc., schema_catalog(), test_schema_catalog_is_generated_without_runtime_data(), test_schema_dictionary_contains_erd_and_regeneration_command()

### Community 92 - "Focused Component 92"
Cohesion: 0.29
Nodes (7): parse_facility(), parse_facility_sheet(), Connection, DataFrame, MP2027 Manager - Facility Parser (施設課) Parses 施設課 MPFY[Year].xlsx to extract: -…, Parse the approved facility workbook and insert into fact_input_data., Parse a facility sheet into list of dicts.

### Community 93 - "Focused Component 93"
Cohesion: 0.52
Nodes (6): main(), Path, ZipFile, safe_zip_members(), sha256(), verify()

### Community 94 - "Focused Component 94"
Cohesion: 0.52
Nodes (6): _run_cli(), test_cli_creates_preview_workbook_in_tmp_path(), test_cli_does_not_modify_template_or_source(), test_cli_help_or_argparse_available(), test_cli_output_has_rows_200_to_205_and_blank_206(), test_cli_requires_explicit_output()

### Community 96 - "Focused Component 96"
Cohesion: 0.62
Nodes (6): child_main(), discover(), main(), _norm(), Path, _scan_one()

### Community 97 - "Focused Component 97"
Cohesion: 0.47
Nodes (4): normalize_uniform_text(), Canonical uniform/cup entitlement and allocation-rule identities., uniform_item_key_for_rule(), UniformItemSpec

### Community 99 - "Focused Component 99"
Cohesion: 0.60
Nodes (5): _builder_with_asset_rows(), test_fixed_assets_payload_marks_explicit_zero_terminal_month_without_post_terminal_months(), test_fixed_assets_payload_omits_months_after_depreciation_ends(), test_fixed_assets_per_asset_rounding_differs_from_rounding_aggregated_usd(), test_fixed_assets_rounds_each_asset_before_category_aggregation()

### Community 100 - "Focused Component 100"
Cohesion: 0.33
Nodes (3): Gate 2D: universal_app.py must support headless export via CLI args., Without CLI args, the GUI entry path must remain intact., TestHeadlessCLIEntry

### Community 103 - "Focused Component 103"
Cohesion: 0.40
Nodes (4): additionalProperties, $schema, title, type

### Community 104 - "Focused Component 104"
Cohesion: 0.40
Nodes (4): additionalProperties, $schema, title, type

### Community 106 - "Focused Component 106"
Cohesion: 0.50
Nodes (4): real_pipeline_acceptance, requires_raw_excel, Release gate: execute source-to-publication CC005 through the real CLI., test_real_cc005_pipeline_runs_end_to_end_in_isolated_workspace()

### Community 107 - "Focused Component 107"
Cohesion: 0.50
Nodes (4): maximum, minimum, type, fiscal_year

### Community 108 - "Focused Component 108"
Cohesion: 0.83
Nodes (3): _conn(), test_target_cc_cleanup_preserves_other_allocator_missing_rows(), test_target_cc_limits_cost_centers_and_mapping_rows()

### Community 113 - "Focused Component 113"
Cohesion: 0.67
Nodes (3): pattern, type, min_app_version

### Community 114 - "Focused Component 114"
Cohesion: 0.67
Nodes (3): version, pattern, type

### Community 115 - "Focused Component 115"
Cohesion: 0.67
Nodes (3): minimum, type, database_schema

### Community 116 - "Focused Component 116"
Cohesion: 0.67
Nodes (3): pattern, type, min_app_version

### Community 117 - "Focused Component 117"
Cohesion: 0.67
Nodes (3): version, pattern, type

### Community 118 - "Focused Component 118"
Cohesion: 0.67
Nodes (3): _failed_run_database_from_output(), Resolve the exact immutable run DB named by the subprocess traceback., test_failed_run_database_resolver_accepts_only_expected_fy_history()

### Community 121 - "Focused Component 121"
Cohesion: 0.67
Nodes (3): fixture, Load the requirement markdown once per module., req_text()

## Knowledge Gaps
- **127 isolated node(s):** `audit_date`, `cells`, `CONSISTENT_REFERENCE_ADJUSTMENT`, `POST_TERMINAL_REFERENCE_CONTINUES`, `REFERENCE_ASSET_NOT_IN_SOURCE_SNAPSHOT` (+122 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **23 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AllocationEngine` connect `Cost Allocation Engine` to `Focused Component 73`, `Focused Component 67`, `Focused Component 20`?**
  _High betweenness centrality (0.003) - this node is a cross-community bridge._
- **Why does `HubBuilder` connect `Hub Workbook Construction` to `Focused Component 73`, `Focused Component 66`, `Focused Component 20`, `Focused Component 62`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **Why does `_resolve_primary_reference_path()` connect `End-to-End Pipeline Runner` to `Fiscal Run Resolution`?**
  _High betweenness centrality (0.002) - this node is a cross-community bridge._
- **Are the 2 inferred relationships involving `AllocationEngine` (e.g. with `AccountResolutionError` and `HeadcountSourceError`) actually correct?**
  _`AllocationEngine` has 2 INFERRED edges - model-reasoned connections that need verification._
- **Are the 3 inferred relationships involving `HubBuilder` (e.g. with `AccountResolutionError` and `OutputGroupSpec`) actually correct?**
  _`HubBuilder` has 3 INFERRED edges - model-reasoned connections that need verification._
- **Are the 4 inferred relationships involving `MPManagerApp` (e.g. with `ApplicationUpdateError` and `ContentPackError`) actually correct?**
  _`MPManagerApp` has 4 INFERRED edges - model-reasoned connections that need verification._
- **What connects `audit_date`, `cells`, `CONSISTENT_REFERENCE_ADJUSTMENT` to the rest of the system?**
  _127 weakly-connected nodes found - possible documentation gaps or missing edges._