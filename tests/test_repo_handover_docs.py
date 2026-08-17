from pathlib import Path


def test_readme_documents_handover_basics():
    text = Path("README.md").read_text(encoding="utf-8")

    assert "09.06.2026" in text
    assert "fail-closed" in text
    assert "missing input" in text
    assert "py -m pytest" in text
    assert "OUTPUT_FY2027" in text


def test_requirement_mapping_contains_core_groups():
    text = Path("docs/requirements/requirement_mapping.yaml").read_text(encoding="utf-8")

    for key in [
        "facility",
        "fixed_assets",
        "it_system_cost",
        "ga_admin_allocation",
        "birthday",
        "nnn_paperwork",
        "manual_headcount",
        "bus",
        "event_drivers",
        "special_costs",
    ]:
        assert f"id: {key}" in text

    assert "09.06.2026" in text
    assert "Do not invent data" in text


def test_repository_has_one_current_handover_with_verified_update_scope():
    canonical = Path("docs/handover/HANDOVER_FOR_NEXT_AGENT.md")
    handovers = sorted(Path("docs").rglob("HANDOVER_FOR_NEXT_AGENT.md"))

    assert handovers == [canonical]
    for obsolete in [
        "CURRENT_OPEN_ITEMS.md",
        "FIXED_ASSETS_DEEP_AUDIT_HANDOVER_2026-07-16.md",
        "FIXED_ASSETS_EVIDENCE_MANIFEST.md",
        "ui_not_responding_clean_form_handover.md",
    ]:
        assert not (Path("docs/handover") / obsolete).exists()

    text = canonical.read_text(encoding="utf-8")
    assert "handover hiện hành duy nhất" in text
    assert "c7fd76b" in text
    assert "LAN/UNC" in text
    assert "WAN/HTTPS" in text
    assert "fstvn01" in text
    assert "WAN/HTTPS: chưa có, tạm thời bỏ qua" in text
    assert "Không thêm backlog nghiệp vụ suy đoán" in text


def test_release_playbook_does_not_describe_online_delivery_as_unimplemented():
    text = Path("docs/handover/release_update_playbook.md").read_text(encoding="utf-8")

    assert "trước khi thêm luồng online tùy chọn" not in text
    assert "Trước khi build, xác minh hai endpoint đọc được" in text


def test_release_playbook_defines_full_update_publish_intent_and_stop_conditions():
    text = Path("docs/handover/release_update_playbook.md").read_text(encoding="utf-8")

    assert "đóng gói theo tiêu chuẩn update" in text
    assert "toàn bộ luồng update" in text
    assert "Đây được xem là quyền publish rõ ràng" in text
    assert "không được dừng ở\nartifact local" in text
    assert "Package cùng tên tồn tại nhưng hash khác" in text
    assert "không bao gồm commit, push, xóa hoặc di chuyển" in text
    assert "release_update\\latest.json" in text
    assert "patch kế tiếp" in text
    assert "bắt buộc phải có cả Setup" in text
    assert "publish Setup vào thư mục phần mềm LAN" in text


def test_current_handover_has_no_active_signing_instructions():
    text = Path("docs/handover/HANDOVER_FOR_NEXT_AGENT.md").read_text(encoding="utf-8")

    assert "HASH_ONLY_LAN" in text
    assert "Không tạo, tìm, khôi phục hoặc cấu hình khóa ký" in text
    assert "Catalog LAN hiện tại là `0.1.6`" in text
    assert "latest.json" in text
    assert "0.1.9" not in text
    assert "0.1.10" not in text


def test_default_update_source_is_the_approved_lan_folder_only():
    import json

    config = json.loads(Path("update_sources.default.json").read_text(encoding="utf-8"))

    assert config == {
        "schema": 1,
        "startup_check": True,
        "sources": [
            {
                "type": "folder",
                "location": (
                    r"\\fstvn01\Data\00_KDTVN Common(KDTVN共通)"
                    r"\⑤Production Engineering(製造技術)\Hang muc can luu"
                    r"\Vinh\MP Saisan\release_update"
                ),
                "enabled": True,
            }
        ],
    }
