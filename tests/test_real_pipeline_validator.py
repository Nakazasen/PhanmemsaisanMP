import sqlite3

import pytest

from src.audit.real_pipeline_validator import (
    BASELINE_PROVENANCE,
    _catalog_row,
    _validate_staffing,
)
from src.utils.fiscal_periods import fiscal_periods


TARGET_CC = "1412000005"


def _create_validator_database(path):
    connection = sqlite3.connect(path)
    connection.executescript(
        """
        CREATE TABLE fact_input_data (
            cc_code TEXT NOT NULL,
            account_code INTEGER NOT NULL
        );
        CREATE TABLE fact_monthly_headcount (
            period TEXT NOT NULL,
            cc_code TEXT NOT NULL,
            source TEXT NOT NULL,
            description TEXT,
            headcount_all REAL,
            headcount_expat REAL,
            headcount_staff REAL,
            headcount_worker REAL,
            headcount_local_total REAL
        );
        CREATE TABLE fact_manual_headcount_baseline_override (
            fiscal_year INTEGER NOT NULL,
            period TEXT NOT NULL,
            cc_code TEXT NOT NULL,
            description TEXT
        );
        """
    )
    connection.execute(
        "INSERT INTO fact_input_data(cc_code,account_code) VALUES(?,5005026371)",
        (TARGET_CC,),
    )
    balanced = (1476.0, 0.0, 103.0, 1373.0, 1476.0)
    connection.execute(
        """INSERT INTO fact_monthly_headcount
           (period,cc_code,source,description,headcount_all,headcount_expat,
            headcount_staff,headcount_worker,headcount_local_total)
           VALUES('202603',?,'manual',?,?,?,?,?,?)""",
        (TARGET_CC, BASELINE_PROVENANCE, *balanced),
    )
    connection.execute(
        """INSERT INTO fact_manual_headcount_baseline_override
           (fiscal_year,period,cc_code,description) VALUES(2027,'202603',?,?)""",
        (TARGET_CC, BASELINE_PROVENANCE),
    )
    connection.executemany(
        """INSERT INTO fact_monthly_headcount
           (period,cc_code,source,description,headcount_all,headcount_expat,
            headcount_staff,headcount_worker,headcount_local_total)
           VALUES(?,?,'department_plan','source',?,?,?,?,?)""",
        [(period, TARGET_CC, *balanced) for period in fiscal_periods(2027)],
    )
    connection.commit()
    return connection


def test_catalog_lookup_is_fail_closed_and_does_not_create_missing_database(tmp_path):
    catalog = tmp_path / "missing" / "run_history.db"

    with pytest.raises(FileNotFoundError):
        _catalog_row(catalog, "absent-run")

    assert not catalog.exists()
    assert not catalog.parent.exists()


def test_staffing_validator_accepts_balanced_real_sqlite_fixture(tmp_path):
    database = tmp_path / "run.db"
    connection = _create_validator_database(database)
    connection.close()

    evidence = _validate_staffing(
        database,
        fiscal_year=2027,
        target_cc=TARGET_CC,
        expected_provenance=BASELINE_PROVENANCE,
    )

    assert evidence["baseline_period"] == "202603"
    assert evidence["department_plan_periods"] == fiscal_periods(2027)
    assert evidence["target_input_fact_rows"] == 1


def test_staffing_validator_rejects_duplicate_department_plan_period(tmp_path):
    database = tmp_path / "run.db"
    connection = _create_validator_database(database)
    connection.execute(
        """INSERT INTO fact_monthly_headcount
           (period,cc_code,source,description,headcount_all,headcount_expat,
            headcount_staff,headcount_worker,headcount_local_total)
           VALUES('202604',?,'department_plan','duplicate',1476,0,103,1373,1476)""",
        (TARGET_CC,),
    )
    connection.commit()
    connection.close()

    with pytest.raises(ValueError, match="Phạm vi dữ liệu nhân sự phòng ban không hợp lệ"):
        _validate_staffing(
            database,
            fiscal_year=2027,
            target_cc=TARGET_CC,
            expected_provenance=BASELINE_PROVENANCE,
        )
