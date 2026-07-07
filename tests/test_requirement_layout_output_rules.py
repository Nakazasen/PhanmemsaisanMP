"""Regression tests for docs/requirements/cai_tien_nhap_du_lieu_chung.md.

These tests lock the layout-output requirements from the canonical Excel
workbook dated 09.06.2026.  They read the committed markdown and assert
that mandatory phrases are present, so any accidental deletion or
rewrite will break CI immediately.

The tests do NOT depend on the raw Excel file.
"""

from pathlib import Path

import pytest

REQ_PATH = Path("docs/requirements/cai_tien_nhap_du_lieu_chung.md")


@pytest.fixture(scope="module")
def req_text():
    """Load the requirement markdown once per module."""
    assert REQ_PATH.exists(), f"Requirement file missing: {REQ_PATH}"
    return REQ_PATH.read_text(encoding="utf-8")


# ------------------------------------------------------------------
# 22.1  Data output starts from row 30
# ------------------------------------------------------------------
class TestRow30Rule:
    def test_mentions_row_30(self, req_text):
        assert "dòng 30" in req_text

    def test_row_30_context_is_output_start(self, req_text):
        assert "xuất dữ liệu từ" in req_text and "dòng 30" in req_text


# ------------------------------------------------------------------
# 22.2  Columns A:D must be white from row 30 onward
# ------------------------------------------------------------------
class TestColumnsADWhite:
    def test_mentions_columns_a_d(self, req_text):
        assert "A:D" in req_text or ("cột A" in req_text and "cột D" in req_text)

    def test_mentions_white_color(self, req_text):
        assert "màu trắng" in req_text

    def test_ad_white_in_same_section(self, req_text):
        # Both concepts must appear close together (within same section 22.2)
        idx_ad = req_text.find("cột A đến cột D")
        if idx_ad == -1:
            idx_ad = req_text.find("A:D")
        assert idx_ad != -1, "Cannot find A:D column reference"
        # "màu trắng" should appear within 500 chars of the A:D reference
        nearby = req_text[max(0, idx_ad - 200):idx_ad + 500]
        assert "màu trắng" in nearby


# ------------------------------------------------------------------
# 22.3  Column E must not contain agent-generated explanations
# ------------------------------------------------------------------
class TestColumnENoExplanation:
    def test_mentions_column_e(self, req_text):
        assert "cột E" in req_text or "Cột E" in req_text

    def test_no_explanation_rule(self, req_text):
        assert "không được có giải thích" in req_text


# ------------------------------------------------------------------
# 22.4  Explanations must come from column B of sheet *配賦額一覧
# ------------------------------------------------------------------
class TestExplanationSource:
    def test_mentions_column_b(self, req_text):
        assert "cột B" in req_text

    def test_mentions_haifugaku_ichiran_sheet(self, req_text):
        assert "配賦額一覧" in req_text

    def test_explanation_not_self_invented(self, req_text):
        assert "không được tự nghĩ" in req_text or "không tự nghĩ" in req_text


# ------------------------------------------------------------------
# 22.5  Canonical workbook wins over markdown
# ------------------------------------------------------------------
class TestCanonicalWins:
    def test_canonical_date_mentioned(self, req_text):
        assert "09.06.2026" in req_text

    def test_canonical_wins_language(self, req_text):
        lower = req_text.lower()
        assert "canonical" in lower or "workbook excel gốc" in lower.replace("\\n", " ")


# ------------------------------------------------------------------
# 22.6  No return to fixed-row output mode
# ------------------------------------------------------------------
class TestNoFixedRowReturn:
    def test_source_order_or_dynamic(self, req_text):
        assert "source-order" in req_text or "dynamic placement" in req_text

    def test_no_fixed_row_hardcode(self, req_text):
        assert "không quay lại" in req_text.lower() or "cách xuất cố định" in req_text


# ------------------------------------------------------------------
# 22.7  CC 1412000040 must ONLY appear in "do not hardcode" context
# ------------------------------------------------------------------
class TestNoHardcodeCC:
    def test_1412000040_context(self, req_text):
        """If 1412000040 appears, it must be in a 'không hardcode' context."""
        occurrences = []
        start = 0
        while True:
            idx = req_text.find("1412000040", start)
            if idx == -1:
                break
            # Extract surrounding context (300 chars around)
            context = req_text[max(0, idx - 300):idx + 300].lower()
            occurrences.append(context)
            start = idx + 1

        # Must have at least one mention
        assert len(occurrences) > 0, "1412000040 must be mentioned at least once"

        # Every occurrence must be in a 'no hardcode' or example/audit context
        for ctx in occurrences:
            safe = (
                "không hardcode" in ctx
                or "không được hardcode" in ctx
                or "ví dụ" in ctx
                or "ghi chú audit" in ctx
                or "không sử dụng làm" in ctx
                or "default" in ctx
            )
            assert safe, (
                f"1412000040 found outside 'không hardcode' context:\n"
                f"...{ctx[200:400]}..."
            )


# ------------------------------------------------------------------
# 22.8  No hardcode of 16.KDTVN file
# ------------------------------------------------------------------
class TestNoHardcodeKDTVN:
    def test_kdtvn_context(self, req_text):
        """If 16.KDTVN appears in requirements, it must be in 'do not hardcode' context."""
        idx = req_text.find("16.KDTVN")
        if idx == -1:
            # Not mentioned is also acceptable
            return
        context = req_text[max(0, idx - 300):idx + 300].lower()
        safe = (
            "không hardcode" in context
            or "không được hardcode" in context
            or "không map riêng" in context
        )
        assert safe, (
            f"16.KDTVN found outside 'không hardcode' context"
        )


# ------------------------------------------------------------------
# Structural: the section header itself must exist
# ------------------------------------------------------------------
class TestSectionExists:
    def test_section_22_header(self, req_text):
        assert "## 22. Yêu cầu layout output từ file gốc 09.06.2026" in req_text

    def test_section_22_subsections_count(self, req_text):
        count = req_text.count("### 22.")
        assert count >= 9, f"Expected >=9 subsections in section 22, got {count}"


# ------------------------------------------------------------------
# GAP-1: 22.9 Clear old content before writing new output
# ------------------------------------------------------------------
class TestClearOldContentRule:
    def test_section_22_9_exists(self, req_text):
        assert "### 22.9" in req_text

    def test_clear_keyword(self, req_text):
        assert "clear" in req_text.lower() or "xóa" in req_text.lower()


# ------------------------------------------------------------------
# GAP-2: Bus terminology "biệt phái"
# ------------------------------------------------------------------
class TestBusBietPhaiTerminology:
    def test_biet_phai_in_markdown(self, req_text):
        assert "biệt phái" in req_text, (
            "Markdown must use 'biệt phái' (Excel original term) alongside 'người Nhật'"
        )


# ------------------------------------------------------------------
# GAP-3: Section 23 completion status table
# ------------------------------------------------------------------
class TestCompletionStatusTable:
    def test_section_23_exists(self, req_text):
        assert "## 23." in req_text

    def test_tscd_not_complete(self, req_text):
        assert "Chưa chạy hết" in req_text, (
            "Section 23 must record TSCĐ as incomplete per Excel source"
        )


# ------------------------------------------------------------------
# GAP-4: Section 24.1 regression guard health check duplicate
# ------------------------------------------------------------------
class TestRegressionHealthCheckDuplicate:
    def test_section_24_1_exists(self, req_text):
        assert "### 24.1" in req_text

    def test_duplicate_keyword(self, req_text):
        assert "lặp 2 lần" in req_text, (
            "Section 24.1 must document the health-check duplication bug"
        )


# ------------------------------------------------------------------
# GAP-5: Section 24.2 regression guard new employee month 12
# ------------------------------------------------------------------
class TestRegressionNewEmployeeMonth12:
    def test_section_24_2_exists(self, req_text):
        assert "### 24.2" in req_text

    def test_month_12_bug(self, req_text):
        assert "tháng 12" in req_text and "người mới" in req_text, (
            "Section 24.2 must document the month-12 aggregation bug"
        )


# ------------------------------------------------------------------
# GAP-6: Reference range A144~A169
# ------------------------------------------------------------------
class TestAdminRangeA144A169:
    def test_a144_reference(self, req_text):
        assert "A144" in req_text, (
            "Markdown must reference range A144~A169 from Excel source"
        )

    def test_a169_reference(self, req_text):
        assert "A169" in req_text


# ------------------------------------------------------------------
# GAP-7: Section 25 description supplement
# ------------------------------------------------------------------
class TestDescriptionSupplement:
    def test_section_25_exists(self, req_text):
        assert "## 25." in req_text

    def test_needs_clarification(self, req_text):
        assert "NEEDS_CLARIFICATION" in req_text, (
            "Section 25 must flag 'bổ sung mô tả' as needing clarification"
        )
