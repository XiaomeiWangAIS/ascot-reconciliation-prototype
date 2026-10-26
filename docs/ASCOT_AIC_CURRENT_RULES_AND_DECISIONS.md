# Ascot AIC — current rules and decisions

As of **2026-10-26**. This is the master working-memory and rule-governance document for the reconciliation prototype. It consolidates current decisions; it does not change executable rules or rewrite historical results. Relative paths below resolve from the repository root unless linked explicitly.

## 1. Purpose, authority, and status legend

Use this document to distinguish accepted rules from unresolved business meanings and experiments. Component reports retain their original evidence and chronology. If code, a report, and this memo disagree, record and investigate the discrepancy rather than silently choosing the result with the highest automation rate.

| Status | Meaning |
|---|---|
| **LOCKED** | Empirically inspected, implemented, QA/tested, and accepted as the current rule/design. Acceptance here records the current project position; it does not imply that Ascot has approved unresolved business meanings. |
| **PENDING ASCOT CONFIRMATION** | Evidence suggests a change may be appropriate, but Ascot has not confirmed the business rule. No production change is authorized by the evidence alone. |
| **DIAGNOSTIC / EXPERIMENTAL** | Sensitivity analysis, counterfactual, validation experiment, or proposed analysis. Must not silently become production logic. |
| **SUPERSEDED** | An earlier interpretation, implementation, or report-stage conclusion replaced by later evidence/decisions. Retained for provenance, no longer current. |

The historical `Ascot_AIC_Automation_Project_Memory_Memo_2026-09-15` was created outside the repository and was unavailable during the initial consolidation. The project owner subsequently supplied its foundational decisions in this conversation on 2026-10-26. Those decisions originated in earlier development discussions before the current repository documentation existed and are now migrated into this master memo, checked against current code and reports. This supplied history is decision provenance, not a claim that the original memo was recovered or independently inspected. No September memo was overwritten or deleted; preserve it as historical provenance if later supplied.

**LOCKED governance/design** below includes these explicitly established historical principles. That label records an accepted design constraint, not a claim that every workflow stage has been implemented and tested. Component implementation claims retain their specific QA/test evidence and limitations. No supplied foundational principle conflicts with newer repository evidence; none requires a new **SUPERSEDED** designation in this migration.

Repository chronology also matters: several core controls were committed on September 13–14, while later SUN and validation work is present in the working tree without corresponding commit history. Filesystem dates are not evidence of business approval. The change log below separates known dated commits from evidence reviewed on this memo's date.

## 2. Non-negotiable empirical-development principles — LOCKED

`inspect actual files → characterize real structure/month-to-month variation → design sanitizer → run → QA → lock`

For cross-source reconciliation:

`inspect actual empirical relationship → characterize patterns/exceptions → only then design production reconciliation logic`

Before writing sanitizer, parser, data-ingestion, or reconciliation logic for an Ascot source, inspect actual underlying data across relevant periods/samples. Documentation, SOPs, transcripts, screenshots, data-request documents, employee explanations, and assumptions can guide inspection but cannot establish workbook structure or machine-readable production rules by themselves. Never infer headers, row boundaries, formulas, continuation logic, field semantics, matching rules, or exception behavior from documentation alone. Flag unresolved structures and business meanings. Preserve raw evidence and provenance; historical/manual corrections must not silently become permanent machine rules. Do not infer a rule merely because it improves historical automation. A status promotion requires documented evidence, validation, and a material decision; business-rule changes also require the relevant Ascot confirmation.

**LOCKED governance:** this is a human-accountable reconciliation system. Automate clear, rule-supported cases; route missing, conflicting, ambiguous, or judgment-sensitive evidence to human review. Human intervention on one item must not stop unaffected automation. Preserve source evidence, exception history, material decisions, reviewer identity/rationale, and final accountability. Evidential reliability takes precedence over automation rate.

**LOCKED allocation of work:** a task is not inherently automated or augmented. Allocate work at the particular task episode / decision instance according to evidence completeness, uncertainty, and accountability requirements. Human judgment can define rules, provide evidence, interpret exceptions, revise rules, review results, and approve accounting treatment; it is not merely a fallback for machine failure. One identifiable human owner remains accountable for consequential reconciliation/accounting decisions. The automation boundary may evolve with evidence, process knowledge, and organizational conditions, through explicit rule provenance and governance rather than silent learning from human corrections.

**LOCKED material accountability record:** preserve material decisions, supporting source records, exception history, and an audit trail sufficient to explain consequential conclusions. Do not attempt to log every machine micro-action. Multiple plausible interpretations remain human review; arbitrary search order or “first match wins” cannot settle identity. A higher match rate is not a better control when achieved through weaker identity assumptions, arbitrary thresholds, evidence reuse, or unsupported combinations. Supporting evidence must not be reused across independent transactions in a way that purports to prove two different payments.

**LOCKED general processing:** use parsed accounting periods for Jan → Feb → … ordering, never arbitrary filesystem order. Historical Excel colors may remain presentation/provenance metadata, while production accounting logic consumes explicit normalized categories such as `category="IMS"`. Workbooks can contain huge formatted-but-empty regions: parsing must be memory-efficient and limited to meaningful data regions/columns where empirical inspection justifies the limits. Streaming and bounded-column approaches in `sanitize_aic_wf.py` and XML streaming in `sanitize_aic_ims.py` support this principle; it does not authorize uninspected fixed cutoffs that could discard real transactions.

Implementation boundary: `src/ascot/workflow.py` illustrates episode ownership, material judgment, and final approval using synthetic data; its illustrative LLM confidence threshold is **DIAGNOSTIC / EXPERIMENTAL**, not an Ascot accounting policy. `shared_records/TX001.json` is a prototype record, not historical reconciliation proof. The current modules do not establish a fully integrated, deployed orchestration or immutable exception-history store. In particular, `review_rejections.py` replaces an item's current review within the episode; preserving historical revisions remains a governance obligation, not a claimed implemented audit log.

## 3. Current end-to-end architecture — LOCKED design

1. Inspect and preserve monthly source workbooks; process in true accounting-period order. Sanitize WF, Previous Day, IMS, and SUN into separate canonical populations with source-row provenance and QA/manifests.
2. Run Previous Day → WF deterministic completeness control, including duplicate groups.
3. Independently run current-month IMS → WF aggregate control using explicit WF IMS categories and normalized IMS actual-cleared statuses. This does not establish individual IMS/WF identities.
4. Evaluate IMS internal controls, including Same Month Void period/absolute-amount groups. Void rows stop here for SUN purposes.
5. Send only eligible actual-cleared-date IMS transactions to conservative SUN evidence verification. Preserve unsupported, ambiguous, conflicting, and excluded outcomes distinctly.
6. Account for every rejection; escalate unknowns. Review exceptions and material human decisions before accountable finalization. A finalization gate does not freeze unrelated processing.

These are distinct controls and populations; passing one does not prove another or establish source completeness beyond the inspected exports.

### Working AIC Cash Expense workflow — LOCKED conceptual architecture

The earlier episode-level architecture remains current:

1. Ingest and normalize inputs.
2. Run upstream integrity checks: Previous Day ↔ AIC WF and current-month AIC IMS ↔ WF IMS-category population.
3. Perform rejection review.
4. Resolve transactions using evidence and classification, including the scoped IMS/SUN controls above where applicable.
5. Establish the resolved transaction population.
6. Prepare a proposed journal entry.
7. Run final accounting/control checks.
8. Resolve exceptions affecting the relevant output.
9. Obtain responsible-person review.
10. Mark the JE ready or the episode formally unresolved.

Resource Pro controls are upstream integrity checks. Once differences are resolved or formally dispositioned, proceed to substantive accounting work rather than extending Resource Pro automation for its own sake. Formal disposition records the evidence, reviewer, and effect on finalization; it does not silently convert a failed control into a pass or authorize unsupported accounting.

These stages express conceptual responsibilities, not a rigid global stop at each step. Complete evidence plus a deterministic rule permits machine continuation. Missing, conflicting, ambiguous, unsupported, or judgment-sensitive evidence routes the particular decision to human review. An unresolved exception may block the relevant final accounting output while unaffected processing continues. Rejection finalization remains governed by the specific gate described below.

Evidence and implementation boundary: `src/ascot/aic_cash_reconciliation.py` is explicitly a **synthetic version-0 end-to-end skeleton**, with transaction resolution, exception queue, proposed JE, final controls, and responsible-person approval. Together with `workflow.py` and `review_rejections.py`, it supports the historical architecture, but does not demonstrate a fully integrated production workflow, complete accounting rules, or a production-ready JE generator. Illustrative synthetic accounting treatments are **DIAGNOSTIC / EXPERIMENTAL**, not newly locked business rules.

## 4. Current LOCKED components and rules

### AIC WF — LOCKED sanitizer

Main cash activity and ZBA/sweep activity are structurally separated. Subtotal/control rows are metadata, not transactions. Historical fill information can be normalized into explicit categories at the source boundary; downstream production rules consume category metadata, not raw RGB/fill values. File and consolidated output ordering uses accounting periods, not alphabetical month names.

The sanitizer followed actual January–July inspection. The observed recurring layout is **main cash-transaction block → subtotal/control row → spacer → secondary ZBA/sweep block**. Identify the separation from the observed subtotal/control boundary and transaction descriptions, not a fixed number of blank rows or an assumed “large blank gap = ZBA” rule. Unexpected post-subtotal activity remains visible for QA rather than being forced into the sweep population. This is corroborated by the locked-design comments, `detect_sum_formula`, section classification in `sanitize_aic_wf.py`, and monthly boundary/section checks in `aic_wf_qa_report.json`.

Evidence: `src/ascot/sanitize_aic_wf.py`, `qa_aic_wf.py`, and `extract_aic_wf_legacy_categories.py`; `data/processed/aic_wf_processing_manifest.json`, `aic_wf_qa_report.json`, and `aic_wf_legacy_category_manifest.json`. QA reports **93 passes, 0 warnings, 0 failures** across Jan–Jul; **1,514** transactions. Per-workbook transaction, control-row, validation, and presentation artifacts retain the source boundary and historical legend.

### AIC IMS — LOCKED sanitizer for inspected Jan–Jul structure

Source transactions, allocation/supplemental rows, balance-forward rows, and void/status semantics remain distinct. Allocation rows must link to source transactions rather than inflate payment counts. `Date Cleared` normalization distinguishes actual clearing evidence from outstanding, returned, void, blank, and other status text. Numeric signs and source amounts remain separate from workpaper allocations.

Evidence: `src/ascot/sanitize_aic_ims.py` (including `classify_row`, `parse_date_cleared`, allocation linkage), `qa_aic_ims.py`; `data/processed/aic_ims_processing_manifest.json`, `aic_ims_qa_report.json`, and `aic_ims_all_months_{rows,transactions,allocations}.csv`. QA reports **128 passes, 0 warnings, 0 failures**; **1,099** source transactions. Locking the inspected structure is not universal compatibility: the new July export required an isolated adapter, described below.

### Previous Day → WF — LOCKED deterministic completeness control

Preserve duplicate groups; do not invent one-to-one identities within indistinguishable duplicates. Historical Jan–Jul reconciles **1,514 vs 1,514**, comprising **1,512 unique-match transactions** and **one two-transaction duplicate group** in July, with **0 exceptions** and all seven periods passing.

Evidence: `src/ascot/sanitize_previous_day.py`, `qa_previous_day.py`, `inspect_previous_day_wf_alignment.py`, `reconcile_previous_day_to_wf.py`; `tests/test_reconcile_previous_day_to_wf.py`; `data/processed/previous_day_wf_alignment_inspection.json`, `wf_previous_day_processing_manifest.json`, `wf_previous_day_qa_report.json`, and `reconciliation/previous_day_to_wf/all_months_summary.json` plus group/exception CSVs.

### Current-month IMS → WF — LOCKED aggregate control

WF population is explicitly categorized `IMS`. IMS population is source transactions normalized as `cleared` or `multiple_cleared_dates`; outstanding, returned, same-month void, blank, and other non-cleared statuses are excluded. The historical amount control compares WF IMS total with **ABS(IMS cleared Credit total)**, with zero tolerance; it does not sum supplemental workpaper allocations or force transaction-level matching. Unexpected cleared non-credit records remain exceptions.

Jan **+300.00** and Feb **−2,220.00** (WF minus normalized IMS outflow) are genuine historical control exceptions, not coding errors. March–July reconcile at zero variance. Do not insert corrective offsets or broaden populations to erase these differences.

Evidence: `src/ascot/inspect_current_month_ims_wf_control.py`, `reconcile_current_month_ims_to_wf.py`; `tests/test_reconcile_current_month_ims_to_wf.py`; `data/processed/inspection/current_month_ims_to_wf/` and `data/processed/reconciliation/current_month_ims_to_wf/{reconciliation_report.json,monthly_reconciliation.csv,exceptions.csv,wf_ims_population.csv,ims_cleared_population.csv}`.

### Rejection review — LOCKED finalization design

Every rejection must be accounted for and explained. Unknown rejections require escalation and escalation notes; they cannot disappear as unclassified leftovers. Incomplete review can block finalization, while `blocks_workflow=False` permits unrelated work. The implemented gate can accept an accounted-for, explained, properly escalated unknown; it does not require inventing a resolved cause before recording escalation.

Evidence: `src/ascot/review_rejections.py`, particularly `evaluate_rejection_review`, `record_rejection_review`, and `check_rejection_finalization_gate`. This module includes a demonstration; no dedicated rejection test file is present. Do not misrepresent the other component tests as comprehensive end-to-end rejection validation.

### SUN JNL — LOCKED sanitizer

Canonical source is **`Page1_1`**. Other sheets are extracts or edited working copies and must not simply be appended. Preserve allocation-line grain, negative/zero amounts, repeated totals as separate fields, exact duplicate occurrences, nullable source values, raw fields, and source provenance. No arbitrary deduplication or aggregation. Preserve AIC, AICRE, AAIC, and other entities separately; sanitization itself retains all companies.

Inspection covered **seven workbooks / 31 sheets**. QA reconciles **6,276 input allocation lines → 6,276 sanitized rows**. Missing values, retained duplicates, and March/June coverage limitations are source warnings, not permission to repair source values from working copies.

Evidence: [structure inspection](sun_jnl_structure_inspection.md), [sanitizer QA](sun_jnl_sanitizer_qa.md), `src/ascot/sanitize_sun_jnl.py`, `tests/test_sanitize_sun_jnl.py`, and `data/processed/sun_jnl/sun_jnl_manifest.json` with seven monthly CSVs.

### Same Month Void — LOCKED IMS-internal control only

Group normalized `same_month_void` rows by **same accounting period + absolute canonical `source_signed_amount`**, using exact Decimal arithmetic and valid nonzero amounts. Two opposite-signed members netting to zero pass as `SAME_MONTH_VOID_NET_ZERO`. Repeated-amount groups netting to zero pass as `SAME_MONTH_VOID_NET_ZERO_GROUP`, preserving all member IDs without arbitrary one-to-one pairings. Invalid or unbalanced groups fail as `VOID_NOT_NETTED_TO_ZERO`.

Do not substitute whole-month netting. No shared reference, exact date, adjacency, vendor, account, or cost center is required. Arithmetic cancellation does not prove unique economic pairing or correct accounting dimensions.

**After internal evaluation, neither passed nor failed Same Month Void rows enter SUN verification, generate candidates, claim SUN evidence, or join SUN reuse conflicts.** No SUN support obligation remains for those rows.

Evidence: [void structure inspection](same_month_void_structure_inspection.md), `src/ascot/verify_ims_sun.py::ims_preverification`, [rules version 5](ims_sun_verification.md), and `tests/test_verify_ims_sun.py` tests for exact netting, internal-only pairs, repeated groups, and historical population separation. The inspection identified **38 flagged rows / 19 apparent pair slots**, including repeated amounts and alternative live-payment arithmetic; its exploratory pairing recommendations are not additional current requirements.

### IMS → SUN — LOCKED conservative rules version 5

- Only statuses `cleared` / `multiple_cleared_dates` with valid actual normalized date tokens enter verification. A `cleared` row must have one distinct date. Status text with date-like content does not override exclusion.
- Same accounting period; exact scope: company **AIC**, bank **AIC Disbursements (2693)**, code **13012085**, sheet **Page1_1**.
- Exact normalized vendor identity (case/punctuation/whitespace normalization). No fuzzy vendor matching or undocumented vendor aliases.
- One-to-one or one-to-many amount support; sum SUN allocation `amount`, including negative lines, with existing **0.00001** precision tolerance. Amount coincidence alone is insufficient.
- Preserve current bounded candidate design: ordered contiguous spans up to **18** positions, or one internal gap with a shared nonempty exact invoice reference; **64** vendor-row / **256** reconciled-candidate safeguards. Incomplete searches require review. No arbitrary monthly subsets, fixed day cutoff, or exact-date equality requirement. Date/order ranking never resolves multiple plausible alternatives.
- **Payment/check identity remains a hard production requirement**: electronic method agreement, or exact IMS Check reference against raw SUN Payment Type. No unapproved payment-method equivalences.
- Ambiguity, conflicting evidence, absent support, and competing SUN claims go to human review. Two-pass reuse auditing includes unresolved candidates; SUN evidence cannot be reused across independent IMS transactions. No greedy assignment to force completion.

Evidence: `src/ascot/verify_ims_sun.py`, `tests/test_verify_ims_sun.py`, [verification specification](ims_sun_verification.md), and `data/processed/verification/ims_to_sun/{verification_manifest.json,verification_summary.json,verification_results.jsonl}`. Manifest records version, hashes, scope, bounds, tolerance, and eligibility. Of **1,099** source records, **731** are eligible; current rules verify **324/731**. Excluded records retain legacy whole-record `HUMAN_REVIEW_REQUIRED` routing but explicit SUN status `NOT_APPLICABLE`. Use `sun_eligible` / `sun_verification_status` for SUN performance; exclusions are not failed SUN matches.

## 5. PENDING ASCOT CONFIRMATION items

**Payment-type meaning — PENDING ASCOT CONFIRMATION**, supported by **DIAGNOSTIC / EXPERIMENTAL** results below. IMS `Direct Debit` frequently corresponds to SUN `ACH` or `Wire`. This strongly suggests payment type may be supplementary rather than a hard identity criterion, but Ascot must confirm the business meaning, including check-reference semantics and exceptions. The current veto remains LOCKED until a documented replacement is approved and validated. The shadow bypass disables the entire payment/check identity test; it does not establish a narrowly approved Direct Debit equivalence.

**Source/business exceptions — PENDING ASCOT CONFIRMATION:** explain Jan +300 and Feb −2,220; confirm March and June SUN export completeness; establish authoritative treatment of edited working-sheet values and missing accounts; explain void accounting-dimension discrepancies and repeated cancellation structures where business interpretation matters. These questions do not alter the locked canonical-sheet or internal net-zero rules.

## 6. DIAGNOSTIC / EXPERIMENTAL findings

### Payment/check sensitivity — DIAGNOSTIC / EXPERIMENTAL; policy change PENDING ASCOT CONFIRMATION

A separate in-memory verifier module disabled **only `payment_agrees`**, holding eligibility, exact names, period/entity scope, dates/order, amounts, candidate bounds, ambiguity handling, and non-reuse constant. No production rule was changed.

| Eligible population | Current production verified | Shadow without payment/check veto |
|---|---:|---:|
| Historical Jan–Jul | 324/731 (44.32%) | 401/731 (54.86%) |
| June | 60/102 (58.82%) | 90/102 (88.24%) |
| Historical July | 73/117 (62.39%) | 109/117 (93.16%) |
| Newly received July file | 73/117 (62.39%) | 109/117 (93.16%) |

Historical gain: **77**, with **0 previously verified lost**, **0 new candidate combinations**, and **0 new reuse conflicts**. **313 unsupported** and **17 reuse-conflict transactions** remain unresolved historically. Removing the veto exposes some previously masked ambiguity in already unresolved cases; it does not justify forcing those cases through. New July retains four unsupported and four reuse-conflict cases in the shadow.

Evidence: [historical sensitivity report](payment_type_sensitivity.md), which retains individual IMS/SUN witnesses; `data/validation/new_july_2026/processed/payment_type_comparison/{comparison_summary.json,run_a_current_results.jsonl,run_b_shadow_results.jsonl}`. Shadow `payment_identity_agrees=True` reflects bypass, not factual agreement of source fields.

### New July file — DIAGNOSTIC / EXPERIMENTAL new-file validation / replication check

This is **not a strict statistical holdout** and not out-of-sample generalization evidence. It tests stability when essentially the same underlying transactions arrive in a new source export/workpaper. Both policies reproduce historical July outcomes and selected SUN evidence for all **117 eligible** transactions, with **0 corresponding eligible outcome/evidence differences**.

The new workbook has **136** source transactions vs **137** historically: one outstanding Washington **−7,774.00** entry is absent; it was never SUN-eligible. New population: **116 cleared + 1 multiple-cleared-dates + 6 same-month void + 13 outstanding**, with **151 allocation records**. Row-based IDs shift for **77/136** shared transactions; comparison uses a unique business-key crosswalk, not arbitrary row pairing. All six voids pass three internal pairs and remain outside SUN.

The locked IMS sanitizer was not changed. A validation-only adapter explicitly excludes identified **G154 SUM footer**, assigns independently established **2026-07**, and isolates outputs. These are **DIAGNOSTIC / EXPERIMENTAL adapter accommodations**, not a general production footer/filename rule.

Evidence: [completed new-file report](../data/validation/new_july_2026/july_holdout_validation.md), `data/validation/new_july_2026/run_july_holdout.py`, `processed/adapter_manifest.json`, `processed/verification/transaction_comparison.jsonl`, verification outputs, and payment comparison artifacts under that directory. Existing filenames containing `holdout` are preserved historical labels; they do not establish statistical independence.

### Vendor-name design decision — LOCKED conservative boundary

Do **not** introduce Jaccard/fuzzy vendor-name matching simply to increase automation. Exact normalized names already support **109/117 July** in the payment-isolated diagnostic. That is evidence against an immediate need to loosen identity, not an approved 93.16% production rate. Uncertain semantic identity can remain human review. No arbitrary hard-coded similarity thresholds or aliases are current production rules.

An LLM-assisted human-review mechanism for semantic name resolution may be evaluated separately as **DIAGNOSTIC / EXPERIMENTAL** if needed; no such production mechanism is established by the current verifier/tests. This records the current governance direction, not a claim that an LLM name-resolution experiment has already passed validation.

## 7. SUPERSEDED interpretations and report stages

| SUPERSEDED position | Why replaced / current boundary | Provenance |
|---|---|---|
| Sending Same Month Void groups or positive/negative identity-context members to SUN, or allowing special void reuse | Version 5 limits voids to IMS-internal control; only actual-dated rows search/claim SUN. | `docs/ims_sun_verification.md`; verifier version 5 and internal-only void tests. |
| Mandatory shared reference for void cancellation | Inspection found zero shared explicit identifiers across 19 apparent pair slots; current control uses period/absolute amount and exact net zero. | `docs/same_month_void_structure_inspection.md`; `ims_preverification`. |
| Exploratory void graph/reciprocal-uniqueness recommendations as if they were implemented rules | Inspection proposals do not override the accepted pair/group net-zero control. Vendor/date/account similarity is not mandatory. | Same inspection vs version 5 implementation. |
| Earlier July report's “NOT RUN” as the latest validation outcome | Correct at initial compatibility stop; later isolated adapter enabled completed validation without changing production sanitization. | `data/validation/july_2026/july_holdout_validation.md` retained; completed report in `new_july_2026/`. |
| SUN inspection's “future sanitizer” / unresolved canonical-sheet selection as current implementation status | Subsequent sanitizer and QA use `Page1_1`; edited extracts remain evidence, not replacement sources. | SUN inspection → sanitizer QA → manifest/tests. |

Whole-month void netting, append-all-sheet SUN ingestion, arbitrary deduplication, fuzzy thresholds, and promoting manual corrections are prohibited alternatives; their presence as cautions here does **not** assert they were previously approved implementations. Likewise, “holdout” terminology in old artifacts is not a current statistical claim.

## 8. Open business questions and promotion requirements

| Status | Question / next required evidence |
|---|---|
| **PENDING ASCOT CONFIRMATION** | Are IMS Direct Debit / SUN ACH or Wire labels different representations of the same business event? Is payment type supplementary? What must remain mandatory for checks and numeric SUN payment fields? Obtain an explicit business decision before changing `payment_agrees`. |
| **PENDING ASCOT CONFIRMATION** | What causes Jan/Feb aggregate differences, and how should they be resolved/accounted for without hiding historical exceptions? |
| **PENDING ASCOT CONFIRMATION** | Are March/June SUN populations complete? Which source corrections are authoritative, including missing accounts and edited extracts? Preserve original values and explicit approvals. |
| **PENDING ASCOT CONFIRMATION** | What do repeated void structures, live/reissued payment alternatives, and the inspected June Lockton account discrepancy mean economically? Internal zero-net pass does not answer these accounting questions. |
| **DIAGNOSTIC / EXPERIMENTAL** | If semantic vendor resolution becomes necessary, define and evaluate a separate human-review mechanism with evidence and accountability before considering production integration. |
| **DIAGNOSTIC / EXPERIMENTAL** | Characterize future export/footer/filename variation before generalizing the new July adapter into production sanitization. |

For each eventual decision, record date, responsible decision-maker/reviewer, evidence, affected scope, tests/QA, and superseded rule. Preserve historical results and distinguish newly run versions. No unresolved question is resolved merely by this memo's creation.

## 9. Source-of-truth and verification index

The component sections above identify code, tests, reports, and manifests together. Operational evidence roots are `data/raw/` (original historical workbooks), `data/processed/` (canonical outputs and historical controls), and `data/validation/new_july_2026/` (isolated new-file experiment). Manifests/hashes establish which inputs produced each run; report prose alone is insufficient to infer a new rule.

| Component | Primary test / independent QA evidence |
|---|---|
| WF sanitizer/categories | `src/ascot/qa_aic_wf.py`; `data/processed/aic_wf_qa_report.json`; processing/category manifests |
| IMS sanitizer | `src/ascot/qa_aic_ims.py`; `data/processed/aic_ims_qa_report.json`; processing manifest and monthly validation JSONs |
| Previous Day / completeness | `src/ascot/qa_previous_day.py`; `tests/test_reconcile_previous_day_to_wf.py`; all-month summary/groups |
| IMS → WF | `tests/test_reconcile_current_month_ims_to_wf.py`; inspection reconstruction and reconciliation report/populations |
| Rejections / accountability | `src/ascot/review_rejections.py` evaluation/gate/demo; synthetic workflow/episode record; dedicated automated coverage not established |
| SUN sanitizer | `tests/test_sanitize_sun_jnl.py`; structure/QA reports; SUN manifest |
| Void and IMS → SUN | `tests/test_verify_ims_sun.py`, including historical witnesses and no-search/no-reuse exclusion tests; rules-v5 manifest/results |
| Payment sensitivity / new July | Historical witness report; isolated adapter manifest; business-key crosswalk; A/B JSONL results and comparison summary |

## 10. Change log

| Date | Status / evidence-backed record |
|---|---|
| 2026-09-13 | Repository history records the basic synthetic routing workflow; **DIAGNOSTIC / EXPERIMENTAL** example thresholds do not establish accounting policy. |
| 2026-09-14 | Repository commits record AIC cash controls, current-month IMS/WF validation, and rejection finalization control. Current accepted controls are **LOCKED** as scoped above. |
| 2026-09-15 | Requested historical memo provenance date; file not located. No contents reconstructed or historical artifact altered. |
| 2026-10-26 | Reviewed existing later SUN inspection/sanitization/QA, void inspection, rules-v5 code/tests/manifests, sensitivity evidence, and completed July validation. Consolidated **LOCKED** internal-only void handling; marked prior SUN-void routing **SUPERSEDED**. Recorded payment relaxation as **PENDING ASCOT CONFIRMATION** supported only by **DIAGNOSTIC / EXPERIMENTAL** runs. Corrected current interpretation of July to replication, and recorded the **LOCKED** no-fuzzy-threshold design boundary. This is the review/consolidation date, not an invented date of prior business approval. |
| 2026-10-26 — historical-principle migration | Project owner supplied earlier decisions from the outside-repository historical memo/development discussions. Carried forward **LOCKED** empirical inspection, episode/decision-level allocation, human ownership and material audit trail, general processing, WF structural boundaries, upstream-control-to-JE architecture, exception routing, and evidence/matching governance. Checked against sanitizer code, QA, synthetic workflow skeleton, rejection gate, and current verifier. No newly supplied principle required **SUPERSEDED** status; existing superseded component rules in section 7 remain unchanged. |

Validation on 2026-10-26: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` — **77 passed**. This verifies the current suite, not unresolved business meanings or unimplemented orchestration. Reviewed `git diff` and the new-file diff; a before/after content-hash inventory confirmed that this memo is the only added file and no existing non-cache project file changed. The pre-existing deletion of `src/ascot/inspect_current_month_control_variances.py` and other pre-existing untracked work were left untouched.

Documentation-only consolidation: no sanitizer, reconciliation/verifier code, tests, source workbook, manifest, or historical report/output is changed by this memo.

Historical-principle migration validation: reviewed the incremental before/after memo diff and `git diff`; content-hash comparison confirmed that only this documentation file changed during the migration. The 77-test result above belongs to the initial consolidation; tests were not rerun for this prose-only update.
