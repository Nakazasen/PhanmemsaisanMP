"""Định nghĩa chế độ đặt dòng kết quả trong Hub MP2027.

Đây là lớp trừu tượng lập kế hoạch thuần, không nhập hoặc gọi bộ ghi sổ làm
việc, bộ đọc dữ liệu, lớp cơ sở dữ liệu hay mã mẫu biểu.
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
        display_name="Chi phí cơ sở vật chất",
        source_file_name="",
        output_mode=OutputMode.FILE_ORDER_GROUP,
        order_index=1,
        cost_items=(
            "6 chi phí cơ sở vật chất",
            "Khấu hao nhà xưởng",
            "Khấu hao đất",
            "Lãi vay nhà xưởng",
            "Lãi vay đất",
            "Điện",
            "Nước",
        ),
        blank_row_after_group=True,
        notes="Nhóm theo thứ tự tệp; không ghi đè ngay vào dòng 40.",
    ),
    OutputGroupSpec(
        group_id="fixed_assets",
        display_name="Tài sản cố định",
        source_file_name="",
        output_mode=OutputMode.FILE_ORDER_GROUP,
        order_index=2,
        cost_items=("Khấu hao tài sản cố định", "Lãi vay tài sản cố định"),
        blank_row_after_group=True,
        notes="Nhóm theo thứ tự tệp nguồn; các dòng FORM cũ 38/42 không phải vị trí đích.",
    ),
    OutputGroupSpec(
        group_id="system_cost",
        display_name="Chi phí hệ thống",
        source_file_name="",
        output_mode=OutputMode.FILE_ORDER_SINGLE_ROW,
        order_index=3,
        cost_items=("Một dòng chi phí tổng hợp",),
        blank_row_after_group=True,
        notes="Chi phí hệ thống được gộp vào một dòng chi phí.",
    ),
    OutputGroupSpec(
        group_id="admin_allocation",
        display_name="Phân bổ hành chính",
        source_file_name="",
        output_mode=OutputMode.FILE_ORDER_GROUP,
        order_index=4,
        blank_row_after_group=True,
        notes="Nhóm ưu tiên cao theo thứ tự tệp.",
    ),
    OutputGroupSpec(
        group_id="birthday",
        display_name="Sinh nhật",
        source_file_name="",
        output_mode=OutputMode.FILE_ORDER_SINGLE_ROW,
        order_index=5,
        cost_items=("Chi phí sinh nhật",),
        blank_row_after_group=True,
        notes="Dòng theo thứ tự tệp nguồn; các dòng FORM cũ 59/63 không phải vị trí đích.",
    ),
    OutputGroupSpec(
        group_id="allocation_master",
        display_name="Danh mục phân bổ",
        source_file_name="",
        output_mode=OutputMode.FILE_ORDER_GROUP,
        order_index=6,
        blank_row_after_group=True,
        notes="Nhóm danh mục phân bổ theo thứ tự tệp.",
    ),
    OutputGroupSpec(
        group_id="nnn_paperwork",
        display_name="Hồ sơ NNN",
        source_file_name="",
        output_mode=OutputMode.FILE_ORDER_SINGLE_ROW,
        order_index=7,
        cost_items=("Hồ sơ NNN",),
        blank_row_after_group=True,
        notes="Dòng theo thứ tự tệp nguồn; dòng FORM cũ 137 không phải vị trí đích.",
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
    raise KeyError(f"Nhóm xuất không xác định: {group_id}")


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
