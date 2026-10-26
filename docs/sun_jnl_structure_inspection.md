# SUN JNL structure inspection: January–July 2026

This report records the completed inspection of seven workbooks and all 31 worksheets in `data/raw`. It uses only those inspection findings. No sanitizer or IMS matching logic was implemented. Row counts below are populated transaction/detail rows, excluding headers and report titles; they are not unique payment counts.

## Files, worksheets, and header rows

Every worksheet is visible and contains transaction-like data. `Page1_1` contains the full population in every month. Other sheets are projections, company extracts, or edited working copies; their rows should not simply be appended together.

All filenames below are relative to `data/raw/`.

| Workbook | Worksheet: header row / detail rows |
|---|---|
| `Paid Invoices for SUN JNL January 2026.xlsx` | `Page1_1`: **1 / 731**; `AIC 2693`: 1 / 64; `AUI 0568`: 1 / 9; `ASC 6620`: 1 / 1; `ASI Re 8443`: 1 / 13; `AIC Re 8427`: 1 / 10 |
| `Paid Invoices for SUN JNL February 2026.xlsx` | `Page1_1`: **4 / 675**; `ASI Rein Concur Feb`: 1 / 7; `AUI Concur Feb`: 4 / 12; `AIC Rein Concur Feb`: 4 / 8; `AIC Concur Feb`: 1 / 59; `ASC Concur Feb`: 1 / 11 |
| `Paid Invoices for SUN JNL Mar 2026.xlsx` | `Page1_1`: **4 / 768**; `ASI Reins`: 5 / 46; `AIC Reins`: 5 / 56; `ASI Disb`: 1 / 768; `ASC`: 4 / 16 |
| `Paid Invoices for SUN JNL Apr 2026.xlsx` | `Page1_1`: **4 / 919** |
| `Paid Invoices for SUN JNL May 2026.xlsx` | `Page1_1`: **4 / 809**; `Sheet1`: 1 / 809; `AIC`: 1 / 51 |
| `Paid Invoices for SUN JNL June 2026.xlsx` | `Page1_1`: **4 / 1,244**; `Sheet1`: 1 / 1,244; `AUI`: 1 / 14; `ASC`: 1 / 76; `AIC`: 1 / 164; `ASI`: 1 / 35; `ASI Re`: 1 / 89 |
| `Paid Invoices for SUN JNL July 2026.xlsx` | `Page1_1`: **5 / 1,130**; `Sheet1`: 1 / 1,130; `AIC Reins`: 1 / 5 |

## Stable columns and month-specific schemas

The baseline main-report structure consists of these 24 columns, in source order:

```text
Layout Identifier, Account, Description, CCY , Amount, D/C,
Paid Date, Trans Date, Trans Ref, Period, T0 YOA, T1 Trust Fund,
T2 Class, T3 Cost Center, T4 Inter Co, T5 VAT, T6 LCA, T8 Emp,
LOC, Company, Bank Account Name, Bank Account Code,
Line Description, Payment Type
```

These fields persist across all seven main reports, allowing for the bank-header aliases below. Presence does not imply population: several dimensions are entirely blank.

| Months | Main-report schema and header differences |
|---|---|
| January | Baseline 24 columns. Header row 1; no report preamble. |
| February–March | 28 columns. Add `Request Total` and `Tax Amount` before `Amount`; add `Payment Amount` and `VAT Amount` after it. Later columns shift accordingly. Header row 4. |
| April–June | Baseline 24 columns, with bank headers renamed to `Bank Account Name (Custom 9)` and `Bank Account Code (Custom 9)`. Header row 4. |
| July | 26 columns. April–June structure plus `VAT Amount ` and `Total Amount` immediately after `Amount`. Later columns shift again. Header row 5, following a blank row 4. |

Whitespace is literal: `CCY ` has a trailing space, as does July's `VAT Amount `.

### Columns in additional worksheets

Column names below use the baseline names, with the applicable monthly bank-header suffix.

| Sheets | Columns |
|---|---|
| January `AIC 2693`; March `ASI Disb`; June `Sheet1`, `ASC`, `ASI`, `ASI Re`; July `Sheet1` | Respective monthly full-report columns minus `Layout Identifier`. |
| February `AUI Concur Feb`, `AIC Rein Concur Feb`, `AIC Concur Feb` | Full February 28-column structure. |
| January `AUI 0568` | `Account, Description, Amount, Paid Date, Trans Ref, T1 Trust Fund, T3 Cost Center, T4 Inter Co, LOC, Company, Bank Account Name, Line Description, Payment Type` |
| January `ASC 6620`, `ASI Re 8443`, `AIC Re 8427`; February `ASI Rein Concur Feb`, `ASC Concur Feb` | `Account, Description, Amount, Paid Date, T1 Trust Fund, T3 Cost Center, T4 Inter Co, LOC, Company, Bank Account Name, Line Description, Payment Type`, followed by an unnamed helper column. |
| March `ASI Reins` | `Account, Description, Amount, Paid Date, T1 Trust Fund, T3 Cost Center, LOC, Company, Bank Account Name, Line Description, Payment Type` |
| March `AIC Reins` | `Account, Description, Amount, Paid Date, Trans Ref, T1 Trust Fund, T3 Cost Center, LOC, Company, Bank Account Name, Bank Account Code, Line Description, Payment Type` |
| March `ASC` | `Layout Identifier, Account, Description, Payment Amount, Paid Date, Trans Ref, T1 Trust Fund, T3 Cost Center, LOC, Company, Bank Account Name, Bank Account Code, Line Description, Payment Type` |
| May `Sheet1` | `Account, Description, Amount, Paid Date, Trans Ref, Period, T1 Trust Fund, T3 Cost Center, T4 Inter Co, LOC, Company, Bank Account Name (Custom 9), Line Description, Payment Type` |
| May `AIC` | `Account, Description, Amount, Paid Date, T1 Trust Fund, T3 Cost Center, Company, Line Description, Payment Type` |
| June `AUI` | `Account, Description, CCY , Amount, Paid Date, Trans Ref, Period, T1 Trust Fund, T3 Cost Center, LOC, Company, Bank Account Name (Custom 9), Bank Account Code (Custom 9), Line Description, Payment Type` |
| June `AIC` | `Account, Description, Amount, Paid Date, Trans Ref, T1 Trust Fund, T3 Cost Center, LOC, Company, Line Description, Payment Type`, followed by an unnamed helper column. |
| July `AIC Reins` | `Account, Description, CCY , Amount, VAT Amount , Total Amount, D/C, Paid Date, Trans Ref, Period, T1 Trust Fund, T3 Cost Center, LOC, Company, Bank Account Name (Custom 9), Bank Account Code (Custom 9), Line Description, Payment Type` |

## Transaction-row structure

The underlying invoice allocation-line structure is consistent across months, while exported schemas and working sheets vary. An invoice/payment can span multiple account or cost-center lines, including negative allocations. Detail-row counts therefore do not represent unique invoices or payments.

February–March request/payment totals repeat across allocation lines. July `Total Amount` likewise repeats across split lines and can include tax. For example, July contains `Amount=30`, `VAT Amount=1.90`, `Total Amount=31.90`. These fields are not interchangeable or safely additive at every grain.

`Description` contains supplier/payee names. `Line Description` contains supporting narratives. `Trans Ref` is populated text throughout the main reports, including numeric-looking invoice numbers, alphanumeric references, rent labels, and date/amount combinations. `Paid Date` contains actual Excel dates; `Trans Date` is entirely blank.

No internal blank sections, subtotals, merged transaction cells, or obvious continuation-only rows were found.

## Observed AIC-identification fields

The following combinations are consistent in every main report. They describe observed populations, not a permanent filtering rule.

| Company | Bank Account Name | Bank Account Code |
|---|---|---|
| `AIC` | `AIC Disbursements (2693)` | `13012085` |
| `AICRE` | `AIC Reinsurance (8427)` | `13012094` |

| Month | AIC detail rows | AICRE detail rows |
|---|---:|---:|
| January | 64 | 10 |
| February | 59 | 8 |
| March | 107 | 56 |
| April | 77 | 82 |
| May | 51 | 78 |
| June | 164 | 77 |
| July | 190 | 5 |

- `AAIC` also appears, using `AAI Disbursements (4942923194)` / `13012053`. Substring identification would conflate distinct populations.
- Supplier descriptions do not provide a consistent AIC marker. Some line descriptions explicitly mention AIC, alongside claim, premium, tax, fee, and other narratives.
- `T3 Cost Center` varies substantially, including `FINU`, `REGU`, `CLMU`, `GLPQ`, `TRUQ`, and many others. No single AIC-specific value emerged.
- `Payment Type` includes `ACH`, `Wire`, occasional `Direct Debit`, numeric-looking strings, and blanks. Numeric values may represent payment/check identifiers; that interpretation remains unconfirmed.

## Structural and data-quality issues

- **Preambles and merged cells:** February–July main sheets each contain four merged title/page/date ranges above the data. July additionally has blank row 4. February's AUI and AIC reinsurance extracts retain the merged preamble. March extracts contain leading blank rows.
- **Formulas:** No `Page1_1` contains formulas. January's ASC/ASI-reinsurance/AIC-reinsurance sheets and February's ASI-reinsurance/ASC sheets use formulas under `Payment Type` for supplier/narrative text, plus unnamed `LEN` helpers. June `Sheet1` contains 54 formulas; June `AIC` contains 238. Working-sheet headers do not always describe their contents.
- **Edited working copies:** May `AIC` changes two amounts from 12,722.33 to 12,756.01 and from 79,705.00 to 80,614.21. June working sheets fill two missing AIC account codes and change one reference; June `AIC` also changes amounts from 14,546.33 to 14,610.75 and from 950.00 to 1,034.31. July `AIC Reins` changes one supplier name from `Arthur J. Gallagher Risk Management Services` to `Gallagher`. Source-sheet precedence requires an explicit future decision.
- **Misleading sheet names:** March `ASI Disb` contains the entire multi-company population. June `ASI` contains company `ASIC`, while `ASI Re` contains `ASI`.
- **Missing accounts:** June's main report has six missing `Account` values, covering Maryland Insurance Administration lines for ACIC, AIC, and ASC. Other months have none.
- **Missing payment types:** January, February, March, May, June, and July each have one; April has 57.
- **Signed amounts:** Negative-line counts for January–July are 5, 9, 39, 40, 63, 90, and 6. February and May each also have one zero line. Every main-report `D/C` is nevertheless `D`; preserve the numeric sign.
- **Repeated totals:** Request/payment totals and July total amounts can repeat across allocations. Preserve their separate meanings rather than treating them as line amounts.
- **Exact duplicate rows:** Excess full-row duplicate counts are March 1, April 2, and May 1; zero elsewhere. Review these rather than automatically removing them.
- **Empty dimensions:** `Layout Identifier`, `Trans Date`, `Period`, `T0 YOA`, `T2 Class`, `T5 VAT`, `T6 LCA`, and `T8 Emp` are entirely blank in every main report. `T4 Inter Co` is sparsely populated. Currency is always USD.
- **Coverage:** March explicitly reports March 1–27, rather than the full month. June specifies June 1–30 but was generated June 29; its latest paid date is June 26. Full-month completeness cannot be assumed from filenames.
- **Header aliases and types:** Normalize surrounding header whitespace and bank-header aliases. Preserve account codes and transaction references as text; edited June working sheets introduce numeric account values.

## Proposed canonical fields for a future sanitizer

Preserve allocation-line grain and source provenance.

| Group | Proposed fields |
|---|---|
| Provenance | `source_file`, `source_sheet`, `source_row`, `report_run_date`, `report_period_start`, `report_period_end` |
| Core | `account_code`, `description`, `currency`, `amount`, `debit_credit`, `paid_date`, `transaction_date`, `transaction_reference` |
| Identification | `company`, `bank_account_name`, `bank_account_code`, `payment_type_raw` |
| Supporting dimensions | `trust_fund`, `cost_center`, `intercompany`, `location`, `line_description` |
| Separate optional monetary fields | `request_total`, `tax_amount`, `payment_amount`, `vat_amount`, `total_amount` |
| Retained nullable source dimensions | `layout_identifier`, `period`, `year_of_account`, `class`, `vat_code`, `lca`, `employee` |

Normalize header aliases and surrounding whitespace while retaining original values and provenance. Keep line amounts separate from payment/request totals, preserve references and account codes as text, and resolve report-versus-working-sheet precedence before implementation. No permanent AIC filter or IMS matching rule is established by this report.
