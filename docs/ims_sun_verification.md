# IMS-to-SUN verification: rules version 5

## SUN-verification eligibility

SUN verification asks whether an IMS transaction with genuine actual cleared dates is supported by SUN. Eligibility requires normalized status `cleared` or `multiple_cleared_dates` plus valid normalized `cleared_dates` tokens. Status `cleared` must identify one distinct date. Date-like text on an outstanding/returned/void status does not override normalized status.

Only eligible rows participate in vendor-order ranking, candidate generation, SUN evidence claims, and the reuse audit. Non-date statuses are excluded without performing SUN matching: same-month void, outstanding, returned, blank, void-reference-only, other text statuses, and invalid normalized dates. Excluded rows do not reserve SUN evidence. There is no special void reuse exception; voids are outside the population entirely.

## IMS-internal pre-verification controls

`ims_preverification()` is unchanged from version 4, including its exact signed-amount grouping, unique pairs, repeated-amount group handling, and complete member provenance.

For each accounting period, normalized same-month-void rows group by absolute canonical `source_signed_amount`. Exact nonzero Decimal netting determines PASSED/FAILED. Unique two-member groups netting to zero record `SAME_MONTH_VOID_NET_ZERO`; larger balanced groups record `SAME_MONTH_VOID_NET_ZERO_GROUP` with all member IDs and no forced pair assignment. Invalid/unbalanced groups retain `VOID_NOT_NETTED_TO_ZERO`. No shared reference, date equality, adjacency, vendor equality, or identical Account/Cost Center is required.

**Same Month Void ends at this internal control.** A passed or failed void group is never sent to SUN; neither its positive members nor negative identity-context members claim SUN rows. It has no SUN amount target or obligation to obtain SUN support. The internal result remains separately available under `ims_internal_control`.

Normal clearing validation also remains recorded separately. Invalid clearing stops before SUN.

## SUN supporting-evidence verification for eligible dated rows

Existing matching behavior is retained:

- Exact SUN entity tuple: company `AIC`, bank name `AIC Disbursements (2693)`, bank code `13012085`, canonical sheet `Page1_1`. AICRE and AAIC remain separate.
- Same accounting period and exact vendor identity after case/punctuation/whitespace normalization. No fuzzy vendors or undocumented aliases.
- Vendor/date/source-row ordering and temporal/relative-order ranking. No fixed calendar-day cutoff or exact date equality rule. All same-period vendor evidence remains eligible for bounded local spans.
- Contiguous spans up to 18 positions, or one internal gap when selected rows share a nonempty exact invoice reference. No arbitrary combinations across unrelated monthly rows.
- One-to-one and one-to-many amount reconciliation using Decimal, negative allocations, and the existing $0.00001 Excel precision tolerance. Only allocation `amount` is summed; normal SUN target sign convention is unchanged.
- ACH/Wire/Direct Debit identity agreement, or exact IMS Check reference against SUN raw Payment Type. No unapproved method equivalences.
- Multiple plausible combinations, conflicting identity/accounting evidence, or absent support require HUMAN_REVIEW_REQUIRED. Proximity rank never resolves ambiguity.
- Existing 64-row vendor-pool and 256-reconciled-candidate safeguards remain; incomplete searches require review.
- Two-pass reuse audit among eligible transactions, including their unresolved candidates. Shared evidence routes affected eligible cases to review. No greedy allocation and no reuse among final verified results.

## Result and summary fields

Every IMS source record retains original provenance, canonical signed amount, internal-control record, final routing status, and relevant candidate/evidence detail. New explicit scope fields avoid treating exclusions as failed SUN checks:

- `sun_eligible`: actual-date eligibility.
- `sun_verification_status`: VERIFIED / HUMAN_REVIEW_REQUIRED for eligible rows; NOT_APPLICABLE for excluded rows.
- `sun_exclusion_reason`: exclusion explanation.
- `sun_evidence_attempted`: false for all excluded rows.

For compatibility, excluded records retain the legacy whole-record routing `status=HUMAN_REVIEW_REQUIRED`. This is not a SUN-review outcome. Passed void rows have routing reason `SAME_MONTH_VOID_INTERNAL_CONTROL_ONLY`, and their independent internal status is PASSED. Failed void rows preserve the internal failure reason. No passed void is labeled NOT_SUPPORTED_BY_SUN or required to obtain SUN support. Consumers reporting SUN performance should use the explicit SUN eligibility/status fields.

The summary exposes `sun_eligible_count`, `sun_excluded_count`, `sun_verified`, `sun_human_review_required`, and `sun_review_reason_code_counts`. Older overall routing fields include exclusions and must not be mistaken for SUN-only counts. Void `human_review_rows`/`reason_code_counts` are legacy routing fields; `internal_passed_rows`, `internal_failure_rows`, and `internal_reason_code_counts` describe actual void-control results. Void SUN searches/support/review-group metrics are all zero.

## January–July 2026 rerun

HUMAN REVIEW in the following table means **eligible SUN transactions only**. Excluded rows are separate.

| Month | IMS total | Dated eligible | Excluded | SUN VERIFIED | ONE_TO_ONE | ONE_TO_MANY | SUN HUMAN REVIEW | Reuse cases / rows |
|---|---|---|---|---|---|---|---|---|
| 2026-01 | 355 | 110 | 245 | 45 | 42 | 3 | 65 | 2 / 2 |
| 2026-02 | 116 | 104 | 12 | 40 | 36 | 4 | 64 | 0 / 0 |
| 2026-03 | 133 | 100 | 33 | 37 | 31 | 6 | 63 | 3 / 2 |
| 2026-04 | 159 | 123 | 36 | 43 | 30 | 13 | 80 | 0 / 0 |
| 2026-05 | 83 | 75 | 8 | 26 | 22 | 4 | 49 | 2 / 1 |
| 2026-06 | 116 | 102 | 14 | 60 | 46 | 14 | 42 | 6 / 3 |
| 2026-07 | 137 | 117 | 20 | 73 | 60 | 13 | 44 | 4 / 5 |

Totals: **1,099 IMS transactions; 731 eligible; 368 excluded; 324 SUN VERIFIED; 407 SUN HUMAN_REVIEW_REQUIRED**. Eligible verification rate: **44.32%**; eligible human-review rate: **55.68%**. Verified methods: **267 ONE_TO_ONE and 57 ONE_TO_MANY**.

The 368 exclusions comprise 330 invalid/missing/non-date normal clearing records and 38 same-month-void rows. Legacy whole-record routing totals are 324 VERIFIED / 775 HUMAN_REVIEW_REQUIRED, including exclusions; these differ deliberately from the SUN-only review count of 407.

### Eligible SUN review reasons

| Month | NOT_SUPPORTED_BY_SUN | SUN_EVIDENCE_CONFLICT | SUN_ROW_REUSE_CONFLICT |
|---|---|---|---|
| 2026-01 | 61 | 2 | 2 |
| 2026-02 | 60 | 4 | 0 |
| 2026-03 | 60 | 0 | 3 |
| 2026-04 | 77 | 3 | 0 |
| 2026-05 | 45 | 2 | 2 |
| 2026-06 | 6 | 30 | 6 |
| 2026-07 | 4 | 36 | 4 |

Totals: **313 NOT_SUPPORTED_BY_SUN, 77 SUN_EVIDENCE_CONFLICT, 17 SUN_ROW_REUSE_CONFLICT**. No other primary review reasons occur among eligible historical rows. Reuse conflicts affect 17 eligible IMS cases and 13 distinct SUN rows. No excluded IMS identifier appears as an evidence owner or competing claimant.

### Same Month Void: internal results only

| Month | Void rows | Zero-net unique pairs | Zero-net repeated-amount groups | Internal failures | SUN searches / claims |
|---|---|---|---|---|---|
| 2026-01 | 0 | 0 | 0 | 0 | 0 / 0 |
| 2026-02 | 0 | 0 | 0 | 0 | 0 / 0 |
| 2026-03 | 0 | 0 | 0 | 0 | 0 / 0 |
| 2026-04 | 26 | 11 | 1 | 0 | 0 / 0 |
| 2026-05 | 2 | 1 | 0 | 0 | 0 / 0 |
| 2026-06 | 4 | 2 | 0 | 0 | 0 / 0 |
| 2026-07 | 6 | 3 | 0 | 0 | 0 / 0 |

All **38 rows pass the same internal controls as before: 17 unique pairs and one four-member balanced group**, zero internal failures. There are 18 internal groups representing 19 cancellation slots. April's four-member 87,822 group retains all four IDs without artificial pairing. No void enters SUN matching or evidence reuse.

## Validation and execution

The full suite passes **77 tests**. Tests cover eligible single/multiple dates; invalid dates and non-date statuses stopping before SUN; void pair/group preservation; exact internal failure behavior; exclusion despite date-like tokens on non-date statuses; no void search/claims; eligible-only reuse; and the existing matching/ambiguity/ordering controls.

A before/after check confirms the entire `ims_preverification()` function is byte-for-byte unchanged and every historical internal-control record is identical. Historical checks confirm all 38 void records have empty SUN candidate/claim fields and no reuse conflicts. **447 distinct SUN rows support 324 finally verified eligible transactions, with no SUN row reused.**

```bash
.venv/bin/python -m src.ascot.verify_ims_sun
```

Canonical inputs: `data/processed/aic_ims_all_months_transactions.csv` and monthly `data/processed/sun_jnl/sun_jnl_YYYY-MM.csv`. Both sanitizers and unrelated controls remain unchanged. Output directory: `data/processed/verification/ims_to_sun/`, containing `verification_results.jsonl`, `verification_summary.json`, and `verification_manifest.json` with input hashes and rules version. Optional CLI arguments remain `--ims`, `--sun-dir`, `--output-dir`.
