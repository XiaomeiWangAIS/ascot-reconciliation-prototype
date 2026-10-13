"""
Data loading and cleaning for AIC Cash Disbursement Matching Engine.

Reads the SUN Concur export and Wells Fargo bank file,
standardises dates and amounts, and flags bad rows without crashing.
"""
import csv
import logging
from decimal import Decimal, InvalidOperation
from datetime import date, datetime
from typing import List, Tuple

from .models import SUNInvoice, WFTransaction

logger = logging.getLogger(__name__)

# ── Date parsing ──────────────────────────────────────────────────────────────

_DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%m-%d-%Y", "%m/%d/%y"]


def _parse_date(raw: str, context: str) -> Optional[date]:
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw.strip(), fmt).date()
        except ValueError:
            continue
    logger.warning("Could not parse date %r in %s — row skipped", raw, context)
    return None


def _parse_amount(raw: str, context: str) -> Optional[Decimal]:
    """Parse a dollar amount string, stripping $, commas, and parens."""
    cleaned = raw.strip().replace("$", "").replace(",", "").replace(" ", "")
    # Parentheses = negative: (1,234.56) → -1234.56
    if cleaned.startswith("(") and cleaned.endswith(")"):
        cleaned = "-" + cleaned[1:-1]
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        logger.warning("Could not parse amount %r in %s — row skipped", raw, context)
        return None


# ── SUN loader ────────────────────────────────────────────────────────────────

def load_sun(path: str) -> Tuple[List[SUNInvoice], List[dict]]:
    """
    Load SUN invoices from a Concur CSV export.

    Returns (invoices, bad_rows).  Bad rows are logged and collected
    rather than raising so the caller always gets a complete result.

    Expected columns (case-insensitive):
        invoice_id, vendor_name, paid_date, amount, check_number, t_code
    """
    invoices: List[SUNInvoice] = []
    bad_rows: List[dict] = []

    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        # Normalise header names to lowercase
        reader.fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]

        for i, row in enumerate(reader, start=2):  # row 1 = header
            ctx = f"SUN row {i}"
            invoice_id  = (row.get("invoice_id") or row.get("id") or "").strip()
            vendor_name = (row.get("vendor_name") or row.get("vendor") or "").strip()
            raw_date    = (row.get("paid_date") or row.get("date") or "").strip()
            raw_amount  = (row.get("amount") or "").strip()

            if not invoice_id:
                logger.warning("%s: missing invoice_id — skipped", ctx)
                bad_rows.append({"row": i, "issue": "missing invoice_id", "data": dict(row)})
                continue

            paid_date = _parse_date(raw_date, ctx)
            amount    = _parse_amount(raw_amount, ctx)

            if paid_date is None or amount is None:
                bad_rows.append({"row": i, "issue": "bad date or amount", "data": dict(row)})
                continue

            invoices.append(SUNInvoice(
                invoice_id   = invoice_id,
                vendor_name  = vendor_name,
                paid_date    = paid_date,
                amount       = amount,
                check_number = (row.get("check_number") or row.get("check_no") or "").strip() or None,
                t_code       = (row.get("t_code") or row.get("tcode") or "").strip() or None,
                raw          = dict(row),
            ))

    logger.info("SUN loaded: %d invoices, %d bad rows from %s", len(invoices), len(bad_rows), path)
    return invoices, bad_rows


# ── Wells Fargo loader ────────────────────────────────────────────────────────

def load_wf(path: str) -> Tuple[List[WFTransaction], List[dict]]:
    """
    Load transactions from a Wells Fargo bank export CSV.

    Returns (transactions, bad_rows).

    Expected columns (case-insensitive):
        transaction_id (or id), post_date (or date), amount, description,
        check_number (optional)
    """
    transactions: List[WFTransaction] = []
    bad_rows: List[dict] = []

    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        reader.fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]

        for i, row in enumerate(reader, start=2):
            ctx = f"WF row {i}"
            tx_id       = (row.get("transaction_id") or row.get("id") or str(i)).strip()
            raw_date    = (row.get("post_date") or row.get("date") or "").strip()
            raw_amount  = (row.get("amount") or "").strip()
            description = (row.get("description") or "").strip()

            post_date = _parse_date(raw_date, ctx)
            amount    = _parse_amount(raw_amount, ctx)

            if post_date is None or amount is None:
                bad_rows.append({"row": i, "issue": "bad date or amount", "data": dict(row)})
                continue

            transactions.append(WFTransaction(
                transaction_id = tx_id,
                post_date      = post_date,
                amount         = amount,
                description    = description,
                check_number   = (row.get("check_number") or row.get("check_no") or "").strip() or None,
                raw            = dict(row),
            ))

    logger.info("WF loaded: %d transactions, %d bad rows from %s", len(transactions), len(bad_rows), path)
    return transactions, bad_rows


# Fix missing import that _parse_date uses
from typing import Optional  # noqa: E402 (already imported above via Tuple)
