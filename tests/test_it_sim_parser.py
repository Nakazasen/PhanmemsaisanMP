import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import sqlite3

import pandas as pd

from src.db.schema import create_schema, init_sys_params
from src.engine.hub_builder import HubBuilder
from src.parsers.it_sim import (
    _join_description,
    _metadata_parts,
    _parse_summary_sheet,
    _summary_account_code_by_cc,
    classify_it_summary_variance,
    parse_it_simulation,
)


class TestItSimParserAuditMetadata(unittest.TestCase):
    def test_classify_it_summary_variance(self):
        self.assertEqual(classify_it_summary_variance(100, 100), ("OK", 0))
        self.assertEqual(classify_it_summary_variance(103, 100), ("WARN_ROUNDING", 3))
        self.assertEqual(classify_it_summary_variance(94, 100), ("ERROR_REVIEW", -6))

    def test_it_component_term_description_preserves_formula_parse_contract(self):
        description = _join_description(
            "it_sim",
            "component_term",
            "vpn",
            "qty=10",
            "unit_usd=3.19",
            metadata=_metadata_parts(
                source_file="システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls",
                source_sheet="VPN detail",
                source_filter="cc:1412000006",
            ),
        )

        self.assertTrue(description.startswith("it_sim|component_term|vpn|qty=10|unit_usd=3.19"))
        self.assertIn("source_file=", description)
        self.assertIn("source_sheet=VPN%20detail", description)
        self.assertIn("source_filter=cc:1412000006", description)

        builder = object.__new__(HubBuilder)
        component_key, quantity, unit_usd = builder._parse_it_component_term(description)
        self.assertEqual(component_key, "vpn")
        self.assertEqual(quantity, 10.0)
        self.assertEqual(unit_usd, 3.19)

    def test_it_sim_records_include_audit_metadata(self):
        df = pd.DataFrame(
            [
                [None, None],
                ["原価センター", "課金金額 VND"],
                ["1412000006", 120399176],
            ]
        )

        records = _parse_summary_sheet(
            df,
            ["202604"],
            source_file="system_sim.xls",
            source_sheet="部門別サマリー（USD）",
        )

        self.assertEqual(len(records), 1)
        description = records[0]["description"]
        self.assertTrue(description.startswith("it_sim|system_usage_total"))
        self.assertIn("source_file=system_sim.xls", description)
        self.assertIn("source_sheet=", description)
        self.assertIn("source_filter=cc:1412000006", description)

    def test_metadata_parts_can_include_audit_status_and_diff(self):
        metadata = _metadata_parts(audit_status="WARN_ROUNDING", audit_diff_vnd=3)
        self.assertIn("audit_status=WARN_ROUNDING", metadata)
        self.assertIn("audit_diff_vnd=3", metadata)

    def test_it_summary_records_include_audit_status_when_detail_vnd_available(self):
        from src.parsers.it_sim import _attach_summary_audit_metadata

        cases = [
            (100, "OK", 0),
            (103, "WARN_ROUNDING", 3),
            (94, "ERROR_REVIEW", -6),
        ]
        for detail_vnd, expected_status, expected_diff in cases:
            with self.subTest(expected_status=expected_status):
                records = [
                    {
                        "cc_code": 1412000006,
                        "period": "202604",
                        "amount_vnd": 100.0,
                        "amount_usd": 0.0,
                        "source": "it_sim",
                        "description": _join_description(
                            "it_sim",
                            "system_usage_total",
                            metadata=_metadata_parts(
                                source_file="system_sim.xls",
                                source_sheet="部門別サマリー（USD）",
                                source_filter="cc:1412000006",
                            ),
                        ),
                    }
                ]

                _attach_summary_audit_metadata(records, {1412000006: detail_vnd})

                description = records[0]["description"]
                self.assertTrue(description.startswith("it_sim|system_usage_total"))
                self.assertIn(f"audit_status={expected_status}", description)
                self.assertIn(f"audit_diff_vnd={expected_diff}", description)


class TestItSimAccountCodeMapping(unittest.TestCase):
    def test_summary_sheet_extracts_account_code_per_cc(self):
        df = pd.DataFrame(
            [
                [None, None, None],
                ["原価センター", "勘定科目", "課金金額 VND"],
                ["1412000006", "5005246282", 120399176],
            ]
        )

        records = _parse_summary_sheet(df, ["202604"])

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["cc_code"], "1412000006")
        self.assertEqual(records[0]["account_code"], 5005246282)
        self.assertEqual(_summary_account_code_by_cc(records), {1412000006: 5005246282})

    def test_parse_it_simulation_persists_account_code_from_parser_records(self):
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        create_schema(conn)
        init_sys_params(conn, exchange_rate=26273, fiscal_year=2027)

        with TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "システム課金金額(Simulation)_FY2027_Apr.2026 ~ June.2026.xls"
            source_path.write_bytes(b"placeholder")

            with patch(
                "src.parsers.it_sim.parse_it_sim_file",
                return_value=[
                    {
                        "period": "202604",
                        "amount_vnd": 120399176,
                        "amount_usd": 0.0,
                        "cc_code": 1412000006,
                        "account_code": 5005246282,
                        "description": "it_sim|system_usage_total",
                    }
                ],
            ):
                result = parse_it_simulation(conn, temp_dir)

        row = conn.execute(
            "SELECT cc_code, account_code, amount_vnd FROM fact_input_data WHERE source = 'it_sim'"
        ).fetchone()
        self.assertEqual(result["total"], 1)
        self.assertEqual(int(row["cc_code"]), 1412000006)
        self.assertEqual(int(row["account_code"]), 5005246282)
        self.assertEqual(float(row["amount_vnd"]), 120399176)


if __name__ == "__main__":
    unittest.main()
