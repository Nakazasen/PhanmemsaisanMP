"""Tiện ích tương thích FY2027 chỉ đọc, không được nạp cho các năm sau."""

import unicodedata


FY2027_AUDITED_REFERENCE_UNIT_PRICES = (
    (("月餅", "bánh trung thu", "banh trung thu", "luna cake"), 56000.0),
    (("運動会", "đại hội thể thao", "dai hoi the thao", "sports day"), 107000.0),
)


def _normalize(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(char for char in text if not unicodedata.combining(char)).lower()


def apply_audited_fy2027_reference_price(item_name: str, unit_price: float) -> float:
    """Legacy audit helper only; never call it from the annual rule loader."""
    if float(unit_price or 0.0) > 0:
        return float(unit_price)
    item = _normalize(item_name)
    for tokens, price in FY2027_AUDITED_REFERENCE_UNIT_PRICES:
        if any(_normalize(token) in item for token in tokens):
            return price
    return float(unit_price or 0.0)
