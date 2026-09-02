"""Regression tests verifying zero-write safety invariants for Operations Assistant & C-AGENT (T037).

Proves that:
1. assemble_operational_case performs 0 write operations.
2. build_cagent_guidance_packet performs 0 write operations.
3. request_cagent_guidance performs 0 write operations.
4. OperationsAssistantDialog rendering and user interactions perform 0 write operations.
5. All file hashes in the workspace and history root remain 100% identical.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from src.services.operations_ai_packet import build_cagent_guidance_packet
from src.services.operations_ai_provider import CagentProviderPolicy
from src.services.operations_cagent_client import request_cagent_guidance
from src.services.operations_case_service import assemble_operational_case
from src.ui.operations_assistant import OperationsAssistantDialog


def _hash_directory(root: Path) -> dict[str, str]:
    """Tính toán bảng băm SHA-256 cho toàn bộ các tệp trong thư mục."""
    hashes: dict[str, str] = {}
    for p in sorted(root.rglob("*")):
        if p.is_file():
            rel = str(p.relative_to(root))
            hashes[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
    return hashes


class TestOperationsNoWriteInvariants(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.history_root = Path(self.temp_dir.name)

        self.run_workspace = self.history_root / "FY2027" / "RUN_SAFE_001"
        self.reports_dir = self.run_workspace / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Create synthetic catalog and run files
        catalog_path = self.history_root / "catalog.json"
        catalog_path.write_text(
            json.dumps([
                {
                    "run_id": "RUN_SAFE_001",
                    "fiscal_year": "2027",
                    "selected_cost_center": "ALL",
                    "status": "FAILED",
                    "failure_stage": "publication",
                    "started_at": "2026-09-01T10:00:00",
                    "finished_at": "2026-09-01T10:05:00",
                    "database_path": str(self.run_workspace / "run.db"),
                }
            ]),
            encoding="utf-8",
        )

        db_path = self.history_root / "run_history.db"
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS planning_runs (
                run_id TEXT PRIMARY KEY,
                fiscal_year INTEGER NOT NULL,
                status TEXT NOT NULL,
                started_at TEXT,
                finished_at TEXT,
                selected_cost_center TEXT,
                source_paths_json TEXT NOT NULL DEFAULT '{}',
                source_checksums_json TEXT NOT NULL DEFAULT '{}',
                template_checksum TEXT,
                exchange_rate REAL NOT NULL,
                exchange_rate_source TEXT,
                output_path TEXT,
                database_path TEXT,
                error_summary TEXT,
                application_version TEXT,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            INSERT INTO planning_runs (
                run_id, fiscal_year, status, started_at, finished_at,
                selected_cost_center, database_path, error_summary, exchange_rate, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "RUN_SAFE_001", 2027, "FAILED", "2026-09-01T10:00:00", "2026-09-01T10:05:00",
                "ALL", str(self.run_workspace / "run.db"), "file locked", 25000.0, "2026-09-01T10:00:00"
            )
        )
        conn.commit()
        conn.close()

        stage_file = self.reports_dir / "pipeline_stage_evidence.json"
        stage_file.write_text(
            json.dumps({"stage": "publication", "status": "FAIL", "error": "file locked"}),
            encoding="utf-8",
        )

        db_file = self.run_workspace / "run.db"
        db_file.write_bytes(b"SQLITE_MOCK_HEADER_DATA_12345678")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()
        OperationsAssistantDialog.clear_registry()

    def test_all_operations_assistant_flows_are_100_percent_read_only(self) -> None:
        # Snapshot initial directory state and file hashes
        initial_hashes = _hash_directory(self.history_root)
        self.assertTrue(len(initial_hashes) >= 3)

        # Step 1: assemble_operational_case
        case = assemble_operational_case(self.history_root, "RUN_SAFE_001", "vi")
        self.assertEqual(case.run_id, "RUN_SAFE_001")
        self.assertEqual(_hash_directory(self.history_root), initial_hashes)

        # Step 2: build_cagent_guidance_packet
        packet = build_cagent_guidance_packet(case, "vi", history_root=self.history_root)
        self.assertEqual(packet.run_id, "RUN_SAFE_001")
        self.assertEqual(_hash_directory(self.history_root), initial_hashes)

        # Step 3: request_cagent_guidance with fake transport
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api/v1/guidance",
            data_policy_id="POL-01",
        )

        def fake_transport(url: str, headers: dict, body: bytes, timeout: float):
            return 200, {}, json.dumps({"answer": "Advisory text", "evidence_ids": ["E1"]}).encode("utf-8")

        result = request_cagent_guidance(
            case=case,
            policy=policy,
            language="vi",
            history_root=self.history_root,
            transport=fake_transport,
        )
        self.assertEqual(result.status, "ready")
        self.assertEqual(_hash_directory(self.history_root), initial_hashes)

        # Step 4: OperationsAssistantDialog execution
        from tests.ui.test_operations_assistant import FakeWidgetFactory
        factory = FakeWidgetFactory()

        dialog = OperationsAssistantDialog(
            parent=None,
            case=case,
            language="vi",
            policy=policy,
            history_root=self.history_root,
            cagent_transport=fake_transport,
            widget_factory=factory,
        )
        dialog.ask_cagent()
        dialog._async_request_cagent()
        dialog.close()

        # Final verification: Hashes must be 100% identical
        final_hashes = _hash_directory(self.history_root)
        self.assertEqual(final_hashes, initial_hashes)


if __name__ == "__main__":
    unittest.main()
