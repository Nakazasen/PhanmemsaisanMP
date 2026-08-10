from pathlib import Path


SOURCE = Path("src/universal_app.py").read_text(encoding="utf-8")


def test_gui_labels_and_messages_do_not_reintroduce_english_terms():
    forbidden_visible_phrases = (
        "Đang dùng project",
        "Mở/đổi project",
        "Tạo project",
        "Cấu hình project",
        "Thứ tự file nguồn",
        "Chọn file...",
        "Baseline T3",
        "Loại event",
        "Số người/count",
        "Key đơn giá",
        '"Period"',
        '"Count"',
        '"Alias TK"',
        '"Form row"',
        '"Source month"',
        '"Headcount basis"',
        '"Description"',
        '"Note"',
        "Sample help-only",
        "company trip May driver",
        "Đã công bố nguyên tử toàn bộ batch",
    )

    assert not [phrase for phrase in forbidden_visible_phrases if phrase in SOURCE]


def test_event_editor_localizes_display_values_without_changing_saved_codes():
    assert '"Câu chuyện của tôi": "My Episode"' in SOURCE
    assert '"Theo số lượng và đơn giá": "manual_count_unit_price"' in SOURCE
    assert '"Theo số tiền trực tiếp": "manual_amount"' in SOURCE
    assert '"Theo tháng riêng": "month_specific_driver"' in SOURCE
    assert "event_display_to_value.get" in SOURCE
    assert "event_type_display_to_value.get" in SOURCE
