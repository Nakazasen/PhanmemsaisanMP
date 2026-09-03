"""Query decomposition engine for MP2027 RAG Retrieval.

Decomposes complex, multi-intent user questions into independent, focused
sub-queries for comprehensive multi-query document retrieval.

Design Invariants:
1. Deterministic & Offline: Zero external NLP service or LLM dependency.
2. Zero Over-splitting: Single-intent queries with compound nouns
   (e.g., 'chi phí chung và riêng', 'software update and version rollback',
   'thứ tự xử lý file nguồn và dòng phân cách') remain intact as single queries.
3. Multilingual Support: First-class decomposition for Vietnamese (VI),
   English (EN), and Japanese (JA).
4. Multi-turn Context Resolution: Resolves anaphoric pronouns and conversational
   follow-ups using prior user turn history.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Sequence

SUPPORTED_LANGUAGES: tuple[str, ...] = ("vi", "en", "ja")

# Minimum token / char lengths for a valid standalone sub-query
_MIN_SUBQUERY_WORDS: int = 2
_MIN_SUBQUERY_CHARS: int = 4

# Vietnamese action, question, and intent starters
_VI_INTENT_STARTERS: tuple[str, ...] = (
    "làm sao", "làm thế nào", "như thế nào", "thế nào", "ở đâu", "vào đâu",
    "khi nào", "tại sao", "vì sao", "ai", "gì", "cái gì", "bao nhiêu",
    "cách", "hướng dẫn", "quy trình", "quy tắc", "thao tác", "các bước", "bước",
    "tra cứu", "kiểm tra", "xác định", "xử lý", "khắc phục", "sửa", "sửa lỗi",
    "tìm", "nhập", "xuất", "tính", "tính toán", "phân bổ", "giải thích",
    "cho tôi hỏi", "cho em hỏi", "cho hỏi", "tôi muốn", "hỏi về", "xem", "đọc",
    "bổ sung", "khai báo", "cấu hình", "cài đặt", "sao chép", "chia",
)

# English action, question, and intent starters
_EN_INTENT_STARTERS: tuple[str, ...] = (
    "how", "what", "where", "why", "when", "who", "which",
    "can", "could", "should", "would", "is", "are", "do", "does",
    "please", "tell", "guide", "explain", "lookup", "find", "calculate",
    "allocate", "input", "import", "export", "check", "verify", "resolve",
    "fix", "troubleshoot", "steps", "procedure", "rule", "rules",
)

# Japanese action, question, and intent starters
_JA_INTENT_STARTERS: tuple[str, ...] = (
    "どう", "何", "どこ", "なぜ", "いつ", "だれ", "誰",
    "方法", "手順", "ルール", "特定", "確認", "検索", "計算",
    "配賦", "入力", "出力", "対処", "解除", "設定", "教えて",
)

# Strong multi-word conjunctions in Vietnamese that unambiguously signal clause boundaries
_VI_STRONG_CONJUNCTIONS: tuple[str, ...] = (
    "đồng thời", "ngoài ra", "với lại", "tiện thể", "bên cạnh đó", "mặt khác",
)

# Regular expression to strip leading list markers or bullets
_LIST_MARKER_PATTERN = re.compile(
    r"^\s*(?:[-*+•–—]|\d+[\.\)\/:]|\(\d+\))\s*",
)

# Regular expression to match inline numbered or bulleted list separators
_INLINE_LIST_PATTERN = re.compile(
    r"(?:^|[\s;；,，])(?:[-*+•–—]|\d+[\.\)\/:]|\(\d+\))\s+",
)

# Regular expression to split multiple question marks or semicolons
_QUESTION_MARK_SPLIT = re.compile(r"[?？]+")
_SEMICOLON_SPLIT = re.compile(r"[;；]+")

# Elliptical / continuation question starters that imply reference to previous topic
_ELLIPTICAL_STARTERS: dict[str, tuple[str, ...]] = {
    "vi": (
        "tại sao", "vì sao", "sao lại", "thế nào", "ra sao", "làm sao",
        "như thế nào", "khi nào", "ở đâu", "vào đâu", "còn", "vậy còn",
        "thế còn", "thế thì", "vậy thì",
    ),
    "en": (
        "why", "how come", "what about", "how about", "then", "when",
        "where", "how so", "why so",
    ),
    "ja": (
        "なぜ", "どうして", "理由は", "どうやって", "どのように",
        "では", "それでは", "その場合",
    ),
}

# Multi-turn anaphoric reference patterns
_ANAPHORIC_PATTERNS: dict[str, tuple[re.Pattern[str], ...]] = {
    "vi": (
        re.compile(r"\b(?:nó|cái\s+đó|vấn\s+đề\s+(?:này|đó)|lỗi\s+(?:này|đó)|sự\s+cố\s+(?:này|đó)|trường\s+hợp\s+(?:này|đó)|ở\s+trên|như\s+vậy|thế\s+này|thế\s+đó|việc\s+(?:này|đó)|khi\s+đó|lúc\s+đó)\b", re.IGNORECASE),
        re.compile(r"^(?:tại\s+sao|vì\s+sao|làm\s+sao|thế\s+nào|khi\s+nào|ở\s+đâu)\s+(?:lại|thì|phải)\b", re.IGNORECASE),
        re.compile(r"^(?:còn|vậy\s+còn)\s+", re.IGNORECASE),
    ),
    "en": (
        re.compile(r"\b(?:it|its|this|that|these|those|this\s+error|that\s+error|this\s+issue|that\s+issue|this\s+problem|that\s+problem|the\s+issue|the\s+error)\b", re.IGNORECASE),
        re.compile(r"^(?:why|how|when|where)\s+(?:does|did|is|can)\s+(?:this|it|that)\b", re.IGNORECASE),
        re.compile(r"^(?:what\s+about|how\s+about)\s+", re.IGNORECASE),
    ),
    "ja": (
        re.compile(r"(?:それ|その|この|これ|このエラー|そのエラー|その問題|この問題|その理由|なぜそれ|どうしてそれ|対象の|該当の)"),
        re.compile(r"^(?:では、|それでは、|その場合、)"),
    ),
}


def _normalize_subquery_text(text: str) -> str:
    """Clean and standardize a sub-query string."""
    clean = unicodedata.normalize("NFC", text).strip()
    # Strip list markers and bullets
    clean = _LIST_MARKER_PATTERN.sub("", clean).strip()

    # Strip leftover leading conjunctions
    clean = re.sub(
        r"^(?:và|đồng\s+thời|ngoài\s+ra|với\s+lại|tiện\s+thể|bên\s+cạnh\s+đó|mặt\s+khác|cũng\s+như|còn|lẫn(?:\s+cả)?|and|as\s+well\s+as|also|additionally|また|および|さらに)[,\s、，]+",
        "",
        clean,
        flags=re.IGNORECASE,
    ).strip()

    # Strip surrounding trailing punctuation (keep trailing '?' if part of natural question)
    clean = re.sub(r"^[\s;；,，:：\-–—\.、。]+|[\s;；,，:：\-–—\.、。]+$", "", clean).strip()

    if not clean:
        return ""

    # Capitalize first character for readability
    if clean[0].islower():
        clean = clean[0].upper() + clean[1:]

    return clean


def _is_meaningful_subquery(text: str, language: str = "vi") -> bool:
    """Validate that a candidate sub-query has enough substance to stand alone."""
    clean = text.strip()
    if len(clean) < _MIN_SUBQUERY_CHARS:
        return False

    lang = str(language or "vi").lower()
    if lang == "ja":
        # Japanese CJK text doesn't always have spaces; check non-punctuation char count
        cjk_chars = [c for c in clean if not c.isspace() and c not in "?？!！;；,，.。"]
        return len(cjk_chars) >= 3

    # For VI and EN: check word count
    words = [w for w in re.findall(r"\b\w+\b", clean) if len(w) > 0]
    return len(words) >= _MIN_SUBQUERY_WORDS


def _starts_with_any(text: str, starters: Sequence[str]) -> bool:
    """Check if normalized text starts with any of the intent starter phrases."""
    norm = text.lower().strip()
    for starter in starters:
        if norm.startswith(starter):
            return True
        # Also check with preceding commas/spaces stripped
        if norm.startswith(f"{starter} "):
            return True
    return False


def _contains_cjk(text: str) -> bool:
    """Check if text contains Japanese/Chinese characters."""
    return bool(re.search(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff]", text))


# Coordinated compound word pairs that should never be split by conjunctions
_VI_COMPOUND_PAIRS: tuple[tuple[str, str], ...] = (
    ("chung", "riêng"),
    ("riêng", "chung"),
    ("thu", "chi"),
    ("chi", "thu"),
    ("nhập", "xuất"),
    ("xuất", "nhập"),
    ("lãi", "lỗ"),
    ("lời", "lỗ"),
    ("nguồn", "dòng"),
    ("nguồn", "đích"),
    ("nợ", "có"),
    ("tăng", "giảm"),
    ("lớn", "nhỏ"),
    ("trong", "ngoài"),
)

_EN_COMPOUND_PAIRS: tuple[tuple[str, str], ...] = (
    ("update", "rollback"),
    ("version", "rollback"),
    ("input", "output"),
    ("import", "export"),
    ("source", "target"),
    ("debit", "credit"),
    ("profit", "loss"),
)


def _has_intent_starter_or_tail(text: str, starters: Sequence[str], lang: str = "vi") -> bool:
    """Check if text starts with intent starters or ends with interrogative/intent phrases."""
    if _starts_with_any(text, starters):
        return True
    norm = text.lower().rstrip("?？!！. ，,、。 ")
    words = [w for w in re.findall(r"\b\w+\b", norm) if w]
    if lang == "vi":
        tail_markers = (
            "như thế nào", "thế nào", "ra sao", "ở đâu", "vào đâu", "thì sao",
            "là gì", "khi nào", "bao nhiêu", "được không", "sao", "thế",
        )
        for t in tail_markers:
            if norm.endswith(t):
                t_words = t.split()
                # Must have at least 2 words before the tail marker (not a dangling modifier like 'riêng thế nào')
                if len(words) - len(t_words) >= 2:
                    return True
    elif lang == "en":
        tail_markers = ("where", "why", "how", "what", "when", "rules", "rule", "lookup", "guide", "procedure", "steps")
        for t in tail_markers:
            if norm.endswith(t):
                t_words = t.split()
                if len(words) - len(t_words) >= 2:
                    return True
    return False


def _split_by_conjunctions(
    segment: str,
    language: str,
) -> list[str]:
    """Split a single segment by coordinating conjunctions if both sides represent valid intents."""
    lang = str(language or "vi").lower()
    norm = segment.strip()
    if not norm:
        return []

    # 1. Check strong multi-word conjunctions in Vietnamese
    for conj in _VI_STRONG_CONJUNCTIONS:
        pattern = re.compile(rf"\s*(?:,\s*)?{re.escape(conj)}\s*", re.IGNORECASE)
        parts = pattern.split(norm)
        if len(parts) >= 2:
            cleaned_parts = [_normalize_subquery_text(p) for p in parts if p.strip()]
            if len(cleaned_parts) >= 2 and all(_is_meaningful_subquery(p, "vi") for p in cleaned_parts):
                results: list[str] = []
                for p in cleaned_parts:
                    results.extend(_split_by_conjunctions(p, language))
                return results

    # 2. Check 'cũng như' (as well as) in Vietnamese
    if "cũng như" in norm.lower():
        pattern = re.compile(r"\s*(?:,\s*)?cũng\s+như\s+", re.IGNORECASE)
        parts = pattern.split(norm)
        if len(parts) >= 2:
            # Check if right part has action/intent starter or >= 3 words
            right = parts[1].strip()
            if _starts_with_any(right, _VI_INTENT_STARTERS) or len(right.split()) >= 3:
                cleaned_parts = [_normalize_subquery_text(p) for p in parts if p.strip()]
                if len(cleaned_parts) >= 2 and all(_is_meaningful_subquery(p, "vi") for p in cleaned_parts):
                    results = []
                    for p in cleaned_parts:
                        results.extend(_split_by_conjunctions(p, language))
                    return results

    # 3. Check 'và' (and) in Vietnamese
    # Only split if 'và' coordinates two distinct clauses/questions, NOT compound nouns
    if " và " in norm.lower() or ", và " in norm.lower():
        # Look for 'và' followed by intent starter or preceded by comma
        va_matches = list(re.finditer(r"(?:,\s*và\s+|\s+và\s+)", norm, re.IGNORECASE))
        for m in va_matches:
            left = norm[:m.start()].strip()
            right = norm[m.end():].strip()

            # Guard against splitting coordinated compound pairs (e.g. 'chung và riêng', 'nguồn và dòng')
            left_words = re.findall(r"\b\w+\b", left.lower())
            right_words = re.findall(r"\b\w+\b", right.lower())
            if left_words and right_words:
                if any(left_words[-1] == p[0] and right_words[0] == p[1] for p in _VI_COMPOUND_PAIRS):
                    continue

            # Guard against splitting simple noun pairs:
            # Right side must start with an intent starter OR be preceded by comma with >= 3 words
            is_comma_va = m.group(0).startswith(",")
            right_has_intent = _has_intent_starter_or_tail(right, _VI_INTENT_STARTERS, "vi")
            left_has_intent = _has_intent_starter_or_tail(left, _VI_INTENT_STARTERS, "vi") or any(
                term in left.lower() for term in ("lỗi", "file", "tệp", "chi phí", "phân bổ", "cách", "hướng dẫn", "quy trình", "quy tắc")
            )

            if (right_has_intent or (is_comma_va and len(right.split()) >= 3)) and left_has_intent:
                cleaned_left = _normalize_subquery_text(left)
                cleaned_right = _normalize_subquery_text(right)
                if _is_meaningful_subquery(cleaned_left, "vi") and _is_meaningful_subquery(cleaned_right, "vi"):
                    res_left = _split_by_conjunctions(cleaned_left, language)
                    res_right = _split_by_conjunctions(cleaned_right, language)
                    return res_left + res_right

    # 4. Check 'còn' in Vietnamese
    if ", còn " in norm.lower() or " còn " in norm.lower():
        con_matches = list(re.finditer(r"(?:,\s*còn\s+|\s+còn\s+)", norm, re.IGNORECASE))
        for m in con_matches:
            left = norm[:m.start()].strip()
            right = norm[m.end():].strip()
            if _starts_with_any(right, _VI_INTENT_STARTERS) or right.lower().endswith(("thế nào", "ra sao", "ở đâu", "thì sao", "như thế nào")):
                cleaned_left = _normalize_subquery_text(left)
                cleaned_right = _normalize_subquery_text(right)
                if _is_meaningful_subquery(cleaned_left, "vi") and _is_meaningful_subquery(cleaned_right, "vi"):
                    res_left = _split_by_conjunctions(cleaned_left, language)
                    res_right = _split_by_conjunctions(cleaned_right, language)
                    return res_left + res_right

    # 5. Check 'lẫn' / 'lẫn cả' in Vietnamese
    if " lẫn " in norm.lower() or ", lẫn " in norm.lower() or ",lẫn " in norm.lower():
        lan_matches = list(re.finditer(r"(?:,\s*lẫn(?:\s+cả)?\s+|\s+lẫn(?:\s+cả)?\s+)", norm, re.IGNORECASE))
        for m in lan_matches:
            left = norm[:m.start()].strip()
            right = norm[m.end():].strip()
            # Guard against compound phrases: 'pha lẫn', 'trộn lẫn', 'lẫn lộn'
            if left.lower().endswith(("pha", "trộn", "hoà", "hòa")) or right.lower().startswith("lộn"):
                continue
            left_words = re.findall(r"\b\w+\b", left.lower())
            right_words = re.findall(r"\b\w+\b", right.lower())
            if left_words and right_words:
                if any(left_words[-1] == p[0] and right_words[0] == p[1] for p in _VI_COMPOUND_PAIRS):
                    continue
            is_comma_lan = m.group(0).startswith(",")
            right_has_intent = _has_intent_starter_or_tail(right, _VI_INTENT_STARTERS, "vi")
            left_has_intent = _has_intent_starter_or_tail(left, _VI_INTENT_STARTERS, "vi") or any(
                term in left.lower() for term in ("lỗi", "file", "tệp", "chi phí", "phân bổ", "cách", "hướng dẫn", "quy trình", "quy tắc")
            )
            if (right_has_intent or is_comma_lan or len(right.split()) >= 3) and left_has_intent:
                cleaned_left = _normalize_subquery_text(left)
                cleaned_right = _normalize_subquery_text(right)
                if _is_meaningful_subquery(cleaned_left, "vi") and _is_meaningful_subquery(cleaned_right, "vi"):
                    res_left = _split_by_conjunctions(cleaned_left, language)
                    res_right = _split_by_conjunctions(cleaned_right, language)
                    return res_left + res_right

    # 6. Check clause-separating comma in Vietnamese (followed by intent starter)
    if (lang == "vi") and (", " in norm or "，" in norm):
        comma_matches = list(re.finditer(r"(?:,\s*|，\s*)", norm))
        for m in comma_matches:
            left = norm[:m.start()].strip()
            right = norm[m.end():].strip()
            if _starts_with_any(right, _VI_INTENT_STARTERS) and len(right.split()) >= 3:
                cleaned_left = _normalize_subquery_text(left)
                cleaned_right = _normalize_subquery_text(right)
                if _is_meaningful_subquery(cleaned_left, "vi") and _is_meaningful_subquery(cleaned_right, "vi"):
                    res_left = _split_by_conjunctions(cleaned_left, language)
                    res_right = _split_by_conjunctions(cleaned_right, language)
                    return res_left + res_right

    # 7. English conjunctions: 'as well as', 'and also', 'and'
    if lang == "en" or not _contains_cjk(norm):
        # as well as
        if "as well as" in norm.lower():
            pattern = re.compile(r"\s*(?:,\s*)?as\s+well\s+as\s+", re.IGNORECASE)
            parts = pattern.split(norm)
            if len(parts) >= 2:
                cleaned_parts = [_normalize_subquery_text(p) for p in parts if p.strip()]
                if len(cleaned_parts) >= 2 and all(_is_meaningful_subquery(p, "en") for p in cleaned_parts):
                    results: list[str] = []
                    for p in cleaned_parts:
                        results.extend(_split_by_conjunctions(p, language))
                    return results

        # and also / additionally
        for en_conj in ("and also", "additionally"):
            pattern = re.compile(rf"\s*(?:,\s*)?{re.escape(en_conj)}\s+", re.IGNORECASE)
            parts = pattern.split(norm)
            if len(parts) >= 2:
                cleaned_parts = [_normalize_subquery_text(p) for p in parts if p.strip()]
                if len(cleaned_parts) >= 2 and all(_is_meaningful_subquery(p, "en") for p in cleaned_parts):
                    results = []
                    for p in cleaned_parts:
                        results.extend(_split_by_conjunctions(p, language))
                    return results

        # 'and': split only when followed by an intent starter or preceded by comma
        if " and " in norm.lower() or ", and " in norm.lower():
            and_matches = list(re.finditer(r"(?:,\s*and\s+|\s+and\s+)", norm, re.IGNORECASE))
            for m in and_matches:
                left = norm[:m.start()].strip()
                right = norm[m.end():].strip()

                # Guard against splitting coordinated compound pairs in English
                left_words = re.findall(r"\b\w+\b", left.lower())
                right_words = re.findall(r"\b\w+\b", right.lower())
                if left_words and right_words:
                    if any(left_words[-1] == p[0] and right_words[0] == p[1] for p in _EN_COMPOUND_PAIRS):
                        continue

                is_comma_and = m.group(0).startswith(",")
                right_has_intent = _has_intent_starter_or_tail(right, _EN_INTENT_STARTERS, "en")
                left_has_intent = _has_intent_starter_or_tail(left, _EN_INTENT_STARTERS, "en") or any(
                    term in left.lower() for term in ("how", "what", "error", "file", "cost", "allocation", "rule", "rules")
                )

                if (right_has_intent or (is_comma_and and len(right.split()) >= 3)) and left_has_intent:
                    cleaned_left = _normalize_subquery_text(left)
                    cleaned_right = _normalize_subquery_text(right)
                    if _is_meaningful_subquery(cleaned_left, "en") and _is_meaningful_subquery(cleaned_right, "en"):
                        res_left = _split_by_conjunctions(cleaned_left, language)
                        res_right = _split_by_conjunctions(cleaned_right, language)
                        return res_left + res_right

    # 8. Japanese conjunctions: 'また', 'および', 'と'
    if lang == "ja" or _contains_cjk(norm):
        # また (mata / also, furthermore)
        if "また" in norm:
            pattern = re.compile(r"(?:、|\s)*また(?:、|\s)*")
            parts = pattern.split(norm)
            if len(parts) >= 2:
                cleaned_parts = [_normalize_subquery_text(p) for p in parts if p.strip()]
                if len(cleaned_parts) >= 2 and all(_is_meaningful_subquery(p, "ja") for p in cleaned_parts):
                    results = []
                    for p in cleaned_parts:
                        results.extend(_split_by_conjunctions(p, language))
                    return results

        # および (oyobi / as well as, and)
        if "および" in norm:
            pattern = re.compile(r"(?:、|\s)*および(?:、|\s)*")
            parts = pattern.split(norm)
            if len(parts) >= 2:
                # Ensure it's not just two single nouns, check length
                if all(len(p.strip()) >= 5 for p in parts):
                    cleaned_parts = [_normalize_subquery_text(p) for p in parts if p.strip()]
                    if len(cleaned_parts) >= 2 and all(_is_meaningful_subquery(p, "ja") for p in cleaned_parts):
                        results = []
                        for p in cleaned_parts:
                            results.extend(_split_by_conjunctions(p, language))
                        return results

        # と、 / と (to / and)
        if "と、" in norm or " と " in norm:
            pattern = re.compile(r"(?:と、|\s+と\s+)")
            parts = pattern.split(norm)
            if len(parts) >= 2 and all(len(p.strip()) >= 5 for p in parts):
                cleaned_parts = [_normalize_subquery_text(p) for p in parts if p.strip()]
                if len(cleaned_parts) >= 2 and all(_is_meaningful_subquery(p, "ja") for p in cleaned_parts):
                    results = []
                    for p in cleaned_parts:
                        results.extend(_split_by_conjunctions(p, language))
                    return results

        # Japanese comma '、' separating two complete clauses
        if "、" in norm:
            parts = norm.split("、")
            if len(parts) >= 2 and all(len(p.strip()) >= 8 for p in parts):
                cleaned_parts = [_normalize_subquery_text(p) for p in parts if p.strip()]
                if len(cleaned_parts) >= 2 and all(_is_meaningful_subquery(p, "ja") for p in cleaned_parts):
                    results = []
                    for p in cleaned_parts:
                        results.extend(_split_by_conjunctions(p, language))
                    return results

    return [norm]


def decompose_query(query: str, language: str = "vi") -> list[str]:
    """Decompose a complex user query into independent, focused sub-queries.

    For single-intent questions, returns a list with the original query unchanged.
    For compound questions (separated by conjunctions, punctuation, bullet points,
    or numbered lists), returns normalized, standalone sub-queries.
    """
    raw = str(query or "").strip()
    if not raw:
        return []

    lang = str(language or "vi").strip().lower()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "vi"

    # Step 1: Split by newlines (multiline lists or bulleted items)
    lines = [line.strip() for line in re.split(r"[\r\n]+", raw) if line.strip()]
    initial_segments: list[str] = []

    if len(lines) >= 2:
        for line in lines:
            cleaned = _LIST_MARKER_PATTERN.sub("", line).strip()
            if cleaned:
                initial_segments.append(cleaned)
    else:
        # Step 2: Check for inline numbered or bulleted list (e.g., '1. ... 2. ...' or '- ... - ...')
        inline_matches = list(_INLINE_LIST_PATTERN.finditer(raw))
        if len(inline_matches) >= 2:
            parts: list[str] = []
            last_idx = 0
            for i, m in enumerate(inline_matches):
                if i == 0 and m.start() > 0:
                    prefix = raw[:m.start()].strip()
                    if prefix:
                        parts.append(prefix)
                elif i > 0:
                    part = raw[last_idx:m.start()].strip()
                    if part:
                        parts.append(part)
                last_idx = m.end()
            trailing = raw[last_idx:].strip()
            if trailing:
                parts.append(trailing)
            initial_segments = parts
        elif len(inline_matches) == 1 and inline_matches[0].start() > 0:
            m = inline_matches[0]
            prefix = raw[:m.start()].strip()
            suffix = raw[m.end():].strip()
            if _is_meaningful_subquery(prefix, lang) and _is_meaningful_subquery(suffix, lang):
                initial_segments = [prefix, suffix]
            else:
                initial_segments = [raw]
        else:
            initial_segments = [raw]

    # Step 3: Split each segment by question marks, Japanese full stops, and semicolons
    punct_segments: list[str] = []
    for seg in initial_segments:
        # Split by question marks if multiple questions exist
        q_parts = [p.strip() for p in _QUESTION_MARK_SPLIT.split(seg) if p.strip()]
        for qp in q_parts:
            # Japanese sentence full stop split
            if (lang == "ja" or _contains_cjk(qp)) and "。" in qp:
                ja_parts = [jp.strip() for jp in re.split(r"[。]+", qp) if jp.strip()]
            else:
                ja_parts = [qp]
            for jp in ja_parts:
                # Semicolon split
                s_parts = [sp.strip() for sp in _SEMICOLON_SPLIT.split(jp) if sp.strip()]
                punct_segments.extend(s_parts)

    # Step 4: Split by coordinating conjunctions
    final_subqueries: list[str] = []
    for seg in punct_segments:
        decomp = _split_by_conjunctions(seg, lang)
        for item in decomp:
            cleaned = _normalize_subquery_text(item)
            if cleaned and _is_meaningful_subquery(cleaned, lang):
                final_subqueries.append(cleaned)

    # Deduplicate while preserving order
    seen: set[str] = set()
    deduped: list[str] = []
    for sq in final_subqueries:
        key = sq.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(sq)

    # Fallback: if no valid sub-queries were formed or only 1, return the original raw query
    if len(deduped) <= 1:
        return [raw.strip()]

    return deduped


def resolve_multiturn_query(
    question: str,
    history: list[dict[str, str]] | None = None,
    language: str = "vi",
) -> str:
    """Resolve anaphoric references (pronouns) and follow-up questions from conversation history.

    Inherits context from prior user questions if the current question contains
    pronouns (e.g., 'nó', 'lỗi đó', 'it', 'that error', 'そのエラー') or is an elliptical
    continuation (e.g., 'Tại sao lại bị lỗi?', 'Why?', 'なぜ？').

    Does NOT pollute standalone questions with previous turn context.
    Idempotent: safe if called repeatedly.
    """
    raw = str(question or "").strip()
    if not history or not raw:
        return raw

    # Find the most recent user turn
    prev_user_queries = [
        str(turn.get("content", "")).strip()
        for turn in history
        if turn.get("role") == "user" and str(turn.get("content", "")).strip()
    ]
    if not prev_user_queries:
        return raw

    last_user_query = prev_user_queries[-1]

    # Idempotency guard: if last_user_query is already prepended, do not repeat
    if last_user_query.lower() in raw.lower():
        return raw

    lang = str(language or "vi").strip().lower()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "vi"

    # Check 1: Explicit anaphoric references / pronouns
    patterns = _ANAPHORIC_PATTERNS.get(lang, _ANAPHORIC_PATTERNS["vi"])
    for pat in patterns:
        if pat.search(raw):
            return f"{last_user_query} {raw}"

    # Check 2: Elliptical follow-up questions (e.g. "Tại sao?", "Vì sao?", "Why?", "How come?", "なぜ？")
    norm_lower = raw.lower()
    elliptical = _ELLIPTICAL_STARTERS.get(lang, _ELLIPTICAL_STARTERS["vi"])
    for starter in elliptical:
        if norm_lower.startswith(starter):
            if lang == "ja" and len(raw) <= 15:
                return f"{last_user_query} {raw}"
            elif lang != "ja" and len(raw.split()) <= 6:
                return f"{last_user_query} {raw}"

    return raw
