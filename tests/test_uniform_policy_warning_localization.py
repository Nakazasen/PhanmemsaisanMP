from src.services.fiscal_run import SourceIssue, ISSUE_SOURCE_SKIPPED
from src.services.i18n import DEFAULT_LANGUAGE, set_current_language
from src.universal_app import _localized_preflight_issue_warning, _uniform_policy_signature


def _issue(category: str, reason: str, *, code: str = "SOURCE_VALIDATION_FAILED") -> SourceIssue:
    return SourceIssue(
        category=category,
        path="D:/sources/uniform-policy.xlsx",
        detected_fiscal_year=2027,
        reason=reason,
        action="raw action must not leak into the localized UI",
        code=code,
        severity=ISSUE_SOURCE_SKIPPED,
        impact="raw impact must not leak into the localized UI",
    )


def test_uniform_policy_duplicate_warning_gives_specific_actions_in_all_languages():
    issue = _issue(
        "form_uniform_master",
        "Cột bị trùng trong sheet 原価センタ: ['giay bao ho loai 2']",
    )
    try:
        set_current_language("vi")
        assert "Không tự sửa file yêu cầu gốc" in _localized_preflight_issue_warning(issue)

        set_current_language("ja")
        assert "元の要件ファイルを自分で変更しないでください" in _localized_preflight_issue_warning(issue)

        set_current_language("en")
        assert "Do not edit the original requirement file yourself" in _localized_preflight_issue_warning(issue)
    finally:
        set_current_language(DEFAULT_LANGUAGE)


def test_uniform_policy_missing_source_warning_is_localized_and_actionable():
    issue = _issue("uniform_policy", "Không có nguồn được chọn cho category này", code="MISSING_SOURCE")
    try:
        set_current_language("en")
        message = _localized_preflight_issue_warning(issue)
        assert "Project Settings" in message
        assert "Deep Source Scan" in message
    finally:
        set_current_language(DEFAULT_LANGUAGE)


def test_uniform_policy_missing_columns_warning_names_the_exact_columns_in_all_languages():
    issue = _issue(
        "uniform_policy",
        "Thiếu cột policy trong sheet 原価センタ: Mũ tĩnh điện, Giày bảo hộ loại 1",
    )
    try:
        set_current_language("vi")
        assert "Mũ tĩnh điện, Giày bảo hộ loại 1" in _localized_preflight_issue_warning(issue)
        assert "Lưu file" in _localized_preflight_issue_warning(issue)

        set_current_language("ja")
        assert "Mũ tĩnh điện, Giày bảo hộ loại 1" in _localized_preflight_issue_warning(issue)
        assert "ファイルを保存します" in _localized_preflight_issue_warning(issue)

        set_current_language("en")
        assert "Mũ tĩnh điện, Giày bảo hộ loại 1" in _localized_preflight_issue_warning(issue)
        assert "Save the file" in _localized_preflight_issue_warning(issue)
    finally:
        set_current_language(DEFAULT_LANGUAGE)


def test_uniform_policy_signature_changes_when_the_hidden_policy_file_is_replaced(tmp_path):
    policy = tmp_path / "uniform-policy.xlsx"
    policy.write_bytes(b"first")
    before = _uniform_policy_signature(str(policy))

    policy.write_bytes(b"replacement policy with a new size")
    after = _uniform_policy_signature(str(policy))

    assert before != after
