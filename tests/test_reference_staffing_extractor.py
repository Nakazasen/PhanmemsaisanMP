import tempfile
import unittest
from pathlib import Path
from openpyxl import Workbook

from src.parsers.extracted_headcount_time_plan import parse_extracted_headcount_time_plan
from src.services.reference_staffing_extractor import evaluate_cell, extract_reference_staffing_sources

ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "reference_outputs" / "secondary" / "FY2027"
OFFICIAL = ROOT / "raw" / "10.07.2026"


class FormulaEvaluatorTests(unittest.TestCase):
    def test_arithmetic_and_cell_references(self):
        wb=Workbook(); ws=wb.active; ws["A1"]=4; ws["B1"]="=A1*8.5-(2+3)"
        self.assertEqual(evaluate_cell(ws,"B1"),29)

    def test_rejects_excel_functions(self):
        wb=Workbook(); ws=wb.active; ws["A1"]="=SUM(B1:B2)"
        with self.assertRaises(ValueError): evaluate_cell(ws,"A1")


class ReferenceExtractionTests(unittest.TestCase):
    def test_real_65_file_extraction_is_complete_and_traceable(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=extract_reference_staffing_sources(REFERENCE,tmp,2027,OFFICIAL)
            self.assertEqual(result["files"],65)
            self.assertEqual(len(result["errors"]),0,[x.errors for x in result["errors"]])
            self.assertEqual(result["ready"],3)
            self.assertEqual(result["split_required"],62)
            self.assertEqual(len({x.cc_code for x in result["results"]}),65)
            self.assertTrue(Path(result["manifest_path"]).exists())
            cc14=next(x for x in result["results"] if x.cc_code=="1412000006")
            self.assertEqual(cc14.status,"READY")
            self.assertEqual(cc14.rows[3]["headcount_staff"],27)
            self.assertEqual(cc14.rows[3]["overtime_hours_local"],385)
            parsed=parse_extracted_headcount_time_plan(cc14.output_path,2027)
            self.assertEqual(parsed.status,"valid",parsed.errors)
            self.assertEqual(len(parsed.rows),12)

if __name__ == "__main__": unittest.main()
