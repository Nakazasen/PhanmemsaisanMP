"""Output mode definitions for MP2027 hub row placement.

This module is intentionally a pure planning abstraction. It does not import or
call the workbook writer, parsers, database layer, or template code.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Iterable


class OutputMode(StrEnum):
    """Canonical output placement modes from Phase 42N1L."""

    FIXED_ROW = "FIXED_ROW"
    FILE_ORDER_GROUP = "FILE_ORDER_GROUP"
    FILE_ORDER_SINGLE_ROW = "FILE_ORDER_SINGLE_ROW"
    MIXED_TRANSITION = "MIXED_TRANSITION"
    ROW_COMPAT_OR_FILE_ORDER_PENDING = "ROW_COMPAT_OR_FILE_ORDER_PENDING"


@dataclass(frozen=True)
class OutputGroupSpec:
    """Declarative output placement spec for one source-file group."""

    group_id: str
    display_name: str
    source_file_name: str
    output_mode: OutputMode
    order_index: int
    cost_items: tuple[str, ...] = field(default_factory=tuple)
    fixed_rows: tuple[int, ...] = field(default_factory=tuple)
    blank_row_after_group: bool = True
    notes: str = ""

    @property
    def costs_expected(self) -> int:
        """Return the number of declared cost items for the group."""
        return len(self.cost_items)


_DEFAULT_OUTPUT_GROUP_SPECS: tuple[OutputGroupSpec, ...] = (
    OutputGroupSpec(
        group_id="facility",
        display_name="Facility",
        source_file_name="施設課　MPFY2027.xlsx",
        output_mode=OutputMode.FILE_ORDER_GROUP,
        order_index=1,
        cost_items=(
            "6 chi phí",
            "depreciation_building",
            "depreciation_land",
            "interest_building",
            "interest_land",
            "electric",
            "water",
        ),
        blank_row_after_group=True,
        notes="File-order group; no immediate row 40 patch.",
    ),
    OutputGroupSpec(
        group_id="fixed_assets",
        display_name="Fixed Assets",
        source_file_name="固定資産情報_Fixed_Assets_Information_2025.11 - Nov.xlsx",
        output_mode=OutputMode.MIXED_TRANSITION,
        order_index=2,
        fixed_rows=(38, 42),
        blank_row_after_group=True,
        notes="Keep row 38/42 compatibility until fixed-assets transition is decided.",
    ),
    OutputGroupSpec(
        group_id="system_cost",
        display_name="System Cost",
        source_file_name="システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls",
        output_mode=OutputMode.FILE_ORDER_SINGLE_ROW,
        order_index=3,
        cost_items=("one combined row",),
        blank_row_after_group=True,
        notes="System cost should be grouped into one cost row.",
    ),
    OutputGroupSpec(
        group_id="admin_allocation",
        display_name="Admin allocation",
        source_file_name="総務課 FY2027 MP 振替予定.xlsx",
        output_mode=OutputMode.FILE_ORDER_GROUP,
        order_index=4,
        blank_row_after_group=True,
        notes="High-priority file-order group.",
    ),
    OutputGroupSpec(
        group_id="birthday",
        display_name="Birthday",
        source_file_name="Sinh nhật MP FY2027.xlsx",
        output_mode=OutputMode.ROW_COMPAT_OR_FILE_ORDER_PENDING,
        order_index=5,
        fixed_rows=(59, 63),
        blank_row_after_group=True,
        notes="Keep row 59/63 compatibility risk until mode decision is final.",
    ),
    OutputGroupSpec(
        group_id="allocation_master",
        display_name="Allocation master",
        source_file_name="FY2027配賦額一覧 (2025.12.29).xlsx",
        output_mode=OutputMode.FILE_ORDER_GROUP,
        order_index=6,
        blank_row_after_group=True,
        notes="Allocation master file-order group.",
    ),
    OutputGroupSpec(
        group_id="nnn_paperwork",
        display_name="NNN paperwork",
        source_file_name="Dự tính chi phí làm giấy tờ cho NNN FY2027.xlsx",
        output_mode=OutputMode.ROW_COMPAT_OR_FILE_ORDER_PENDING,
        order_index=7,
        fixed_rows=(137,),
        blank_row_after_group=True,
        notes="Keep row 137 compatibility until NNN file-order decision is final.",
    ),
)


def get_default_output_group_specs() -> tuple[OutputGroupSpec, ...]:
    """Return canonical default output group specs sorted by requirement order."""
    return _DEFAULT_OUTPUT_GROUP_SPECS


def sort_output_groups_by_file_order(specs: Iterable[OutputGroupSpec]) -> list[OutputGroupSpec]:
    """Sort output groups by requirement file order."""
    return sorted(specs, key=lambda spec: (spec.order_index, spec.group_id))


def get_group_spec(group_id: str) -> OutputGroupSpec:
    """Return the default output group spec for ``group_id``."""
    for spec in _DEFAULT_OUTPUT_GROUP_SPECS:
        if spec.group_id == group_id:
            return spec
    raise KeyError(f"Unknown output group: {group_id}")


def requires_blank_row_after_group(spec: OutputGroupSpec) -> bool:
    """Return whether a blank row should separate this completed group."""
    return bool(spec.blank_row_after_group)


def is_file_order_mode(spec: OutputGroupSpec) -> bool:
    """Return whether the spec is intended for file-order placement."""
    return spec.output_mode in {
        OutputMode.FILE_ORDER_GROUP,
        OutputMode.FILE_ORDER_SINGLE_ROW,
    }


def is_fixed_row_compatible(spec: OutputGroupSpec) -> bool:
    """Return whether the spec carries fixed-row compatibility metadata."""
    return bool(spec.fixed_rows) or spec.output_mode in {
        OutputMode.FIXED_ROW,
        OutputMode.MIXED_TRANSITION,
        OutputMode.ROW_COMPAT_OR_FILE_ORDER_PENDING,
    }
