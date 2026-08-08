from pathlib import Path

import pytest

from src.services.batch_publication import BatchPublicationError, publish_selected_cc_batch


def _write_workbook(path: Path, payload: str) -> None:
    path.write_bytes(payload.encode("utf-8"))


def test_selected_cc_batch_publishes_all_workbooks_in_one_snapshot(tmp_path):
    public = tmp_path / "OUTPUT_FY2027"
    public.mkdir()
    _write_workbook(public / "MP_CC_100.xlsx", "old-100")
    _write_workbook(public / "MP_CC_200.xlsx", "old-200")
    _write_workbook(public / "untouched.txt", "keep")

    stage = tmp_path / "private-stage"
    stage.mkdir()
    _write_workbook(stage / "MP_CC_100.xlsx", "new-100")
    _write_workbook(stage / "MP_CC_200.xlsx", "new-200")

    assert publish_selected_cc_batch(public, stage, ("100", "200")) == str(public)
    assert (public / "MP_CC_100.xlsx").read_text() == "new-100"
    assert (public / "MP_CC_200.xlsx").read_text() == "new-200"
    assert (public / "untouched.txt").read_text() == "keep"


def test_selected_cc_batch_rejects_incomplete_stage_without_touching_public_output(tmp_path):
    public = tmp_path / "OUTPUT_FY2027"
    public.mkdir()
    _write_workbook(public / "MP_CC_100.xlsx", "old-100")
    _write_workbook(public / "MP_CC_200.xlsx", "old-200")

    stage = tmp_path / "private-stage"
    stage.mkdir()
    _write_workbook(stage / "MP_CC_100.xlsx", "new-100")

    with pytest.raises(BatchPublicationError, match="không toàn vẹn"):
        publish_selected_cc_batch(public, stage, ("100", "200"))

    assert (public / "MP_CC_100.xlsx").read_text() == "old-100"
    assert (public / "MP_CC_200.xlsx").read_text() == "old-200"
