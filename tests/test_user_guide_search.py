from src.services.i18n import set_current_language
from src.services.user_guide_content import (
    get_user_guide_search_suggestions,
    get_user_guide_text,
)
from src.universal_app import USER_GUIDE_TEXT_LATEST, filter_user_guide_text


def test_guide_search_is_accent_insensitive_and_returns_compact_matches():
    set_current_language("vi")
    rendered, count = filter_user_guide_text(USER_GUIDE_TEXT_LATEST, "nam nu")

    assert count >= 1
    assert "Nam/Nữ" in rendered
    assert len(rendered) < len(USER_GUIDE_TEXT_LATEST)


def test_guide_search_finds_update_instructions_and_handles_no_match():
    set_current_language("vi")
    rendered, count = filter_user_guide_text(USER_GUIDE_TEXT_LATEST, "cai ban cap nhat")
    assert count >= 1
    assert "Cài bản cập nhật" in rendered

    empty, count = filter_user_guide_text(USER_GUIDE_TEXT_LATEST, "tu-khoa-khong-ton-tai")
    assert count == 0
    assert "Không tìm thấy" in empty


def test_guide_search_multilingual_japanese_and_english():
    # Japanese
    set_current_language("ja")
    ja_text = get_user_guide_text("ja")
    rendered, count = filter_user_guide_text(ja_text, "原価センタ")
    assert count >= 1
    assert "原価センタ" in rendered
    assert "クイック検索結果" in rendered

    empty_ja, count_ja = filter_user_guide_text(ja_text, "存在しないキーワード")
    assert count_ja == 0
    assert "該当する内容が見つかりませんでした" in empty_ja

    # English
    set_current_language("en")
    en_text = get_user_guide_text("en")
    rendered_en, count_en = filter_user_guide_text(en_text, "Cost Center")
    assert count_en >= 1
    assert "Cost Center" in rendered_en
    assert "QUICK SEARCH RESULTS" in rendered_en

    empty_en, count_en = filter_user_guide_text(en_text, "nonexistentkeywordxyz")
    assert count_en == 0
    assert "男女" in get_user_guide_search_suggestions("ja")
    assert "gender" in get_user_guide_search_suggestions("en")
    assert "Nam Nữ" in get_user_guide_search_suggestions("vi")
