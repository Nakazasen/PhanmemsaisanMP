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
        (source, period, amount_usd, cc_code, account_code, description)
        VALUES ('fixed_assets', ?, ?, ?, ?, ?)
        """,
        rows,
    )
    builder = HubBuilder.__new__(HubBuilder)
    builder.conn = conn
    builder.fiscal_year = 2027
    return builder, conn


def test_fixed_assets_aggregate_usd_by_category_before_vnd_rounding():
    builder, conn = _builder_with_asset_rows(
        [
            ("202604", 10.25, "1412000004", 5006016242, "fixed_assets_depr|machinery_equipment|A001"),
            ("202604", 2.50, "1412000004", 5006016242, "fixed_assets_depr|machinery_equipment|A002"),
            ("202604", 1.00, "1412000004", 9114120007, "fixed_assets_interest|machinery_equipment|A001"),
            ("202604", 0.50, "1412000004", 9114120007, "fixed_assets_interest|machinery_equipment|A002"),
        ]
    )
    try:
        rows = builder._load_fixed_asset_source_order_rows(1412000004)
        assert len(rows) == 2
        assert rows[0]["account_code"] == 5006016242
        assert rows[0]["terms"] == {"202604": ["ROUND(12.75*$B$2,0)"]}
        assert rows[1]["account_code"] == 9114120007
        assert rows[1]["terms"] == {"202604": ["ROUND(1.5*$B$2,0)"]}
        assert rows[0]["source_file"] == rows[1]["source_file"]
    finally:
        conn.close()


def test_fixed_assets_payload_omits_months_after_depreciation_ends():
    builder, conn = _builder_with_asset_rows(
        [
            ("202604", 10.00, "1412000004", 5006016243, "fixed_assets_depr|vehicles|V001"),
            ("202605", 3.25, "1412000004", 5006016243, "fixed_assets_depr|vehicles|V001"),
        ]
    )
    try:
        rows = builder._load_fixed_asset_source_order_rows(1412000004)
        assert len(rows) == 1
        assert rows[0]["account_code"] == 5006016243
        assert rows[0]["terms"] == {
            "202604": ["ROUND(10*$B$2,0)"],
            "202605": ["ROUND(3.25*$B$2,0)"],
        }
        assert "202606" not in rows[0]["terms"]
    finally:
        conn.close()
