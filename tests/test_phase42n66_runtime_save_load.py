import csv
import hashlib
import sqlite3
from pathlib import Path

import pytest

from src.db.schema import create_schema
from src.parsers.manual_headcount import parse_manual_headcount
from src.universal_app import validate_headcount_save_period_rows
from src.parsers.manual_headcount import get_required_headcount_periods, validate_manual_headcount_rows

HEADER = ["cc_code", "period", "headcount_staff", "headcount_worker", "headcount_male", "headcount_female", "description"]


def _period_rows(fiscal_year, staff="0", worker="0"):
    periods = get_required_headcount_periods(fiscal_year)
    labels = {p: p for p in periods}
    inputs = {p: {"staff": staff, "worker": worker, "male": "", "female": "", "description": ""} for p in periods}
    rows, errors = validate_headcount_save_period_rows(periods, inputs, labels)
    assert errors == []
    return rows


def _write_csv(path: Path, cc_rows):
    with path.open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=HEADER)
        writer.writeheader()
        for cc, rows in cc_rows:
            for row in rows:
                out = {"cc_code": cc, **row}
                writer.writerow(out)


def _read_csv(path: Path):
    with path.open(newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def _seed_runtime(conn, fiscal_year, *ccs):
    conn.execute("INSERT OR REPLACE INTO sys_params (key, value) VALUES (?, ?)", ("fiscal_year", str(fiscal_year)))
    for cc in ccs:
        conn.execute("INSERT OR IGNORE INTO dim_cost_centers (code, name_jp, name_vn, saisan_type, cost_type) VALUES (?, ?, ?, ?, ?)", (cc, cc, cc, "製造", "製造"))
    conn.commit()


def _db_periods(conn, cc):
    cur = conn.cursor()
    return [r[0] for r in cur.execute("SELECT period FROM fact_monthly_headcount WHERE cc_code=? AND source='manual' ORDER BY period", (cc,))]


def test_temp_csv_db_save_load_fy2027_and_multi_cc(tmp_path):
    csv_path = tmp_path / "headcount_manual.csv"
    rows_a = _period_rows(2027, staff="0", worker="0")
    rows_b = _period_rows(2027, staff="5", worker="1")
    _write_csv(csv_path, [("1412000006", rows_a), ("1412000007", rows_b)])
    loaded = _read_csv(csv_path)
    assert [r["period"] for r in loaded if r["cc_code"] == "1412000006"] == ["202603", "202604", "202605", "202606", "202607", "202608", "202609", "202610", "202611", "202612", "202701", "202702", "202703"]
    assert [r["period"] for r in loaded if r["cc_code"] == "1412000007"] == ["202603", "202604", "202605", "202606", "202607", "202608", "202609", "202610", "202611", "202612", "202701", "202702", "202703"]

    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    try:
        _seed_runtime(conn, 2027, "1412000006", "1412000007")
        result = parse_manual_headcount(conn, str(tmp_path))
        assert result["errors"] == 0
        assert _db_periods(conn, "1412000006") == sorted(["202603", "202604", "202605", "202606", "202607", "202608", "202609", "202610", "202611", "202612", "202701", "202702", "202703"])
        assert _db_periods(conn, "1412000007") == sorted(["202603", "202604", "202605", "202606", "202607", "202608", "202609", "202610", "202611", "202612", "202701", "202702", "202703"])
    finally:
        conn.close()


def test_temp_csv_db_save_load_fy2028(tmp_path):
    csv_path = tmp_path / "headcount_manual.csv"
    rows_a = _period_rows(2028, staff="0", worker="0")
    _write_csv(csv_path, [("1412000006", rows_a)])
    loaded_periods = [r["period"] for r in _read_csv(csv_path)]
    assert loaded_periods == ["202703", "202704", "202705", "202706", "202707", "202708", "202709", "202710", "202711", "202712", "202801", "202802", "202803"]
    assert "202804" not in loaded_periods


def test_atomic_failure_does_not_change_csv_or_db(tmp_path):
    csv_path = tmp_path / "headcount_manual.csv"
    rows_a = _period_rows(2027, staff="1", worker="0")
    _write_csv(csv_path, [("1412000006", rows_a)])
    before_hash = hashlib.sha256(csv_path.read_bytes()).hexdigest()
    conn = sqlite3.connect(":memory:")
    create_schema(conn)
    try:
        _seed_runtime(conn, 2027, "1412000006")
        assert parse_manual_headcount(conn, str(tmp_path))["errors"] == 0
        before_db = list(conn.execute("SELECT cc_code, period, headcount_staff, headcount_worker FROM fact_monthly_headcount ORDER BY cc_code, period"))
        bad_rows = _read_csv(csv_path)
        bad_rows[1]["headcount_worker"] = ""
        result = validate_manual_headcount_rows(bad_rows, {"1412000006"}, 2027)
        assert result["errors"] > 0
        # GUI save path returns before write/parse on validation error.
        assert hashlib.sha256(csv_path.read_bytes()).hexdigest() == before_hash
        after_db = list(conn.execute("SELECT cc_code, period, headcount_staff, headcount_worker FROM fact_monthly_headcount ORDER BY cc_code, period"))
        assert after_db == before_db
    finally:
        conn.close()
