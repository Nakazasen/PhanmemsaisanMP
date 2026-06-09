"""Source-file-order output row placement helpers.

This module is intentionally pure. It does not read or write Excel files; it only
assigns output rows to already-derived business rows.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from src.engine.output_mode import get_default_output_group_specs

CANONICAL_SOURCE_FILE_ORDER = list(
    spec.source_file_name for spec in get_default_output_group_specs()
)


@dataclass(frozen=True)
class OutputRow:
    source_file: str
    values: dict[str, Any]
    provenance: str = ""


@dataclass(frozen=True)
class PlacedRow:
    output_row: int
    source_file: str
    values: dict[str, Any]
    provenance: str = ""
    is_blank_separator: bool = False


def source_file_name(source_file: str) -> str:
    return source_file.replace("/", "\\").split("\\")[-1]


def source_order_index(source_file: str) -> int:
    name = source_file_name(source_file)
    try:
        return CANONICAL_SOURCE_FILE_ORDER.index(name)
    except ValueError:
        return len(CANONICAL_SOURCE_FILE_ORDER)


def group_rows_by_canonical_source_order(rows: Iterable[OutputRow]) -> tuple[tuple[str, tuple[OutputRow, ...]], ...]:
    buckets: dict[str, list[OutputRow]] = {}
    for row in rows:
        buckets.setdefault(source_file_name(row.source_file), []).append(row)

    ordered_names = sorted(buckets, key=lambda name: (source_order_index(name), name))
    return tuple((name, tuple(buckets[name])) for name in ordered_names)


def place_rows_by_source_file_order(rows: Iterable[OutputRow], *, start_row: int) -> tuple[PlacedRow, ...]:
    """Place rows sequentially by canonical source file order.

    Rules:
    - preserve row order inside each source file block;
    - insert exactly one blank separator row between completed file blocks;
    - do not use legacy FORM target rows such as 38/42/58/59/97/98/137.
    """
    placed: list[PlacedRow] = []
    current_row = int(start_row)
    groups = group_rows_by_canonical_source_order(rows)

    for group_index, (source_name, group_rows) in enumerate(groups):
        for row in group_rows:
            placed.append(
                PlacedRow(
                    output_row=current_row,
                    source_file=source_name,
                    values=dict(row.values),
                    provenance=row.provenance,
                )
            )
            current_row += 1

        if group_index != len(groups) - 1:
            placed.append(
                PlacedRow(
                    output_row=current_row,
                    source_file=source_name,
                    values={},
                    provenance="BLANK_SEPARATOR_AFTER_SOURCE_FILE",
                    is_blank_separator=True,
                )
            )
            current_row += 1

    return tuple(placed)
