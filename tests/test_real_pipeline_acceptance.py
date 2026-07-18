import json
from pathlib import Path
import sqlite3
import subprocess
import sys

import pytest

from scripts.run_real_pipeline_acceptance import _snapshot_sqlite


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TARGET_CC = "1412000005"
FISCAL_YEAR = 2027
RECOVERY_RUN_ID = "e99210faa8664ebb8bf08f99b2b6e0a7"


def test_immutable_sqlite_snapshot_does_not_touch_source_shm(tmp_path):
    source = tmp_path / "source.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE evidence(value TEXT)")
    connection.execute("INSERT INTO evidence(value) VALUES('stable')")
    connection.commit()
    connection.close()
    shm = Path(f"{source}-shm")
    shm.write_bytes(b"existing-sidecar-metadata")
    before = shm.stat().st_mtime_ns

    destination = tmp_path / "snapshot.db"
    _snapshot_sqlite(source, destination)

    assert shm.stat().st_mtime_ns == before
    assert shm.read_bytes() == b"existing-sidecar-metadata"
    snapshot = sqlite3.connect(destination)
    try:
        assert snapshot.execute("SELECT value FROM evidence").fetchone()[0] == "stable"
    finally:
        snapshot.close()


def test_immutable_sqlite_snapshot_rejects_uncheckpointed_wal(tmp_path):
    source = tmp_path / "source.db"
    connection = sqlite3.connect(source)
    connection.execute("CREATE TABLE evidence(value TEXT)")
    connection.commit()
    connection.close()
    Path(f"{source}-wal").write_bytes(b"uncheckpointed")

    with pytest.raises(RuntimeError, match="uncheckpointed WAL"):
        _snapshot_sqlite(source, tmp_path / "snapshot.db")


@pytest.mark.real_pipeline_acceptance
@pytest.mark.requires_raw_excel
def test_real_cc005_pipeline_runs_end_to_end_in_isolated_workspace(tmp_path):
    """Release gate: execute source-to-publication CC005 through the real CLI."""
    required = [
        PROJECT_ROOT / "docs" / "MP2027" / "FORM.xlsx",
        PROJECT_ROOT / "docs" / "MP2027",
        PROJECT_ROOT / "raw" / "10.07.2026",
        PROJECT_ROOT / "raw" / "Cải tiến nhập dữ liệu chung vào file MPnew 10.07.2026.xlsx",
        PROJECT_ROOT / "raw" / "FY2027" / "manual_inputs.db",
        PROJECT_ROOT / "mp2027.db",
        PROJECT_ROOT / "OUTPUT_FY2027",
        PROJECT_ROOT / "RUN_HISTORY" / "FY2027" / RECOVERY_RUN_ID / "run.db",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        pytest.skip("Private/local acceptance inputs are absent: " + ", ".join(missing))

    workspace_root = tmp_path / "real_pipeline_acceptance"
    completed = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "run_real_pipeline_acceptance.py"),
            "--fy", str(FISCAL_YEAR),
            "--target-cc", TARGET_CC,
            "--workspace-root", str(workspace_root),
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        timeout=1800,
    )

    evidence_files = list(workspace_root.glob("*/acceptance_evidence.json"))
    assert len(evidence_files) == 1, (
        f"stdout:\n{completed.stdout}\n\nstderr:\n{completed.stderr}"
    )
    evidence = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert completed.returncode == 0, json.dumps(evidence, ensure_ascii=False, indent=2)
    assert evidence["status"] == "PASS", json.dumps(evidence, ensure_ascii=False, indent=2)
    assert evidence["production_unchanged"] is True
    assert evidence["subprocess"]["return_code"] == 0
    assert evidence["subprocess"]["hidden_traceback"] is False
    assert evidence["validator_status"] == "PASS"
    assert evidence["run_id"]
