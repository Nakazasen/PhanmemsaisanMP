import json
import sqlite3

from scripts.classify_fixed_assets_mismatches import archive_audit_history


def _matrix_row():
    return {
        "fy": "FY2026",
        "cc": "1412000098",
        "account": 9114120007,
        "period": "202504",
        "expected_per_asset_round_vnd": 11021800,
        "reference_actual_vnd": 10582552,
        "delta_reference_minus_expected_vnd": -439248,
        "reference_formula_kind": "MIXED_OR_LINKED_FORMULA",
        "source_asset_count_in_group": 12,
        "source_asset_evidence": [{"asset_no": "140000249", "scheduled_usd_for_period": 201.4}],
        "reference_evidence": [{"reference_file": "department.xlsx", "row": 75, "formula": "=ROUND(201.4*$B$2,0)"}],
        "evidence_classification": "UNEXPLAINED_FORMULA_OR_AGGREGATE_CONTRADICTION",
        "decision_status": "KHONG_THE_XAC_DINH_TU_DU_LIEU",
        "allowed_action": "REQUIRE_ROW_LEVEL_BUSINESS_EVIDENCE",
        "classification_reason": "Source and reference totals differ without a supplied explanation.",
    }


def test_fixed_asset_mismatch_history_preserves_snapshot_and_queryable_rows(tmp_path):
    current_csv = tmp_path / "fixed_assets_true_mismatch_decision_matrix_2026-07-16.csv"
    current_report = tmp_path / "fixed_assets_true_mismatch_decision_matrix_2026-07-16.md"
    current_csv.write_text("fy,cc\n2026,1412000098\n", encoding="utf-8")
    current_report.write_text("# matrix\n", encoding="utf-8")
    history_dir = tmp_path / "history"
    db_path = tmp_path / "mp2027.db"

    run_id, snapshot_dir = archive_audit_history(
        [_matrix_row()],
        audit_date="2026-07-16",
        matrix_csv_path=current_csv,
        matrix_report_path=current_report,
        history_dir=history_dir,
        history_db=db_path,
    )

    assert (snapshot_dir / current_csv.name).read_text(encoding="utf-8") == current_csv.read_text(encoding="utf-8")
    manifest = json.loads((snapshot_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == run_id
    assert manifest["classifications"] == {"UNEXPLAINED_FORMULA_OR_AGGREGATE_CONTRADICTION": 1}
    assert "UNEXPLAINED_FORMULA_OR_AGGREGATE_CONTRADICTION" in (history_dir / "run_index.csv").read_text(encoding="utf-8-sig")

    conn = sqlite3.connect(db_path)
    run = conn.execute("SELECT matrix_sha256, summary_json FROM audit_fixed_asset_mismatch_runs WHERE run_id=?", (run_id,)).fetchone()
    history = conn.execute(
        """
        SELECT fiscal_year, cc_code, account_code, period, delta_vnd,
               evidence_classification, source_evidence_json
        FROM audit_fixed_asset_mismatch_history WHERE run_id=?
        """,
        (run_id,),
    ).fetchone()
    conn.close()
    assert len(run[0]) == 64
    assert json.loads(run[1])["cells"] == 1
    assert history[:6] == (2026, "1412000098", 9114120007, "202504", -439248, "UNEXPLAINED_FORMULA_OR_AGGREGATE_CONTRADICTION")
    assert json.loads(history[6])[0]["asset_no"] == "140000249"
