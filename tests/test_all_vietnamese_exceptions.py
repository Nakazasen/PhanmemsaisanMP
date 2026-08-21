"""Kiểm thử tính toàn vẹn ngôn ngữ tiếng Việt và hướng dẫn xử lý của các thông báo lỗi, ngoại lệ."""
from pathlib import Path
import sqlite3
import pytest

from src.universal_app import _friendly_error_message


def test_account_resolver_exceptions_are_vietnamese():
    src = Path("src/engine/account_resolver.py").read_text(encoding="utf-8")
    forbidden = (
        "Account not found",
        "Ambiguous account",
        "Missing target cost center",
        "Cost center not found",
        "Cost center has no cost_type",
        "Unsupported source for account policy",
        "Missing form_row for source",
        "Unsupported form_row for source",
        "Unsupported description for source",
        "Source account policy has no base-account",
        "Unsupported cost type for account lookup",
        "Missing account key/name",
    )
    for phrase in forbidden:
        assert phrase not in src, f"Found English error phrase in account_resolver.py: {phrase}"


def test_fixed_assets_exceptions_are_vietnamese():
    src = Path("src/parsers/fixed_assets.py").read_text(encoding="utf-8")
    forbidden = (
        "Multiple source workbooks contain equally likely",
        "Missing Q/last-month depreciation",
        "Missing authoritative exchange_rate_usd_vnd",
        "Missing authoritative fiscal_year",
        "Fixed-assets workbook has no recognizable current source sheet",
        "Missing cached formula value at",
        "Unknown fixed-assets Category at",
    )
    for phrase in forbidden:
        assert phrase not in src, f"Found English error phrase in fixed_assets.py: {phrase}"


def test_loader_exceptions_are_vietnamese():
    src = Path("src/db/loader.py").read_text(encoding="utf-8")
    forbidden = (
        "Missing required source directory",
        "Expected docs/MP2027 either next to the app",
    )
    for phrase in forbidden:
        assert phrase not in src, f"Found English error phrase in loader.py: {phrase}"


def test_complete_v1_source_order_writer_exceptions_are_vietnamese():
    src = Path("src/engine/complete_v1_source_order_writer.py").read_text(encoding="utf-8")
    forbidden = (
        "Dynamic source group index ngoài manifest",
        "NNN paperwork có chi phí nhưng thiếu account code",
        "NNN paperwork có chi phí nhưng thiếu mô tả nguồn",
    )
    for phrase in forbidden:
        assert phrase not in src, f"Found mixed/English error phrase in complete_v1_source_order_writer.py: {phrase}"


def test_writers_and_contexts_exceptions_are_vietnamese():
    sys_cost = Path("src/engine/system_cost_writer.py").read_text(encoding="utf-8")
    assert "must not overwrite" not in sys_cost
    assert "Đường dẫn tệp kết quả không được ghi đè" in sys_cost

    admin_writer = Path("src/engine/admin_consumables_writer.py").read_text(encoding="utf-8")
    assert "must not overwrite" not in admin_writer
    assert "Đường dẫn tệp kết quả không được ghi đè" in admin_writer

    cc_ctx = Path("src/engine/cost_center_context.py").read_text(encoding="utf-8")
    assert "requires an explicit cost_center" not in cc_ctx
    assert "yêu cầu chỉ định rõ mã Trung tâm chi phí" in cc_ctx

    out_mode = Path("src/engine/output_mode.py").read_text(encoding="utf-8")
    assert "Unknown output group" not in out_mode
    assert "Nhóm xuất không xác định" in out_mode

    hub_builder = Path("src/engine/hub_builder.py").read_text(encoding="utf-8")
    assert "Exported workbook failed integrity check" not in hub_builder
    assert "Exported workbook has no business rows although DB facts exist" not in hub_builder


def test_hub_account_resolution_error_uses_non_technical_vietnamese_labels():
    hub_builder = Path("src/engine/hub_builder.py").read_text(encoding="utf-8")
    assert "Không thể chuẩn hóa account cố định theo cost type" not in hub_builder
    assert "Không thể chuẩn hóa account NNN theo cost type" not in hub_builder
    assert "Không thể xác định tài khoản phù hợp cho khoản chi cố định của Trung tâm chi phí" in hub_builder
    assert "Không thể xác định tài khoản phù hợp cho khoản chi từ nguồn NNN của Trung tâm chi phí" in hub_builder


def test_allocator_missing_inputs_are_vietnamese():
    src = Path("src/engine/allocator.py").read_text(encoding="utf-8")
    forbidden = (
        "Missing bus allocation input",
        "Provide a valid bus driver count",
        "Missing canonical monthly headcount driver",
        "Missing complete monthly headcount driver",
        "Provide explicit headcount entries",
        "Missing manual event driver",
        "Missing manual distribution driver",
    )
    for phrase in forbidden:
        assert phrase not in src, f"Found English error phrase in allocator.py: {phrase}"


def test_friendly_error_message_always_includes_action_guidance():
    test_cases = [
        "database is locked",
        "Permission denied: 'out.xlsx'",
        "Không tìm thấy mã tài khoản theo từ khóa tra cứu",
        "Tài khoản '5004086291' không có giá trị cột 'ga_code' cho loại chi phí '一般'",
        "Thiếu tham số tỷ giá USD/VND (exchange_rate_usd_vnd) trong cơ sở dữ liệu hệ thống.",
        "Unknown unhandled exception in background thread",
    ]
    for case in test_cases:
        msg = _friendly_error_message(case)
        assert "Cách xử lý:" in msg or "cách xử lý:" in msg.lower(), f"Missing action guidance for case: {case}"


def test_account_resolver_exceptions_include_action_guidance():
    from src.engine.account_resolver import AccountResolutionError, resolve_account_code_for_connection

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE dim_cost_centers (code TEXT PRIMARY KEY, cost_type TEXT)")
    conn.execute("CREATE TABLE dim_accounts (code INT, name_jp TEXT, name_vn TEXT, group_name TEXT, group_vn TEXT, mfg_code INT, ga_code INT, sales_code INT)")
    conn.execute("INSERT INTO dim_cost_centers VALUES ('1412000040', '製造')")
    conn.commit()

    with pytest.raises(AccountResolutionError) as exc_info:
        resolve_account_code_for_connection(conn, "1412000040", "non_existent_account")

    err_str = str(exc_info.value)
    assert "Không tìm thấy" in err_str
    assert "Cách xử lý:" in err_str
    conn.close()


def test_migrations_exceptions_are_vietnamese():
    src = Path("src/db/migrations.py").read_text(encoding="utf-8")
    forbidden = (
        "Legacy dim_cost_centers cannot be migrated safely",
        "Legacy fact_allocation_log cannot be migrated safely",
        "Database schema v",
        "newer than supported",
        "Schema migration failed; no partial change was committed",
        "foreign-key validation found",
    )
    for phrase in forbidden:
        assert phrase not in src, f"Found English error phrase in migrations.py: {phrase}"
    assert "Nguyên nhân:" in src
    assert "Cách xử lý:" in src


def test_migrations_unhandled_failure_is_vietnamese_and_does_not_leak_english_driver_error(monkeypatch):
    import src.db.migrations as migrations

    def _failing_rebuild(conn):
        raise RuntimeError("English database driver failure: disk I/O error or permission denied")

    monkeypatch.setattr(migrations, "_rebuild_legacy_cost_centers", _failing_rebuild)

    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE dim_cost_centers (code INT PRIMARY KEY)")  # triggers legacy rebuild

    with pytest.raises(migrations.SchemaCompatibilityError) as exc_info:
        migrations.run_migrations(conn)

    err_str = str(exc_info.value)
    assert "English database driver failure" not in err_str, "English raw exception leaked to user!"
    assert "Chuyển đổi lược đồ cơ sở dữ liệu thất bại" in err_str
    assert "Nguyên nhân:" in err_str
    assert "Cách xử lý:" in err_str
    conn.close()


def test_content_packs_exceptions_have_cause_and_action_guidance():
    src = Path("src/services/content_packs.py").read_text(encoding="utf-8")
    assert "Nguyên nhân:" in src
    assert "Cách xử lý:" in src


def test_headcount_time_plan_errors_have_cause_and_action_guidance():
    src = Path("src/parsers/headcount_time_plan.py").read_text(encoding="utf-8")
    assert "Nguyên nhân:" in src
    assert "Cách xử lý:" in src


def test_fiscal_periods_exceptions_have_cause_and_action_guidance():
    src = Path("src/utils/fiscal_periods.py").read_text(encoding="utf-8")
    assert "Nguyên nhân:" in src
    assert "Cách xử lý:" in src


def test_update_security_exceptions_have_cause_and_action_guidance():
    src = Path("src/services/update_security.py").read_text(encoding="utf-8")
    assert "Nguyên nhân:" in src
    assert "Cách xử lý:" in src


def test_update_security_all_exception_branches_produce_cause_and_action():
    from src.services.update_security import (
        ArtifactVerificationError,
        validate_manifest,
        _safe_relative_path,
        safe_extract_zip,
    )

    # 1. Invalid schema
    with pytest.raises(ArtifactVerificationError) as exc_info:
        validate_manifest({"schema": 999}, artifact_kind="content")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 2. Missing required fields
    with pytest.raises(ArtifactVerificationError) as exc_info:
        validate_manifest({"schema": 1}, artifact_kind="content")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 3. Wrong artifact kind
    valid_base = {
        "schema": 1,
        "kind": "application",
        "id": "app",
        "version": "1.0.0",
        "min_app_version": "1.0.0",
        "files": [{"path": "a.txt", "sha256": "0" * 64, "size": 10}],
    }
    with pytest.raises(ArtifactVerificationError) as exc_info:
        validate_manifest(valid_base, artifact_kind="content")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 4. Empty strings in id/version
    bad_id = dict(valid_base, kind="content", id=" ")
    with pytest.raises(ArtifactVerificationError) as exc_info:
        validate_manifest(bad_id, artifact_kind="content")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 5. Empty files
    bad_files = dict(valid_base, kind="content", files=[])
    with pytest.raises(ArtifactVerificationError) as exc_info:
        validate_manifest(bad_files, artifact_kind="content")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 6. Invalid entry keys
    bad_entry = dict(valid_base, kind="content", files=[{"path": "a.txt"}])
    with pytest.raises(ArtifactVerificationError) as exc_info:
        validate_manifest(bad_entry, artifact_kind="content")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 7. Duplicate path in manifest
    dup_files = dict(
        valid_base,
        kind="content",
        files=[
            {"path": "a.txt", "sha256": "0" * 64, "size": 10},
            {"path": "a.txt", "sha256": "0" * 64, "size": 10},
        ],
    )
    with pytest.raises(ArtifactVerificationError) as exc_info:
        validate_manifest(dup_files, artifact_kind="content")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 8. Invalid sha256
    bad_sha = dict(
        valid_base,
        kind="content",
        files=[{"path": "a.txt", "sha256": "invalid_hex", "size": 10}],
    )
    with pytest.raises(ArtifactVerificationError) as exc_info:
        validate_manifest(bad_sha, artifact_kind="content")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 9. Invalid size
    bad_size = dict(
        valid_base,
        kind="content",
        files=[{"path": "a.txt", "sha256": "0" * 64, "size": -5}],
    )
    with pytest.raises(ArtifactVerificationError) as exc_info:
        validate_manifest(bad_size, artifact_kind="content")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 10. Unsafe relative path
    with pytest.raises(ArtifactVerificationError) as exc_info:
        _safe_relative_path("../escape.txt")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 11. Hidden path
    with pytest.raises(ArtifactVerificationError) as exc_info:
        _safe_relative_path(".hidden/file.txt")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 12. Forbidden executable in content pack
    with pytest.raises(ArtifactVerificationError) as exc_info:
        _safe_relative_path("payload.exe", allow_executable=False)
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)

    # 13. safe_extract_zip unsupported kind
    with pytest.raises(ArtifactVerificationError) as exc_info:
        safe_extract_zip("dummy.zip", "target", artifact_kind="unsupported_kind")
    assert "Nguyên nhân:" in str(exc_info.value)
    assert "Cách xử lý:" in str(exc_info.value)


def test_headcount_time_plan_nfkc_unicode_normalization_department_match():
    from src.parsers.headcount_time_plan import _resolve_lookup_identity

    lookup_rows = [
        ("1412000040", "ABC製造課", "Bộ phận sản xuất ABC"),
    ]

    # Full-width Japanese letters: ＡＢＣ製造課 vs ABC製造課
    status, jp_name, vn_name = _resolve_lookup_identity("1412000040", "ＡＢＣ製造課", lookup_rows)
    assert status == "matched"
    assert jp_name == "ABC製造課"
    assert vn_name == "Bộ phận sản xuất ABC"

    # Full-width digits: １４１２００００４０ vs 1412000040
    status, jp_name, vn_name = _resolve_lookup_identity("１４１２００００４０", "ABC製造課", lookup_rows)
    assert status == "matched"
    assert jp_name == "ABC製造課"
