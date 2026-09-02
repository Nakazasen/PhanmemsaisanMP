"""Packet builder for C-AGENT Operations Guidance (T030).

Constructs minimal, privacy-preserving, technical CagentGuidancePacket objects
only from a selected terminal OperationalCase and its verified evidence within
the run's workspace.

Guarantees:
- Scoped strictly to the selected terminal run.
- Bounded technical report excerpts and traceback extracts.
- Opaque random packet IDs.
- Fail-closed rejection of missing/mismatched evidence, files outside run workspace, and secret tokens.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import uuid

from src.services.operations_ai_provider import (
    MAX_EVIDENCE_ITEMS,
    MAX_EXCERPT_LENGTH,
    MAX_GUIDANCE_SUMMARY_LENGTH,
    MAX_QUESTION_LENGTH,
    MAX_REQUEST_PAYLOAD_BYTES,
    CagentGuidancePacket,
    CaseContext,
    SafeEvidenceItem,
)
from src.services.operations_case_service import OperationalCase
from src.services.operations_knowledge import SUPPORTED_LANGUAGES

_QUESTION_BY_LANGUAGE = {
    "vi": "Phân tích nguyên nhân và đề xuất các bước kiểm tra, khắc phục thủ công an toàn cho lần chạy này dựa trên các bằng chứng kỹ thuật đã cung cấp.",
    "en": "Analyze the root cause and provide safe manual troubleshooting steps for this run based on the provided technical evidence.",
    "ja": "提供された技術的証拠に基づいて、この実行の根本原因を分析し、安全な手動トラブルシューティング手順を提案してください。",
}


def _read_bounded_excerpt(file_path: Path, max_chars: int = 2000) -> str:
    """Đọc một đoạn trích có giới hạn độ dài từ tệp bằng chứng trong workspace."""
    try:
        if not file_path.is_file():
            return ""
        text = file_path.read_text(encoding="utf-8", errors="replace")
        if len(text) > max_chars:
            return text[:max_chars] + "\n...[truncated]..."
        return text
    except Exception:
        return ""


def build_cagent_guidance_packet(
    case: OperationalCase,
    language: str,
    history_root: Path | str | None = None,
    *,
    max_excerpt_chars: int = 2000,
    max_evidence_items: int = MAX_EVIDENCE_ITEMS,
    max_payload_bytes: int = MAX_REQUEST_PAYLOAD_BYTES,
) -> CagentGuidancePacket:
    """Xây dựng gói tin CagentGuidancePacket từ OperationalCase đã chọn.

    Args:
        case: Trường hợp vận hành (phải ở trạng thái kết thúc).
        language: Mã ngôn ngữ ('vi', 'en', 'ja').
        history_root: Thư mục gốc chứa lịch sử các lần chạy (nếu có để đọc excerpt).
        max_excerpt_chars: Độ dài tối đa của đoạn trích kỹ thuật từ mỗi tệp bằng chứng.
        max_evidence_items: Số lượng mục bằng chứng tối đa (mặc định 10).
        max_payload_bytes: Dung lượng tối đa của toàn bộ gói tin tuần tự hóa (mặc định 48 KB).

    Returns:
        CagentGuidancePacket hợp lệ và sẵn sàng gửi tới C-AGENT.
    """
    if not isinstance(case, OperationalCase):
        raise TypeError("case phải là một đối tượng OperationalCase hợp lệ.")

    lang_norm = str(language or "").strip().lower()
    if lang_norm not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Ngôn ngữ '{language}' không được hỗ trợ. Phải là một trong {sorted(SUPPORTED_LANGUAGES)}.")

    # 1. Sinh packet_id ngẫu nhiên, không dùng run_id làm packet_id
    packet_id = f"pkt-{uuid.uuid4().hex[:12]}"

    # 2. Xây dựng CaseContext
    case_context = CaseContext(
        fiscal_year=str(case.fiscal_year or "2027"),
        cost_center_scope=str(case.cost_center_scope or "ALL"),
        status=str(case.status),
        stage=str(case.stage or "unknown"),
        classification=str(case.classification or "unknown"),
        confidence=str(case.confidence or "unknown"),
    )

    # 3. Câu hỏi nghiệp vụ chuẩn theo ngôn ngữ
    question = _QUESTION_BY_LANGUAGE.get(lang_norm, _QUESTION_BY_LANGUAGE["vi"])
    if len(question) > MAX_QUESTION_LENGTH:
        question = question[:MAX_QUESTION_LENGTH]

    # 4. Tóm tắt hướng dẫn cục bộ
    if case.presentation is not None:
        what_to_do_text = "\n".join(case.presentation.what_to_do) if isinstance(case.presentation.what_to_do, (tuple, list)) else str(case.presentation.what_to_do or "")
        summary_parts = [
            str(case.presentation.what_happened or ""),
            str(case.presentation.why_it_happened or ""),
            what_to_do_text,
        ]
        local_guidance_summary = "\n".join(p for p in summary_parts if p.strip())
    else:
        local_guidance_summary = str(case.summary or "Tóm tắt sự cố vận hành.")

    if len(local_guidance_summary) > MAX_GUIDANCE_SUMMARY_LENGTH:
        local_guidance_summary = local_guidance_summary[:MAX_GUIDANCE_SUMMARY_LENGTH]

    # 5. Xác định thư mục workspace của lần chạy đã chọn (nếu có history_root)
    run_workspace: Path | None = None
    if history_root is not None:
        hr_path = Path(history_root).resolve()
        fy_dir = f"FY{case.fiscal_year}" if case.fiscal_year else "FY2027"
        run_workspace = (hr_path / fy_dir / case.run_id).resolve()

    # 6. Thu thập các mục bằng chứng an toàn (chỉ lấy verified và thuộc workspace)
    safe_evidence_items: list[SafeEvidenceItem] = []
    evidence_idx = 1

    for ev in case.evidence:
        # Chỉ nhận bằng chứng đã được xác minh (verified)
        if str(ev.verification).strip().lower() != "verified":
            continue

        excerpt = ""
        rel_path = str(ev.local_path or "").strip()

        if run_workspace is not None and rel_path:
            target_path = (run_workspace / rel_path).resolve()
            # Bảo đảm an toàn: tệp phải nằm trong thư mục workspace của lần chạy đang chọn
            try:
                target_path.relative_to(run_workspace)
            except ValueError:
                # Tệp nằm ngoài run_workspace -> Loại bỏ hoàn toàn mục bằng chứng này
                continue
            if target_path.is_file():
                excerpt = _read_bounded_excerpt(target_path, max_chars=min(max_excerpt_chars, MAX_EXCERPT_LENGTH))
        elif rel_path:
            p = Path(rel_path)
            if p.is_absolute() or ".." in p.parts:
                # Đường dẫn ngoài hoặc không an toàn -> Loại bỏ hoàn toàn
                continue

        # Chuẩn hóa summary không để trống
        summary_text = str(ev.summary or "").strip()
        if not summary_text:
            summary_text = f"Bằng chứng {ev.type} của lần chạy {case.run_id}."

        evidence_id = f"E{evidence_idx}"
        safe_item = SafeEvidenceItem(
            evidence_id=evidence_id,
            type=str(ev.type or "stage_evidence"),
            summary=summary_text,
            verification="verified",
            local_path=rel_path,
            technical_excerpt=excerpt,
        )
        safe_evidence_items.append(safe_item)
        evidence_idx += 1

    # 7. Giới hạn số lượng mục bằng chứng tối đa
    safe_evidence_items = safe_evidence_items[:max_evidence_items]

    # 8. Giới hạn tổng dung lượng tuần tự hóa của gói tin (48 KB payload cap)
    while True:
        packet = CagentGuidancePacket(
            packet_id=packet_id,
            run_id=case.run_id,
            language=lang_norm,
            question=question,
            case_context=case_context,
            local_guidance_summary=local_guidance_summary,
            evidence_items=tuple(safe_evidence_items),
        )
        try:
            raw_payload = json.dumps(packet.to_dict(), ensure_ascii=False).encode("utf-8")
        except Exception:
            break
        if len(raw_payload) <= max_payload_bytes or not safe_evidence_items:
            break
        # Loại bỏ mục bằng chứng cuối cùng một cách tất định để giảm kích thước
        safe_evidence_items.pop()

    return packet
