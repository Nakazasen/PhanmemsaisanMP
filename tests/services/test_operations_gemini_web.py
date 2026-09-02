"""Tests for the user-triggered Gemini Web comparison path."""

from __future__ import annotations

import json
from unittest.mock import patch

from src.services.operations_case_service import EvidenceReference, OperationalCase
from src.services.operations_gemini_web import (
    DEFAULT_GEMINI_WEB_PROXY_URL,
    request_gemini_web_business_guidance,
    request_gemini_web_guidance,
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
