import csv
import sqlite3
from pathlib import Path

from src.db.schema import create_schema
from src.parsers.manual_headcount import (
    copy_missing_baseline_from_april,
    parse_manual_headcount,
)
from src.universal_app import MPManagerApp


def test_copy_missing_baseline_t3_from_t4_persists_and_is_parseable(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.execute("INSERT INTO sys_params(key,value) VALUES('fiscal_year','2027')")
    conn.execute(
        "INSERT INTO dim_cost_centers(code,name_jp,saisan_type,cost_type) VALUES('1412000001','CC 01','MFG','Fixed')"
    )
    conn.execute(
        """INSERT INTO fact_monthly_headcount
        (period,cc_code,headcount_all,headcount_expat,headcount_staff,headcount_worker,
         headcount_local_total,source)
        VALUES('202604','1412000001',15,2,5,8,13,'department_plan')"""
    )
    conn.commit()

    copied = copy_missing_baseline_from_april(conn, str(tmp_path), 2027)

    assert copied["copied"] == 1
    with open(copied["template_path"], encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows == [
        {
            "cc_code": "1412000001",
            "period": "202603",
            "headcount_expat": "2",
            "headcount_staff": "5",
            "headcount_worker": "8",
            "headcount_male": "",
            "headcount_female": "",
            "description": "COPIED_BASELINE_T3_FROM_T4",
        }
    ]

    result = parse_manual_headcount(conn, str(tmp_path))
    assert result["errors"] == 0
    baseline = conn.execute(
        """SELECT headcount_all,headcount_expat,headcount_staff,headcount_worker,description
        FROM fact_monthly_headcount WHERE period='202603' AND cc_code='1412000001' AND source='manual'"""
    ).fetchone()
    assert tuple(baseline) == (15.0, 2.0, 5.0, 8.0, "COPIED_BASELINE_T3_FROM_T4")


def test_copy_missing_baseline_t3_does_not_replace_existing_manual_row(tmp_path):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_schema(conn)
    conn.execute(
        "INSERT INTO fact_monthly_headcount(period,cc_code,headcount_all,source) VALUES('202604','1412000001',8,'department_plan')"
    )
    (tmp_path / "headcount_manual.csv").write_text(
        "cc_code,period,headcount_staff,headcount_worker,headcount_male,headcount_female,description\n"
        "1412000001,202603,4,3,,,Người dùng nhập\n",
        encoding="utf-8-sig",
    )

    copied = copy_missing_baseline_from_april(conn, str(tmp_path), 2027)

    assert copied["copied"] == 0
    with open(tmp_path / "headcount_manual.csv", encoding="utf-8-sig", newline="") as handle:
        assert list(csv.DictReader(handle))[0]["description"] == "Người dùng nhập"


def test_gui_passes_confirmed_t3_copy_to_pipeline_command():
    command = MPManagerApp._pipeline_subprocess_command(
        None,
        2027,
        "FORM.xlsx",
        "source",
        "headcount-source",
        25450.0,
        "1412000001",
        True,
    )

    assert "--copy-baseline-t3-from-t4" in command
    source = Path("src/universal_app.py").read_text(encoding="utf-8")
    assert 'text="Yes"' in source
    assert 'text="Mở Nhập nhân sự thủ công"' in source
    assert 'text="No"' in source
