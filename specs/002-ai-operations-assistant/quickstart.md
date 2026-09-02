# Quickstart Validation: C-AGENT Operations Guidance

## Prerequisites

- CI-safe temporary `RUN_HISTORY` fixtures; never a real workbook, report, or company log.
- Python environment used by the repository test suite.
- For manual C-AGENT acceptance only: company-approved endpoint, authentication method, data-policy reference, and a disposable/synthetic test case. Do not place the URL or token in this document, source, or Git.

## Scenario A: Offline local guidance remains useful

1. Open a known and an unknown terminal fixture with no C-AGENT configuration.
2. Verify existing local evidence-backed guidance remains visible.
3. Verify the C-AGENT action explains it is unavailable and creates no HTTP call.
4. Verify no selected-run file, catalog database, configuration, or output checksum changes.

## Scenario B: C-AGENT packet and response

1. Use a fake approved C-AGENT transport and a terminal fixture.
2. Review the generated packet: it contains only the selected run's verified facts, technical excerpts, paths/locators, and opaque `E*` evidence IDs.
3. Assert it excludes a credential, process environment value, evidence from another run, arbitrary external file, and missing/mismatched evidence; assert technical excerpt and packet totals respect their size limits.
4. Return a well-formed advisory answer and verify the UI labels it as company AI guidance, displays its limits, and preserves the local guidance beside it.
5. Return timeout, HTTP error, malformed JSON, and unknown evidence IDs; verify each leaves local guidance intact and calls no Gemini/other provider.

## Scenario C: Gemini public experiment isolation

1. With the flag absent, verify the experiment is unavailable.
2. With the flag present, submit the built-in fictional scenario through fake transport.
3. Verify the client cannot accept an `OperationalCase`, `run_id`, path, history root, free-text, or evidence payload.
4. Verify its result carries the experimental/public-data warning and no fallback path can reach it.

## CI-Safe Commands

```powershell
py -3 -m compileall -q src tests
py -3 -m pytest tests/test_i18n.py tests/ui/test_operations_assistant.py tests/services/test_operations_case_service.py tests/services/test_operations_knowledge.py tests/services/test_operations_ai_packet.py tests/services/test_operations_cagent_client.py tests/services/test_operations_gemini_experiment.py tests/test_run_history.py -q
git diff --check
```

## Manual Acceptance (not evidence for CI)

- C-AGENT: On the company network, use only a disposable synthetic incident. Verify approved URL/auth, packet preview, Vietnamese response quality, timeout behaviour, and that no real operational content was sent. Record only the pass/fail outcome and policy reference in the operations runbook.
- Gemini experiment: Run only the built-in fictional scenario after explicit enablement. Record provider availability and answer quality as an experiment; never claim it is production-ready or transfer a selected run.
- Existing T027 read-only human acceptance remains required and is not replaced by these checks.
