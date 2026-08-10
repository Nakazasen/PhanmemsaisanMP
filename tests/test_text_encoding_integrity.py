from tools.check_mojibake import scan_repository


def test_tracked_text_files_have_no_detectable_mojibake():
    assert scan_repository() == []
