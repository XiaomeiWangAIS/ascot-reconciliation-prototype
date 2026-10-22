"""
AIC Cash Disbursement Matching Engine
CARLab @ Rutgers Business School

Matches SUN (Concur) invoices to Wells Fargo bank transactions using
four strategies in priority order:

  1. NETTING_BATCH     – ACH batch netting (same-day SUN group ↔ one WF line)
  2. CHECK             – Exact check number match
  3. TRANS_REF         – Invoice ID found inside WF description text
  4. AMOUNT_DATE_FALLBACK – Same amount + dates within settlement window
                          (low confidence — requires human approval)

Any invoice not matched by strategy 4 goes to UNMATCHED.

All money arithmetic uses Python Decimal to avoid floating-point drift.
The engine never raises on bad input; it logs and keeps going.
"""

import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Tuple

from .models import (
    SUNInvoice,
    WFTransaction,
    MatchResult,
    STRATEGY_NETTING,
    STRATEGY_CHECK,
    STRATEGY_TRANS_REF,
    STRATEGY_AMOUNT_DATE,
    STRATEGY_UNMATCHED,
    CONFIDENCE_HIGH,
    CONFIDENCE_LOW,
)

logger = logging.getLogger(__name__)

# ── Tuneable constants ────────────────────────────────────────────────────────

# Maximum absolute difference (in dollars) for a netting or amount match
NETTING_TOLERANCE   = Decimal("0.02")
AMOUNT_TOLERANCE    = Decimal("0.02")

# How many calendar days either side of the SUN paid_date to search WF post_date
SETTLEMENT_WINDOW_DAYS = 2


# ── Main entry point ──────────────────────────────────────────────────────────

def run_matching(
    invoices: List[SUNInvoice],
    transactions: List[WFTransaction],
) -> List[MatchResult]:
    """
    Run all four matching strategies against the loaded data.

    Returns a list of MatchResult objects — one per invoice (or per
    netting group).  Every invoice appears in exactly one result.
    """
    results: List[MatchResult] = []
    unmatched_invoices: List[SUNInvoice] = list(invoices)
    used_wf_ids: set = set()

    # Strategy 1 — ACH batch netting
    netting_results, unmatched_invoices, used_wf_ids = _strategy_netting(
        unmatched_invoices, transactions, used_wf_ids
    )
    results.extend(netting_results)
    logger.info("Strategy 1 (NETTING_BATCH): %d groups matched, %d invoices remaining",
                len(netting_results), len(unmatched_invoices))

    # Strategy 2 — Check number
    check_results, unmatched_invoices, used_wf_ids = _strategy_check(
        unmatched_invoices, transactions, used_wf_ids
    )
    results.extend(check_results)
    logger.info("Strategy 2 (CHECK): %d matched, %d remaining",
                len(check_results), len(unmatched_invoices))

    # Strategy 3 — Transaction reference in WF description
    ref_results, unmatched_invoices, used_wf_ids = _strategy_trans_ref(
        unmatched_invoices, transactions, used_wf_ids
    )
    results.extend(ref_results)
    logger.info("Strategy 3 (TRANS_REF): %d matched, %d remaining",
                len(ref_results), len(unmatched_invoices))

    # Strategy 4 — Amount + date fallback (low confidence)
    fallback_results, unmatched_invoices, used_wf_ids = _strategy_amount_date(
        unmatched_invoices, transactions, used_wf_ids
    )
    results.extend(fallback_results)
    logger.info("Strategy 4 (AMOUNT_DATE_FALLBACK): %d matched, %d remaining",
                len(fallback_results), len(unmatched_invoices))

    # Remaining → UNMATCHED
    for inv in unmatched_invoices:
        results.append(MatchResult(
            invoice_ids      = [inv.invoice_id],
            wf_transaction_id = None,
            strategy         = STRATEGY_UNMATCHED,
            confidence       = CONFIDENCE_LOW,
            notes            = "No matching WF transaction found by any strategy",
        ))

    logger.info("Total results: %d (%d unmatched)", len(results),
                sum(1 for r in results if r.strategy == STRATEGY_UNMATCHED))
    return results


# ── Strategy 1: ACH batch netting ────────────────────────────────────────────

def _strategy_netting(
    invoices: List[SUNInvoice],
    transactions: List[WFTransaction],
    used_wf_ids: set,
) -> Tuple[List[MatchResult], List[SUNInvoice], set]:
    """
    Group SUN invoices by paid_date, sum each group, and look for a
    WF transaction within SETTLEMENT_WINDOW_DAYS whose amount matches
    the group total within NETTING_TOLERANCE.

    A WF line matching a group is consumed (added to used_wf_ids) so
    it cannot also match individual invoices in later strategies.
    """
    results: List[MatchResult] = []
    matched_invoice_ids: set = set()
    used = set(used_wf_ids)

    # Build date → [invoices] index for SUN
    by_date: Dict[str, List[SUNInvoice]] = defaultdict(list)
    for inv in invoices:
        by_date[str(inv.paid_date)].append(inv)

    # Build a searchable list of WF debits
    wf_debits = [tx for tx in transactions if tx.amount < 0 and tx.transaction_id not in used]

    for date_key, group in by_date.items():
        if len(group) < 2:
            continue  # Single invoice on this date — no netting needed

        group_total = sum(inv.amount for inv in group)

        match = _find_wf_by_amount(
            target=group_total,
            wf_debits=wf_debits,
            paid_date=group[0].paid_date,
            tolerance=NETTING_TOLERANCE,
            used=used,
        )

        if match:
            used.add(match.transaction_id)
            for inv in group:
                matched_invoice_ids.add(inv.invoice_id)
            results.append(MatchResult(
                invoice_ids       = [inv.invoice_id for inv in group],
                wf_transaction_id = match.transaction_id,
                strategy          = STRATEGY_NETTING,
                confidence        = CONFIDENCE_HIGH,
                notes             = (
                    f"ACH batch: {len(group)} invoices totalling "
                    f"${group_total:,.2f} matched WF {match.transaction_id} "
                    f"(${abs(match.amount):,.2f}) within ${NETTING_TOLERANCE}"
                ),
            ))

    remaining = [inv for inv in invoices if inv.invoice_id not in matched_invoice_ids]
    return results, remaining, used


# ── Strategy 2: Check number ──────────────────────────────────────────────────

def _strategy_check(
    invoices: List[SUNInvoice],
    transactions: List[WFTransaction],
    used_wf_ids: set,
) -> Tuple[List[MatchResult], List[SUNInvoice], set]:
    """
    Match invoices that carry a check_number to WF transactions with
    the same check_number.
    """
    results: List[MatchResult] = []
    matched_ids: set = set()
    used = set(used_wf_ids)

    # Index WF transactions by check number
    wf_by_check: Dict[str, WFTransaction] = {}
    for tx in transactions:
        if tx.check_number and tx.transaction_id not in used:
            wf_by_check[tx.check_number.strip()] = tx

    for inv in invoices:
        if not inv.check_number:
            continue
        tx = wf_by_check.get(inv.check_number.strip())
        if tx and tx.transaction_id not in used:
            used.add(tx.transaction_id)
            matched_ids.add(inv.invoice_id)
            results.append(MatchResult(
                invoice_ids       = [inv.invoice_id],
                wf_transaction_id = tx.transaction_id,
                strategy          = STRATEGY_CHECK,
                confidence        = CONFIDENCE_HIGH,
                notes             = f"Check number {inv.check_number} matched",
            ))

    remaining = [inv for inv in invoices if inv.invoice_id not in matched_ids]
    return results, remaining, used


# ── Strategy 3: Transaction reference in WF description ──────────────────────

def _strategy_trans_ref(
    invoices: List[SUNInvoice],
    transactions: List[WFTransaction],
    used_wf_ids: set,
) -> Tuple[List[MatchResult], List[SUNInvoice], set]:
    """
    Look for the SUN invoice_id inside the WF transaction description text.
    Case-insensitive substring search.
    """
    results: List[MatchResult] = []
    matched_ids: set = set()
    used = set(used_wf_ids)

    available_wf = [tx for tx in transactions if tx.transaction_id not in used]

    for inv in invoices:
        needle = inv.invoice_id.lower()
        for tx in available_wf:
            if needle in tx.description.lower() and tx.transaction_id not in used:
                used.add(tx.transaction_id)
                matched_ids.add(inv.invoice_id)
                results.append(MatchResult(
                    invoice_ids       = [inv.invoice_id],
                    wf_transaction_id = tx.transaction_id,
                    strategy          = STRATEGY_TRANS_REF,
                    confidence        = CONFIDENCE_HIGH,
                    notes             = (
                        f"Invoice ID '{inv.invoice_id}' found in WF description: "
                        f"'{tx.description[:80]}'"
                    ),
                ))
                break

    remaining = [inv for inv in invoices if inv.invoice_id not in matched_ids]
    return results, remaining, used


# ── Strategy 4: Amount + date fallback ───────────────────────────────────────

def _strategy_amount_date(
    invoices: List[SUNInvoice],
    transactions: List[WFTransaction],
    used_wf_ids: set,
) -> Tuple[List[MatchResult], List[SUNInvoice], set]:
    """
    Last-resort match: same dollar amount, dates within SETTLEMENT_WINDOW_DAYS.

    Marked LOW CONFIDENCE — these must be reviewed and approved by a human
    before posting.  Nothing posts automatically from this strategy.
    """
    results: List[MatchResult] = []
    matched_ids: set = set()
    used = set(used_wf_ids)

    wf_debits = [tx for tx in transactions if tx.amount < 0 and tx.transaction_id not in used]

    for inv in invoices:
        match = _find_wf_by_amount(
            target    = inv.amount,
            wf_debits = wf_debits,
            paid_date = inv.paid_date,
            tolerance = AMOUNT_TOLERANCE,
            used      = used,
        )
        if match:
            used.add(match.transaction_id)
            matched_ids.add(inv.invoice_id)
            results.append(MatchResult(
                invoice_ids       = [inv.invoice_id],
                wf_transaction_id = match.transaction_id,
                strategy          = STRATEGY_AMOUNT_DATE,
                confidence        = CONFIDENCE_LOW,
                notes             = (
                    f"Amount ${inv.amount:,.2f} matched WF {match.transaction_id} "
                    f"within ${AMOUNT_TOLERANCE}; dates within {SETTLEMENT_WINDOW_DAYS} days. "
                    f"REQUIRES HUMAN APPROVAL BEFORE POSTING."
                ),
            ))

    remaining = [inv for inv in invoices if inv.invoice_id not in matched_ids]
    return results, remaining, used


# ── Shared helper ─────────────────────────────────────────────────────────────

def _find_wf_by_amount(
    target: Decimal,
    wf_debits: List[WFTransaction],
    paid_date,
    tolerance: Decimal,
    used: set,
) -> Optional[WFTransaction]:
    """
    Return the first WF debit whose absolute amount is within `tolerance`
    of `target` and whose post_date is within SETTLEMENT_WINDOW_DAYS of
    `paid_date`, or None if no candidate found.
    """
    window = timedelta(days=SETTLEMENT_WINDOW_DAYS)
    for tx in wf_debits:
        if tx.transaction_id in used:
            continue
        if abs(paid_date - tx.post_date) > window:
            continue
        if abs(abs(tx.amount) - target) <= tolerance:
            return tx
    return None
