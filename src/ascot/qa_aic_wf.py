# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# AIC WF SANITIZER — STRUCTURAL QA
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# The sanitizer ran successfully, but "the code ran" does not
# necessarily mean "the accounting data were interpreted
# correctly."
#
# Before building the IMS sanitizer, this script performs a
# structural quality check on the normalized AIC WF outputs.
#
#
# WE WILL CHECK:
#
# 1. Were all seven accounting months processed?
#
#       January 2026
#       February 2026
#       ...
#       July 2026
#
# 2. Are the months in true chronological order?
#
# 3. Did each month have:
#
#       - transactions,
#       - a detected main subtotal boundary,
#       - at least one control/subtotal row?
#
# 4. Does the transaction population reconcile structurally?
#
#       total transactions
#           =
#       main cash activity
#           +
#       ZBA/sweep
#           +
#       unexpected post-subtotal
#
# 5. Are ZBA/sweep transactions actually located after the
#    main subtotal?
#
# 6. Do source rows and accounting periods look consistent?
#
# 7. Are legacy Excel presentation/color labels being captured?
#
#
# IMPORTANT:
#
# Some conditions are FAILURES.
#
# Example:
#     zero transactions
#
# Some conditions are WARNINGS.
#
# Example:
#     a post-subtotal transaction that is not recognized
#     as ZBA/sweep
#
# We do not want to silently delete unusual accounting cases.
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import csv
import json

from pathlib import Path


# ============================================================
# PROJECT PATHS
# ============================================================

PROCESSED_FOLDER = Path(
    "data/processed"
)


MANIFEST_PATH = (
    PROCESSED_FOLDER
    / "aic_wf_processing_manifest.json"
)


QA_REPORT_PATH = (
    PROCESSED_FOLDER
    / "aic_wf_qa_report.json"
)


# ============================================================
# EXPECTED ACCOUNTING PERIODS
# ============================================================
#
# We explicitly define the periods currently supplied by Ascot.
#
# Later, when August is added, we can extend this list or make
# the expected period range dynamic.
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
# HELPER: READ JSON
# ============================================================

def read_json(path):
    """
    Read a JSON file and return the Python object.
    """

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:

        return json.load(
            file
        )


# ============================================================
# HELPER: READ CSV
# ============================================================

def read_csv(path):
    """
    Read a CSV file as a list of dictionaries.

    No pandas is needed.
    """

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
# HELPER: CONVERT TEXT TO INTEGER
# ============================================================

def to_int(value):
    """
    Safely convert a CSV/JSON value into an integer.
    """

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
# HELPER: RECORD A QA RESULT
# ============================================================

def add_check(
    checks,
    level,
    name,
    message,
):
    """
    Add one QA finding.

    level should be:

        PASS
        WARN
        FAIL
    """

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
    """
    Perform structural QA on one accounting month.
    """

    period = (
        manifest_entry[
            "accounting_period"
        ]
    )


    workbook_name = (
        manifest_entry[
            "source_workbook"
        ]
    )


    workbook_stem = Path(
        workbook_name
    ).stem


    month_folder = (

        PROCESSED_FOLDER

        / workbook_stem
    )


    transaction_path = (

        month_folder

        / "aic_wf_transactions.csv"
    )


    control_path = (

        month_folder

        / "aic_wf_control_rows.csv"
    )


    validation_path = (

        month_folder

        / "aic_wf_validation.json"
    )


    presentation_path = (

        month_folder

        / "aic_wf_presentation.json"
    )


    checks = []


    # ========================================================
    # CHECK 1:
    # REQUIRED OUTPUT FILES EXIST
    # ========================================================

    required_files = [

        transaction_path,

        control_path,

        validation_path,

        presentation_path,
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
                "Missing sanitizer output(s): "
                + ", ".join(
                    missing_files
                )
            ),
        )


        # We cannot meaningfully continue this month's QA.
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

        "All expected sanitizer output files exist.",
    )


    # ========================================================
    # LOAD OUTPUTS
    # ========================================================

    transactions = read_csv(
        transaction_path
    )


    control_rows = read_csv(
        control_path
    )


    validation = read_json(
        validation_path
    )


    presentation = read_json(
        presentation_path
    )


    # ========================================================
    # CHECK 2:
    # TRANSACTION COUNT IS NONZERO
    # ========================================================

    if len(
        transactions
    ) == 0:

        add_check(

            checks,

            "FAIL",

            "transaction_population",

            "No normalized transactions were produced.",
        )


    else:

        add_check(

            checks,

            "PASS",

            "transaction_population",

            (
                f"{len(transactions)} normalized "
                f"transactions were produced."
            ),
        )


    # ========================================================
    # CHECK 3:
    # CSV COUNT AGREES WITH VALIDATION JSON
    # ========================================================

    expected_transaction_count = (
        validation.get(
            "transaction_count"
        )
    )


    if (
        expected_transaction_count
        == len(transactions)
    ):

        add_check(

            checks,

            "PASS",

            "transaction_count_reconciliation",

            (
                f"CSV count agrees with validation file: "
                f"{len(transactions)}."
            ),
        )


    else:

        add_check(

            checks,

            "FAIL",

            "transaction_count_reconciliation",

            (
                f"CSV contains {len(transactions)} rows, "
                f"but validation reports "
                f"{expected_transaction_count}."
            ),
        )


    # ========================================================
    # CHECK 4:
    # MAIN SUBTOTAL BOUNDARY EXISTS
    # ========================================================

    main_subtotal_row = (
        validation.get(
            "main_subtotal_row"
        )
    )


    if main_subtotal_row is None:

        add_check(

            checks,

            "FAIL",

            "main_subtotal_boundary",

            "No main AIC WF subtotal boundary was detected.",
        )


    else:

        add_check(

            checks,

            "PASS",

            "main_subtotal_boundary",

            (
                f"Main subtotal/control boundary detected "
                f"at source row {main_subtotal_row}."
            ),
        )


    # ========================================================
    # CHECK 5:
    # CONTROL ROW EXISTS
    # ========================================================

    if len(
        control_rows
    ) < 1:

        add_check(

            checks,

            "FAIL",

            "control_rows",

            "No subtotal/control row was preserved.",
        )


    else:

        add_check(

            checks,

            "PASS",

            "control_rows",

            (
                f"{len(control_rows)} control/subtotal "
                f"row(s) preserved."
            ),
        )


    # ========================================================
    # CHECK 6:
    # SECTION COUNTS RECONCILE
    # ========================================================

    main_count = sum(

        row.get(
            "section"
        )
        == "main_cash_activity"

        for row
        in transactions
    )


    sweep_count = sum(

        row.get(
            "section"
        )
        == "zba_sweep_transfers"

        for row
        in transactions
    )


    unexpected_count = sum(

        row.get(
            "section"
        )
        == "post_subtotal_other"

        for row
        in transactions
    )


    reconstructed_total = (

        main_count
        + sweep_count
        + unexpected_count
    )


    if reconstructed_total == len(
        transactions
    ):

        add_check(

            checks,

            "PASS",

            "section_population_reconciliation",

            (
                f"Sections reconcile: "
                f"{main_count} main + "
                f"{sweep_count} ZBA/sweep + "
                f"{unexpected_count} unexpected "
                f"= {len(transactions)}."
            ),
        )


    else:

        add_check(

            checks,

            "FAIL",

            "section_population_reconciliation",

            (
                f"Section counts total "
                f"{reconstructed_total}, "
                f"but transaction population is "
                f"{len(transactions)}."
            ),
        )


    # ========================================================
    # CHECK 7:
    # ZBA / SWEEP ITEMS ARE AFTER THE MAIN SUBTOTAL
    # ========================================================

    sweep_rows_before_boundary = []


    if main_subtotal_row is not None:

        for row in transactions:


            if (
                row.get(
                    "section"
                )
                != "zba_sweep_transfers"
            ):

                continue


            source_row = to_int(
                row.get(
                    "source_row"
                )
            )


            if (
                source_row is not None
                and source_row
                <= main_subtotal_row
            ):

                sweep_rows_before_boundary.append(
                    source_row
                )


    if sweep_rows_before_boundary:

        add_check(

            checks,

            "FAIL",

            "zba_sweep_position",

            (
                "ZBA/sweep transactions were classified "
                "before the subtotal boundary at rows: "
                + ", ".join(
                    str(row_number)
                    for row_number
                    in sweep_rows_before_boundary
                )
            ),
        )


    else:

        add_check(

            checks,

            "PASS",

            "zba_sweep_position",

            (
                "All identified ZBA/sweep transactions "
                "occur after the main subtotal boundary."
            ),
        )


    # ========================================================
    # CHECK 8:
    # POST-SUBTOTAL NON-SWEEP TRANSACTIONS
    # ========================================================
    #
    # This is a WARNING rather than an automatic failure.
    #
    # An unusual transaction could be legitimate and should
    # never be silently removed merely because it differs
    # from our expected pattern.
    # ========================================================

    if unexpected_count == 0:

        add_check(

            checks,

            "PASS",

            "unexpected_post_subtotal",

            (
                "No unexplained transactions appear "
                "after the main subtotal."
            ),
        )


    else:

        unexpected_examples = [

            (
                f"row {row.get('source_row')}: "
                f"{row.get('transaction_description')}"
            )

            for row
            in transactions

            if (
                row.get(
                    "section"
                )
                == "post_subtotal_other"
            )
        ]


        add_check(

            checks,

            "WARN",

            "unexpected_post_subtotal",

            (
                f"{unexpected_count} transaction(s) appear "
                f"after the subtotal but are not recognized "
                f"as ZBA/sweep. Examples: "
                + " | ".join(
                    unexpected_examples[:5]
                )
            ),
        )


    # ========================================================
    # CHECK 9:
    # ACCOUNTING PERIOD IS CONSISTENT
    # ========================================================

    incorrect_period_rows = [

        row.get(
            "source_row"
        )

        for row
        in transactions

        if (
            row.get(
                "accounting_period"
            )
            != period
        )
    ]


    if incorrect_period_rows:

        add_check(

            checks,

            "FAIL",

            "accounting_period_consistency",

            (
                f"{len(incorrect_period_rows)} transaction(s) "
                f"have an accounting period inconsistent "
                f"with {period}."
            ),
        )


    else:

        add_check(

            checks,

            "PASS",

            "accounting_period_consistency",

            (
                f"All transactions are labeled "
                f"{period}."
            ),
        )


    # ========================================================
    # CHECK 10:
    # SOURCE ROWS ARE PRESENT
    # ========================================================

    missing_source_rows = [

        row

        for row
        in transactions

        if to_int(
            row.get(
                "source_row"
            )
        ) is None
    ]


    if missing_source_rows:

        add_check(

            checks,

            "FAIL",

            "source_provenance",

            (
                f"{len(missing_source_rows)} transaction(s) "
                f"do not contain a usable source row."
            ),
        )


    else:

        add_check(

            checks,

            "PASS",

            "source_provenance",

            "Every transaction retains its original Excel row.",
        )


    # ========================================================
    # CHECK 11:
    # SOURCE ROWS SHOULD NOT BE DUPLICATED
    # ========================================================

    source_rows = [

        to_int(
            row.get(
                "source_row"
            )
        )

        for row
        in transactions
    ]


    duplicate_source_rows = sorted(

        {

            row_number

            for row_number
            in source_rows

            if (
                row_number is not None
                and source_rows.count(
                    row_number
                ) > 1
            )
        }
    )


    if duplicate_source_rows:

        add_check(

            checks,

            "FAIL",

            "source_row_uniqueness",

            (
                "The sanitizer produced multiple transactions "
                "from the same AIC WF source row: "
                + ", ".join(
                    str(row_number)
                    for row_number
                    in duplicate_source_rows[:10]
                )
            ),
        )


    else:

        add_check(

            checks,

            "PASS",

            "source_row_uniqueness",

            (
                "Each normalized transaction maps to one "
                "unique AIC WF source row."
            ),
        )


    # ========================================================
    # CHECK 12:
    # COLOR / PRESENTATION LEGEND WAS CAPTURED
    # ========================================================

    color_legend = (
        presentation.get(
            "color_legend",
            [],
        )
    )


    if not color_legend:

        add_check(

            checks,

            "WARN",

            "presentation_legend",

            (
                "No Ascot presentation/color legend "
                "was captured."
            ),
        )


    else:

        captured_labels = [

            item.get(
                "label"
            )

            for item
            in color_legend
        ]


        add_check(

            checks,

            "PASS",

            "presentation_legend",

            (
                f"Captured {len(color_legend)} legend "
                f"entry/entries: "
                + ", ".join(
                    str(label)
                    for label
                    in captured_labels
                )
            ),
        )


    # ========================================================
    # CHECK 13:
    # HOW MANY TRANSACTIONS ACTUALLY RETAIN A LEGACY LABEL?
    # ========================================================

    labeled_transactions = [

        row

        for row
        in transactions

        if (
            row.get(
                "legacy_presentation_labels"
            )
            not in {
                None,
                "",
            }
        )
    ]


    if len(
        labeled_transactions
    ) == 0:

        add_check(

            checks,

            "WARN",

            "legacy_color_application",

            (
                "The legend was searched, but no normalized "
                "transaction retained a legacy presentation "
                "label. We should inspect the color-reading "
                "logic before relying on colors."
            ),
        )


    else:

        percentage = (

            len(
                labeled_transactions
            )

            / len(
                transactions
            )

            * 100
        )


        add_check(

            checks,

            "PASS",

            "legacy_color_application",

            (
                f"{len(labeled_transactions)} of "
                f"{len(transactions)} transactions "
                f"({percentage:.1f}%) retain at least one "
                f"legacy presentation label."
            ),
        )


    # ========================================================
    # RETURN MONTH QA
    # ========================================================

    return {

        "accounting_period":
            period,

        "source_workbook":
            workbook_name,

        "transaction_count":
            len(
                transactions
            ),

        "main_cash_activity_count":
            main_count,

        "zba_sweep_count":
            sweep_count,

        "unexpected_post_subtotal_count":
            unexpected_count,

        "checks":
            checks,
    }


# ============================================================
# MAIN QA PROGRAM
# ============================================================

def main():

    print(
        "ASCOT AIC WF SANITIZER — STRUCTURAL QA"
    )


    # ========================================================
    # MANIFEST MUST EXIST
    # ========================================================

    if not MANIFEST_PATH.exists():

        raise FileNotFoundError(

            "Could not find:\n"
            "data/processed/"
            "aic_wf_processing_manifest.json\n\n"
            "Run sanitize_aic_wf.py first."
        )


    manifest = read_json(
        MANIFEST_PATH
    )


    # ========================================================
    # CHECK GLOBAL PROCESSING ORDER
    # ========================================================

    global_checks = []


    successful_entries = [

        item

        for item
        in manifest

        if item.get(
            "status"
        ) == "success"
    ]


    actual_periods = [

        item[
            "accounting_period"
        ]

        for item
        in successful_entries
    ]


    # --------------------------------------------------------
    # ALL SEVEN MONTHS SUCCESSFUL?
    # --------------------------------------------------------

    if len(
        successful_entries
    ) == len(
        EXPECTED_PERIODS
    ):

        add_check(

            global_checks,

            "PASS",

            "successful_month_count",

            (
                f"All {len(EXPECTED_PERIODS)} expected "
                f"months were successfully sanitized."
            ),
        )


    else:

        add_check(

            global_checks,

            "FAIL",

            "successful_month_count",

            (
                f"Expected {len(EXPECTED_PERIODS)} "
                f"successful months, found "
                f"{len(successful_entries)}."
            ),
        )


    # --------------------------------------------------------
    # EXACT ACCOUNTING PERIODS?
    # --------------------------------------------------------

    if actual_periods == EXPECTED_PERIODS:

        add_check(

            global_checks,

            "PASS",

            "chronological_period_order",

            (
                "Accounting periods are in the correct "
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
                "Expected: "
                + " -> ".join(
                    EXPECTED_PERIODS
                )
                + " | Actual: "
                + " -> ".join(
                    actual_periods
                )
            ),
        )


    # ========================================================
    # QA EACH SUCCESSFUL MONTH
    # ========================================================

    monthly_results = []


    for entry in successful_entries:

        monthly_results.append(

            qa_one_month(
                entry
            )
        )


    # ========================================================
    # COUNT PASS / WARN / FAIL
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
    # DETERMINE OVERALL QA STATUS
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
    # SAVE QA REPORT
    # ========================================================

    qa_report = {

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

            qa_report,

            file,

            indent=2,

            ensure_ascii=False,
        )


    # ========================================================
    # PRINT SUMMARY
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


    # ========================================================
    # PRINT MONTHLY SUMMARY
    # ========================================================

    for month in monthly_results:


        print(
            "\n----------------------------------------"
        )


        print(

            f"{month['accounting_period']} | "
            f"{month['source_workbook']}"
        )


        print(

            f"Transactions: "
            f"{month['transaction_count']} | "
            f"Main: "
            f"{month['main_cash_activity_count']} | "
            f"ZBA/Sweep: "
            f"{month['zba_sweep_count']} | "
            f"Unexpected: "
            f"{month['unexpected_post_subtotal_count']}"
        )


        # To keep the terminal readable, print only
        # WARNINGS and FAILURES at the monthly level.
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


    # ========================================================
    # FINAL STATUS
    # ========================================================

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
        "aic_wf_qa_report.json"
    )


    # ========================================================
    # INTERPRETATION
    # ========================================================

    if overall_status == "PASS":

        print(
            "\n✓ AIC WF sanitizer is structurally ready "
            "for the next module."
        )


    elif overall_status == "PASS_WITH_WARNINGS":

        print(
            "\n✓ No structural failures were found, but "
            "one or more warnings should be reviewed "
            "before we lock the sanitizer."
        )


    else:

        print(
            "\n✗ Structural failures were found. "
            "We should correct them before building "
            "the IMS sanitizer."
        )


# ============================================================
# RUN QA
# ============================================================

if __name__ == "__main__":

    main()