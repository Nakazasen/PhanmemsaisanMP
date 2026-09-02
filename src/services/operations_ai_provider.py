"""Provider-neutral models and contracts for AI Operations Assistance (C-AGENT primary).

Implements immutable data structures matching specs/002-ai-operations-assistant/data-model.md:
- CagentProviderPolicy: Deployment configuration policy for C-AGENT guidance.
- SafeEvidenceItem: Verified, scoped technical evidence item for selected run.
- CaseContext: Context of the selected local operational case.
- CagentGuidancePacket: Minimal, privacy-preserving outbound request packet.
- CagentGuidanceResult: Advisory, in-memory response envelope.

All models are frozen dataclasses with fail-closed validation.
Defaults to disabled. No network calls, credentials, or persistence.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Any, Sequence
from urllib.parse import urlparse

from src.services.operations_knowledge import SUPPORTED_LANGUAGES

CAGENT_CONTRACT_VERSION = "cagent-guidance/v1"

CAGENT_RESULT_STATUSES = frozenset({
    "ready",
    "unavailable",
    "rejected",
    "failed",
    "timed_out",
})

CAGENT_AUTH_MODES = frozenset({
    "none",
    "bearer_env",
})

ALLOWED_EVIDENCE_TYPES = frozenset({
    "stage_evidence",
    "preflight_report",
    "run_manifest",
    "traceback_signal",
    "failure_traceback",
    "catalog_row",
    "documentation",
})

_TERMINAL_RUN_STATUSES = frozenset({
    "FAILED",
    "PRECHECK_FAILED",
    "SUCCEEDED_INCOMPLETE",
    "SUCCEEDED",
    "LEGACY_FY2027",
})

_CASE_CONFIDENCES = frozenset({"confirmed", "possible", "unknown"})

_EVIDENCE_ID_PATTERN = re.compile(r"^E\d+$")

# Named bounded text length and payload limits
MAX_EVIDENCE_SUMMARY_LENGTH = 2000
MAX_EXCERPT_LENGTH = 4000
MAX_GUIDANCE_SUMMARY_LENGTH = 2000
MAX_QUESTION_LENGTH = 1000
MAX_ANSWER_LENGTH = 4000
MAX_LIMITATION_LENGTH = 1000
MAX_CONTEXT_FIELD_LENGTH = 200
MAX_REQUEST_PAYLOAD_BYTES = 48 * 1024  # 48 KB
MAX_EVIDENCE_ITEMS = 10

_SECRET_LEAK_PATTERN = re.compile(
    r"(?:api[_-]?key|bearer\s+[a-zA-Z0-9_\-\.]+|ghp_[a-zA-Z0-9]+|sk-[a-zA-Z0-9]+|password\s*[:=]|secret\s*[:=]|token\s*[:=]|PRIVATE\s+KEY)",
    re.IGNORECASE,
)


def _check_secret_leak(text: str, field_name: str) -> None:
    """Kiểm tra và từ chối các dấu hiệu rò rỉ thông tin xác thực, token, password hoặc private key."""
    if _SECRET_LEAK_PATTERN.search(text):
        raise ValueError(f"{field_name} chứa dấu hiệu rò rỉ credential/secret/token.")


@dataclass(frozen=True)
class CagentProviderPolicy:
    """Chính sách cấu hình nhà cung cấp C-AGENT ở cấp triển khai (Deployment Policy)."""

    enabled: bool = False
    endpoint_url: str = ""
    auth_mode: str = "none"
    bearer_token_env_var: str = "CAGENT_API_KEY"
    timeout_seconds: int = 60
    data_policy_id: str = ""
    allowed_packet_version: str = CAGENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise TypeError("CagentProviderPolicy.enabled phải là kiểu bool.")
        if not isinstance(self.endpoint_url, str):
            raise TypeError("CagentProviderPolicy.endpoint_url phải là kiểu str.")
        if not isinstance(self.auth_mode, str) or not self.auth_mode.strip():
            raise ValueError("CagentProviderPolicy.auth_mode không được để trống.")
        if self.auth_mode not in CAGENT_AUTH_MODES:
            raise ValueError(
                f"CagentProviderPolicy.auth_mode ('{self.auth_mode}') không hợp lệ. "
                f"Phải thuộc danh mục đã duyệt: {sorted(CAGENT_AUTH_MODES)}."
            )
        if not isinstance(self.bearer_token_env_var, str):
            raise TypeError("CagentProviderPolicy.bearer_token_env_var phải là kiểu str.")
        if not isinstance(self.timeout_seconds, int):
            raise TypeError("CagentProviderPolicy.timeout_seconds phải là kiểu int.")
        if not (1 <= self.timeout_seconds <= 60):
            raise ValueError(
                f"CagentProviderPolicy.timeout_seconds ({self.timeout_seconds}) phải nằm trong khoảng 1 đến 60."
            )
        if not isinstance(self.data_policy_id, str):
            raise TypeError("CagentProviderPolicy.data_policy_id phải là kiểu str.")
        if self.allowed_packet_version != CAGENT_CONTRACT_VERSION:
            raise ValueError(
                f"CagentProviderPolicy.allowed_packet_version phải là '{CAGENT_CONTRACT_VERSION}'."
            )

        if self.enabled:
            if not self.data_policy_id.strip():
                raise ValueError("CagentProviderPolicy.data_policy_id bắt buộc không được để trống khi enabled=True.")
            url = self.endpoint_url.strip()
            if not url:
                raise ValueError("CagentProviderPolicy.endpoint_url bắt buộc không được để trống khi enabled=True.")
            parsed = urlparse(url)
            if parsed.scheme.lower() != "https" or not parsed.netloc:
                raise ValueError("CagentProviderPolicy.endpoint_url phải là URL HTTPS hợp lệ.")
            if parsed.username or parsed.password or "@" in parsed.netloc:
                raise ValueError(
                    "CagentProviderPolicy.endpoint_url không được chứa thông tin xác thực người dùng (userinfo/credentials)."
                )
            if parsed.query or "?" in url:
                raise ValueError(
                    "CagentProviderPolicy.endpoint_url không được chứa query string/token."
                )
            if parsed.fragment or "#" in url:
                raise ValueError(
                    "CagentProviderPolicy.endpoint_url không được chứa URL fragment."
                )


@dataclass(frozen=True)
class SafeEvidenceItem:
    """Mục bằng chứng an toàn đã được xác minh của lần chạy được chọn cho C-AGENT packet."""

    evidence_id: str
    type: str
    summary: str
    verification: str = "verified"
    local_path: str = ""
    technical_excerpt: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_id, str) or not self.evidence_id.strip():
            raise ValueError("SafeEvidenceItem.evidence_id không được để trống.")
        if not _EVIDENCE_ID_PATTERN.match(self.evidence_id.strip()):
            raise ValueError(
                f"SafeEvidenceItem.evidence_id ('{self.evidence_id}') phải có định dạng 'E1', 'E2', ..."
            )
        if self.type not in ALLOWED_EVIDENCE_TYPES:
            raise ValueError(
                f"SafeEvidenceItem.type ('{self.type}') không nằm trong danh sách loại bằng chứng cho phép."
            )
        if not isinstance(self.summary, str) or not self.summary.strip():
            raise ValueError("SafeEvidenceItem.summary không được để trống.")
        if len(self.summary) > MAX_EVIDENCE_SUMMARY_LENGTH:
            raise ValueError(
                f"SafeEvidenceItem.summary vượt quá độ dài tối đa {MAX_EVIDENCE_SUMMARY_LENGTH} ký tự "
                f"(hiện tại: {len(self.summary)})."
            )
        if self.verification != "verified":
            raise ValueError(
                f"SafeEvidenceItem.verification bắt buộc phải là 'verified', nhận được '{self.verification}'."
            )
        if not isinstance(self.local_path, str):
            raise TypeError("SafeEvidenceItem.local_path phải là kiểu str.")
        if not isinstance(self.technical_excerpt, str):
            raise TypeError("SafeEvidenceItem.technical_excerpt phải là kiểu str.")
        if len(self.technical_excerpt) > MAX_EXCERPT_LENGTH:
            raise ValueError(
                f"SafeEvidenceItem.technical_excerpt vượt quá {MAX_EXCERPT_LENGTH} ký tự."
            )

        _check_secret_leak(self.summary, "SafeEvidenceItem.summary")
        _check_secret_leak(self.local_path, "SafeEvidenceItem.local_path")
        _check_secret_leak(self.technical_excerpt, "SafeEvidenceItem.technical_excerpt")


@dataclass(frozen=True)
class CaseContext:
    """Ngữ cảnh tóm lược của OperationalCase cho packet C-AGENT."""

    fiscal_year: str
    cost_center_scope: str
    status: str
    stage: str
    classification: str
    confidence: str

    def __post_init__(self) -> None:
        if not isinstance(self.fiscal_year, str) or not self.fiscal_year.strip():
            raise ValueError("CaseContext.fiscal_year không được để trống.")
        if len(self.fiscal_year) > MAX_CONTEXT_FIELD_LENGTH:
            raise ValueError(f"CaseContext.fiscal_year vượt quá {MAX_CONTEXT_FIELD_LENGTH} ký tự.")
        _check_secret_leak(self.fiscal_year, "CaseContext.fiscal_year")

        if not isinstance(self.cost_center_scope, str) or not self.cost_center_scope.strip():
            raise ValueError("CaseContext.cost_center_scope không được để trống.")
        if len(self.cost_center_scope) > MAX_CONTEXT_FIELD_LENGTH:
            raise ValueError(f"CaseContext.cost_center_scope vượt quá {MAX_CONTEXT_FIELD_LENGTH} ký tự.")
        _check_secret_leak(self.cost_center_scope, "CaseContext.cost_center_scope")

        if self.status not in _TERMINAL_RUN_STATUSES:
            raise ValueError(
                f"CaseContext.status ('{self.status}') không phải là trạng thái kết thúc (terminal status)."
            )

        if not isinstance(self.stage, str) or not self.stage.strip():
            raise ValueError("CaseContext.stage không được để trống.")
        if len(self.stage) > MAX_CONTEXT_FIELD_LENGTH:
            raise ValueError(f"CaseContext.stage vượt quá {MAX_CONTEXT_FIELD_LENGTH} ký tự.")
        _check_secret_leak(self.stage, "CaseContext.stage")

        if not isinstance(self.classification, str) or not self.classification.strip():
            raise ValueError("CaseContext.classification không được để trống.")
        if len(self.classification) > MAX_CONTEXT_FIELD_LENGTH:
            raise ValueError(f"CaseContext.classification vượt quá {MAX_CONTEXT_FIELD_LENGTH} ký tự.")
        _check_secret_leak(self.classification, "CaseContext.classification")

        if self.confidence not in _CASE_CONFIDENCES:
            raise ValueError(f"CaseContext.confidence ('{self.confidence}') không hợp lệ.")


@dataclass(frozen=True)
class CagentGuidancePacket:
    """Gói tin yêu cầu hướng dẫn tối giản gửi tới C-AGENT từ một lần chạy đã chọn."""

    packet_id: str
    language: str
    question: str
    case_context: CaseContext
    local_guidance_summary: str
    evidence_items: tuple[SafeEvidenceItem, ...]
    run_id: str = ""
    packet_version: str = CAGENT_CONTRACT_VERSION

    def __post_init__(self) -> None:
        if self.packet_version != CAGENT_CONTRACT_VERSION:
            raise ValueError(
                f"CagentGuidancePacket.packet_version phải là '{CAGENT_CONTRACT_VERSION}'."
            )
        if not isinstance(self.packet_id, str) or not self.packet_id.strip():
            raise ValueError("CagentGuidancePacket.packet_id không được để trống.")
        if self.language not in SUPPORTED_LANGUAGES:
            raise ValueError(f"CagentGuidancePacket.language ('{self.language}') không được hỗ trợ.")
        if not isinstance(self.question, str) or not self.question.strip():
            raise ValueError("CagentGuidancePacket.question không được để trống.")
        if len(self.question) > MAX_QUESTION_LENGTH:
            raise ValueError(
                f"CagentGuidancePacket.question vượt quá độ dài tối đa {MAX_QUESTION_LENGTH} ký tự "
                f"(hiện tại: {len(self.question)})."
            )
        if not isinstance(self.case_context, CaseContext):
            raise TypeError("CagentGuidancePacket.case_context phải là kiểu CaseContext.")
        if not isinstance(self.local_guidance_summary, str) or not self.local_guidance_summary.strip():
            raise ValueError("CagentGuidancePacket.local_guidance_summary không được để trống.")
        if len(self.local_guidance_summary) > MAX_GUIDANCE_SUMMARY_LENGTH:
            raise ValueError(
                f"CagentGuidancePacket.local_guidance_summary vượt quá độ dài tối đa {MAX_GUIDANCE_SUMMARY_LENGTH} ký tự "
                f"(hiện tại: {len(self.local_guidance_summary)})."
            )

        if not isinstance(self.evidence_items, (tuple, list)):
            raise TypeError("CagentGuidancePacket.evidence_items phải là sequence của SafeEvidenceItem.")
        items_tuple = tuple(self.evidence_items)
        object.__setattr__(self, "evidence_items", items_tuple)

        seen_ids: set[str] = set()
        for item in items_tuple:
            if not isinstance(item, SafeEvidenceItem):
                raise TypeError("Mọi phần tử trong evidence_items phải là SafeEvidenceItem.")
            if item.evidence_id in seen_ids:
                raise ValueError(f"Trùng lặp evidence_id '{item.evidence_id}' trong CagentGuidancePacket.")
            seen_ids.add(item.evidence_id)

        _check_secret_leak(self.local_guidance_summary, "CagentGuidancePacket.local_guidance_summary")
        _check_secret_leak(self.question, "CagentGuidancePacket.question")

    def to_dict(self) -> dict[str, Any]:
        """Chuyển đổi packet sang cấu trúc dictionary JSON-serializable."""
        return {
            "contract_version": self.packet_version,
            "packet_id": self.packet_id,
            "run_id": self.run_id,
            "language": self.language,
            "question": self.question,
            "case_context": {
                "fiscal_year": self.case_context.fiscal_year,
                "cost_center_scope": self.case_context.cost_center_scope,
                "status": self.case_context.status,
                "stage": self.case_context.stage,
                "classification": self.case_context.classification,
                "confidence": self.case_context.confidence,
            },
            "local_guidance_summary": self.local_guidance_summary,
            "evidence_items": [
                {
                    "evidence_id": item.evidence_id,
                    "type": item.type,
                    "summary": item.summary,
                    "verification": item.verification,
                    "local_path": item.local_path,
                    "technical_excerpt": item.technical_excerpt,
                }
                for item in self.evidence_items
            ],
        }


@dataclass(frozen=True)
class CagentGuidanceResult:
    """Kết quả phản hồi hướng dẫn từ C-AGENT (chỉ lưu trữ in-memory trong UI)."""

    status: str
    limitation: str
    provider_label: str = "C-AGENT (company service)"
    answer: str = ""
    cited_evidence_ids: tuple[str, ...] = ()
    request_started_at: float | None = None
    packet_id: str = ""

    def __post_init__(self) -> None:
        if self.status not in CAGENT_RESULT_STATUSES:
            raise ValueError(f"CagentGuidanceResult.status ('{self.status}') không hợp lệ.")
        if not isinstance(self.provider_label, str) or not self.provider_label.strip():
            raise ValueError("CagentGuidanceResult.provider_label không được để trống.")
        if not isinstance(self.limitation, str) or not self.limitation.strip():
            raise ValueError("CagentGuidanceResult.limitation không được để trống.")
        if len(self.limitation) > MAX_LIMITATION_LENGTH:
            raise ValueError(
                f"CagentGuidanceResult.limitation vượt quá độ dài tối đa {MAX_LIMITATION_LENGTH} ký tự."
            )
        if not isinstance(self.answer, str):
            raise TypeError("CagentGuidanceResult.answer phải là kiểu str.")
        if len(self.answer) > MAX_ANSWER_LENGTH:
            raise ValueError(
                f"CagentGuidanceResult.answer vượt quá độ dài tối đa {MAX_ANSWER_LENGTH} ký tự."
            )

        if not isinstance(self.cited_evidence_ids, (tuple, list)):
            raise TypeError("CagentGuidanceResult.cited_evidence_ids phải là sequence của str.")
        ids_tuple = tuple(self.cited_evidence_ids)
        for eid in ids_tuple:
            if not isinstance(eid, str) or not eid.strip():
                raise ValueError("Mọi phần tử trong cited_evidence_ids phải là chuỗi không rỗng.")
        object.__setattr__(self, "cited_evidence_ids", ids_tuple)

        if self.status == "ready" and not self.answer.strip():
            raise ValueError("CagentGuidanceResult.answer không được để trống khi status='ready'.")

        if self.request_started_at is not None:
            if isinstance(self.request_started_at, bool) or not isinstance(
                self.request_started_at, (int, float)
            ):
                raise TypeError(
                    f"CagentGuidanceResult.request_started_at phải là float/int hoặc None, "
                    f"nhận được {type(self.request_started_at).__name__}."
                )
            if not math.isfinite(self.request_started_at):
                raise ValueError(
                    f"CagentGuidanceResult.request_started_at phải là số hữu hạn (finite number), "
                    f"nhận được {self.request_started_at}."
                )
            if self.request_started_at < 0:
                raise ValueError(
                    f"CagentGuidanceResult.request_started_at không được âm ({self.request_started_at})."
                )


def load_cagent_provider_policy_from_env(
    environ: dict[str, str] | None = None,
) -> CagentProviderPolicy:
    """Tải chính sách cấu hình triển khai C-AGENT từ biến môi trường.

    Các biến môi trường:
    - CAGENT_ENABLED: '1', 'true', 'yes', 'on' để kích hoạt.
    - CAGENT_ENDPOINT_URL: URL endpoint HTTPS của C-AGENT.
    - CAGENT_DATA_POLICY_ID: Mã chính sách dữ liệu đã phê duyệt.
    - CAGENT_AUTH_MODE: Chế độ xác thực ('none', 'bearer_env').
    - CAGENT_BEARER_TOKEN_ENV: Tên biến môi trường chứa token (mặc định CAGENT_API_KEY).
    - CAGENT_TIMEOUT_SECONDS: Thời gian chờ yêu cầu (1-60 giây).

    Nếu không có cấu hình hoặc cấu hình không hợp lệ, trả về CagentProviderPolicy(enabled=False).
    Tuyệt đối không ném exception ra ngoài ứng dụng.
    """
    import os

    env = os.environ if environ is None else environ
    enabled_raw = str(env.get("CAGENT_ENABLED") or "").strip().lower()
    if enabled_raw not in ("1", "true", "yes", "on"):
        return CagentProviderPolicy(enabled=False)

    endpoint_url = str(env.get("CAGENT_ENDPOINT_URL") or "").strip()
    data_policy_id = str(env.get("CAGENT_DATA_POLICY_ID") or "").strip()
    auth_mode = str(env.get("CAGENT_AUTH_MODE") or "none").strip().lower()
    bearer_env = str(
        env.get("CAGENT_BEARER_TOKEN_ENV")
        or env.get("CAGENT_BEARER_TOKEN_ENV_VAR")
        or "CAGENT_API_KEY"
    ).strip()

    timeout_str = str(
        env.get("CAGENT_TIMEOUT_SECONDS") or env.get("CAGENT_TIMEOUT") or "60"
    ).strip()
    try:
        timeout_sec = int(timeout_str)
    except ValueError:
        timeout_sec = 60
    timeout_sec = max(1, min(60, timeout_sec))

    try:
        return CagentProviderPolicy(
            enabled=True,
            endpoint_url=endpoint_url,
            data_policy_id=data_policy_id,
            auth_mode=auth_mode,
            bearer_token_env_var=bearer_env,
            timeout_seconds=timeout_sec,
        )
    except (ValueError, TypeError):
        return CagentProviderPolicy(enabled=False)
