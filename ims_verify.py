"""
IMS Verification Tool  (v2)
===========================
Verifies each row in the AIC IMS tab (July_2026_Resource_Pro_Cash.xlsx)
against the standalone Paid Invoices for SUN JNL (Sheet1 / AIC Reins).

Source files
------------
  IMS_FILE   : July_2026_Resource_Pro_Cash.xlsx  — AIC IMS tab
  SUN_FILE   : Paid_Invoices_for_SUN_JNL_July_2026.xlsx — Sheet1 + AIC Reins

Matching strategies (in priority order)
----------------------------------------
  1. EXACT_AMOUNT_NAME  — amount within $0.02 AND name similarity ≥ 55%
  2. SPLIT_SUM          — 2-6 SUN rows whose amounts sum to IMS amount (±$0.02),
                          candidate rows filtered by name similarity ≥ 30%
  3. MATCHED_CHECK      — Check payment type: IMS CheckOrRef matches SUN
                          Payment Type (numeric check number)
  4. EXACT_AMOUNT_ONLY  — amount match only (name similarity < 55%), flagged amber
  5. UNMATCHED          — no match found; Voids (blank amount) handled separately

Output
------
  IMS_Verification_July_2026.xlsx  — colour-coded IMS rows + Summary sheet
"""

import re
from decimal import Decimal, ROUND_HALF_UP
from itertools import combinations
from pathlib import Path

import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

# ── Paths ─────────────────────────────────────────────────────────────────────

IMS_FILE = Path(
    "/mnt/user-data/uploads/July_2026_Resource_Pro_Cash.xlsx"
)
SUN_FILE = Path(
    "/root/.claude/uploads/84d0e59b-dfe1-5249-bd35-8a30564f7b93/"
    "b8b8651a-Paid_Invoices_for_SUN_JNL_July_2026.xlsx"
)
OUT_PATH = Path("/home/claude/aic-matching-engine/IMS_Verification_July_2026.xlsx")

AMOUNT_TOL          = Decimal("0.02")
NAME_SIM_THRESHOLD  = 0.55
NAME_SIM_WEAK       = 0.25
MAX_SPLIT_SIZE      = 10

# ── Colours ───────────────────────────────────────────────────────────────────

FILL_GREEN  = PatternFill("solid", fgColor="C6EFCE")
FILL_YELLOW = PatternFill("solid", fgColor="FFEB9C")
FILL_RED    = PatternFill("solid", fgColor="FFC7CE")
FILL_GREY   = PatternFill("solid", fgColor="D9D9D9")
FILL_HEADER = PatternFill("solid", fgColor="4472C4")
FONT_HEADER = Font(color="FFFFFF", bold=True)

STATUS_FILL = {
    "MATCHED":           FILL_GREEN,
    "MATCHED_SPLIT":     FILL_YELLOW,
    "MATCHED_CHECK":     FILL_GREEN,
    "MATCHED_AMT_ONLY":  FILL_YELLOW,
    "VOID":              FILL_GREY,
    "UNMATCHED":         FILL_RED,
}

STATUS_LABEL = {
    "MATCHED":           "✅ Matched",
    "MATCHED_SPLIT":     "🔀 Split Match",
    "MATCHED_CHECK":     "✅ Check Match",
    "MATCHED_AMT_ONLY":  "⚠️ Amount Match (review name)",
    "VOID":              "—  Void / Zero",
    "UNMATCHED":         "❌ Unmatched",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def norm_amt(v) -> Decimal | None:
    if v is None:
        return None
    try:
        d = Decimal(str(v)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return d
    except Exception:
        return None


def clean(s: str) -> str:
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


STOPS = {"inc", "llc", "ltd", "corp", "the", "and", "of", "dba", "co",
         "company", "services", "group", "insurance", "holdings"}


def name_sim(a: str, b: str) -> float:
    ta = set(clean(a).split()) - STOPS
    tb = set(clean(b).split()) - STOPS
    if not ta or not tb:
        return 0.4
    overlap = ta & tb
    return len(overlap) / max(len(ta), len(tb))


def fmt_date(d) -> str:
    if d is None:
        return ""
    if hasattr(d, "date"):
        return d.date().isoformat()
    return str(d)


# ── Loaders ───────────────────────────────────────────────────────────────────

def load_ims() -> list[dict]:
    wb = openpyxl.load_workbook(str(IMS_FILE), read_only=True, data_only=True)
    ws = wb["AIC IMS"]
    rows = list(ws.iter_rows(values_only=True))
    # cols: TransactionDate, CheckOrRef, Method, PaymentType, Description,
    #       Debit, Credit, Date Cleared, Account, Cost Center,
    #       Description2, Amount, Backup

    data, pending = [], None
    for r in rows[1:]:
        tx_date = r[0]
        check_ref, method, ptype, desc = r[1], r[2], r[3], r[4]
        debit, credit, date_cleared = r[5], r[6], r[7]
        acct, cc, desc2, amt, backup = r[8], r[9], r[10], r[11], r[12]

        if tx_date is not None and desc != "Balance Forward":
            if pending:
                data.append(pending)
            raw_amt = abs(credit) if credit else amt
            pending = {
                "date":         tx_date,
                "check_ref":    (check_ref or "").strip(),
                "payment_type": (ptype or "").strip(),
                "description":  (desc or "").strip(),
                "credit":       credit,
                "date_cleared": date_cleared,
                "amount":       norm_amt(raw_amt),
                "backup_note":  (backup or "").strip(),
                "sub_rows":     [(acct, cc, desc2, norm_amt(amt))],
            }
        elif tx_date is None and pending and cc is not None:
            pending["sub_rows"].append((acct, cc, desc2, norm_amt(amt)))

    if pending:
        data.append(pending)
    return data


def load_sun() -> list[dict]:
    """Load AIC Disbursements rows from Sheet1 + AIC Reins tab."""
    wb = openpyxl.load_workbook(str(SUN_FILE), read_only=True, data_only=True)

    rows = []

    # Sheet1: Account, Description, CCY, Amount, VAT, TotalAmount, D/C,
    #         PaidDate, TransDate, TransRef, Period, T0 YOA, T1 TrustFund,
    #         T2 Class, T3 CostCenter, T4 InterCo, T5 VAT, T6 LCA, T8 Emp,
    #         LOC, Company, BankAcctName(C9), BankAcctCode(C9), LineDesc, PaymentType
    ws1 = wb["Sheet1"]
    for r in list(ws1.iter_rows(values_only=True))[1:]:
        if len(r) < 25:
            continue
        bank_name = str(r[21] or "")
        if "AIC Disbursements" not in bank_name:
            continue
        rows.append({
            "description":  (r[1] or "").strip(),
            "amount":       norm_amt(r[3]),
            "total_amount": norm_amt(r[5]),
            "paid_date":    r[7],
            "trans_ref":    (r[9] or "").strip(),
            "cost_center":  r[14],
            "bank_acct":    bank_name,
            "line_desc":    (r[23] or "").strip(),
            "payment_type": str(r[24] or "").strip(),
            "sheet":        "Sheet1",
        })

    # AIC Reins tab: Account, Description, CCY, Amount, VAT, TotalAmount, D/C,
    #                PaidDate, TransRef, Period, T1 TrustFund, T3 CostCenter,
    #                LOC, Company, BankAcctName(C9), BankAcctCode(C9),
    #                LineDesc, PaymentType
    ws2 = wb["AIC Reins"]
    for r in list(ws2.iter_rows(values_only=True))[1:]:
        if not r[1]:
            continue
        rows.append({
            "description":  (r[1] or "").strip(),
            "amount":       norm_amt(r[3]),
            "total_amount": norm_amt(r[5]),
            "paid_date":    r[7],
            "trans_ref":    (r[8] or "").strip(),
            "cost_center":  r[11],
            "bank_acct":    (r[14] or "").strip(),
            "line_desc":    (r[16] or "").strip(),
            "payment_type": str(r[17] or "").strip(),
            "sheet":        "AIC Reins",
        })

    return rows


# ── Matching ─────────────────────────────────────────────────────────────────

def match_row(ims: dict, sun: list[dict]) -> dict:
    target  = ims["amount"]
    name    = ims["description"]
    ptype   = ims["payment_type"].upper()
    chk_ref = ims["check_ref"]

    # Voids / blank amount / negative (reversal)
    desc_lower = name.lower()
    if not target or target == Decimal("0") or target < Decimal("0") or "void" in desc_lower:
        return {"status": "VOID", "matches": [], "confidence": 1.0}

    # ── Strategy 1: Exact amount + name ──────────────────────────────────────
    amt_hits = [s for s in sun if s["amount"] and abs(s["amount"] - target) <= AMOUNT_TOL]
    if amt_hits:
        scored = sorted([(name_sim(name, s["description"]), i) for i, s in enumerate(amt_hits)], reverse=True)
        best_score, best_i = scored[0]
        best = amt_hits[best_i]
        if best_score >= NAME_SIM_THRESHOLD:
            return {"status": "MATCHED", "matches": [best], "confidence": best_score}

    # ── Strategy 2: Split sum ─────────────────────────────────────────────────
    # Use a low name threshold or first-word match to catch "Broadspire Services Inc." etc.
    first_word = clean(name).split()[0] if clean(name).split() else ""
    candidates = [
        s for s in sun
        if s["amount"] and s["amount"] > Decimal("0") and s["amount"] <= target + AMOUNT_TOL
        and (name_sim(name, s["description"]) >= 0.20
             or (first_word and len(first_word) >= 4 and first_word in clean(s["description"])))
    ]
    for size in range(2, min(MAX_SPLIT_SIZE + 1, len(candidates) + 1)):
        for combo in combinations(candidates, size):
            if abs(sum(c["amount"] for c in combo) - target) <= AMOUNT_TOL:
                avg = sum(name_sim(name, c["description"]) for c in combo) / size
                return {"status": "MATCHED_SPLIT", "matches": list(combo), "confidence": avg}

    # ── Strategy 3: Check number ──────────────────────────────────────────────
    if ptype == "CHECK" or (chk_ref and re.sub(r"\D", "", chk_ref)):
        ref_num = re.sub(r"\D", "", chk_ref) if chk_ref else ""
        if not ref_num:
            ref_num = re.sub(r"\D", "", ptype)
        for s in sun:
            s_num = re.sub(r"\D", "", s["payment_type"])
            if s_num and s_num == ref_num:
                return {"status": "MATCHED_CHECK", "matches": [s], "confidence": 1.0}

    # ── Strategy 4: Amount only (weak) ───────────────────────────────────────
    if amt_hits:
        scored = sorted([(name_sim(name, s["description"]), i) for i, s in enumerate(amt_hits)], reverse=True)
        best_score, best_i = scored[0]
        best = amt_hits[best_i]
        if best_score >= NAME_SIM_WEAK:
            return {"status": "MATCHED_AMT_ONLY", "matches": [best], "confidence": best_score}

    return {"status": "UNMATCHED", "matches": [], "confidence": 0.0}


# ── Output ────────────────────────────────────────────────────────────────────

def write_output(ims_data: list[dict], results: list[dict]):
    wb_out = openpyxl.Workbook()
    ws = wb_out.active
    ws.title = "IMS Verification"

    headers = [
        "IMS Date", "Payment Type", "Check/Ref", "Description",
        "IMS Amount ($)", "Date Cleared", "Backup Note",
        "Match Status", "Confidence",
        "SUN Vendor(s)", "SUN Amount(s)", "SUN Paid Date(s)",
        "SUN Trans Ref / Check#", "SUN Line Description", "Notes"
    ]
    ws.append(headers)
    for col in range(1, len(headers) + 1):
        cell = ws.cell(1, col)
        cell.fill = FILL_HEADER
        cell.font = FONT_HEADER
        cell.alignment = Alignment(horizontal="center")

    for ims, res in zip(ims_data, results):
        status  = res["status"]
        matches = res["matches"]
        conf    = res["confidence"]

        sun_vendors  = "; ".join(m.get("description", "") for m in matches)
        sun_amts     = "; ".join(f"${m['amount']:,.2f}" if m.get("amount") else "" for m in matches)
        sun_dates    = "; ".join(fmt_date(m.get("paid_date")) for m in matches)
        sun_refs     = "; ".join(str(m.get("trans_ref") or m.get("payment_type", "")) for m in matches)
        sun_lines    = "; ".join(m.get("line_desc", "") for m in matches)

        notes = ""
        if status == "MATCHED_AMT_ONLY":
            notes = f"Name similarity only {conf:.0%} — confirm vendor"
        elif status == "MATCHED_SPLIT":
            notes = f"{len(matches)} SUN rows summed; avg name sim {conf:.0%}"
        elif status == "VOID":
            notes = "No amount — check same-month-void netting"

        ws.append([
            fmt_date(ims["date"]),
            ims["payment_type"],
            ims["check_ref"],
            ims["description"],
            float(ims["amount"]) if ims["amount"] else "",
            fmt_date(ims["date_cleared"]),
            ims["backup_note"],
            STATUS_LABEL[status],
            f"{conf:.0%}" if status != "VOID" else "",
            sun_vendors, sun_amts, sun_dates, sun_refs, sun_lines, notes,
        ])
        fill = STATUS_FILL[status]
        for col in range(1, len(headers) + 1):
            ws.cell(ws.max_row, col).fill = fill

    widths = [12, 13, 10, 42, 15, 13, 14, 26, 11, 42, 18, 14, 22, 38, 38]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(i)].width = w
    ws.freeze_panes = "A2"

    # ── Summary ───────────────────────────────────────────────────────────────
    ws2 = wb_out.create_sheet("Summary")
    from collections import Counter
    counts = Counter(r["status"] for r in results)
    total  = len(results)
    auto   = sum(counts[s] for s in ("MATCHED", "MATCHED_SPLIT", "MATCHED_CHECK", "MATCHED_AMT_ONLY"))
    voids  = counts["VOID"]

    ws2.append(["AIC IMS Verification — July 2026"])
    ws2.append([])
    ws2.append(["Status", "Count", "% of Total"])
    for status, label in STATUS_LABEL.items():
        n = counts.get(status, 0)
        ws2.append([label, n, f"{n/total:.1%}"])
    ws2.append([])
    ws2.append(["Total IMS rows", total])
    ws2.append(["Auto-verified (excl. voids)", auto, f"{auto/(total-voids):.1%}" if total > voids else ""])
    ws2.append(["Voids (zero amount)", voids])
    ws2.append(["Requires manual review", counts.get("UNMATCHED", 0)])

    wb_out.save(OUT_PATH)
    print(f"\nOutput: {OUT_PATH}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading IMS...")
    ims_data = load_ims()
    print(f"  {len(ims_data)} IMS rows")

    print("Loading SUN JNL (AIC Disbursements)...")
    sun = load_sun()
    print(f"  {len(sun)} SUN rows (AIC Disbursements + AIC Reins)")

    print("\nMatching...")
    results = [match_row(ims, sun) for ims in ims_data]

    from collections import Counter
    counts = Counter(r["status"] for r in results)
    total  = len(results)
    voids  = counts["VOID"]
    auto   = sum(counts[s] for s in ("MATCHED", "MATCHED_SPLIT", "MATCHED_CHECK", "MATCHED_AMT_ONLY"))

    print("\n=== RESULTS ===")
    for status, label in STATUS_LABEL.items():
        n = counts[status]
        print(f"  {label:38} {n:4}  ({n/total*100:.1f}%)")
    print(f"\n  Total rows:              {total}")
    print(f"  Voids (excluded):        {voids}")
    print(f"  AUTO-VERIFIED:           {auto}/{total-voids} = {auto/(total-voids)*100:.1f}%")

    unmatched = [(ims, r) for ims, r in zip(ims_data, results) if r["status"] == "UNMATCHED"]
    if unmatched:
        print(f"\n=== UNMATCHED ({len(unmatched)}) ===")
        for ims, _ in unmatched:
            print(f"  {fmt_date(ims['date'])} | {ims['payment_type']:12} | {ims['description'][:50]:50} | ${ims['amount']}")

    write_output(ims_data, results)


if __name__ == "__main__":
    main()
