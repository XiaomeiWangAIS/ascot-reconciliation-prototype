# Payment-type sensitivity: isolated counterfactual diagnostic

## Scope and implementation

Production rules version: **5**. Inputs are the existing historical January–July 2026 canonical IMS transactions and seven locked SUN CSVs. The incompatible newly received July holdout workbook is not included.

Of 1099 IMS source transactions, only **731** with valid actual normalized cleared dates enter either run. All 368 non-date/invalid-date records, including all same-month voids, are excluded.

A fresh Python process loaded the same verifier source into a separate shadow module. Only that module’s `payment_agrees(ims, sun)` function returned True unconditionally. The production module/function was not modified, and neither CLI main program was invoked. Results were held in memory; no canonical or historical output was rewritten.

Exact AIC scope, same accounting period, vendor identity, signed amount convention/tolerance, vendor/date ordering, contiguous/one-gap candidates, ranking, ambiguity handling, bounds, and evidence non-reuse remain identical. Payment/reference fields remain in each original IMS record and matched SUN record and are displayed below. Shadow verification is diagnostic, not an approved production outcome.

## Overall results

| Metric | Current enforcement | Shadow without enforcement |
|---|---|---|
| Eligible actual-cleared-date IMS transactions | 731 | 731 |
| VERIFIED | 324 | 401 |
| VERIFIED / eligible | 44.32% | 54.86% |
| HUMAN_REVIEW_REQUIRED | 407 | 330 |
| Human-review rate | 55.68% | 45.14% |
| NOT_SUPPORTED_BY_SUN | 313 | 313 |
| SUN_EVIDENCE_CONFLICT (primary) | 77 | 0 |
| SUN_ROW_REUSE_CONFLICT (primary) | 17 | 17 |
| Standalone multiple-candidate primary reasons | 0 | 0 |

**Incremental newly verified: 77** (10.53 percentage points of the eligible population). **Previously verified transactions lost: 0**. All newly verified rows originally had primary reason `SUN_EVIDENCE_CONFLICT`.

## Monthly results

| Month | Eligible | Current verified | Current rate | Shadow verified | Shadow rate | Newly verified | Shadow 1:1 | Shadow 1:many | Shadow review | Unsupported | Reuse cases |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-01 | 110 | 45 | 40.91% | 47 | 42.73% | 2 | 44 | 3 | 63 | 61 | 2 |
| 2026-02 | 104 | 40 | 38.46% | 44 | 42.31% | 4 | 39 | 5 | 60 | 60 | 0 |
| 2026-03 | 100 | 37 | 37.00% | 37 | 37.00% | 0 | 31 | 6 | 63 | 60 | 3 |
| 2026-04 | 123 | 43 | 34.96% | 46 | 37.40% | 3 | 33 | 13 | 77 | 77 | 0 |
| 2026-05 | 75 | 26 | 34.67% | 28 | 37.33% | 2 | 23 | 5 | 47 | 45 | 2 |
| 2026-06 | 102 | 60 | 58.82% | 90 | 88.24% | 30 | 59 | 31 | 12 | 6 | 6 |
| 2026-07 | 117 | 73 | 62.39% | 109 | 93.16% | 36 | 83 | 26 | 8 | 4 | 4 |

June increases **60 → 90** verified (**58.82% → 88.24%**), adding 30. July increases **73 → 109** (**62.39% → 93.16%**), adding 36. Together these months account for **66 of 77** gains. These gains isolate the effect of payment/check enforcement on existing candidates; no dates, amounts, vendor aliases, or population rules were tuned.

## Remaining ambiguity, unsupported cases, and newly exposed ambiguity

- **17 transactions remain unresolved due to shared SUN evidence.** Of these, **9** have multiple local candidate combinations; the other 8 have a single combination that conflicts with another eligible IMS claimant.
- **313 remain unsupported**: removing payment identity does not create an amount/identity-supported candidate under existing rules. Unsupported counts and identities are unchanged.
- **No new candidate combinations or new reuse conflicts were created.** Payment agreement is evaluated after candidate generation, and all candidate signatures and reuse-conflict details were checked unchanged.
- **6 transactions newly expose a multiple-candidate reason** when the prior payment conflict is removed. All already had primary `SUN_ROW_REUSE_CONFLICT`, and remain in human review. This is revealed ambiguity, not additional generated combinations or newly unresolved previously verified cases.

| IMS transaction | Vendor | Shadow candidate count | Current reasons | Shadow reasons |
|---|---|---|---|---|
| IMS-2026-06-R56 | Kansas Insurance Department | 2 | SUN_EVIDENCE_CONFLICT; SUN_ROW_REUSE_CONFLICT | MULTIPLE_PLAUSIBLE_SUN_COMBINATIONS; SUN_ROW_REUSE_CONFLICT |
| IMS-2026-06-R84 | Oklahoma Department of Insurance | 2 | SUN_EVIDENCE_CONFLICT; SUN_ROW_REUSE_CONFLICT | MULTIPLE_PLAUSIBLE_SUN_COMBINATIONS; SUN_ROW_REUSE_CONFLICT |
| IMS-2026-06-R149 | NAIC SERFF | 2 | SUN_EVIDENCE_CONFLICT; SUN_ROW_REUSE_CONFLICT | MULTIPLE_PLAUSIBLE_SUN_COMBINATIONS; SUN_ROW_REUSE_CONFLICT |
| IMS-2026-07-R42 | NAIC SERFF | 4 | SUN_EVIDENCE_CONFLICT; SUN_ROW_REUSE_CONFLICT | MULTIPLE_PLAUSIBLE_SUN_MATCHES; SUN_ROW_REUSE_CONFLICT |
| IMS-2026-07-R133 | Louisiana Department of Insurance | 2 | SUN_EVIDENCE_CONFLICT; SUN_ROW_REUSE_CONFLICT | MULTIPLE_PLAUSIBLE_SUN_COMBINATIONS; SUN_ROW_REUSE_CONFLICT |
| IMS-2026-07-R154 | NAIC SERFF | 4 | SUN_EVIDENCE_CONFLICT; SUN_ROW_REUSE_CONFLICT | MULTIPLE_PLAUSIBLE_SUN_MATCHES; SUN_ROW_REUSE_CONFLICT |

All remaining reuse/ambiguity cases:

| IMS transaction | Vendor | Candidate combinations | Competing IMS IDs |
|---|---|---|---|
| IMS-2026-01-R278 | Sedgwick Claims Management Services | 2 | IMS-2026-01-R295 |
| IMS-2026-01-R295 | Sedgwick Claims Management Services | 2 | IMS-2026-01-R278 |
| IMS-2026-03-R6 | Safe Harbor Pollution Insurance | 1 | IMS-2026-03-R23 |
| IMS-2026-03-R7 | Safe Harbor Pollution Insurance | 1 | IMS-2026-03-R23 |
| IMS-2026-03-R23 | Safe Harbor Pollution Insurance | 1 | IMS-2026-03-R6, IMS-2026-03-R7 |
| IMS-2026-05-R53 | U.S. Bank | 2 | IMS-2026-05-R54 |
| IMS-2026-05-R54 | U.S. Bank | 1 | IMS-2026-05-R53 |
| IMS-2026-06-R56 | Kansas Insurance Department | 2 | IMS-2026-06-R127 |
| IMS-2026-06-R58 | NAIC SERFF | 1 | IMS-2026-06-R149 |
| IMS-2026-06-R84 | Oklahoma Department of Insurance | 2 | IMS-2026-06-R135 |
| IMS-2026-06-R127 | Kansas Insurance Department | 1 | IMS-2026-06-R56 |
| IMS-2026-06-R135 | Oklahoma Department of Insurance | 1 | IMS-2026-06-R84 |
| IMS-2026-06-R149 | NAIC SERFF | 2 | IMS-2026-06-R58 |
| IMS-2026-07-R29 | Louisiana Department of Insurance | 1 | IMS-2026-07-R133 |
| IMS-2026-07-R42 | NAIC SERFF | 4 | IMS-2026-07-R154 |
| IMS-2026-07-R133 | Louisiana Department of Insurance | 2 | IMS-2026-07-R29 |
| IMS-2026-07-R154 | NAIC SERFF | 4 | IMS-2026-07-R42 |

## Every newly verified transaction and its SUN evidence

Amounts below preserve canonical values. IMS signed amount and positive SUN target are shown separately. SUN per-line amounts are allocation amounts; their verified sum is recorded for each case. `<blank>` denotes an absent source value. Row identifiers reference the original canonical provenance; no source fields were rewritten.

### 1. IMS-2026-01-R34

- IMS source: `January 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **34**.
- IMS vendor: TRISTAR Claims Management Services Inc..
- IMS signed amount: `-227288.49`; SUN target: `227288.49`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-01-15; cleared dates: 2026/01/15.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `227288.49`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL January 2026.xlsx | Page1_1 | 621 | TRISTAR Claims Management Services Inc. | 227288.49 | Wire | 202512-ASCOT Go6506 | 2026-01-16 |

### 2. IMS-2026-01-R292

- IMS source: `January 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **292**.
- IMS vendor: The Bank of Nova Scotia.
- IMS signed amount: `-49420.76`; SUN target: `49420.76`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-01-23; cleared dates: 2026/01/28.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `49420.76`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL January 2026.xlsx | Page1_1 | 563 | The Bank of Nova Scotia | 49420.76 | Wire | 12252025/49420.76 | 2026-01-26 |

### 3. IMS-2026-02-R17

- IMS source: `February 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **17**.
- IMS vendor: TRISTAR Claims Management Services Inc..
- IMS signed amount: `-305485.76`; SUN target: `305485.76`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-02-05; cleared dates: 2026/02/05.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `305485.76`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL February 2026.xlsx | Page1_1 | 642 | TRISTAR Claims Management Services Inc. | 305485.76 | Wire | 202601-ASCOT Go6506 | 2026-02-06 |

### 4. IMS-2026-02-R30

- IMS source: `February 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **30**.
- IMS vendor: Department of Consumer & Business Services.
- IMS signed amount: `-1500.0`; SUN target: `1500.0`.
- IMS payment type: Check; check/reference: 4339.
- IMS transaction date: 2026-02-09 08:52:50; cleared dates: 2026/02/26.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `1500`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL February 2026.xlsx | Page1_1 | 151 | Department of Consumer & Business Services | 1500 | ACH | 2500167 CF | 2026-02-06 |

### 5. IMS-2026-02-R33

- IMS source: `February 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **33**.
- IMS vendor: State of Idaho Industrial Commission.
- IMS signed amount: `-7217.64`; SUN target: `7217.64`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-02-10; cleared dates: 2026/02/11.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `7217.64`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL February 2026.xlsx | Page1_1 | 580 | State of Idaho Industrial Commission | 7217.64 | ACH | 23752-IC-4008 | 2026-02-11 |

### 6. IMS-2026-02-R90

- IMS source: `February 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **90**.
- IMS vendor: Idaho Department of Insurance.
- IMS signed amount: `-4783.0`; SUN target: `4783.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-02-26; cleared dates: 2026/02/27.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `4783`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL February 2026.xlsx | Page1_1 | 230 | Idaho Department of Insurance | 4500 | ACH | 23752 - Annual PT Return | 2026-02-27 |
| data/raw/Paid Invoices for SUN JNL February 2026.xlsx | Page1_1 | 231 | Idaho Department of Insurance | 8 | ACH | 23752 - Annual PT Return | 2026-02-27 |
| data/raw/Paid Invoices for SUN JNL February 2026.xlsx | Page1_1 | 232 | Idaho Department of Insurance | 275 | ACH | 23752 - Annual PT Return | 2026-02-27 |

### 7. IMS-2026-04-R77

- IMS source: `April 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **77**.
- IMS vendor: CDPS Natural Disaster Mitigation Enterprise.
- IMS signed amount: `-78.0`; SUN target: `78.0`.
- IMS payment type: ACH; check/reference: `<blank>`.
- IMS transaction date: 2026-04-21 09:55:30; cleared dates: 2026/04/22.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `78`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL Apr 2026.xlsx | Page1_1 | 873 | CDPS Natural Disaster Mitigation Enterprise | 78 | `<blank>` | #4 - 23752 - 2026 NDME | 2026-04-23 |

### 8. IMS-2026-04-R78

- IMS source: `April 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **78**.
- IMS vendor: Lloyds Bank Corporate Markets PLC.
- IMS signed amount: `-121114.02`; SUN target: `121114.02`.
- IMS payment type: Wire; check/reference: `<blank>`.
- IMS transaction date: 2026-04-21 09:58:20; cleared dates: 2026/04/22.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `121114.02`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL Apr 2026.xlsx | Page1_1 | 908 | Lloyds Bank Corporate Markets PLC | 121114.02 | `<blank>` | 0000053323 | 2026-04-23 |

### 9. IMS-2026-04-R123

- IMS source: `April 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **123**.
- IMS vendor: The Bank of Nova Scotia.
- IMS signed amount: `-49525.57`; SUN target: `49525.57`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-04-29 09:38:13; cleared dates: 2026/04/29.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `49525.57`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL Apr 2026.xlsx | Page1_1 | 909 | The Bank of Nova Scotia | 49525.57 | Wire | 040726/49525.57 | 2026-04-24 |

### 10. IMS-2026-05-R11

- IMS source: `May 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **11**.
- IMS vendor: Cardinal Comp LLC.
- IMS signed amount: `-252220.15`; SUN target: `252220.15`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-05-07; cleared dates: 2026/05/07.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `252220.15`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL May 2026.xlsx | Page1_1 | 721 | Cardinal Comp LLC | 310920.66 | Wire | 050526/252220.15 | 2026-05-08 |
| data/raw/Paid Invoices for SUN JNL May 2026.xlsx | Page1_1 | 722 | Cardinal Comp LLC | -58700.51 | Wire | 050526/252220.15 | 2026-05-08 |

### 11. IMS-2026-05-R57

- IMS source: `May 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **57**.
- IMS vendor: Gallagher Bassett Services, Inc..
- IMS signed amount: `-165000.0`; SUN target: `165000.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-05-27; cleared dates: 2026/05/27.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `165000`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL May 2026.xlsx | Page1_1 | 636 | Gallagher Bassett Services, Inc. | 165000 | Wire | 00001 | 2026-05-28 |

### 12. IMS-2026-06-R37

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **37**.
- IMS vendor: Federal Motor Carrier Safety Adminstration.
- IMS signed amount: `-560.0`; SUN target: `560.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-09; cleared dates: 2026/06/08.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `560`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 680 | Federal Motor Carrier Safety Adminstration | 560 | ACH | 050726/560.00 | 2026-06-10 |

### 13. IMS-2026-06-R42

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **42**.
- IMS vendor: Idaho Department of Insurance.
- IMS signed amount: `-17850.0`; SUN target: `17850.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-11; cleared dates: 2026/06/12.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `17850`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 690 | Idaho Department of Insurance | 8 | ACH | 2026EST23752 | 2026-06-12 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1098 | Idaho Department of Insurance | 17842 | ACH | 2026EST23752 | 2026-06-12 |

### 14. IMS-2026-06-R45

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **45**.
- IMS vendor: NAIC SERFF.
- IMS signed amount: `-96.0`; SUN target: `96.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-11; cleared dates: 2026/06/01\|2026/06/02.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `96`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 733 | NAIC SERFF | 25 | ACH | 06.01.2026 AIC | 2026-06-12 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 736 | NAIC SERFF | 71 | ACH | 06.02.2026 AIC | 2026-06-12 |

### 15. IMS-2026-06-R49

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **49**.
- IMS vendor: State of California Department of Insurance.
- IMS signed amount: `-10299.75`; SUN target: `10299.75`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-11; cleared dates: 2026/06/09.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `10299.75`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1208 | State of California Department of Insurance | 10299.75 | ACH | Pro-666167 | 2026-06-12 |

### 16. IMS-2026-06-R54

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **54**.
- IMS vendor: Delaware Department of Insurance.
- IMS signed amount: `-16084.41`; SUN target: `16084.41`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-11; cleared dates: 2026/06/10.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `16084.41`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 678 | Delaware Department of Insurance | 17.5 | ACH | Q2 2026 DE PT 23752 | 2026-06-15 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1085 | Delaware Department of Insurance | 16066.91 | ACH | Q2 2026 DE PT 23752 | 2026-06-15 |

### 17. IMS-2026-06-R55

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **55**.
- IMS vendor: State of Indiana Department of Insurance.
- IMS signed amount: `-45328.5`; SUN target: `45328.5`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-11; cleared dates: 2026/06/10.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `45328.5`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 811 | State of Indiana Department of Insurance | 17.5 | ACH | Q2 2026 IN PT 23752 | 2026-06-15 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1151 | State of Indiana Department of Insurance | 45311 | ACH | Q2 2026 IN PT 23752 | 2026-06-15 |

### 18. IMS-2026-06-R57

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **57**.
- IMS vendor: Maryland Insurance Administration.
- IMS signed amount: `-70429.63`; SUN target: `70429.63`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-11; cleared dates: 2026/06/10.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `70429.63`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 7 | Maryland Insurance Administration | 17.5 | ACH | MD 2026 Q2 Estimated PT Payment_AIC | 2026-06-15 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 8 | Maryland Insurance Administration | 70412.13 | ACH | MD 2026 Q2 Estimated PT Payment_AIC | 2026-06-15 |

### 19. IMS-2026-06-R63

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **63**.
- IMS vendor: California Department of Insurance.
- IMS signed amount: `-169088.0`; SUN target: `169088.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-16; cleared dates: 2026/06/15.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `169088`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1075 | California Department of Insurance | 169088 | ACH | CA 2025 Ocean Marine Tax Return_AIC | 2026-06-17 |

### 20. IMS-2026-06-R64

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **64**.
- IMS vendor: Minnesota Revenue.
- IMS signed amount: `-28530.0`; SUN target: `28530.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-16; cleared dates: 2026/06/15.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `28530`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1123 | Minnesota Revenue | 28530 | ACH | MN 2026 Q2 Est PT_AIC | 2026-06-17 |

### 21. IMS-2026-06-R65

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **65**.
- IMS vendor: Commonwealth of Massachusetts.
- IMS signed amount: `-166787.0`; SUN target: `166787.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-16; cleared dates: 2026/06/15.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `166787`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1077 | Commonwealth of Massachusetts | 1432 | ACH | MA 2026 Q2 Est PT_AIC | 2026-06-17 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1078 | Commonwealth of Massachusetts | 165355 | ACH | MA 2026 Q2 Est PT_AIC | 2026-06-17 |

### 22. IMS-2026-06-R66

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **66**.
- IMS vendor: CT Commissioner of Revenue Services.
- IMS signed amount: `-106142.0`; SUN target: `106142.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-16; cleared dates: 2026/06/15.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `106142`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1073 | CT Commissioner of Revenue Services | 106142 | ACH | CT 2026 Q2 Est PT_AIC | 2026-06-17 |

### 23. IMS-2026-06-R67

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **67**.
- IMS vendor: Florida Department of Revenue.
- IMS signed amount: `-214023.84`; SUN target: `214023.84`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-16; cleared dates: 2026/06/15.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `214023.84`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 609 | Florida Department of Revenue | 250 | ACH | FL Q2 2026 Est PT_AIC | 2026-06-17 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1062 | Florida Department of Revenue | 232 | ACH | FL Q2 2026 Est PT_AIC | 2026-06-17 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1090 | Florida Department of Revenue | 213541.84 | ACH | FL Q2 2026 Est PT_AIC | 2026-06-17 |

### 24. IMS-2026-06-R90

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **90**.
- IMS vendor: Minnesota Department of Public Safety.
- IMS signed amount: `-4401.0`; SUN target: `4401.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-18; cleared dates: 2026/06/16.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `4401`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 716 | Minnesota Department of Public Safety | 1 | ACH | MN 2026 Fraud Prevention Assessment AIC | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1186 | Minnesota Department of Public Safety | 4400 | ACH | MN 2026 Fraud Prevention Assessment AIC | 2026-06-25 |

### 25. IMS-2026-06-R114

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **114**.
- IMS vendor: Federal Motor Carrier Safety Adminstration.
- IMS signed amount: `-10.0`; SUN target: `10.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/22.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `10`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 681 | Federal Motor Carrier Safety Adminstration | 10 | ACH | 206910 | 2026-06-25 |

### 26. IMS-2026-06-R116

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **116**.
- IMS vendor: West Virginia Offices of the Insurance Commissioner.
- IMS signed amount: `-1067.5`; SUN target: `1067.5`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/22.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `1067.5`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 825 | West Virginia Offices of the Insurance Commissioner | 17.5 | ACH | WV 2026 Exam Assmt AIC | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1220 | West Virginia Offices of the Insurance Commissioner | 1050 | ACH | WV 2026 Exam Assmt AIC | 2026-06-25 |

### 27. IMS-2026-06-R117

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **117**.
- IMS vendor: Missouri Department of Commerce & Insurance.
- IMS signed amount: `-2000.5`; SUN target: `2000.5`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/22.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `2000.5`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 624 | Missouri Department of Commerce & Insurance | 2000 | ACH | MO 2026 Ann Renewal, Filing Fee_AIC | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 722 | Missouri Department of Commerce & Insurance | 0.5 | ACH | MO 2026 Ann Renewal, Filing Fee_AIC | 2026-06-25 |

### 28. IMS-2026-06-R119

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **119**.
- IMS vendor: NAIC.
- IMS signed amount: `-2105.0`; SUN target: `2105.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/17\|2026/06/18.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `2105.0`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 726 | NAIC | 17.5 | ACH | HI 2026 May Est PT Payment AIC | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 730 | NAIC | 17.5 | ACH | NY 2026 May MVLEF Fee AIC | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1065 | NAIC | 2070 | ACH | NY 2026 May MVLEF Fee AIC | 2026-06-25 |

### 29. IMS-2026-06-R122

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **122**.
- IMS vendor: State of Wisconsin.
- IMS signed amount: `-84730.5`; SUN target: `84730.5`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/17\|2026/06/18.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `84730.5`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 816 | State of Wisconsin | 17.5 | ACH | WI 2026 Q2 Est PT_AIC | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1156 | State of Wisconsin | 84713 | ACH | WI 2026 Q2 Est PT_AIC | 2026-06-25 |

### 30. IMS-2026-06-R124

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **124**.
- IMS vendor: Insurance Commissioner - State of Washington.
- IMS signed amount: `-66067.0`; SUN target: `66067.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/23.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `66067`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1103 | Insurance Commissioner - State of Washington | 66067 | ACH | WA 2026 Q1 Est PT Payments_AIC | 2026-06-25 |

### 31. IMS-2026-06-R125

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **125**.
- IMS vendor: MS Department of Revenue.
- IMS signed amount: `-85737.75`; SUN target: `85737.75`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/17.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `85737.75`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1117 | MS Department of Revenue | 85737.75 | ACH | MS 2026 Q2 Est PT Payment_AIC | 2026-06-25 |

### 32. IMS-2026-06-R126

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **126**.
- IMS vendor: Kentucky State Treasurer.
- IMS signed amount: `-5286.0`; SUN target: `5286.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/18.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `5286`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1063 | Kentucky State Treasurer | 5286 | ACH | KY 2026 May Monthly Surcharge Report_AIC | 2026-06-25 |

### 33. IMS-2026-06-R129

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **129**.
- IMS vendor: Maryland Insurance Administration.
- IMS signed amount: `-1500.0`; SUN target: `1500.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/17.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `1500`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 618 | Maryland Insurance Administration | 1500 | ACH | MD 2026 COA Annual Renewal and Fraud Fee AIC | 2026-06-25 |

### 34. IMS-2026-06-R130

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **130**.
- IMS vendor: State of California - Department of Insurance.
- IMS signed amount: `-475.0`; SUN target: `475.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/18.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `475`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 627 | State of California - Department of Insurance | 475 | ACH | CA 2025 Fin Review_AIC | 2026-06-25 |

### 35. IMS-2026-06-R131

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **131**.
- IMS vendor: Vertafore Inc.
- IMS signed amount: `-3610.0`; SUN target: `3610.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/18\|2026/06/22.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `3610`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 820 | Vertafore Inc | 10 | ACH | 5679704 | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1213 | Vertafore Inc | 3600 | ACH | NV 2026 Annual Admin and Enf Fee AIC | 2026-06-25 |

### 36. IMS-2026-06-R133

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **133**.
- IMS vendor: Illinois Director of Insurance.
- IMS signed amount: `-22500.5`; SUN target: `22500.5`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/18.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `22500.5`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 701 | Illinois Director of Insurance | 0.5 | ACH | IL 2026 Fin Regulation Fee_AIC | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1181 | Illinois Director of Insurance | 22500 | ACH | IL 2026 Fin Regulation Fee_AIC | 2026-06-25 |

### 37. IMS-2026-06-R137

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **137**.
- IMS vendor: Virginia Department of Taxation.
- IMS signed amount: `-88231.0`; SUN target: `88231.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/17.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `88231`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1162 | Virginia Department of Taxation | 88231 | ACH | VA 2026 Q2 Est PT_AIC | 2026-06-25 |

### 38. IMS-2026-06-R138

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **138**.
- IMS vendor: Treasurer - State of Ohio.
- IMS signed amount: `-175.0`; SUN target: `175.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/18.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `175`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 632 | Treasurer - State of Ohio | 175 | ACH | OH 2026 Annual COA Renewal AIC | 2026-06-25 |

### 39. IMS-2026-06-R139

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **139**.
- IMS vendor: NIPR.
- IMS signed amount: `-45253.05`; SUN target: `45253.05`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/22.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `45253.05`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 759 | NIPR | 19200 | ACH | NRAR731027 | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 760 | NIPR | 192 | ACH | NRAR731027 | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 773 | NIPR | 1920 | ACH | NRNE722534 | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 774 | NIPR | 19.2 | ACH | NRNE722534 | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 779 | NIPR | 17760 | ACH | NRVT736629 | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 780 | NIPR | 177.6 | ACH | NRVT736629 | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 791 | NIPR | 5925 | ACH | NRWV738078 | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 792 | NIPR | 59.25 | ACH | NRWV738078 | 2026-06-25 |

### 40. IMS-2026-06-R147

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **147**.
- IMS vendor: Treasurer, State of Maine.
- IMS signed amount: `-29351.0`; SUN target: `29351.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-24; cleared dates: 2026/06/17.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `29351`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1158 | Treasurer, State of Maine | 116 | ACH | ME 2026 J une Estimated Fire Tax AIC | 2026-06-25 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 1161 | Treasurer, State of Maine | 29235 | ACH | ME 2026 Q2 Estimated PT Payment_AIC | 2026-06-25 |

### 41. IMS-2026-06-R150

- IMS source: `June 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **150**.
- IMS vendor: Kansas Division of Workers Compensation.
- IMS signed amount: `-338.45`; SUN target: `338.45`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-06-25; cleared dates: 2026/06/17.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `338.45`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 705 | Kansas Division of Workers Compensation | 1.25 | ACH | KS 2026 WC Op Ex Assmt_AIC | 2026-06-26 |
| data/raw/Paid Invoices for SUN JNL June 2026.xlsx | Page1_1 | 829 | Kansas Division of Workers Compensation | 337.2 | ACH | KS 2026 WC Op Ex Assmt_AIC | 2026-06-26 |

### 42. IMS-2026-07-R25

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **25**.
- IMS vendor: NAIC SERFF.
- IMS signed amount: `-1510.0`; SUN target: `1510.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-09; cleared dates: 2026/07/01\|2026/07/02.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `1510`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 621 | NAIC SERFF | 1468 | ACH | 07.01.2026 AIC | 2026-07-09 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 625 | NAIC SERFF | 42 | ACH | 07.02.2026 AIC | 2026-07-09 |

### 43. IMS-2026-07-R33

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **33**.
- IMS vendor: New Mexico Taxation and Revenue Department.
- IMS signed amount: `-10781.92`; SUN target: `10781.92`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/08.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `10781.92`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 739 | New Mexico Taxation and Revenue Department | 10781.92 | ACH | NM 2026 Q2 Premium AIC | 2026-07-13 |

### 44. IMS-2026-07-R34

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **34**.
- IMS vendor: Vertafore Inc.
- IMS signed amount: `-2000.0`; SUN target: `2000.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/08.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `2000`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 1080 | Vertafore Inc | 2000 | ACH | NV 1377173 AIC | 2026-07-13 |

### 45. IMS-2026-07-R36

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **36**.
- IMS vendor: Michigan Department of Treasury.
- IMS signed amount: `-215937.0`; SUN target: `215937.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/08.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `215937`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 564 | Michigan Department of Treasury | 215937 | ACH | MI 2026 Q2 AIC | 2026-07-13 |

### 46. IMS-2026-07-R38

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **38**.
- IMS vendor: WNGATES.COM.
- IMS signed amount: `-395.0`; SUN target: `395.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/07.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `395`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 1119 | WNGATES.COM | 95 | ACH | 06252026001 | 2026-07-13 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 1121 | WNGATES.COM | 300 | ACH | 06252026019 | 2026-07-13 |

### 47. IMS-2026-07-R40

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **40**.
- IMS vendor: New York State Department of Financial Services.
- IMS signed amount: `-3088.25`; SUN target: `3088.25`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/09.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `3088.25`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 743 | New York State Department of Financial Services | 3070.75 | ACH | NY Q2 26 Fire Ins Fee AIC | 2026-07-13 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 744 | New York State Department of Financial Services | 17.5 | ACH | NY Q2 26 Fire Ins Fee AIC | 2026-07-13 |

### 48. IMS-2026-07-R41

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **41**.
- IMS vendor: MS Department of Revenue.
- IMS signed amount: `-78899.1`; SUN target: `78899.1`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/09.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `78899.1`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 602 | MS Department of Revenue | 78899.1 | ACH | MS 2026 Q3 Est PT Pmt_AIC | 2026-07-13 |

### 49. IMS-2026-07-R43

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **43**.
- IMS vendor: Kentucky State Treasurer.
- IMS signed amount: `-659.0`; SUN target: `659.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/09.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `659`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 438 | Kentucky State Treasurer | 659 | ACH | KY 2026 June Surchg Rpt AIC | 2026-07-13 |

### 50. IMS-2026-07-R44

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **44**.
- IMS vendor: City of Chicago.
- IMS signed amount: `-5359.0`; SUN target: `5359.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/09.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `5359`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 180 | City of Chicago | 5359 | ACH | IL 2026 City of Chicago Foreign Fire Ins Tax_AIC | 2026-07-13 |

### 51. IMS-2026-07-R45

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **45**.
- IMS vendor: District of Columbia Life and Health Insurance Guaranty Association.
- IMS signed amount: `-117.5`; SUN target: `117.5`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/09.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `117.5`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 293 | District of Columbia Life and Health Insurance Guaranty Association | 100 | ACH | 23752DHCF2026 | 2026-07-13 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 294 | District of Columbia Life and Health Insurance Guaranty Association | 17.5 | ACH | 23752DHCF2026 | 2026-07-13 |

### 52. IMS-2026-07-R46

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **46**.
- IMS vendor: West Virginia Life and Health Insurance Guaranty Association.
- IMS signed amount: `-401.59`; SUN target: `401.59`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-10; cleared dates: 2026/07/09.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `401.59`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 1101 | West Virginia Life and Health Insurance Guaranty Association | 400 | ACH | WV 2026 LHIGA Class A Assmnt AIC | 2026-07-13 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 1102 | West Virginia Life and Health Insurance Guaranty Association | 1.59 | ACH | WV 2026 LHIGA Class A Assmnt AIC | 2026-07-13 |

### 53. IMS-2026-07-R57

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **57**.
- IMS vendor: DCCA, State of Hawaii.
- IMS signed amount: `-17.5`; SUN target: `17.5`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-14; cleared dates: 2026/07/10.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `17.5`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 280 | DCCA, State of Hawaii | 17.5 | ACH | HI Jun26 FEE AIC | 2026-07-15 |

### 54. IMS-2026-07-R61

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **61**.
- IMS vendor: Michigan Dept of Insurance & Financial Services.
- IMS signed amount: `-6804.0`; SUN target: `6804.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-14; cleared dates: 2026/07/10.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `6804`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 570 | Michigan Dept of Insurance & Financial Services | 6804 | ACH | MI 2026 Reg Assmt Fee_AIC | 2026-07-15 |

### 55. IMS-2026-07-R67

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **67**.
- IMS vendor: The Bank of Nova Scotia.
- IMS signed amount: `-50811.05`; SUN target: `50811.05`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-16; cleared dates: 2026/07/16.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `50811.05`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 1032 | The Bank of Nova Scotia | 50811.05 | Wire | 071026/50811.05 | 2026-07-17 |

### 56. IMS-2026-07-R70

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **70**.
- IMS vendor: Insurance Commissioner - State of Washington.
- IMS signed amount: `-7774.0`; SUN target: `7774.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-16; cleared dates: 2026/07/15.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `7774`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 412 | Insurance Commissioner - State of Washington | 382 | ACH | WA 2026 Fraud Surcharge_AIC | 2026-07-20 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 414 | Insurance Commissioner - State of Washington | 7392 | ACH | WA 2026 Reg Surchg Assmt AIC | 2026-07-20 |

### 57. IMS-2026-07-R88

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **88**.
- IMS vendor: NAIC SERFF.
- IMS signed amount: `-83.0`; SUN target: `83.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-22; cleared dates: 2026/07/15.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `83`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 634 | NAIC SERFF | 83 | ACH | 07.15.2026 AIC | 2026-07-23 |

### 58. IMS-2026-07-R113

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **113**.
- IMS vendor: State of Idaho.
- IMS signed amount: `-1010.0`; SUN target: `1010.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-23; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `1010`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 960 | State of Idaho | 1010 | ACH | 23752 - IC-4008 2026 1st Half | 2026-07-27 |

### 59. IMS-2026-07-R132

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **132**.
- IMS vendor: Utah State Tax Commission.
- IMS signed amount: `-33447.0`; SUN target: `33447.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `33447`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 1076 | Utah State Tax Commission | 33447 | ACH | UT 2026 Q2 Est PT Pmts_AIC | 2026-07-30 |

### 60. IMS-2026-07-R134

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **134**.
- IMS vendor: Illinois Department of Insurance.
- IMS signed amount: `-55142.04`; SUN target: `55142.04`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `55142.04`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 389 | Illinois Department of Insurance | 55141.54 | ACH | IL 2026 IC Ops Fund Surchg_AIC | 2026-07-30 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 390 | Illinois Department of Insurance | 0.5 | ACH | IL 2026 IC Ops Fund Surchg_AIC | 2026-07-30 |

### 61. IMS-2026-07-R135

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **135**.
- IMS vendor: State Comptroller.
- IMS signed amount: `-575225.01`; SUN target: `575225.01`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `575225.01`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 956 | State Comptroller | 566226.84 | ACH | TX 2026 2nd Instllmt Est PT_AIC | 2026-07-30 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 957 | State Comptroller | 8998.17 | ACH | TX 26 Vol Fire Dept Assist Fund Assmt AIC | 2026-07-30 |

### 62. IMS-2026-07-R137

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **137**.
- IMS vendor: NAIC SERFF.
- IMS signed amount: `-4079.0`; SUN target: `4079.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/28.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `4079`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 650 | NAIC SERFF | 4079 | ACH | 07.28.2026 AIC | 2026-07-30 |

### 63. IMS-2026-07-R138

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **138**.
- IMS vendor: MN Dept of Labor & Industry-Financial Services.
- IMS signed amount: `-3190.13`; SUN target: `3190.13`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `3190.13`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 594 | MN Dept of Labor & Industry-Financial Services | 3190.13 | ACH | MN 2026 1st Half SCF Assmt_AIC | 2026-07-30 |

### 64. IMS-2026-07-R139

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **139**.
- IMS vendor: Division of Workers Compensation.
- IMS signed amount: `-21959.99`; SUN target: `21959.99`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/23.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `21959.99`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 298 | Division of Workers Compensation | 21959.99 | ACH | FL 2026 Q2 WCATF & SDTF Assmt_AIC | 2026-07-30 |

### 65. IMS-2026-07-R140

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **140**.
- IMS vendor: Kentucky Workers’ Compensation Funding Commission.
- IMS signed amount: `-10798.21`; SUN target: `10798.21`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/23.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `10798.21`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 445 | Kentucky Workers’ Compensation Funding Commission | 10798.21 | ACH | KY 2026 Q2 WC Funding Prem Rpt_AIC | 2026-07-30 |

### 66. IMS-2026-07-R141

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **141**.
- IMS vendor: Arizona Automobile Theft Authority.
- IMS signed amount: `-32.5`; SUN target: `32.5`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/23.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `32.5`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 70 | Arizona Automobile Theft Authority | 15 | ACH | AZ 2026 1st Half Auto Theft Auth Assmt AIC | 2026-07-30 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 71 | Arizona Automobile Theft Authority | 17.5 | ACH | AZ 2026 1st Half Auto Theft Auth Assmt AIC | 2026-07-30 |

### 67. IMS-2026-07-R142

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **142**.
- IMS vendor: Compensation Advisory Org of Michigan (CAOM).
- IMS signed amount: `-926.45`; SUN target: `926.45`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/22.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `926.45`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 270 | Compensation Advisory Org of Michigan (CAOM) | 926.45 | ACH | MI 2026 Q3 CAOM Assmt_AIC | 2026-07-30 |

### 68. IMS-2026-07-R143

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **143**.
- IMS vendor: Division of Workers' Compensation.
- IMS signed amount: `-15905.15`; SUN target: `15905.15`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/23.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `15905.15`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 305 | Division of Workers' Compensation | 15904.15 | ACH | CO 2026 1st Half WC Surchg Form_AIC | 2026-07-30 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 306 | Division of Workers' Compensation | 1 | ACH | CO 2026 1st Half WC Surchg Form_AIC | 2026-07-30 |

### 69. IMS-2026-07-R144

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **144**.
- IMS vendor: Melrose Park Fire Department.
- IMS signed amount: `-172.15`; SUN target: `172.15`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `172.15`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 554 | Melrose Park Fire Department | 172.15 | ACH | IL 2025 Foreign Fire Tax LOCAL GOV - Various AIC | 2026-07-30 |

### 70. IMS-2026-07-R145

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **145**.
- IMS vendor: Michigan Workers Compensation Placement Facility.
- IMS signed amount: `-900.99`; SUN target: `900.99`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/22.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `900.99`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 575 | Michigan Workers Compensation Placement Facility | 900.99 | ACH | MI 2026 Q3 MWCPF Assmt_AIC | 2026-07-30 |

### 71. IMS-2026-07-R146

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **146**.
- IMS vendor: Industrial Commission of Arizona.
- IMS signed amount: `-5266.07`; SUN target: `5266.07`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/23.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `5266.07`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 399 | Industrial Commission of Arizona | 5266.07 | ACH | AZ 2026 Q2 WC Est PT_AIC | 2026-07-30 |

### 72. IMS-2026-07-R147

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **147**.
- IMS vendor: Office of Commissioner, Attn: IFO Division.
- IMS signed amount: `-728326.7`; SUN target: `728326.7`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/28.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `728326.7`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 766 | Office of Commissioner, Attn: IFO Division | 728321.7 | ACH | GA 2026 Municipal Premium Tax AIC | 2026-07-30 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 767 | Office of Commissioner, Attn: IFO Division | 5 | ACH | GA 2026 Municipal Premium Tax AIC | 2026-07-30 |

### 73. IMS-2026-07-R148

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **148**.
- IMS vendor: Nevada Department of Taxation.
- IMS signed amount: `-136719.71`; SUN target: `136719.71`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `136719.71`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 728 | Nevada Department of Taxation | 136719.71 | ACH | NV 2026 Q2 Est P&I Pmt_AIC | 2026-07-30 |

### 74. IMS-2026-07-R149

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **149**.
- IMS vendor: Joliet Fire Department.
- IMS signed amount: `-242.6`; SUN target: `242.6`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `242.6`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 433 | Joliet Fire Department | 242.6 | ACH | IL 2025 Foreign Fire Tax LOCAL GOV - Various AIC | 2026-07-30 |

### 75. IMS-2026-07-R150

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **150**.
- IMS vendor: Colorado Divison of Insurance.
- IMS signed amount: `-61668.5`; SUN target: `61668.5`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `61668.5`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 262 | Colorado Divison of Insurance | 61651 | ACH | CO 2026 Q2 Est PT Pmt AIC | 2026-07-30 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 263 | Colorado Divison of Insurance | 17.5 | ACH | CO 2026 Q2 Est PT Pmt AIC | 2026-07-30 |

### 76. IMS-2026-07-R151

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **151**.
- IMS vendor: Treasurer, State of Maine.
- IMS signed amount: `-11.0`; SUN target: `11.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-29; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_ONE`; matched SUN allocation sum: `11`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 1062 | Treasurer, State of Maine | 11 | ACH | ME 2026 July Est Fire Tax AIC | 2026-07-30 |

### 77. IMS-2026-07-R153

- IMS source: `July 2026 Resource Pro Cash.xlsx` / `AIC IMS` / row **153**.
- IMS vendor: Massachusetts Department of Industrial Accidents.
- IMS signed amount: `-3898.0`; SUN target: `3898.0`.
- IMS payment type: Direct Debit; check/reference: `<blank>`.
- IMS transaction date: 2026-07-30; cleared dates: 2026/07/24.
- Original failure: `SUN_EVIDENCE_CONFLICT`; all original reasons: `SUN_EVIDENCE_CONFLICT`.
- Shadow method: `ONE_TO_MANY`; matched SUN allocation sum: `3898.00`.

| SUN source file | Sheet | Row | Vendor | Amount | Payment type raw | Transaction reference | Paid date |
|---|---|---|---|---|---|---|---|
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 545 | Massachusetts Department of Industrial Accidents | 1006.27 | ACH | MA 2026 Q2 PTF & SF Assmt_AIC | 2026-07-30 |
| data/raw/Paid Invoices for SUN JNL July 2026.xlsx | Page1_1 | 546 | Massachusetts Department of Industrial Accidents | 2891.73 | ACH | MA 2026 Q2 PTF & SF Assmt_AIC | 2026-07-30 |

## Safeguards and reproducibility

- Current in-memory outcomes/methods/reasons/selected evidence were checked against existing historical production results for all 731 eligible rows.
- Current and shadow IMS source records, candidate row sets/order, reconciled amounts, differences, rankings, and evidence-reuse conflicts were asserted identical. Only agreement flags and resulting decision reasons/statuses changed.
- Final verified SUN source-row identities were checked unique independently in each run. No same-month void participates in either run.
- The original production `payment_agrees` function object remains unchanged. No matching or sanitizer source file was written. The shadow override existed only inside this diagnostic process.
- All existing files under `data/processed/` and the three production component source files were SHA256-checked before and after creating this report. The report is the only new diagnostic artifact.

Input/source SHA256 fingerprints:

| Path | SHA256 |
|---|---|
| /workspaces/ascot-reconciliation-prototype/src/ascot/verify_ims_sun.py | e57bcc71b42afba92175b2ebeceb1c3966ddaa7738d5e7ccadf0e1cbc754d28e |
| data/processed/aic_ims_all_months_transactions.csv | 48366280960dd6add389270319aca7d41f0541701ae7fce16f7e28e818ed551d |
| data/processed/sun_jnl/sun_jnl_2026-01.csv | d3fdee031ab4469782621517dea1f707c2bf32a5368ce7dcff98020a079574da |
| data/processed/sun_jnl/sun_jnl_2026-02.csv | 2b5abd8b5035a81c002913eb112c88cf5ed5f9db7f8094c1ac5ed040a0580498 |
| data/processed/sun_jnl/sun_jnl_2026-03.csv | c7b32364ccc6913e6f300bceb09a562ab17cbb554c1a9bb591c1d6fe77a42410 |
| data/processed/sun_jnl/sun_jnl_2026-04.csv | fce456634179923a13ccc3c3ac7134b7f019d0012d02b504ef7c0c76bfce15be |
| data/processed/sun_jnl/sun_jnl_2026-05.csv | 3ec7894e2c95f2244c9c99fa38c427c832bfe71f4e339326d3eef2bc2bce9f00 |
| data/processed/sun_jnl/sun_jnl_2026-06.csv | 372df7a984cad0636ebb1016df74647206a6d61a5dc24edd5e5ab0268a1ec5d6 |
| data/processed/sun_jnl/sun_jnl_2026-07.csv | 347cf75f05333139da72378f2f330c655f3a3e2bfe18610e63c06980d672e883 |

This analysis measures sensitivity only. It does not establish that payment methods are interchangeable or authorize relaxing production identity controls.
