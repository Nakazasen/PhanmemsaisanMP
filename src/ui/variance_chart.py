"""Small, testable chart-data adapter for the MP YoY screen."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import sys
from typing import Iterable

from src.engine.variance_analyzer import CostLineVariance


@dataclass(frozen=True)
class VarianceChartRow:
    label: str
    amount: float
    color: str


def resolve_multilingual_font_path(*, language: str = "vi") -> Path | None:
    """Find a Windows font that can render the active chart language."""
    japanese_font_candidates = [
        Path(r"C:\Windows\Fonts\meiryo.ttc"),
        Path(r"C:\Windows\Fonts\YuGothR.ttc"),
    ]
    if language == "ja":
        return next((path for path in japanese_font_candidates if path.is_file()), None)

    candidates = [
        Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / "assets" / "fonts" / "NotoSansTC-Regular.ttf",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.append(Path(local_app_data) / "Microsoft" / "Windows" / "Fonts" / "NotoSansTC-Regular.ttf")
    candidates.extend(
        Path(path)
        for path in (
            r"C:\Windows\Fonts\NotoSansTC-Regular.ttf",
            r"C:\Windows\Fonts\segoeui.ttf",
        )
    )
    return next((path for path in candidates if path.is_file()), None)


def build_variance_chart_rows(
    lines: Iterable[CostLineVariance], *, limit: int = 12, language: str = "vi"
) -> list[VarianceChartRow]:
    """Return the largest meaningful changes, preserving increase/decrease."""
    changed = [line for line in lines if line.variance_absolute != 0]
    changed.sort(key=lambda line: abs(line.variance_absolute), reverse=True)

    rows: list[VarianceChartRow] = []
    for line in changed[:max(0, limit)]:
        name = str(line.item_name or "").strip()
        bilingual_parts = [part.strip() for part in name.split("/") if part.strip()]
        if len(bilingual_parts) >= 2:
            name = bilingual_parts[0] if language == "ja" else bilingual_parts[-1]
        account = str(line.account_code or "").strip()
        label = f"{account} - {name}" if account and name else (name or account)
        rows.append(
            VarianceChartRow(
                label=label,
                amount=line.variance_absolute,
                color="#2e7d32" if line.variance_absolute > 0 else "#c62828",
            )
        )
    return rows
