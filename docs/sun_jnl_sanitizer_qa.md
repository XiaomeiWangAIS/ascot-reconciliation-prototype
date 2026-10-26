# SUN JNL sanitizer QA: January–July 2026

Implemented `src/ascot/sanitize_sun_jnl.py` and processed all seven monthly Paid Invoices for SUN JNL workbooks using only `Page1_1` as the canonical source.

Outputs are seven monthly CSVs (`sun_jnl_2026-01.csv` through `sun_jnl_2026-07.csv`) and `sun_jnl_manifest.json` in `data/processed/sun_jnl/`.

## Row reconciliation and data-quality counts

Counts refer to allocation lines, not unique payments. Duplicate excess counts represent occurrences beyond the first identical source row; all occurrences are retained.

| Month | Input detail rows | Sanitized rows | AIC | AICRE | Negative amounts | Zero amounts | Missing Account | Missing Payment Type | Exact duplicate excess |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| January | 731 | 731 | 64 | 10 | 5 | 0 | 0 | 1 | 0 |
| February | 675 | 675 | 59 | 8 | 9 | 1 | 0 | 1 | 0 |
| March | 768 | 768 | 107 | 56 | 39 | 0 | 0 | 1 | 1 |
| April | 919 | 919 | 77 | 82 | 40 | 0 | 0 | 57 | 2 |
| May | 809 | 809 | 51 | 78 | 63 | 1 | 0 | 1 | 1 |
| June | 1,244 | 1,244 | 164 | 77 | 90 | 0 | 6 | 1 | 0 |
| July | 1,130 | 1,130 | 190 | 5 | 6 | 0 | 0 | 1 | 0 |

All **6,276 input allocation lines** reconcile to **6,276 sanitized rows**. No allocation lines were aggregated, deduplicated, or filtered to AIC.

## Company counts

| Month | AAIC | ACIC | AIC | AICRE | ANIC | ASC | ASI | ASIC | AUI | TAF | USC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| January | 21 | 33 | 64 | 10 | 54 | 1 | 13 | 23 | 9 | 0 | 503 |
| February | 24 | 35 | 59 | 8 | 49 | 11 | 7 | 39 | 12 | 0 | 431 |
| March | 18 | 20 | 107 | 56 | 43 | 16 | 46 | 29 | 9 | 0 | 424 |
| April | 18 | 24 | 77 | 82 | 48 | 13 | 35 | 37 | 8 | 4 | 573 |
| May | 11 | 21 | 51 | 78 | 43 | 18 | 55 | 46 | 9 | 1 | 476 |
| June | 64 | 84 | 164 | 77 | 110 | 76 | 89 | 35 | 14 | 3 | 528 |
| July | 64 | 74 | 190 | 5 | 102 | 34 | 2 | 42 | 26 | 0 | 591 |

## Schema handling and preservation

- Header detection handles January row 1, February–June row 4, and July row 5 without fixed column positions or manual edits.
- Header aliases normalize surrounding whitespace and the April–July bank-account `(Custom 9)` suffixes.
- February–March additional monetary columns and July VAT/Total Amount fields remain separate. Absent optional fields are nullable and listed in the manifest.
- Monetary values use `Decimal` in the reusable API and decimal text in CSV. Negative and zero values are preserved.
- Account codes and transaction references remain text. Numeric-looking Payment Type values remain uninterpreted.
- Provenance includes source file, sheet, row, accounting period, available report metadata, raw cell values, workbook SHA256, source headers, header mapping, and ignored-sheet names.
- Additional worksheets are not appended or merged. Unexpected formulas or Excel errors in the canonical source cause an explicit failure. Excel formatting is not used as accounting logic.

## Warnings and remaining source limitations

| Month | Reported warnings |
|---|---|
| January | Report-period metadata absent; accounting period derived from filename. One missing Payment Type. |
| February | One missing Payment Type. |
| March | Report period ends before accounting month-end, and report was generated before month-end; completeness unconfirmed. One missing Payment Type. One exact duplicate excess retained. |
| April | 57 missing Payment Types. Two exact duplicate excess rows retained. |
| May | One missing Payment Type. One exact duplicate excess retained. |
| June | Report generated before accounting month-end; completeness unconfirmed. Six missing Account values. One missing Payment Type. |
| July | One missing Payment Type. |

Missing source values and duplicate rows are retained and reported rather than silently corrected. No unresolved sanitizer failures were identified in this run. Source completeness limitations remain as documented above.

## Validation and rerun

The full test suite passed: **31 tests**, including **10 SUN sanitizer tests**. CSV round-trip checks verified row counts and parseable monetary values for all seven outputs.

```bash
.venv/bin/python -m src.ascot.sanitize_sun_jnl
```

No IMS-to-SUN matching was implemented. Existing production code and the intentionally deleted `src/ascot/inspect_current_month_control_variances.py` were left untouched.
