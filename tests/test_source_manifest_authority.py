from pathlib import Path

import openpyxl

from src.utils.source_manifest import read_source_manifest


def test_saved_manifest_accepts_renamed_source_without_filename_classification(tmp_path):
    source = tmp_path / "renamed-anything.xlsx"
    source.write_bytes(b"configured source placeholder")
    workbook = openpyxl.Workbook()
    worksheet = workbook.active
    worksheet.append(
        ("order", "category", "filename", "enabled", "description", "period_start", "period_end")
    )
    worksheet.append(("1", "it_simulation", source.name, "1", "renamed", "202604", "202606"))
    workbook.save(tmp_path / "source_file_order.xlsx")
    workbook.close()

    entries = read_source_manifest(str(tmp_path))

    assert len(entries) == 1
    assert Path(entries[0]["_path"]) == source
    assert entries[0]["period_start"] == "202604"
    assert entries[0]["period_end"] == "202606"
