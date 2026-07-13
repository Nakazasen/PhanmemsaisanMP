"""Pure output row placement planner for MP2027.

This module calculates planned row positions from output mode specs only. It has
no Excel/openpyxl dependency and does not write workbooks.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from src.engine.output_mode import OutputGroupSpec, OutputMode, sort_output_groups_by_file_order


@dataclass(frozen=True)
class PlannedOutputGroup:
    """Planned row placement metadata for one output source-file group."""

    group_id: str
    output_mode: OutputMode
    source_file_name: str
    order_index: int
    start_row: int | None
    end_row: int | None
    item_rows: tuple[tuple[str, int], ...]
    blank_row_after: int | None
    notes: str = ""


def _file_order_group_row_count(spec: OutputGroupSpec, item_counts: Mapping[str, int]) -> int:
    if spec.group_id in item_counts:
        return max(1, int(item_counts[spec.group_id]))
    if spec.cost_items:
        return max(1, len(spec.cost_items))
    return 1


def _item_labels(spec: OutputGroupSpec, row_count: int) -> tuple[str, ...]:
    labels = tuple(spec.cost_items[:row_count])
    if len(labels) == row_count:
        return labels
    generated = tuple(f"item_{index}" for index in range(len(labels) + 1, row_count + 1))
    return labels + generated


def _planned_rows(spec: OutputGroupSpec, start_row: int, row_count: int) -> tuple[tuple[str, int], ...]:
    return tuple(
        (label, start_row + offset)
        for offset, label in enumerate(_item_labels(spec, row_count))
    )


def plan_output_groups(
    specs: tuple[OutputGroupSpec, ...],
    start_row: int,
    item_counts: dict[str, int] | None = None,
) -> tuple[PlannedOutputGroup, ...]:
    """Plan output group rows without mutating specs or writing Excel files."""
    counts = item_counts or {}
    current_row = int(start_row)
    planned: list[PlannedOutputGroup] = []

    for spec in sort_output_groups_by_file_order(specs):
        row_count = 0
        notes = spec.notes
        if spec.output_mode == OutputMode.FILE_ORDER_GROUP:
            row_count = _file_order_group_row_count(spec, counts)
        elif spec.output_mode == OutputMode.FILE_ORDER_SINGLE_ROW:
            row_count = 1
        elif spec.output_mode == OutputMode.MIXED_TRANSITION:
            notes = "mixed_transition_no_write_yet"
        elif spec.output_mode == OutputMode.ROW_COMPAT_OR_FILE_ORDER_PENDING:
            notes = "row_compat_or_file_order_pending_no_write_yet"
        elif spec.output_mode == OutputMode.FIXED_ROW:
            notes = "fixed_row_no_file_order_write"

        if row_count > 0:
            group_start_row: int | None = current_row
            group_end_row: int | None = current_row + row_count - 1
            item_rows = _planned_rows(spec, current_row, row_count)
            blank_row_after = group_end_row + 1 if spec.blank_row_after_group else None
            current_row = group_end_row + (2 if spec.blank_row_after_group else 1)
        else:
            group_start_row = None
            group_end_row = None
            item_rows = ()
            blank_row_after = current_row if spec.blank_row_after_group else None
            current_row += 1 if spec.blank_row_after_group else 0

        planned.append(
            PlannedOutputGroup(
                group_id=spec.group_id,
                output_mode=spec.output_mode,
                source_file_name=spec.source_file_name,
                order_index=spec.order_index,
                start_row=group_start_row,
                end_row=group_end_row,
                item_rows=item_rows,
                blank_row_after=blank_row_after,
                notes=notes,
            )
        )

    return tuple(planned)
