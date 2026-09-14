# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# AIC IMS SANITIZER — STRUCTURAL QA
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# The AIC IMS sanitizer successfully processed January–July.
#
# This QA script independently checks whether the sanitized
# outputs preserve the structures that we observed directly
# in the actual Excel files.
#
#
# IMPORTANT PRINCIPLE
# ------------------------------------------------------------
#
# We are NOT asking:
#
#     "Did Python finish without an error?"
#
# We are asking:
#
#     "Did Python represent the accounting data correctly?"
#
#
# QA CHECKS INCLUDE:
#
# 1. All seven accounting periods were processed.
#
# 2. Processing order is chronological.
#
# 3. Header row is row 1 in every month.
#
# 4. Balance Forward occurs at its empirically observed
#    location:
#
#       Jan = 2
#       Feb = 2
#       Mar = 2
#       Apr = 168
#       May = 2
#       Jun = 2
#       Jul = 2
#
# 5. Actual row-type counts agree with what we inspected.
#
# 6. Transaction IDs are unique.
#
# 7. Allocation IDs are unique.
#
# 8. Every allocation links to a valid source transaction.
#
# 9. Supplemental allocation blocks are unambiguous.
#
# 10. Allocation totals independently reconcile to source
#     transaction amounts.
#
# 11. Formula cells occur only in K/L.
#
# 12. The six January inherited-metadata source transactions
#     are retained.
#
# 13. Transactions without allocation lines are explicitly
#     surfaced rather than silently discarded.
#
#     We currently expect exactly ONE:
#
#         March source row 135
#         Outstanding ACH
#
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import csv
import json

from collections import defaultdict
from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROCESSED_FOLDER = Path(
    "data/processed"
)


MANIFEST_PATH = (

    PROCESSED_FOLDER

    / "aic_ims_processing_manifest.json"
)


QA_REPORT_PATH = (

    PROCESSED_FOLDER

    / "aic_ims_qa_report.json"
)


# ============================================================
# ACCOUNTING TOLERANCE
# ============================================================

TOLERANCE = 0.02


# ============================================================
# EXPECTED ACCOUNTING PERIODS
# ============================================================

EXPECTED_PERIODS = [

    "2026-01",
    "2026-02",
    "2026-03",
    "2026-04",
    "2026-05",
    "2026-06",
    "2026-07",
]


# ============================================================
# EXPECTATIONS BASED ON DIRECT INSPECTION OF THE REAL FILES
# ============================================================
#
# These are not assumptions from the SOP.
#
# They are the structures observed directly in the seven
# actual AIC IMS worksheets.
# ============================================================

EXPECTED_STRUCTURE = {

    "2026-01": {

        "balance_forward_rows":
            [2],

        "source_transaction":
            348,

        "source_transaction_inherited_metadata":
            6,

        "void_transaction":
            1,

        "allocation_or_supplemental":
            0,

        "source_transaction_count":
            355,

        "supplemental_block_count":
            0,

        "expected_transactions_without_allocation":
            0,
    },


    "2026-02": {

        "balance_forward_rows":
            [2],

        "source_transaction":
            110,

        "source_transaction_inherited_metadata":
            0,

        "void_transaction":
            6,

        "allocation_or_supplemental":
            0,

        "source_transaction_count":
            116,

        "supplemental_block_count":
            0,

        "expected_transactions_without_allocation":
            0,
    },


    "2026-03": {

        "balance_forward_rows":
            [2],

        "source_transaction":
            124,

        "source_transaction_inherited_metadata":
            0,

        "void_transaction":
            9,

        "allocation_or_supplemental":
            0,

        "source_transaction_count":
            133,

        "supplemental_block_count":
            0,

        # Real source-data condition:
        #
        # March row 135 is an Outstanding ACH source
        # transaction with no I-M accounting allocation.
        "expected_transactions_without_allocation":
            1,
    },


    "2026-04": {

        "balance_forward_rows":
            [168],

        "source_transaction":
            145,

        "source_transaction_inherited_metadata":
            0,

        "void_transaction":
            14,

        "allocation_or_supplemental":
            7,

        "source_transaction_count":
            159,

        "supplemental_block_count":
            5,

        "expected_transactions_without_allocation":
            0,
    },


    "2026-05": {

        "balance_forward_rows":
            [2],

        "source_transaction":
            81,

        "source_transaction_inherited_metadata":
            0,

        "void_transaction":
            2,

        "allocation_or_supplemental":
            5,

        "source_transaction_count":
            83,

        "supplemental_block_count":
            2,

        "expected_transactions_without_allocation":
            0,
    },


    "2026-06": {

        "balance_forward_rows":
            [2],

        "source_transaction":
            109,

        "source_transaction_inherited_metadata":
            0,

        "void_transaction":
            7,

        "allocation_or_supplemental":
            34,

        "source_transaction_count":
            116,

        "supplemental_block_count":
            18,

        "expected_transactions_without_allocation":
            0,
    },


    "2026-07": {

        "balance_forward_rows":
            [2],

        "source_transaction":
            134,

        "source_transaction_inherited_metadata":
            0,

        "void_transaction":
            3,

        "allocation_or_supplemental":
            15,

        "source_transaction_count":
            137,

        "supplemental_block_count":
            10,

        "expected_transactions_without_allocation":
            0,
    },
}


# ============================================================
# READ JSON
# ============================================================

def read_json(path):

    with path.open(

        "r",

        encoding="utf-8",

    ) as file:

        return json.load(
            file
        )


# ============================================================
# READ CSV
# ============================================================

def read_csv(path):

    if not path.exists():

        return []


    with path.open(

        "r",

        newline="",

        encoding="utf-8-sig",

    ) as file:

        return list(

            csv.DictReader(
                file
            )
        )


# ============================================================
# SAFE FLOAT
# ============================================================

def to_float(value):

    if value in {
        None,
        "",
    }:

        return None


    try:

        return float(
            value
        )


    except (
        ValueError,
        TypeError,
    ):

        return None


# ============================================================
# SAFE INTEGER
# ============================================================

def to_int(value):

    if value in {
        None,
        "",
    }:

        return None


    try:

        return int(
            value
        )


    except (
        ValueError,
        TypeError,
    ):

        return None


# ============================================================
# RECORD QA CHECK
# ============================================================

def add_check(
    checks,
    level,
    name,
    message,
):

    checks.append(

        {
            "level":
                level,

            "check":
                name,

            "message":
                message,
        }
    )


# ============================================================
# QA ONE MONTH
# ============================================================

def qa_one_month(
    manifest_entry,
):

    period = manifest_entry[
        "accounting_period"
    ]


    workbook_name = manifest_entry[
        "source_workbook"
    ]


    workbook_stem = Path(
        workbook_name
    ).stem


    month_folder = (

        PROCESSED_FOLDER

        / workbook_stem
    )


    rows_path = (

        month_folder

        / "aic_ims_rows.csv"
    )


    transactions_path = (

        month_folder

        / "aic_ims_transactions.csv"
    )


    allocations_path = (

        month_folder

        / "aic_ims_allocations.csv"
    )


    validation_path = (

        month_folder

        / "aic_ims_validation.json"
    )


    checks = []


    # ========================================================
    # REQUIRED FILES
    # ========================================================

    required_files = [

        rows_path,

        transactions_path,

        allocations_path,

        validation_path,
    ]


    missing_files = [

        str(path)

        for path
        in required_files

        if not path.exists()
    ]


    if missing_files:

        add_check(

            checks,

            "FAIL",

            "required_output_files",

            (
                "Missing output files: "
                + ", ".join(
                    missing_files
                )
            ),
        )


        return {

            "accounting_period":
                period,

            "source_workbook":
                workbook_name,

            "checks":
                checks,
        }


    add_check(

        checks,

        "PASS",

        "required_output_files",

        "All expected IMS sanitizer outputs exist.",
    )


    # ========================================================
    # LOAD DATA
    # ========================================================

    rows = read_csv(
        rows_path
    )


    transactions = read_csv(
        transactions_path
    )


    allocations = read_csv(
        allocations_path
    )


    validation = read_json(
        validation_path
    )


    expected = EXPECTED_STRUCTURE[
        period
    ]


    # ========================================================
    # HEADER ROW
    # ========================================================

    if validation.get(
        "header_row"
    ) == 1:

        add_check(

            checks,

            "PASS",

            "header_row",

            "Actual IMS header correctly detected at row 1.",
        )


    else:

        add_check(

            checks,

            "FAIL",

            "header_row",

            (
                "Expected header row 1, got "
                f"{validation.get('header_row')}."
            ),
        )


    # ========================================================
    # BALANCE FORWARD LOCATION
    # ========================================================

    actual_balance_rows = validation.get(

        "balance_forward_rows",

        [],
    )


    if (
        actual_balance_rows
        == expected[
            "balance_forward_rows"
        ]
    ):

        add_check(

            checks,

            "PASS",

            "balance_forward_detection",

            (
                "Balance Forward detected from content "
                f"at row(s) {actual_balance_rows}."
            ),
        )


    else:

        add_check(

            checks,

            "FAIL",

            "balance_forward_detection",

            (
                "Expected Balance Forward row(s) "
                f"{expected['balance_forward_rows']}, "
                f"got {actual_balance_rows}."
            ),
        )


    # ========================================================
    # ROW-TYPE COUNTS
    # ========================================================

    actual_row_types = validation.get(

        "row_kind_counts",

        {},
    )


    row_types_to_check = [

        "source_transaction",

        "source_transaction_inherited_metadata",

        "void_transaction",

        "allocation_or_supplemental",
    ]


    for row_type in row_types_to_check:


        actual_count = actual_row_types.get(

            row_type,

            0,
        )


        expected_count = expected[
            row_type
        ]


        if actual_count == expected_count:

            add_check(

                checks,

                "PASS",

                f"row_count_{row_type}",

                (
                    f"{row_type}: "
                    f"{actual_count}, matching actual "
                    "spreadsheet inspection."
                ),
            )


        else:

            add_check(

                checks,

                "FAIL",

                f"row_count_{row_type}",

                (
                    f"Expected {expected_count}, "
                    f"got {actual_count}."
                ),
            )


    # ========================================================
    # SOURCE TRANSACTION COUNT
    # ========================================================

    if (
        len(
            transactions
        )
        == expected[
            "source_transaction_count"
        ]
    ):

        add_check(

            checks,

            "PASS",

            "source_transaction_count",

            (
                f"{len(transactions)} source transactions "
                "were preserved."
            ),
        )


    else:

        add_check(

            checks,

            "FAIL",

            "source_transaction_count",

            (
                f"Expected "
                f"{expected['source_transaction_count']} "
                f"source transactions, "
                f"got {len(transactions)}."
            ),
        )


    # ========================================================
    # SUPPLEMENTAL BLOCK COUNT
    # ========================================================

    actual_blocks = validation.get(

        "supplemental_block_count",

        0,
    )


    if (
        actual_blocks
        == expected[
            "supplemental_block_count"
        ]
    ):

        add_check(

            checks,

            "PASS",

            "supplemental_block_count",

            (
                f"{actual_blocks} supplemental allocation "
                "block(s), matching actual inspection."
            ),
        )


    else:

        add_check(

            checks,

            "FAIL",

            "supplemental_block_count",

            (
                f"Expected "
                f"{expected['supplemental_block_count']}, "
                f"got {actual_blocks}."
            ),
        )


    # ========================================================
    # TRANSACTION IDS MUST BE UNIQUE
    # ========================================================

    transaction_ids = [

        row.get(
            "transaction_id"
        )

        for row
        in transactions
    ]


    duplicate_transaction_ids = {

        transaction_id

        for transaction_id
        in transaction_ids

        if (

            transaction_id

            and transaction_ids.count(
                transaction_id
            ) > 1
        )
    }


    if duplicate_transaction_ids:

        add_check(

            checks,

            "FAIL",

            "transaction_id_uniqueness",

            (
                "Duplicate transaction IDs: "
                + ", ".join(
                    sorted(
                        duplicate_transaction_ids
                    )
                )
            ),
        )


    else:

        add_check(

            checks,

            "PASS",

            "transaction_id_uniqueness",

            "Every source transaction has a unique ID.",
        )


    # ========================================================
    # ALLOCATION IDS MUST BE UNIQUE
    # ========================================================

    allocation_ids = [

        row.get(
            "allocation_id"
        )

        for row
        in allocations
    ]


    duplicate_allocation_ids = {

        allocation_id

        for allocation_id
        in allocation_ids

        if (

            allocation_id

            and allocation_ids.count(
                allocation_id
            ) > 1
        )
    }


    if duplicate_allocation_ids:

        add_check(

            checks,

            "FAIL",

            "allocation_id_uniqueness",

            (
                "Duplicate allocation IDs found."
            ),
        )


    else:

        add_check(

            checks,

            "PASS",

            "allocation_id_uniqueness",

            "Every allocation line has a unique ID.",
        )


    # ========================================================
    # EVERY ALLOCATION MUST LINK TO A REAL TRANSACTION
    # ========================================================

    valid_transaction_ids = set(
        transaction_ids
    )


    invalid_allocation_links = [

        allocation

        for allocation
        in allocations

        if (
            allocation.get(
                "transaction_id"
            )
            not in valid_transaction_ids
        )
    ]


    if invalid_allocation_links:

        add_check(

            checks,

            "FAIL",

            "allocation_transaction_linkage",

            (
                f"{len(invalid_allocation_links)} allocation "
                "line(s) point to nonexistent transactions."
            ),
        )


    else:

        add_check(

            checks,

            "PASS",

            "allocation_transaction_linkage",

            (
                "Every normalized allocation line points "
                "to a valid source transaction."
            ),
        )


    # ========================================================
    # NO AMBIGUOUS SUPPLEMENTAL BLOCKS
    # ========================================================

    ambiguous_count = validation.get(

        "ambiguous_supplemental_block_count",

        0,
    )


    if ambiguous_count == 0:

        add_check(

            checks,

            "PASS",

            "supplemental_allocation_linkage",

            (
                "All supplemental allocation blocks were "
                "linked without ambiguity."
            ),
        )


    else:

        add_check(

            checks,

            "FAIL",

            "supplemental_allocation_linkage",

            (
                f"{ambiguous_count} supplemental block(s) "
                "remain ambiguous."
            ),
        )


    # ========================================================
    # JANUARY INHERITED-METADATA LOGIC
    # ========================================================

    inherited_ambiguities = validation.get(

        "source_continuation_inheritance_ambiguity_count",

        0,
    )


    if inherited_ambiguities == 0:

        add_check(

            checks,

            "PASS",

            "inherited_metadata_linkage",

            (
                "All inherited-metadata source transactions "
                "were resolved without ambiguity."
            ),
        )


    else:

        add_check(

            checks,

            "FAIL",

            "inherited_metadata_linkage",

            (
                f"{inherited_ambiguities} inherited-metadata "
                "row(s) remain ambiguous."
            ),
        )


    # ========================================================
    # FORMULAS ONLY IN K/L
    # ========================================================

    formula_outside_k_l = validation.get(

        "formula_cells_outside_K_L",

        0,
    )


    if formula_outside_k_l == 0:

        add_check(

            checks,

            "PASS",

            "formula_location",

            (
                "Formula behavior is confined to K/L, "
                "matching actual workbook inspection."
            ),
        )


    else:

        add_check(

            checks,

            "FAIL",

            "formula_location",

            (
                f"{formula_outside_k_l} formula cell(s) "
                "occur outside K/L."
            ),
        )


    # ========================================================
    # INDEPENDENT ALLOCATION TOTAL RECONCILIATION
    # ========================================================
    #
    # Do not rely only on the sanitizer's own validation.
    #
    # Recalculate allocation totals from the output CSVs.
    # ========================================================

    allocation_totals = defaultdict(
        float
    )


    numeric_allocation_count = defaultdict(
        int
    )


    for allocation in allocations:


        amount = to_float(

            allocation.get(
                "allocation_amount_numeric"
            )
        )


        if amount is None:

            continue


        transaction_id = (
            allocation[
                "transaction_id"
            ]
        )


        allocation_totals[
            transaction_id
        ] += amount


        numeric_allocation_count[
            transaction_id
        ] += 1


    reconciliation_failures = []


    for transaction in transactions:


        transaction_id = transaction[
            "transaction_id"
        ]


        expected_amount = to_float(

            transaction.get(
                "expected_workpaper_amount"
            )
        )


        if expected_amount is None:

            continue


        if (
            transaction_id
            not in allocation_totals
        ):

            # No allocation is handled separately below.
            continue


        actual_amount = allocation_totals[
            transaction_id
        ]


        difference = (

            actual_amount

            - expected_amount
        )


        if abs(
            difference
        ) > TOLERANCE:


            reconciliation_failures.append(

                {
                    "transaction_id":
                        transaction_id,

                    "source_row":
                        transaction.get(
                            "source_row"
                        ),

                    "expected":
                        expected_amount,

                    "actual":
                        actual_amount,

                    "difference":
                        difference,
                }
            )


    if reconciliation_failures:

        add_check(

            checks,

            "FAIL",

            "independent_allocation_reconciliation",

            (
                f"{len(reconciliation_failures)} transaction(s) "
                "failed independent allocation-total "
                "reconciliation."
            ),
        )


    else:

        add_check(

            checks,

            "PASS",

            "independent_allocation_reconciliation",

            (
                "All transactions with numeric allocations "
                "independently reconcile to their expected "
                "workpaper amount."
            ),
        )


    # ========================================================
    # TRANSACTIONS WITH NO ALLOCATION
    # ========================================================
    #
    # Missing allocation is NOT automatically a sanitizer
    # failure.
    #
    # It can represent a genuine unresolved accounting item.
    #
    # March row 135 is the known example.
    # ========================================================

    transaction_ids_with_allocations = {

        allocation[
            "transaction_id"
        ]

        for allocation
        in allocations
    }


    transactions_without_allocation = [

        transaction

        for transaction
        in transactions

        if (
            transaction[
                "transaction_id"
            ]
            not in transaction_ids_with_allocations
        )
    ]


    expected_missing = expected[
        "expected_transactions_without_allocation"
    ]


    actual_missing = len(
        transactions_without_allocation
    )


    if actual_missing == expected_missing:


        if actual_missing == 0:

            message = (
                "Every source transaction has at least "
                "one normalized accounting allocation."
            )


        else:

            details = [

                (
                    f"row {transaction.get('source_row')}: "
                    f"{transaction.get('source_description')} | "
                    f"{transaction.get('date_cleared_raw')}"
                )

                for transaction
                in transactions_without_allocation
            ]


            message = (

                f"{actual_missing} source transaction(s) "
                "have no allocation, matching actual data: "
                + " | ".join(
                    details
                )
            )


        add_check(

            checks,

            "PASS",

            "transactions_without_allocation",

            message,
        )


    else:

        add_check(

            checks,

            "FAIL",

            "transactions_without_allocation",

            (
                f"Expected {expected_missing} source "
                "transaction(s) without allocations, "
                f"found {actual_missing}."
            ),
        )


    # ========================================================
    # SOURCE ROW UNIQUENESS
    # ========================================================

    source_rows = [

        to_int(
            transaction.get(
                "source_row"
            )
        )

        for transaction
        in transactions
    ]


    duplicate_source_rows = {

        source_row

        for source_row
        in source_rows

        if (

            source_row is not None

            and source_rows.count(
                source_row
            ) > 1
        )
    }


    if duplicate_source_rows:

        add_check(

            checks,

            "FAIL",

            "source_row_uniqueness",

            (
                "Multiple source transactions were created "
                "from the same IMS source row."
            ),
        )


    else:

        add_check(

            checks,

            "PASS",

            "source_row_uniqueness",

            (
                "Each normalized source transaction maps "
                "to one unique original IMS row."
            ),
        )


    # ========================================================
    # RETURN MONTH RESULT
    # ========================================================

    return {

        "accounting_period":
            period,

        "source_workbook":
            workbook_name,

        "source_transaction_count":
            len(
                transactions
            ),

        "allocation_line_count":
            len(
                allocations
            ),

        "transactions_without_allocation":
            [

                {
                    "transaction_id":
                        transaction.get(
                            "transaction_id"
                        ),

                    "source_row":
                        transaction.get(
                            "source_row"
                        ),

                    "description":
                        transaction.get(
                            "source_description"
                        ),

                    "date_cleared_raw":
                        transaction.get(
                            "date_cleared_raw"
                        ),
                }

                for transaction
                in transactions_without_allocation
            ],

        "checks":
            checks,
    }


# ============================================================
# MAIN QA
# ============================================================

def main():

    print(
        "ASCOT AIC IMS SANITIZER — STRUCTURAL QA"
    )


    # ========================================================
    # MANIFEST EXISTS?
    # ========================================================

    if not MANIFEST_PATH.exists():

        raise FileNotFoundError(

            "Could not find:\n"
            "data/processed/"
            "aic_ims_processing_manifest.json\n\n"
            "Run sanitize_aic_ims.py first."
        )


    manifest = read_json(
        MANIFEST_PATH
    )


    global_checks = []


    # ========================================================
    # SUCCESSFUL MONTHS
    # ========================================================

    successful_entries = [

        entry

        for entry
        in manifest

        if entry.get(
            "status"
        ) == "success"
    ]


    if len(
        successful_entries
    ) == 7:


        add_check(

            global_checks,

            "PASS",

            "successful_month_count",

            "All 7 expected accounting periods were sanitized.",
        )


    else:

        add_check(

            global_checks,

            "FAIL",

            "successful_month_count",

            (
                f"Expected 7 successful months, "
                f"found {len(successful_entries)}."
            ),
        )


    # ========================================================
    # CHRONOLOGICAL ORDER
    # ========================================================

    actual_periods = [

        entry[
            "accounting_period"
        ]

        for entry
        in successful_entries
    ]


    if actual_periods == EXPECTED_PERIODS:


        add_check(

            global_checks,

            "PASS",

            "chronological_period_order",

            (
                "IMS accounting periods are in true "
                "chronological order: "
                + " -> ".join(
                    actual_periods
                )
            ),
        )


    else:

        add_check(

            global_checks,

            "FAIL",

            "chronological_period_order",

            (
                "Expected "
                + " -> ".join(
                    EXPECTED_PERIODS
                )
                + "; actual "
                + " -> ".join(
                    actual_periods
                )
            ),
        )


    # ========================================================
    # QA EACH MONTH
    # ========================================================

    monthly_results = []


    for entry in successful_entries:


        monthly_results.append(

            qa_one_month(
                entry
            )
        )


    # ========================================================
    # COUNT RESULTS
    # ========================================================

    all_checks = list(
        global_checks
    )


    for month in monthly_results:

        all_checks.extend(
            month[
                "checks"
            ]
        )


    pass_count = sum(

        check[
            "level"
        ] == "PASS"

        for check
        in all_checks
    )


    warn_count = sum(

        check[
            "level"
        ] == "WARN"

        for check
        in all_checks
    )


    fail_count = sum(

        check[
            "level"
        ] == "FAIL"

        for check
        in all_checks
    )


    # ========================================================
    # OVERALL RESULT
    # ========================================================

    if fail_count > 0:

        overall_status = (
            "FAIL"
        )


    elif warn_count > 0:

        overall_status = (
            "PASS_WITH_WARNINGS"
        )


    else:

        overall_status = (
            "PASS"
        )


    # ========================================================
    # SAVE FULL REPORT
    # ========================================================

    report = {

        "overall_status":
            overall_status,

        "summary": {

            "passes":
                pass_count,

            "warnings":
                warn_count,

            "failures":
                fail_count,
        },

        "global_checks":
            global_checks,

        "monthly_results":
            monthly_results,
    }


    with QA_REPORT_PATH.open(

        "w",

        encoding="utf-8",

    ) as file:


        json.dump(

            report,

            file,

            indent=2,

            ensure_ascii=False,
        )


    # ========================================================
    # TERMINAL OUTPUT
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "GLOBAL CHECKS"
    )

    print(
        "========================================"
    )


    for check in global_checks:


        print(

            f"[{check['level']}] "
            f"{check['check']}: "
            f"{check['message']}"
        )


    for month in monthly_results:


        print(
            "\n----------------------------------------"
        )


        print(

            f"{month['accounting_period']} | "
            f"{month['source_workbook']}"
        )


        print(

            f"Source transactions: "
            f"{month['source_transaction_count']} | "
            f"Allocations: "
            f"{month['allocation_line_count']} | "
            f"No allocation: "
            f"{len(month['transactions_without_allocation'])}"
        )


        important_checks = [

            check

            for check
            in month[
                "checks"
            ]

            if check[
                "level"
            ] in {
                "WARN",
                "FAIL",
            }
        ]


        if not important_checks:


            print(
                "[PASS] All structural checks passed."
            )


        else:


            for check in important_checks:


                print(

                    f"[{check['level']}] "
                    f"{check['check']}: "
                    f"{check['message']}"
                )


    print(
        "\n========================================"
    )

    print(
        "QA RESULT"
    )

    print(
        "========================================"
    )


    print(
        f"Overall status: "
        f"{overall_status}"
    )


    print(
        f"PASS: {pass_count}"
    )


    print(
        f"WARN: {warn_count}"
    )


    print(
        f"FAIL: {fail_count}"
    )


    print(
        "\nFull QA report:"
    )


    print(
        "data/processed/"
        "aic_ims_qa_report.json"
    )


    if overall_status == "PASS":


        print(
            "\n✓ AIC IMS sanitizer is structurally ready "
            "for the next module."
        )


    elif overall_status == "PASS_WITH_WARNINGS":


        print(
            "\n✓ IMS has no structural failures, but "
            "warnings should be reviewed before lock-in."
        )


    else:


        print(
            "\n✗ IMS structural QA failed. "
            "Do not proceed to the next data source yet."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()