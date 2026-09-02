"""HTTP Client and Orchestrator for C-AGENT Operations Guidance (T031, T032, T033).

Implements internal contract specs/002-ai-operations-assistant/contracts/cagent-guidance-v1.md:
- Injected transport support for deterministic unit tests.
- Deployment-owned configuration policy.
- Bounded payload and response limits.
- Strict response validation and evidence-ID isolation.
- Fail-closed error sanitisation (never leaks URLs or tokens).
- Service orchestration requiring explicit caller invocation with zero provider fallback.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import socket
import time
from typing import Any, Callable
import urllib.error
import urllib.request
import uuid

from src.services.i18n import translate_for_language
from src.services.operations_ai_packet import build_cagent_guidance_packet
from src.services.operations_ai_provider import (
    MAX_ANSWER_LENGTH,
    MAX_LIMITATION_LENGTH,
    CagentGuidancePacket,
    CagentGuidanceResult,
    CagentProviderPolicy,
    CaseContext,
    SafeEvidenceItem,
)
from src.services.operations_case_service import OperationalCase

# Transport signature for testing: (url: str, headers: dict[str, str], body: bytes, timeout: float) -> tuple[int, dict[str, str], bytes]
TransportFunc = Callable[[str, dict[str, str], bytes, float], tuple[int, dict[str, str], bytes]]

MAX_RESPONSE_BYTES = 64 * 1024  # 64 KB max response size


class CagentHttpClient:
    """Client gửi yêu cầu hướng dẫn tới dịch vụ nội bộ C-AGENT."""

    def __init__(
        self,
        policy: CagentProviderPolicy,
        transport: TransportFunc | None = None,
    ) -> None:
        if not isinstance(policy, CagentProviderPolicy):
            raise TypeError("policy phải là một đối tượng CagentProviderPolicy.")
        self.policy = policy
        self.transport = transport

    def send_guidance_request(
        self,
        packet: CagentGuidancePacket,
        language: str,
    ) -> CagentGuidanceResult:
        """Gửi gói tin CagentGuidancePacket tới endpoint C-AGENT và nhận kết quả tư vấn."""
        start_time = time.time()

        if not self.policy.enabled:
            return CagentGuidanceResult(
                status="unavailable",
                limitation=translate_for_language("operations_assistant_ai_unavailable", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )

        # Kiểm tra nếu không có bất kỳ bằng chứng hợp lệ nào trong gói tin -> Không gọi mạng
        if not packet.evidence_items:
            return CagentGuidanceResult(
                status="unavailable",
                limitation=translate_for_language("operations_assistant_ai_unavailable", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )

        # Chuẩn bị headers
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "MP2027-OperationsAssistant/1.0",
        }

        # Xác thực theo auth_mode
        if self.policy.auth_mode == "bearer_env":
            env_var = self.policy.bearer_token_env_var or "CAGENT_API_KEY"
            token = os.environ.get(env_var, "").strip()
            if not token:
                return CagentGuidanceResult(
                    status="unavailable",
                    limitation=translate_for_language("operations_assistant_ai_unavailable", language),
                    packet_id=packet.packet_id,
                    request_started_at=start_time,
                )
            headers["Authorization"] = f"Bearer {token}"

        # Đóng gói JSON
        payload_dict = packet.to_dict()
        try:
            payload_bytes = json.dumps(payload_dict, ensure_ascii=False).encode("utf-8")
        except Exception:
            return CagentGuidanceResult(
                status="failed",
                limitation=translate_for_language("operations_assistant_ai_failed", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )

        # Kiểm tra giới hạn dung lượng tải yêu cầu (48 KB payload cap)
        from src.services.operations_ai_provider import MAX_REQUEST_PAYLOAD_BYTES
        if len(payload_bytes) > MAX_REQUEST_PAYLOAD_BYTES:
            return CagentGuidanceResult(
                status="failed",
                limitation=translate_for_language("operations_assistant_ai_failed", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )

        # Thực thi gửi yêu cầu qua transport hoặc urllib
        status_code: int = 500
        resp_headers: dict[str, str] = {}
        resp_bytes: bytes = b""

        try:
            if self.transport is not None:
                status_code, resp_headers, resp_bytes = self.transport(
                    self.policy.endpoint_url,
                    headers,
                    payload_bytes,
                    float(self.policy.timeout_seconds),
                )
            else:
                req = urllib.request.Request(
                    self.policy.endpoint_url,
                    data=payload_bytes,
                    headers=headers,
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=float(self.policy.timeout_seconds)) as resp:
                    status_code = resp.getcode()
                    resp_bytes = resp.read(MAX_RESPONSE_BYTES + 1)
        except (socket.timeout, TimeoutError, urllib.error.URLError) as err:
            if isinstance(err, urllib.error.HTTPError):
                if err.code in (401, 403):
                    return CagentGuidanceResult(
                        status="unavailable",
                        limitation=translate_for_language("operations_assistant_ai_unavailable", language),
                        packet_id=packet.packet_id,
                        request_started_at=start_time,
                    )
                return CagentGuidanceResult(
                    status="failed",
                    limitation=translate_for_language("operations_assistant_ai_failed", language),
                    packet_id=packet.packet_id,
                    request_started_at=start_time,
                )
            return CagentGuidanceResult(
                status="timed_out",
                limitation=translate_for_language("operations_assistant_ai_timed_out", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )
        except Exception:
            return CagentGuidanceResult(
                status="failed",
                limitation=translate_for_language("operations_assistant_ai_failed", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )

        # Kiểm tra mã phản hồi HTTP
        if status_code != 200:
            if status_code in (401, 403):
                return CagentGuidanceResult(
                    status="unavailable",
                    limitation=translate_for_language("operations_assistant_ai_unavailable", language),
                    packet_id=packet.packet_id,
                    request_started_at=start_time,
                )
            return CagentGuidanceResult(
                status="failed",
                limitation=translate_for_language("operations_assistant_ai_failed", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )

        # Kiểm tra kích thước phản hồi
        if len(resp_bytes) > MAX_RESPONSE_BYTES:
            return CagentGuidanceResult(
                status="failed",
                limitation=translate_for_language("operations_assistant_ai_failed", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )

        # Giải mã và kiểm tra cấu trúc JSON phản hồi (T032 Response Validation)
        return self._validate_and_parse_response(resp_bytes, packet, language, start_time)

    def _validate_and_parse_response(
        self,
        resp_bytes: bytes,
        packet: CagentGuidancePacket,
        language: str,
        start_time: float,
    ) -> CagentGuidanceResult:
        """Kiểm thực tính toàn vẹn và hợp lệ của phản hồi từ C-AGENT (T032)."""
        try:
            data = json.loads(resp_bytes.decode("utf-8", errors="replace"))
        except Exception:
            return CagentGuidanceResult(
                status="failed",
                limitation=translate_for_language("operations_assistant_ai_failed", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )

        if not isinstance(data, dict):
            return CagentGuidanceResult(
                status="failed",
                limitation=translate_for_language("operations_assistant_ai_failed", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )

        # 1. Trích xuất answer
        answer = str(data.get("answer") or data.get("response") or data.get("guidance") or "").strip()
        if not answer:
            return CagentGuidanceResult(
                status="failed",
                limitation=translate_for_language("operations_assistant_ai_failed", language),
                packet_id=packet.packet_id,
                request_started_at=start_time,
            )
        if len(answer) > MAX_ANSWER_LENGTH:
            answer = answer[:MAX_ANSWER_LENGTH]

        # 2. Trích xuất và kiểm thực cited_evidence_ids (phải là tập con của packet.evidence_items)
        allowed_ids = {item.evidence_id for item in packet.evidence_items}
        raw_evidence_ids = data.get("evidence_ids") or data.get("cited_evidence_ids") or []
        cited_ids: list[str] = []
        if isinstance(raw_evidence_ids, (list, tuple)):
            for eid in raw_evidence_ids:
                eid_str = str(eid).strip()
                if not eid_str:
                    continue
                if eid_str not in allowed_ids:
                    # Bất kỳ evidence ID nào không thuộc gói tin đều khiến phản hồi bị từ chối/thất bại
                    return CagentGuidanceResult(
                        status="failed",
                        limitation=translate_for_language("operations_assistant_ai_failed", language),
                        packet_id=packet.packet_id,
                        request_started_at=start_time,
                    )
                if eid_str not in cited_ids:
                    cited_ids.append(eid_str)

        # 3. Trích xuất limitation
        default_limitation = translate_for_language("operations_assistant_ai_advisory_notice", language)
        limitation = str(data.get("limitations") or data.get("limitation") or default_limitation).strip()
        if not limitation:
            limitation = default_limitation
        if len(limitation) > MAX_LIMITATION_LENGTH:
            limitation = limitation[:MAX_LIMITATION_LENGTH]

        return CagentGuidanceResult(
            status="ready",
            provider_label="C-AGENT (company service)",
            answer=answer,
            cited_evidence_ids=tuple(cited_ids),
            limitation=limitation,
            packet_id=packet.packet_id,
            request_started_at=start_time,
        )


def request_cagent_guidance(
    case: OperationalCase,
    policy: CagentProviderPolicy | None = None,
    language: str = "vi",
    history_root: Path | str | None = None,
    *,
    transport: TransportFunc | None = None,
) -> CagentGuidanceResult:
    """Hàm điều phối cấp dịch vụ yêu cầu hướng dẫn từ C-AGENT (T033).

    Chỉ chạy khi có lệnh gọi trực tiếp. Không tự ý kích hoạt.
    Tuyệt đối không fallback sang Gemini hay bất kỳ provider nào khác.
    """
    if policy is None:
        policy = CagentProviderPolicy()

    if not policy.enabled:
        return CagentGuidanceResult(
            status="unavailable",
            limitation=translate_for_language("operations_assistant_ai_unavailable", language),
        )

    packet = build_cagent_guidance_packet(case, language, history_root=history_root)
    if not packet.evidence_items:
        return CagentGuidanceResult(
            status="unavailable",
            limitation=translate_for_language("operations_assistant_ai_unavailable", language),
            packet_id=packet.packet_id,
        )

    client = CagentHttpClient(policy, transport=transport)
    return client.send_guidance_request(packet, language)


def request_cagent_business_guidance(
    question: str,
    local_context: str,
    policy: CagentProviderPolicy | None = None,
    language: str = "vi",
    *,
    transport: TransportFunc | None = None,
) -> CagentGuidanceResult:
    """Ask C-AGENT a business question using a short local-document context."""
    normalized_question = str(question or "").strip()[:500]
    normalized_context = str(local_context or "").strip()[:1000]
    if not normalized_question or not normalized_context:
        return CagentGuidanceResult(
            status="unavailable",
            limitation=translate_for_language("operations_assistant_ai_unavailable", language),
        )
    active_policy = policy or CagentProviderPolicy()
    packet = CagentGuidancePacket(
        packet_id=f"pkt-business-{uuid.uuid4().hex[:12]}",
        run_id="",
        language=language,
        question=normalized_question,
        case_context=CaseContext(
            fiscal_year="2027",
            cost_center_scope="ALL",
            status="SUCCEEDED",
            stage="business_guidance",
            classification="business_question",
            confidence="possible",
        ),
        local_guidance_summary=normalized_context,
        evidence_items=(
            SafeEvidenceItem(
                evidence_id="E1",
                type="catalog_row",
                summary="Internal MP2027 business guidance summary.",
                technical_excerpt="",
            ),
        ),
    )
    return CagentHttpClient(active_policy, transport=transport).send_guidance_request(packet, language)
