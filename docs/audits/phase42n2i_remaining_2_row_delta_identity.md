# Phase 42N2I - Remaining 2-Row Delta Identity after Hybrid v2

## Classification

`PASS_PHASE_42N2I_REMAINING_DELTA_IS_FALSE_GAP`

## Method

Used the same 42N1P-B physical count method:

- Sheet: `内訳ﾘｽﾄ(4～3月)`
- Excluded layout rows: `1, 2, 3, 4, 5, 9, 17, 25`
- Counted a row when it has at least one of:
  - column B account/code,
  - column S description,
  - any F:Q month value/formula.

## Count result

| Workbook | Counted business rows |
|---|---:|
| Primary reference | 277 |
| Generated hybrid v2 | 275 |
| Delta | 2 |

## Exact identity of remaining 2-row delta

The remaining 2-row delta is exactly the two rows intentionally skipped from
reference-assisted append because invariant accounting already classified them as
false gaps / aliases already generated.

| Primary row | Account/code B | Description S | F:Q non-empty count | Generated candidate match | Classification |
|---:|---|---|---:|---|---|
| 159 | `5005066281` | 電気代 | 12 | generated row 204: electricity / Điện | `ALREADY_GENERATED_FALSE_GAP` |
| 160 | `5005066282` | 水道代 | 12 | generated row 205: water / Nước | `ALREADY_GENERATED_FALSE_GAP` |


## Non-tech conclusion

Có thể nói: **HYBRID v2 không còn thiếu business logic cho 2 dòng này**.

Không nên nói: “còn thiếu 2 dòng thật”.

Câu đúng là:

> Delta 2 còn lại là chênh lệch physical row/reference-row-shape do primary có
> hai dòng `電気代` và `水道代`, trong khi generated v2 đã sinh nghiệp vụ tương ứng
> ở Facility rows 204/205 dưới alias `electricity` và `water`. Hai dòng này không
> được append lại để tránh duplicate.

## Why not append them again

- `電気代` maps to generated Facility row 204 as `electricity`.
- `水道代` maps to generated Facility row 205 as `water`.
- Appending primary rows 159/160 again would double count the same business cost.
- Therefore the delta is a physical-count/reference-row-shape issue, not missing
  business logic.

## Appendix: exact-signature note

A strict exact-signature comparison lists many primary rows because generated v2
contains a mix of v1 source-derived rows and appended reference-assisted rows,
and some v1 rows use normalized/generated descriptions. The 2-row physical delta,
however, is explained by the skipped invariant false gaps above.

- Exact-signature primary rows not found in generated v2: 124
- This appendix count is not the physical row-count delta and must not be used to
  claim missing rows.

## Final answer

`PASS_PHASE_42N2I_REMAINING_DELTA_IS_FALSE_GAP`
