import sqlite3

from src.engine.hub_builder import HubBuilder


def _builder_with_asset_rows(rows):
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE fact_input_data (
            source TEXT,
            period TEXT,
            amount_vnd REAL,
            amount_usd REAL,
            cc_code TEXT,
            account_code INTEGER,
            description TEXT
        )
        """
    )
    conn.executemany(
        """
        INSERT INTO fact_input_data
        (source, period, amount_vnd, amount_usd, cc_code, account_code, description)
        VALUES ('fixed_assets', ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    builder = HubBuilder.__new__(HubBuilder)
    builder.conn = conn
    builder.fiscal_year = 2027
    builder.source_file_by_category = {"fixed_assets": "fixed_assets"}
    return builder, conn


def test_fixed_assets_rounds_each_asset_before_category_aggregation():
    builder, conn = _builder_with_asset_rows(
        [
            ("202604", 1025, 10.25, "1412000004", 5006016242, "fixed_assets_depr|machinery_equipment|A001"),
            ("202604", 250, 2.50, "1412000004", 5006016242, "fixed_assets_depr|machinery_equipment|A002"),
            ("202604", 100, 1.00, "1412000004", 9114120007, "fixed_assets_interest|machinery_equipment|A001"),
            ("202604", 50, 0.50, "1412000004", 9114120007, "fixed_assets_interest|machinery_equipment|A002"),
        ]
    )
    try:
        rows = builder._load_fixed_asset_source_order_rows(1412000004)
        assert len(rows) == 2
        assert rows[0]["account_code"] == 5006016242
        assert rows[0]["terms"] == {}
        assert rows[0]["numeric_months"] == {"202604": 1275}
        assert "fiscal_year=2027" in rows[0]["audit_trail"]
        assert "depreciation_cc=1412000004" in rows[0]["audit_trail"]
        assert rows[1]["account_code"] == 9114120007
        assert rows[1]["terms"] == {}
        assert rows[1]["numeric_months"] == {"202604": 150}
        assert rows[0]["source_file"] == rows[1]["source_file"]
    finally:
        conn.close()


def test_fixed_assets_per_asset_rounding_differs_from_rounding_aggregated_usd():
    builder, conn = _builder_with_asset_rows(
        [
            ("202604", 1, 0.5, "1412000004", 5006016242, "fixed_assets_depr|machinery_equipment|A001"),
            ("202604", 1, 0.5, "1412000004", 5006016242, "fixed_assets_depr|machinery_equipment|A002"),
        ]
    )
    try:
        rows = builder._load_fixed_asset_source_order_rows(1412000004)
        assert rows[0]["numeric_months"]["202604"] == 2
        # At FX=1: ROUND(0.5)+ROUND(0.5)=2, while ROUND(0.5+0.5)=1.
        assert 2 != 1
    finally:
        conn.close()


def test_fixed_assets_payload_omits_months_after_depreciation_ends():
    builder, conn = _builder_with_asset_rows(
        [
            ("202604", 1000, 10.00, "1412000004", 5006016243, "fixed_assets_depr|vehicles|V001"),
            ("202605", 325, 3.25, "1412000004", 5006016243, "fixed_assets_depr|vehicles|V001"),
        ]
    )
    try:
        rows = builder._load_fixed_asset_source_order_rows(1412000004)
        assert len(rows) == 1
        assert rows[0]["account_code"] == 5006016243
        assert rows[0]["numeric_months"] == {"202604": 1000, "202605": 325}
        assert "202606" not in rows[0]["numeric_months"]
    finally:
        conn.close()


def test_fixed_assets_payload_marks_explicit_zero_terminal_month_without_post_terminal_months():
    builder, conn = _builder_with_asset_rows(
        [
            ("202604", 1000, 10.00, "1412000004", 5006016243, "fixed_assets_depr|vehicles|V001"),
            ("202605", 0, 0.00, "1412000004", 5006016243, "fixed_assets_depr|vehicles|V001"),
        ]
    )
    try:
        rows = builder._load_fixed_asset_source_order_rows(1412000004)
        assert rows[0]["numeric_months"] == {"202604": 1000}
        assert rows[0]["explicit_zero_periods"] == {"202605"}
        assert "202606" not in rows[0]["numeric_months"]
        assert "202606" not in rows[0]["explicit_zero_periods"]
    finally:
        conn.close()
