# Phase 42N2E - Secondary Skeleton Patterns for Account 5005026371

## Classification

`PASS_PHASE_42N2E_SECONDARY_SKELETON_PATTERN_READY`

## Scope

Analyzed secondary FY2027 workbooks as reference/skeleton inputs for account
`5005026371`. No output code was changed. No full pytest was run. Secondary files
remain untracked/read-only.

## Summary

| Metric | Count |
|---|---:|
| Primary `5005026371` rows | 75 |
| Secondary files containing `5005026371` rows | 57 |
| Secondary `5005026371` rows extracted | 724 |
| Reusable skeleton pattern groups | 1 |
| Reference-assisted fill candidate rows | 48 |

## Pattern classifications

| classification | Count |
|---|---:|
| `REPEATED_SECONDARY_SKELETON_PATTERN` | 137 |
| `UNIQUE_OR_UNUSABLE` | 536 |
| `REFERENCE_ASSISTED_FILL_CANDIDATE` | 48 |
| `FORMULA_ONLY_REFERENCE_PATTERN` | 3 |

## Interpretation

The secondary pool contains repeated `5005026371` structures across departments.
These are useful for row skeletons, formula shapes, ordering, and identifying
which descriptions recur. They are **not** source-derived proof by themselves.
In short: secondary skeleton rows are not source-derived.

A `reference_assisted_skeleton_export` can safely reduce the physical row-count
gap only if every generated row carries provenance such as
`reference_assisted_secondary_skeleton`, and reports clearly distinguish it from
source-derived rows.

## Source-derived proof status

Source-derived proof is still missing for the extracted secondary rows because
secondary workbooks are generated output references/skeletons, not proven raw
amount sources. The next code phase must not label these rows as source-derived.

## Recommended next code phase

Because there are at least 10 reference-assisted candidates, the recommended next
phase is to implement an explicit default-OFF flag such as
`--reference-assisted-skeleton-export` or a narrower
`--fixed-assets-reference-skeleton-export`. It should:

1. Generate only rows whose description/order appears in primary and repeated
   secondary skeletons.
2. Preserve formulas/blank/value pattern from the primary/reference skeleton.
3. Add provenance metadata/reporting that says `reference-assisted`, not
   `source-derived`.
4. Keep default export unchanged.

## Primary 5005026371 row sample

| row | description | F sample | Q sample |
|---:|---|---|---|
| 56 |  | `` | `` |
| 57 | Vendor用Micro SD(8B) 単価:VND | `` | `` |
| 58 | 湿度計 単価:$28, LCRmeter Probe(SMDA-22) | `` | `` |
| 59 | ノートPCのRAM　16gb | `=6*2150000` | `` |
| 60 | Master用DVD $22(20pack) | `` | `` |
| 61 | USB 10本(単価$7.5) | `` | `` |
| 62 | ROMライター実装ベンダ支給用(MINATO) | `` | `` |
| 63 | ROMライター実装ベンダ支給用(FSG) | `` | `` |
| 64 | Test Board 10枚((7x9cm)単価24,000VND／(9x15cm)単価37,000VND) | `` | `` |
| 65 | Arduino Nano V3.0 Atmega328P - USB CH340 | `` | `` |
| 66 | Resistor 5本(単価30,000) | `` | `` |
| 67 | 画像検査装置開発用PC | `` | `` |
| 68 | 画像検査装置用　OFFICE | `` | `` |
| 69 | スタンレー 240V/40W グルーガン/Sung ban keo 240V/40W Stanley | `` | `` |
| 70 | WebCam　C920/WebCam　C615 | `` | `` |
| 71 | Cable usb to lan 2.0 20254 Ugreen | `` | `` |
| 72 | 2NM PANEL KEY FT改造費\16,000　⇒　科目変更 | `` | `` |
| 73 | テスター購入費 | `` | `` |
| 74 | 実験場の棚　単価6,800,000ＶＮＤｘ2 | `` | `` |
| 75 | GARNET選別用の温度プローブ
Temperature Sensor SE10605 | `` | `` |

## Output CSV

`docs/audits/phase42n2e_5005026371_secondary_skeleton_patterns.csv`

## Conclusion

`PASS_PHASE_42N2E_SECONDARY_SKELETON_PATTERN_READY`
