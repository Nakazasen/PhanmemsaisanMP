"""Gemini Web comparison path for the Operations Assistant.

It first talks to a locally running ``gemini-web-to-api`` sidecar when one is
available.  If that sidecar is not running, it uses the same Gemini Web
StreamGenerate path already used by AIOS_habbit.  Neither path asks the
desktop user for a Gemini API key or writes a credential to disk.
"""

from __future__ import annotations

import json
import os
import re
import ssl
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable

from src.services.i18n import translate_for_language
from src.services.operations_ai_packet import build_cagent_guidance_packet
from src.services.operations_ai_provider import MAX_ANSWER_LENGTH, CagentGuidanceResult
from src.services.operations_case_service import OperationalCase


DEFAULT_GEMINI_WEB_PROXY_URL = "http://127.0.0.1:8081/v1/chat/completions"
GEMINI_WEB_PROXY_MODEL = "gemini-3.6-flash"
_DEFAULT_GEMINI_BL = "boq_assistant-bard-web-server_20260821.03_p0"
_CURRENT_GEMINI_BL = _DEFAULT_GEMINI_BL
_MAX_RESPONSE_BYTES = 256 * 1024
_PROXY_COOLDOWN_SECONDS: float = 30.0
_PROXY_HTTP_TIMEOUT_SECONDS: float = 5.0
_proxy_disabled_until: float = 0.0

GeminiTransport = Callable[[str, dict[str, str], bytes, float], tuple[int, bytes]]


def is_proxy_available() -> bool:
    """Kiểm tra proxy cục bộ có đang trong thời gian cooldown hay không."""
    global _proxy_disabled_until
    return time.monotonic() >= _proxy_disabled_until


def mark_proxy_failed() -> None:
    """Đánh dấu proxy cục bộ tạm thời không khả dụng trong 30 giây."""
    global _proxy_disabled_until
    _proxy_disabled_until = time.monotonic() + _PROXY_COOLDOWN_SECONDS


def mark_proxy_success() -> None:
    """Đánh dấu proxy cục bộ hoạt động bình thường và reset cooldown."""
    global _proxy_disabled_until
    _proxy_disabled_until = 0.0


def reset_proxy_cooldown() -> None:
    """Reset trạng thái cooldown của proxy (dùng cho testing hoặc khi proxy phục hồi)."""
    global _proxy_disabled_until
    _proxy_disabled_until = 0.0


def check_local_proxy_running(timeout: float = 0.3) -> bool:
    """Kiểm tra xem proxy cục bộ (mặc định 127.0.0.1:8081) có đang mở kết nối hay không."""
    import socket
    parsed = urllib.parse.urlparse(_proxy_url())
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8081
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, socket.timeout):
        return False


def _proxy_url() -> str:
    return os.environ.get("GEMINI_WEB_PROXY_URL", DEFAULT_GEMINI_WEB_PROXY_URL).strip() or DEFAULT_GEMINI_WEB_PROXY_URL


def _prompt_for_packet(packet: Any) -> str:
    return (
        "You are an MP2027 operations business assistant for non-technical planners and accountants. "
        "Reply in the requested language using friendly, accessible, simple terms. Explain what happened "
        "in plain language and provide at most 3 clear, safe manual next steps (such as checking Excel files "
        "or software inputs). Do NOT quote raw stack traces, exceptions, programming code, JSON syntax, "
        "or technical file internals. Do not claim to have modified files or rerun anything. Here is the "
        "run summary and evidence:\n\n"
        + json.dumps(packet.to_dict(), ensure_ascii=False)
    )


def _extract_gemini_web_text(raw: str) -> str:
    """Extract the final answer from Gemini Web's ``wrb.fr`` stream."""
    texts: list[str] = []
    for line in raw.splitlines():
        if '"wrb.fr"' not in line:
            continue
        try:
            outer = json.loads(line)
            encoded = outer[0][2]
            inner = json.loads(encoded)
            for part in inner[4] or ():
                for text in part[1] or ():
                    if isinstance(text, str) and text.strip():
                        texts.append(text)
        except (IndexError, TypeError, json.JSONDecodeError):
            continue
    return texts[-1].strip() if texts else ""


def _displayable_answer(answer: str) -> str:
    """Remove Gemini UI markup and keep a compact, readable operator answer."""
    cleaned = re.sub(r"<FollowUp\b.*?(?:/>|</FollowUp>)", "", str(answer or ""), flags=re.IGNORECASE | re.DOTALL)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = cleaned.replace("**", "").replace("`", "")
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned[:MAX_ANSWER_LENGTH]


def _refresh_gemini_bl() -> str:
    global _CURRENT_GEMINI_BL
    try:
        request = urllib.request.Request(
            "https://gemini.google.com/app",
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
        )
        with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=10) as response:
            page = response.read().decode("utf-8", errors="replace")
        match = re.search(r"(boq_assistant-bard-web-server_\d+\.\d+_p\d+)", page)
        if match:
            _CURRENT_GEMINI_BL = match.group(1)
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        pass
    return _CURRENT_GEMINI_BL


def _request_direct_gemini_web(prompt: str) -> str:
    """Use the anonymous Gemini Web path from AIOS_habbit as an experiment."""
    inner: list[Any] = [None] * 80
    inner[0] = [prompt, 0, None, None, None, None, 0]
    inner[1] = ["en"]
    inner[2] = ["", "", "", None, None, None, None, None, None, ""]
    inner[6], inner[7], inner[10], inner[11] = [0], 1, 1, 0
    inner[17], inner[18], inner[27], inner[30] = [[4]], 0, 1, [4]
    inner[41], inner[53], inner[59], inner[61] = [2], 0, str(uuid.uuid4()), []
    inner[68], inner[79] = 1, 1
    body = urllib.parse.urlencode({"f.req": json.dumps([None, json.dumps(inner)])}).encode("utf-8")
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Origin": "https://gemini.google.com",
        "Referer": "https://gemini.google.com/app",
        "X-Same-Domain": "1",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    endpoint = (
        "https://gemini.google.com/_/BardChatUi/data/"
        "assistant.lamda.BardFrontendService/StreamGenerate"
        f"?bl={_refresh_gemini_bl()}&hl=en&_reqid={int(time.time()) % 1_000_000}&rt=c"
    )
    request = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
    last_answer = ""
    total_bytes = 0
    with urllib.request.urlopen(request, context=ssl.create_default_context(), timeout=60) as response:
        for line in response:
            total_bytes += len(line)
            if total_bytes > _MAX_RESPONSE_BYTES:
                raise RuntimeError("Gemini Web response is too large")
            line_str = line.decode("utf-8", errors="replace")
            if '"wrb.fr"' in line_str:
                candidate = _extract_gemini_web_text(line_str)
                if candidate:
                    last_answer = candidate
    if not last_answer:
        raise RuntimeError("Gemini Web returned no text")
    return last_answer


def request_gemini_web_guidance(
    case: OperationalCase,
    language: str,
    history_root: Path | str | None = None,
    *,
    transport: GeminiTransport | None = None,
) -> CagentGuidanceResult:
    """Ask Gemini Web about the selected run, without collecting an API key."""
    try:
        packet = build_cagent_guidance_packet(case, language, history_root=history_root)
        prompt = _prompt_for_packet(packet)
    except Exception:
        return CagentGuidanceResult(
            status="failed",
            provider_label="Gemini Web",
            limitation=translate_for_language("operations_assistant_ai_failed", language),
        )

    proxy_body = json.dumps(
        {"model": GEMINI_WEB_PROXY_MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False},
        ensure_ascii=False,
    ).encode("utf-8")
    if transport is not None:
        try:
            status, response_bytes = transport(_proxy_url(), {"Content-Type": "application/json"}, proxy_body, 60.0)
            if status != 200 or len(response_bytes) > _MAX_RESPONSE_BYTES:
                raise RuntimeError("Gemini Web proxy unavailable")
            answer = str(json.loads(response_bytes.decode("utf-8"))["choices"][0]["message"]["content"] or "").strip()
            if not answer:
                raise RuntimeError("Gemini Web proxy returned no text")
            mark_proxy_success()
            provider_label = "Gemini Web (local proxy)"
        except Exception:
            return CagentGuidanceResult(
                status="unavailable",
                provider_label="Gemini Web (local proxy)",
                limitation=translate_for_language("operations_assistant_gemini_proxy_unavailable", language),
                packet_id=packet.packet_id,
            )
    else:
        proxy_succeeded = False
        answer = ""
        provider_label = ""
        if is_proxy_available() and check_local_proxy_running():
            try:
                request = urllib.request.Request(_proxy_url(), data=proxy_body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=_PROXY_HTTP_TIMEOUT_SECONDS) as response:
                    status, response_bytes = response.getcode(), response.read(_MAX_RESPONSE_BYTES + 1)
                if status == 200 and len(response_bytes) <= _MAX_RESPONSE_BYTES:
                    answer = str(json.loads(response_bytes.decode("utf-8"))["choices"][0]["message"]["content"] or "").strip()
                    if answer:
                        mark_proxy_success()
                        proxy_succeeded = True
                        provider_label = "Gemini Web (local proxy)"
                if not proxy_succeeded:
                    mark_proxy_failed()
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError, IndexError, TypeError, RuntimeError, json.JSONDecodeError):
                mark_proxy_failed()
        elif is_proxy_available():
            mark_proxy_failed()

        if not proxy_succeeded:
            try:
                answer = _request_direct_gemini_web(prompt)
                provider_label = "Gemini Web Direct"
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, ValueError):
                return CagentGuidanceResult(
                    status="unavailable",
                    provider_label="Gemini Web Direct",
                    limitation=translate_for_language("operations_assistant_gemini_proxy_unavailable", language),
                    packet_id=packet.packet_id,
                )

    return CagentGuidanceResult(
        status="ready",
        provider_label=provider_label,
        answer=_displayable_answer(answer),
        limitation=translate_for_language("operations_assistant_ai_advisory_notice", language),
        packet_id=packet.packet_id,
    )


def request_gemini_web_business_guidance(
    question: str,
    local_context: str,
    language: str,
    intent: str = "business",
    *,
    history: list[dict[str, str]] | None = None,
    transport: GeminiTransport | None = None,
) -> CagentGuidanceResult:
    """Use Gemini Web as the primary answer source for an MP2027 business chat."""
    language_name = {"vi": "Vietnamese", "ja": "Japanese", "en": "English"}.get(language, "Vietnamese")

    if intent == "incident":
        intent_rules = (
            "- Question Intent: INCIDENT_OR_TROUBLESHOOTING.\n"
            "- The user is reporting an operational error/issue or requesting troubleshooting guidance.\n"
            "- Explain and troubleshoot the incident STRICTLY based on the provided case diagnosis context.\n"
            "- If the context states that no matching incident or error case was found, do NOT speculate, invent reasons, or name specific unconfirmed errors. State concisely that no matching incident was found and advise checking Run History or on-screen error messages.\n"
            "- Provide direct troubleshooting guidance based strictly on the provided incident/case context.\n"
            "- Provide at most 3 clear, safe manual action steps.\n"
        )
    elif intent == "clarify":
        intent_rules = (
            "- Question Intent: CLARIFICATION_NEEDED.\n"
            "- The user's question lacks sufficient context, scope, or parameters (e.g. asking for counts or amounts without specifying fiscal year or cost center).\n"
            "- Do NOT guess or invent numbers, rules, or data.\n"
            "- Ask exactly ONE focused, concise question in " + language_name + " to clarify the missing scope (for example: whether they need the count of cost groups or individual line items, and for which fiscal year or cost center).\n"
            "- Do NOT mention system health, normality, or errors.\n"
        )
    else:
        intent_rules = (
            "- Question Intent: BUSINESS_INQUIRY.\n"
            "- Answer the user's actual question first. Do NOT add any preamble (such as greeting or pleasantries).\n"
            "- Do NOT add any health or incident statement unless the user explicitly asks about an error/status or the curated context describes a specific incident.\n"
            "- Absolutely do NOT discuss system normality, absence of failures, troubleshooting procedures, or run histories for business questions unless the user explicitly asked about an error.\n"
            "- For a how-to question, give only the steps relevant to that task; do not turn it into a troubleshooting response. Only include action steps if the question specifically asks for how-to or procedure.\n"
            "- For a count or amount question, use an exact number only when it is present in the curated context. Otherwise, explain briefly what the count depends on and ask for the one missing scope (for example fiscal year, cost center, or whether the user means cost groups or cost rows). Never invent a number.\n"
        )

    history_context = ""
    if history:
        history_lines = []
        for turn in history[-6:]:
            role_label = "User" if turn.get("role") == "user" else "Assistant"
            content = str(turn.get("content") or "").strip()
            if content:
                history_lines.append(f"{role_label}: {content[:350]}")
        if history_lines:
            history_context = "Recent conversation context:\n" + "\n".join(history_lines) + "\n\n"

    prompt = (
        f"You are the MP2027 internal business assistant. Answer in {language_name}.\n"
        "Crucial Environment Rules:\n"
        "- MP2027 is a local Windows desktop application for budget planning and cost allocations from Excel files.\n"
        "- It is NOT a web application. NEVER tell users to press F5/refresh browser, clear browser cache, or log out/log in.\n"
        "- The main desktop UI buttons are: 'Quét lại nội dung' (Rescan / 再スキャン) and 'CHẠY TÍNH TOÁN' (Run Calculation / 計算実行).\n"
        "- CRITICAL BUSINESS DEFINITION: 'MP' in MP2027 stands for 'Master Plan' (Kế hoạch tổng thể / 中期経営計画・マスタープラン). It does NOT mean 'Man Power', 'Member of Parliament', or anything else. Always explain MP as Master Plan.\n"
        f"{intent_rules}"
        "Guidelines for non-technical users (accountants / operations staff):\n"
        "- Use friendly, simple, and direct language that anyone can easily understand.\n"
        "- Strictly avoid technical developer jargon (e.g. traceback, exception, pipeline, JSON, SQL, function, variable, bug, internal code).\n"
        "- Give a direct answer in 1-2 sentences. Add at most 3 concrete steps only when they help answer the question.\n"
        "- Keep it concise, helpful, and polite.\n\n"
        f"{history_context}"
        f"Question: {str(question or '').strip()[:500]}\n\n"
        f"Curated internal knowledge (pre-approved business guidance):\n{str(local_context or '').strip()[:1000]}"
    )
    if not str(question or "").strip():
        return CagentGuidanceResult(
            status="unavailable",
            provider_label="Gemini Web",
            limitation=translate_for_language("operations_assistant_gemini_proxy_unavailable", language),
        )
    body = json.dumps(
        {"model": GEMINI_WEB_PROXY_MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False},
        ensure_ascii=False,
    ).encode("utf-8")
    if transport is not None:
        try:
            status, response_bytes = transport(_proxy_url(), {"Content-Type": "application/json"}, body, 60.0)
            if status != 200 or len(response_bytes) > _MAX_RESPONSE_BYTES:
                raise RuntimeError("Gemini Web proxy unavailable")
            answer = str(json.loads(response_bytes.decode("utf-8"))["choices"][0]["message"]["content"] or "").strip()
            if not answer:
                raise RuntimeError("Gemini Web proxy returned no text")
            mark_proxy_success()
            provider_label = "Gemini Web (local proxy)"
        except Exception:
            return CagentGuidanceResult(
                status="unavailable",
                provider_label="Gemini Web (local proxy)",
                limitation=translate_for_language("operations_assistant_gemini_proxy_unavailable", language),
            )
    else:
        proxy_succeeded = False
        answer = ""
        provider_label = ""
        if is_proxy_available() and check_local_proxy_running():
            try:
                request = urllib.request.Request(_proxy_url(), data=body, headers={"Content-Type": "application/json"}, method="POST")
                with urllib.request.urlopen(request, timeout=_PROXY_HTTP_TIMEOUT_SECONDS) as response:
                    status, response_bytes = response.getcode(), response.read(_MAX_RESPONSE_BYTES + 1)
                if status == 200 and len(response_bytes) <= _MAX_RESPONSE_BYTES:
                    answer = str(json.loads(response_bytes.decode("utf-8"))["choices"][0]["message"]["content"] or "").strip()
                    if answer:
                        mark_proxy_success()
                        proxy_succeeded = True
                        provider_label = "Gemini Web (local proxy)"
                if not proxy_succeeded:
                    mark_proxy_failed()
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, KeyError, IndexError, TypeError, RuntimeError, json.JSONDecodeError):
                mark_proxy_failed()
        elif is_proxy_available():
            mark_proxy_failed()

        if not proxy_succeeded:
            try:
                answer = _request_direct_gemini_web(prompt)
                provider_label = "Gemini Web Direct"
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, RuntimeError, ValueError):
                return CagentGuidanceResult(
                    status="unavailable",
                    provider_label="Gemini Web Direct",
                    limitation=translate_for_language("operations_assistant_gemini_proxy_unavailable", language),
                )
    return CagentGuidanceResult(
        status="ready",
        provider_label=provider_label,
        answer=_displayable_answer(answer),
        limitation=translate_for_language("operations_assistant_ai_advisory_notice", language),
    )
