# Sales Account Resolution Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure the deployed MP2027 Manager resolves facility building depreciation account `5006016260` for sales Cost Center `1412000030` instead of failing with an ambiguous grouped-account error.

**Architecture:** The resolver selects the account column from the Cost Center's `cost_type`, then identifies the matching sibling account by the semantic account-name stem and its cost-type suffix. The source repository already contains the required resolver support for the abbreviated sales suffix `（販）`; the observed failure is from the deployed 0.1.6 package, which predates it. A new release must carry the existing source fix without modifying allocation or financial logic.

**Tech Stack:** Python 3.13, SQLite, pytest, PyInstaller/Inno Setup release flow.

---

### Task 1: Verify the root-cause regression in source

**Files:**
- Verify: `src/engine/account_resolver.py:177-277`
- Verify: `tests/test_account_resolver.py:499-525`

- [X] **Step 1: Verify the resolver recognizes the real sales suffix.**

Confirm `_ACCOUNT_NAME_COST_TYPE_SUFFIXES` removes `（販）` and `_ACCOUNT_SUFFIXES_BY_COLUMN["sales_code"]` accepts `（販）`.

- [X] **Step 2: Run the focused resolver regression.**

Run: `py -3 -m pytest tests/test_account_resolver.py::TestSharedAccountResolver::test_shared_numeric_variant_matches_abbreviated_sales_marker_inside_account_name -q`

Expected: PASS. The source account `5006016260` resolves to the sales building account, not an ambiguous sibling row.

### Task 2: Verify no financial behavior is widened

**Files:**
- Verify: `tests/test_account_resolver.py`
- Verify: `tests/test_headcount_and_export.py`

- [X] **Step 1: Run resolver coverage.**

Run: `py -3 -m pytest tests/test_account_resolver.py -q`

Expected: PASS. Manufacturing, general, and sales mappings remain isolated by `cost_type`.

- [X] **Step 2: Run targeted export/account regressions.**

Run: `py -3 -m pytest tests/test_headcount_and_export.py::TestHubBuilderExport::test_fixed_rows_resolve_facility_accounts_for_general_cost_center tests/test_headcount_and_export.py::TestHubBuilderExport::test_it_system_account_resolves_from_cost_type_when_fact_account_is_zero -q`

Expected: PASS. Facility and system export formulas retain their source-specific account mapping across cost types.

### Task 3: Deliver the corrected runtime

**Files:**
- Modify only after release preflight: `release.json`
- Modify only after release preflight: `installer/MP2027_Manager.iss`
- Create only after release preflight: `docs/handover/releases/<catalog-next-patch>.md`

- [ ] **Step 1: Obtain explicit release/build authority and a clean release worktree.**

Do not edit versions, build, or publish from the current dirty worktree. Follow `docs/handover/release_update_playbook.md` in full.

- [ ] **Step 2: Read the LAN catalog and choose its next patch version.**

Read `release_update/latest.json`; do not infer the version from local artifacts or commit history.

- [ ] **Step 3: Build, health-check, and publish only if explicitly requested.**

Use the HASH_ONLY_LAN process. Do not create keys, signatures, or change existing historical artifacts.

### Task 4: Audit

**Files:**
- Verify: `git diff --check`
- Verify: release health-check outputs, if Task 3 is authorized

- [X] **Step 1: Record source-test evidence and the deployed-version gap.**

The audit must distinguish source correctness from deployment status. A source-test pass alone does not update a user running 0.1.6.
