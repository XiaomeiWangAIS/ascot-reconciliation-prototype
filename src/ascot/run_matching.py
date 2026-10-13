#!/usr/bin/env python3
"""
AIC Cash Disbursement Matching Engine — CLI entry point

Usage:
    python run_matching.py --sun path/to/sun_export.csv \
                           --wf  path/to/wf_bank.csv \
                           --out output/

Outputs four files in --out:
    matched.csv          High-confidence matches
    low_confidence.csv   Amount+date matches (need human approval before posting)
    exceptions.csv       Unmatched invoices with reason
    match_summary.json   Run statistics
"""

import argparse
import logging
import sys

from aic_matcher.loader  import load_sun, load_wf
from aic_matcher.matcher import run_matching
from aic_matcher.writer  import write_outputs


def main():
    parser = argparse.ArgumentParser(description="AIC Cash Disbursement Matching Engine")
    parser.add_argument("--sun", required=True, help="Path to SUN Concur export CSV")
    parser.add_argument("--wf",  required=True, help="Path to Wells Fargo bank file CSV")
    parser.add_argument("--out", default="output", help="Output directory (default: output/)")
    parser.add_argument("--log-level", default="INFO",
                        choices=["DEBUG", "INFO", "WARNING", "ERROR"])
    args = parser.parse_args()

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%H:%M:%S",
    )

    # Load
    invoices, sun_bad = load_sun(args.sun)
    transactions, wf_bad = load_wf(args.wf)

    if not invoices:
        print("ERROR: No valid SUN invoices loaded. Check the file path and format.")
        sys.exit(1)
    if not transactions:
        print("ERROR: No valid WF transactions loaded. Check the file path and format.")
        sys.exit(1)

    print(f"\nLoaded {len(invoices)} SUN invoices ({len(sun_bad)} bad rows skipped)")
    print(f"Loaded {len(transactions)} WF transactions ({len(wf_bad)} bad rows skipped)\n")

    # Match
    results = run_matching(invoices, transactions)

    # Write outputs
    paths = write_outputs(results, invoices, transactions, output_dir=args.out)

    # Print summary
    matched  = sum(1 for r in results if r.strategy not in ("UNMATCHED",) and r.confidence == "high")
    low_conf = sum(1 for r in results if r.confidence == "low" and r.strategy != "UNMATCHED")
    unmatched = sum(1 for r in results if r.strategy == "UNMATCHED")

    print("=" * 50)
    print(f"  Total invoices:      {len(invoices)}")
    print(f"  Matched (high conf): {matched}")
    print(f"  Low confidence:      {low_conf}  ← need human review")
    print(f"  Unmatched:           {unmatched}")
    print(f"  Match rate:          {matched / len(invoices) * 100:.1f}%")
    print("=" * 50)
    print(f"\nOutputs written to: {args.out}/")
    for name, path in paths.items():
        print(f"  {name}: {path}")


if __name__ == "__main__":
    main()
