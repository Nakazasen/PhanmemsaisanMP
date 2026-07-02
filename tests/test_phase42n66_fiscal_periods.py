import csv
from pathlib import Path

import pytest

from src.parsers.manual_headcount import get_required_headcount_periods, validate_manual_headcount_rows, validate_manual_bus_headcount_rows
from src.utils.fiscal_periods import fiscal_baseline_period, fiscal_month_labels, fiscal_period_for_month, fiscal_periods
from src.utils.excel_helpers import get_fy_months, get_month_mapping


def test_fiscal_period_helper_examples():
    assert fiscal_period_for_month(2027, 4) == "202604"
    assert fiscal_period_for_month(2027, 12) == "202612"
    assert fiscal_period_for_month(2027, 1) == "202701"
    assert fiscal_period_for_month(2027, 3) == "202703"
    assert fiscal_period_for_month(2028, 4) == "202704"
    assert fiscal_period_for_month(2028, 12) == "202712"
    assert fiscal_period_for_month(2028, 1) == "202801"
    assert fiscal_period_for_month(2028, 3) == "202803"
    assert fiscal_period_for_month(2029, 4) == "202804"
    assert fiscal_period_for_month(2029, 3) == "202903"


@pytest.mark.parametrize("bad_month", [0, 13, "x"])
def test_fiscal_period_invalid_month_rejects(bad_month):
    with pytest.raises(ValueError):
        fiscal_period_for_month(2027, bad_month)


def test_fiscal_period_invalid_year_rejects():
    with pytest.raises(ValueError):
        fiscal_period_for_month("bad", 4)


def test_period_lists_and_baseline():
    assert fiscal_periods(2027) == ["202604", "202605", "202606", "202607", "202608", "202609", "202610", "202611", "202612", "202701", "202702", "202703"]
    assert fiscal_periods(2028) == ["202704", "202705", "202706", "202707", "202708", "202709", "202710", "202711", "202712", "202801", "202802", "202803"]
    assert fiscal_periods(2029) == ["202804", "202805", "202806", "202807", "202808", "202809", "202810", "202811", "202812", "202901", "202902", "202903"]
    for fy in [2027, 2028, 2029]:
        periods = fiscal_periods(fy)
        assert len(periods) == 12
        assert len(set(periods)) == 12
        assert fiscal_baseline_period(fy) not in periods
    assert fiscal_baseline_period(2027) == "202603"
    assert fiscal_baseline_period(2028) == "202703"
    assert fiscal_baseline_period(2029) == "202803"
    assert "202704" not in fiscal_periods(2027)
    assert "202804" not in fiscal_periods(2028)


def test_legacy_excel_helpers_delegate_to_fiscal_helper():
    assert get_fy_months(2027) == fiscal_periods(2027)
    assert get_month_mapping(2027)[0] == "202604"
    assert get_month_mapping(2027)[11] == "202703"


def test_gui_labels_follow_canonical_month_only_requirement_with_period_mapping():
    rows_2027 = {m: (p, label) for m, p, label in fiscal_month_labels(2027)}
    rows_2028 = {m: (p, label) for m, p, label in fiscal_month_labels(2028)}
    assert rows_2027[4] == ("202604", "Tháng 4")
    assert rows_2027[1] == ("202701", "Tháng 1")
    assert rows_2028[4] == ("202704", "Tháng 4")


def _rows(cc, fiscal_year, staff="0", worker="0"):
    return [
        {"cc_code": cc, "period": p, "headcount_staff": staff, "headcount_worker": worker, "headcount_male": "", "headcount_female": "", "description": ""}
        for p in get_required_headcount_periods(fiscal_year)
    ]


def test_validation_accepts_zero_and_rejects_wrong_fy_periods():
    valid = {"1412000006"}
    result = validate_manual_headcount_rows(_rows("1412000006", 2027, staff="0", worker="0"), valid, 2027)
    assert result["errors"] == 0
    bad = _rows("1412000006", 2027)
    bad[1]["period"] = "202704"
    result = validate_manual_headcount_rows(bad, valid, 2027)
    assert result["errors"] == 1
    assert result["error_details"][0]["field"] == "period"
    fy2028 = _rows("1412000006", 2028)
    assert "202704" in [r["period"] for r in fy2028]
    assert validate_manual_headcount_rows(fy2028, valid, 2028)["errors"] == 0


def test_blank_decimal_text_duplicate_and_multi_cc_isolation():
    valid = {"1412000006", "1412000007"}
    assert validate_manual_headcount_rows(_rows("1412000006", 2027, staff="", worker="0"), valid, 2027)["errors"] > 0
    assert validate_manual_headcount_rows(_rows("1412000006", 2027, staff="1.5", worker="0"), valid, 2027)["errors"] > 0
    assert validate_manual_headcount_rows(_rows("1412000006", 2027, staff="x", worker="0"), valid, 2027)["errors"] > 0
    rows = _rows("1412000006", 2027) + _rows("1412000007", 2027)
    assert validate_manual_headcount_rows(rows, valid, 2027)["errors"] == 0
    dup = _rows("1412000006", 2027) + [_rows("1412000006", 2027)[0]]
    assert validate_manual_headcount_rows(dup, valid, 2027)["errors"] > 0


def test_bus_scalar_contract_has_no_period():
    rows = [{"cc_code": "1412000006", "bus_expat_count": "0", "bus_vietnamese_count": "22", "description": ""}]
    result = validate_manual_bus_headcount_rows(rows, {"1412000006"})
    assert result["errors"] == 0
    assert "period" not in result["valid_rows"][0]


def test_scope_guards_fixed_assets_and_canonical_writer_unchanged():
    fixed = Path("src/parsers/fixed_assets.py").read_text(encoding="utf-8")
    assert "HEADER_ALIASES" in fixed
    assert "LEGACY_COLUMN_MAP" in fixed
    assert '"cc_code": 7' in fixed
    assert "helpers.extract_cc_code(row[9]" not in fixed
    canonical = Path("src/engine/complete_v1_source_order_writer.py").read_text(encoding="utf-8")
    assert "MANAGED_CLEAR_COLS" in canonical


def test_no_forbidden_manual_fiscal_calendar_concat():
    text = Path("src/universal_app.py").read_text(encoding="utf-8") + Path("src/parsers/manual_headcount.py").read_text(encoding="utf-8")
    assert "{fiscal_year}{" not in text
    assert 'f"{fy}{' not in text
