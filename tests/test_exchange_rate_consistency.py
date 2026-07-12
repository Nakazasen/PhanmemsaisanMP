from pathlib import Path

import pytest
from openpyxl import Workbook, load_workbook

from src.audit.exchange_rate_audit import (
    assert_exchange_rate_formulas_safe,
    normalize_exchange_rate_formula,
)
from src.utils.excel_helpers import read_exchange_rate_from_form, write_exchange_rate_to_form


SHEET = "内訳ﾘｽﾄ(4～3月)"


def _workbook(path: Path, rate: float = 26273.0, formula: str = "=ROUND(2*$B$2,0)") -> Path:
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = SHEET
    worksheet["B2"] = rate
    worksheet["F30"] = formula
    workbook.save(path)
    workbook.close()
    return path


def test_output_rate_is_written_to_b2_without_changing_the_template(tmp_path):
    template = _workbook(tmp_path / "template.xlsx")
    output = _workbook(tmp_path / "output.xlsx")

    write_exchange_rate_to_form(output, 25000)

    assert read_exchange_rate_from_form(template) == 26273
    assert read_exchange_rate_from_form(output) == 25000
    assert assert_exchange_rate_formulas_safe(output, 25000)["status"] == "PASS"


def test_reference_formula_normalization_uses_absolute_b2_rate_cell():
    assert normalize_exchange_rate_formula("=ROUND(4*B2,0)", 25000) == "=ROUND(4*$B$2,0)"
    assert normalize_exchange_rate_formula("=14*2*26273", 25000) == "=14*2*$B$2"
    assert normalize_exchange_rate_formula("=3*25450", 25000) == "=3*$B$2"


def test_audit_rejects_hardcoded_or_unanchored_exchange_rate_formulas(tmp_path):
    hardcoded = _workbook(tmp_path / "hardcoded.xlsx", rate=25000, formula="=2*26273")
    with pytest.raises(ValueError, match="F30"):
        assert_exchange_rate_formulas_safe(hardcoded, 25000)

    unanchored = _workbook(tmp_path / "unanchored.xlsx", rate=25000, formula="=2*B2")
    with pytest.raises(ValueError, match="F30"):
        assert_exchange_rate_formulas_safe(unanchored, 25000)

    normalized = _workbook(
        tmp_path / "normalized.xlsx",
        rate=25000,
        formula=normalize_exchange_rate_formula("=2*26273", 25000),
    )
    assert assert_exchange_rate_formulas_safe(normalized, 25000)["status"] == "PASS"
