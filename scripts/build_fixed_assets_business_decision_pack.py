"""Condense the fixed-assets decision matrix into business-review requests.

This consumes the row-level matrix; it makes no accounting or workbook change.
Each request groups one FY/cost-center/account/cause so business reviewers can
choose a governing snapshot or supply the missing evidence without reviewing
all 638 monthly cells individually.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

from classify_fixed_assets_mismatches import AUDIT_DATE, AUDIT_DIR


REVIEW_CLASSES = {
    "REFERENCE_EMBEDDED_USD_SNAPSHOT_FORMULA",
    "CONSISTENT_REFERENCE_ADJUSTMENT",
    "REFERENCE_ASSET_NOT_IN_SOURCE_SNAPSHOT",
    "UNEXPLAINED_FORMULA_OR_AGGREGATE_CONTRADICTION",
}


def read_matrix() -> list[dict[str, str]]:
    csv.field_size_limit(sys.maxsize)
    path = AUDIT_DIR / f"fixed_assets_true_mismatch_decision_matrix_{AUDIT_DATE}.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def compact_evidence(serialized: str, *, limit: int = 3) -> str:
    values = json.loads(serialized)
    result: list[str] = []
    for value in values[:limit]:
        if "reference_file" in value:
            result.append(f"{value['reference_file']}|{value['sheet']}!{value['row']}")
        else:
            result.append(
                f"{value['source_file']}|{value['sheet']}!{value['row']}"
                f"|asset={value.get('asset_no') or value.get('asset_text') or ''}"
            )
    return " ; ".join(result)


def question_for(evidence_classification: str) -> tuple[str, str]:
    if evidence_classification == "REFERENCE_ASSET_NOT_IN_SOURCE_SNAPSHOT":
        return (
            "Xác nhận các asset trong file phòng ban có phải mua/snapshot sau file nguồn hay không; nếu có, cung cấp asset register/snapshot được duyệt.",
            "PROVIDE_APPROVED_NEWER_REGISTER | PRESERVE_REFERENCE_EXCEPTION",
        )
    if evidence_classification == "UNEXPLAINED_FORMULA_OR_AGGREGATE_CONTRADICTION":
        return (
            "Cung cấp chứng từ hoặc công thức giải thích điều chỉnh; không thể chọn số đúng từ dữ liệu hiện có.",
            "PROVIDE_ROW_LEVEL_EVIDENCE | PRESERVE_REFERENCE_EXCEPTION",
        )
    return (
        "Chọn snapshot chính thức dùng cho kế hoạch: asset ledger nguồn hay công thức USD nhúng trong file phòng ban.",
        "ADOPT_SOURCE_LEDGER | PRESERVE_REFERENCE_SNAPSHOT | PROVIDE_APPROVED_NEWER_REGISTER",
    )


def main() -> None:
    grouped: defaultdict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in read_matrix():
        classification = row["evidence_classification"]
        if classification in REVIEW_CLASSES:
            grouped[(row["fy"], row["cc"], row["account"], classification)].append(row)

    requests: list[dict[str, Any]] = []
    for index, (key, rows) in enumerate(sorted(grouped.items()), start=1):
        fy, cc, account, classification = key
        question, allowed_responses = question_for(classification)
        periods = sorted(row["period"] for row in rows)
        requests.append(
            {
                "request_id": f"FA-DEC-{index:03d}",
                "fy": fy,
                "cc": cc,
                "account": account,
                "evidence_classification": classification,
                "monthly_cells": len(rows),
                "periods": ";".join(periods),
                "expected_vnd_total": sum(int(row["expected_per_asset_round_vnd"] or 0) for row in rows),
                "reference_vnd_total": sum(int(row["reference_actual_vnd"] or 0) for row in rows),
                "delta_vnd_total": sum(int(row["delta_reference_minus_expected_vnd"] or 0) for row in rows),
                "source_evidence_examples": compact_evidence(rows[0]["source_asset_evidence"]),
                "reference_evidence_examples": compact_evidence(rows[0]["reference_evidence"]),
                "business_question": question,
                "accepted_response": allowed_responses,
            }
        )

    csv_path = AUDIT_DIR / f"fixed_assets_business_decision_requests_{AUDIT_DATE}.csv"
    fields = list(requests[0]) if requests else []
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(requests)

    classes: defaultdict[str, int] = defaultdict(int)
    for row in requests:
        classes[str(row["evidence_classification"])] += int(row["monthly_cells"])
    markdown_path = AUDIT_DIR / f"fixed_assets_business_decision_requests_{AUDIT_DATE}.md"
    markdown_path.write_text(
        "\n".join(
            [
                "# Fixed assets — business decision requests",
                "",
                f"This pack condenses **{sum(classes.values())}** cells into **{len(requests)}** decisions. "
                "It excludes rows already proven by source policy and rows already classified as manual/other layers.",
                "",
                "| Classification | Cells requiring review |",
                "| --- | ---: |",
                *[f"| `{classification}` | {count} |" for classification, count in sorted(classes.items())],
                "",
                "## Reviewer instruction",
                "",
                "For each `request_id` in the CSV, choose exactly one permitted response or attach the stated evidence. "
                "Do not use this pack to overwrite a departmental output before approval.",
                "",
                f"- Detail source: `fixed_assets_true_mismatch_decision_matrix_{AUDIT_DATE}.csv`.",
                f"- Decision requests: `fixed_assets_business_decision_requests_{AUDIT_DATE}.csv`.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"WROTE {csv_path}")
    print(f"WROTE {markdown_path}")
    print({"requests": len(requests), "cells": sum(classes.values()), "by_class": dict(classes)})


if __name__ == "__main__":
    main()
