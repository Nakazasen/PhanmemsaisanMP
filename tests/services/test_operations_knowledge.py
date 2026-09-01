"""Kiểm thử đơn vị cho mô hình tri thức vận hành (Operations Knowledge Service).

Kiểm tra:
1. Tính bất biến (frozen=True) của KnowledgeEntry và GuidancePresentation.
2. Validation bắt buộc 100% đủ 3 ngôn ngữ: 'vi', 'en', 'ja'.
3. Validation đầy đủ các trường hướng dẫn: title, what_happened, why_it_happened, what_to_do,
   confidence_label, evidence_label, technical_details_label.
4. Từ chối các bản dịch thiếu trường, rỗng, sai ngôn ngữ, hoặc chứa raw traceback.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
import pytest

from src.services.operations_knowledge import (
    ENTRY_BLOCKED_OUTPUT_FILE_LOCK,
    ENTRY_MISSING_STAFFING_BASELINE,
    ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
    ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK,
    ERROR_CODE_MISSING_STAFFING_BASELINE,
    ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
    SUPPORTED_LANGUAGES,
    GuidancePresentation,
    KnowledgeEntry,
    get_approved_knowledge_entries,
    get_knowledge_entry,
    is_blocked_output_file_lock_match,
    is_missing_staffing_baseline_match,
    is_preflight_source_validation_failure_match,
)


def _make_valid_sample_presentation(lang: str = "vi") -> GuidancePresentation:
    """Tạo một đối tượng GuidancePresentation mẫu hợp lệ theo ngôn ngữ."""
    if lang == "vi":
        return GuidancePresentation(
            language="vi",
            title="Tệp Excel đầu ra đang bị khóa",
            what_happened="Không thể ghi đè báo cáo kết quả vì một ứng dụng khác đang mở tệp.",
            why_it_happened="Windows đang khóa quyền ghi vào tệp Excel trong thư mục kết quả.",
            what_to_do=(
                "Đóng tất cả các cửa sổ Excel đang mở tệp kết quả.",
                "Đóng cửa sổ File Explorer tại thư mục kết quả.",
                "Bấm nút Chạy lại để tiếp tục.",
            ),
            confidence_label="Đã xác nhận",
            evidence_label="Bằng chứng từ nhật ký",
            technical_details_label="Chi tiết kỹ thuật bổ sung",
        )
    elif lang == "en":
        return GuidancePresentation(
            language="en",
            title="Output Excel file is locked",
            what_happened="Cannot overwrite output report because another application is holding a file lock.",
            why_it_happened="Windows has locked write access to the output workbook.",
            what_to_do=(
                "Close all open Excel windows displaying output workbooks.",
                "Close File Explorer windows browsing the output folder.",
                "Click Rerun to proceed.",
            ),
            confidence_label="Confirmed",
            evidence_label="Log evidence",
            technical_details_label="Supplementary technical details",
        )
    elif lang == "ja":
        return GuidancePresentation(
            language="ja",
            title="出力Excelファイルがロックされています",
            what_happened="他のアプリケーションがファイルを開いているため、出力レポートを上書きできません。",
            why_it_happened="Windowsによって出力フォルダー内のExcelファイルへの書き込みがロックされています。",
            what_to_do=(
                "対象のExcelファイルをすべて閉じてください。",
                "出力フォルダーを開いているエクスプローラーを閉じてください。",
                "再実行ボタンを押して処理を継続してください。",
            ),
            confidence_label="確認済み",
            evidence_label="ログの根拠",
            technical_details_label="追加の技術詳細",
        )
    else:
        raise ValueError(f"Ngôn ngữ test không hợp lệ: {lang}")


def _make_valid_sample_knowledge_entry(error_code: str = "sample_error") -> KnowledgeEntry:
    """Tạo một KnowledgeEntry mẫu hợp lệ có đủ 3 bản dịch vi/en/ja."""
    return KnowledgeEntry(
        error_code=error_code,
        conditions={"stage": "publication", "error_type": "OutputPublicationLockedError"},
        translations={
            "vi": _make_valid_sample_presentation("vi"),
            "en": _make_valid_sample_presentation("en"),
            "ja": _make_valid_sample_presentation("ja"),
        },
        evidence_requirements=("stage_evidence", "failure_traceback"),
        review_status="approved",
        owner="Planning Operations Team",
    )


# ---------------------------------------------------------------------------
# Test: GuidancePresentation
# ---------------------------------------------------------------------------

def test_guidance_presentation_instantiation_and_immutability() -> None:
    """Xác thực GuidancePresentation được khởi tạo đúng và đóng băng (frozen=True)."""
    pres = _make_valid_sample_presentation("vi")

    assert pres.language == "vi"
    assert pres.title == "Tệp Excel đầu ra đang bị khóa"
    assert len(pres.what_to_do) == 3

    with pytest.raises(FrozenInstanceError):
        pres.title = "Tiêu đề mới"  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        pres.language = "en"  # type: ignore[misc]


def test_guidance_presentation_rejects_unsupported_language() -> None:
    """Xác thực từ chối các mã ngôn ngữ không nằm trong SUPPORTED_LANGUAGES."""
    for invalid_lang in ("fr", "de", "zh", "", None):
        with pytest.raises(ValueError, match="không được hỗ trợ"):
            GuidancePresentation(
                language=invalid_lang,  # type: ignore[arg-type]
                title="Title",
                what_happened="Happened",
                why_it_happened="Why",
                what_to_do=("Step 1",),
                confidence_label="Confidence",
                evidence_label="Evidence",
                technical_details_label="Technical",
            )


def test_guidance_presentation_rejects_empty_or_whitespace_fields() -> None:
    """Xác thực từ chối các trường văn bản bị để trống hoặc chỉ có khoảng trắng."""
    valid_kwargs = {
        "language": "vi",
        "title": "Tiêu đề",
        "what_happened": "Chuyện xảy ra",
        "why_it_happened": "Lý do",
        "what_to_do": ("Bước 1",),
        "confidence_label": "Độ tin cậy",
        "evidence_label": "Bằng chứng",
        "technical_details_label": "Chi tiết kỹ thuật",
    }

    for field_name in (
        "title",
        "what_happened",
        "why_it_happened",
        "confidence_label",
        "evidence_label",
        "technical_details_label",
    ):
        bad_kwargs = dict(valid_kwargs)
        bad_kwargs[field_name] = "   "
        with pytest.raises(ValueError, match=f"Trường '{field_name}'"):
            GuidancePresentation(**bad_kwargs)


def test_guidance_presentation_rejects_empty_what_to_do() -> None:
    """Xác thực từ chối when what_to_do bị rỗng hoặc có bước rỗng."""
    with pytest.raises(ValueError, match="what_to_do"):
        GuidancePresentation(
            language="vi",
            title="Title",
            what_happened="Happened",
            why_it_happened="Why",
            what_to_do=(),
            confidence_label="Confidence",
            evidence_label="Evidence",
            technical_details_label="Technical",
        )

    with pytest.raises(ValueError, match="Bước hành động thứ 2"):
        GuidancePresentation(
            language="vi",
            title="Title",
            what_happened="Happened",
            why_it_happened="Why",
            what_to_do=("Bước 1", "   ", "Bước 3"),
            confidence_label="Confidence",
            evidence_label="Evidence",
            technical_details_label="Technical",
        )


def test_guidance_presentation_rejects_raw_traceback_in_primary_fields() -> None:
    """Xác thực từ chối khi phát hiện raw traceback tràn vào nội dung hướng dẫn chính."""
    raw_tb = (
        "Traceback (most recent call last):\n"
        '  File "test.py", line 1, in <module>\n'
        "PermissionError: Access is denied"
    )

    with pytest.raises(ValueError, match="chứa dấu vết ngoại lệ kỹ thuật thô"):
        GuidancePresentation(
            language="vi",
            title="Lỗi kỹ thuật",
            what_happened=raw_tb,
            why_it_happened="Lý do",
            what_to_do=("Bước 1",),
            confidence_label="Độ tin cậy",
            evidence_label="Bằng chứng",
            technical_details_label="Chi tiết kỹ thuật",
        )


@pytest.mark.parametrize(
    ("field_name", "technical_text"),
    (
        ("title", "OutputPublicationLockedError"),
        ("why_it_happened", '"pipeline_stage_evidence": "FAIL"'),
        ("what_to_do", ("Open the report for OutputPublicationLockedError",)),
        ("what_happened", "[14:02:41] pipeline stage failed"),
    ),
)
def test_guidance_presentation_rejects_raw_exception_and_internal_log_content(
    field_name: str,
    technical_text: str | tuple[str, ...],
) -> None:
    """Primary guidance cannot expose exception names, JSON keys, or raw log content."""
    valid_kwargs = {
        "language": "en",
        "title": "Cannot save the output report",
        "what_happened": "The report was not saved.",
        "why_it_happened": "Another application is using the output file.",
        "what_to_do": ("Close the file, then try again.",),
        "confidence_label": "Confirmed",
        "evidence_label": "Evidence",
        "technical_details_label": "Technical details",
    }
    valid_kwargs[field_name] = technical_text

    with pytest.raises(ValueError):
        GuidancePresentation(**valid_kwargs)


# ---------------------------------------------------------------------------
# Test: KnowledgeEntry
# ---------------------------------------------------------------------------

def test_knowledge_entry_instantiation_and_immutability() -> None:
    """Xác thực KnowledgeEntry được khởi tạo đúng và bảo toàn tính bất biến."""
    entry = _make_valid_sample_knowledge_entry("test_error")

    assert entry.error_code == "test_error"
    assert entry.review_status == "approved"
    assert entry.owner == "Planning Operations Team"
    assert len(entry.translations) == 3
    assert set(entry.translations.keys()) == set(SUPPORTED_LANGUAGES)

    # Thử thay đổi thuộc tính cấp 1 -> FrozenInstanceError
    with pytest.raises(FrozenInstanceError):
        entry.error_code = "another_code"  # type: ignore[misc]

    # Thử thay đổi dictionary bên trong -> TypeError từ MappingProxyType
    with pytest.raises(TypeError):
        entry.conditions["new_key"] = "val"  # type: ignore[index]

    with pytest.raises(TypeError):
        entry.translations["vi"] = _make_valid_sample_presentation("vi")  # type: ignore[index]


def test_knowledge_entry_requires_all_three_languages() -> None:
    """Xác thực bắt buộc có đủ cả 3 ngôn ngữ 'vi', 'en', 'ja'; từ chối nếu thiếu bất kỳ ngôn ngữ nào."""
    valid_trans = {
        "vi": _make_valid_sample_presentation("vi"),
        "en": _make_valid_sample_presentation("en"),
        "ja": _make_valid_sample_presentation("ja"),
    }

    # Thiếu 'ja'
    missing_ja = dict(valid_trans)
    del missing_ja["ja"]
    with pytest.raises(ValueError, match="thiếu bản dịch bắt buộc cho ngôn ngữ 'ja'"):
        KnowledgeEntry(
            error_code="err_missing_ja",
            conditions={},
            translations=missing_ja,
            evidence_requirements=("stage_evidence",),
        )

    # Thiếu 'en'
    missing_en = dict(valid_trans)
    del missing_en["en"]
    with pytest.raises(ValueError, match="thiếu bản dịch bắt buộc cho ngôn ngữ 'en'"):
        KnowledgeEntry(
            error_code="err_missing_en",
            conditions={},
            translations=missing_en,
            evidence_requirements=("stage_evidence",),
        )

    # Thiếu 'vi'
    missing_vi = dict(valid_trans)
    del missing_vi["vi"]
    with pytest.raises(ValueError, match="thiếu bản dịch bắt buộc cho ngôn ngữ 'vi'"):
        KnowledgeEntry(
            error_code="err_missing_vi",
            conditions={},
            translations=missing_vi,
            evidence_requirements=("stage_evidence",),
        )


def test_knowledge_entry_rejects_mismatched_language_keys() -> None:
    """Xác thực từ chối khi khóa ngôn ngữ trong dict không khớp với language của GuidancePresentation."""
    mismatched_trans = {
        "vi": _make_valid_sample_presentation("en"),  # Gán đối tượng en vào khóa vi
        "en": _make_valid_sample_presentation("en"),
        "ja": _make_valid_sample_presentation("ja"),
    }

    with pytest.raises(ValueError, match="không khớp"):
        KnowledgeEntry(
            error_code="err_mismatch",
            conditions={},
            translations=mismatched_trans,
            evidence_requirements=("stage_evidence",),
        )


def test_knowledge_entry_rejects_invalid_review_status() -> None:
    """Xác thực từ chối các trạng thái kiểm duyệt không hợp lệ."""
    with pytest.raises(ValueError, match="Trạng thái kiểm duyệt"):
        KnowledgeEntry(
            error_code="err_invalid_status",
            conditions={},
            translations={
                "vi": _make_valid_sample_presentation("vi"),
                "en": _make_valid_sample_presentation("en"),
                "ja": _make_valid_sample_presentation("ja"),
            },
            evidence_requirements=("stage_evidence",),
            review_status="unreviewed_custom_status",
        )


def test_knowledge_entry_rejects_empty_error_code_or_requirements() -> None:
    """Xác thực từ chối khi thiếu error_code hoặc evidence_requirements."""
    valid_trans = {
        "vi": _make_valid_sample_presentation("vi"),
        "en": _make_valid_sample_presentation("en"),
        "ja": _make_valid_sample_presentation("ja"),
    }

    with pytest.raises(ValueError, match="Mã lỗi 'error_code' không được để trống"):
        KnowledgeEntry(
            error_code="   ",
            conditions={},
            translations=valid_trans,
            evidence_requirements=("stage_evidence",),
        )

    with pytest.raises(ValueError, match="evidence_requirements"):
        KnowledgeEntry(
            error_code="err_no_req",
            conditions={},
            translations=valid_trans,
            evidence_requirements=(),
        )


# ---------------------------------------------------------------------------
# T011: Tests for Missing Staffing Baseline Knowledge Entry & Matcher
# ---------------------------------------------------------------------------

def test_missing_staffing_baseline_entry_structure_and_translations() -> None:
    """Xác thực cấu trúc, trạng thái duyệt và bản dịch 3 ngôn ngữ của ENTRY_MISSING_STAFFING_BASELINE."""
    entry = ENTRY_MISSING_STAFFING_BASELINE

    assert entry.error_code == ERROR_CODE_MISSING_STAFFING_BASELINE
    assert entry.review_status == "approved"
    assert entry.owner == "Planning Operations Team"
    assert entry.evidence_requirements == ("stage_evidence", "failure_traceback")

    # Kiểm tra cả 3 ngôn ngữ
    for lang in ("vi", "en", "ja"):
        pres = entry.translations[lang]
        assert pres.language == lang
        assert len(pres.title) > 0
        assert len(pres.what_happened) > 0
        assert len(pres.why_it_happened) > 0
        assert len(pres.what_to_do) >= 3
        assert len(pres.confidence_label) > 0
        assert len(pres.evidence_label) > 0
        assert len(pres.technical_details_label) > 0

        # Khẳng định không có raw exception / JSON / traceback
        assert "Traceback" not in pres.what_happened
        assert "Error" not in pres.title
        assert "Exception" not in pres.why_it_happened
        for step in pres.what_to_do:
            assert "{" not in step
            assert "}" not in step

    assert "Nhập nhân sự thủ công" in entry.translations["vi"].what_to_do[0]
    assert "Manual staffing input" in entry.translations["en"].what_to_do[0]
    assert "手動人員入力" in entry.translations["ja"].what_to_do[0]


def test_missing_staffing_baseline_positive_matches() -> None:
    """Xác thực match confirmed khi có đủ bằng chứng thiếu baseline nhân sự."""
    stage_payload_vi = {
        "status": "FAILED",
        "stages": [
            {
                "name": "validate_staffing",
                "status": "FAIL",
                "error_summary": "Phòng 1412000086: chưa có Tổng số người tháng 03/2026.",
            }
        ],
    }
    assert is_missing_staffing_baseline_match(stage_payload_vi) is True

    stage_payload_en = {
        "status": "FAILED",
        "stages": [
            {
                "name": "validate_staffing",
                "status": "FAIL",
                "error_summary": "Missing staffing baseline headcount for Cost Center 1412000086.",
            }
        ],
    }
    assert is_missing_staffing_baseline_match(stage_payload_en) is True


def test_missing_staffing_baseline_negative_matches() -> None:
    """Xác thực từ chối match khi thiếu bằng chứng, hoặc là lỗi khác."""
    # 1. Payload None hoặc rỗng
    assert is_missing_staffing_baseline_match(None) is False
    assert is_missing_staffing_baseline_match({}) is False

    # 2. Chỉ có error summary, không có bước validate_staffing thất bại.
    assert is_missing_staffing_baseline_match(
        {"status": "FAILED", "stages": []},
        error_summary="Missing staffing baseline headcount",
    ) is False

    # 3. Đúng câu lỗi nhưng sai bước chạy.
    assert is_missing_staffing_baseline_match(
        {
            "status": "FAILED",
            "stages": [
                {
                    "name": "preflight",
                    "status": "FAIL",
                    "error_summary": "Missing staffing baseline headcount",
                }
            ],
        }
    ) is False

    # 4. Đúng bước nhưng không phải thiếu baseline.
    assert is_missing_staffing_baseline_match(
        {
            "status": "FAILED",
            "stages": [
                {
                    "name": "validate_staffing",
                    "status": "FAIL",
                    "error_summary": "Phát hiện dòng nhân sự bị trùng lặp.",
                }
            ],
        }
    ) is False


def test_get_approved_knowledge_entries_and_lookup() -> None:
    """Xác thực registry các entry đã duyệt và hàm tra cứu get_knowledge_entry."""
    entries = get_approved_knowledge_entries()
    assert len(entries) >= 3
    assert ENTRY_MISSING_STAFFING_BASELINE in entries
    assert ENTRY_BLOCKED_OUTPUT_FILE_LOCK in entries
    assert ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE in entries

    found_staffing = get_knowledge_entry(ERROR_CODE_MISSING_STAFFING_BASELINE)
    assert found_staffing is not None
    assert found_staffing.error_code == ERROR_CODE_MISSING_STAFFING_BASELINE

    found_lock = get_knowledge_entry(ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK)
    assert found_lock is not None
    assert found_lock.error_code == ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK

    found_source = get_knowledge_entry(ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE)
    assert found_source is not None
    assert found_source.error_code == ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE

    not_found = get_knowledge_entry("non_existent_unknown_error")
    assert not_found is None


# ---------------------------------------------------------------------------
# T012: Tests for Blocked Output File Lock Knowledge Entry & Matcher
# ---------------------------------------------------------------------------

def test_blocked_output_file_lock_entry_structure_and_translations() -> None:
    """Xác thực cấu trúc, trạng thái duyệt và bản dịch 3 ngôn ngữ của ENTRY_BLOCKED_OUTPUT_FILE_LOCK."""
    entry = ENTRY_BLOCKED_OUTPUT_FILE_LOCK

    assert entry.error_code == ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK
    assert entry.review_status == "approved"
    assert entry.owner == "Planning Operations Team"
    assert "stage_evidence" in entry.evidence_requirements
    assert "failure_traceback" in entry.evidence_requirements

    # Kiểm tra cả 3 ngôn ngữ
    for lang in ("vi", "en", "ja"):
        pres = entry.translations[lang]
        assert pres.language == lang
        assert len(pres.title) > 0
        assert len(pres.what_happened) > 0
        assert len(pres.why_it_happened) > 0
        assert len(pres.what_to_do) >= 3
        assert len(pres.confidence_label) > 0
        assert len(pres.evidence_label) > 0
        assert len(pres.technical_details_label) > 0

        # Khẳng định không có raw exception / JSON / traceback trong nội dung chính
        assert "Traceback" not in pres.what_happened
        assert "Error" not in pres.title
        assert "Exception" not in pres.why_it_happened
        for step in pres.what_to_do:
            assert "{" not in step
            assert "}" not in step


def test_blocked_output_file_lock_positive_matches() -> None:
    """Xác thực match confirmed khi có publication FAIL + dấu hiệu khóa file."""
    stage_payload_valid = {
        "status": "FAILED",
        "stages": [
            {"name": "preflight", "status": "PASS"},
            {"name": "allocation", "status": "PASS"},
            {"name": "publication", "status": "FAIL"},
        ],
    }

    # 1. OutputPublicationLockedError trong traceback
    tb_1 = (
        "OutputPublicationLockedError: Không thể cập nhật thư mục kết quả vì Windows đang khóa tệp.\n"
        "PermissionError: [WinError 5] Access is denied"
    )
    assert is_blocked_output_file_lock_match(stage_payload_valid, traceback_text=tb_1) is True

    # 2. PermissionError [WinError 5] trong traceback
    tb_2 = "PermissionError: [WinError 5] Access is denied: 'D:/OUTPUT/MP_CC_1412000040.xlsx'"
    assert is_blocked_output_file_lock_match(stage_payload_valid, traceback_text=tb_2) is True

    # 3. [WinError 32] (process cannot access file because being used by another process)
    tb_3 = (
        "PermissionError: [WinError 32] The process cannot access "
        "D:/OUTPUT/MP_CC_1412000040.xlsx because it is being used by another process"
    )
    assert is_blocked_output_file_lock_match(stage_payload_valid, traceback_text=tb_3) is True

    # 4. Tiếng Việt trong error_summary
    assert is_blocked_output_file_lock_match(
        stage_payload_valid,
        error_summary="Không thể lưu tệp kết quả vì Windows đang khóa file",
    ) is True


def test_blocked_output_file_lock_negative_matches() -> None:
    """Xác thực từ chối match khi thiếu publication FAIL hoặc không có dấu hiệu khóa file."""
    # 1. Lỗi ở giai đoạn khác (allocation FAIL), dù traceback có PermissionError
    stage_allocation_fail = {
        "status": "FAILED",
        "stages": [
            {"name": "preflight", "status": "PASS"},
            {"name": "allocation", "status": "FAIL"},
            {"name": "publication", "status": "PENDING"},
        ],
    }
    tb_perm = "PermissionError: [WinError 5] Access is denied"
    assert is_blocked_output_file_lock_match(stage_allocation_fail, traceback_text=tb_perm) is False

    # 2. Giai đoạn publication FAIL nhưng do lỗi khác (không có dấu hiệu khóa file)
    stage_pub_other_error = {
        "status": "FAILED",
        "stages": [
            {"name": "publication", "status": "FAIL"},
        ],
    }
    tb_other = "ZeroDivisionError: division by zero in formula computation"
    assert is_blocked_output_file_lock_match(stage_pub_other_error, traceback_text=tb_other) is False

    # 3. Payload None hoặc rỗng dù traceback có OutputPublicationLockedError
    assert is_blocked_output_file_lock_match(None, traceback_text=tb_perm) is False
    assert is_blocked_output_file_lock_match({}, traceback_text=tb_perm) is False

    # 4. Publication PASS nhưng text có nhắc đến lock
    stage_pub_pass = {
        "status": "SUCCEEDED",
        "stages": [
            {"name": "publication", "status": "PASS"},
        ],
    }
    assert is_blocked_output_file_lock_match(stage_pub_pass, traceback_text=tb_perm) is False

    # 5. Từ ngữ đơn lẻ ("Excel", "output", "file", "lock") trong ngữ cảnh không liên quan
    generic_text = "Checking Excel output template file locking configuration"
    assert is_blocked_output_file_lock_match(stage_pub_other_error, error_summary=generic_text) is False

    # 6. Generic permission errors are not enough without a result-workbook or
    # destination signal, even when publication is the failed stage.
    assert is_blocked_output_file_lock_match(
        stage_pub_other_error,
        traceback_text="PermissionError: [WinError 5] Access is denied",
    ) is False


# ---------------------------------------------------------------------------
# T013: Tests for Preflight Source Validation Failure Knowledge Entry & Matcher
# ---------------------------------------------------------------------------

def test_preflight_source_validation_failure_entry_structure_and_translations() -> None:
    """Xác thực cấu trúc, trạng thái duyệt và bản dịch 3 ngôn ngữ của ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE."""
    entry = ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE

    assert entry.error_code == ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE
    assert entry.review_status == "approved"
    assert entry.owner == "Planning Operations Team"
    assert "preflight_report" in entry.evidence_requirements

    # Kiểm tra cả 3 ngôn ngữ
    for lang in ("vi", "en", "ja"):
        pres = entry.translations[lang]
        assert pres.language == lang
        assert len(pres.title) > 0
        assert len(pres.what_happened) > 0
        assert len(pres.why_it_happened) > 0
        assert len(pres.what_to_do) >= 3
        assert len(pres.confidence_label) > 0
        assert len(pres.evidence_label) > 0
        assert len(pres.technical_details_label) > 0

        # Khẳng định không có raw exception / JSON / traceback trong nội dung chính
        assert "Traceback" not in pres.what_happened
        assert "Error" not in pres.title
        assert "Exception" not in pres.why_it_happened
        for step in pres.what_to_do:
            assert "{" not in step
            assert "}" not in step


def test_preflight_source_validation_failure_positive_matches() -> None:
    """Xác thực match confirmed khi preflight ok=False có BLOCKING issue đúng schema."""
    # 1. Khớp từ issue chuẩn với selected_path, reason, required_action
    preflight_1 = {
        "ok": False,
        "fiscal_year": 2028,
        "issues": [
            {
                "category": "facility",
                "selected_path": "Facility_2028.xlsx",
                "detected_fiscal_year": 2028,
                "expected_fiscal_year": 2028,
                "status": "FAILED",
                "code": "SOURCE_VALIDATION_FAILED",
                "severity": "BLOCKING",
                "reason": "Cấu trúc cột trong workbook Facilities không hợp lệ: thiếu cột 'Tên thiết bị'",
                "required_action": "Sửa workbook nguồn rồi kiểm tra lại.",
            }
        ],
    }
    assert is_preflight_source_validation_failure_match(preflight_1) is True

def test_preflight_source_validation_failure_negative_matches() -> None:
    """Xác thực từ chối match khi preflight thành công, chỉ SOURCE_SKIPPED, thiếu trường hoặc lỗi baseline."""
    # 1. Preflight thành công (ok=True)
    assert is_preflight_source_validation_failure_match({"ok": True, "issues": []}) is False

    # 2. Toàn bộ issues chỉ là SOURCE_SKIPPED (non-blocking)
    preflight_skipped = {
        "ok": False,
        "issues": [
            {
                "category": "facility",
                "selected_path": "Facility_2028.xlsx",
                "severity": "SOURCE_SKIPPED",
                "reason": "Tệp bị bỏ qua do người dùng không chọn",
                "required_action": "Chọn lại tệp nếu cần.",
            }
        ],
    }
    assert is_preflight_source_validation_failure_match(preflight_skipped) is False

    # 3. BLOCKING issue nhưng thiếu selected_path / path
    preflight_no_path = {
        "ok": False,
        "issues": [
            {
                "category": "facility",
                "severity": "BLOCKING",
                "reason": "Thiếu dữ liệu",
                "required_action": "Kiểm tra lại",
            }
        ],
    }
    assert is_preflight_source_validation_failure_match(preflight_no_path) is False

    # 4. BLOCKING issue nhưng thiếu reason hoặc required_action
    preflight_no_reason = {
        "ok": False,
        "issues": [
            {
                "category": "facility",
                "selected_path": "Facility_2028.xlsx",
                "severity": "BLOCKING",
                "reason": "",
                "required_action": "Sửa lại file",
            }
        ],
    }
    assert is_preflight_source_validation_failure_match(preflight_no_reason) is False

    # 5. Không được chấp nhận alias cũ path/action: báo cáo thật chỉ phát
    # selected_path/required_action.
    assert is_preflight_source_validation_failure_match(
        {
            "ok": False,
            "issues": [
                {
                    "category": "fixed_assets",
                    "path": "docs/MP2027/Fixed_Assets.xlsx",
                    "status": "FAILED",
                    "code": "SOURCE_VALIDATION_FAILED",
                    "severity": "BLOCKING",
                    "reason": "Không tìm thấy sheet bắt buộc.",
                    "action": "Kiểm tra lại tên sheet.",
                }
            ],
        }
    ) is False

    # 6. BLOCKING row thiếu status/code/category thực tế không phải bằng chứng
    # source-validation đầy đủ.
    assert is_preflight_source_validation_failure_match(
        {
            "ok": False,
            "issues": [
                {
                    "selected_path": "Facility_2028.xlsx",
                    "severity": "BLOCKING",
                    "reason": "Thiếu dữ liệu",
                    "required_action": "Kiểm tra lại",
                }
            ],
        }
    ) is False

    # 7. Issue là lỗi thiếu baseline nhân sự (phải được xử lý bởi missing_staffing_baseline)
    preflight_staffing_baseline = {
        "ok": False,
        "issues": [
            {
                "category": "headcount",
                "selected_path": "headcount_manual.csv",
                "code": "MISSING_BASELINE",
                "status": "FAILED",
                "severity": "BLOCKING",
                "reason": "Thiếu dữ liệu nhân sự baseline tháng 202703",
                "required_action": "Bổ sung baseline tháng 03",
            }
        ],
    }
    assert is_preflight_source_validation_failure_match(preflight_staffing_baseline) is False

    # 8. Payload None hoặc rỗng
    assert is_preflight_source_validation_failure_match(None) is False
    assert is_preflight_source_validation_failure_match({}) is False


# ---------------------------------------------------------------------------
# T016: Multilingual Presentation Contract Test for Knowledge Entries
# ---------------------------------------------------------------------------

def test_knowledge_entries_multilingual_presentation_contract() -> None:
    """Kiểm tra hợp đồng trình bày đa ngôn ngữ tĩnh cho toàn bộ mục tri thức đã phê duyệt."""
    entries = get_approved_knowledge_entries()
    assert len(entries) >= 3

    for entry in entries:
        assert entry.review_status == "approved"
        assert len(entry.error_code) > 0
        assert len(entry.evidence_requirements) > 0

        # Bắt buộc có đủ 3 ngôn ngữ
        for lang in ("vi", "en", "ja"):
            assert lang in entry.translations
            pres = entry.translations[lang]
            assert pres.language == lang

            # 7 trường bắt buộc không được rỗng
            assert len(pres.title.strip()) > 0
            assert len(pres.what_happened.strip()) > 0
            assert len(pres.why_it_happened.strip()) > 0
            assert len(pres.what_to_do) >= 3
            for step in pres.what_to_do:
                assert len(step.strip()) > 0
            assert len(pres.confidence_label.strip()) > 0
            assert len(pres.evidence_label.strip()) > 0
            assert len(pres.technical_details_label.strip()) > 0

            # Khẳng định không chứa forbidden tokens trong nội dung hiển thị chính
            for text_val in (
                pres.title,
                pres.what_happened,
                pres.why_it_happened,
                *pres.what_to_do,
            ):
                assert "Traceback" not in text_val
                assert "Error" not in text_val
                assert "Exception" not in text_val
                assert "FAILED" not in text_val
                assert "PRECHECK_FAILED" not in text_val
                assert "pipeline_stage_evidence" not in text_val
                assert "preflight_report" not in text_val
                assert "run_manifest" not in text_val
                assert "failure_traceback" not in text_val
                assert "{{" not in text_val
                assert "}}" not in text_val
                assert "i18n." not in text_val
                assert "translation_key" not in text_val
                assert "TODO" not in text_val
                assert "TBD" not in text_val
                assert "{" not in text_val
                assert "}" not in text_val

