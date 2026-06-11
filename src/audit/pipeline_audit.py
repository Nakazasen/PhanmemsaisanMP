"""Pipeline audit report for user confidence and missing-input review."""

from __future__ import annotations

import csv
import os
import sqlite3
from pathlib import Path
from typing import Any

from src.parsers.manual_event_drivers import TEMPLATE_FILENAME as EVENT_DRIVER_FILENAME
from src.utils.excel_helpers import get_fy_months


def _count_rows(conn: sqlite3.Connection, source: str) -> int:
    row = conn.execute("SELECT COUNT(*) FROM fact_input_data WHERE source = ?", (source,)).fetchone()
    return int(row[0] or 0)


def _distinct_cc_count(conn: sqlite3.Connection, source: str) -> int:
    row = conn.execute("SELECT COUNT(DISTINCT cc_code) FROM fact_input_data WHERE source = ?", (source,)).fetchone()
    return int(row[0] or 0)


def _manual_event_rows(source_dir: str) -> int:
    path = Path(source_dir) / EVENT_DRIVER_FILENAME
    if not path.exists():
        return 0
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return sum(1 for row in reader if any(str(value or "").strip() for value in row.values()))


def _manual_headcount_ccs(conn: sqlite3.Connection) -> set[str]:
    return {
        str(row[0]).strip()
        for row in conn.execute("SELECT DISTINCT cc_code FROM fact_monthly_headcount WHERE source = 'manual'").fetchall()
        if row[0] is not None
    }


def _manual_health_check_gender_ccs(conn: sqlite3.Connection, fiscal_year: int) -> set[str]:
    december_period = f"{fiscal_year - 1}12"
    return {
        str(row[0]).strip()
        for row in conn.execute(
            """
            SELECT DISTINCT cc_code
            FROM fact_monthly_headcount
            WHERE source = 'manual'
              AND period = ?
              AND (headcount_male > 0 OR headcount_female > 0)
            """,
            (december_period,),
        ).fetchall()
        if row[0] is not None
    }


def _target_ccs(conn: sqlite3.Connection, target_cc: object | None) -> list[str]:
    if target_cc:
        return [str(target_cc).strip()]
    return [
        str(row[0]).strip()
        for row in conn.execute("SELECT code FROM dim_cost_centers ORDER BY code").fetchall()
        if row[0] is not None
    ]


def _recorded_missing_inputs(conn: sqlite3.Connection) -> list[dict[str, str]]:
    rows = conn.execute(
        """
        SELECT severity, cc_code, period, area, message, action
        FROM fact_missing_inputs
        ORDER BY id
        """
    ).fetchall()
    return [
        {
            "severity": str(row["severity"] or "action"),
            "cc_code": str(row["cc_code"] or ""),
            "period": str(row["period"] or ""),
            "area": str(row["area"] or ""),
            "message": str(row["message"] or ""),
            "action": str(row["action"] or ""),
        }
        for row in rows
    ]


def write_pipeline_audit_report(
    *,
    conn: sqlite3.Connection,
    output_dir: str,
    source_dir: str,
    fiscal_year: int,
    target_cc: object | None,
    parser_results: dict[str, dict[str, Any]],
) -> dict[str, str]:
    """Write an audit markdown report and a missing-input CSV.

    This report is intentionally business-facing: it explains what the system did,
    what it did not infer, and what the user must provide to make output complete.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "MP2027_AUDIT_REPORT.md"
    missing_csv_path = out_dir / "MP2027_MISSING_INPUTS.csv"

    fy_months = get_fy_months(fiscal_year)
    manual_hc_ccs = _manual_headcount_ccs(conn)
    health_gender_ccs = _manual_health_check_gender_ccs(conn, fiscal_year)
    cc_list = _target_ccs(conn, target_cc)
    manual_event_count = _manual_event_rows(source_dir)

    missing_rows: list[dict[str, str]] = []
    for cc_code in cc_list:
        if cc_code not in manual_hc_ccs:
            missing_rows.append(
                {
                    "severity": "review",
                    "cc_code": cc_code,
                    "period": "",
                    "area": "headcount",
                    "message": "Chưa có manual headcount cho CC này; pipeline sẽ dùng master headcount/fallback nếu có.",
                    "action": "Nếu CC này cần tính theo số người thực tế từng tháng, nhập vào headcount_manual.csv.",
                }
            )

        if cc_code not in health_gender_ccs:
            missing_rows.append(
                {
                    "severity": "review",
                    "cc_code": cc_code,
                    "period": f"{fiscal_year - 1}12",
                    "area": "health_check_gender_split",
                    "message": "Chưa có dữ liệu Nam/Nữ tháng 12 cho health-check row 57.",
                    "action": "Nếu CC này cần tính khám sức khỏe theo Nam/Nữ, nhập headcount_male/headcount_female tháng 12 trong headcount_manual.csv.",
                }
            )

    if manual_event_count == 0:
        missing_rows.append(
            {
                "severity": "action",
                "cc_code": str(target_cc or "ALL"),
                "period": ",".join(fy_months),
                "area": "manual_event_driver",
                "message": "Chưa có dòng sự kiện thủ công nào cho các số liệu không thể suy luận.",
                "action": (
                    "Nếu có JP/VN bus, quà không đi du lịch, kỷ niệm 10 năm, company anniversary, "
                    "VISA/Passport row khác 137..., hãy nhập vào event_drivers_manual.csv."
                ),
            }
        )

    missing_rows.extend(_recorded_missing_inputs(conn))

    source_summary = {
        "manual_event_driver": _count_rows(conn, "manual_event_driver"),
        "nnn_paperwork": _count_rows(conn, "nnn_paperwork"),
        "birthday_workbook": _count_rows(conn, "birthday_workbook"),
        "manual_special_cost": _count_rows(conn, "manual_special_cost"),
        "it_sim": _count_rows(conn, "it_sim"),
        "facility": _count_rows(conn, "facility"),
        "fixed_assets": _count_rows(conn, "fixed_assets"),
    }

    with missing_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        fieldnames = ["severity", "cc_code", "period", "area", "message", "action"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(missing_rows)

    lines = [
        "# MP2027 Audit Report",
        "",
        f"- Fiscal year: `FY{fiscal_year}`",
        f"- Target CC: `{target_cc or 'ALL'}`",
        f"- Source folder: `{source_dir}`",
        f"- Output folder: `{output_dir}`",
        "",
        "## Nguyên tắc an toàn",
        "",
        "- Chương trình không tự bịa số liệu.",
        "- Nếu có file nguồn máy đọc được, chương trình lấy từ file nguồn và để lại công thức trong FORM khi có thể.",
        "- Nếu thiếu số liệu không thể suy luận, chương trình dựa vào danh sách cần người dùng nhập/chốt.",
        "",
        "## Dữ liệu đã nạp",
        "",
        "| Nguồn | Số record | Số CC | Ghi chú |",
        "|---|---:|---:|---|",
    ]
    source_notes = {
        "manual_event_driver": "Dữ liệu người dùng nhập cho sự kiện không thể suy luận.",
        "nnn_paperwork": "Workbook NNN/VISA/GPLD/Passport FY2027 vào row 137.",
        "birthday_workbook": "Workbook sinh nhật vào row 59, công thức count*152000.",
        "manual_special_cost": "Override thủ công theo form_row.",
        "it_sim": "Chi phí hệ thống.",
        "facility": "Khấu hao/lãi nhà đất/điện/nước.",
        "fixed_assets": "Tài sản cố định.",
    }
    for source, count in source_summary.items():
        lines.append(f"| `{source}` | {count} | {_distinct_cc_count(conn, source)} | {source_notes[source]} |")

    lines.extend(
        [
            "",
            "## Kết quả parser",
            "",
            "| Parser | Inserted | Skipped | Errors | File |",
            "|---|---:|---:|---:|---|",
        ]
    )
    for name, result in parser_results.items():
        path = result.get("path") or result.get("template_path") or ""
        lines.append(
            "| `{name}` | {inserted} | {skipped} | {errors} | `{path}` |".format(
                name=name,
                inserted=result.get("inserted", result.get("total", 0)),
                skipped=result.get("skipped", 0),
                errors=result.get("errors", 0),
                path=path,
            )
        )

    lines.extend(["", "## Cần người dùng xem/chốt", ""])
    if missing_rows:
        lines.extend(
            [
                "| Mức độ | CC | Kỳ | Khu vực | Cần làm |",
                "|---|---|---|---|---|",
            ]
        )
        for row in missing_rows:
            lines.append(
                f"| `{row['severity']}` | `{row['cc_code']}` | `{row['period']}` | {row['area']} | {row['action']} |"
            )
    else:
        lines.append("- Chưa phát hiện missing input trong các check hiện tại.")

    lines.extend(
        [
            "",
            "## File liên quan",
            "",
            f"- Missing-input CSV: `{missing_csv_path}`",
            f"- Manual event input: `{Path(source_dir) / EVENT_DRIVER_FILENAME}`",
            "",
        ]
    )
    report_path.write_text("\n".join(lines), encoding="utf-8")
    return {"report_path": str(report_path), "missing_csv_path": str(missing_csv_path)}
