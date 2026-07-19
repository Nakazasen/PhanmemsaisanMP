from scripts.export_schema_documentation import markdown, schema_catalog
from src.db.migrations import CURRENT_SCHEMA_VERSION


def test_schema_catalog_is_generated_without_runtime_data():
    catalog = schema_catalog()
    names = {table["name"] for table in catalog["tables"]}
    assert catalog["runtime_data_included"] is False
    assert catalog["schema_version"] == CURRENT_SCHEMA_VERSION
    assert {"dim_cost_centers", "fact_input_data", "schema_migrations"} <= names


def test_schema_dictionary_contains_erd_and_regeneration_command():
    text = markdown(schema_catalog())
    assert "```mermaid" in text
    assert "fact_allocation_log" in text
    assert "py scripts/export_schema_documentation.py" in text
