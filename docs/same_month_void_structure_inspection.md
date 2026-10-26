# Same Month Void structure inspection: January–July 2026

## Scope and approach

Inspected all 1,099 canonical IMS source transactions in `data/processed/aic_ims_all_months_transactions.csv`, selecting every normalized `cleared_status=same_month_void` (38 rows), each selected row’s two preceding/following source transactions, and all same-period exact opposite amounts. Also inspected normalized IMS rows 108–113 in `aic_ims_all_months_rows.csv` for the June account discrepancy. No SUN data or verification logic was used or changed.

Canonical transaction input SHA256: `48366280960dd6add389270319aca7d41f0541701ae7fce16f7e28e818ed551d`.

Exact Decimal arithmetic was sufficient; no tolerance or rounding was needed to establish these zero sums. Searches for multi-row alternatives were restricted to the named vendor(s) on the flagged outgoing side and same-period outgoing transactions. This is not an exhaustive arbitrary subset search across unrelated monthly transactions, and no business relationship is inferred from a sum alone.

## Monthly population

| Month | Flagged rows | Debit / outgoing rows | Signed net |
|---|---:|---:|---:|
| 2026-01 | 0 | 0 / 0 | 0.00 |
| 2026-02 | 0 | 0 / 0 | 0.00 |
| 2026-03 | 0 | 0 / 0 | 0.00 |
| 2026-04 | 26 | 13 / 13 | 0.00 |
| 2026-05 | 2 | 1 / 1 | 0.00 |
| 2026-06 | 4 | 2 / 2 | 0.00 |
| 2026-07 | 6 | 3 / 3 | 0.00 |

All 38 rows have at least one exact opposite **also labeled `same_month_void`**. The flagged population supports 19 disjoint one-to-one zero-net pair slots. Seventeen pair slots have distinct amounts within that flagged population; the remaining two share April’s 87,822.00 amount, creating alternative assignments. No flagged row lacks a zero-net possibility.

## Every flagged transaction: monetary fields and full-period counterparts

IDs below abbreviate `IMS-2026-MM-Rn` as `MM-Rn`; all source sheets are `AIC IMS` and filenames are `<Month> 2026 Resource Pro Cash.xlsx`. `—` means blank, not zero. `Amount` means canonical `workpaper_amount_raw` (the worksheet/workpaper Amount), not bank transaction amount. Its numeric counterpart is blank for every `N/A` and equals the displayed number otherwise. `Expected` is `expected_workpaper_amount`; `Signed` is `source_signed_amount`. Normalized credits are already negative; they must not be negated again.

Counterpart suffixes: **S** = `same_month_void`, **C** = `cleared`, **O** = `outstanding`. Dates/values for non-S candidates appear below. **U** = `UNIQUE_AND_DETERMINISTIC`; **M** = `MULTIPLE_POSSIBLE_COUNTERPARTS`.

Classification is conservative and reciprocal across the full-period evidence: both sides must have a unique compatible cancellation relationship, not just one direction finding one number. A rival on the partner side or a same-vendor split alternative makes both sides M. These labels describe the inspection, not production verification outcomes. Status/context strongly favor many apparent S/S pairs, but this table does not assume in advance that differently labeled candidates must be excluded.

| IMS row | Transaction date | Debit | Credit | Amount | Signed | Expected | Exact opposite rows in full period | Class |
|---|---|---:|---:|---:|---:|---:|---|---|
| 04-R142 | 2026-04-01 | 1055.06 | — | N/A | 1055.06 | -1055.06 | 04-R9 C, 04-R143 S | M |
| 04-R143 | 2026-04-01 08:22:06 | — | -1055.06 | N/A | -1055.06 | 1055.06 | 04-R142 S | M |
| 04-R144 | 2026-04-03 | — | -25.0 | N/A | -25.0 | 25.0 | 04-R145 S | M |
| 04-R145 | 2026-04-06 | 25.0 | — | N/A | 25.0 | -25.0 | 04-R126 C, 04-R144 S | M |
| 04-R146 | 2026-04-14 | 54511.6 | — | N/A | 54511.6 | -54511.6 | 04-R49 C, 04-R151 S | M |
| 04-R147 | 2026-04-14 | 38313.08 | — | N/A | 38313.08 | -38313.08 | 04-R46 C, 04-R155 S | M |
| 04-R148 | 2026-04-14 | 87822.0 | — | N/A | 87822.0 | -87822.0 | 04-R50 C, 04-R152 S, 04-R165 S | M |
| 04-R149 | 2026-04-14 | 96123.0 | — | N/A | 96123.0 | -96123.0 | 04-R51 C, 04-R154 S | M |
| 04-R150 | 2026-04-14 | 69218.0 | — | N/A | 69218.0 | -69218.0 | 04-R52 C, 04-R153 S | M |
| 04-R151 | 2026-04-14 12:07:32 | — | -54511.6 | N/A | -54511.6 | 54511.6 | 04-R146 S | M |
| 04-R152 | 2026-04-14 12:08:22 | — | -87822.0 | N/A | -87822.0 | 87822.0 | 04-R148 S, 04-R156 S | M |
| 04-R153 | 2026-04-14 12:09:51 | — | -69218.0 | N/A | -69218.0 | 69218.0 | 04-R150 S | M |
| 04-R154 | 2026-04-14 12:10:15 | — | -96123.0 | N/A | -96123.0 | 96123.0 | 04-R149 S | M |
| 04-R155 | 2026-04-14 12:11:06 | — | -38313.08 | N/A | -38313.08 | 38313.08 | 04-R147 S | M |
| 04-R156 | 2026-04-20 | 87822.0 | — | N/A | 87822.0 | -87822.0 | 04-R50 C, 04-R152 S, 04-R165 S | M |
| 04-R157 | 2026-04-20 | — | -78.0 | N/A | -78.0 | 78.0 | 04-R164 S | M |
| 04-R158 | 2026-04-20 | — | -95108.92 | N/A | -95108.92 | 95108.92 | 04-R161 S | M |
| 04-R159 | 2026-04-20 | — | -100.0 | N/A | -100.0 | 100.0 | 04-R162 S | M |
| 04-R160 | 2026-04-20 | — | -121114.02 | N/A | -121114.02 | 121114.02 | 04-R163 S | M |
| 04-R161 | 2026-04-21 | 95108.92 | — | N/A | 95108.92 | -95108.92 | 04-R76 C, 04-R158 S | M |
| 04-R162 | 2026-04-21 | 100.0 | — | N/A | 100.0 | -100.0 | 04-R136 O, 04-R159 S | M |
| 04-R163 | 2026-04-21 | 121114.02 | — | N/A | 121114.02 | -121114.02 | 04-R78 C, 04-R160 S | M |
| 04-R164 | 2026-04-21 | 78.0 | — | N/A | 78.0 | -78.0 | 04-R77 C, 04-R157 S | M |
| 04-R165 | 2026-04-21 08:31:39 | — | -87822.0 | N/A | -87822.0 | 87822.0 | 04-R148 S, 04-R156 S | M |
| 04-R166 | 2026-04-23 | — | -49525.57 | N/A | -49525.57 | 49525.57 | 04-R167 S | M |
| 04-R167 | 2026-04-24 | 49525.57 | — | N/A | 49525.57 | -49525.57 | 04-R123 C, 04-R166 S | M |
| 05-R13 | 2026-05-08 10:56:44 | — | -23518.76 | 23518.76 | -23518.76 | 23518.76 | 05-R39 S | U |
| 05-R39 | 2026-05-19 | 23518.76 | — | -23518.76 | 23518.76 | -23518.76 | 05-R13 S | U |
| 06-R91 | 2026-06-22 | 15.0 | — | -15 | 15.0 | -15.0 | 06-R93 S | U |
| 06-R93 | 2026-06-22 10:55:56 | — | -15.0 | 15 | -15.0 | 15.0 | 06-R91 S | U |
| 06-R110 | 2026-06-24 | — | -312500.0 | 312500 | -312500.0 | 312500.0 | 06-R112 S | M |
| 06-R112 | 2026-06-24 | 312500.0 | — | -312500 | 312500.0 | -312500.0 | 06-R110 S, 06-R113 C | M |
| 07-R37 | 2026-07-10 | — | -2102.0 | 2102 | -2102.0 | 2102.0 | 07-R39 S | M |
| 07-R39 | 2026-07-10 | 2102.0 | — | -2102 | 2102.0 | -2102.0 | 07-R37 S | M |
| 07-R63 | 2026-07-15 | — | -1300.0 | 1300 | -1300.0 | 1300.0 | 07-R64 S | M |
| 07-R64 | 2026-07-15 | 1300.0 | — | -1300 | 1300.0 | -1300.0 | 07-R63 S, 07-R65 C | M |
| 07-R85 | 2026-07-22 | — | -10579.55 | 10579.55 | -10579.55 | 10579.55 | 07-R103 S | M |
| 07-R103 | 2026-07-22 | 10579.55 | — | -10579.55 | 10579.55 | -10579.55 | 07-R85 S | M |

Full-period conservative classifications: **4 UNIQUE_AND_DETERMINISTIC**, **34 MULTIPLE_POSSIBLE_COUNTERPARTS**, **0 DOES_NOT_NET_TO_ZERO**, **0 UNRESOLVED**. Here M includes accounting-link ambiguity even where zero sums exist; it does not mean the contextual void pairing is equally likely as a cleared reissue. If status/block context is used to distinguish void activity from live payments, 34 rows have unique S/S pairings and four Baldwin rows still have multiple S/S assignments. This contextual refinement is an observation, not a newly implemented rule.

## Apparent relationships and linking fields

All 19 positive rows have `method=V`, `check_or_ref=Void`, `source_description=Void`, blank payment type, and no explicit check number in their Date Cleared text. Negative sides contain the real payee and method C/Check or O/ACH, Wire, or Direct Debit. Thus vendor and reference are asymmetric, not shared identifiers.

| Period / amount | Flagged debit row(s) ↔ flagged outgoing row(s) | Outgoing vendor; reference / payment type | Date / order evidence |
|---|---|---|---|
| 2026-04 / 1055.06 | 04-R142 ↔ 04-R143 | Commonwealth of Massachusetts; 04-R143: 4360 / Check | 04-R142 2026-04-01; 04-R143 2026-04-01 08:22:06 |
| 2026-04 / 25.00 | 04-R145 ↔ 04-R144 | Superintendent of Financial Services; 04-R144: 4363 / Check | 04-R144 2026-04-03; 04-R145 2026-04-06 |
| 2026-04 / 54511.60 | 04-R146 ↔ 04-R151 | Safe Harbor Pollution Insurance, LLC; 04-R151: blank / ACH | 04-R146 2026-04-14; 04-R151 2026-04-14 12:07:32 |
| 2026-04 / 38313.08 | 04-R147 ↔ 04-R155 | Broadspire Services Inc.; 04-R155: blank / Wire | 04-R147 2026-04-14; 04-R155 2026-04-14 12:11:06 |
| 2026-04 / 87822.00 | 04-R148, 04-R156 ↔ 04-R152, 04-R165 | The Baldwin Group Specialty Industry LLC; 04-R152: blank / ACH; 04-R165: blank / Wire | 04-R148 2026-04-14; 04-R152 2026-04-14 12:08:22; 04-R156 2026-04-20; 04-R165 2026-04-21 08:31:39 |
| 2026-04 / 96123.00 | 04-R149 ↔ 04-R154 | James A . Scott & Son Inc. DBA Scott Insurance; 04-R154: blank / ACH | 04-R149 2026-04-14; 04-R154 2026-04-14 12:10:15 |
| 2026-04 / 69218.00 | 04-R150 ↔ 04-R153 | Marsh & McLennan Agency LLC; 04-R153: blank / ACH | 04-R150 2026-04-14; 04-R153 2026-04-14 12:09:51 |
| 2026-04 / 78.00 | 04-R164 ↔ 04-R157 | CDPS Natural Disaster Mitigation Enterprise; 04-R157: blank / ACH | 04-R157 2026-04-20; 04-R164 2026-04-21 |
| 2026-04 / 95108.92 | 04-R161 ↔ 04-R158 | ANZ Banking Group Limited; 04-R158: blank / Wire | 04-R158 2026-04-20; 04-R161 2026-04-21 |
| 2026-04 / 100.00 | 04-R162 ↔ 04-R159 | Florida Department of Financial Services; 04-R159: 4386 / Check | 04-R159 2026-04-20; 04-R162 2026-04-21 |
| 2026-04 / 121114.02 | 04-R163 ↔ 04-R160 | Lloyds Bank Corporate Markets PLC; 04-R160: blank / Wire | 04-R160 2026-04-20; 04-R163 2026-04-21 |
| 2026-04 / 49525.57 | 04-R167 ↔ 04-R166 | The Bank of Nova Scotia; 04-R166: blank / Direct Debit | 04-R166 2026-04-23; 04-R167 2026-04-24 |
| 2026-05 / 23518.76 | 05-R39 ↔ 05-R13 | Division of Workers Compensation; 05-R13: 4396 / Check | 05-R13 2026-05-08 10:56:44; 05-R39 2026-05-19 |
| 2026-06 / 15.00 | 06-R91 ↔ 06-R93 | City of Milan; 06-R93: 4420 / Check | 06-R91 2026-06-22; 06-R93 2026-06-22 10:55:56 |
| 2026-06 / 312500.00 | 06-R112 ↔ 06-R110 | Lockton Management LLC; 06-R110: blank / Direct Debit | 06-R110 2026-06-24; 06-R112 2026-06-24 |
| 2026-07 / 2102.00 | 07-R39 ↔ 07-R37 | Oklahoma Tax Commission; 07-R37: 4426 / Check | 07-R37 2026-07-10; 07-R39 2026-07-10 |
| 2026-07 / 1300.00 | 07-R64 ↔ 07-R63 | Department of Workforce Development Bureau of Finance; 07-R63: 4431 / Check | 07-R63 2026-07-15; 07-R64 2026-07-15 |
| 2026-07 / 10579.55 | 07-R103 ↔ 07-R85 | Louisville-Jefferson Co Revenue Commission; 07-R85: 4438 / Check | 07-R85 2026-07-22; 07-R103 2026-07-22 |

- April rows 142–167 form a contiguous flagged block, although their transaction dates run April 1–24 and the preceding row 141 is a returned transaction. Rows 146–150 are five generic debits followed by five named outgoing rows 151–155 in a different amount order: adjacency alone would mispair them. Every April flagged row has Account, Cost Center, workpaper description, and workpaper Amount `N/A`; bank Debit/Credit still carry the offsetting amounts.
- Baldwin: April debit rows 148 (April 14) and 156 (April 20) each +87,822 can offset outgoing rows 152 (April 14 ACH) or 165 (April 21 Wire), each −87,822. Date/order favors 148↔152 and 156↔165, but does not prove that assignment. All four together net exactly zero; this is a two-by-two ambiguity, not evidence of one debit consuming two full outgoing amounts.
- May rows 13↔39 are separated by 26 source-row positions and 11 days. Amount and opposite sign, shared flagged status, Account 3024020 and Cost Center ZZZZ support the pair. Exact date or adjacency is not a necessary historical feature.
- June rows 91↔93 have row 92 interposed: a different 47.21 void-reference transaction. They share June 22, Account 1020857, blank Cost Center, and opposite 15.00 amounts. Pairing adjacent void rows 91↔92 would be wrong.
- June 110↔112 nets 312,500, but 110 has Account 3015025 / ZZZZ while 112 has Account 1020861 / blank. Row 111 between them is a 300.00 outstanding Florida check using Account 1020861. This is a material accounting-field inconsistency, not a reason to silently copy or repair the void account. Cleared Lockton row 113 supplies a rival equal outgoing amount.
- July 37↔39 shares Account 3024020 but differs FINU versus ZZZZ. Rows 63↔64 share Account 1020815 but CLMU versus blank; row 65 is a cleared same-vendor replacement-sized check. Rows 85↔103 share Account 3023035 and ZZZZ but are 18 row positions apart. Account/Cost Center agreement is useful corroboration, not universally available or identical.
- `backup_raw=Concur Report` occurs on seven flagged outgoing rows, never on a generic positive void row. All flagged `cleared_dates` are blank. Raw Date Cleared is `Same Month Void` on 28 rows and `Same month void check` on 10. The word “check” is not a reliable payment-method restriction: non-check ACH/Wire/Direct Debit cases exist.

## Other-status alternatives and split-payment structure

The following exact opposite-size records occur in the same period. Their cleared dates/status are different from the flagged void rows. They resemble live originals/reissues by vendor/amount/date context; the canonical data does not explicitly link them as replacements.

| Other-status row | Vendor | Signed amount | Transaction date | Check/ref | Date Cleared raw |
|---|---|---:|---|---|---|
| 04-R9 | Commonwealth of Massachusetts | -1055.06 | 2026-04-01 09:01:58 | 4361 | 2026/04/03 |
| 04-R126 | Superintendent of Financial Services | -25.0 | 2026-04-06 10:07:47 | 4364 | 2026/04/30 |
| 04-R49 | Safe Harbor Pollution Insurance, LLC | -54511.6 | 2026-04-07 | — | 2026/04/15 |
| 04-R46 | Broadspire Services Inc. | -38313.08 | 2026-04-07 | — | 2026/04/14 |
| 04-R50 | The Baldwin Group Specialty Industry LLC | -87822.0 | 2026-04-07 | — | 2026/04/15 |
| 04-R51 | James A . Scott & Son Inc. DBA Scott Insurance | -96123.0 | 2026-04-07 | — | 2026/04/15 |
| 04-R52 | Marsh & McLennan Agency LLC | -69218.0 | 2026-04-07 | — | 2026/04/15 |
| 04-R76 | ANZ Banking Group Limited | -95108.92 | 2026-04-21 09:54:33 | — | 2026/04/22 |
| 04-R136 | Florida Department of Financial Services | -100.0 | 2026-04-21 09:56:44 | 4387 | Outstanding Check |
| 04-R78 | Lloyds Bank Corporate Markets PLC | -121114.02 | 2026-04-21 09:58:20 | — | 2026/04/22 |
| 04-R77 | CDPS Natural Disaster Mitigation Enterprise | -78.0 | 2026-04-21 09:55:30 | — | 2026/04/22 |
| 04-R123 | The Bank of Nova Scotia | -49525.57 | 2026-04-29 09:38:13 | — | 2026/04/29 |
| 06-R113 | Lockton Management LLC | -312500.0 | 2026-06-24 11:32:04 | — | 2026/06/25 |
| 07-R65 | Department of Workforce Development Bureau of Finance | -1300.0 | 2026-07-15 14:52:31 | 4432 | 2026/07/22 |

Two same-vendor **one-to-many arithmetic alternatives** also occur:

- July Oklahoma: flagged debit 39 (+2,102) can net flagged outgoing 37 (−2,102, check 4426), or cleared rows 47 (−1,815, check 4427) + 48 (−287, check 4428). All transaction dates are July 10; the latter two clear July 14. All use Account 3024020; flagged outgoing Cost Center FINU differs from ZZZZ on the split records.
- July Louisville: flagged debit 103 (+10,579.55) can net flagged outgoing 85 (−10,579.55, check 4438), or cleared rows 104 (−6,923.90, check 4455) + 105 (−3,655.65, check 4456). All transaction dates are July 22; the latter two clear July 28. Account 3023035 agrees; split records use FINU rather than flagged ZZZZ.

Therefore the directly flagged cancellation structure is one-to-one with a repeated two-by-two case; the broader same-period numeric relationship is **mixed**, including one-to-many alternatives. No flagged transaction requires a many-row counterpart to reach zero. The split alternatives must not be declared additional cancellations or consumed together with the already-netted flagged originals. No other multi-row sums were found within the exact named-vendor outgoing populations examined; this does not prove absence of arbitrary unrelated arithmetic sums.

## Findings on the two current requirements and recommendation

1. **Shared explicit reference is not supported as a mandatory historical requirement.** Zero of the 19 apparent pair slots has a shared explicit identifier: every debit says only `Void`; outgoing checks carry actual numbers, while outgoing electronic payments often have blank references. This requirement excludes the entire observed void population despite exact zero-net flagged structures. An explicit reference remains strong optional evidence when available.
2. **Both sides labeled `same_month_void` is supported by the observed cancellation structure, but is not independently proven as a universal business requirement.** Every one of the 38 rows has a flagged exact opposite, and all flagged amounts can be partitioned into 19 pairs. No historical flagged case needs a differently labeled counterpart to reach zero. However, differently labeled equal-sized and split outgoing alternatives really exist; status helps distinguish the apparent cancellation from live payment/reissue activity. The inspection does not establish that a cleared/outstanding alternative was actually voided.
3. For a future design, evaluate a same-period signed-amount graph with reciprocal uniqueness, explicit separation of void activity from live/reissued payments, and date/order/account evidence as corroboration. Do not require a shared reference, exact date, immediate adjacency, shared vendor text, or identical accounting dimensions blindly. These findings support considering richer deterministic context, not promoting amount-only equality to proof.
4. Keep the four Baldwin rows and the June Lockton account discrepancy visible for human confirmation. A balanced flagged block proves arithmetic cancellation, not a unique row assignment or correct GL treatment. Obtain accountant confirmation of whether status/block context may identify the apparent pair when cleared/outstanding reissues share the amount, and how mixed-status relationships should be handled.
5. No production rules, sanitizers, canonical datasets, or verification outputs were modified. No SUN data was consulted. This report is the only new inspection artifact.
