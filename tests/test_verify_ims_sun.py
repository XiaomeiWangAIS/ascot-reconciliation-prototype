from copy import deepcopy

import pytest

from src.ascot.verify_ims_sun import REVIEW, VERIFIED, summarize, verify_transactions


def ims(tid='I1', amount='-100', **changes):
    row = dict(transaction_id=tid, accounting_period='2026-07', source_workbook='ims.xlsx',
               source_sheet='AIC IMS', source_row='3', source_signed_amount=amount,
               transaction_datetime='2026-07-01', source_description='Vendor, Inc.',
               cleared_status='cleared', cleared_dates='2026/07/03', date_cleared_raw='2026/07/03',
               payment_type='ACH', check_or_ref='', account_raw='100', cost_center_raw='FINU')
    return dict(row, **changes)


def sun(row='6', amount='100', **changes):
    record = dict(source_file='sun.xlsx', source_sheet='Page1_1', source_row=row,
                  accounting_period='2026-07', amount=amount, description='Vendor Inc',
                  paid_date='2026-07-02', company='AIC', bank_account_name='AIC Disbursements (2693)',
                  bank_account_code='13012085', currency='USD', debit_credit='D',
                  payment_type_raw='ACH', transaction_reference='invoice-1',
                  account_code='100', cost_center='FINU', line_description='Invoice allocation')
    return dict(record, **changes)


def test_one_to_one_with_non_equal_dates_and_precision_noise():
    result, = verify_transactions([ims(amount='-99.99999997')], [sun()])
    assert result['status'] == VERIFIED
    assert result['verification_method'] == 'ONE_TO_ONE'
    assert result['matched_sun_rows'][0]['source_row'] == '6'
    assert result['ims_source']['transaction_id'] == 'I1'


def test_one_to_many_across_invoice_references_with_negative_allocation():
    rows = [sun('6', '80'), sun('7', '30', transaction_reference='invoice-2'), sun('8', '-10')]
    result, = verify_transactions([ims()], rows)
    assert result['status'] == VERIFIED
    assert result['verification_method'] == 'ONE_TO_MANY'
    assert len(result['matched_sun_rows']) == 3
    assert result['matched_sun_amount'] == '100'


def test_multiple_one_to_one_candidates():
    result, = verify_transactions([ims()], [sun(), sun('7')])
    assert result['status'] == REVIEW
    assert result['reason_code'] == 'MULTIPLE_PLAUSIBLE_SUN_MATCHES'
    assert len(result['candidate_combinations']) == 2


def test_multiple_combinations_and_no_single_match_precedence():
    result, = verify_transactions([ims()], [sun(), sun('7', '60'), sun('8', '40')])
    assert result['status'] == REVIEW
    assert result['reason_code'] == 'MULTIPLE_PLAUSIBLE_SUN_COMBINATIONS'


def test_two_distinct_one_to_many_combinations():
    result, = verify_transactions([ims()], [sun('6', '60'), sun('7', '40'),
                                           sun('8', '70'), sun('9', '30')])
    assert result['status'] == REVIEW
    assert result['reason_code'] == 'MULTIPLE_PLAUSIBLE_SUN_COMBINATIONS'
    assert len(result['candidate_combinations']) == 2
    assert all(len(c['sun_rows']) == 2 for c in result['candidate_combinations'])


def test_unsupported_and_no_amount_only_matching():
    result, = verify_transactions([ims()], [sun(description='Unrelated vendor')])
    assert result['status'] == REVIEW
    assert result['reason_code'] == 'NOT_SUPPORTED_BY_SUN'


def test_reuse_conflict_affects_both_transactions_and_is_order_independent():
    rows = [ims(), ims('I2')]
    before = deepcopy(rows)
    results = verify_transactions(rows, [sun()])
    assert rows == before
    assert all(r['reason_code'] == 'SUN_ROW_REUSE_CONFLICT' for r in results)
    assert all(r['status'] == REVIEW and not r['matched_sun_rows'] for r in results)
    assert {r['ims_transaction_id']: r for r in results} == {
        r['ims_transaction_id']: r for r in verify_transactions(rows[::-1], [sun()])}
    assert summarize(results)[0]['sun_reuse_conflict_cases'] == 2
    assert summarize(results)[0]['sun_reuse_conflict_rows'] == 1


def test_ambiguous_transaction_also_reserves_rows():
    results = verify_transactions([ims(), ims('I2', payment_type='Check', check_or_ref='4447')],
                                  [sun(payment_type_raw='4447')])
    assert all(r['reason_code'] == 'SUN_ROW_REUSE_CONFLICT' for r in results)
    assert 'SUN_EVIDENCE_CONFLICT' in results[0]['reason_codes']


def void_pair(second_amount='100'):
    return [ims(cleared_status='same_month_void', cleared_dates='', check_or_ref='4447', payment_type='Check'),
            ims('I2', second_amount, cleared_status='same_month_void', cleared_dates='', check_or_ref='Void',
                source_description='Void', date_cleared_raw='Same Month Void Check #4447')]






def test_nonzero_void_stops_before_sun(monkeypatch):
    import src.ascot.verify_ims_sun as module
    def forbidden(*args):
        pytest.fail('SUN matching attempted after failed precontrol')
    monkeypatch.setattr(module, 'reconcile_candidates', forbidden)
    results = module.verify_transactions(void_pair('99'), [sun(payment_type_raw='4447')])
    assert all(r['reason_code'] == 'VOID_NOT_NETTED_TO_ZERO' for r in results)
    assert all(not r['sun_evidence_attempted'] for r in results)






def test_internal_void_uses_exact_net_not_sun_precision_tolerance():
    results = verify_transactions(void_pair('100.00000001'), [])
    assert all(r['ims_internal_control']['status'] == 'FAILED' for r in results)


def test_invalid_clearing_never_calls_sun(monkeypatch):
    import src.ascot.verify_ims_sun as module
    def forbidden(*args):
        pytest.fail('SUN matching attempted with invalid clearing')
    monkeypatch.setattr(module, 'reconcile_candidates', forbidden)
    result, = module.verify_transactions([ims(cleared_dates='invalid')], [sun()])
    assert not result['sun_evidence_attempted']
    assert result['reason_code'] == 'DATE_CLEARED_MISSING_OR_INVALID'


@pytest.mark.parametrize('status,dates', [('cleared', ''), ('cleared', '2026/02/30'),
                                          ('outstanding', '2026/07/02'), ('returned', ''),
                                          ('void_reference', ''), ('multiple_cleared_dates', '2026/07/02|invalid')])
def test_missing_or_invalid_clearing(status, dates):
    result, = verify_transactions([ims(cleared_status=status, cleared_dates=dates)], [sun()])
    assert result['status'] == REVIEW
    assert result['reason_code'] == 'DATE_CLEARED_MISSING_OR_INVALID'
    assert not result['candidate_combinations']


def test_multiple_valid_clearing_dates_are_evidence():
    result, = verify_transactions([ims(cleared_status='multiple_cleared_dates',
                                     cleared_dates='2026/07/02|2026/07/03')], [sun()])
    assert result['status'] == VERIFIED


@pytest.mark.parametrize('changes', [dict(company='AICRE', bank_account_name='AIC Reinsurance (8427)', bank_account_code='13012094'),
                                    dict(company='AAIC'), dict(bank_account_code='wrong'),
                                    dict(accounting_period='2026-06')])
def test_exact_entity_and_period_scope(changes):
    result, = verify_transactions([ims()], [sun(**changes)])
    assert result['status'] == REVIEW
    assert result['reason_code'] == 'NOT_SUPPORTED_BY_SUN'


def test_check_number_identity_and_method_conflict():
    record = ims(payment_type='Check', check_or_ref='4447')
    result, = verify_transactions([record], [sun(payment_type_raw='4447')])
    assert result['status'] == VERIFIED
    result, = verify_transactions([record], [sun(payment_type_raw='4448')])
    assert result['reason_code'] == 'SUN_EVIDENCE_CONFLICT'


def test_search_bound_never_verifies_partial_solution():
    result, = verify_transactions([ims()], [sun(str(n), '100') for n in range(65)])
    assert result['status'] == REVIEW
    assert result['reason_code'] == 'OTHER_UNRESOLVED'
    assert result['search_complete'] is False


def test_pennies_are_not_precision_noise():
    result, = verify_transactions([ims()], [sun(amount='100.01')])
    assert result['status'] == REVIEW


def test_nearby_different_paid_dates_can_combine():
    result, = verify_transactions([ims()], [sun(amount='60'), sun('7', '40', paid_date='2026-07-03')])
    assert result['status'] == VERIFIED
    assert result['verification_method'] == 'ONE_TO_MANY'


def test_duplicate_provenance_and_ims_ids_fail_explicitly():
    with pytest.raises(ValueError):
        verify_transactions([ims(), ims()], [])
    with pytest.raises(ValueError):
        verify_transactions([ims()], [sun(), sun()])


def test_historical_witnesses_and_row_conservation():
    """Validate real evidence independently of the published summary counters."""
    from decimal import Decimal
    from pathlib import Path
    from src.ascot.verify_ims_sun import PRECISION_TOLERANCE, read_csv, row_key

    ims_path = Path('data/processed/aic_ims_all_months_transactions.csv')
    sun_files = sorted(Path('data/processed/sun_jnl').glob('sun_jnl_2026-??.csv'))
    if not ims_path.exists() or len(sun_files) != 7:
        pytest.skip('Local historical canonical inputs not available')
    transactions = read_csv(ims_path)
    evidence = [r for p in sun_files for r in read_csv(p)]
    lookup = {row_key(r): r for r in evidence}
    results = verify_transactions(transactions, evidence)
    assert len(results) == len(transactions)
    assert {r['ims_transaction_id'] for r in results} == {r['transaction_id'] for r in transactions}
    consumed = set()
    for result in results:
        if result['status'] != VERIFIED:
            assert result['reason_code']
            assert not result['matched_sun_rows']
            continue
        assert result['verification_method'] in ('ONE_TO_ONE', 'ONE_TO_MANY', 'SAME_MONTH_VOID_NET_ZERO', 'SAME_MONTH_VOID_NET_ZERO_GROUP')
        assert not result['reason_code']
        refs = result['matched_sun_rows']
        if not refs:
            assert result['verification_method'] == 'SAME_MONTH_VOID_NET_ZERO'
            continue
        total = Decimal(0)
        for ref in refs:
            key = row_key(ref)
            assert key not in consumed
            consumed.add(key)
            row = lookup[key]
            assert row['company'] == 'AIC'
            assert row['bank_account_code'] == '13012085'
            assert row['bank_account_name'] == 'AIC Disbursements (2693)'
            assert row['accounting_period'] == result['accounting_period']
            total += Decimal(row['amount'])
        assert abs(total + Decimal(result['ims_source']['source_signed_amount'])) <= PRECISION_TOLERANCE


def test_no_seven_day_hard_cutoff_for_ordered_support():
    result, = verify_transactions([ims()], [sun(amount='60'), sun('7', '40', paid_date='2026-07-25')])
    assert result['status'] == VERIFIED
    assert result['candidate_window']['date_hard_cutoff_days'] is None
    assert result['candidate_window']['local_rows'] == 2
    assert result['verification_method'] == 'ONE_TO_MANY'


def test_near_contiguous_shared_reference_and_stable_source_order():
    rows = [sun('6', '60'), sun('7', '999', transaction_reference='unrelated'), sun('8', '40')]
    first, = verify_transactions([ims()], rows)
    reverse, = verify_transactions([ims()], rows[::-1])
    assert first == reverse
    assert first['status'] == VERIFIED
    assert first['identity_evidence']['ordering_evidence']['gaps'] == 1
    assert [r['source_row'] for r in first['matched_sun_rows']] == ['6', '8']


def test_noncontiguous_unrelated_invoices_not_combined():
    rows = [sun('6', '60', transaction_reference='a'), sun('7', '999'),
            sun('8', '40', transaction_reference='b')]
    result, = verify_transactions([ims()], rows)
    assert result['status'] == REVIEW
    assert not result['candidate_combinations']


def test_arbitrary_multiple_gaps_not_searched():
    rows = [sun('6', '60'), sun('7', '999'), sun('8', '888'), sun('9', '40')]
    result, = verify_transactions([ims()], rows)
    assert result['status'] == REVIEW
    assert not result['candidate_combinations']


def test_proximity_ranking_never_resolves_two_plausible_candidates():
    result, = verify_transactions([ims()], [sun(), sun('7', paid_date='2026-07-06')])
    assert result['status'] == REVIEW
    assert result['reason_code'] == 'MULTIPLE_PLAUSIBLE_SUN_MATCHES'
    assert result['candidate_combinations'][0]['rank'] < result['candidate_combinations'][1]['rank']










def test_explicit_target_does_not_derive_amount_from_identity_context():
    from decimal import Decimal
    from src.ascot.verify_ims_sun import reconcile_candidates
    candidates, bounded, invalid = reconcile_candidates(
        ims(amount='-999'), [sun()], sun_target_amount=Decimal('100'))
    assert len(candidates) == 1
    assert candidates[0]['sun_amount'] == '100'
    assert not bounded and not invalid






@pytest.mark.parametrize('status,dates', [('same_month_void',''), ('same_month_void','2026/07/03'),
                                         ('outstanding','2026/07/03'), ('returned',''),
                                         ('',''), ('void_reference',''), ('other_non_date_text','')])
def test_non_dated_status_never_searches_or_claims_sun(monkeypatch, status, dates):
    import src.ascot.verify_ims_sun as module
    def forbidden(*args, **kwargs):
        pytest.fail('Excluded transaction entered SUN search')
    monkeypatch.setattr(module, 'reconcile_candidates', forbidden)
    result, = module.verify_transactions([ims(cleared_status=status, cleared_dates=dates)], [sun()])
    assert result['sun_eligible'] is False
    assert result['sun_verification_status'] == 'NOT_APPLICABLE'
    assert not result['sun_evidence_attempted']
    assert not result['candidate_sun_rows'] and not result['candidate_combinations']
    assert not result['matched_sun_rows'] and not result['evidence_reuse_conflicts']


@pytest.mark.parametrize('status,dates', [('cleared','2026/07/03'),
                                         ('multiple_cleared_dates','2026/07/02|2026/07/03')])
def test_actual_cleared_dates_are_sun_eligible(status, dates):
    result, = verify_transactions([ims(cleared_status=status, cleared_dates=dates)], [sun()])
    assert result['sun_eligible'] and result['sun_evidence_attempted']
    assert result['sun_verification_status'] == VERIFIED


def test_void_pair_control_unchanged_but_no_sun_search_or_reuse(monkeypatch):
    import src.ascot.verify_ims_sun as module
    rows = void_pair()
    rows[1].update(date_cleared_raw='Same Month Void', transaction_datetime='2026-07-29',
                   account_raw='different', cost_center_raw='different')
    controls, _ = module.ims_preverification(rows)
    # An eligible rival must now verify; the void rows cannot reserve its evidence.
    results = module.verify_transactions(rows + [ims('I3', payment_type='Check', check_or_ref='4447')],
                                         [sun(payment_type_raw='4447')])
    assert results[2]['status'] == VERIFIED
    for result in results[:2]:
        assert result['ims_internal_control'] == controls[result['ims_transaction_id']]
        assert result['ims_internal_control']['method'] == 'SAME_MONTH_VOID_NET_ZERO'
        assert not result['sun_eligible'] and not result['sun_evidence_attempted']
        assert not result['matched_sun_rows'] and not result['evidence_reuse_conflicts']
        assert result['reason_code'] == 'SAME_MONTH_VOID_INTERNAL_CONTROL_ONLY'
    assert summarize(results)[0]['sun_reuse_conflict_cases'] == 0


def test_repeated_void_amount_group_is_internal_only_without_forced_pairing(monkeypatch):
    import src.ascot.verify_ims_sun as module
    rows = void_pair() + [ims('I3', '-100', cleared_status='same_month_void', cleared_dates='',
                             source_description='Other Vendor'),
                          ims('I4', '100', cleared_status='same_month_void', cleared_dates='',
                              source_description='Void', check_or_ref='Void', method='V')]
    def forbidden(*args, **kwargs):
        pytest.fail('Void group entered SUN search')
    monkeypatch.setattr(module, 'reconcile_candidates', forbidden)
    results = module.verify_transactions(rows, [sun()])
    for result in results:
        control = result['ims_internal_control']
        assert control['status'] == 'PASSED'
        assert control['method'] == 'SAME_MONTH_VOID_NET_ZERO_GROUP'
        assert control['group_member_ids'] == ['I1','I2','I3','I4']
        assert control['group_net_amount'] == '0'
        assert 'void_partner_ids' not in result
        assert result['sun_verification_status'] == 'NOT_APPLICABLE'
    summary = summarize(results)[0]
    assert summary['same_month_void']['zero_net_groups'] == 1
    assert summary['same_month_void']['proceeding_to_sun_rows'] == 0
    assert summary['same_month_void']['sun_review_groups'] == 0


def test_historical_void_controls_and_sun_population_are_separate():
    from pathlib import Path
    from src.ascot.verify_ims_sun import read_csv
    path = Path('data/processed/aic_ims_all_months_transactions.csv')
    files = sorted(Path('data/processed/sun_jnl').glob('sun_jnl_2026-??.csv'))
    if not path.exists() or len(files) != 7:
        pytest.skip('Local historical inputs unavailable')
    results = verify_transactions(read_csv(path), [r for p in files for r in read_csv(p)])
    voids = [r for r in results if r['ims_source']['cleared_status'] == 'same_month_void']
    assert len(voids) == 38
    assert all(r['ims_internal_control']['status'] == 'PASSED' for r in voids)
    assert all(not r['sun_eligible'] and not r['sun_evidence_attempted'] for r in voids)
    assert all(not r['candidate_sun_rows'] and not r['candidate_combinations']
               and not r['matched_sun_rows'] and not r['evidence_reuse_conflicts'] for r in voids)
    controls = {r['ims_internal_control']['group_id']: r['ims_internal_control'] for r in voids}
    assert sum(c['method'] == 'SAME_MONTH_VOID_NET_ZERO' for c in controls.values()) == 17
    assert sum(c['method'] == 'SAME_MONTH_VOID_NET_ZERO_GROUP' for c in controls.values()) == 1
    assert sum(r['sun_eligible'] for r in results) == 731
    excluded_ids = {r['ims_transaction_id'] for r in results if not r['sun_eligible']}
    assert all(not (set(c['competing_ims_ids']) & excluded_ids)
               for r in results for c in r['evidence_reuse_conflicts'])
