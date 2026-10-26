# July 2026 holdout validation — stopped at compatibility inspection

## Outcome

**NOT RUN: the newly received workbook is not safely compatible with the locked IMS sanitizer as-is.** Per the requested stop condition, no isolated canonical population or SUN verification run was produced. No rules, thresholds, sanitizer logic, or historical outputs were changed. The July SUN canonical file was not used for a new verification run.

## Received input

- Actual uploaded file: `data/validation/new_july_2026/AIC_A JE#3784 WF Disb Cash Expense Activity July 2026.xlsx`.
- This differs from the proposed `data/validation/july_2026/` location and `(1).xlsx` suffix. The uploaded file was inspected in place and not moved or renamed.
- Workbook SHA256: `0fab7955b52fe7cadba22eba6c5cf00066432f1d2d30074b91ce17627e967a7f`.
- Worksheet: `AIC IMS`. Other workbook sheets were not combined into the IMS population.

## Actual worksheet structure

- Header row: **1**; 13 columns A:M, identical to the prior July IMS header.
- Exact headers: `['TransactionDate', 'CheckOrRef', 'Method', 'PaymentType', 'Description', 'Debit', 'Credit', 'Date Cleared', 'Account', 'Cost Center', 'Description', ' Amount', 'Backup']`.
- Worksheet dimensions: 476 rows × 13 columns; most trailing rows are empty/formatted.
- Populated rows: **154 including the header**, or **153 below the header**: 136 source payment/void transactions, 15 allocation/supplemental-only rows, one balance-forward row, and one SUM footer.
- Actual source transactions, excluding the identifiable footer: **136**. The locked row classifier would instead count **137**, because it treats the footer as an inherited-metadata source transaction.
- Debit/Credit semantics agree with the previous July workbook: three positive debit void rows (2,102; 1,300; 10,579.55), with negative credits on the 133 outgoing rows. Supplemental allocation amounts remain distinct from bank transaction amounts.

### Date Cleared distribution on actual source transactions

| Normalized status from the existing parser | Count |
|---|---:|
| cleared | 116 |
| multiple_cleared_dates | 1 |
| outstanding | 13 |
| same_month_void | 6 |
| returned / blank / void-reference / other text | 0 |

Inspection therefore identifies **117 actual dated transactions**, six same-month-void rows, and 13 other non-date exclusions. These are inspection counts, not an accepted sanitized holdout dataset.

| Date Cleared value | Count |
|---|---:|
| `2026/07/01` | 2 |
| `2026/07/01, 2026/07/02` | 1 |
| `2026/07/02` | 5 |
| `2026/07/03` | 1 |
| `2026/07/07` | 2 |
| `2026/07/08` | 9 |
| `2026/07/09` | 7 |
| `2026/07/10` | 7 |
| `2026/07/14` | 3 |
| `2026/07/15` | 12 |
| `2026/07/16` | 1 |
| `2026/07/17` | 4 |
| `2026/07/21` | 2 |
| `2026/07/22` | 8 |
| `2026/07/23` | 6 |
| `2026/07/24` | 19 |
| `2026/07/27` | 1 |
| `2026/07/28` | 7 |
| `2026/07/29` | 13 |
| `2026/07/30` | 4 |
| `2026/07/31` | 3 |
| `Outstanding Check` | 13 |
| `Same month void check` | 6 |

## Concrete incompatibilities

### G154 contains a SUM footer, not another source transaction

Row 154 has no transaction date, check/reference, method, payee, Debit, Date Cleared, or accounting allocation identity. Its only populated original cell is G154:

```text
=SUM(G136:G153,G131:G134,G127:G129,G125,G122,G117:G121,G115,G103:G113,G95:G99,G92,G85:G90,G82,G75:G78,G65:G72,G61:G62,G40:G58,G38,G31:G36,G23:G29,G19:G20,G10:G17,G3:G5,G123)
```

Its stored cached value is **-8266692.29**. The unchanged sanitizer’s `read_aic_ims_rows()` exposes that cached numeric Credit, and `classify_row()` returns **`source_transaction_inherited_metadata`**. This was confirmed by calling those existing read/classification helpers, without running the sanitizer or changing its implementation.

This would introduce a false −8,266,692.29 source transaction and inherited metadata. The new formula is in column G, whereas the prior supported July sheet has formulas only in K/L. A formula warning does not make the falsely included transaction safe. The footer was not deleted, ignored by an adapter, or manually corrected for this validation.

### Filename metadata is unsupported as-is

The locked `accounting_period_label()` requires a filename beginning with a full month and year, such as `July 2026 ...xlsx`. Directly applying it to the uploaded filename raises:

```text
Cannot determine accounting period from filename: AIC_A JE#3784 WF Disb Cash Expense Activity July 2026.xlsx
```

No rename, period-parser override, runtime replacement of sanitizer logic, or staged input rewrite was performed. Even if the naming issue were addressed separately, G154 remains a substantive row-classification incompatibility.

## Other differences from the previous July source

- The previous source has 477 formatted rows; the received sheet has 476. Both have 154 populated rows, but the prior file has 137 actual transactions and no G154 SUM footer; the received file has 136 actual transactions plus that footer.
- Comparing A:H transaction values independently of shifted worksheet row numbers finds one removed transaction and no added actual payment transactions: Insurance Commissioner - State of Washington, −7,774, `Outstanding Direct Debit` (previous source row 71).
- Other source transactions shift upward after that removal. The 117 valid-dated transactions and their A:H identity/payment/clearing values are unchanged in this comparison. This does not substitute for running the locked pipeline.
- All six same-month-void rows now have I:L set to `N/A`; the prior July file retained numeric account/workpaper fields on those void rows. Debit/Credit amounts and clearing labels remain unchanged.
- Formula counts exposed by the locked XML reader: previous July K=4, L=9; received July K=4, L=6, G=1. Some workpaper amounts differ in formula-versus-static representation. No accounting reinterpretation or normalization fix was applied.

## Same Month Void — inspection only

| Positive row | Negative row | Amount | Exact signed net |
|---|---|---:|---:|
| 39 | 37 | 2,102.00 | 0.00 |
| 64 | 63 | 1,300.00 | 0.00 |
| 102 | 84 | 10,579.55 | 0.00 |

The six actual flagged rows show three unique exact zero-net pairs and no repeated-amount group or arithmetic exception. **Arithmetic inspection: PASS.** The internal verifier was not run on an incompatible sanitized population. No void was sent to SUN or claimed SUN evidence.

## Previous July versus received July

| Metric | Previous July canonical run | Received July holdout |
|---|---:|---|
| Actual source transactions | 137 | 136 inspected; locked classifier would produce 137 including footer |
| Valid actual-cleared-date population | 117 | 117 inspected; not sanitized/verified |
| Same Month Void rows | 6 | 6 inspected |
| SUN VERIFIED | 73 | NOT RUN |
| VERIFIED / valid-cleared-date population | 62.39% | NOT RUN; no rate claimed |
| ONE_TO_ONE | 60 | NOT RUN |
| ONE_TO_MANY | 13 | NOT RUN |
| Eligible SUN HUMAN_REVIEW_REQUIRED | 44 | NOT RUN |
| Eligible SUN human-review rate | 37.61% | NOT RUN |
| SUN reuse conflicts | 4 IMS cases / 5 SUN rows | NOT RUN |

Previous July eligible SUN review reasons: `NOT_SUPPORTED_BY_SUN`: 4; `SUN_EVIDENCE_CONFLICT`: 36; `SUN_ROW_REUSE_CONFLICT`: 4.

The observed population change is removal of an outstanding transaction, not newly supplied clearing dates for the existing eligible population. The workbook also introduces a report-total formula incompatible with locked normalization. No conclusions about improved holdout verification performance or cleaner matching can be drawn without a valid isolated canonical input; previous verifier limitations were not retuned.

## Validation safeguards and stopping point

1. No historical input, sanitized output, or January–July verification output was overwritten. Only this report was created under the requested validation location.
2. No holdout IMS transaction entered SUN matching; therefore no holdout void entered matching or claimed SUN evidence.
3. There are no holdout verified results or SUN claims: non-reuse is not asserted as a completed-run metric.
4. Both locked sanitizers and the current verifier were unchanged. File hashes for protected files were checked before and after writing this report.
5. No thresholds or matching rules were tuned; no old/new July populations were combined.
6. Validation stops here as requested for an incompatible input. A compatible source export without the transaction-like SUM footer, plus compatible period metadata/naming, is needed before a genuine locked-pipeline holdout run can be reported.
