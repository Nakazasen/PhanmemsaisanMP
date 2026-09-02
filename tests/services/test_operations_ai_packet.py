"""Unit tests for C-AGENT models (T029) and packet builder (T030).

Covers:
- Models: CagentProviderPolicy, SafeEvidenceItem, CaseContext, CagentGuidancePacket, CagentGuidanceResult.
- Practical anti-secret guardrails (detecting API keys, tokens, passwords).
- Technical logs, paths, stack traces, and JSON allowed for valid selected-run evidence.
- build_cagent_guidance_packet:
  - Scoped strictly to selected run workspace.
  - Generates opaque random packet IDs.
  - Reads bounded excerpts from verified report/traceback files.
  - Rejects missing/mismatched evidence.
  - Rejects attempts to read files outside run workspace.
"""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import tempfile
import unittest

from src.services.operations_ai_packet import build_cagent_guidance_packet
from src.services.operations_ai_provider import (
    CAGENT_CONTRACT_VERSION,
    MAX_ANSWER_LENGTH,
    MAX_CONTEXT_FIELD_LENGTH,
    MAX_EVIDENCE_SUMMARY_LENGTH,
    MAX_EXCERPT_LENGTH,
    MAX_GUIDANCE_SUMMARY_LENGTH,
    MAX_LIMITATION_LENGTH,
    MAX_QUESTION_LENGTH,
    CagentGuidancePacket,
    CagentGuidanceResult,
    CagentProviderPolicy,
    CaseContext,
    SafeEvidenceItem,
)
from src.services.operations_case_service import (
    EvidenceReference,
    OperationalCase,
)
from src.services.operations_knowledge import (
    ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK,
    get_knowledge_entry,
)


class TestCagentProviderPolicy(unittest.TestCase):
    def test_default_policy_is_disabled(self) -> None:
        policy = CagentProviderPolicy()
        self.assertFalse(policy.enabled)
        self.assertEqual(policy.endpoint_url, "")
        self.assertEqual(policy.auth_mode, "none")
        self.assertEqual(policy.timeout_seconds, 60)
        self.assertEqual(policy.data_policy_id, "")
        self.assertEqual(policy.allowed_packet_version, CAGENT_CONTRACT_VERSION)

    def test_policy_is_immutable(self) -> None:
        policy = CagentProviderPolicy()
        with self.assertRaises(FrozenInstanceError):
            policy.enabled = True  # type: ignore[misc]

    def test_valid_enabled_policy(self) -> None:
        policy = CagentProviderPolicy(
            enabled=True,
            endpoint_url="https://cagent.internal.company.com/api/v1/guidance",
            data_policy_id="POL-2026-AI-OPS-01",
            auth_mode="bearer_env",
            timeout_seconds=30,
        )
        self.assertTrue(policy.enabled)
        self.assertEqual(policy.endpoint_url, "https://cagent.internal.company.com/api/v1/guidance")
        self.assertEqual(policy.data_policy_id, "POL-2026-AI-OPS-01")
        self.assertEqual(policy.auth_mode, "bearer_env")
        self.assertEqual(policy.timeout_seconds, 30)

    def test_rejects_unapproved_auth_mode(self) -> None:
        unapproved_modes = ["custom_token", "basic_auth", "api_key", "oauth2", "jwt", "header_secret"]
        for bad_mode in unapproved_modes:
            with self.subTest(bad_mode=bad_mode):
                with self.assertRaises(ValueError) as ctx:
                    CagentProviderPolicy(auth_mode=bad_mode)
                self.assertIn("auth_mode", str(ctx.exception))

    def test_enabled_policy_requires_data_policy_id(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            CagentProviderPolicy(
                enabled=True,
                endpoint_url="https://cagent.internal.company.com/api",
                data_policy_id="",
            )
        self.assertIn("data_policy_id", str(ctx.exception))

    def test_enabled_policy_requires_https_url(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            CagentProviderPolicy(
                enabled=True,
                endpoint_url="http://cagent.internal.company.com/api",
                data_policy_id="POL-01",
            )
        self.assertIn("HTTPS", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            CagentProviderPolicy(
                enabled=True,
                endpoint_url="",
                data_policy_id="POL-01",
            )
        self.assertIn("endpoint_url", str(ctx.exception))

    def test_rejects_credentials_query_fragment_in_endpoint_url(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            CagentProviderPolicy(
                enabled=True,
                endpoint_url="https://user:secret@cagent.example.test/api",
                data_policy_id="POL-01",
            )
        self.assertIn("userinfo", str(ctx.exception).lower())
        self.assertNotIn("user:secret", str(ctx.exception))
        self.assertNotIn("secret", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            CagentProviderPolicy(
                enabled=True,
                endpoint_url="https://cagent.example.test/api?token=secret",
                data_policy_id="POL-01",
            )
        self.assertIn("query string", str(ctx.exception).lower())
        self.assertNotIn("token=secret", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            CagentProviderPolicy(
                enabled=True,
                endpoint_url="https://cagent.example.test/api#token=secret",
                data_policy_id="POL-01",
            )
        self.assertIn("fragment", str(ctx.exception).lower())
        self.assertNotIn("token=secret", str(ctx.exception))


class TestSafeEvidenceItemAndSecretGuardrail(unittest.TestCase):
    def test_valid_safe_evidence_item_with_technical_details(self) -> None:
        # Technical paths, traceback excerpts, and JSON are allowed and encouraged for real diagnosis
        item = SafeEvidenceItem(
            evidence_id="E1",
            type="stage_evidence",
            summary="Stage publication failed: PermissionError [Errno 13] Permission denied: 'D:/Sandbox/MP2027/output.xlsx'",
            verification="verified",
            local_path="reports/pipeline_stage_evidence.json",
            technical_excerpt='{"stage": "publication", "status": "FAIL", "error": "file_locked"}',
        )
        self.assertEqual(item.evidence_id, "E1")
        self.assertEqual(item.type, "stage_evidence")
        self.assertEqual(item.local_path, "reports/pipeline_stage_evidence.json")
        self.assertIn("PermissionError", item.summary)
        self.assertIn("file_locked", item.technical_excerpt)

    def test_rejects_secret_leak_in_summary_or_excerpt(self) -> None:
        secrets = [
            "Error: api_key=sk-1234567890abcdef locked",
            "Authorization: Bearer my_secret_token_value",
            "password: super_secret_password_123",
            "secret=db_admin_secret",
            "-----BEGIN PRIVATE KEY-----",
        ]
        for bad_text in secrets:
            with self.subTest(bad_text=bad_text):
                with self.assertRaises(ValueError) as ctx:
                    SafeEvidenceItem(
                        evidence_id="E1",
                        type="stage_evidence",
                        summary=bad_text,
                    )
                self.assertIn("credential/secret/token", str(ctx.exception))


class TestBuildCagentGuidancePacket(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.history_root = Path(self.temp_dir.name)

        # Create synthetic run workspace: <history_root>/FY2027/RUN_TEST_001
        self.run_workspace = self.history_root / "FY2027" / "RUN_TEST_001"
        self.reports_dir = self.run_workspace / "reports"
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Write synthetic report and traceback files inside the run workspace
        self.stage_file = self.reports_dir / "pipeline_stage_evidence.json"
        self.stage_file.write_text(
            '{\n  "stage": "publication",\n  "status": "FAIL",\n  "error": "PermissionError: [Errno 13] file is locked by Excel"\n}',
            encoding="utf-8",
        )

        self.traceback_file = self.reports_dir / "failure_traceback.txt"
        self.traceback_file.write_text(
            "Traceback (most recent call last):\n  File 'pipeline.py', line 120, in export\nPermissionError: Excel locked file",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_build_packet_happy_path(self) -> None:
        evidence = (
            EvidenceReference(
                type="stage_evidence",
                local_path="reports/pipeline_stage_evidence.json",
                locator="stage=publication",
                summary="Giai đoạn xuất bản tệp gặp lỗi PermissionError.",
                verification="verified",
            ),
            EvidenceReference(
                type="failure_traceback",
                local_path="reports/failure_traceback.txt",
                locator="line=120",
                summary="Traceback chi tiết từ tiến trình xuất bản.",
                verification="verified",
            ),
            EvidenceReference(
                type="preflight_report",
                local_path="reports/missing.md",
                locator="section=preflight",
                summary="Báo cáo tiền trạm bị thiếu (sẽ bị bỏ qua).",
                verification="missing",
            ),
        )
        presentation = get_knowledge_entry(ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK).translations["vi"]
        case = OperationalCase(
            case_id="CASE-001",
            run_id="RUN_TEST_001",
            fiscal_year=2027,
            cost_center_scope="ALL",
            status="FAILED",
            stage="publication",
            classification="blocked_output_file_lock",
            confidence="confirmed",
            summary="Tệp đầu ra bị khóa.",
            evidence=evidence,
            presentation=presentation,
        )

        packet = build_cagent_guidance_packet(case, language="vi", history_root=self.history_root)

        self.assertEqual(packet.packet_version, CAGENT_CONTRACT_VERSION)
        self.assertTrue(packet.packet_id.startswith("pkt-"))
        self.assertNotEqual(packet.packet_id, case.run_id)
        self.assertEqual(packet.run_id, "RUN_TEST_001")
        self.assertEqual(packet.language, "vi")
        self.assertEqual(packet.case_context.status, "FAILED")
        self.assertEqual(packet.case_context.stage, "publication")

        # Missing evidence is excluded; only 2 verified items included
        self.assertEqual(len(packet.evidence_items), 2)
        self.assertEqual(packet.evidence_items[0].evidence_id, "E1")
        self.assertEqual(packet.evidence_items[1].evidence_id, "E2")

        # Excerpts were read from inside workspace
        self.assertIn("PermissionError", packet.evidence_items[0].technical_excerpt)
        self.assertIn("Traceback", packet.evidence_items[1].technical_excerpt)

        # to_dict serialization works
        d = packet.to_dict()
        self.assertEqual(d["contract_version"], CAGENT_CONTRACT_VERSION)
        self.assertEqual(d["run_id"], "RUN_TEST_001")
        self.assertEqual(len(d["evidence_items"]), 2)

    def test_rejects_files_outside_run_workspace(self) -> None:
        # Create a file outside the run workspace
        outside_file = self.history_root / "private_company_data.txt"
        outside_file.write_text("Confidential external content", encoding="utf-8")

        evidence = (
            EvidenceReference(
                type="stage_evidence",
                local_path="../../private_company_data.txt",
                locator="file",
                summary="Attempt to reference outside file",
                verification="verified",
            ),
        )
        presentation = get_knowledge_entry(ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK).translations["en"]
        case = OperationalCase(
            case_id="CASE-002",
            run_id="RUN_TEST_001",
            fiscal_year=2027,
            cost_center_scope="ALL",
            status="FAILED",
            stage="calc",
            classification="unknown",
            confidence="unknown",
            summary="Summary",
            evidence=evidence,
            presentation=presentation,
        )

        packet = build_cagent_guidance_packet(case, language="en", history_root=self.history_root)
        # Bằng chứng ngoài workspace phải bị loại trừ hoàn toàn (không gửi path, summary, hay excerpt)
        self.assertEqual(len(packet.evidence_items), 0)
        d = packet.to_dict()
        self.assertEqual(len(d["evidence_items"]), 0)
        self.assertNotIn("private_company_data.txt", str(d))

    def test_payload_cap_deterministically_drops_excess_evidence(self) -> None:
        # Create multiple large evidence files
        for i in range(1, 6):
            f = self.reports_dir / f"large_evidence_{i}.txt"
            f.write_text("X" * 1500, encoding="utf-8")

        evidence_list = [
            EvidenceReference(
                type="stage_evidence",
                local_path=f"reports/large_evidence_{i}.txt",
                locator=f"stage_{i}",
                summary=f"Summary {i}",
                verification="verified",
            )
            for i in range(1, 6)
        ]
        presentation = get_knowledge_entry(ERROR_CODE_BLOCKED_OUTPUT_FILE_LOCK).translations["vi"]
        case = OperationalCase(
            case_id="CASE-CAP-001",
            run_id="RUN_TEST_001",
            fiscal_year=2027,
            cost_center_scope="ALL",
            status="FAILED",
            stage="calc",
            classification="unknown",
            confidence="unknown",
            summary="Summary",
            evidence=tuple(evidence_list),
            presentation=presentation,
        )

        # Set a small cap (e.g. 3500 bytes)
        packet = build_cagent_guidance_packet(
            case,
            language="vi",
            history_root=self.history_root,
            max_payload_bytes=3500,
        )
        import json
        raw_bytes = json.dumps(packet.to_dict(), ensure_ascii=False).encode("utf-8")
        self.assertLessEqual(len(raw_bytes), 3500)
        self.assertTrue(len(packet.evidence_items) < 5)


class TestLoadCagentProviderPolicyFromEnv(unittest.TestCase):
    def test_load_disabled_when_empty_or_off(self) -> None:
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        self.assertFalse(load_cagent_provider_policy_from_env({}).enabled)
        self.assertFalse(load_cagent_provider_policy_from_env({"CAGENT_ENABLED": "0"}).enabled)
        self.assertFalse(load_cagent_provider_policy_from_env({"CAGENT_ENABLED": "false"}).enabled)

    def test_load_enabled_from_env_vars(self) -> None:
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        env = {
            "CAGENT_ENABLED": "1",
            "CAGENT_ENDPOINT_URL": "https://cagent.corp.example.com/api/v1",
            "CAGENT_DATA_POLICY_ID": "POL-2026-001",
            "CAGENT_AUTH_MODE": "bearer_env",
            "CAGENT_BEARER_TOKEN_ENV": "CUSTOM_CAGENT_TOKEN",
            "CAGENT_TIMEOUT_SECONDS": "30",
        }
        policy = load_cagent_provider_policy_from_env(env)
        self.assertTrue(policy.enabled)
        self.assertEqual(policy.endpoint_url, "https://cagent.corp.example.com/api/v1")
        self.assertEqual(policy.data_policy_id, "POL-2026-001")
        self.assertEqual(policy.auth_mode, "bearer_env")
        self.assertEqual(policy.bearer_token_env_var, "CUSTOM_CAGENT_TOKEN")
        self.assertEqual(policy.timeout_seconds, 30)

    def test_load_invalid_config_safely_falls_back_to_disabled(self) -> None:
        from src.services.operations_ai_provider import load_cagent_provider_policy_from_env

        # HTTP instead of HTTPS -> fails validation safely
        env = {
            "CAGENT_ENABLED": "true",
            "CAGENT_ENDPOINT_URL": "http://insecure.example.com",
            "CAGENT_DATA_POLICY_ID": "POL-01",
        }
        policy = load_cagent_provider_policy_from_env(env)
        self.assertFalse(policy.enabled)


if __name__ == "__main__":
    unittest.main()
