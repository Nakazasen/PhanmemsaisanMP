from src.engine.variance_analyzer import CostLineVariance, VarianceStatus
from src.ui.variance_chart import build_variance_chart_rows, resolve_multilingual_font_path


def _line(account: str, name: str, variance: float) -> CostLineVariance:
    return CostLineVariance(
        account_code=account,
        item_name=name,
        base_value=100.0,
        current_value=100.0 + variance,
        variance_absolute=variance,
        variance_percent=variance,
        status=VarianceStatus.INCREASE if variance > 0 else VarianceStatus.DECREASE,
        is_alert=False,
    )


def test_chart_rows_sort_by_material_change_and_keep_direction():
    rows = build_variance_chart_rows(
        [_line("100", "Small", 10), _line("200", "Decrease", -500), _line("300", "Increase", 900)],
        limit=2,
    )

    assert [row.label for row in rows] == ["300 - Increase", "200 - Decrease"]
    assert [row.amount for row in rows] == [900, -500]
    assert [row.color for row in rows] == ["#2e7d32", "#c62828"]


def test_chart_rows_exclude_unchanged_lines_and_use_account_when_name_missing():
    rows = build_variance_chart_rows([_line("100", "", 0), _line("200", "", 42)])

    assert len(rows) == 1
    assert rows[0].label == "200"


def test_chart_labels_follow_the_selected_ui_language_for_bilingual_source_names():
    source_name = "Japanese item/Vietnamese item"

    assert build_variance_chart_rows([_line("100", source_name, 42)], language="vi")[0].label == "100 - Vietnamese item"
    assert build_variance_chart_rows([_line("100", source_name, 42)], language="en")[0].label == "100 - Vietnamese item"
    assert build_variance_chart_rows([_line("100", source_name, 42)], language="ja")[0].label == "100 - Japanese item"


def test_chart_resolves_a_unicode_capable_system_font_when_available():
    font_path = resolve_multilingual_font_path(language="vi")
    japanese_font_path = resolve_multilingual_font_path(language="ja")

    assert font_path is not None
    assert font_path.is_file()
    assert japanese_font_path is not None
    assert japanese_font_path.is_file()
    assert japanese_font_path.name.lower() in {"meiryo.ttc", "yugothr.ttc"}
