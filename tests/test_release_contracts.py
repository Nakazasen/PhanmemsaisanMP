"""Fast semantic contract plus an explicitly opt-in performance budget."""

from __future__ import annotations

import os
from time import perf_counter

import pytest

from src.engine.source_order_output import (
    CANONICAL_SOURCE_FILE_ORDER,
    OutputRow,
    place_rows_by_source_file_order,
)


@pytest.mark.unit
def test_source_order_semantic_contract(synthetic_output_rows):
    placed = place_rows_by_source_file_order(synthetic_output_rows, start_row=20)

    snapshot = [
        (
            row.output_row,
            row.source_file,
            row.values.get("item"),
            row.is_blank_separator,
        )
        for row in placed
    ]
    assert snapshot == [
        (20, CANONICAL_SOURCE_FILE_ORDER[0], "facility-1", False),
        (21, CANONICAL_SOURCE_FILE_ORDER[0], "facility-2", False),
        (22, CANONICAL_SOURCE_FILE_ORDER[0], None, True),
        (23, CANONICAL_SOURCE_FILE_ORDER[4], "birthday", False),
        (24, CANONICAL_SOURCE_FILE_ORDER[4], None, True),
        (25, "new-department-costs.xlsx", "unknown", False),
    ]


@pytest.mark.performance
@pytest.mark.skipif(
    os.environ.get("MP_MANAGER_RUN_PERFORMANCE") != "1",
    reason="opt-in only: set MP_MANAGER_RUN_PERFORMANCE=1",
)
def test_source_order_10k_rows_stays_within_budget():
    rows = [
        OutputRow(
            CANONICAL_SOURCE_FILE_ORDER[index % len(CANONICAL_SOURCE_FILE_ORDER)],
            {"sequence": index},
        )
        for index in range(10_000)
    ]

    started = perf_counter()
    placed = place_rows_by_source_file_order(rows, start_row=1)
    elapsed = perf_counter() - started

    assert len(placed) == 10_000 + len(CANONICAL_SOURCE_FILE_ORDER) - 1
    assert elapsed < 2.0, f"source-order placement took {elapsed:.3f}s (budget: 2.0s)"
