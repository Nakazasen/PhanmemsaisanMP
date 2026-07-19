"""Create a row-level decision matrix for fixed-assets cross-trace mismatches.

This script intentionally consumes the reproducible CSV artifacts produced by
``audit_fixed_assets_cross_trace.py``.  It does not alter any source or output
workbook.  The purpose is to finish classifying every TRUE_AMOUNT_MISMATCH
before an accounting-code change is considered.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import shutil
import sqlite3
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:  # Supports both ``py scripts/...`` and import from automated tests.
    from audit_fixed_assets_cross_trace import (
        AUDIT_DATE,
        CATEGORY_SPECS,
        INTEREST_ACCOUNT,
        ROOT,
        excel_round,
    )
except ModuleNotFoundError:  # pragma: no cover - exercised through package import.
    from scripts.audit_fixed_assets_cross_trace import (
        AUDIT_DATE,
        CATEGORY_SPECS,
        INTEREST_ACCOUNT,
        ROOT,
        excel_round,
    )

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from src.db.schema import create_schema, get_connection
from src.utils.cli import VietnameseArgumentParser


AUDIT_DIR = ROOT / "docs" / "audits"
VALID_DECISIONS = {
    "XAC_DINH_TU_BANG_CHUNG",
    "LA_NGOAI_LE_NHAP_TAY_HOAC_TANG_KHAC",
    "MAU_THUAN_CAN_NGHIEP_VU_DUYET",
    "KHONG_THE_XAC_DINH_TU_DU_LIEU",
}


def read_csv(name: str) -> list[dict[str, str]]:
    with (AUDIT_DIR / name).open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def json_value(value: str | None, fallback: Any) -> Any:
    if value in (None, ""):
        return fallback
    return json.loads(value)


def as_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(float(value))


def asset_account(asset: dict[str, str]) -> int | None:
    if asset["category_status"] != "supported":
        return None
    key = asset["category_key"]
    spec = CATEGORY_SPECS.get(key)
    return int(spec["account"]) if spec else None


def source_assets_by_key(ledger: list[dict[str, str]]) -> dict[tuple[str, str, int], list[dict[str, str]]]:
    grouped: defaultdict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for asset in ledger:
        cc = asset["depreciation_cc"]
        account = asset_account(asset)
        if cc and account is not None:
            grouped[(asset["fy"], cc, account)].append(asset)
            grouped[(asset["fy"], cc, INTEREST_ACCOUNT)].append(asset)
    return dict(grouped)


def selected_reference_by_key(
    references: list[dict[str, str]],
) -> dict[tuple[str, str, int], list[dict[str, str]]]:
    grouped: defaultdict[tuple[str, str, int], list[dict[str, str]]] = defaultdict(list)
    for row in references:
        if row["source_candidate_status"] != "SELECTED_SOURCE_DERIVED_CANDIDATE":
            continue
        if row["cc"]:
            grouped[(row["fy"], row["cc"], int(row["account"]))].append(row)
    return dict(grouped)


def schedule_for(asset: dict[str, str], account: int) -> dict[str, float]:
    field = "interest_schedule" if account == INTEREST_ACCOUNT else "depreciation_schedule"
    return {period: float(amount) for period, amount in json_value(asset[field], {}).items()}


def formula_kind(reference_rows: list[dict[str, str]], period: str) -> str:
    formulas = [
        str(json_value(row["monthly_formulas"], {}).get(period, "") or "")
        for row in reference_rows
        if json_value(row["monthly_values"], {}).get(period) is not None
    ]
    if not formulas:
        return "NO_REFERENCE_COMPONENT"
    if all(not formula.startswith("=") for formula in formulas):
        return "STATIC_VALUE"
    if all(formula.startswith("=") and "$B$2" in formula for formula in formulas):
        return "EMBEDDED_USD_SNAPSHOT_FORMULA"
    if any(formula.startswith("=") for formula in formulas):
        return "MIXED_OR_LINKED_FORMULA"
    return "UNCLASSIFIED"


def has_mixed_static_and_formula_components(reference_rows: list[dict[str, str]], period: str) -> bool:
    formulas = [
        str(json_value(row["monthly_formulas"], {}).get(period, "") or "")
        for row in reference_rows
        if json_value(row["monthly_values"], {}).get(period) is not None
    ]
    return any(formula.startswith("=") for formula in formulas) and any(
        formula and not formula.startswith("=") for formula in formulas
    )


def reference_components(reference_rows: list[dict[str, str]], period: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in reference_rows:
        values = json_value(row["monthly_values"], {})
        amount = values.get(period)
        if amount is None:
            continue
        formulas = json_value(row["monthly_formulas"], {})
        result.append(
            {
                "reference_file": row["reference_file"],
                "sheet": row["sheet"],
                "row": int(row["row"]),
                "description": row["description"],
                "value_vnd": int(excel_round(float(amount))),
                "formula": formulas.get(period, ""),
            }
        )
    return result


def source_components(source_rows: list[dict[str, str]], account: int, period: str) -> list[dict[str, Any]]:
    components: list[dict[str, Any]] = []
    for asset in source_rows:
        amount = schedule_for(asset, account).get(period, 0.0)
        terminal = asset["terminal_period"]
        if amount == 0 and not (terminal and terminal < period):
            continue
        components.append(
            {
                "source_file": asset["source_file"],
                "sheet": asset["source_sheet"],
                "row": int(asset["source_row"]),
                "asset_no": asset["asset_no"],
                "asset_text": asset["asset_text"],
                "L_monthly_depr_usd": as_int(asset["monthly_depr_usd"]),
                "P_terminal_period": terminal or None,
                "Q_terminal_depr_usd": as_int(asset["terminal_depr_usd"]),
                "V_apr_interest_usd": as_int(asset["apr_interest_usd"]),
                "W_may_interest_usd": as_int(asset["may_interest_usd"]),
                "scheduled_usd_for_period": amount,
                "terminal_relation": asset["terminal_relation"],
            }
        )
    return components


def known_reference_asset_numbers(reference_rows: list[dict[str, str]]) -> set[str]:
    found: set[str] = set()
    for row in reference_rows:
        found.update(re.findall(r"\d{6,}", row["description"] or ""))
    return found


def has_direct_post_terminal_continuation(
    source_rows: list[dict[str, str]], account: int, period: str, delta: int, rate: int
) -> bool:
    """Only claim a terminal defect when the added amount is exact evidence.

    It is intentionally conservative: either one expired asset or all expired
    assets must account for the complete positive difference.
    """
    if delta <= 0 or account == INTEREST_ACCOUNT or not rate:
        return False
    expired = [
        int(excel_round(float(asset["monthly_depr_usd"] or 0) * rate))
        for asset in source_rows
        if asset["terminal_relation"] == "within_fy"
        and asset["terminal_period"]
        and asset["terminal_period"] < period
    ]
    positives = [amount for amount in expired if amount > 0]
    return delta in positives or (positives and delta == sum(positives))


def has_direct_terminal_transition(
    source_rows: list[dict[str, str]],
    account: int,
    period: str,
    rate: int,
    comparison_by_key_period: dict[tuple[str, str, int, str], dict[str, str]],
    key: tuple[str, str, int],
) -> bool:
    """Prove a continuation by comparing the terminal-month transition.

    This captures the common real-world pattern where a reference keeps its
    prior-month amount unchanged after an asset expires, while unrelated
    snapshot variance prevents a simple current-month delta from matching.
    """
    if account == INTEREST_ACCOUNT or not rate:
        return False
    year, month = int(period[:4]), int(period[4:])
    # Fiscal April has no prior month inside this FY comparison.
    if month == 4:
        return False
    prior_period = f"{year - 1 if month == 1 else year}{12 if month == 1 else month - 1:02d}"
    prior = comparison_by_key_period.get((*key, prior_period))
    if not prior:
        return False
    terminal_amount = sum(
        int(excel_round(schedule_for(asset, account).get(prior_period, 0.0) * rate))
        for asset in source_rows
        if asset["terminal_relation"] == "within_fy" and asset["terminal_period"] == prior_period
    )
    if terminal_amount <= 0:
        return False
    expected_prior = as_int(prior["expected_per_asset_round_vnd"])
    expected_current = as_int(comparison_by_key_period[(*key, period)]["expected_per_asset_round_vnd"])
    actual_prior = as_int(prior["reference_actual_vnd"])
    actual_current = as_int(comparison_by_key_period[(*key, period)]["reference_actual_vnd"])
    return (
        expected_prior is not None
        and expected_current is not None
        and actual_prior is not None
        and actual_current is not None
        and expected_prior - expected_current == terminal_amount
        and actual_current == actual_prior
    )


def group_delta_pattern(rows: list[dict[str, str]]) -> dict[tuple[str, str, int], set[int]]:
    grouped: defaultdict[tuple[str, str, int], set[int]] = defaultdict(set)
    for row in rows:
        if row["classification"] != "TRUE_AMOUNT_MISMATCH":
            continue
        delta = as_int(row["delta_reference_minus_expected"])
        if delta is not None:
            grouped[(row["fy"], row["cc"], int(row["account"]))].add(delta)
    return dict(grouped)


def classify_row(
    row: dict[str, str],
    source_rows: list[dict[str, str]],
    reference_rows: list[dict[str, str]],
    all_source_asset_numbers: set[str],
    deltas_in_group: set[int],
    comparison_by_key_period: dict[tuple[str, str, int, str], dict[str, str]],
) -> tuple[str, str, str, str]:
    """Return (classification, decision_status, allowed_action, reason)."""
    period = row["period"]
    account = int(row["account"])
    actual = as_int(row["reference_actual_vnd"]) or 0
    expected = as_int(row["expected_per_asset_round_vnd"]) or 0
    delta = actual - expected
    components = reference_components(reference_rows, period)
    rates = {int(ref["fx_rate"]) for ref in reference_rows if ref["fx_rate"] not in ("", "0")}
    rate = next(iter(rates)) if len(rates) == 1 else 0
    reference_assets = known_reference_asset_numbers(reference_rows)
    if reference_assets and reference_assets.isdisjoint(all_source_asset_numbers):
        return (
            "REFERENCE_ASSET_NOT_IN_SOURCE_SNAPSHOT",
            "KHONG_THE_XAC_DINH_TU_DU_LIEU",
            "REQUEST_NEWER_ASSET_REGISTER_OR_BUSINESS_CONFIRMATION",
            "Tệp tham khảo mô tả mã tài sản không có trong ảnh chụp dữ liệu nguồn đã kiểm toán; bằng chứng chưa xác định được đây là tài sản mua trong tương lai hay thuộc một sổ tài sản khác.",
        )
    key = (row["fy"], row["cc"], account)
    if has_direct_terminal_transition(source_rows, account, period, rate, comparison_by_key_period, key):
        return (
            "POST_TERMINAL_REFERENCE_CONTINUES",
            "XAC_DINH_TU_BANG_CHUNG",
            "POLICY_FIX_ALLOWED_DO_NOT_COPY_REFERENCE",
            "Tổng nguồn giảm đúng bằng số tiền Q của tháng kết thúc nhưng tệp tham khảo không giảm ở tháng kế tiếp. Điều này chứng minh tệp tham khảo đã tiếp tục ghi nhận chi phí sau tháng kết thúc P.",
        )
    if has_direct_post_terminal_continuation(source_rows, account, period, delta, rate):
        return (
            "POST_TERMINAL_REFERENCE_CONTINUES",
            "XAC_DINH_TU_BANG_CHUNG",
            "POLICY_FIX_ALLOWED_DO_NOT_COPY_REFERENCE",
            "Chênh lệch dương đúng bằng khấu hao của các tài sản nguồn có kỳ kết thúc P trước tháng này. Q là số tiền của tháng kết thúc; không được tiếp tục ghi nhận chi phí sau đó.",
        )
    kind = formula_kind(reference_rows, period)
    if kind == "STATIC_VALUE":
        return (
            "REFERENCE_STATIC_MANUAL_INPUT",
            "LA_NGOAI_LE_NHAP_TAY_HOAC_TANG_KHAC",
            "PRESERVE_AS_REFERENCE_EXCEPTION_DO_NOT_OVERWRITE",
            "Tất cả thành phần tham khảo được chọn của tháng này là giá trị nhập trực tiếp, vì vậy số tiền đã nộp là dữ liệu nhập tay hoặc thuộc lớp khác, không phải công thức liên kết với sổ nguồn đã kiểm toán.",
        )
    if kind == "EMBEDDED_USD_SNAPSHOT_FORMULA":
        return (
            "REFERENCE_EMBEDDED_USD_SNAPSHOT_FORMULA",
            "MAU_THUAN_CAN_NGHIEP_VU_DUYET",
            "REQUIRE_BUSINESS_DECISION_BEFORE_ACCOUNTING_CHANGE",
            "Công thức tham khảo được chọn dùng các số tiền USD gắn cứng nhân với $B$2, không liên kết với sổ nguồn. Ảnh chụp dữ liệu nguồn và ảnh chụp tham khảo mâu thuẫn, nhưng không được tự động ghi đè bên nào.",
        )
    if has_mixed_static_and_formula_components(reference_rows, period):
        return (
            "REFERENCE_MIXED_STATIC_AND_FORMULA_INPUT",
            "LA_NGOAI_LE_NHAP_TAY_HOAC_TANG_KHAC",
            "PRESERVE_AS_REFERENCE_EXCEPTION_DO_NOT_OVERWRITE",
            "Tổng đã nộp gồm cả thành phần VND nhập trực tiếp và thành phần công thức. Thành phần nhập trực tiếp không liên kết với sổ nguồn, nên đây là ngoại lệ tham khảo nhập tay hoặc thuộc lớp khác, không phải lỗi tính toán nguồn chưa giải thích.",
        )
    if len(deltas_in_group) == 1:
        return (
            "CONSISTENT_REFERENCE_ADJUSTMENT",
            "MAU_THUAN_CAN_NGHIEP_VU_DUYET",
            "REQUIRE_BUSINESS_DECISION_BEFORE_ACCOUNTING_CHANGE",
            "Cùng một khoản điều chỉnh không phải do làm tròn lặp lại ở mọi tháng lệch của nhóm FY/CC/tài khoản này; dữ liệu nguồn được cung cấp không chứa nguồn gốc của khoản điều chỉnh.",
        )
    return (
        "UNEXPLAINED_FORMULA_OR_AGGREGATE_CONTRADICTION",
        "KHONG_THE_XAC_DINH_TU_DU_LIEU",
        "REQUIRE_ROW_LEVEL_BUSINESS_EVIDENCE",
        "Số tiền vẫn khác sau khi xét phương án làm tròn theo từng tài sản và kết thúc trước năm tài chính. Các dòng nguồn và tham khảo hiện có chưa chứng minh được một nguyên nhân duy nhất.",
    )


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False, sort_keys=True)
                    if isinstance(value, (dict, list))
                    else value
                    for key, value in row.items()
                }
            )


def write_report(path: Path, rows: list[dict[str, Any]]) -> None:
    classifications = Counter(row["evidence_classification"] for row in rows)
    decisions = Counter(row["decision_status"] for row in rows)
    groups = {(row["fy"], row["cc"], row["account"]) for row in rows}
    lines = [
        "# Tài sản cố định: ma trận quyết định cho toàn bộ chênh lệch số tiền thực",
        "",
        "- Được tạo từ các tệp CSV đối chiếu chéo có thể tái lập ngày 2026-07-16.",
        f"- Phạm vi: **{len(rows)} trên 638** ô tháng `TRUE_AMOUNT_MISMATCH`, thuộc {len(groups)} nhóm FY/CC/tài khoản.",
        "- Đây là phân loại bằng chứng, không phải quyền ghi đè dữ liệu do phòng ban nộp.",
        "",
        "## Phân loại bằng chứng",
        "",
        "| Phân loại | Số ô |",
        "| --- | ---: |",
        *[f"| `{key}` | {value} |" for key, value in sorted(classifications.items())],
        "",
        "## Trạng thái quyết định",
        "",
        "| Trạng thái | Số ô | Ý nghĩa |",
        "| --- | ---: | --- |",
        *[
            f"| `{key}` | {value} | "
            + {
                "XAC_DINH_TU_BANG_CHUNG": "Bằng chứng xác định kết quả theo chính sách; code được phép tuân theo chính sách đó, không sao chép tệp tham khảo đã nộp.",
                "LA_NGOAI_LE_NHAP_TAY_HOAC_TANG_KHAC": "Tệp tham khảo là dữ liệu nhập tay hoặc thuộc lớp khác; giữ lại như ngoại lệ và không ghi đè.",
                "MAU_THUAN_CAN_NGHIEP_VU_DUYET": "Hai ảnh chụp dữ liệu nguồn mâu thuẫn; nghiệp vụ phải chọn ảnh chụp hoặc chính sách có hiệu lực.",
                "KHONG_THE_XAC_DINH_TU_DU_LIEU": "Dữ liệu được cung cấp thiếu sổ tài sản hoặc giải thích cấp dòng cần thiết để ra quyết định.",
            }[key]
            + " |"
            for key, value in sorted(decisions.items())
        ],
        "",
        "## Kiểm soát trước khi thay đổi số liệu kế toán",
        "",
        "1. Ma trận chứng minh mỗi ô đều có nguồn gốc từ dữ liệu nguồn và tham khảo, nhưng chỉ `XAC_DINH_TU_BANG_CHUNG` đủ điều kiện sửa theo chính sách mà không cần quyết định nghiệp vụ.",
        "2. 222 ô `ROUNDING_ORDER` nằm ngoài ma trận này vì nguyên nhân đã được chứng minh: làm tròn theo từng tài sản trước khi cộng tổng.",
        "3. Không mã hóa ảnh chụp tham khảo, số tiền nhập tay, CC, tài khoản, kỳ, tỷ giá, tên file, sheet hoặc dòng FORM thành giá trị dự phòng.",
        "4. Giữ `FA-OPEN` ở trạng thái mở cho đến khi hoàn tất quyết định nghiệp vụ và bộ đối chiếu sau sửa lỗi.",
        "",
        "## Tệp bằng chứng",
        "",
        f"- `docs/audits/fixed_assets_true_mismatch_decision_matrix_{AUDIT_DATE}.csv` chứa từng ô tháng, hai giá trị, chênh lệch, L/P/Q/V/W nguồn, dòng/công thức tham khảo, phân loại, quyết định và hành động được phép.",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


def history_payload(rows: list[dict[str, Any]]) -> str:
    """Tạo dữ liệu băm ổn định, không phụ thuộc thời điểm thực thi."""
    return json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def display_path(path: Path) -> str:
    """Ưu tiên đường dẫn tương đối theo kho mã nhưng không hạn chế test/người dùng."""
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def fiscal_year_number(value: Any) -> int:
    """Chuẩn hóa nhãn sổ cái như ``FY2026`` trước khi lưu vào CSDL."""
    digits = re.sub(r"\D", "", str(value))
    if len(digits) != 4:
        raise ValueError(f"Năm tài chính không hợp lệ cho lịch sử kiểm toán: {value!r}")
    return int(digits)


def archive_audit_history(
    rows: list[dict[str, Any]],
    *,
    audit_date: str,
    matrix_csv_path: Path,
    matrix_report_path: Path,
    history_dir: Path,
    history_db: Path,
) -> tuple[str, Path]:
    """Lưu ảnh chụp kiểm toán bất biến, dễ đọc và có nhật ký CSDL truy vấn được.

    Các tệp ma trận quyết định theo ngày vẫn là chế độ xem hiện tại hữu ích nhưng sẽ
    được ghi đè khi kiểm toán lại trong cùng ngày. Hàm này chỉ nối thêm: mỗi lần gọi
    nhận một mã lượt chạy riêng và giữ nguyên các dòng, bằng chứng cùng phân loại tại
    thời điểm thực hiện.
    """
    payload = history_payload(rows)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    executed_at = datetime.now(timezone.utc).replace(microsecond=0)
    base_run_id = f"fa-{executed_at.strftime('%Y%m%dT%H%M%SZ')}-{digest[:12]}"
    run_id = base_run_id
    snapshot_dir = history_dir / run_id
    sequence = 2
    while snapshot_dir.exists():
        run_id = f"{base_run_id}-{sequence}"
        snapshot_dir = history_dir / run_id
        sequence += 1
    snapshot_dir.mkdir(parents=True, exist_ok=False)
    snapshot_csv = snapshot_dir / matrix_csv_path.name
    snapshot_report = snapshot_dir / matrix_report_path.name
    shutil.copy2(matrix_csv_path, snapshot_csv)
    shutil.copy2(matrix_report_path, snapshot_report)

    classifications = Counter(row["evidence_classification"] for row in rows)
    decisions = Counter(row["decision_status"] for row in rows)
    manifest = {
        "run_id": run_id,
        "audit_date": audit_date,
        "executed_at_utc": executed_at.isoformat(),
        "matrix_sha256": digest,
        "cells": len(rows),
        "classifications": dict(sorted(classifications.items())),
        "decision_statuses": dict(sorted(decisions.items())),
        "current_matrix_csv": display_path(matrix_csv_path),
        "current_matrix_report": display_path(matrix_report_path),
        "snapshot_csv": display_path(snapshot_csv),
        "snapshot_report": display_path(snapshot_report),
    }
    (snapshot_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    index_row = {
        "run_id": run_id,
        "audit_date": audit_date,
        "executed_at_utc": executed_at.isoformat(),
        "matrix_sha256": digest,
        "cells": len(rows),
        "classification_summary": json.dumps(dict(sorted(classifications.items())), ensure_ascii=False),
        "decision_summary": json.dumps(dict(sorted(decisions.items())), ensure_ascii=False),
        "snapshot_dir": display_path(snapshot_dir),
    }
    conn: sqlite3.Connection = get_connection(str(history_db))
    try:
        create_schema(conn)
        conn.execute(
            """
            INSERT INTO audit_fixed_asset_mismatch_runs
            (run_id, audit_date, executed_at, matrix_sha256, matrix_csv_path,
             matrix_report_path, history_snapshot_dir, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                audit_date,
                executed_at.isoformat(),
                digest,
                display_path(matrix_csv_path),
                display_path(matrix_report_path),
                display_path(snapshot_dir),
                json.dumps(manifest, ensure_ascii=False, sort_keys=True),
            ),
        )
        conn.executemany(
            """
            INSERT INTO audit_fixed_asset_mismatch_history
            (run_id, fiscal_year, cc_code, account_code, period, expected_vnd,
             reference_vnd, delta_vnd, reference_formula_kind,
             source_asset_count, evidence_classification, decision_status,
             allowed_action, classification_reason, source_evidence_json,
             reference_evidence_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    fiscal_year_number(row["fy"]),
                    row["cc"],
                    int(row["account"]),
                    row["period"],
                    row["expected_per_asset_round_vnd"],
                    row["reference_actual_vnd"],
                    row["delta_reference_minus_expected_vnd"],
                    row["reference_formula_kind"],
                    row["source_asset_count_in_group"],
                    row["evidence_classification"],
                    row["decision_status"],
                    row["allowed_action"],
                    row["classification_reason"],
                    json.dumps(row["source_asset_evidence"], ensure_ascii=False, sort_keys=True),
                    json.dumps(row["reference_evidence"], ensure_ascii=False, sort_keys=True),
                )
                for row in rows
            ],
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
    index_path = history_dir / "run_index.csv"
    write_header = not index_path.exists()
    with index_path.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(index_row))
        if write_header:
            writer.writeheader()
        writer.writerow(index_row)
    return run_id, snapshot_dir


def main() -> None:
    import argparse

    parser = VietnameseArgumentParser()
    parser.add_argument(
        "--history-dir",
        type=Path,
        default=AUDIT_DIR / "history" / "fixed_assets",
        help="Thư mục chỉ ghi nối tiếp để lưu ảnh chụp kiểm toán bất biến.",
    )
    parser.add_argument(
        "--history-db",
        type=Path,
        default=ROOT / "mp2027.db",
        help="Cơ sở dữ liệu SQLite lưu lịch sử chênh lệch để truy vấn.",
    )
    parser.add_argument(
        "--skip-history",
        action="store_true",
        help="Chỉ tạo lại ma trận hiện tại; không tạo bản ghi lịch sử.",
    )
    args = parser.parse_args()
    ledger = read_csv(f"fixed_assets_asset_ledger_{AUDIT_DATE}.csv")
    references = read_csv(f"fixed_assets_reference_rows_{AUDIT_DATE}.csv")
    comparisons = read_csv(f"fixed_assets_monthly_comparison_{AUDIT_DATE}.csv")
    true_rows = [row for row in comparisons if row["classification"] == "TRUE_AMOUNT_MISMATCH"]
    source_by_key = source_assets_by_key(ledger)
    reference_by_key = selected_reference_by_key(references)
    all_source_asset_numbers = {str(row["asset_no"]) for row in ledger if row["asset_no"] not in ("", "None")}
    group_deltas = group_delta_pattern(comparisons)
    comparison_by_key_period = {
        (row["fy"], row["cc"], int(row["account"]), row["period"]): row for row in comparisons
    }
    matrix: list[dict[str, Any]] = []
    for row in true_rows:
        key = (row["fy"], row["cc"], int(row["account"]))
        source_rows = source_by_key.get(key, [])
        reference_rows = reference_by_key.get(key, [])
        classification, decision, action, reason = classify_row(
            row,
            source_rows,
            reference_rows,
            all_source_asset_numbers,
            group_deltas.get(key, set()),
            comparison_by_key_period,
        )
        components = reference_components(reference_rows, row["period"])
        matrix.append(
            {
                "fy": row["fy"],
                "cc": row["cc"],
                "account": int(row["account"]),
                "period": row["period"],
                "expected_per_asset_round_vnd": as_int(row["expected_per_asset_round_vnd"]),
                "reference_actual_vnd": as_int(row["reference_actual_vnd"]),
                "delta_reference_minus_expected_vnd": as_int(row["delta_reference_minus_expected"]),
                "reference_formula_kind": formula_kind(reference_rows, row["period"]),
                "source_asset_count_in_group": len(source_rows),
                "source_asset_evidence": source_components(source_rows, int(row["account"]), row["period"]),
                "reference_evidence": components,
                "evidence_classification": classification,
                "decision_status": decision,
                "allowed_action": action,
                "classification_reason": reason,
            }
        )
    if len(matrix) != 638:
        raise RuntimeError(f"Cần 638 ô TRUE_AMOUNT_MISMATCH, tìm thấy {len(matrix)}")
    if any(row["decision_status"] not in VALID_DECISIONS for row in matrix):
        raise RuntimeError("Ma trận quyết định chứa trạng thái quyết định không hợp lệ")
    missing_provenance = [
        row
        for row in matrix
        if not row["source_asset_evidence"] or not row["reference_evidence"]
    ]
    if missing_provenance:
        sample = [
            {
                "fy": row["fy"], "cc": row["cc"], "account": row["account"], "period": row["period"],
                "has_source": bool(row["source_asset_evidence"]),
                "has_reference": bool(row["reference_evidence"]),
            }
            for row in missing_provenance[:10]
        ]
        raise RuntimeError(f"Các dòng quyết định đang thiếu thông tin nguồn gốc: {sample}")
    fields = [
        "fy", "cc", "account", "period", "expected_per_asset_round_vnd", "reference_actual_vnd",
        "delta_reference_minus_expected_vnd", "reference_formula_kind", "source_asset_count_in_group",
        "source_asset_evidence", "reference_evidence", "evidence_classification", "decision_status",
        "allowed_action", "classification_reason",
    ]
    csv_path = AUDIT_DIR / f"fixed_assets_true_mismatch_decision_matrix_{AUDIT_DATE}.csv"
    report_path = AUDIT_DIR / f"fixed_assets_true_mismatch_decision_matrix_{AUDIT_DATE}.md"
    write_csv(csv_path, matrix, fields)
    write_report(report_path, matrix)
    if not args.skip_history:
        run_id, snapshot_dir = archive_audit_history(
            matrix,
            audit_date=AUDIT_DATE,
            matrix_csv_path=csv_path,
            matrix_report_path=report_path,
            history_dir=args.history_dir.resolve(),
            history_db=args.history_db.resolve(),
        )
        print(f"ĐÃ GHI lượt lịch sử {run_id}: {snapshot_dir}")
    print(f"ĐÃ GHI {csv_path}")
    print(f"ĐÃ GHI {report_path}")
    print(json.dumps({"cells": len(matrix), "classifications": Counter(row["evidence_classification"] for row in matrix), "decisions": Counter(row["decision_status"] for row in matrix)}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
