# July 2026 holdout validation — completed current and payment-sensitivity runs

## Scope and validation-only adapter

Input: `data/validation/new_july_2026/AIC_A JE#3784 WF Disb Cash Expense Activity July 2026.xlsx`, sheet `AIC IMS`.

The validation-only adapter is `run_july_holdout.py` in this directory. It loads a separate in-memory instance of the unchanged locked IMS sanitizer, then performs only the authorized adaptations:

1. Validate and exclude original row **154**, whose only populated value is the identified column-G SUM footer.
2. Assign accounting period **2026-07**, independently of the unsupported uploaded filename.
3. Route every sanitizer output to this validation directory's `processed/` folder.

All other parsing, header validation, Debit/Credit normalization, formula/cached-value handling, source-row provenance, allocation linkage, and QA use the locked sanitizer's existing functions. The uploaded workbook was not edited or renamed. No staging file with rewritten cell values was created. Canonical provenance retains the actual uploaded workbook filename and original worksheet row numbers.

Reproduction from the repository root:

```bash
.venv/bin/python -m data.validation.new_july_2026.run_july_holdout
```

The adapter refuses to overwrite a completed run. It can reuse this task's canonical files after a comparison-only interruption without rewriting them. Production sanitizers and verifier are not patched on disk or configured differently for matching.

## Input compatibility and isolated normalization

Header row **1**, columns A:M, unchanged from the earlier inspection:

```text
['TransactionDate', 'CheckOrRef', 'Method', 'PaymentType', 'Description', 'Debit', 'Credit', 'Date Cleared', 'Account', 'Cost Center', 'Description', ' Amount', 'Backup']
```

The raw worksheet has 154 populated rows including the header and SUM footer. After explicitly excluding the footer, the meaningful population consists of the header, one balance-forward row, **136 source transactions**, and 15 allocation/supplemental-only rows. The locked sanitizer produces **136 canonical transactions** and 151 allocation records. Debit/Credit signs and allocation-line semantics are unchanged.

Canonical transaction statuses:

| Status | Count |
|---|---:|
| cleared | 116 |
| multiple_cleared_dates | 1 |
| same_month_void | 6 |
| outstanding | 13 |

QA: **0** ambiguous supplemental blocks, **0** inheritance ambiguities, **0** allocation reconciliation mismatches, **0** unexpected rows, **0** formula cells outside K/L after footer exclusion. No source transaction has source row 154.

## Same Month Void: internal control only

The unchanged internal verifier evaluates all six void rows. They form three exact zero-net unique pairs:

| Holdout IMS members | Positive / negative signed amount | Internal result |
|---|---:|---|
| `IMS-2026-07-R39` / `IMS-2026-07-R37` | +2,102.00 / −2,102.00 | PASSED, SAME_MONTH_VOID_NET_ZERO |
| `IMS-2026-07-R64` / `IMS-2026-07-R63` | +1,300.00 / −1,300.00 | PASSED, SAME_MONTH_VOID_NET_ZERO |
| `IMS-2026-07-R102` / `IMS-2026-07-R84` | +10,579.55 / −10,579.55 | PASSED, SAME_MONTH_VOID_NET_ZERO |

Repeated-amount groups: **0**. Internal exceptions/failures: **0**. All six are SUN-ineligible, perform no SUN search, and make no SUN evidence claims. Source-row shifts alter the last pair's identifiers relative to the old July workbook but not its amounts or internal outcome.

## Run A — Current production SUN verification

The unchanged current production verifier (rules version **5**, with payment/check enforcement enabled) receives only this new canonical population and `data/processed/sun_jnl/sun_jnl_2026-07.csv`. It does not combine old and new IMS transactions. Its eligibility gate limits SUN searches to **117 actual-dated transactions**; six voids and 13 outstanding records remain outside SUN.

| Metric | Holdout result |
|---|---:|
| Eligible dated IMS transactions / SUN evaluated | **117** |
| VERIFIED | **73** |
| Primary verification rate: VERIFIED / 117 | **62.39%** |
| ONE_TO_ONE | **60** |
| ONE_TO_MANY | **13** |
| Eligible HUMAN_REVIEW_REQUIRED | **44** |
| Eligible human-review rate: 44 / 117 | **37.61%** |
| NOT_SUPPORTED_BY_SUN | **4** |
| SUN_EVIDENCE_CONFLICT | **36** |
| SUN_ROW_REUSE_CONFLICT | **4** |
| SUN rows involved in reuse conflicts | **5** |

The four reuse-conflict transactions are routed to human review. **102 distinct SUN allocation rows** support the 73 finally verified transactions, with **no row reused** among those results.

The standard verifier summary also retains legacy whole-population metrics: 73/136 overall automatic rate and 63 whole-record human-review routes (44 SUN review + 19 exclusions). These are **not** the requested primary holdout rates. The correct SUN denominator is **117**, as shown above; void exclusions are not failed SUN verifications.

## Comparison against the previous July canonical run

| Metric | Previous July | New July holdout |
|---|---:|---:|
| Total source transactions | 137 | 136 |
| Valid actual-cleared-date population | 117 | 117 |
| Same Month Void rows | 6 | 6 |
| Other non-date exclusions | 14 | 13 |
| SUN VERIFIED | 73 | 73 |
| Eligible verification rate | 62.39% | 62.39% |
| ONE_TO_ONE | 60 | 60 |
| ONE_TO_MANY | 13 | 13 |
| Eligible HUMAN_REVIEW_REQUIRED | 44 | 44 |
| NOT_SUPPORTED_BY_SUN | 4 | 4 |
| SUN_EVIDENCE_CONFLICT | 36 | 36 |
| SUN_ROW_REUSE_CONFLICT | 4 | 4 |

**No shared transaction changes eligibility, final routing outcome, SUN outcome, verification method, primary reason, or selected SUN source rows.** All 117 eligible transactions remain the same 73 verified and 44 unresolved business transactions. All six void and 13 retained outstanding transactions also keep their outcomes.

### Every changed outcome or population membership

There are **zero changed outcomes among shared transactions**, zero added source transactions, and one removed non-date record:

| Previous IMS ID / source row | Holdout ID | Vendor / amount | Previous result | Explanation |
|---|---|---|---|---|
| `IMS-2026-07-R71` / 71 | Not present | Insurance Commissioner - State of Washington / −7,774.00 | SUN-ineligible; HUMAN_REVIEW_REQUIRED; DATE_CLEARED_MISSING_OR_INVALID; raw value Outstanding Direct Debit | The received workbook omits this outstanding entry. It never belonged to the 117 eligible July transactions, so its removal changes total population but not SUN results. |

The separate cleared Washington transaction (`IMS-2026-07-R70`) remains. Its Cost Center FINU distinguishes it from the removed outstanding entry's ZZZZ; the adapter's **comparison-only** identity key uses these existing dimensions to distinguish the two, without modifying verification logic.

Source-row IDs must not be compared directly across workbooks: **77 of the 136 shared transactions have shifted row-based IDs** following the removed entry. Comparison uses a unique canonical business key (period, transaction date, check/reference, method, payment type, vendor, signed amount, and non-void account dimensions). Void N/A dimensions are not used as stable cross-workbook identifiers. Duplicate keys are explicitly rejected rather than paired by arbitrary order. The complete 137-entry crosswalk, including both original result records, is saved as `processed/verification/transaction_comparison.jsonl`.

The differences reflect removal of an outstanding transaction and N/A workpaper dimensions on void rows, not new clearing dates or improved eligible matching data. Existing verifier limitations remain visible: unsupported evidence, payment/check identity conflicts, and competing claims. No rules or thresholds were tuned to improve the holdout result.

## Artifacts and safeguards

- Canonical files: `processed/AIC_A JE#3784 WF Disb Cash Expense Activity July 2026/` (`aic_ims_rows.csv`, `aic_ims_transactions.csv`, `aic_ims_allocations.csv`, `aic_ims_validation.json`).
- Verification: `processed/verification/verification_results.jsonl` and `verification_summary.json`.
- Comparison: `processed/verification/transaction_comparison.jsonl`.
- Provenance and protection hashes: `processed/adapter_manifest.json`, including original workbook hash, exact excluded footer formula/cached value, sanitizer/verifier hashes, period override, SUN hash, and comparison counts.

Confirmed by run assertions and SHA256 checks:

1. The production IMS sanitizer, SUN sanitizer, and verifier were **not modified**.
2. Production historical files under `data/processed/` were **not overwritten**; hashes remain unchanged. All new outputs are under the validation directory.
3. No Same Month Void transaction entered SUN matching, generated candidate evidence, claimed SUN evidence, or joined reuse conflicts.
4. No SUN row was reused among finally VERIFIED eligible transactions.
5. The old and new IMS populations were never combined for verification; old results were read only afterward for comparison.

The current-rule holdout results above are retained. The completed second, payment-sensitivity run and its comparison follow below.


## Run A / Run B completed comparison — new July population

Eligibility was reconfirmed **before either run** from the isolated canonical CSV: **136 total source transactions, 116 cleared + one multiple-cleared-dates = 117 eligible**, with six same-month voids and 13 outstanding rows excluded. The original workbook, sanitizer, verifier, and July SUN hashes still match the prior adapter manifest, so the already normalized validation population was reused without rewriting its canonical files.

Run A calls the production verifier unchanged with only those 117 eligible records. Run B loads the exact same production source in a separate in-memory module and overrides only `payment_agrees(ims, sun)` to return True. It receives the identical 117 records and identical July SUN data. The production module's function object and source file remain untouched. This is the **production payment-enforced baseline versus a diagnostic shadow**, not an approved change to production policy.

| Metric | New July current rules | New July without payment-type enforcement |
|---|---|---|
| Eligible actual-cleared transactions | 117 | 117 |
| VERIFIED | 73 | 109 |
| Verification rate | 62.39% | 93.16% |
| ONE_TO_ONE | 60 | 83 |
| ONE_TO_MANY | 13 | 26 |
| HUMAN_REVIEW_REQUIRED | 44 | 8 |
| Human-review rate | 37.61% | 6.84% |
| NOT_SUPPORTED_BY_SUN | 4 | 4 |
| SUN_EVIDENCE_CONFLICT | 36 | 0 |
| SUN_ROW_REUSE_CONFLICT | 4 | 4 |
| SUN rows involved in reuse conflicts | 5 | 5 |
| Distinct SUN rows supporting finally verified transactions | 102 | 151 |

**36 additional transactions become VERIFIED solely from disabling payment/check enforcement**: +30.77 percentage points of the same 117-row denominator. All 36 originally had primary reason `SUN_EVIDENCE_CONFLICT`. **Zero previously verified transactions become unresolved.**

### Ambiguity and reuse

Candidate row sets, sums, differences, ranking, and existing reuse-conflict details were asserted identical between A and B. Therefore removing payment enforcement creates **zero new candidate combinations and zero new reuse conflicts**. All four existing reuse-conflict cases remain human review, covering the same five SUN rows. Three expose multiple-candidate reasons after the payment veto is removed:

| Holdout IMS ID | Previous July IMS ID | Run A reasons | Run B reasons |
|---|---|---|---|
| IMS-2026-07-R42 | IMS-2026-07-R42 | SUN_EVIDENCE_CONFLICT; SUN_ROW_REUSE_CONFLICT | MULTIPLE_PLAUSIBLE_SUN_MATCHES; SUN_ROW_REUSE_CONFLICT |
| IMS-2026-07-R132 | IMS-2026-07-R133 | SUN_EVIDENCE_CONFLICT; SUN_ROW_REUSE_CONFLICT | MULTIPLE_PLAUSIBLE_SUN_COMBINATIONS; SUN_ROW_REUSE_CONFLICT |
| IMS-2026-07-R153 | IMS-2026-07-R154 | SUN_EVIDENCE_CONFLICT; SUN_ROW_REUSE_CONFLICT | MULTIPLE_PLAUSIBLE_SUN_MATCHES; SUN_ROW_REUSE_CONFLICT |

This is newly exposed ambiguity in already unresolved cases, not a new ambiguous assignment or a loss of a previously verified match. None is forced through. Four unsupported cases also remain unsupported. No SUN row is reused among finally verified results in either run.

### Comparison with previous July

| Policy | Previous July historical | New July holdout | Difference |
|---|---:|---:|---:|
| Current rules | 73 / 117 = 62.39% | 73 / 117 = 62.39% | None |
| No-payment-type shadow | 109 / 117 = 93.16% | 109 / 117 = 93.16% | None |

A separate in-memory reference calculation on the old July eligible canonical data, using the same SUN data and same shadow override, confirms the same outcomes, methods, primary reasons, and selected SUN rows for **every corresponding eligible transaction**, not just the aggregate counts. The populations were not combined for verification.

The new workbook removes one outstanding Washington entry and changes void workpaper dimensions, but does not improve or expand the eligible 117 payment/clearing population. Row-based IDs shift, so the existing unique business-key crosswalk is used. There is no evidence here of cleaner actual clearing information producing a higher rate. The 36-row gain is entirely a consequence of disabling the existing payment/check identity veto; it is not an improvement attributable to receiving a newer workbook. Matching rules, date handling, identities, amounts, bounds, ambiguity handling, and non-reuse were not tuned.

### Additional shadow verifications

Full IMS and SUN payment/reference fields remain in both diagnostic result files. The additional cases are listed below; SUN row numbers refer to the unchanged July canonical source (`Page1_1`).

| Holdout IMS ID | Previous July IMS ID | IMS vendor | IMS signed amount | IMS payment / reference | Shadow method | SUN row(s) | SUN payment / reference |
|---|---|---|---|---|---|---|---|
| IMS-2026-07-R25 | IMS-2026-07-R25 | NAIC SERFF | -1510.0 | Direct Debit / <blank> | ONE_TO_MANY | 621, 625 | ACH / 07.01.2026 AIC; ACH / 07.02.2026 AIC |
| IMS-2026-07-R33 | IMS-2026-07-R33 | New Mexico Taxation and Revenue Department | -10781.92 | Direct Debit / <blank> | ONE_TO_ONE | 739 | ACH / NM 2026 Q2 Premium AIC |
| IMS-2026-07-R34 | IMS-2026-07-R34 | Vertafore Inc | -2000.0 | Direct Debit / <blank> | ONE_TO_ONE | 1080 | ACH / NV 1377173 AIC |
| IMS-2026-07-R36 | IMS-2026-07-R36 | Michigan Department of Treasury | -215937.0 | Direct Debit / <blank> | ONE_TO_ONE | 564 | ACH / MI 2026 Q2 AIC |
| IMS-2026-07-R38 | IMS-2026-07-R38 | WNGATES.COM | -395.0 | Direct Debit / <blank> | ONE_TO_MANY | 1119, 1121 | ACH / 06252026001; ACH / 06252026019 |
| IMS-2026-07-R40 | IMS-2026-07-R40 | New York State Department of Financial Services | -3088.25 | Direct Debit / <blank> | ONE_TO_MANY | 743, 744 | ACH / NY Q2 26 Fire Ins Fee AIC; ACH / NY Q2 26 Fire Ins Fee AIC |
| IMS-2026-07-R41 | IMS-2026-07-R41 | MS Department of Revenue | -78899.1 | Direct Debit / <blank> | ONE_TO_ONE | 602 | ACH / MS 2026 Q3 Est PT Pmt_AIC |
| IMS-2026-07-R43 | IMS-2026-07-R43 | Kentucky State Treasurer | -659.0 | Direct Debit / <blank> | ONE_TO_ONE | 438 | ACH / KY 2026 June Surchg Rpt AIC |
| IMS-2026-07-R44 | IMS-2026-07-R44 | City of Chicago | -5359.0 | Direct Debit / <blank> | ONE_TO_ONE | 180 | ACH / IL 2026 City of Chicago Foreign Fire Ins Tax_AIC |
| IMS-2026-07-R45 | IMS-2026-07-R45 | District of Columbia Life and Health Insurance Guaranty Association | -117.5 | Direct Debit / <blank> | ONE_TO_MANY | 293, 294 | ACH / 23752DHCF2026; ACH / 23752DHCF2026 |
| IMS-2026-07-R46 | IMS-2026-07-R46 | West Virginia Life and Health Insurance Guaranty Association | -401.59 | Direct Debit / <blank> | ONE_TO_MANY | 1101, 1102 | ACH / WV 2026 LHIGA Class A Assmnt AIC; ACH / WV 2026 LHIGA Class A Assmnt AIC |
| IMS-2026-07-R57 | IMS-2026-07-R57 | DCCA, State of Hawaii | -17.5 | Direct Debit / <blank> | ONE_TO_ONE | 280 | ACH / HI Jun26 FEE AIC |
| IMS-2026-07-R61 | IMS-2026-07-R61 | Michigan Dept of Insurance & Financial Services | -6804.0 | Direct Debit / <blank> | ONE_TO_ONE | 570 | ACH / MI 2026 Reg Assmt Fee_AIC |
| IMS-2026-07-R67 | IMS-2026-07-R67 | The Bank of Nova Scotia | -50811.05 | Direct Debit / <blank> | ONE_TO_ONE | 1032 | Wire / 071026/50811.05 |
| IMS-2026-07-R70 | IMS-2026-07-R70 | Insurance Commissioner - State of Washington | -7774.0 | Direct Debit / <blank> | ONE_TO_MANY | 412, 414 | ACH / WA 2026 Fraud Surcharge_AIC; ACH / WA 2026 Reg Surchg Assmt AIC |
| IMS-2026-07-R87 | IMS-2026-07-R88 | NAIC SERFF | -83.0 | Direct Debit / <blank> | ONE_TO_ONE | 634 | ACH / 07.15.2026 AIC |
| IMS-2026-07-R112 | IMS-2026-07-R113 | State of Idaho | -1010.0 | Direct Debit / <blank> | ONE_TO_ONE | 960 | ACH / 23752 - IC-4008 2026 1st Half |
| IMS-2026-07-R131 | IMS-2026-07-R132 | Utah State Tax Commission | -33447.0 | Direct Debit / <blank> | ONE_TO_ONE | 1076 | ACH / UT 2026 Q2 Est PT Pmts_AIC |
| IMS-2026-07-R133 | IMS-2026-07-R134 | Illinois Department of Insurance | -55142.04 | Direct Debit / <blank> | ONE_TO_MANY | 389, 390 | ACH / IL 2026 IC Ops Fund Surchg_AIC; ACH / IL 2026 IC Ops Fund Surchg_AIC |
| IMS-2026-07-R134 | IMS-2026-07-R135 | State Comptroller | -575225.01 | Direct Debit / <blank> | ONE_TO_MANY | 956, 957 | ACH / TX 2026 2nd Instllmt Est PT_AIC; ACH / TX 26 Vol Fire Dept Assist Fund Assmt AIC |
| IMS-2026-07-R136 | IMS-2026-07-R137 | NAIC SERFF | -4079.0 | Direct Debit / <blank> | ONE_TO_ONE | 650 | ACH / 07.28.2026 AIC |
| IMS-2026-07-R137 | IMS-2026-07-R138 | MN Dept of Labor & Industry-Financial Services | -3190.13 | Direct Debit / <blank> | ONE_TO_ONE | 594 | ACH / MN 2026 1st Half SCF Assmt_AIC |
| IMS-2026-07-R138 | IMS-2026-07-R139 | Division of Workers Compensation | -21959.99 | Direct Debit / <blank> | ONE_TO_ONE | 298 | ACH / FL 2026 Q2 WCATF & SDTF Assmt_AIC |
| IMS-2026-07-R139 | IMS-2026-07-R140 | Kentucky Workers’ Compensation Funding Commission | -10798.21 | Direct Debit / <blank> | ONE_TO_ONE | 445 | ACH / KY 2026 Q2 WC Funding Prem Rpt_AIC |
| IMS-2026-07-R140 | IMS-2026-07-R141 | Arizona Automobile Theft Authority | -32.5 | Direct Debit / <blank> | ONE_TO_MANY | 70, 71 | ACH / AZ 2026 1st Half Auto Theft Auth Assmt AIC; ACH / AZ 2026 1st Half Auto Theft Auth Assmt AIC |
| IMS-2026-07-R141 | IMS-2026-07-R142 | Compensation Advisory Org of Michigan (CAOM) | -926.45 | Direct Debit / <blank> | ONE_TO_ONE | 270 | ACH / MI 2026 Q3 CAOM Assmt_AIC |
| IMS-2026-07-R142 | IMS-2026-07-R143 | Division of Workers' Compensation | -15905.15 | Direct Debit / <blank> | ONE_TO_MANY | 305, 306 | ACH / CO 2026 1st Half WC Surchg Form_AIC; ACH / CO 2026 1st Half WC Surchg Form_AIC |
| IMS-2026-07-R143 | IMS-2026-07-R144 | Melrose Park Fire Department | -172.15 | Direct Debit / <blank> | ONE_TO_ONE | 554 | ACH / IL 2025 Foreign Fire Tax LOCAL GOV - Various AIC |
| IMS-2026-07-R144 | IMS-2026-07-R145 | Michigan Workers Compensation Placement Facility | -900.99 | Direct Debit / <blank> | ONE_TO_ONE | 575 | ACH / MI 2026 Q3 MWCPF Assmt_AIC |
| IMS-2026-07-R145 | IMS-2026-07-R146 | Industrial Commission of Arizona | -5266.07 | Direct Debit / <blank> | ONE_TO_ONE | 399 | ACH / AZ 2026 Q2 WC Est PT_AIC |
| IMS-2026-07-R146 | IMS-2026-07-R147 | Office of Commissioner, Attn: IFO Division | -728326.7 | Direct Debit / <blank> | ONE_TO_MANY | 766, 767 | ACH / GA 2026 Municipal Premium Tax AIC; ACH / GA 2026 Municipal Premium Tax AIC |
| IMS-2026-07-R147 | IMS-2026-07-R148 | Nevada Department of Taxation | -136719.71 | Direct Debit / <blank> | ONE_TO_ONE | 728 | ACH / NV 2026 Q2 Est P&I Pmt_AIC |
| IMS-2026-07-R148 | IMS-2026-07-R149 | Joliet Fire Department | -242.6 | Direct Debit / <blank> | ONE_TO_ONE | 433 | ACH / IL 2025 Foreign Fire Tax LOCAL GOV - Various AIC |
| IMS-2026-07-R149 | IMS-2026-07-R150 | Colorado Divison of Insurance | -61668.5 | Direct Debit / <blank> | ONE_TO_MANY | 262, 263 | ACH / CO 2026 Q2 Est PT Pmt AIC; ACH / CO 2026 Q2 Est PT Pmt AIC |
| IMS-2026-07-R150 | IMS-2026-07-R151 | Treasurer, State of Maine | -11.0 | Direct Debit / <blank> | ONE_TO_ONE | 1062 | ACH / ME 2026 July Est Fire Tax AIC |
| IMS-2026-07-R152 | IMS-2026-07-R153 | Massachusetts Department of Industrial Accidents | -3898.0 | Direct Debit / <blank> | ONE_TO_MANY | 545, 546 | ACH / MA 2026 Q2 PTF & SF Assmt_AIC; ACH / MA 2026 Q2 PTF & SF Assmt_AIC |

### Two-run artifacts and final safeguards

New files under `processed/payment_type_comparison/`:

- `run_a_current_results.jsonl`: all 117 eligible results with current enforcement.
- `run_b_shadow_results.jsonl`: all 117 eligible results with only payment enforcement disabled.
- `comparison_summary.json`: both metric sets, additional IDs, exposed ambiguity IDs, input fingerprints, and the exact shadow scope.

Original IMS records, raw SUN payment types/references, candidate SUN source records, sums, identity evidence, and source-row provenance are retained. The diagnostic `diagnostic_actual_matched_payment_agreement` records factual production payment agreement separately: the shadow's `payment_identity_agrees=True` means the veto was bypassed, not that differing payment fields actually agree.

Confirmed: both locked sanitizers and production verifier remain unchanged; existing historical outputs and the prior holdout canonical/results/comparison files were not overwritten; no same-month void enters either SUN run or claims evidence; final verified evidence is unique in each run. Protection hashes were checked before and after creating the two-run artifacts and updating this report. The only existing file updated is this explicitly requested report. No production rule change is proposed or applied by this validation.
