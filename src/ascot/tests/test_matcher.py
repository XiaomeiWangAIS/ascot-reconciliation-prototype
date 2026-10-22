"""
Unit tests for the AIC matching engine.

Run with:  python -m pytest tests/
"""

import pytest
from datetime import date
from decimal import Decimal

from aic_matcher.models import SUNInvoice, WFTransaction
from aic_matcher.matcher import run_matching, NETTING_TOLERANCE
from aic_matcher.models import (
    STRATEGY_NETTING, STRATEGY_CHECK, STRATEGY_TRANS_REF,
    STRATEGY_AMOUNT_DATE, STRATEGY_UNMATCHED,
    CONFIDENCE_HIGH, CONFIDENCE_LOW,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def inv(invoice_id, amount, paid_date=date(2026,1,5), check_number=None, t_code=None):
    return SUNInvoice(
        invoice_id=invoice_id,
        vendor_name="Test Vendor",
        paid_date=paid_date,
        amount=Decimal(str(amount)),
        check_number=check_number,
        t_code=t_code,
    )

def wftx(tx_id, amount, post_date=date(2026,1,5), description="MISCELLANEOUS ACH DEBIT", check_number=None):
    return WFTransaction(
        transaction_id=tx_id,
        post_date=post_date,
        amount=Decimal(str(amount)),   # negative = debit
        description=description,
        check_number=check_number,
    )


# ── Strategy 1: Netting ───────────────────────────────────────────────────────

def test_netting_two_invoices_match_one_wf_batch():
    invoices = [inv("I001", "12500.00"), inv("I002", "8200.00")]
    transactions = [wftx("WF01", "-20700.00")]
    results = run_matching(invoices, transactions)

    assert len(results) == 1
    r = results[0]
    assert r.strategy == STRATEGY_NETTING
    assert r.confidence == CONFIDENCE_HIGH
    assert set(r.invoice_ids) == {"I001", "I002"}
    assert r.wf_transaction_id == "WF01"


def test_netting_within_tolerance():
    invoices = [inv("I001", "1000.00"), inv("I002", "500.00")]
    transactions = [wftx("WF01", "-1500.01")]   # 1 cent off
    results = run_matching(invoices, transactions)
    assert results[0].strategy == STRATEGY_NETTING


def test_netting_exceeds_tolerance():
    invoices = [inv("I001", "1000.00"), inv("I002", "500.00")]
    transactions = [wftx("WF01", "-1500.10")]   # 10 cents off — too much
    results = run_matching(invoices, transactions)
    # Should fall through to other strategies; both likely UNMATCHED
    strategies = {r.strategy for r in results}
    assert STRATEGY_NETTING not in strategies


def test_netting_single_invoice_skipped():
    """A single invoice on a date should not be grouped for netting."""
    invoices = [inv("I001", "500.00")]
    transactions = [wftx("WF01", "-500.00")]
    results = run_matching(invoices, transactions)
    # Should match via AMOUNT_DATE_FALLBACK, not NETTING
    assert results[0].strategy != STRATEGY_NETTING


# ── Strategy 2: Check number ──────────────────────────────────────────────────

def test_check_number_exact_match():
    invoices = [inv("I001", "3000.00", check_number="10042")]
    transactions = [wftx("WF01", "-3000.00", check_number="10042")]
    results = run_matching(invoices, transactions)
    assert results[0].strategy == STRATEGY_CHECK
    assert results[0].confidence == CONFIDENCE_HIGH


def test_check_number_no_match_different_number():
    invoices = [inv("I001", "3000.00", check_number="10042")]
    transactions = [wftx("WF01", "-3000.00", check_number="99999")]
    results = run_matching(invoices, transactions)
    assert results[0].strategy != STRATEGY_CHECK


# ── Strategy 3: Transaction reference ────────────────────────────────────────

def test_trans_ref_found_in_description():
    invoices = [inv("INV-2026-0042", "750.00")]
    transactions = [wftx("WF01", "-750.00", description="ACH CREDIT INV-2026-0042 VENDOR X")]
    results = run_matching(invoices, transactions)
    assert results[0].strategy == STRATEGY_TRANS_REF
    assert results[0].confidence == CONFIDENCE_HIGH


def test_trans_ref_case_insensitive():
    invoices = [inv("inv-2026-0042", "750.00")]
    transactions = [wftx("WF01", "-750.00", description="PAYMENT FOR INV-2026-0042")]
    results = run_matching(invoices, transactions)
    assert results[0].strategy == STRATEGY_TRANS_REF


# ── Strategy 4: Amount + date fallback ───────────────────────────────────────

def test_amount_date_fallback_low_confidence():
    invoices = [inv("I001", "250.00", paid_date=date(2026,1,10))]
    transactions = [wftx("WF01", "-250.00", post_date=date(2026,1,11))]
    results = run_matching(invoices, transactions)
    assert results[0].strategy == STRATEGY_AMOUNT_DATE
    assert results[0].confidence == CONFIDENCE_LOW


def test_amount_date_outside_window():
    invoices = [inv("I001", "250.00", paid_date=date(2026,1,1))]
    transactions = [wftx("WF01", "-250.00", post_date=date(2026,1,10))]  # 9 days apart
    results = run_matching(invoices, transactions)
    assert results[0].strategy == STRATEGY_UNMATCHED


# ── Unmatched ─────────────────────────────────────────────────────────────────

def test_unmatched_when_no_candidate():
    invoices = [inv("I001", "999.99")]
    transactions = [wftx("WF01", "-111.11")]
    results = run_matching(invoices, transactions)
    assert results[0].strategy == STRATEGY_UNMATCHED


# ── Priority ordering ─────────────────────────────────────────────────────────

def test_check_wins_over_amount_date():
    """If an invoice can match by check AND by amount+date, check should win."""
    invoices = [inv("I001", "500.00", check_number="20001")]
    transactions = [
        wftx("WF01", "-500.00", check_number="20001"),
    ]
    results = run_matching(invoices, transactions)
    assert results[0].strategy == STRATEGY_CHECK


def test_wf_transaction_not_reused():
    """One WF transaction should not match more than one invoice."""
    invoices = [inv("I001", "500.00"), inv("I002", "500.00", paid_date=date(2026,1,6))]
    transactions = [wftx("WF01", "-500.00")]
    results = run_matching(invoices, transactions)
    wf_ids_used = [r.wf_transaction_id for r in results if r.wf_transaction_id]
    assert len(wf_ids_used) == len(set(wf_ids_used)), "WF transaction reused"
