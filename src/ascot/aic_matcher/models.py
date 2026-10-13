"""
Data models for AIC Cash Disbursement Matching Engine.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from datetime import date
from typing import Optional


# Match strategy labels (priority order)
STRATEGY_NETTING   = "NETTING_BATCH"
STRATEGY_CHECK     = "CHECK"
STRATEGY_TRANS_REF = "TRANS_REF"
STRATEGY_AMOUNT_DATE = "AMOUNT_DATE_FALLBACK"
STRATEGY_UNMATCHED = "UNMATCHED"

# Confidence levels
CONFIDENCE_HIGH = "high"
CONFIDENCE_LOW  = "low"   # Requires human approval before posting


@dataclass
class SUNInvoice:
    """A single invoice record from the SUN accounting system (Concur export)."""
    invoice_id: str
    vendor_name: str
    paid_date: date
    amount: Decimal
    check_number: Optional[str] = None
    t_code: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class WFTransaction:
    """A single transaction line from the Wells Fargo bank file."""
    transaction_id: str
    post_date: date
    amount: Decimal                # negative = debit (payment)
    description: str
    check_number: Optional[str] = None
    raw: dict = field(default_factory=dict)


@dataclass
class MatchResult:
    """Result of attempting to match one or more SUN invoices to a WF transaction."""
    invoice_ids: list
    wf_transaction_id: Optional[str]
    strategy: str
    confidence: str
    notes: str = ""
