"""Document-grounded RAG v3 retrieval engine for MP2027.

Provides hybrid lexical and semantic-ready retrieval over indexed document chunks
in VI/EN/JA with authority weighting, confidence thresholds, and fail-closed safety.

Design Invariants:
1. Zero network dependency: Operates entirely offline with deterministic ranking.
2. Authority hierarchy: Canonical sources receive priority over supporting sources;
   historical/superseded documents are never retrieved.
3. Cross-lingual grounding: Allows EN/JA queries to retrieve relevant Vietnamese canonical
   specification documents when no native translation exists, while prioritizing
   same-language translations when available.
4. Strict confidentiality: No local filesystem paths, pipeline packet internals, or
   developer tracebacks are included in formatted contexts or user fallbacks.
5. Pluggable backend: Exposes RetrievalBackend protocol for future IT-approved vector backends.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence, runtime_checkable

from src.services.business_chat_knowledge import get_source_label, get_source_registry
from src.services.business_knowledge_index import DocumentChunk, get_knowledge_index

SUPPORTED_LANGUAGES: tuple[str, ...] = ("vi", "en", "ja")
MIN_CONFIDENCE_SCORE: int = 7
_MAX_RESULTS: int = 3

# Scoring weights
_SCORE_EXACT_ALIAS: int = 10
_SCORE_EXACT_TITLE: int = 8
_SCORE_EXACT_CODE: int = 14
_SCORE_EXACT_KEYWORD: int = 6
_SCORE_TITLE_TOKEN: int = 4
_SCORE_KEYWORD_TOKEN: int = 3
_SCORE_TEXT_TOKEN: int = 2
_SCORE_UNACCENTED_MATCH: int = 4
_SCORE_CJK_BIGRAM: int = 3
_SCORE_SAME_LANGUAGE_BOOST: int = 4
_SCORE_CANONICAL_BOOST: int = 2
_SCORE_FY_RECENCY_BOOST: int = 8

_STOP_WORDS: dict[str, frozenset[str]] = {
    "en": frozenset({
        "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "has", "he",
        "in", "is", "it", "its", "of", "on", "that", "the", "to", "was", "were", "will",
        "with", "what", "when", "where", "which", "who", "why", "how", "get", "getting",
        "do", "does", "did", "can", "could", "should", "would", "about", "guide", "help",
        "today", "now", "day", "time", "weather", "recipe", "cook", "food",
    }),
    "vi": frozenset({
        "la", "va", "cho", "cua", "o", "tai", "duoc", "cach", "lam", "the", "nao", "gi",
        "huong", "dan", "co", "khong", "thi", "ma", "cac", "nhung", "mot", "nhu", "voi",
        "trong", "tren", "hay", "hoi", "ve", "hom", "nay", "mai", "ngay", "gio", "thoi",
        "tiet", "cho", "biet", "xin", "nau", "an", "mon", "ngon", "phap", "y",
    }),
    "ja": frozenset({
        "の", "に", "は", "を", "た", "が", "で", "て", "と", "し", "れ", "さ", "ある",
        "いる", "も", "する", "から", "な", "こと", "として", "い", "や", "れる", "など",
        "今日", "天気", "何", "どう", "料理", "作り方", "ご飯", "美味しい",
    }),
}

# ---------------------------------------------------------------------------
# Intent Classification Rules (Strict Multi-lingual Routing)
# ---------------------------------------------------------------------------

_BUSINESS_OVERRIDE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Questions asking why allocation is done a certain way (business reason)
    re.compile(r"tại\s+sao.*(?:phân\s+bổ|chia\s+chi\s+phí|tính\s+chi\s+phí|50/50|tỷ\s+lệ|kết\s+quả)", re.IGNORECASE),
    re.compile(r"why.*(?:allocat|distribut|split|cost\s+center|50/50|proportion)", re.IGNORECASE),
    re.compile(r"なぜ.*(?:配賦|按分|割り当て|費用|50/50|割合)", re.IGNORECASE),
    # Questions asking where to enter data or input missing data
    re.compile(r"(?:nhập|điền|khai\s+báo|bổ\s+sung).*(?:ở\s+đâu|vào\s+đâu|mục\s+nào|trang\s+tính\s+nào|file\s+nào)", re.IGNORECASE),
    re.compile(r"(?:ở\s+đâu|vào\s+đâu).*(?:nhập|điền|khai\s+báo|bổ\s+sung)", re.IGNORECASE),
    re.compile(r"(?:where|how).*(?:enter|input|fill|import|record)", re.IGNORECASE),
    re.compile(r"where\s+do\s+i\s+(?:enter|input|find|fill)", re.IGNORECASE),
    re.compile(r"(?:どこに入力|どこで入力|どこに登録|どこで登録)", re.IGNORECASE),
    # Questions asking about usage, how-to, general guides
    re.compile(r"^(?:cách|hướng\s+dẫn)\s+sử\s+dụng", re.IGNORECASE),
    re.compile(r"^(?:how\s+to\s+use|how\s+do\s+i\s+use|user\s+guide)", re.IGNORECASE),
    re.compile(r"(?:の使い方|使用方法|利用方法)", re.IGNORECASE),
    # Questions asking about definitions, e.g. closing
    re.compile(r"(?:khóa\s+sổ|khoá\s+sổ).*(?:là\s+gì|như\s+thế\s+nào)", re.IGNORECASE),
    re.compile(r"(?:quy\s+trình|thao\s+tác|các\s+bước).*(?:kiểm\s+tra|tính\s+toán|phân\s+bổ)", re.IGNORECASE),
)

_CLARIFY_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Count / quantity questions lacking specific context/scope
    re.compile(r"(?:co\s+)?bao\s+nhieu\s+(?:chi\s+phi|khoan\s+chi|nhom\s+chi\s+phi|dong\s+chi\s+phi|cost\s+center|trung\s+tam\s+chi\s+phi|phong\s+ban|bo\s+phan|quy\s+tac|chi\s+tieu)", re.IGNORECASE),
    re.compile(r"^(?:mp|mp2027|phan\s+mem)?\s*(?:co\s+)?bao\s+nhieu\s+chi\s+phi\??$", re.IGNORECASE),
    re.compile(r"^(?:tong\s+)?chi\s+phi\s+la\s+bao\s+nhieu\??$", re.IGNORECASE),
    re.compile(r"^(?:so\s+luong\s+)?(?:chi\s+phi|khoan\s+chi)\s+la\s+bao\s+nhieu\??$", re.IGNORECASE),
    re.compile(r"how\s+many\s+(?:expenses|costs|cost\s+items|cost\s+categories|cost\s+centers|departments|allocation\s+rules|items)", re.IGNORECASE),
    re.compile(r"^(?:what\s+is\s+the\s+total\s+cost|how\s+much\s+is\s+the\s+cost)\??$", re.IGNORECASE),
    re.compile(r"(?:費用|コスト|勘定科目|部門|コストセンター|配賦ルール|項目)(?:は|が)?(?:いくつ|何個|何件|いくら)", re.IGNORECASE),
    re.compile(r"^(?:mp|mp2027)?(?:には)?(?:費用|コスト)(?:は|が)?いくつ(?:ありますか)?\??$", re.IGNORECASE),
)

_INCIDENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Vietnamese incident signals
    re.compile(r"(?:chạy|tính\s+toán|xuất\s+excel|tiến\s+trình|hệ\s+thống|quá\s+trình|ứng\s+dụng).*(?:bị\s+dừng|dừng\s+lại|dừng\s+đột\s+ngột|thất\s+bại|bị\s+crash|bị\s+treo|bị\s+đơ|bị\s+lỗi)", re.IGNORECASE),
    re.compile(r"(?:bị\s+dừng|dừng\s+lại|dừng\s+khi|thất\s+bại|bị\s+lỗi|bị\s+crash|bị\s+treo).*(?:khi\s+chạy|khi\s+tính|khi\s+xuất|khi\s+export|khi\s+lưu|khi\s+đang)", re.IGNORECASE),
    re.compile(r"(?:không\s+chạy\s+được|không\s+mở\s+được|không\s+xuất\s+được|không\s+lưu\s+được|không\s+ghi\s+được|không\s+đọc\s+được\s+file)", re.IGNORECASE),
    re.compile(r"(?:báo\s+lỗi|gặp\s+lỗi|phát\s+sinh\s+lỗi|gặp\s+sự\s+cố|phát\s+sinh\s+sự\s+cố)", re.IGNORECASE),
    re.compile(r"(?:lỗi\s+này\s+là\s+gì|lỗi\s+gì\s+đây|sự\s+cố\s+này\s+là\s+gì|nguyên\s+nhân\s+gây\s+lỗi|khắc\s+phục\s+sự\s+cố|xử\s+lý\s+sự\s+cố|hướng\s+dẫn\s+sửa\s+lỗi|cách\s+sửa\s+lỗi|cách\s+xử\s+lý\s+lỗi|cách\s+khắc\s+phục)", re.IGNORECASE),
    re.compile(r"(?:lỗi\s+file\s+(?:bị\s+)?khóa|lỗi\s+thiếu\s+nhân\s+sự|lỗi\s+khóa\s+file|lỗi\s+tiền\s+trạm|lỗi\s+validation|lỗi\s+preflight|lỗi\s+permission|file\s+bị\s+khóa)", re.IGNORECASE),
    re.compile(r"(?:khắc\s+phục|sửa\s+lỗi|xử\s+lý).*(?:file\s+bị\s+khóa|khóa\s+file|lỗi|sự\s+cố)", re.IGNORECASE),
    re.compile(r"(?:sự\s+cố|lỗi).*(?:không\s+chạy\s+được|thất\s+bại|bị\s+khóa|bị\s+treo)", re.IGNORECASE),
    re.compile(r"tại\s+sao.*(?:thất\s+bại|bị\s+lỗi|bị\s+dừng|bị\s+crash|không\s+chạy\s+được)", re.IGNORECASE),
    re.compile(r"(?:lỗi\s+file\s+kết\s+quả|file\s+kết\s+quả\s+bị\s+khóa).*(?:xử\s+lý\s+thế\s+nào|làm\s+sao|cần\s+làm\s+gì)", re.IGNORECASE),
    re.compile(r"^(?:lỗi\s+này\s+là\s+gì\??|sự\s+cố\s+gì\??)$", re.IGNORECASE),

    # English incident signals
    re.compile(r"(?:calculation|run|process|export|software|application).*(?:stopped|failed|crashed|interrupted|errored|hang|hung)", re.IGNORECASE),
    re.compile(r"(?:stopped|failed|crashed|interrupted).*(?:when\s+exporting|when\s+running|during\s+calculation|during\s+export|while\s+exporting)", re.IGNORECASE),
    re.compile(r"(?:cannot\s+open|failed\s+to\s+open|cannot\s+export|failed\s+to\s+export|cannot\s+save|failed\s+to\s+save|permission\s+denied)", re.IGNORECASE),
    re.compile(r"(?:encountered\s+an\s+error|got\s+an\s+error|what\s+does\s+this\s+error\s+mean|what\s+is\s+this\s+error|how\s+to\s+fix\s+this\s+error|how\s+to\s+resolve\s+this\s+error|troubleshoot\s+error|troubleshoot\s+missing\s+staffing|resolve\s+locked\s+output|resolve\s+issue\s+with)", re.IGNORECASE),
    re.compile(r"why\s+did\s+the\s+(?:calculation|run|export|process)\s+fail", re.IGNORECASE),
    re.compile(r"how\s+to\s+(?:fix|resolve)\s+(?:locked\s+(?:output\s+)?excel|locked\s+file)", re.IGNORECASE),

    # Japanese incident signals
    re.compile(r"(?:計算|処理|実行|エクスポート|書き出し|アプリ).*(?:停止した|中断した|失敗した|エラーで止ま|クラッシュした|フリーズした)", re.IGNORECASE),
    re.compile(r"(?:停止した|失敗した|クラッシュした).*(?:計算|処理|エクスポート時|実行時)", re.IGNORECASE),
    re.compile(r"(?:ファイルが開けない|出力できない|保存できない|読み込めない|ロック解除|ファイルロックの解除)", re.IGNORECASE),
    re.compile(r"(?:エラーが発生|エラーが出た|障害が発生|エラーの原因|エラーの対処|このエラーは何|エラーの意味|エラーの修正|どうすれば対処できますか|ロックされた場合の対処)", re.IGNORECASE),
    re.compile(r"(?:処理が失敗した原因|なぜ計算が失敗した)", re.IGNORECASE),
)


def classify_question_intent(query: str, language: str = "vi") -> str:
    """Phân loại ý định câu hỏi của người dùng thành: 'incident', 'clarify', hoặc 'business'.

    - 'incident': Người dùng đang báo lỗi/sự cố thực tế hoặc hỏi cách khắc phục một sự cố cụ thể.
    - 'clarify': Câu hỏi thiếu ngữ cảnh/phạm vi (ví dụ: hỏi số lượng chi phí mà không rõ năm tài chính/phòng ban).
    - 'business': Câu hỏi về cách sử dụng phần mềm, quy trình, nghiệp vụ, chi phí, dữ liệu, phân bổ, kết quả.
    """
    raw = str(query or "").strip()
    if not raw:
        return "business"

    norm = unicodedata.normalize("NFC", raw)
    unaccented = _strip_vietnamese_diacritics(norm).lower()

    # 1. Kiểm tra ưu tiên nghiệp vụ rõ ràng (hỏi tại sao phân bổ, hỏi nơi nhập liệu, hỏi cách sử dụng)
    # Tránh nhầm các từ 'tại sao', 'thiếu', 'khóa' trong câu hỏi nghiệp vụ thành incident
    for p in _BUSINESS_OVERRIDE_PATTERNS:
        if p.search(norm):
            return "business"

    # 2. Kiểm tra câu hỏi cần làm rõ phạm vi (clarify)
    for p in _CLARIFY_PATTERNS:
        if p.search(norm) or p.search(unaccented):
            # Nếu câu hỏi đã có đầy đủ FY và Cost Center cụ thể (vd: FY2028 phòng 1412000040), giữ là business
            has_fy = bool(re.search(r"\bfy20\d\d\b", norm, re.IGNORECASE))
            has_cc = bool(re.search(r"\b\d{4,}\b", norm))
            if has_fy and has_cc:
                return "business"
            return "clarify"

    # 3. Kiểm tra tín hiệu sự cố / lỗi thực tế (incident)
    for p in _INCIDENT_PATTERNS:
        if p.search(norm):
            return "incident"

    # 4. Mặc định an toàn: business
    return "business"


def _normalize_text(text: str) -> str:
    """Normalize text for matching: NFC, lowercase, strip."""
    return unicodedata.normalize("NFC", text).lower().strip()


def _strip_vietnamese_diacritics(text: str) -> str:
    """Strip Vietnamese tone marks and convert đ/Đ to d/D."""
    normalized = _normalize_text(text)
    nfkd = unicodedata.normalize("NFKD", normalized)
    stripped = "".join(c for c in nfkd if unicodedata.category(c) != "Mn")
    stripped = stripped.replace("đ", "d").replace("Đ", "D")
    return stripped.strip()


def _cjk_bigrams(text: str) -> set[str]:
    """Generate character bigrams from CJK runs in text for Japanese matching."""
    cjk_pattern = re.compile(r"[\u3040-\u309f\u30a0-\u30ff\u4e00-\u9fff\u3400-\u4dbf]+")
    bigrams: set[str] = set()
    for match in cjk_pattern.finditer(text):
        run = match.group()
        for i in range(len(run) - 1):
            bigrams.add(run[i:i + 2])
    return bigrams


def _tokenize(text: str) -> set[str]:
    """Extract word tokens (>=2 chars) for keyword matching."""
    normalized = _normalize_text(text)
    return {t for t in re.findall(r"[\wÀ-ỹぁ-んァ-ヶ一-龯]{2,}", normalized) if t}


@runtime_checkable
class RetrievalBackend(Protocol):
    """Protocol for pluggable retrieval backends (lexical, hybrid, or future vector)."""

    def search(
        self, query: str, language: str, top_k: int = _MAX_RESULTS,
    ) -> list[DocumentChunk]:
        """Return top matching DocumentChunk objects for query in language."""
        ...  # pragma: no cover


class HybridDocumentRetrievalEngine:
    """Deterministic hybrid retrieval engine over indexed DocumentChunk objects."""

    def score_chunk(
        self,
        chunk: DocumentChunk,
        lang: str,
        norm_query: str,
        query_tokens: set[str],
        query_unaccented: str,
        query_bigrams: set[str],
    ) -> tuple[int, list[str]]:
        """Score a single chunk against normalized query representations."""
        if not chunk.external_shareable or chunk.authority not in ("canonical", "supporting", "caveat", "reference_with_caveat"):
            return 0, []

        # Allow matching chunks in the same language OR canonical Vietnamese chunks for EN/JA queries
        is_same_language = (chunk.language == lang)
        is_cross_lingual = (not is_same_language and chunk.language == "vi" and lang in ("en", "ja"))
        if not is_same_language and not is_cross_lingual:
            return 0, []

        title_norm = _normalize_text(chunk.section_title)
        text_norm = _normalize_text(chunk.text)
        steps_norm = " ".join(_normalize_text(s) for s in chunk.safe_steps)
        combined_text = f"{title_norm} {text_norm} {steps_norm}"

        stop_words = _STOP_WORDS.get(lang, frozenset())
        meaningful_query_tokens = query_tokens - stop_words
        if not meaningful_query_tokens and not query_bigrams and not query_unaccented:
            return 0, []

        score = 0
        reasons: list[str] = []
        has_strong_signal = False

        # 1. Exact alias match
        for alias in chunk.aliases:
            norm_alias = _normalize_text(alias)
            if norm_alias and (norm_alias in norm_query or norm_query in norm_alias):
                score += _SCORE_EXACT_ALIAS
                has_strong_signal = True
                reasons.append(f"exact_alias:{norm_alias}(+{_SCORE_EXACT_ALIAS})")
                break

        # 2. Exact code / entity ID match (for example, a cost-center ID)
        for token in meaningful_query_tokens:
            if re.match(r"^\d{4,}$", token) and token in combined_text:
                score += _SCORE_EXACT_CODE
                has_strong_signal = True
                reasons.append(f"exact_code_token:{token}(+{_SCORE_EXACT_CODE})")

        # 3. Exact phrase in section title
        if norm_query and len(norm_query) >= 4 and norm_query in title_norm:
            score += _SCORE_EXACT_TITLE
            has_strong_signal = True
            reasons.append(f"exact_phrase_in_title(+{_SCORE_EXACT_TITLE})")

        # Exact keyword phrase match
        for kw in chunk.keywords:
            norm_kw = _normalize_text(kw)
            if norm_kw and len(norm_kw) >= 3 and norm_kw in norm_query:
                score += _SCORE_EXACT_KEYWORD
                has_strong_signal = True
                reasons.append(f"exact_keyword:{norm_kw}(+{_SCORE_EXACT_KEYWORD})")
                break

        # 4. Section title token overlap (only meaningful tokens)
        title_tokens = _tokenize(title_norm) - stop_words
        matching_title = meaningful_query_tokens & title_tokens
        if matching_title:
            pts = len(matching_title) * _SCORE_TITLE_TOKEN
            score += pts
            has_strong_signal = True
            reasons.append(f"title_tokens:{matching_title}(+{pts})")

        # 5. Keyword token overlap
        all_kw_tokens = set()
        for kw in chunk.keywords:
            all_kw_tokens.update(_tokenize(kw))
        all_kw_tokens -= stop_words
        matching_kws = meaningful_query_tokens & all_kw_tokens
        if matching_kws:
            pts = len(matching_kws) * _SCORE_KEYWORD_TOKEN
            score += pts
            has_strong_signal = True
            reasons.append(f"keyword_tokens:{matching_kws}(+{pts})")

        # 6. Body text token overlap
        body_tokens = _tokenize(combined_text) - stop_words
        matching_body = meaningful_query_tokens & body_tokens
        if len(matching_body) >= 2 or (matching_body and has_strong_signal):
            pts = len(matching_body) * _SCORE_TEXT_TOKEN
            score += pts
            reasons.append(f"body_tokens:{matching_body}(+{pts})")

        # 7. Vietnamese unaccented matching (VI query only)
        if lang == "vi" and query_unaccented:
            title_unaccented = _strip_vietnamese_diacritics(title_norm)
            body_unaccented = _strip_vietnamese_diacritics(combined_text)
            for alias in chunk.aliases:
                alias_unaccented = _strip_vietnamese_diacritics(alias)
                if alias_unaccented and (alias_unaccented in query_unaccented or query_unaccented in alias_unaccented):
                    score += _SCORE_UNACCENTED_MATCH * 2
                    has_strong_signal = True
                    reasons.append(f"unaccented_alias:{alias_unaccented}(+{_SCORE_UNACCENTED_MATCH * 2})")
                    break
            if len(query_unaccented) >= 4 and query_unaccented in title_unaccented:
                score += _SCORE_UNACCENTED_MATCH
                has_strong_signal = True
                reasons.append(f"unaccented_title(+{_SCORE_UNACCENTED_MATCH})")
            else:
                unacc_stop = _STOP_WORDS.get("vi", frozenset())
                unaccented_query_tokens = _tokenize(query_unaccented) - unacc_stop
                if unaccented_query_tokens:
                    body_unacc_tokens = _tokenize(body_unaccented) - unacc_stop
                    title_unacc_tokens = _tokenize(title_unaccented) - unacc_stop
                    matching_unacc_title = unaccented_query_tokens & title_unacc_tokens
                    matching_unacc_body = unaccented_query_tokens & body_unacc_tokens
                    if matching_unacc_title:
                        pts = len(matching_unacc_title) * _SCORE_UNACCENTED_MATCH
                        score += pts
                        has_strong_signal = True
                        reasons.append(f"unaccented_title_tokens:{matching_unacc_title}(+{pts})")
                    elif len(matching_unacc_body) >= 2 and has_strong_signal:
                        pts = len(matching_unacc_body) * _SCORE_UNACCENTED_MATCH
                        score += pts
                        reasons.append(f"unaccented_body_tokens:{matching_unacc_body}(+{pts})")

        # 8. Japanese CJK bigram matching (JA query against chunk text)
        if lang == "ja" and query_bigrams:
            chunk_bigrams = _cjk_bigrams(f"{title_norm} {combined_text}")
            matching_bigrams = query_bigrams & chunk_bigrams
            if matching_bigrams:
                pts = len(matching_bigrams) * _SCORE_CJK_BIGRAM
                score += pts
                has_strong_signal = True
                reasons.append(f"cjk_bigrams:{matching_bigrams}(+{pts})")

        # 9. Same-language priority boost (native translation favored over cross-lingual fallback)
        if is_same_language and has_strong_signal:
            score += _SCORE_SAME_LANGUAGE_BOOST
            reasons.append(f"same_lang_boost(+{_SCORE_SAME_LANGUAGE_BOOST})")

        # 10. Authority weighting: canonical boost (only if genuine match with strong signal)
        if score >= MIN_CONFIDENCE_SCORE and has_strong_signal and chunk.authority == "canonical":
            score += _SCORE_CANONICAL_BOOST
            reasons.append(f"canonical_boost(+{_SCORE_CANONICAL_BOOST})")

        # 11. Fiscal year recency boost for newer confirmed rules (e.g. FY2028 > FY2027)
        if (
            score >= MIN_CONFIDENCE_SCORE
            and has_strong_signal
            and chunk.authority == "canonical"
            and getattr(chunk, "fiscal_year", "FY2027") > "FY2027"
        ):
            score += _SCORE_FY_RECENCY_BOOST
            reasons.append(f"fy_recency_boost:{chunk.fiscal_year}(+{_SCORE_FY_RECENCY_BOOST})")

        return score, reasons

    def search_with_trace(
        self,
        query: str,
        language: str,
        top_k: int = _MAX_RESULTS,
        index: list[DocumentChunk] | None = None,
    ) -> list[tuple[DocumentChunk, dict[str, Any]]]:
        """Search indexed chunks and return (chunk, trace_dict) tuples."""
        lang = str(language or "").strip().lower()
        if lang not in SUPPORTED_LANGUAGES:
            lang = "vi"

        chunks = index if index is not None else get_knowledge_index()
        if not chunks:
            return []

        norm_query = _normalize_text(query)
        query_tokens = _tokenize(norm_query)
        query_unaccented = _strip_vietnamese_diacritics(query) if lang == "vi" else ""
        query_bigrams = _cjk_bigrams(norm_query) if lang == "ja" else set()

        if not query_tokens and not query_bigrams:
            return []

        scored: list[tuple[int, DocumentChunk, dict[str, Any]]] = []
        for chunk in chunks:
            score, reasons = self.score_chunk(
                chunk, lang, norm_query, query_tokens, query_unaccented, query_bigrams,
            )
            if score < MIN_CONFIDENCE_SCORE:
                continue

            trace = {
                "chunk_id": chunk.chunk_id,
                "source_id": chunk.source_id,
                "score": score,
                "authority": chunk.authority,
                "match_reasons": reasons,
            }
            scored.append((score, chunk, trace))

        scored.sort(key=lambda x: x[0], reverse=True)

        # Identify superseded topic keys from matching chunks
        superseded_set: set[str] = set()
        for _, chunk, _ in scored:
            if getattr(chunk, "replaces_or_supersedes", ()):
                for target in chunk.replaces_or_supersedes:
                    superseded_set.add(str(target).strip().lower())

        final: list[tuple[DocumentChunk, dict[str, Any]]] = []
        seen_token_sets: list[set[str]] = []
        for _, chunk, trace in scored[:top_k * 4]:
            # Suppress legacy chunk if superseded by an active newer rule
            cid_lower = chunk.chunk_id.lower()
            sid_lower = chunk.source_id.lower()
            if any(sup in cid_lower or sup == sid_lower for sup in superseded_set):
                continue

            item_tokens = _tokenize(chunk.section_title + " " + chunk.text)
            is_duplicate = False
            for existing in seen_token_sets:
                if not item_tokens or not existing:
                    continue
                overlap = len(item_tokens & existing)
                if overlap / min(len(item_tokens), len(existing)) > 0.8:
                    is_duplicate = True
                    break
            if not is_duplicate:
                final.append((chunk, trace))
                seen_token_sets.append(item_tokens)
            if len(final) >= top_k:
                break

        return final

    def search(
        self,
        query: str,
        language: str,
        top_k: int = _MAX_RESULTS,
        index: list[DocumentChunk] | None = None,
    ) -> list[DocumentChunk]:
        """Return top matching DocumentChunk objects."""
        traced = self.search_with_trace(query, language, top_k, index)
        return [chunk for chunk, _ in traced]


_DEFAULT_RETRIEVAL_ENGINE = HybridDocumentRetrievalEngine()


def merge_multi_query_chunks(
    results_per_query: Sequence[Sequence[DocumentChunk]],
    max_per_query: int = 2,
    max_total: int | None = None,
) -> list[DocumentChunk]:
    """Merge retrieved chunks from multiple sub-queries with deduplication and fair representation.

    Guarantees:
    1. Every sub-query that found matching chunks has at least 1-2 representative chunks
       in the final result, regardless of score disparity.
    2. Strict chunk_id uniqueness (no duplicate chunks).
    3. Respects overall capacity limit if specified.
    """
    if not results_per_query:
        return []

    limit = max_total if max_total is not None else max(len(results_per_query) * max_per_query, _MAX_RESULTS)
    seen_ids: set[str] = set()
    merged: list[DocumentChunk] = []

    # Iterative rounds: each round gives each sub-query one slot (up to max_per_query)
    for _ in range(max_per_query):
        for q_chunks in results_per_query:
            if len(merged) >= limit:
                break
            for chunk in q_chunks:
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    merged.append(chunk)
                    break

    # Fill remaining capacity up to limit from any remaining chunks
    if len(merged) < limit:
        for q_chunks in results_per_query:
            for chunk in q_chunks:
                if len(merged) >= limit:
                    break
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    merged.append(chunk)

    return merged


def merge_multi_query_traces(
    traces_per_query: Sequence[tuple[str, Sequence[tuple[DocumentChunk, dict[str, Any]]]]],
    max_per_query: int = 2,
    max_total: int | None = None,
) -> list[tuple[DocumentChunk, dict[str, Any]]]:
    """Merge traced chunks from multiple sub-queries with deduplication and fair representation."""
    if not traces_per_query:
        return []

    limit = max_total if max_total is not None else max(len(traces_per_query) * max_per_query, _MAX_RESULTS)
    seen_ids: set[str] = set()
    merged: list[tuple[DocumentChunk, dict[str, Any]]] = []

    for _ in range(max_per_query):
        for sub_query, q_traces in traces_per_query:
            if len(merged) >= limit:
                break
            for chunk, trace in q_traces:
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    tr = dict(trace)
                    tr["sub_query"] = sub_query
                    merged.append((chunk, tr))
                    break

    if len(merged) < limit:
        for sub_query, q_traces in traces_per_query:
            for chunk, trace in q_traces:
                if len(merged) >= limit:
                    break
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    tr = dict(trace)
                    tr["sub_query"] = sub_query
                    merged.append((chunk, tr))

    return merged


def retrieve_grounded_chunks(
    query: str,
    language: str,
    top_k: int = _MAX_RESULTS,
    index: list[DocumentChunk] | None = None,
    decompose: bool = True,
) -> list[DocumentChunk]:
    """Retrieve top-k grounded DocumentChunk objects for query in language.

    Supports automatic query decomposition for multi-intent questions,
    retrieving grounded chunks for each sub-query and performing fair-representation,
    deduplicated merging.
    """
    if not decompose:
        return _DEFAULT_RETRIEVAL_ENGINE.search(query, language, top_k, index)

    from src.services.query_decomposition import decompose_query

    sub_queries = decompose_query(query, language)
    if len(sub_queries) <= 1:
        return _DEFAULT_RETRIEVAL_ENGINE.search(query, language, top_k, index)

    results_per_query: list[list[DocumentChunk]] = []
    for sq in sub_queries:
        res = _DEFAULT_RETRIEVAL_ENGINE.search(sq, language, top_k=top_k, index=index)
        results_per_query.append(res)

    max_total = top_k if top_k < _MAX_RESULTS else max(top_k, len(sub_queries) * 2)
    return merge_multi_query_chunks(results_per_query, max_per_query=2, max_total=max_total)


def retrieve_grounded_chunks_with_trace(
    query: str,
    language: str,
    top_k: int = _MAX_RESULTS,
    index: list[DocumentChunk] | None = None,
    decompose: bool = True,
) -> list[tuple[DocumentChunk, dict[str, Any]]]:
    """Retrieve top-k chunks along with diagnostic trace information.

    Supports automatic query decomposition for multi-intent questions.
    """
    if not decompose:
        return _DEFAULT_RETRIEVAL_ENGINE.search_with_trace(query, language, top_k, index)

    from src.services.query_decomposition import decompose_query

    sub_queries = decompose_query(query, language)
    if len(sub_queries) <= 1:
        return _DEFAULT_RETRIEVAL_ENGINE.search_with_trace(query, language, top_k, index)

    traces_per_query: list[tuple[str, list[tuple[DocumentChunk, dict[str, Any]]]]] = []
    for sq in sub_queries:
        res = _DEFAULT_RETRIEVAL_ENGINE.search_with_trace(sq, language, top_k=top_k, index=index)
        traces_per_query.append((sq, res))

    max_total = top_k if top_k < _MAX_RESULTS else max(top_k, len(sub_queries) * 2)
    return merge_multi_query_traces(traces_per_query, max_per_query=2, max_total=max_total)


def select_relevant_citations(
    citations: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    question: str = "",
    language: str = "vi",
    max_citations: int = 2,
) -> list[dict[str, Any]]:
    """Select the 1-2 most relevant evidence citations for a question based on semantic overlap."""
    if not citations:
        return []
    if len(citations) == 1 or not question or not str(question).strip():
        return [citations[0]]

    import re
    q_clean = str(question).lower()
    raw_tokens = re.findall(r"[\w]+", q_clean)
    q_tokens = set(t for t in raw_tokens if len(t) > 1)
    for i in range(len(q_clean) - 1):
        bi = q_clean[i:i+2].strip()
        if len(bi) == 2 and not bi.isascii():
            q_tokens.add(bi)

    scored: list[tuple[float, int, dict[str, Any]]] = []
    for idx, cit in enumerate(citations):
        ht = str(cit.get("heading_title", "")).lower()
        ss = str(cit.get("supported_summary", "")).lower()
        dt = str(cit.get("display_title", "")).lower()

        score = 0.0
        for tok in q_tokens:
            if tok in ht:
                score += 3.0
            if tok in ss:
                score += 2.0
            if tok in dt:
                score += 1.0

        for word in raw_tokens:
            if len(word) >= 4:
                if word in ht:
                    score += 5.0
                elif word in ss:
                    score += 3.0

        scored.append((score, idx, cit))

    scored.sort(key=lambda x: (x[0], -x[1]), reverse=True)

    top_score, _, top_cit = scored[0]
    if top_score <= 0.0:
        return [citations[0]]

    selected = [top_cit]
    if max_citations >= 2 and len(scored) >= 2:
        second_score, _, second_cit = scored[1]
        if second_score > 0.0 and second_score >= 0.8 * top_score:
            if second_cit.get("heading_title") != top_cit.get("heading_title"):
                selected.append(second_cit)

    return selected


def format_grounded_context(
    chunks: list[DocumentChunk],
    language: str,
    registry: dict[str, Any] | None = None,
    question: str = "",
) -> str:
    """Format retrieved document chunks into a clean, concise, non-technical context string.

    Never leaks internal file paths, SHA-256 hashes, JSON/MD file names, or code tokens.
    Uses select_relevant_citations to display the most relevant source heading for the question.
    """
    if not chunks:
        return ""

    lang = str(language or "").strip().lower()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "vi"

    source_prefix = {
        "vi": "Nguồn tham khảo",
        "en": "Source Reference",
        "ja": "参照元",
    }.get(lang, "Nguồn tham khảo")

    confidence_prefix = {
        "vi": "Mức tin cậy",
        "en": "Confidence Level",
        "ja": "信頼度",
    }.get(lang, "Mức tin cậy")

    confirmed_label = {
        "vi": "Đã xác nhận",
        "en": "Confirmed",
        "ja": "確定",
    }.get(lang, "Đã xác nhận")

    caveat_label = {
        "vi": "Tham khảo nội bộ",
        "en": "Internal Reference",
        "ja": "社内参考",
    }.get(lang, "Tham khảo nội bộ")

    parts: list[str] = []
    for chunk in chunks:
        title = chunk.section_title
        text = chunk.text
        steps = chunk.safe_steps
        source_label = get_source_label(chunk.source_id, lang, registry)

        is_caveat = (chunk.authority in ("caveat", "reference_with_caveat"))

        selected_citations = select_relevant_citations(
            chunk.evidence_citations, question=question, language=lang, max_citations=2
        )
        if selected_citations:
            cit_parts = []
            for cit in selected_citations:
                d_t = cit.get("display_title") or source_label
                h_t = cit.get("heading_title") or title
                cit_parts.append(f"{d_t} — {h_t}")

            sep = "；" if lang == "ja" else "; "
            source_line = f"{source_prefix}: {sep.join(cit_parts)}"

            has_caveat = any(c.get("classification") == "reference_with_caveat" for c in selected_citations)
            confidence_text = caveat_label if (has_caveat or is_caveat) else confirmed_label
        else:
            source_line = f"{source_prefix}: {source_label} — {title}" if source_label else f"{source_prefix}: {title}"
            confidence_text = caveat_label if is_caveat else confirmed_label

        steps_text = " ".join(f"({i + 1}) {s}" for i, s in enumerate(steps))
        conf_line = f"{confidence_prefix}: {confidence_text}"
        parts.append(f"{text} {steps_text}\n{source_line}\n{conf_line}".strip())

    max_len = max(1400, len(parts) * 700)
    return "\n\n".join(parts)[:max_len]


def grounded_local_fallback(
    question: str,
    language: str,
    index: list[DocumentChunk] | None = None,
    registry: dict[str, Any] | None = None,
    intent: str | None = None,
) -> str:
    """Return an authoritative local fallback answer from index chunks when Gemini is offline."""
    lang = str(language or "").strip().lower()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "vi"

    resolved_intent = intent if intent in ("incident", "clarify", "business") else classify_question_intent(question, lang)

    if resolved_intent == "clarify":
        clarify_msg = {
            "vi": "Bạn đang cần hỏi về số lượng nhóm chi phí hay số dòng chi phí cụ thể, cho năm tài chính (FY) và trung tâm chi phí (cost center) nào?",
            "en": "Are you asking about the number of cost categories or specific cost line items, and for which fiscal year (FY) and cost center?",
            "ja": "費用の分類項目数ですか、それとも具体的な明細行数ですか？対象の会計年度（FY）とコストセンターをお知らせください。",
        }
        return clarify_msg.get(lang, clarify_msg["vi"])

    chunks = retrieve_grounded_chunks(question, lang, top_k=1, index=index)
    if not chunks:
        if resolved_intent == "incident":
            incident_no_match = {
                "vi": (
                    "Chưa tìm thấy thông tin sự cố phù hợp với mô tả này.\n"
                    "Vui lòng kiểm tra lại thông báo lỗi cụ thể trên màn hình, xem chi tiết trong \"Lịch sử lần chạy\", "
                    "hoặc chọn lần chạy bị lỗi để được phân tích."
                ),
                "en": (
                    "No matching incident information was found for this description.\n"
                    "Please check the specific on-screen error message, inspect \"Run History\", "
                    "or select the failed run for diagnosis."
                ),
                "ja": (
                    "この内容に該当する障害情報が見つかりませんでした。\n"
                    "画面上に表示されたエラーメッセージを確認するか、「実行履歴」で対象のエラー実行を選択して診断してください。"
                ),
            }
            return incident_no_match.get(lang, incident_no_match["vi"])

        no_match = {
            "vi": (
                "Chưa tìm thấy hướng dẫn nội bộ phù hợp với câu hỏi này.\n"
                "Vui lòng thử hỏi lại bằng từ ngữ nghiệp vụ đơn giản hơn, "
                "ví dụ: \"phân bổ chi phí chung và riêng thế nào\", \"nhập dữ liệu nhân sự ở đâu\", "
                "hoặc nêu rõ năm tài chính và trung tâm chi phí cần hỏi."
            ),
            "en": (
                "No matching internal guidance was found for this question.\n"
                "Please try rephrasing using simpler business terms, "
                "e.g. \"how are common and special costs allocated?\", \"where do I enter staffing data?\", "
                "or specify the fiscal year and cost center."
            ),
            "ja": (
                "この質問に該当する社内ガイダンスが見つかりませんでした。\n"
                "よりシンプルな業務用語で質問し直してください。"
                "例：「共通費と個別費はどう配賦しますか」「人員データはどこに入力しますか」、"
                "または対象の年度とコストセンターを指定してください。"
            ),
        }
        return no_match.get(lang, no_match["vi"])

    best = chunks[0]

    source_prefix = {
        "vi": "Nguồn tham khảo",
        "en": "Source Reference",
        "ja": "参照元",
    }.get(lang, "Nguồn tham khảo")

    confidence_prefix = {
        "vi": "Mức tin cậy",
        "en": "Confidence Level",
        "ja": "信頼度",
    }.get(lang, "Mức tin cậy")

    is_caveat = (best.authority in ("caveat", "reference_with_caveat"))

    selected_citations = select_relevant_citations(
        best.evidence_citations, question=question, language=lang, max_citations=2
    )
    if selected_citations:
        cit_parts = []
        for cit in selected_citations:
            d_t = cit.get("display_title") or get_source_label(best.source_id, lang, registry) or "MP2027"
            h_t = cit.get("heading_title") or best.section_title
            cit_parts.append(f"{d_t} — {h_t}")
        sep = "；" if lang == "ja" else "; "
        source_line = f"{source_prefix}: {sep.join(cit_parts)}"
        has_caveat = any(c.get("classification") == "reference_with_caveat" for c in selected_citations)
        confidence_val = {
            "vi": ("Tham khảo nội bộ" if (has_caveat or is_caveat) else "Đã xác nhận"),
            "en": ("Internal Reference" if (has_caveat or is_caveat) else "Confirmed"),
            "ja": ("社内参考" if (has_caveat or is_caveat) else "確定"),
        }.get(lang, "Đã xác nhận")
    else:
        source_label = get_source_label(best.source_id, lang, registry) or "MP2027"
        source_line = f"{source_prefix}: {source_label} — {best.section_title}"
        confidence_val = {
            "vi": ("Tham khảo nội bộ" if is_caveat else "Đã xác nhận"),
            "en": ("Internal Reference" if is_caveat else "Confirmed"),
            "ja": ("社内参考" if is_caveat else "確定"),
        }.get(lang, "Đã xác nhận")

    lines: list[str] = [best.text]
    if best.safe_steps:
        lines.append("")
        for i, step in enumerate(best.safe_steps, 1):
            lines.append(f"{i}. {step}")

    lines.append("")
    lines.append(source_line)
    lines.append(f"{confidence_prefix}: {confidence_val}")

    return "\n".join(lines)
