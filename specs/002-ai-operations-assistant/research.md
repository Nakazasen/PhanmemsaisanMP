# Research: C-AGENT Operations Guidance and Gemini Public Experiment

## Decision 1: Keep C-AGENT as the only operational provider

**Decision**: MP2027 calls only the company-provided C-AGENT endpoint for real Operations Assistant AI guidance.

**Rationale**: The owner explicitly rejected Nakazasen Router because it uses untrusted free sources, rejected BGE-M3 RAG because of machine cost, and needs end users to work without Antigravity IDE. C-AGENT can be governed by the company when its URL, authentication, retention, and data classification are supplied.

**Alternatives considered**:

- Nakazasen Router: rejected; not an approved security boundary.
- Gemini Web Direct: rejected for operational data; it uses an anonymous, unofficial public web path and does not provide a company-controlled data boundary.
- Local BGE-M3 RAG: rejected; too heavy for this application and not a generative operations guide.

## Decision 2: Send a selected-run technical packet to the company service

**Decision**: Build a separate `CagentGuidancePacket` from verified case facts plus bounded technical evidence from the selected run before the HTTP client can run.

**Rationale**: The owner confirmed that C-AGENT is a company-controlled service and IT owns its data-security controls. The model needs technical context to diagnose unknown failures. A separate packet still prevents accidentally mixing another run, arbitrary external file, credential, or process environment into that request.

**Alternatives considered**:

- Send all local directories or arbitrary user files: rejected; only the selected run workspace is in scope.
- Send credentials/environment/configuration: rejected; C-AGENT does not need them and they must not enter a packet.
- Use a generic prompt assembled in the UI: rejected; it couples disclosure policy to widgets and is difficult to test.

## Decision 3: Retain offline guidance; never silently fall back

**Decision**: A failed or unavailable C-AGENT request leaves the existing local knowledge guidance visible. No other provider is attempted.

**Rationale**: A user must know whether advice came from approved local guidance or company AI. Silent fallback can conceal a provider or data-boundary change.

**Alternatives considered**:

- Automatic Gemini retry: rejected; public-provider data sharing is a different decision.
- Blank dialog on C-AGENT failure: rejected; removes already useful evidence and safe steps.

## Decision 4: Make Gemini Web Direct a synthetic-only quality probe

**Decision**: The Gemini path uses only a built-in fictional incident, opt-in flag, and explicit experimental screen.

**Rationale**: It lets the owner observe an answer without allowing a selected run, a local path, user free-text, or financial content to leave the workstation.

**Alternatives considered**:

- Add Gemini as a selectable provider in the Operations Assistant: rejected; makes it too easy to send a real run to a public service.
- Use Gemini as a hidden fallback: rejected; violates disclosure and security boundaries.

## Decision 5: Treat provider details as a deployment gate

**Decision**: Implement a testable provider contract, but do not enable C-AGENT until the company provides endpoint, authentication, request/response schema, retention approval, and allowed data classification.

**Rationale**: The owner can obtain these at the company. Guessing the protocol or storing a token in UI/configuration would be unsafe.

**Alternatives considered**:

- Hard-code a temporary URL or token: rejected; secrets and endpoint ownership cannot enter Git.
- Permit arbitrary `http://` endpoint entry in the UI: rejected; it weakens transport and makes approval untraceable.
