# AIC Cash Disbursement Matching Engine

**CARLab @ Rutgers Business School**  
Developed by Miruthu & Xiaomei

---

## What it does

Automatically reconciles invoices from the SUN (Concur) accounting system against Wells Fargo bank transactions, using four strategies in priority order:

| Priority | Strategy | Description | Confidence |
|---|---|---|---|
| 1 | `NETTING_BATCH` | Groups same-day SUN invoices, matches total to one WF ACH batch | High |
| 2 | `CHECK` | Exact check number match | High |
| 3 | `TRANS_REF` | Invoice ID found in WF description text | High |
| 4 | `AMOUNT_DATE_FALLBACK` | Same amount + dates within 2 days | **Low — human approval required** |

Any invoice not matched by strategy 4 goes to `UNMATCHED` in the exceptions file.

**January 2026 test run:** 64 invoices · $5.7M total · 18 matched · 5 low-confidence · 41 exceptions · 35.9% match rate

---

## Project structure

```
aic-matching-engine/
├── aic_matcher/
│   ├── __init__.py
│   ├── models.py      # Data classes: SUNInvoice, WFTransaction, MatchResult
│   ├── loader.py      # CSV readers with flag-and-continue error handling
│   ├── matcher.py     # All four matching strategies
│   └── writer.py      # Writes the four output files
├── tests/
│   └── test_matcher.py
├── run_matching.py    # CLI entry point
└── requirements.txt
```

---

## Quick start

```bash
pip install -r requirements.txt

python run_matching.py \
  --sun data/jan2026_sun_export.csv \
  --wf  data/jan2026_wf_bank.csv \
  --out output/jan2026/
```

### Output files

| File | Contents |
|---|---|
| `matched.csv` | High-confidence matches with how they matched |
| `low_confidence.csv` | Amount+date matches — reviewer fills in `approved` column |
| `exceptions.csv` | Unmatched invoices with reason code |
| `match_summary.json` | Run statistics |

---

## Running tests

```bash
pip install pytest
python -m pytest tests/ -v
```

---

## Key design decisions

- **Python `Decimal` for all money math** — avoids floating-point rounding errors that accumulate at scale
- **Flag-and-continue** — bad rows are logged and collected; the run always produces a complete output
- **Nothing posts automatically from low-confidence matches** — those sit in `low_confidence.csv` until a human approves them
- **One WF transaction is never reused** — once consumed by a match, it can't match anything else
- **ACH netting tolerance: $0.02** — handles minor rounding in batch totals; configurable in `matcher.py`

---

## Open questions for Ascot

1. Can the Concur export be scheduled automatically, or does someone always export it manually?
2. Does the WF file format change month to month?
3. Are wire transfers and state payments (NCCI, AIPSO) in a separate bank file?
4. Which bank account do Sedgwick wire transfers go through?
5. Can we get February–June 2026 SUN + WF files to improve testing?
6. T-code mapping table needs confirmation before auto-posting is turned on.

---

## Next steps (October–December 2026)

- [ ] Integrate additional bank files (wires, state accounts) to reduce exception rate  
- [ ] Confirm T-code mapping with Ascot accounting team  
- [ ] Test on Feb–Jun 2026 data  
- [ ] Build runbook for Ascot team to run independently  
- [ ] Live parallel run (November)  
- [ ] Full handover (December)
