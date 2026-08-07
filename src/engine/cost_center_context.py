"""Kiểm tra ngữ cảnh trung tâm chi phí cho các bộ ghi kết quả được gọi rõ ràng."""

from __future__ import annotations

from typing import Any


def require_cost_center(cost_center: Any, *, context: str) -> str:
    text = "" if cost_center is None else str(cost_center).strip()
    if text.endswith(".0") and text[:-2].isdigit():
        text = text[:-2]
    if not text:
        raise ValueError(f"{context} requires an explicit cost_center from the export context.")
    return text
