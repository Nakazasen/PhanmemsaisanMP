from pathlib import Path

from src.engine.admin_consumables_preview import preview_admin_consumables_file_order

ADMIN_SOURCE = Path("raw/総務課 FY2027 MP 振替予定.xlsx")
ALLOC_SOURCE = Path("raw/FY2027配賦額一覧 (2025.12.29).xlsx")


def test_admin_consumables_preview_finds_three_exact_items():
    preview = preview_admin_consumables_file_order(ADMIN_SOURCE, ALLOC_SOURCE)
    assert [item.item_id for item in preview.items] == ["toilet_paper", "hand_soap", "alcohol_disinfectant"]
    assert [item.display_name for item in preview.items] == ["トイレットペーパー", "手洗い洗剤", "アルコール消毒"]
    assert all(item.confidence == "HIGH" for item in preview.items)


def test_admin_consumables_preview_rows_207_to_209_blank_210():
    preview = preview_admin_consumables_file_order(ADMIN_SOURCE, ALLOC_SOURCE)
    assert [item.planned_row for item in preview.items] == [207, 208, 209]
    assert preview.blank_row_after == 210
