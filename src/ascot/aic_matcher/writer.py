"""
Output writer for AIC Cash Disbursement Matching Engine.

Writes four CSV files:
  - matched.csv         — high-confidence matches
  - low_confidence.csv  — amount+date fallback matches (need human approval)
  - exceptions.csv      — unmatched invoices with reason
  - match_summary.json  — run statistics
"""

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from .models import (
    MatchResult,
    SUNInvoice,
    WFTransaction,
    STRATEGY_UNMATCHED,
    CONFIDENCE_LOW,
)

logger = logging.getLogger(__name__)


def write_outputs(
    results: List[MatchResult],
    invoices: List[SUNInvoice],
    transactions: List[WFTransaction],
    output_dir: str = "output",
) -> Dict[str, str]:
    """
    Write all four output files to `output_dir`.

    Returns a dict mapping output name → file path.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Build lookup dicts for enriching output
    inv_by_id: Dict[str, SUNInvoice] = {inv.invoice_id: inv for inv in invoices}
    tx_by_id: Dict[str, WFTransaction] = {tx.transaction_id: tx for tx in transactions}

    matched_rows      = []
    low_conf_rows     = []
    exception_rows    = []

    for r in results:
        if r.strategy == STRATEGY_UNMATCHED:
            for iid in r.invoice_ids:
                inv = inv_by_id.get(iid)
                exception_rows.append({
                    "invoice_id":   iid,
                    "vendor_name":  inv.vendor_name if inv else "",
                    "paid_date":    str(inv.paid_date) if inv else "",
                    "amount":       str(inv.amount) if inv else "",
                    "t_code":       inv.t_code if inv else "",
                    "reason":       r.notes,
                })
        elif r.confidence == CONFIDENCE_LOW:
            tx = tx_by_id.get(r.wf_transaction_id) if r.wf_transaction_id else None
            for iid in r.invoice_ids:
                inv = inv_by_id.get(iid)
                low_conf_rows.append({
                    "invoice_id":       iid,
                    "vendor_name":      inv.vendor_name if inv else "",
                    "paid_date":        str(inv.paid_date) if inv else "",
                    "invoice_amount":   str(inv.amount) if inv else "",
                    "t_code":           inv.t_code if inv else "",
                    "wf_transaction_id": r.wf_transaction_id or "",
                    "wf_post_date":     str(tx.post_date) if tx else "",
                    "wf_amount":        str(tx.amount) if tx else "",
                    "strategy":         r.strategy,
                    "notes":            r.notes,
                    "approved":         "",   # human fills this in
                })
        else:
            tx = tx_by_id.get(r.wf_transaction_id) if r.wf_transaction_id else None
            for iid in r.invoice_ids:
                inv = inv_by_id.get(iid)
                matched_rows.append({
                    "invoice_id":        iid,
                    "vendor_name":       inv.vendor_name if inv else "",
                    "paid_date":         str(inv.paid_date) if inv else "",
                    "invoice_amount":    str(inv.amount) if inv else "",
                    "t_code":            inv.t_code if inv else "",
                    "wf_transaction_id": r.wf_transaction_id or "",
                    "wf_post_date":      str(tx.post_date) if tx else "",
                    "wf_amount":         str(tx.amount) if tx else "",
                    "strategy":          r.strategy,
                    "notes":             r.notes,
                })

    paths = {}

    # matched.csv
    paths["matched"] = _write_csv(out / "matched.csv", matched_rows,
        ["invoice_id","vendor_name","paid_date","invoice_amount","t_code",
         "wf_transaction_id","wf_post_date","wf_amount","strategy","notes"])

    # low_confidence.csv
    paths["low_confidence"] = _write_csv(out / "low_confidence.csv", low_conf_rows,
        ["invoice_id","vendor_name","paid_date","invoice_amount","t_code",
         "wf_transaction_id","wf_post_date","wf_amount","strategy","notes","approved"])

    # exceptions.csv
    paths["exceptions"] = _write_csv(out / "exceptions.csv", exception_rows,
        ["invoice_id","vendor_name","paid_date","amount","t_code","reason"])

    # match_summary.json
    total = len(invoices)
    summary = {
        "run_timestamp":      datetime.utcnow().isoformat() + "Z",
        "total_invoices":     total,
        "matched_high":       len(matched_rows),
        "matched_low_conf":   len(low_conf_rows),
        "unmatched":          len(exception_rows),
        "match_rate_pct":     round(len(matched_rows) / total * 100, 1) if total else 0,
        "strategy_breakdown": _count_strategies(results),
    }
    summary_path = out / "match_summary.json"
    summary_path.write_text(json.dumps(summary, indent=2))
    paths["summary"] = str(summary_path)
    logger.info("Summary: %s", summary)

    return paths


def _write_csv(path: Path, rows: list, fieldnames: list) -> str:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    logger.info("Wrote %d rows → %s", len(rows), path)
    return str(path)


def _count_strategies(results: List[MatchResult]) -> dict:
    counts: Dict[str, int] = {}
    for r in results:
        counts[r.strategy] = counts.get(r.strategy, 0) + len(r.invoice_ids)
    return counts
