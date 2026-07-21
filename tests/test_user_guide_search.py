from src.universal_app import USER_GUIDE_TEXT_LATEST, filter_user_guide_text


def test_guide_search_is_accent_insensitive_and_returns_compact_matches():
    rendered, count = filter_user_guide_text(USER_GUIDE_TEXT_LATEST, "nam nu")

    assert count >= 1
    assert "Nam/Nữ" in rendered
    assert len(rendered) < len(USER_GUIDE_TEXT_LATEST)


def test_guide_search_finds_update_instructions_and_handles_no_match():
    rendered, count = filter_user_guide_text(USER_GUIDE_TEXT_LATEST, "cai ban cap nhat")
    assert count >= 1
    assert "Cài bản cập nhật" in rendered

    empty, count = filter_user_guide_text(USER_GUIDE_TEXT_LATEST, "tu-khoa-khong-ton-tai")
    assert count == 0
    assert "Không tìm thấy" in empty
