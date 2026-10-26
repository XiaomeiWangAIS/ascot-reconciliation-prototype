"""Conservative AIC IMS verification using locked canonical IMS and SUN inputs.

Run: python -m src.ascot.verify_ims_sun
Vendor/date ordering generates bounded local contiguous or one-gap candidates.
Proximity ranks evidence but cannot establish verification or break ambiguity.
"""
import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

VERIFIED = 'VERIFIED'
REVIEW = 'HUMAN_REVIEW_REQUIRED'
# Canonical files contain observed Excel artifacts of about 1e-7 dollars.
# This reconciles precision noise, never a cent-level discrepancy.
PRECISION_TOLERANCE = Decimal('0.00001')
MAX_BUCKET_ROWS = 64
MAX_CANDIDATE_SPAN = 18
MAX_COMBINATIONS = 256
AIC_ACCOUNT = ('AIC', 'AIC Disbursements (2693)', '13012085')
RULES_VERSION = '5'


def identity(value):
    """Case/punctuation/whitespace only; no vendor aliases or removed words."""
    return re.sub(r'[^\w]', '', str(value or '').casefold())


def money(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else None
    except (InvalidOperation, ValueError):
        return None


def parsed_date(value):
    try:
        return date.fromisoformat(str(value).strip().replace('/', '-'))
    except ValueError:
        return None


def row_key(row):
    return (row['source_file'], row['source_sheet'], str(row['source_row']))


def source_ref(row):
    return dict(zip(('source_file', 'source_sheet', 'source_row'), row_key(row)))


def clearing_dates(row):
    values = str(row.get('cleared_dates') or '').split('|')
    dates = [parsed_date(v) for v in values]
    if row.get('cleared_status') not in ('cleared', 'multiple_cleared_dates') or not all(dates):
        return None
    if row.get('cleared_status') == 'cleared' and len(set(dates)) != 1:
        return None
    return dates


def ims_preverification(ims_rows):
    """Run IMS-only controls before candidate generation; exact void netting."""
    controls, groups = {}, defaultdict(list)
    for row in ims_rows:
        tid = row['transaction_id']
        if row.get('cleared_status') == 'same_month_void':
            signed = money(row.get('source_signed_amount'))
            key = (row['accounting_period'], abs(signed) if signed is not None else tid)
            groups[key].append(row)
        else:
            passed = bool(clearing_dates(row))
            controls[tid] = dict(status='PASSED' if passed else 'FAILED',
                                 method='VALID_CLEARING_EVIDENCE' if passed else None,
                                 reason_code=None if passed else 'DATE_CLEARED_MISSING_OR_INVALID')
    void_groups = {}
    for (period, absolute), members in groups.items():
        members = sorted(members, key=lambda r: r['transaction_id'])
        amounts = [money(r.get('source_signed_amount')) for r in members]
        valid = all(a is not None and a != 0 for a in amounts)
        net = sum(amounts, Decimal(0)) if valid else None
        passed = valid and net == 0
        amount_label = format(absolute.normalize(), 'f') if isinstance(absolute, Decimal) else absolute
        gid = f'VOID-{period}-{amount_label}'
        activities = [r for r in members if money(r.get('source_signed_amount')) is not None
                      and money(r['source_signed_amount']) < 0
                      and identity(r.get('source_description')) not in ('', 'void')
                      and identity(r.get('method')) != 'v'
                      and identity(r.get('payment_type')) in ('check', 'ach', 'wire', 'directdebit')]
        control = dict(status='PASSED' if passed else 'FAILED',
                       method=('SAME_MONTH_VOID_NET_ZERO' if len(members) == 2 else 'SAME_MONTH_VOID_NET_ZERO_GROUP') if passed else None,
                       reason_code=None if passed else 'VOID_NOT_NETTED_TO_ZERO',
                       group_id=gid, group_member_ids=[r['transaction_id'] for r in members],
                       group_signed_amounts={r['transaction_id']: r.get('source_signed_amount') for r in members},
                       group_net_amount=str(net) if net is not None else None,
                       payment_activity_ids=[r['transaction_id'] for r in activities])
        void_groups[gid] = members
        for row in members:
            controls[row['transaction_id']] = control.copy()
    return controls, void_groups


def payment_agrees(ims, sun):
    method = identity(ims.get('payment_type'))
    raw = str(sun.get('payment_type_raw') or '').strip()
    if method == 'check':
        # Historical June/July check numbers agree exactly with SUN Payment Type.
        ref = str(ims.get('check_or_ref') or '').strip()
        return bool(ref and raw == ref)
    return method in ('ach', 'wire', 'directdebit') and method == identity(raw)


def ordered_evidence(pool):
    return sorted(pool, key=lambda r: (
        parsed_date(r.get('paid_date')) or date.max,
        r['source_file'], r['source_sheet'], int(r['source_row'])))


def local_window(ims, pool):
    """Retain the whole vendor cluster; dates anchor ranking, never exclusion."""
    anchors = [parsed_date(ims.get('transaction_datetime', '')[:10])]
    anchors.extend(clearing_dates(ims) or [])
    anchors = [d for d in anchors if d]
    ordered = ordered_evidence(pool)
    # Date is a ranking signal, never a hard day-count filter. Locality is
    # enforced by contiguous/one-gap spans in the exact vendor/date ordering.
    local = ordered
    return local, anchors, ordered


def reconcile_candidates(ims, pool, *, sun_target_amount=None):
    """Enumerate local ordered spans, never arbitrary monthly subsets.

    A one-gap span additionally needs a common nonempty invoice reference on
    selected rows. All plausible local sums remain rivals regardless of rank.
    """
    # Normal transactions retain their existing sign convention. A void target
    # is supplied explicitly from positive group members, independently of the
    # negative member whose vendor/payment fields provide identity context.
    target = -money(ims['source_signed_amount']) if sun_target_amount is None else sun_target_amount
    rows, anchors, ordered = local_window(ims, pool)
    invalid = any(money(r.get('amount')) is None or not parsed_date(r.get('paid_date'))
                  or r.get('currency') != 'USD' or r.get('debit_credit') != 'D' for r in rows)
    if invalid or not anchors:
        return [], False, True
    if len(rows) > MAX_BUCKET_ROWS:
        return [], True, False
    positions = {row_key(r): i for i, r in enumerate(ordered)}
    candidates, seen = [], set()
    for start in range(len(rows)):
        for end in range(start + 1, min(len(rows), start + MAX_CANDIDATE_SPAN) + 1):
            span = rows[start:end]
            # Spans must preserve vendor/date ordering.
            if positions[row_key(span[-1])] - positions[row_key(span[0])] != len(span) - 1:
                continue
            groups = [(span, 0)]
            for gap in range(1, len(span) - 1):
                group = span[:gap] + span[gap + 1:]
                references = {r.get('transaction_reference', '').strip() for r in group}
                if len(references) == 1 and '' not in references:
                    groups.append((group, 1))
            for group, gaps in groups:
                key = tuple(row_key(r) for r in group)
                if key in seen:
                    continue
                seen.add(key)
                total = sum((money(r['amount']) for r in group), Decimal(0))
                if abs(total - target) > PRECISION_TOLERANCE:
                    continue
                proximity = max(min(abs((parsed_date(r['paid_date']) - d).days) for d in anchors) for r in group)
                center = sum(positions[row_key(r)] for r in group) / len(group)
                order_distance = abs(center - ims.get('_expected_sun_position', center))
                candidates.append({
                    'sun_rows': [source_ref(r) for r in group],
                    'sun_amount': str(total), 'difference': str(total - target),
                    'payment_identity_agrees': all(payment_agrees(ims, r) for r in group),
                    'vendor_identity': identity(ims.get('source_description')),
                    'paid_dates': sorted({r['paid_date'] for r in group}),
                    'transaction_references': sorted({r.get('transaction_reference', '') for r in group}),
                    'account_agreement_count': sum(r.get('account_code') == ims.get('account_raw') for r in group),
                    'cost_center_agreement_count': sum(r.get('cost_center') == ims.get('cost_center_raw') for r in group),
                    'ordering_evidence': dict(gaps=gaps, max_anchor_distance_days=proximity,
                                              relative_order_distance=order_distance,
                                              vendor_positions=[positions[row_key(r)] for r in group]),
                    'rank': [gaps, proximity, order_distance],
                })
                if len(candidates) >= MAX_COMBINATIONS:
                    return sorted(candidates, key=lambda c: c['rank']), True, False
    return sorted(candidates, key=lambda c: c['rank']), False, False


def verify_transactions(ims_rows, sun_rows):
    """Return one auditable result per IMS source transaction, in input order."""
    ids = [r['transaction_id'] for r in ims_rows]
    if len(set(ids)) != len(ids) or any(not value for value in ids):
        raise ValueError('IMS transaction identifiers must be unique and nonempty')
    keys = [row_key(r) for r in sun_rows]
    if len(set(keys)) != len(keys):
        raise ValueError('SUN source provenance must be unique; duplicate lines need distinct source rows')
    controls, _ = ims_preverification(ims_rows)
    population = defaultdict(list)
    for row in sun_rows:
        entity = tuple(row.get(k) for k in ('company', 'bank_account_name', 'bank_account_code'))
        if entity == AIC_ACCOUNT and row.get('source_sheet') == 'Page1_1':
            population[(row['accounting_period'], identity(row.get('description')))].append(row)
    vendor_ims = defaultdict(list)
    for row in ims_rows:
        if clearing_dates(row):
            vendor_ims[(row['accounting_period'], identity(row.get('source_description')))].append(row)
    relative_positions = {}
    for key, rows in vendor_ims.items():
        rows = sorted(rows, key=lambda r: (r.get('transaction_datetime', ''), r['transaction_id']))
        count = len(population.get(key, []))
        for rank, row in enumerate(rows):
            relative_positions[row['transaction_id']] = (rank + 0.5) * count / len(rows) - 0.5
    results = []
    claims = defaultdict(set)
    for ims in ims_rows:
        tid = ims['transaction_id']
        signed = money(ims.get('source_signed_amount'))
        result = dict(rules_version=RULES_VERSION, ims_transaction_id=tid, accounting_period=ims['accounting_period'],
                      ims_source=ims.copy(), status=REVIEW, verification_method=None,
                      reason_code=None, reason_codes=[], ims_signed_amount=str(signed) if signed is not None else None,
                      expected_sun_amount=str(-signed) if signed is not None else None,
                      matched_sun_rows=[], matched_sun_amount=None, candidate_combinations=[],
                      candidate_sun_rows=[], evidence_reuse_conflicts=[],
                      ims_internal_control=controls[tid], sun_evidence_attempted=False,
                      sun_verification_method=None, sun_eligible=bool(clearing_dates(ims)),
                      sun_verification_status='PENDING' if clearing_dates(ims) else 'NOT_APPLICABLE',
                      sun_exclusion_reason=None)
        results.append(result)

        def review(reason):
            result['reason_code'] = reason
            result['reason_codes'] = [reason]

        control = controls[tid]
        if not result['sun_eligible']:
            result['expected_sun_amount'] = None
            if ims.get('cleared_status') == 'same_month_void':
                result['sun_exclusion_reason'] = 'SAME_MONTH_VOID_INTERNAL_CONTROL_ONLY'
                # Retain the existing internal result separately. REVIEW is the
                # legacy whole-record routing status, not a SUN failure or a
                # requirement to obtain SUN support for an excluded void.
                review(control['reason_code'] or 'SAME_MONTH_VOID_INTERNAL_CONTROL_ONLY')
            else:
                result['sun_exclusion_reason'] = 'DATE_CLEARED_MISSING_OR_INVALID'
                review('DATE_CLEARED_MISSING_OR_INVALID')
            continue
        dates = clearing_dates(ims) or []
        result['sun_evidence_attempted'] = True
        if signed is None or signed == 0:
            review('OTHER_UNRESOLVED')
            continue
        vendor = identity(ims.get('source_description'))
        pool = population.get((ims['accounting_period'], vendor), []) if vendor else []
        local, anchors, ordered = local_window(ims, pool)
        result['candidate_window'] = dict(date_hard_cutoff_days=None,
                                          anchor_dates=[d.isoformat() for d in anchors],
                                          vendor_cluster_rows=len(ordered), local_rows=len(local),
                                          expected_sun_position=relative_positions.get(tid))
        result['candidate_sun_rows'] = [{k: v for k, v in r.items() if k != 'raw_values_json'} for r in local]
        ranked_ims = dict(ims, _expected_sun_position=relative_positions.get(tid, 0))
        candidates, bounded, invalid = reconcile_candidates(ranked_ims, pool)
        result['candidate_combinations'] = candidates
        result['search_complete'] = not bounded
        for c in candidates:
            for ref in c['sun_rows']:
                claims[row_key(ref)].add(tid)
        if bounded or invalid:
            # Unexamined or invalid identity-linked evidence can rival another
            # transaction's candidate: reserve the entire pool conservatively.
            for r in local:
                claims[row_key(r)].add(tid)
            review('OTHER_UNRESOLVED' if bounded else 'SUN_EVIDENCE_CONFLICT')
            result['review_detail'] = 'Candidate search bound reached' if bounded else 'Invalid SUN amount/date/currency/debit-credit evidence'
            continue
        if not candidates:
            review('NOT_SUPPORTED_BY_SUN')
        elif any(not c['payment_identity_agrees'] for c in candidates):
            review('SUN_EVIDENCE_CONFLICT')
        elif len(candidates) > 1:
            review('MULTIPLE_PLAUSIBLE_SUN_COMBINATIONS' if any(len(c['sun_rows']) > 1 for c in candidates) else 'MULTIPLE_PLAUSIBLE_SUN_MATCHES')
        else:
            candidate = candidates[0]
            result.update(status=VERIFIED,
                          verification_method='ONE_TO_ONE' if len(candidate['sun_rows']) == 1 else 'ONE_TO_MANY',
                          matched_sun_rows=candidate['sun_rows'], matched_sun_amount=candidate['sun_amount'],
                          identity_evidence=candidate,
                          sun_verification_method='ONE_TO_ONE' if len(candidate['sun_rows']) == 1 else 'ONE_TO_MANY',
                          cleared_dates=[d.isoformat() for d in dates])
    # Two-pass conflict resolution: ambiguous candidates also reserve evidence.
    by_id = {r['ims_transaction_id']: r for r in results}
    for key, owners in claims.items():
        if len(owners) < 2:
            continue
        for tid in owners:
            result = by_id[tid]
            result['evidence_reuse_conflicts'].append(dict(sun_row=dict(zip(('source_file', 'source_sheet', 'source_row'), key)), competing_ims_ids=sorted(owners - {tid})))
            if 'SUN_ROW_REUSE_CONFLICT' not in result['reason_codes']:
                result['reason_codes'].append('SUN_ROW_REUSE_CONFLICT')
            result.update(status=REVIEW, reason_code='SUN_ROW_REUSE_CONFLICT',
                          verification_method=None, sun_verification_method=None, matched_sun_rows=[], matched_sun_amount=None)
    for result in results:
        if result['sun_eligible']:
            result['sun_verification_status'] = result['status']
    return results


def summarize(results):
    summaries = []
    for period in sorted({r['accounting_period'] for r in results}):
        rows = [r for r in results if r['accounting_period'] == period]
        normal = [r for r in rows if r['ims_source'].get('cleared_status') != 'same_month_void']
        voids = [r for r in rows if r['ims_source'].get('cleared_status') == 'same_month_void']
        groups = {r['ims_internal_control']['group_id']: r['ims_internal_control'] for r in voids}
        verified = sum(r['status'] == VERIFIED for r in rows)
        methods = Counter(r['sun_verification_method'] for r in rows if r['status'] == VERIFIED)
        summaries.append(dict(accounting_period=period, ims_source_transactions=len(rows),
                              sun_eligible_count=sum(r['sun_eligible'] for r in rows),
                              sun_excluded_count=sum(not r['sun_eligible'] for r in rows),
                              sun_verified=verified,
                              sun_human_review_required=sum(r['sun_eligible'] and r['status'] == REVIEW for r in rows),
                              sun_review_reason_code_counts=dict(Counter(r['reason_code'] for r in rows if r['sun_eligible'] and r['status'] == REVIEW)),
                              sun_exclusion_reason_counts=dict(Counter(r['sun_exclusion_reason'] for r in rows if not r['sun_eligible'])),
                              verified=verified, one_to_one=methods['ONE_TO_ONE'], one_to_many=methods['ONE_TO_MANY'],
                              same_month_void_verified=sum(r['status'] == VERIFIED for r in voids),
                              human_review_required=len(rows)-verified,
                              normal=dict(total=len(normal),
                                          valid_clearing=sum(r['ims_internal_control']['status'] == 'PASSED' for r in normal),
                                          invalid_missing_clearing=sum(r['ims_internal_control']['status'] != 'PASSED' for r in normal),
                                          sun_verified=sum(r['status'] == VERIFIED for r in normal),
                                          sun_human_review_required=sum(r['sun_evidence_attempted'] and r['status'] == REVIEW for r in normal)),
                              same_month_void=dict(total_rows=len(voids),
                                                   sun_excluded_rows=sum(not r['sun_eligible'] for r in voids),
                                                   internal_passed_rows=sum(r['ims_internal_control']['status'] == 'PASSED' for r in voids),
                                                   internal_reason_code_counts=dict(Counter(r['ims_internal_control']['reason_code'] for r in voids if r['ims_internal_control']['reason_code'])),
                                                   zero_net_unique_pairs=sum(c['method'] == 'SAME_MONTH_VOID_NET_ZERO' for c in groups.values()),
                                                   zero_net_groups=sum(c['method'] == 'SAME_MONTH_VOID_NET_ZERO_GROUP' for c in groups.values()),
                                                   internal_failure_groups=sum(c['status'] == 'FAILED' for c in groups.values()),
                                                   internal_failure_rows=sum(r['ims_internal_control']['status'] == 'FAILED' for r in voids),
                                                   proceeding_to_sun_rows=sum(r['sun_evidence_attempted'] for r in voids),
                                                   proceeding_to_sun_groups=len({r['ims_internal_control']['group_id'] for r in voids if r['sun_evidence_attempted']}),
                                                   payment_activities_searched=sum(r['ims_transaction_id'] in r['ims_internal_control']['payment_activity_ids'] and r['sun_evidence_attempted'] for r in voids),
                                                   verified_rows=sum(r['status'] == VERIFIED for r in voids),
                                                   sun_supported_groups=len({r['ims_internal_control']['group_id'] for r in voids if r['status'] == VERIFIED}),
                                                   sun_review_groups=len({r['ims_internal_control']['group_id'] for r in voids if r['sun_eligible'] and r['status'] == REVIEW}),
                                                   human_review_rows=sum(r['status'] == REVIEW for r in voids),
                                                   reason_code_counts=dict(Counter(r['reason_code'] for r in voids if r['status'] == REVIEW))),
                              reason_code_counts=dict(Counter(r['reason_code'] for r in rows if r['status'] == REVIEW)),
                              all_reason_code_counts=dict(Counter(c for r in rows for c in r['reason_codes'])),
                              sun_reuse_conflict_cases=sum(bool(r['evidence_reuse_conflicts']) for r in rows),
                              sun_reuse_conflict_rows=len({row_key(c['sun_row']) for r in rows for c in r['evidence_reuse_conflicts']}),
                              automatic_verification_rate=verified/len(rows), human_review_rate=(len(rows)-verified)/len(rows)))
    return summaries


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ims', type=Path, default=Path('data/processed/aic_ims_all_months_transactions.csv'))
    parser.add_argument('--sun-dir', type=Path, default=Path('data/processed/sun_jnl'))
    parser.add_argument('--output-dir', type=Path, default=Path('data/processed/verification/ims_to_sun'))
    args = parser.parse_args()
    files = sorted(args.sun_dir.glob('sun_jnl_????-??.csv'))
    if not files:
        raise FileNotFoundError('No canonical SUN files found')
    ims = read_csv(args.ims)
    sun = [r for p in files for r in read_csv(p)]
    missing = {r['accounting_period'] for r in ims} - {r['accounting_period'] for r in sun}
    if missing:
        raise ValueError(f'Missing SUN periods: {sorted(missing)}')
    results = verify_transactions(ims, sun)
    summary = summarize(results)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with (args.output_dir / 'verification_results.jsonl').open('w', encoding='utf-8') as stream:
        for result in results:
            stream.write(json.dumps(result, ensure_ascii=False) + '\n')
    (args.output_dir / 'verification_summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    inputs = []
    for path in [args.ims, *files]:
        with path.open('rb') as stream:
            inputs.append(dict(path=str(path), sha256=hashlib.file_digest(stream, 'sha256').hexdigest()))
    manifest = dict(rules_version=RULES_VERSION, inputs=inputs,
                    source_sheet='Page1_1', aic_entity_account=AIC_ACCOUNT,
                    precision_tolerance=str(PRECISION_TOLERANCE),
                    max_local_rows=MAX_BUCKET_ROWS, max_candidate_span=MAX_CANDIDATE_SPAN,
                    date_hard_cutoff_days=None, max_candidate_combinations=MAX_COMBINATIONS,
                    ims_void_control='Exact net zero by accounting period and absolute signed amount; no mandatory shared reference',
                    sun_eligibility='Valid normalized actual cleared dates with cleared/multiple_cleared_dates status only; same-month void is internal-control-only and never claims SUN evidence',
                    candidate_scope='Dated eligible IMS only; same period and vendor; date ranking without day cutoff; contiguous spans or one gap with shared invoice reference; ranking never resolves ambiguity',
                    total_ims_transactions=len(results), monthly_summary_file='verification_summary.json',
                    results_file='verification_results.jsonl')
    (args.output_dir / 'verification_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
