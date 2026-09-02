# Internal Contract: Gemini Web Direct Public Experiment v1

> **Contract Identifier**: `contracts/gemini-public-experiment-v1.md`
> **Safety Boundary**: Opt-in experiment with built-in fictional data only. Not an MP2027 operational provider.

## Enablement and Input

- Disabled unless `MP2027_ENABLE_GEMINI_WEB_EXPERIMENT=1` is present before the application starts.
- The only input is an allow-listed scenario ID resolved to a built-in fictional incident. No text box, selected run, `OperationalCase`, history root, evidence record, file path, clipboard data, or attached data is accepted.
- The screen must state that the public provider receives the fictional prompt and that model identity/availability may be unverified.

## Isolation Rules

- The experiment client imports no run-history, case-assembly, workbook, or C-AGENT credential module.
- No C-AGENT failure/retry path may call the experiment client.
- It does not create, edit, or save a run, case, source file, workbook, database, configuration, or output.
- Automated tests use fake transport only. A live call is a separate manual smoke check with no business content.

## Result

The result is shown with a fixed label: **Experimental public Gemini result — not operational guidance**. The result is temporary UI state and may not be copied into a case, knowledge catalog, or run history.
