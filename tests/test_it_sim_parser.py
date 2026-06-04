import unittest

import pandas as pd

from src.engine.hub_builder import HubBuilder
from src.parsers.it_sim import (
    _join_description,
    _metadata_parts,
    _parse_summary_sheet,
    classify_it_summary_variance,
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


if __name__ == "__main__":
    unittest.main()
