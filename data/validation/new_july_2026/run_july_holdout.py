"""Validation-only adapter: fixed July period and exclusion of inspected SUM footer.

Run from repository root. No production module or historical output is modified.
"""
import sys
sys.dont_write_bytecode = True
import csv
import hashlib
import importlib.util
import json
from collections import Counter, defaultdict
from pathlib import Path

from src.ascot import verify_ims_sun as verifier

ROOT = Path('data/validation/new_july_2026')
SOURCE = ROOT / 'AIC_A JE#3784 WF Disb Cash Expense Activity July 2026.xlsx'
OUTPUT = ROOT / 'processed'
SANITIZER = Path('src/ascot/sanitize_aic_ims.py')
SUN = Path('data/processed/sun_jnl/sun_jnl_2026-07.csv')
HISTORICAL = Path('data/processed/verification/ims_to_sun/verification_results.jsonl')


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def business_key(row):
    # Source-row numbers shift in the new workbook; do not equate their IDs.
    core = tuple(row.get(k, '') for k in ('accounting_period', 'transaction_datetime',
                 'check_or_ref', 'method', 'payment_type', 'source_description', 'source_signed_amount'))
    # The two old Washington entries have identical payment fields but different
    # account dimensions (FINU versus ZZZZ); those dimensions disambiguate them.
    # Void dimensions are explicitly N/A in the received workbook and cannot be
    # stable cross-workbook identifiers.
    dimensions = () if row.get('cleared_status') == 'same_month_void' else (row.get('account_raw', ''), row.get('cost_center_raw', ''))
    return core + dimensions


def main():
    if (OUTPUT / 'adapter_manifest.json').exists():
        raise FileExistsError(f'Refusing to overwrite completed holdout outputs: {OUTPUT}')
    protected = [p for p in Path('data/processed').rglob('*') if p.is_file()]
    protected += [SOURCE, SANITIZER, Path('src/ascot/sanitize_sun_jnl.py'), Path(verifier.__file__)]
    before = {str(p): digest(p) for p in protected}
    spec = importlib.util.spec_from_file_location('july_holdout_locked_sanitizer', SANITIZER)
    sanitizer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sanitizer)
    original_reader = sanitizer.read_aic_ims_rows
    excluded = []

    def read_without_footer(path):
        rows = original_reader(path)
        footer = [(n, cells) for n, cells in rows if n == 154]
        assert len(footer) == 1, 'Identified footer row is missing'
        cells = footer[0][1]
        assert cells.get(7, {}).get('formula_text', '').startswith('SUM(')
        assert all(cell.get('value') in (None, '') for col, cell in cells.items() if col != 7)
        excluded.append(dict(source_row=154, source_column='G', **cells[7]))
        return [(n, cells) for n, cells in rows if n != 154]

    # Isolated module bindings only: the two explicitly authorized adaptations,
    # plus output routing. All locked normalization functions remain unchanged.
    sanitizer.read_aic_ims_rows = read_without_footer
    sanitizer.accounting_period_label = lambda path: '2026-07'
    sanitizer.PROCESSED_FOLDER = OUTPUT
    canonical_dir = OUTPUT / SOURCE.stem
    if canonical_dir.exists():
        # Resume after a comparison-only interruption; do not rewrite canonical
        # files already produced by this validation adapter.
        read_without_footer(SOURCE)
        normalized = verifier.read_csv(canonical_dir / 'aic_ims_rows.csv')
        transactions = verifier.read_csv(canonical_dir / 'aic_ims_transactions.csv')
        allocations = verifier.read_csv(canonical_dir / 'aic_ims_allocations.csv')
        qa = json.loads((canonical_dir / 'aic_ims_validation.json').read_text())
    else:
        normalized, transactions, allocations, qa = sanitizer.sanitize_one_workbook(SOURCE, 1)
    assert len(transactions) == 136
    assert all(str(r['source_row']) != '154' for r in transactions)
    assert sum(bool(verifier.clearing_dates(r)) for r in transactions) == 117
    assert qa['ambiguous_supplemental_block_count'] == 0
    assert qa['source_continuation_inheritance_ambiguity_count'] == 0
    assert qa['allocation_reconciliation_mismatch_count'] == 0
    assert qa['unexpected_row_count'] == 0
    assert qa['formula_cells_outside_K_L'] == 0
    canonical_path = OUTPUT / SOURCE.stem / 'aic_ims_transactions.csv'
    # Use the written canonical CSV, exactly as the production verifier does.
    canonical = verifier.read_csv(canonical_path)
    results = verifier.verify_transactions(canonical, verifier.read_csv(SUN))
    summary = verifier.summarize(results)
    assert len(summary) == 1 and summary[0]['sun_eligible_count'] == 117
    voids = [r for r in results if r['ims_source']['cleared_status'] == 'same_month_void']
    assert len(voids) == 6
    assert all(r['ims_internal_control']['status'] == 'PASSED' for r in voids)
    assert all(not r['sun_eligible'] and not r['sun_evidence_attempted']
               and not r['candidate_sun_rows'] and not r['matched_sun_rows']
               and not r['evidence_reuse_conflicts'] for r in voids)
    used = [verifier.row_key(ref) for r in results if r['status'] == verifier.VERIFIED for ref in r['matched_sun_rows']]
    assert len(used) == len(set(used))
    old = [json.loads(line) for line in HISTORICAL.open()]
    old = [r for r in old if r['accounting_period'] == '2026-07']
    old_map, new_map = defaultdict(list), defaultdict(list)
    for r in old:
        old_map[business_key(r['ims_source'])].append(r)
    for r in results:
        new_map[business_key(r['ims_source'])].append(r)
    # Refuse unsupported row-order pairing if duplicate identities occur.
    assert all(len(v) == 1 for v in old_map.values())
    assert all(len(v) == 1 for v in new_map.values())
    comparisons = []
    for key in sorted(set(old_map) | set(new_map)):
        previous = old_map[key][0] if key in old_map else None
        holdout = new_map[key][0] if key in new_map else None
        if previous and holdout:
            previous_refs = [verifier.row_key(r) for r in previous['matched_sun_rows']]
            holdout_refs = [verifier.row_key(r) for r in holdout['matched_sun_rows']]
            changed = any(previous.get(k) != holdout.get(k) for k in ('sun_eligible', 'status', 'sun_verification_status', 'reason_code', 'verification_method')) or previous_refs != holdout_refs
            kind = 'OUTCOME_OR_EVIDENCE_CHANGED' if changed else 'UNCHANGED'
        else:
            kind = 'REMOVED_FROM_HOLDOUT' if previous else 'ADDED_IN_HOLDOUT'
        comparisons.append(dict(comparison=kind, previous_ims_id=previous['ims_transaction_id'] if previous else None,
                                previous_source_row=previous['ims_source']['source_row'] if previous else None,
                                holdout_ims_id=holdout['ims_transaction_id'] if holdout else None,
                                holdout_source_row=holdout['ims_source']['source_row'] if holdout else None,
                                vendor=(holdout or previous)['ims_source']['source_description'],
                                previous_result=previous, holdout_result=holdout))
    verification = OUTPUT / 'verification'
    verification.mkdir(parents=True)
    with (verification / 'verification_results.jsonl').open('x') as stream:
        for row in results:
            stream.write(json.dumps(row) + '\n')
    (verification / 'verification_summary.json').write_text(json.dumps(summary, indent=2))
    with (verification / 'transaction_comparison.jsonl').open('x') as stream:
        for row in comparisons:
            stream.write(json.dumps(row) + '\n')
    manifest = dict(source_file=str(SOURCE), source_sha256=digest(SOURCE), accounting_period='2026-07',
                    excluded_footer=excluded, canonical_transactions=str(canonical_path),
                    sanitizer_source=str(SANITIZER), sanitizer_sha256=digest(SANITIZER),
                    sun_file=str(SUN), sun_sha256=digest(SUN), verifier_rules_version=verifier.RULES_VERSION,
                    verifier_sha256=digest(Path(verifier.__file__)),
                    adapter_scope=['Exclude identified SUM footer R154', 'Assign period 2026-07', 'Route outputs to validation only'],
                    comparison_counts=dict(Counter(r['comparison'] for r in comparisons)),
                    protection_hashes=before)
    assert all(digest(Path(path)) == value for path, value in before.items())
    manifest['protected_files_unchanged'] = True
    (OUTPUT / 'adapter_manifest.json').write_text(json.dumps(manifest, indent=2))
    print('HOLDOUT SUMMARY', json.dumps(summary, indent=2))
    print('COMPARISON', manifest['comparison_counts'])
    print('CHANGES', [(r['comparison'], r['previous_ims_id'], r['holdout_ims_id'], r['vendor']) for r in comparisons if r['comparison'] != 'UNCHANGED'])


if __name__ == '__main__':
    main()
