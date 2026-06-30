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
