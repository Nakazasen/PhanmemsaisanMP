import json
import io

from src.services.runtime_health import print_health_report, run_health_checks


def test_health_check_reports_healthy_runtime(tmp_path, capsys):
    (tmp_path / "docs" / "MP2027").mkdir(parents=True)
    (tmp_path / "docs" / "MP2027" / "FORM.xlsx").write_bytes(b"test-form")

    report = run_health_checks(tmp_path)

    assert report["status"] == "ok"
    assert {item["name"] for item in report["checks"]} == {
        "release_metadata", "runtime_write", "seed_form", "sqlite"
    }
    assert print_health_report(tmp_path) == 0
    assert json.loads(capsys.readouterr().out)["status"] == "ok"


def test_health_check_is_safe_for_cp932_console(tmp_path, monkeypatch):
    from src.services import runtime_health

    stream = io.TextIOWrapper(io.BytesIO(), encoding="cp932")
    monkeypatch.setattr(runtime_health.sys, "stdout", stream)

    assert runtime_health.print_health_report(tmp_path) == 2
    stream.flush()
    payload = stream.buffer.getvalue().decode("ascii")
    assert "\\u" in payload


def test_health_check_fails_when_seed_form_is_missing(tmp_path):
    report = run_health_checks(tmp_path)

    assert report["status"] == "error"
    seed = next(item for item in report["checks"] if item["name"] == "seed_form")
    assert seed["status"] == "error"
