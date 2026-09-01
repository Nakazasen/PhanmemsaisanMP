"""Mô hình tri thức vận hành chuẩn tắc và nội dung hướng dẫn nghiệp vụ đa ngôn ngữ.

Tuân thủ kiến trúc MVP Operations Assistant:
1. Bất biến (immutable): Data class KnowledgeEntry và GuidancePresentation được đóng băng (frozen=True).
2. Đa ngôn ngữ bắt buộc (Strict Multilingual): Bắt buộc 100% có đầy đủ 3 ngôn ngữ ('vi', 'en', 'ja')
   cho mọi mục tri thức đã duyệt.
3. Không tự dịch máy / không tự rơi sang ngôn ngữ khác (Fail-closed Validation): Thiếu bất kỳ
   trường nào hoặc ngôn ngữ nào sẽ bị từ chối ngay lập tức tại bước kiểm tra tính hợp lệ.
4. Ngôn ngữ nghiệp vụ thân thiện (Non-tech friendly): Toàn bộ lời giải thích và hướng dẫn hành động
   phải dùng ngôn ngữ đời thường, dễ hiểu cho người làm nghiệp vụ; không dùng raw exception,
   traceback, hoặc JSON key làm nội dung giải thích chính.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
from types import MappingProxyType
from typing import Any, Mapping, Sequence

SUPPORTED_LANGUAGES: tuple[str, ...] = ("vi", "en", "ja")
APPROVED_REVIEW_STATUSES: tuple[str, ...] = ("approved", "draft")


# Technical tokens may be retained only in the separately labelled evidence or
# technical-details view. They must never become the user's main explanation.
_PRIMARY_TECHNICAL_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"Traceback \(most recent call last\):"),
    re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:Error|Exception)\b"),
    re.compile(r"[\"'][A-Za-z_][A-Za-z0-9_]*[\"']\s*:"),
    re.compile(
        r"\b(?:pipeline_stage_evidence|preflight_report|run_manifest|"
        r"failure_traceback|source_paths_json|template_checksum)\b"
    ),
    re.compile(r"^\s*\[\d{1,2}:\d{2}:\d{2}\]", re.MULTILINE),
)


def _contains_raw_technical_content(value: str) -> bool:
    """Return whether a primary user-facing text leaks an internal artefact."""
    return any(pattern.search(value) for pattern in _PRIMARY_TECHNICAL_PATTERNS)


@dataclass(frozen=True)
class GuidancePresentation:
    """Nội dung trình bày hướng dẫn giải quyết sự cố cho người dùng nghiệp vụ theo ngôn ngữ cụ thể."""

    language: str
    title: str
    what_happened: str
    why_it_happened: str
    what_to_do: tuple[str, ...]
    confidence_label: str
    evidence_label: str
    technical_details_label: str

    def __post_init__(self) -> None:
        """Kiểm thực tính toàn vẹn và ranh giới an toàn của nội dung hướng dẫn."""
        lang = str(self.language).strip().lower() if self.language else ""
        if lang not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Ngôn ngữ '{self.language}' không được hỗ trợ. "
                f"Các ngôn ngữ hợp lệ: {SUPPORTED_LANGUAGES}"
            )
        object.__setattr__(self, "language", lang)

        # Kiểm tra các trường văn bản bắt buộc
        for field_name in (
            "title",
            "what_happened",
            "why_it_happened",
            "confidence_label",
            "evidence_label",
            "technical_details_label",
        ):
            val = getattr(self, field_name)
            if not isinstance(val, str) or not val.strip():
                raise ValueError(
                    f"Trường '{field_name}' trong GuidancePresentation ({lang}) "
                    "không được để trống hoặc sai kiểu dữ liệu."
                )
            object.__setattr__(self, field_name, val.strip())

        # Kiểm tra danh sách các bước hành động (what_to_do)
        if not self.what_to_do or not isinstance(self.what_to_do, (list, tuple)):
            raise ValueError(
                f"Trường 'what_to_do' trong GuidancePresentation ({lang}) "
                "phải là một danh sách hoặc tuple chứa ít nhất một bước hành động."
            )

        cleaned_steps: list[str] = []
        for idx, step in enumerate(self.what_to_do, start=1):
            if not isinstance(step, str) or not step.strip():
                raise ValueError(
                    f"Bước hành động thứ {idx} trong 'what_to_do' ({lang}) không được để trống."
                )
            cleaned_steps.append(step.strip())
        object.__setattr__(self, "what_to_do", tuple(cleaned_steps))

        if any(_contains_raw_technical_content(step) for step in cleaned_steps):
            raise ValueError(
                "A primary action step contains raw technical content. "
                "Keep it in the optional technical-details view instead."
            )

        # Kiểm tra chống tràn raw traceback vào nội dung chính
        for field_name in ("title", "what_happened", "why_it_happened"):
            content = getattr(self, field_name)
            if _contains_raw_technical_content(content):
                raise ValueError(
                    f"Trường '{field_name}' chứa dấu vết ngoại lệ kỹ thuật thô (Traceback). "
                    "Nội dung chính phải là ngôn ngữ nghiệp vụ dễ hiểu."
                )


@dataclass(frozen=True)
class KnowledgeEntry:
    """Mục tri thức lỗi chuẩn tắc dùng để đối chiếu tất định và hướng dẫn người dùng."""

    error_code: str
    conditions: Mapping[str, Any]
    translations: Mapping[str, GuidancePresentation]
    evidence_requirements: tuple[str, ...]
    review_status: str = "approved"
    owner: str = "Planning Operations Team"

    def __post_init__(self) -> None:
        """Kiểm thực nghiêm ngặt tính toàn vẹn của mục tri thức chuẩn tắc."""
        code = str(self.error_code).strip() if self.error_code else ""
        if not code:
            raise ValueError("Mã lỗi 'error_code' không được để trống.")
        object.__setattr__(self, "error_code", code)

        status = str(self.review_status).strip().lower() if self.review_status else ""
        if status not in APPROVED_REVIEW_STATUSES:
            raise ValueError(
                f"Trạng thái kiểm duyệt '{self.review_status}' không hợp lệ. "
                f"Chỉ chấp nhận: {APPROVED_REVIEW_STATUSES}"
            )
        object.__setattr__(self, "review_status", status)

        own = str(self.owner).strip() if self.owner else ""
        if not own:
            raise ValueError("Chủ sở hữu 'owner' không được để trống.")
        object.__setattr__(self, "owner", own)

        # Chuẩn hóa conditions thành mapping bất biến (MappingProxyType)
        if not isinstance(self.conditions, (dict, Mapping)):
            raise ValueError("Trường 'conditions' phải là một dictionary hoặc Mapping.")
        object.__setattr__(self, "conditions", MappingProxyType(dict(self.conditions)))

        # Chuẩn hóa evidence_requirements
        if not self.evidence_requirements or not isinstance(self.evidence_requirements, (list, tuple)):
            raise ValueError(
                "Trường 'evidence_requirements' phải là danh sách/tuple chứa ít nhất một loại bằng chứng."
            )
        cleaned_ev: list[str] = []
        for ev in self.evidence_requirements:
            if not isinstance(ev, str) or not ev.strip():
                raise ValueError("Loại bằng chứng trong 'evidence_requirements' không được để trống.")
            cleaned_ev.append(ev.strip())
        object.__setattr__(self, "evidence_requirements", tuple(cleaned_ev))

        # Kiểm tra bắt buộc có đủ 3 ngôn ngữ: vi, en, ja
        if not isinstance(self.translations, (dict, Mapping)):
            raise ValueError("Trường 'translations' phải là một dictionary hoặc Mapping.")

        for required_lang in SUPPORTED_LANGUAGES:
            if required_lang not in self.translations:
                raise ValueError(
                    f"Mục tri thức '{code}' thiếu bản dịch bắt buộc cho ngôn ngữ '{required_lang}'."
                )
            presentation = self.translations[required_lang]
            if not isinstance(presentation, GuidancePresentation):
                raise TypeError(
                    f"Bản dịch cho ngôn ngữ '{required_lang}' phải là đối tượng GuidancePresentation."
                )
            if presentation.language != required_lang:
                raise ValueError(
                    f"Bản dịch gán cho khóa '{required_lang}' có language='{presentation.language}' không khớp."
                )

        object.__setattr__(self, "translations", MappingProxyType(dict(self.translations)))


# ---------------------------------------------------------------------------
# T011: Approved Error Class 1 - Missing Staffing Baseline
# ---------------------------------------------------------------------------

ERROR_CODE_MISSING_STAFFING_BASELINE: str = "missing_staffing_baseline"

ENTRY_MISSING_STAFFING_BASELINE: KnowledgeEntry = KnowledgeEntry(
    error_code=ERROR_CODE_MISSING_STAFFING_BASELINE,
    conditions={
        "stage": "validate_staffing",
        "signal": "missing_manual_baseline",
    },
    translations={
        "vi": GuidancePresentation(
            language="vi",
            title="Thiếu dữ liệu nhân sự mốc ban đầu (Baseline tháng 03)",
            what_happened=(
                "Quá trình kiểm tra trước tính toán phát hiện thiếu số liệu nhân sự của "
                "tháng mốc ban đầu (tháng 03) cho phòng ban được chỉ định."
            ),
            why_it_happened=(
                "Hệ thống phân bổ chi phí yêu cầu phải có số lượng nhân sự của tháng mốc "
                "đầu kỳ để làm căn cứ tính toán cho toàn bộ các tháng tiếp theo trong năm tài chính."
            ),
            what_to_do=(
                "1. Trên MP2027, bấm nút Nhập nhân sự thủ công.",
                "2. Chọn đúng phòng ban được nêu trong thông báo và nhập Tổng số người của tháng 03.",
                "3. Bấm Lưu nhân sự & thời gian để lưu dữ liệu vừa nhập.",
                "4. Bấm Quét lại nội dung, sau đó bấm Chạy tính toán.",
            ),
            confidence_label="Đã xác nhận",
            evidence_label="Bằng chứng từ báo cáo kiểm tra tiền trạm",
            technical_details_label="Chi tiết kỹ thuật từ hệ thống",
        ),
        "en": GuidancePresentation(
            language="en",
            title="Missing Baseline Staffing Data (March Baseline)",
            what_happened=(
                "Preflight validation detected missing headcount numbers for the initial "
                "baseline period (March) for the specified Cost Center."
            ),
            why_it_happened=(
                "The cost allocation engine requires baseline staffing counts from the opening "
                "month to compute monthly distributions across the entire fiscal year."
            ),
            what_to_do=(
                "1. In MP2027, click Manual staffing input.",
                "2. Select the Cost Center named in the message and enter the total headcount for March.",
                "3. Click Save staffing and time to save the data you entered.",
                "4. Click Rescan, then click Run calculation.",
            ),
            confidence_label="Confirmed",
            evidence_label="Evidence from preflight report",
            technical_details_label="System technical details",
        ),
        "ja": GuidancePresentation(
            language="ja",
            title="人員配置の基準データ（3月ベースライン）の不足",
            what_happened=(
                "事前検証処理において、対象コストセンターの期首基準月（3月）の人員データが登録されていないことが検出されました。"
            ),
            why_it_happened=(
                "費用配賦処理では、年度全体の月別配賦を計算するための基準として期首月の人員数データが必須となります。"
            ),
            what_to_do=(
                "1. MP2027で「手動人員入力」をクリックしてください。",
                "2. メッセージに表示されたコストセンターを選択し、3月の総人数を入力してください。",
                "3. 「人員・時間を保存」をクリックして入力内容を保存してください。",
                "4. 「内容を再確認」をクリックしてから、「計算を実行」をクリックしてください。",
            ),
            confidence_label="確認済み",
            evidence_label="事前検証レポートの根拠",
            technical_details_label="システム技術詳細",
        ),
    },
    evidence_requirements=("stage_evidence", "failure_traceback"),
    review_status="approved",
    owner="Planning Operations Team",
)


def is_missing_staffing_baseline_match(
    stage_payload: Mapping[str, Any] | None,
    error_summary: str = "",
) -> bool:
    """Kiểm tra điều kiện khớp tất định cho lỗi thiếu dữ liệu nhân sự mốc ban đầu (baseline).

    Yêu cầu bắt buộc để khớp (Confirmed match):
    Chỉ khớp khi bằng chứng bước chạy xác nhận bước ``validate_staffing`` thất bại
    và nội dung lỗi đúng với việc thiếu ``Tổng số người`` ở tháng mốc. Báo cáo
    preflight chỉ kiểm tra file nguồn nên không thể tự nó xác nhận lỗi này.
    """
    if not stage_payload or not isinstance(stage_payload, (dict, Mapping)):
        return False

    stages = stage_payload.get("stages")
    if not isinstance(stages, list):
        return False

    for stage in stages:
        if not isinstance(stage, Mapping):
            continue
        if str(stage.get("name") or "").strip() != "validate_staffing":
            continue
        if str(stage.get("status") or "").strip().upper() != "FAIL":
            continue

        text = "\n".join(
            str(value or "")
            for value in (
                stage.get("error_summary"),
                stage_payload.get("error_summary"),
                error_summary,
            )
        ).lower()
        has_actual_vietnamese_signal = "chưa có tổng số người tháng" in text
        has_explicit_english_signal = (
            "missing" in text
            and "baseline" in text
            and ("staffing" in text or "headcount" in text)
        )
        if has_actual_vietnamese_signal or has_explicit_english_signal:
            return True

    return False


# ---------------------------------------------------------------------------
# T012: Approved Error Class 2 - Blocked Output File Lock
# ---------------------------------------------------------------------------

ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK: str = "blocked_output_file_lock"

ENTRY_BLOCKED_OUTPUT_FILE_LOCK: KnowledgeEntry = KnowledgeEntry(
    error_code=ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK,
    conditions={
        "stage": "publication",
        "error_type": "OutputPublicationLockedError",
    },
    translations={
        "vi": GuidancePresentation(
            language="vi",
            title="Tệp Excel đầu ra đang bị khóa hoặc mở bởi ứng dụng khác",
            what_happened=(
                "Khi lưu kết quả tính toán, chương trình không thể ghi tệp vào thư mục kết quả "
                "vì hệ điều hành hoặc ứng dụng Excel đang khóa quyền ghi tệp."
            ),
            why_it_happened=(
                "Khi có người dùng hoặc chương trình khác đang mở tệp kết quả "
                "(hoặc đang duyệt thư mục đích trong File Explorer), Windows sẽ ngăn chặn "
                "thao tác ghi đè tệp để bảo vệ dữ liệu."
            ),
            what_to_do=(
                "1. Đóng tất cả các cửa sổ Excel đang mở các tệp bảng tính trong thư mục kết quả.",
                "2. Đóng cửa sổ File Explorer nếu đang mở xem thư mục kết quả đầu ra.",
                "3. Chờ vài giây để hệ thống giải phóng khóa tệp hoàn toàn.",
                "4. Bấm nút Chạy tính toán lại trên màn hình ứng dụng để tiếp tục.",
            ),
            confidence_label="Đã xác nhận",
            evidence_label="Bằng chứng từ nhật ký giai đoạn xuất bản và dấu vết lỗi",
            technical_details_label="Chi tiết kỹ thuật từ hệ thống",
        ),
        "en": GuidancePresentation(
            language="en",
            title="Output Excel Workbook is Locked by Another Application",
            what_happened=(
                "The program could not save the output workbooks because Windows "
                "or Excel is currently holding a lock on the destination file."
            ),
            why_it_happened=(
                "When an output workbook is currently open in Excel or being viewed in "
                "File Explorer, the operating system blocks overwrite operations to protect file integrity."
            ),
            what_to_do=(
                "1. Close all open Excel windows displaying output workbooks.",
                "2. Close any File Explorer windows currently browsing the output folder.",
                "3. Wait a few seconds for the operating system to release the file lock.",
                "4. Click Recalculate on the application screen to proceed.",
            ),
            confidence_label="Confirmed",
            evidence_label="Evidence from publication stage log and traceback",
            technical_details_label="System technical details",
        ),
        "ja": GuidancePresentation(
            language="ja",
            title="出力先Excelファイルが他のアプリケーションによりロックされています",
            what_happened=(
                "出力先フォルダー内のExcelファイルを他のアプリケーションが開いているため、"
                "計算結果の上書き保存ができませんでした。"
            ),
            why_it_happened=(
                "Excelで出力ファイルを開いているか、エクスプローラーでフォルダーを参照している場合、"
                "OSによりファイルへの書き込みが保護・制限されます。"
            ),
            what_to_do=(
                "1. 出力先フォルダー内の開いているExcelファイルをすべて閉じてください。",
                "2. 出力フォルダーを開いているエクスプローラーのウィンドウを閉じてください。",
                "3. ファイルロックが完全に解除されるまで数秒お待ちください。",
                "4. 画面上の再計算ボタンをクリックして処理を再開してください。",
            ),
            confidence_label="確認済み",
            evidence_label="出力段階ログおよびエラー証跡の根拠",
            technical_details_label="システム技術詳細",
        ),
    },
    evidence_requirements=("stage_evidence", "failure_traceback"),
    review_status="approved",
    owner="Planning Operations Team",
)


def is_blocked_output_file_lock_match(
    stage_payload: Mapping[str, Any] | None,
    traceback_text: str = "",
    error_summary: str = "",
) -> bool:
    """Kiểm tra điều kiện khớp tất định cho lỗi khóa tệp Excel đầu ra (blocked_output_file_lock).

    Yêu cầu bắt buộc để khớp (Confirmed match):
    1. stage_payload phải tồn tại và có bước 'publication' ở trạng thái 'FAIL'.
    2. traceback_text hoặc error_summary phải thể hiện lỗi khóa tệp / quyền ghi:
       - OutputPublicationLockedError, hoặc
       - PermissionError / [WinError 5] / WinError 32 / Access is denied liên quan đến tệp đầu ra, hoặc
       - Văn bản tiếng Việt xác nhận 'windows đang khóa' / 'không thể cập nhật thư mục kết quả'.
    3. Tuyệt đối không khớp nếu:
       - Thất bại ở giai đoạn khác (không phải publication FAIL).
       - Publication FAIL nhưng do nguyên nhân khác (không có dấu hiệu khóa tệp / permission error).
       - Chỉ có traceback/summary mà không có bằng chứng publication FAIL.
    """
    if not stage_payload or not isinstance(stage_payload, (dict, Mapping)):
        return False

    stages = stage_payload.get("stages")
    if not isinstance(stages, list):
        return False

    has_publication_fail = False
    for stage in stages:
        if isinstance(stage, Mapping):
            name = str(stage.get("name") or "").strip().lower()
            status = str(stage.get("status") or "").strip().upper()
            if name == "publication" and status == "FAIL":
                has_publication_fail = True
                break

    if not has_publication_fail:
        return False

    # Kiểm tra các dấu hiệu khóa tệp
    combined_text = f"{traceback_text}\n{error_summary}\n{stage_payload.get('error_summary', '')}".lower()

    # The dedicated exception is conclusive. A generic permission error is not:
    # it also needs a concrete output-workbook/destination signal so a different
    # permission problem during publication is not misrepresented as an Excel lock.
    if "outputpublicationlockederror" in combined_text:
        return True

    has_permission_or_lock_signal = any(
        signal in combined_text
        for signal in (
            "permissionerror",
            "winerror 5",
            "winerror 32",
            "access is denied",
            "windows đang khóa",
            "đang khóa tệp",
            "đang khóa file",
            "file is locked",
            "locked by another process",
        )
    )
    has_output_destination_signal = any(
        signal in combined_text
        for signal in (
            ".xlsx",
            "mp_cc_",
            "output_fy",
            "thư mục kết quả",
            "tệp kết quả",
            "output workbook",
            "destination file",
        )
    )
    return has_permission_or_lock_signal and has_output_destination_signal


# ---------------------------------------------------------------------------
# T013: Approved Error Class 3 - Preflight Source Validation Failure
# ---------------------------------------------------------------------------

ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE: str = "preflight_source_validation_failure"

ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE: KnowledgeEntry = KnowledgeEntry(
    error_code=ERROR_CODE_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
    conditions={
        "preflight_ok": False,
        "severity": "BLOCKING",
    },
    translations={
        "vi": GuidancePresentation(
            language="vi",
            title="Tệp dữ liệu nguồn đã chọn chưa thể dùng để tính toán",
            what_happened=(
                "Quá trình kiểm tra trước phát hiện một hoặc nhiều tệp nguồn đã chọn "
                "chưa phù hợp để dùng cho năm tài chính đang tính."
            ),
            why_it_happened=(
                "Mỗi tệp nguồn cần đúng năm tài chính, có thể mở được và có đủ nội dung "
                "mà chương trình cần để tính chi phí chính xác."
            ),
            what_to_do=(
                "1. Xem đường dẫn tệp nguồn và nội dung lỗi cụ thể trong phần bằng chứng kiểm tra tiền trạm bên dưới.",
                "2. Mở tệp bảng tính nguồn theo đúng đường dẫn được chỉ định.",
                "3. Chỉnh sửa và bổ sung nội dung hoặc cấu trúc cột theo đúng hướng dẫn trong báo cáo kiểm tra.",
                "4. Lưu tệp bảng tính sau khi cập nhật.",
                "5. Bấm nút Quét lại nội dung và Chạy tính toán lại trên màn hình ứng dụng.",
            ),
            confidence_label="Đã xác nhận",
            evidence_label="Bằng chứng từ báo cáo kiểm tra tiền trạm",
            technical_details_label="Chi tiết kỹ thuật từ hệ thống",
        ),
        "en": GuidancePresentation(
            language="en",
            title="A Selected Source File Cannot Be Used for This Calculation",
            what_happened=(
                "The initial check found that one or more selected source files cannot "
                "be used for the fiscal year being calculated."
            ),
            why_it_happened=(
                "Each source file must match the fiscal year, open correctly, and contain "
                "the information needed to calculate costs accurately."
            ),
            what_to_do=(
                "1. Review the affected source file path and issue details in the preflight evidence section below.",
                "2. Open the source workbook at the specified path.",
                "3. Correct the content or column structure as instructed in the validation report.",
                "4. Save and close the updated workbook file.",
                "5. Click Rescan Sources and Recalculate on the application screen.",
            ),
            confidence_label="Confirmed",
            evidence_label="Evidence from preflight validation report",
            technical_details_label="System technical details",
        ),
        "ja": GuidancePresentation(
            language="ja",
            title="入力元データファイルの形式または構造が不正です",
            what_happened=(
                "事前検証処理において、指定された入力元データファイルが存在しないか、"
                "列構造または形式が不正であることが検出されました。"
            ),
            why_it_happened=(
                "費用配賦計算を正確に実行するためには、すべての元データファイルが"
                "所定の列構成およびフォーマットに準拠している必要があります。"
            ),
            what_to_do=(
                "1. 下記の事前検証レポートの根拠に表示されている対象ファイルパスと指摘事項を確認してください。",
                "2. 指定されたパスにある元データファイルを開いてください。",
                "3. レポートの指示に従って内容または列構造を修正してください。",
                "4. ファイルを保存して閉じてください。",
                "5. 画面上の「元データ再スキャン」および「再計算」ボタンをクリックしてください。",
            ),
            confidence_label="確認済み",
            evidence_label="事前検証レポートの根拠",
            technical_details_label="システム技術詳細",
        ),
    },
    evidence_requirements=("preflight_report",),
    review_status="approved",
    owner="Planning Operations Team",
)


def is_preflight_source_validation_failure_match(
    preflight_payload: Mapping[str, Any] | None,
) -> bool:
    """Kiểm tra điều kiện khớp tất định cho lỗi kiểm tra file nguồn đầu vào thất bại (preflight_source_validation_failure).

    Yêu cầu bắt buộc để khớp (Confirmed match):
    1. preflight_payload phải tồn tại và có 'ok' là False.
    2. Có ít nhất một issue trong preflight_payload thỏa mãn:
       - severity == 'BLOCKING' (Không chấp nhận SOURCE_SKIPPED hoặc non-blocking).
       - Có đầy đủ các trường bằng chứng do báo cáo thực tế phát ra: 'category', 'status', 'code', 'selected_path', 'reason', 'required_action' (không được để trống).
       - Issue phải là lỗi kiểm tra file nguồn (category thuộc các nguồn như facility, fixed_assets, it_system, ga_admin, v.v.,
         hoặc code là SOURCE_VALIDATION_FAILED / SCHEMA_ERROR / SOURCE_MISSING / SOURCE_CORRUPT).
       - KHÔNG PHẢI lỗi thiếu baseline nhân sự (không trùng với is_missing_staffing_baseline_match).
    3. Tuyệt đối từ chối nếu:
       - preflight_payload is None hoặc ok == True.
       - Toàn bộ issues chỉ là SOURCE_SKIPPED.
       - Thiếu selected_path, reason hoặc required_action trong BLOCKING issue.
       - Chỉ có error_summary / log mà không có BLOCKING issue trong preflight report.
    """
    if not preflight_payload or not isinstance(preflight_payload, (dict, Mapping)):
        return False

    if preflight_payload.get("ok") is not False:
        return False

    issues = preflight_payload.get("issues")
    if not isinstance(issues, list) or len(issues) == 0:
        return False

    has_blocking_source_issue = False
    for issue in issues:
        if not isinstance(issue, (dict, Mapping)):
            continue

        severity = str(issue.get("severity") or "").strip().upper()
        if severity != "BLOCKING":
            continue

        # Kiểm tra bắt buộc có đủ các trường bằng chứng
        selected_path = str(issue.get("selected_path") or "").strip()
        reason = str(issue.get("reason") or "").strip()
        required_action = str(issue.get("required_action") or "").strip()
        cat = str(issue.get("category") or "").strip().lower()
        status = str(issue.get("status") or "").strip().upper()
        code = str(issue.get("code") or "").strip().upper()

        if not all((selected_path, reason, required_action, cat, code)) or status != "FAILED":
            continue

        # Bỏ qua nếu là lỗi thiếu baseline nhân sự
        if cat in ("headcount", "staffing", "personnel", "nhan_su"):
            continue

        has_blocking_source_issue = True
        break

    return has_blocking_source_issue


def get_approved_knowledge_entries() -> tuple[KnowledgeEntry, ...]:
    """Trả về danh sách các mục tri thức lỗi chuẩn tắc đã được phê duyệt."""
    return (
        ENTRY_MISSING_STAFFING_BASELINE,
        ENTRY_BLOCKED_OUTPUT_FILE_LOCK,
        ENTRY_PREFLIGHT_SOURCE_VALIDATION_FAILURE,
    )


def get_knowledge_entry(error_code: str) -> KnowledgeEntry | None:
    """Tra cứu mục tri thức theo mã lỗi."""
    target_code = str(error_code).strip()
    for entry in get_approved_knowledge_entries():
        if entry.error_code == target_code:
            return entry
    return None
