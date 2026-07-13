# Phase 42N1P-B - Output Row Count vs Primary

## Files inspected

- Generated flag OFF: `dist/phase42n1p_b_facility_export_flag/flag_off/OUTPUT_FY2027/MP_CC_1412000040.xlsx`
- Generated flag ON: `dist/phase42n1p_b_facility_export_flag/flag_on/OUTPUT_FY2027/MP_CC_1412000040.xlsx`
- Primary reference: `reference_outputs/primary/16.KDTVN 電気製造技術課_MP FY2027_各予定(Ver01).xlsx`

## Commands run

```powershell
py scripts/run_e2e.py --target-cc 1412000040
py scripts/run_e2e.py --target-cc 1412000040 --facility-file-order-export --facility-file-order-start-row 200
```

Both commands were run from isolated working directories under:

```text
dist/phase42n1p_b_facility_export_flag/
```

## Count criteria

Sheet selected: `内訳ﾘｽﾄ(4～3月)`.

A row is counted as a business row when it is not one of excluded layout rows
`1, 2, 3, 4, 5, 9, 17, 25` and has at least one of:

- account/code in column `B`, or
- description in column `S`, or
- any value/formula in month columns `F:Q`.

This is a row-count audit only. It does not judge formula correctness.

## Counts

| Workbook | Business row count | Rows after 200 | Facility rows 200-205 | Row 206 blank |
|---|---:|---:|---:|---|
| Generated flag OFF | 133 | 1 | 2 | yes |
| Generated flag ON | 137 | 5 | 6 | yes |
| Primary reference | 277 | 96 | 4 | no |

## Delta and gap

- Delta ON vs OFF: `+4` business rows.
- Gap ON vs primary: `140` fewer business rows.
- Generated ON count equals primary count: `NO`.

## Facility row verification

Generated flag ON rows `200-205`:

| Row | item_id | description |
|---:|---|---|
| 200 | `building_depreciation` | Khấu hao nhà |
| 201 | `land_depreciation` | Khấu hao đất |
| 202 | `building_interest` | Lãi nhà |
| 203 | `land_interest` | Lãi đất |
| 204 | `electricity` | Điện |
| 205 | `water` | Nước |

- Rows `200-205`: OK for the six Facility file-order rows.
- Row `206`: blank in generated flag ON.

## Notes

The total row-count delta is `+4`, not `+6`, because the flag OFF workbook already
had business rows at `200-201`. The Facility export flag writes the six Facility
rows into `200-205`, replacing those two existing business rows and adding four
net counted rows.

The primary reference has additional business rows after row `200` through row
`307`. Therefore, enabling only the Facility file-order export does not yet make
the generated workbook row count match the primary reference.

## Conclusion

`STILL_FEWER_THAN_PRIMARY`

The Facility file-order export flag correctly writes the Facility block and blank
separator, but generated output remains significantly shorter than the primary
reference by this count method.
