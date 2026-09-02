"""Tests for the user-triggered Gemini Web comparison path."""

from __future__ import annotations

import json
from unittest.mock import patch

from src.services.operations_case_service import EvidenceReference, OperationalCase
from src.services.operations_gemini_web import (
    DEFAULT_GEMINI_WEB_PROXY_URL,
    is_proxy_available,
    mark_proxy_failed,
    mark_proxy_success,
    request_gemini_web_business_guidance,
    request_gemini_web_guidance,
    reset_proxy_cooldown,
)
from src.services.operations_knowledge import ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK, get_knowledge_entry


def _case() -> OperationalCase:
    return OperationalCase(
        case_id="case-gemini-web",
        run_id="run-gemini-web",
        fiscal_year=2027,
        cost_center_scope="ALL",
        status="FAILED",
        stage="publication",
        classification="blocked_output_file_lock",
        confidence="confirmed",
        summary="Output workbook is locked.",
        evidence=(
            EvidenceReference(
                type="stage_evidence",
                local_path="reports/pipeline_stage_evidence.json",
                locator="publication",
                summary="PermissionError while publishing the output workbook.",
                verification="verified",
            ),
        ),
        presentation=get_knowledge_entry(ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK).translations["en"],
    )


def test_gemini_web_posts_selected_case_and_returns_answer() -> None:
    captured: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        captured.update(url=url, headers=headers, body=body, timeout=timeout)
        return 200, json.dumps(
            {"choices": [{"message": {"content": "Close the workbook, then run again."}}]}
        ).encode("utf-8")

    result = request_gemini_web_guidance(_case(), "en", transport=fake_transport)

    assert result.status == "ready"
    assert result.provider_label == "Gemini Web (local proxy)"
    assert result.answer == "Close the workbook, then run again."
    assert captured["url"] == DEFAULT_GEMINI_WEB_PROXY_URL
    assert captured["headers"] == {"Content-Type": "application/json"}
    assert b"run-gemini-web" in captured["body"]


def test_gemini_web_returns_a_clean_failure_for_a_bad_response() -> None:
    result = request_gemini_web_guidance(
        _case(),
        "en",
        transport=lambda *_: (200, b'{"candidates": []}'),
    )

    assert result.status == "unavailable"


def test_gemini_web_answers_a_business_question_without_an_api_key() -> None:
    captured: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        captured["body"] = body
        return 200, json.dumps(
            {"choices": [{"message": {"content": "Check the approved source before calculation."}}]}
        ).encode("utf-8")

    result = request_gemini_web_business_guidance(
        "How do I check the source?",
        "The source must be checked before calculation.",
        "en",
        transport=fake_transport,
    )

    assert result.status == "ready"
    assert result.provider_label == "Gemini Web (local proxy)"
    assert b"How do I check the source?" in captured["body"]


def test_business_prompt_does_not_force_error_status_for_normal_questions() -> None:
    captured: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        captured["body"] = body
        return 200, json.dumps(
            {"choices": [{"message": {"content": "Use the source form, then rescan it."}}]}
        ).encode("utf-8")

    result = request_gemini_web_business_guidance(
        "cách sử dụng phần mềm này",
        "MP2027 hỗ trợ lập kế hoạch ngân sách và phân bổ chi phí từ tệp Excel.",
        "vi",
        transport=fake_transport,
    )

    assert result.status == "ready"
    prompt = captured["body"].decode("utf-8")
    assert "Do NOT add any health or incident statement" in prompt
    assert "system is currently normal" not in prompt
    assert "no recent errors" not in prompt


def test_business_prompt_requires_scope_instead_of_inventing_a_cost_count() -> None:
    captured: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        captured["body"] = body
        return 200, json.dumps(
            {"choices": [{"message": {"content": "Please specify the fiscal year and cost center."}}]}
        ).encode("utf-8")

    result = request_gemini_web_business_guidance(
        "MP có bao nhiêu chi phí?",
        "Chưa có số lượng khoản chi cụ thể trong ngữ cảnh này.",
        "vi",
        transport=fake_transport,
    )

    assert result.status == "ready"
    prompt = captured["body"].decode("utf-8")
    assert "For a count or amount question" in prompt
    assert "Never invent a number" in prompt
    assert "no recent errors" not in prompt


def test_gemini_web_removes_internal_followup_markup_from_displayed_answer() -> None:
    result = request_gemini_web_business_guidance(
        "How do I check the source?",
        "Check the source before calculation.",
        "en",
        transport=lambda *_: (
            200,
            json.dumps(
                {"choices": [{"message": {"content": "Check the source. <FollowUp label='More'/>"}}]}
            ).encode("utf-8"),
        ),
    )

    assert result.status == "ready"
    assert result.answer == "Check the source."


def test_gemini_web_falls_back_to_direct_mode_when_local_service_is_offline() -> None:
    with patch(
        "src.services.operations_gemini_web._request_direct_gemini_web",
        return_value="Check the source workbook and retry.",
    ):
        result = request_gemini_web_guidance(_case(), "en")

    assert result.status == "ready"
    assert result.provider_label == "Gemini Web Direct"
    assert result.answer == "Check the source workbook and retry."


def test_gemini_payload_contains_only_curated_context() -> None:
    """Verify the Gemini prompt uses curated context and not raw paths/logs/traceback/v1 docs."""
    captured: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        captured["body"] = body
        return 200, json.dumps(
            {"choices": [{"message": {"content": "Close the file and retry."}}]}
        ).encode("utf-8")

    result = request_gemini_web_business_guidance(
        "file bị khóa",
        "Tệp kết quả đang bị khóa: Khi tệp Excel kết quả đang được mở (1) Đóng tất cả tệp Excel",
        "vi",
        transport=fake_transport,
    )

    assert result.status == "ready"
    body_text = captured["body"].decode("utf-8")

    # Must contain "Curated internal knowledge" label in the prompt
    assert "Curated internal knowledge" in body_text or "curated" in body_text.lower(), \
        "Prompt must reference curated knowledge, not raw documents"

    # Must NOT contain paths to v1 knowledge base or raw Markdown files
    forbidden_fragments = [
        "mp_saisan_business_knowledge_base",
        "cai_tien_nhap_du_lieu_chung",
        "knowledge_base_v2.md",
        "knowledge_base.md",
        "Traceback (most recent call last)",
        "pipeline_stage_evidence",
        "failure_traceback",
        ".py:",
    ]
    for fragment in forbidden_fragments:
        assert fragment not in body_text, \
            f"Gemini payload must not contain '{fragment}'"


def test_gemini_offline_returns_local_fallback_in_vietnamese() -> None:
    """When Gemini is offline with transport=, fallback must be in Vietnamese."""
    result = request_gemini_web_business_guidance(
        "file bị khóa không lưu được",
        "Tệp kết quả đang bị khóa",
        "vi",
        transport=lambda *_: (500, b"error"),
    )
    assert result.status == "unavailable"
    # The limitation message should be in Vietnamese
    assert result.limitation is not None
    assert isinstance(result.limitation, str)


def test_gemini_offline_returns_local_fallback_in_japanese() -> None:
    """When Gemini is offline with transport=, fallback must be in Japanese."""
    result = request_gemini_web_business_guidance(
        "ファイルロック",
        "出力ファイルがロックされています",
        "ja",
        transport=lambda *_: (500, b"error"),
    )
    assert result.status == "unavailable"
    assert result.limitation is not None


def test_gemini_offline_returns_local_fallback_in_english() -> None:
    """When Gemini is offline with transport=, fallback must be in English."""
    result = request_gemini_web_business_guidance(
        "locked file",
        "Output file is locked",
        "en",
        transport=lambda *_: (500, b"error"),
    )
    assert result.status == "unavailable"
    assert result.limitation is not None


def test_gemini_web_incident_prompt_rules() -> None:
    """Verify Gemini prompt correctly embeds INCIDENT_OR_TROUBLESHOOTING intent rules."""
    captured: dict[str, object] = {}

    def fake_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        captured["body"] = body
        return 200, json.dumps(
            {"choices": [{"message": {"content": "Follow the action steps."}}]}
        ).encode("utf-8")

    result = request_gemini_web_business_guidance(
        "Chạy tính toán bị dừng khi xuất Excel",
        "Tệp Excel kết quả đang bị khóa.",
        "vi",
        intent="incident",
        transport=fake_transport,
    )

    assert result.status == "ready"
    prompt = captured["body"].decode("utf-8")
    assert "INCIDENT_OR_TROUBLESHOOTING" in prompt
    assert "Provide direct troubleshooting guidance" in prompt
    assert "at most 3 clear, safe manual action steps" in prompt


def test_gemini_web_clarify_prompt_rules_multilingual() -> None:
    """Verify Gemini prompt correctly embeds CLARIFICATION_NEEDED intent rules in EN and JA."""
    captured_en: dict[str, object] = {}

    def fake_transport_en(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        captured_en["body"] = body
        return 200, json.dumps(
            {"choices": [{"message": {"content": "Which fiscal year?"}}]}
        ).encode("utf-8")

    res_en = request_gemini_web_business_guidance(
        "How many expenses in MP?",
        "No specific count available.",
        "en",
        intent="clarify",
        transport=fake_transport_en,
    )
    assert res_en.status == "ready"
    prompt_en = captured_en["body"].decode("utf-8")
    assert "CLARIFICATION_NEEDED" in prompt_en
    assert "Ask exactly ONE focused, concise question in English" in prompt_en

    captured_ja: dict[str, object] = {}

    def fake_transport_ja(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, bytes]:
        captured_ja["body"] = body
        return 200, json.dumps(
            {"choices": [{"message": {"content": "対象の年度は？"}}]}
        ).encode("utf-8")

    res_ja = request_gemini_web_business_guidance(
        "MPには費用がいくつありますか？",
        "該当する件数は記載されていません。",
        "ja",
        intent="clarify",
        transport=fake_transport_ja,
    )
    assert res_ja.status == "ready"
    prompt_ja = captured_ja["body"].decode("utf-8")
    assert "CLARIFICATION_NEEDED" in prompt_ja
    assert "Ask exactly ONE focused, concise question in Japanese" in prompt_ja


def test_proxy_failure_activates_cooldown_and_falls_back_to_direct() -> None:
    """Khi proxy cục bộ bị lỗi (VD kết nối từ chối), kích hoạt cooldown và đi thẳng Gemini Web Direct."""
    import urllib.error

    reset_proxy_cooldown()
    assert is_proxy_available() is True

    with patch("src.services.operations_gemini_web.check_local_proxy_running", return_value=False), \
         patch("src.services.operations_gemini_web._request_direct_gemini_web", return_value="Direct answer from Web") as mock_direct:
        result = request_gemini_web_business_guidance(
            "Hướng dẫn kiểm tra nguồn",
            "Nội dung kiểm tra nguồn...",
            "vi",
        )

        assert result.status == "ready"
        assert result.provider_label == "Gemini Web Direct"
        assert result.answer == "Direct answer from Web"
        mock_direct.assert_called_once()
        # Cooldown phải được kích hoạt
        assert is_proxy_available() is False


def test_subsequent_query_within_cooldown_skips_proxy_immediately() -> None:
    """Trong thời gian cooldown, proxy bị bỏ qua hoàn toàn và không tốn thời gian chờ."""
    # Cooldown is already active or we activate it
    mark_proxy_failed()
    assert is_proxy_available() is False

    with patch("urllib.request.urlopen") as mock_urlopen, \
         patch("src.services.operations_gemini_web._request_direct_gemini_web", return_value="Fast direct answer") as mock_direct:
        result = request_gemini_web_business_guidance(
            "Câu hỏi kế tiếp",
            "Nội dung ngữ cảnh...",
            "vi",
        )

        assert result.status == "ready"
        assert result.provider_label == "Gemini Web Direct"
        assert result.answer == "Fast direct answer"
        # urlopen tuyệt đối không được gọi -> 0s chờ proxy chết!
        mock_urlopen.assert_not_called()
        mock_direct.assert_called_once()


def test_after_cooldown_expires_proxy_is_retried_and_succeeds() -> None:
    """Sau khi hết cooldown, proxy được thử lại và nếu thành công sẽ không gọi Gemini Web Direct."""
    mark_proxy_failed()
    assert is_proxy_available() is False

    fake_response_data = json.dumps(
        {"choices": [{"message": {"content": "Phản hồi từ proxy cục bộ đã hồi phục."}}]}
    ).encode("utf-8")

    with patch("src.services.operations_gemini_web.time.monotonic", return_value=float("inf")), \
         patch("src.services.operations_gemini_web.check_local_proxy_running", return_value=True), \
         patch("urllib.request.urlopen") as mock_urlopen, \
         patch("src.services.operations_gemini_web._request_direct_gemini_web") as mock_direct:
        mock_urlopen.return_value.__enter__.return_value.getcode.return_value = 200
        mock_urlopen.return_value.__enter__.return_value.read.return_value = fake_response_data

        result = request_gemini_web_business_guidance(
            "Câu hỏi sau hồi phục",
            "Nội dung...",
            "vi",
        )

        assert result.status == "ready"
        assert result.provider_label == "Gemini Web (local proxy)"
        assert result.answer == "Phản hồi từ proxy cục bộ đã hồi phục."
        mock_urlopen.assert_called_once()
        mock_direct.assert_not_called()

    reset_proxy_cooldown()


def test_direct_gemini_accumulates_stream_frames_until_final_answer() -> None:
    """Direct mode must accumulate stream frames and return the final complete answer."""
    from src.services.operations_gemini_web import _request_direct_gemini_web

    frame1_inner = [None, None, None, None, [[None, ["MP2"]]]]
    frame1 = (json.dumps([["wrb.fr", None, json.dumps(frame1_inner)]]) + "\n").encode("utf-8")
    frame2_inner = [None, None, None, None, [[None, ["MP2027 la he thong ngan sach"]]]]
    frame2 = (json.dumps([["wrb.fr", None, json.dumps(frame2_inner)]]) + "\n").encode("utf-8")

    class _StreamingResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def __iter__(self):
            yield frame1
            yield frame2

    with patch("src.services.operations_gemini_web._refresh_gemini_bl", return_value="test-build"), \
         patch("urllib.request.urlopen", return_value=_StreamingResponse()):
        assert _request_direct_gemini_web("hello") == "MP2027 la he thong ngan sach"
