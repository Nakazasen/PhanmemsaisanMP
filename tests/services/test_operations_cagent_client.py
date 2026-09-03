"""Unit tests for C-AGENT HTTP Client (T031), Response Validation (T032), and Service Orchestration (T033).

Covers:
- Fake transport injection for deterministic test execution.
- Happy path: 200 OK returns ready status, advisory answer, and validated cited evidence IDs.
- Guardrails:
  - Policy disabled -> unavailable (zero network).
  - Missing bearer token in environment -> unavailable (zero network).
  - Timeout -> timed_out status (clean, sanitized).
  - HTTP 401/403/500 -> unavailable/failed status (clean, sanitized).
  - Malformed JSON / empty answer -> failed status.
  - Foreign evidence IDs in response -> sanitized to only IDs in request packet.
  - No provider fallback under any circumstance.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import unittest

from src.services.operations_ai_packet import build_cagent_guidance_packet
from src.services.operations_ai_provider import (
    CagentGuidancePacket,
    CagentGuidanceResult,
    CagentProviderPolicy,
    CaseContext,
    SafeEvidenceItem,
)
from src.services.operations_cagent_client import (
    DEFAULT_CAGENT_PREDICTION_URL,
    CagentHttpClient,
    _clean_cagent_text,
    request_cagent_business_guidance,
    request_cagent_chat_guidance,
    request_cagent_guidance,
)
from src.services.operations_case_service import (
    EvidenceReference,
    OperationalCase,
)
from src.services.operations_knowledge import (
    ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK,
    get_knowledge_entry,
)


class TestCagentHttpClient(unittest.TestCase):
    def _make_packet(self) -> CagentGuidancePacket:
        ctx = CaseContext(
            fiscal_year="FY2027",
            cost_center_scope="ALL",
            status="FAILED",
            stage="publication",
            classification="blocked_output_file_lock",
            confidence="confirmed",
        )
        items = (
            SafeEvidenceItem(
                evidence_id="E1",
                type="stage_evidence",
                summary="Publication failed due to locked file.",
                local_path="reports/pipeline_stage_evidence.json",
            ),
            SafeEvidenceItem(
                evidence_id="E2",
                type="failure_traceback",
                summary="Traceback showing Excel file lock.",
                local_path="reports/failure_traceback.txt",
            ),
        )
        return CagentGuidancePacket(
            packet_id="pkt-test-12345",
            run_id="RUN_20270901_001",
            language="vi",
            question="Phân tích nguyên nhân và đề xuất các bước kiểm tra.",
            case_context=ctx,
            local_guidance_summary="Tệp đầu ra đang bị khóa bởi Excel.",
            evidence_items=items,
        )

    def test_happy_path_successful_guidance(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api/v1/guidance",
            data_policy_id="POL-2026-AI-OPS-01",
            auth_mode="none",
            timeout_seconds=10,
        )
        packet = self._make_packet()

        recorded_requests = []

        def fake_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, dict[str, str], bytes]:
            recorded_requests.append((url, headers, body, timeout))
            resp_data = {
                "answer": "Vui lòng đóng ứng dụng Microsoft Excel và chạy lại tính toán.",
                "evidence_ids": ["E1", "E2"],
                "limitations": "Tư vấn tham khảo; người vận hành kiểm tra thủ công.",
            }
            return 200, {"Content-Type": "application/json"}, json.dumps(resp_data).encode("utf-8")

        client = CagentHttpClient(policy, transport=fake_transport)
        result = client.send_guidance_request(packet, language="vi")

        self.assertEqual(len(recorded_requests), 1)
        url, headers, body, timeout = recorded_requests[0]
        self.assertEqual(url, "https://cagent.internal.company.com/api/v1/guidance")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(timeout, 10.0)

        # Check result
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.answer, "Vui lòng đóng ứng dụng Microsoft Excel và chạy lại tính toán.")
        self.assertEqual(result.cited_evidence_ids, ("E1", "E2"))
        self.assertEqual(result.limitation, "Tư vấn tham khảo; người vận hành kiểm tra thủ công.")
        self.assertEqual(result.packet_id, "pkt-test-12345")
        self.assertIsNotNone(result.request_started_at)

    def test_disabled_policy_makes_zero_network_calls(self) -> None:
        policy = CagentProviderPolicy(enabled=False)
        packet = self._make_packet()

        call_count = 0

        def fake_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, dict[str, str], bytes]:
            nonlocal call_count
            call_count += 1
            return 200, {}, b"{}"

        client = CagentHttpClient(policy, transport=fake_transport)
        result = client.send_guidance_request(packet, language="vi")

        self.assertEqual(call_count, 0)
        self.assertEqual(result.status, "unavailable")
        self.assertIn("không khả dụng", result.limitation.lower())

    def test_bearer_env_auth_mode_reads_token(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api/v1/guidance",
            data_policy_id="POL-01",
            auth_mode="bearer_env",
            bearer_token_env_var="TEST_CAGENT_TOKEN",
        )
        packet = self._make_packet()

        # Case 1: Environment variable missing
        os.environ.pop("TEST_CAGENT_TOKEN", None)
        client = CagentHttpClient(policy, transport=lambda *args: (200, {}, b"{}"))
        res_missing = client.send_guidance_request(packet, language="vi")
        self.assertEqual(res_missing.status, "unavailable")

        # Case 2: Environment variable present
        os.environ["TEST_CAGENT_TOKEN"] = "mock_secret_token_123"
        try:
            sent_headers = {}

            def fake_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, dict[str, str], bytes]:
                sent_headers.update(headers)
                resp = {"answer": "Answer text", "evidence_ids": ["E1"]}
                return 200, {}, json.dumps(resp).encode("utf-8")

            client2 = CagentHttpClient(policy, transport=fake_transport)
            res_auth = client2.send_guidance_request(packet, language="vi")
            self.assertEqual(res_auth.status, "ready")
            self.assertEqual(sent_headers.get("Authorization"), "Bearer mock_secret_token_123")
        finally:
            os.environ.pop("TEST_CAGENT_TOKEN", None)

    def test_timeout_handling(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api",
            data_policy_id="POL-01",
        )
        packet = self._make_packet()

        def timeout_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, dict[str, str], bytes]:
            raise TimeoutError("Connection timed out")

        client = CagentHttpClient(policy, transport=timeout_transport)
        result = client.send_guidance_request(packet, language="vi")

        self.assertEqual(result.status, "timed_out")
        self.assertIn("thời gian chờ", result.limitation.lower())
        self.assertNotIn("https://", result.limitation)

    def test_http_error_status_codes(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api",
            data_policy_id="POL-01",
        )
        packet = self._make_packet()

        # 401 Unauthorized -> unavailable
        client_401 = CagentHttpClient(policy, transport=lambda *args: (401, {}, b"Unauthorized"))
        res_401 = client_401.send_guidance_request(packet, language="vi")
        self.assertEqual(res_401.status, "unavailable")

        # 500 Internal Server Error -> failed
        client_500 = CagentHttpClient(policy, transport=lambda *args: (500, {}, b"Internal Error"))
        res_500 = client_500.send_guidance_request(packet, language="vi")
        self.assertEqual(res_500.status, "failed")

    def test_malformed_json_response(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api",
            data_policy_id="POL-01",
        )
        packet = self._make_packet()

        client = CagentHttpClient(policy, transport=lambda *args: (200, {}, b"NOT_JSON_DATA"))
        result = client.send_guidance_request(packet, language="vi")
        self.assertEqual(result.status, "failed")

    def test_response_validation_rejects_foreign_evidence_ids(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api",
            data_policy_id="POL-01",
        )
        packet = self._make_packet()  # Contains E1 and E2

        def fake_transport_foreign(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, dict[str, str], bytes]:
            resp_data = {
                "answer": "Valid answer",
                "evidence_ids": ["E1", "E999_FOREIGN_ID", "E2"],
            }
            return 200, {}, json.dumps(resp_data).encode("utf-8")

        client = CagentHttpClient(policy, transport=fake_transport_foreign)
        result = client.send_guidance_request(packet, language="vi")

        # Bất kỳ ID ngoại lai nào đều khiến kết quả bị từ chối/failed (không âm thầm bỏ qua)
        self.assertEqual(result.status, "failed")

    def test_zero_valid_evidence_does_not_call_transport(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api",
            data_policy_id="POL-01",
        )
        # Empty evidence packet
        packet = CagentGuidancePacket(
            packet_id="pkt-empty",
            run_id="RUN_001",
            language="vi",
            question="Question",
            case_context=CaseContext(
                fiscal_year="2027",
                cost_center_scope="ALL",
                status="FAILED",
                stage="calc",
                classification="unknown",
                confidence="unknown",
            ),
            local_guidance_summary="Summary",
            evidence_items=(),
        )
        transport_called = False

        def mock_transport(*args):
            nonlocal transport_called
            transport_called = True
            return 200, {}, b"{}"

        client = CagentHttpClient(policy, transport=mock_transport)
        result = client.send_guidance_request(packet, language="vi")
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(transport_called)

    def test_oversized_payload_does_not_call_transport(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api",
            data_policy_id="POL-01",
        )
        # Create packet with valid items that together exceed 48 KB
        items = tuple(
            SafeEvidenceItem(
                evidence_id=f"E{i}",
                type="stage_evidence",
                summary=f"Summary {i}",
                verification="verified",
                technical_excerpt="Y" * 3800,
            )
            for i in range(1, 16)
        )
        packet = CagentGuidancePacket(
            packet_id="pkt-huge",
            run_id="RUN_001",
            language="vi",
            question="Question",
            case_context=CaseContext(
                fiscal_year="2027",
                cost_center_scope="ALL",
                status="FAILED",
                stage="calc",
                classification="unknown",
                confidence="unknown",
            ),
            local_guidance_summary="Summary",
            evidence_items=items,
        )
        transport_called = False

        def mock_transport(*args):
            nonlocal transport_called
            transport_called = True
            return 200, {}, b"{}"

        client = CagentHttpClient(policy, transport=mock_transport)
        result = client.send_guidance_request(packet, language="vi")
        self.assertEqual(result.status, "failed")
        self.assertFalse(transport_called)


class TestRequestCagentGuidanceOrchestration(unittest.TestCase):
    def test_business_question_uses_the_same_internal_cagent_service(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api",
            data_policy_id="POL-01",
        )
        captured: dict[str, object] = {}

        def mock_transport(url, headers, body, timeout):
            captured["payload"] = json.loads(body.decode("utf-8"))
            return 200, {}, json.dumps({"answer": "Use the selected MP2027 workflow."}).encode("utf-8")

        result = request_cagent_business_guidance(
            "How do I check the MP2027 workflow?",
            "MP2027 workflow guidance: verify sources before calculation.",
            policy,
            "en",
            transport=mock_transport,
        )

        self.assertEqual(result.status, "ready")
        self.assertEqual(captured["payload"]["run_id"], "")
        self.assertEqual(captured["payload"]["question"], "How do I check the MP2027 workflow?")

    def test_orchestration_happy_path(self) -> None:
        evidence = (
            EvidenceReference(
                type="stage_evidence",
                local_path="reports/pipeline_stage_evidence.json",
                locator="stage=publication",
                summary="Publication failed",
                verification="verified",
            ),
        )
        presentation = get_knowledge_entry(ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK).translations["vi"]
        case = OperationalCase(
            case_id="CASE-001",
            run_id="RUN_001",
            fiscal_year=2027,
            cost_center_scope="ALL",
            status="FAILED",
            stage="publication",
            classification="blocked_output_file_lock",
            confidence="confirmed",
            summary="Lỗi",
            evidence=evidence,
            presentation=presentation,
        )
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api",
            data_policy_id="POL-01",
        )

        def mock_transport(url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, dict[str, str], bytes]:
            return 200, {}, json.dumps({"answer": "Hướng dẫn xử lý", "evidence_ids": ["E1"]}).encode("utf-8")

        result = request_cagent_guidance(
            case=case,
            policy=policy,
            language="vi",
            transport=mock_transport,
        )
        self.assertEqual(result.status, "ready")
        self.assertEqual(result.answer, "Hướng dẫn xử lý")
        self.assertEqual(result.cited_evidence_ids, ("E1",))

    def test_orchestration_zero_verified_evidence_returns_unavailable_without_transport(self) -> None:
        evidence = (
            EvidenceReference(
                type="stage_evidence",
                local_path="reports/missing.json",
                locator="stage=publication",
                summary="Missing evidence",
                verification="missing",
            ),
        )
        presentation = get_knowledge_entry(ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK).translations["vi"]
        case = OperationalCase(
            case_id="CASE-002",
            run_id="RUN_002",
            fiscal_year=2027,
            cost_center_scope="ALL",
            status="FAILED",
            stage="publication",
            classification="blocked_output_file_lock",
            confidence="confirmed",
            summary="Lỗi",
            evidence=evidence,
            presentation=presentation,
        )
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api",
            data_policy_id="POL-01",
        )
        transport_called = False

        def mock_transport(*args):
            nonlocal transport_called
            transport_called = True
            return 200, {}, b"{}"

        result = request_cagent_guidance(
            case=case,
            policy=policy,
            language="vi",
            transport=mock_transport,
        )
        self.assertEqual(result.status, "unavailable")
        self.assertFalse(transport_called)


class TestCagentChatGuidance(unittest.TestCase):
    def test_clean_cagent_text_unwraps_json_markdown(self) -> None:
        raw = '```json\n{\n  "summary": "Giới thiệu",\n  "message": "Xin chào! Tôi có thể giúp bạn."\n}\n```'
        cleaned = _clean_cagent_text(raw)
        self.assertEqual(cleaned, "Xin chào! Tôi có thể giúp bạn.")

    def test_clean_cagent_text_plain_text(self) -> None:
        raw = "Đây là câu trả lời trực tiếp."
        self.assertEqual(_clean_cagent_text(raw), "Đây là câu trả lời trực tiếp.")

    def test_clean_cagent_text_strips_leading_code_assistant_metadata(self) -> None:
        raw = '{\n  "summary": "Cần thêm thông tin",\n  "changes": [],\n  "tests": []\n}\n\nDựa vào thông tin được cung cấp, MP2027 là một hệ thống kế toán.'
        cleaned = _clean_cagent_text(raw)
        self.assertEqual(cleaned, "Dựa vào thông tin được cung cấp, MP2027 là một hệ thống kế toán.")

    def test_happy_path_chat_guidance(self) -> None:
        captured = {}

        def fake_transport(url, headers, body, timeout):
            captured["url"] = url
            captured["headers"] = headers
            captured["body"] = json.loads(body.decode("utf-8"))
            return 200, {}, json.dumps({"text": "Quy trình phân bổ chi phí gồm 4 bước."}).encode("utf-8")

        res = request_cagent_chat_guidance(
            question="Quy trình phân bổ thế nào?",
            local_context="Tài liệu phân bổ MP2027.",
            language="vi",
            transport=fake_transport,
        )
        self.assertEqual(res.status, "ready")
        self.assertEqual(res.provider_label, "C-Agent (KDTVN AI)")
        self.assertEqual(res.answer, "Quy trình phân bổ chi phí gồm 4 bước.")
        self.assertEqual(captured["url"], DEFAULT_CAGENT_PREDICTION_URL)
        self.assertIn("Tài liệu phân bổ MP2027", captured["body"]["question"])
        self.assertIn("Quy trình phân bổ thế nào?", captured["body"]["question"])

    def test_chat_guidance_with_chat_id_and_history(self) -> None:
        captured = {}

        def fake_transport(url, headers, body, timeout):
            captured["body"] = json.loads(body.decode("utf-8"))
            return 200, {}, json.dumps({"text": "Bước 2 là tính tỷ lệ nhân sự."}).encode("utf-8")

        history = [
            {"role": "user", "content": "Quy trình phân bổ gồm những bước nào?"},
            {"role": "assistant", "content": "Gồm 4 bước: 1. Thu thập, 2. Tính tỷ lệ, 3. Phân bổ, 4. Xuất báo cáo."},
        ]

        res = request_cagent_chat_guidance(
            question="Giải thích rõ hơn bước 2",
            local_context="Ngữ cảnh tài liệu.",
            language="vi",
            chat_id="session-xyz-123",
            history=history,
            transport=fake_transport,
        )
        self.assertEqual(res.status, "ready")
        self.assertEqual(captured["body"]["chatId"], "session-xyz-123")
        self.assertIn("Lịch sử cuộc trò chuyện trước đó", captured["body"]["question"])
        self.assertIn("Quy trình phân bổ gồm những bước nào?", captured["body"]["question"])
        self.assertIn("Giải thích rõ hơn bước 2", captured["body"]["question"])

    def test_empty_question_returns_unavailable(self) -> None:
        res = request_cagent_chat_guidance("", language="vi")
        self.assertEqual(res.status, "unavailable")

    def test_timeout_handling(self) -> None:
        def fake_transport(*args):
            raise TimeoutError("timeout")

        res = request_cagent_chat_guidance("test?", language="vi", transport=fake_transport)
        self.assertEqual(res.status, "timed_out")

    def test_http_error_handling(self) -> None:
        import urllib.error
        def fake_transport(*args):
            raise urllib.error.HTTPError("url", 500, "Internal Server Error", {}, None)

        res = request_cagent_chat_guidance("test?", language="vi", transport=fake_transport)
        self.assertEqual(res.status, "failed")


if __name__ == "__main__":
    unittest.main()
