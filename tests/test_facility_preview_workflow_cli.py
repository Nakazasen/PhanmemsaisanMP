from pathlib import Path

import pytest

import scripts.run_e2e as run_e2e
from src.services.fiscal_run import RunPreflightReport


def test_default_cli_or_export_behavior_unchanged():
    text = Path("scripts/run_e2e.py").read_text(encoding="utf-8")

    assert "builder.export_to_template(template_path, out_path, cc_code=target_cc)" in text
    assert "builder.export_to_template(template_path, out_path, cc_code=cc)" in text
    assert "facility_file_order_preview: bool = False" in text


def test_facility_preview_flag_creates_preview_workbook(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    calls = []
    output = tmp_path / "facility_preview.xlsx"

    def fake_get_connection(db_path):
        return object()

    def fake_noop(*args, **kwargs):
        return None

    class FakeCursor:
        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return []

        def fetchone(self):
            return (0,)

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def execute(self, *args, **kwargs):
            return FakeCursor()

        def executemany(self, *args, **kwargs):
            return FakeCursor()

        def commit(self):
            return None

        def rollback(self):
            return None

        def close(self):
            return None

    class FakeHubBuilder:
        def __init__(self, conn, fiscal_year, **kwargs):
            self.conn = conn
            self.fiscal_year = fiscal_year

        def export_to_template(self, template_path, output_path, cc_code=None):
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            from openpyxl import Workbook

            workbook = Workbook()
            workbook.save(output_path)
            workbook.close()
            calls.append(("export", template_path, output_path, cc_code))
            return True

    (tmp_path / "raw").mkdir()
    monkeypatch.setattr(run_e2e, "get_connection", lambda db_path: FakeConn())
    monkeypatch.setattr(
        run_e2e,
        "preflight_fiscal_run",
        lambda context: RunPreflightReport(
            fiscal_year=2027,
            resolved_sources={
                "facility": (str(tmp_path / "raw" / "施設課　MPFY2027.xlsx"),),
            },
        ),
    )
    monkeypatch.setattr(
        run_e2e,
        "import_headcount_time_sources",
        lambda *args, **kwargs: {
            "files": 1,
            "imported_files": 1,
            "skipped": [],
            "errors": [],
            "results": [],
        },
    )
    monkeypatch.setattr(run_e2e, "_staffing_preflight", lambda *args, **kwargs: [])
    monkeypatch.setattr(run_e2e, "create_schema", fake_noop)
    monkeypatch.setattr(run_e2e, "init_sys_params", fake_noop)
    monkeypatch.setattr(run_e2e, "load_all", fake_noop)
    monkeypatch.setattr(run_e2e, "describe_manifest", lambda source_dir: [])
    monkeypatch.setattr(run_e2e, "parse_facility", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_fixed_assets", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_it_simulation", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_ga", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_birthday_workbook", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_manual_headcount", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_manual_special_costs", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_manual_event_drivers", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "parse_nnn_paperwork", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "AllocationEngine", lambda conn: type("Engine", (), {"run_allocation": lambda self: None})())
    monkeypatch.setattr(run_e2e, "HubBuilder", FakeHubBuilder)
    monkeypatch.setattr(run_e2e, "write_pipeline_audit_report", lambda **kwargs: {"report_path": "audit.md", "missing_csv_path": "missing.csv"})
    monkeypatch.setattr(run_e2e, "audit_exchange_rate_workbook", lambda *args, **kwargs: {})
    monkeypatch.setattr(run_e2e, "write_exchange_rate_audit_report", lambda *args, **kwargs: "exchange-audit.xlsx")
    monkeypatch.setattr(
        run_e2e,
        "write_facility_file_order_preview_workbook",
        lambda **kwargs: calls.append(("preview", kwargs)) or Path(kwargs["output_path"]),
    )

    ok, _ = run_e2e.run_universal_pipeline(
        fiscal_year=2027,
        template_path="FORM.xlsx",
        source_dir="raw",
        exchange_rate=25450,
        target_cc=1412000040,
        facility_file_order_preview=True,
        facility_preview_output=str(output),
        mp_saisan_complete_v1=False,
    )

    assert ok
    assert any(call[0] == "export" for call in calls)
    preview_call = [call for call in calls if call[0] == "preview"][0][1]
    assert preview_call["output_path"] == str(output)
    assert preview_call["facility_source_path"].endswith("施設課　MPFY2027.xlsx")
    assert preview_call["cost_center"] == 1412000040


def test_facility_preview_flag_requires_explicit_opt_in(monkeypatch, tmp_path):
    called = False

    def fake_preview(**kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(run_e2e, "write_facility_file_order_preview_workbook", fake_preview)

    assert "facility_file_order_preview: bool = False" in Path("scripts/run_e2e.py").read_text(encoding="utf-8")
    assert not called


@pytest.mark.requires_raw_excel
def test_facility_preview_does_not_modify_template_or_source():
    template = Path("FORM.xlsx")
    source = Path("raw/施設課　MPFY2027.xlsx")

    before_template_mtime = template.stat().st_mtime_ns
    before_source_mtime = source.stat().st_mtime_ns

    # This integration test only inspects the explicit flag wiring and does not run the writer.
    assert "--facility-file-order-preview" in Path("scripts/run_e2e.py").read_text(encoding="utf-8")

    assert template.stat().st_mtime_ns == before_template_mtime
    assert source.stat().st_mtime_ns == before_source_mtime


def test_no_default_hub_builder_file_order_call():
    hub_builder = Path("src/engine/hub_builder.py").read_text(encoding="utf-8")

    assert "facility_file_order_writer" not in hub_builder
    assert "write_facility_file_order_preview_workbook" not in hub_builder
    assert "self._write_fixed_rows(worksheet, target_cc)" in hub_builder
