# Internal Contract: C-AGENT Guidance v1

> **Contract Identifier**: `contracts/cagent-guidance-v1.md`
> **Safety Boundary**: Company-approved internal request for one selected run; read-only; no provider fallback.

## Preconditions

The client must refuse to call until all conditions are true:

1. `CagentProviderPolicy.enabled` is true and names a non-empty company data-policy reference.
2. The endpoint is a valid HTTPS URL, unless a documented company exception is passed by a deployment-owned configuration adapter.
3. Required authentication is available at runtime without appearing in source, GUI state, logs, or persistent application configuration.
4. The active case is terminal and a `CagentGuidancePacket` passes the v1 minimisation validator.

## Request

The concrete C-AGENT/AgentFlow schema is a company handoff item. MP2027 owns this provider-neutral logical body:

```json
{
  "contract_version": "cagent-guidance/v1",
  "packet_id": "ephemeral-random-id",
  "language": "vi",
  "question": "...fixed safe question...",
  "case_context": {
    "fiscal_year": "FY2027",
    "cost_center_scope": "ALL",
    "status": "FAILED",
    "stage": "publication",
    "classification": "blocked_output_file_lock",
    "confidence": "confirmed"
  },
  "local_guidance_summary": "...",
  "evidence_items": [
    {"evidence_id": "E1", "type": "stage_evidence", "summary": "...", "verification": "verified"}
  ]
}
```

The request may include bounded verified technical excerpts and paths from the selected run. It may not include a credential, environment value, another run's evidence, arbitrary external file, or payload from a missing/mismatched evidence item.

## Expected Logical Response

```json
{
  "answer": "Plain-language advisory answer in the requested language.",
  "evidence_ids": ["E1"],
  "limitations": "Advice only; user must perform checks manually."
}
```

The implementation may adapt C-AGENT's actual field names only inside `operations_cagent_client.py`. It must reject a missing/empty answer, unknown evidence IDs, oversized response, or protocol error without exposing endpoint or credential details to the user.

## Failure Contract

Timeout, non-2xx response, bad JSON, auth failure, or unsafe response returns a localised non-secret status. The caller continues displaying local deterministic guidance. It must not retry to Gemini or another provider.
