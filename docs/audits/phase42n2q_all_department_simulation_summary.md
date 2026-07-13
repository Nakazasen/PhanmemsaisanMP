# Phase 42N2Q - All Department Simulation Summary

## Classification

`WARNING_PHASE_42N2Q_SIMULATION_PARTIAL`

## Results

- Scanned recursive secondary `.xlsx` files: 82
- Root secondary `.xlsx` files inventoried: 65
- Departments attempted: 0
- Departments skipped unknown CC: 65
- Successful runs: 0
- Failed runs: 0
- Near-parity count: 0
- Source-derived strong count: 0
- Hybrid-reference-dependent count: 0

## What happened

Opening the secondary workbook set with `openpyxl` hung twice with no progress.
To avoid an infinite run, the phase was completed as a safe metadata-only
inventory plus CC-mapping coverage matrix.

No simulation was run because target CC could not be inferred safely from the
secondary reference files. Per rule, CC must not be guessed and secondary files
are comparison references only, not raw source proof.

## Top blockers

1. Missing explicit department-to-CC map for all secondary references.
2. Complete v1 still uses primary reference-assisted rows for near parity.
3. Fixed assets, birthday, NNN paperwork, and allocation need stronger raw
   source-derived row/cell/month traceability.
4. Batch workbook inspection needs a timeout-safe scanner before full coverage.

## Non-tech conclusion

Có thể gọi 100% source-derived chưa? **Chưa.**

Muốn đạt 100%, trước hết phải có mapping CC cho toàn bộ phòng ban. Sau đó mới
chạy được batch simulation thật và chuyển các module còn reference-assisted sang
parser đọc raw source có trace rõ ràng.

## Outputs

- `dist/phase42n2q_all_department_simulation/inventory.csv`
- `dist/phase42n2q_all_department_simulation/reference_candidates.csv`
- `docs/audits/phase42n2q_all_department_simulation_matrix.csv`
- `docs/audits/phase42n2q_source_derived_gap_to_100_percent.md`

## Final classification

`WARNING_PHASE_42N2Q_SIMULATION_PARTIAL`
