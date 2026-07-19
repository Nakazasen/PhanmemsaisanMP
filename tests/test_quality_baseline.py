from scripts import generate_quality_baseline as baseline


def test_quality_baseline_is_fast_static_and_machine_readable(monkeypatch):
    monkeypatch.setattr(baseline, "python_files", lambda: [baseline.ROOT / "src" / "config.py"])
    report = baseline.scan(collect_tests=False)
    assert report["schema_version"] == 1
    assert report["scope"]["private_runtime_data_scanned"] is False
    assert report["scope"]["business_pipeline_executed"] is False
    assert report["summary"]["python_files"] == 1
    assert report["modules"][0]["path"] == "src/config.py"


def test_quality_markdown_explains_remaining_release_gates():
    report = {"generated_at": "2026-01-01T00:00:00+00:00",
              "summary": {"python_files": 1, "python_lines": 1, "test_count": 2,
                          "findings_by_severity": {"critical": 0, "high": 0, "medium": 0, "low": 0}},
              "findings": []}
    text = baseline.markdown(report)
    assert "ĐÃ ĐẠT CỔNG KIỂM TRA TĨNH" in text
    assert "vẫn phải kiểm tra vận hành và nghiệm thu nghiệp vụ" in text
    assert "## Tóm tắt" in text
    assert "## Quyết định đóng gói" in text
    assert "STATIC GATE PASSED" not in text
    assert "Packaging decision" not in text
