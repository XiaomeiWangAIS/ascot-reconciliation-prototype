# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# WF PREVIOUS DAY SANITIZER — STRUCTURAL QA
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# The Previous Day sanitizer ran successfully.
#
# This script now checks whether the sanitized outputs actually
# preserve the structures we observed directly in the original
# January–July 2026 workbooks.
#
#
# THIS QA DOES NOT MODIFY DATA.
#
#
# WE CHECK:
#
# 1. All 7 months processed successfully.
#
# 2. Months are in chronological order.
#
# 3. Actual header placement is preserved:
#
#       Jan 1
#       Feb 1
#       Mar 2
#       Apr 1
#       May 1
#       Jun 1
#       Jul 1
#
# 4. Full-report transaction counts match the inspected files.
#
# 5. AIC Disbursement transaction counts match inspection.
#
# 6. Main cash vs ZBA/sweep populations match inspection.
#
# 7. The AIC account number is consistently 4062522693.
#
# 8. Every transaction has exactly one nonzero debit/credit.
#
# 9. bank_net_amount independently equals:
#
#       debit - credit
#
#    We deliberately do NOT trust source column G.
#
# 10. AIC ZBA/sweep tags use only the four observed source
#     transaction descriptions.
#
# 11. Source transaction IDs are unique.
#
# 12. Source rows are unique.
#
# 13. July's legitimate duplicate-visible transaction remains
#     preserved.
#
# 14. AIC client-analysis-fee count is zero Jan–Jul.
#
# 15. Structural warning count remains zero.
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
    / "wf_previous_day_processing_manifest.json"
)


QA_REPORT_PATH = (
    PROCESSED_FOLDER
    / "wf_previous_day_qa_report.json"
)


# ============================================================
# ACCOUNTING TOLERANCE
# ============================================================

TOLERANCE = 0.02


# ============================================================
# EXPECTED MONTHS
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
# EXPECTED STRUCTURE FROM DIRECT INSPECTION
# ============================================================
#
# These are based on the actual Previous Day workbooks,
# NOT on the SOP.
# ============================================================

EXPECTED = {

    "2026-01": {

        "header_row":
            1,

        "full_report_transactions":
            3718,

        "bank_accounts":
            31,

        "control_rows":
            1,

        "extra_sheets":
            9,

        "aic_total":
            167,

        "aic_main":
            106,

        "aic_zba":
            41,

        "aic_sweep":
            20,

        "aic_zba_sweep":
            61,

        "aic_analysis_fees":
            0,

        "visible_duplicate_extra_rows":
            0,
    },


    "2026-02": {

        "header_row":
            1,

        "full_report_transactions":
            4208,

        "bank_accounts":
            31,

        "control_rows":
            0,

        "extra_sheets":
            0,

        "aic_total":
            369,

        "aic_main":
            310,

        "aic_zba":
            40,

        "aic_sweep":
            19,

        "aic_zba_sweep":
            59,

        "aic_analysis_fees":
            0,

        "visible_duplicate_extra_rows":
            0,
    },


    "2026-03": {

        "header_row":
            2,

        "full_report_transactions":
            4449,

        "bank_accounts":
            29,

        "control_rows":
            1,

        "extra_sheets":
            0,

        "aic_total":
            204,

        "aic_main":
            127,

        "aic_zba":
            55,

        "aic_sweep":
            22,

        "aic_zba_sweep":
            77,

        "aic_analysis_fees":
            0,

        "visible_duplicate_extra_rows":
            0,
    },


    "2026-04": {

        "header_row":
            1,

        "full_report_transactions":
            4267,

        "bank_accounts":
            29,

        "control_rows":
            0,

        "extra_sheets":
            1,

        "aic_total":
            215,

        "aic_main":
            123,

        "aic_zba":
            70,

        "aic_sweep":
            22,

        "aic_zba_sweep":
            92,

        "aic_analysis_fees":
            0,

        "visible_duplicate_extra_rows":
            0,
    },


    "2026-05": {

        "header_row":
            1,

        "full_report_transactions":
            3997,

        "bank_accounts":
            28,

        "control_rows":
            0,

        "extra_sheets":
            0,

        "aic_total":
            157,

        "aic_main":
            70,

        "aic_zba":
            67,

        "aic_sweep":
            20,

        "aic_zba_sweep":
            87,

        "aic_analysis_fees":
            0,

        "visible_duplicate_extra_rows":
            0,
    },


    "2026-06": {

        "header_row":
            1,

        "full_report_transactions":
            4185,

        "bank_accounts":
            28,

        "control_rows":
            0,

        "extra_sheets":
            0,

        "aic_total":
            180,

        "aic_main":
            90,

        "aic_zba":
            69,

        "aic_sweep":
            21,

        "aic_zba_sweep":
            90,

        "aic_analysis_fees":
            0,

        "visible_duplicate_extra_rows":
            0,
    },


    "2026-07": {

        "header_row":
            1,

        "full_report_transactions":
            4221,

        "bank_accounts":
            26,

        "control_rows":
            0,

        "extra_sheets":
            0,

        "aic_total":
            222,

        "aic_main":
            126,

        "aic_zba":
            73,

        "aic_sweep":
            23,

        "aic_zba_sweep":
            96,

        "aic_analysis_fees":
            0,

        # Actual data contains one additional row sharing
        # identical visible values with another transaction.
        #
        # It is legitimate and must remain preserved.
        "visible_duplicate_extra_rows":
            1,
    },
}


# ============================================================
# KNOWN AIC ACCOUNT
# ============================================================

AIC_ACCOUNT = (
    "4062522693"
)


# ============================================================
# EXACT ZBA / SWEEP TYPES OBSERVED
# ============================================================

ZBA_TYPES = {

    "ZBA DEBIT TRANSFER",

    "ZBA CREDIT TRANSFER",
}


SWEEP_TYPES = {

    "SWEEP PRINCIPAL BUY",

    "SWEEP PRINCIPAL SELL",
}


ZBA_SWEEP_TYPES = (

    ZBA_TYPES

    | SWEEP_TYPES
)


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
# BOOLEAN FROM CSV
# ============================================================
#
# CSV stores booleans as strings such as:
#
#     True
#     False
#
# ============================================================

def to_bool(value):

    return str(
        value
    ).strip().lower() == "true"


# ============================================================
# ADD QA RESULT
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
# QA ONE ACCOUNTING MONTH
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


    full_transactions_path = (

        month_folder

        / "wf_previous_day_transactions.csv"
    )


    aic_transactions_path = (

        month_folder

        / "aic_previous_day_transactions.csv"
    )


    control_rows_path = (

        month_folder

        / "wf_previous_day_control_rows.csv"
    )


    account_summary_path = (

        month_folder

        / "wf_previous_day_account_summary.csv"
    )


    validation_path = (

        month_folder

        / "wf_previous_day_validation.json"
    )


    checks = []


    # ========================================================
    # REQUIRED OUTPUTS
    # ========================================================

    required_files = [

        full_transactions_path,

        aic_transactions_path,

        control_rows_path,

        account_summary_path,

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

        "All expected Previous Day sanitizer outputs exist.",
    )


    # ========================================================
    # LOAD OUTPUTS
    # ========================================================

    full_transactions = read_csv(
        full_transactions_path
    )


    aic_transactions = read_csv(
        aic_transactions_path
    )


    control_rows = read_csv(
        control_rows_path
    )


    account_summary = read_csv(
        account_summary_path
    )


    validation = read_json(
        validation_path
    )


    expected = EXPECTED[
        period
    ]


    # ========================================================
    # HEADER ROW
    # ========================================================

    actual_header = validation.get(
        "header_row"
    )


    if (
        actual_header
        == expected[
            "header_row"
        ]
    ):


        add_check(

            checks,

            "PASS",

            "header_row",

            (
                f"Header correctly detected at row "
                f"{actual_header}."
            ),
        )


    else:


        add_check(

            checks,

            "FAIL",

            "header_row",

            (
                f"Expected row "
                f"{expected['header_row']}, "
                f"got {actual_header}."
            ),
        )


    # ========================================================
    # FULL REPORT TRANSACTION COUNT
    # ========================================================

    if (
        len(
            full_transactions
        )
        == expected[
            "full_report_transactions"
        ]
    ):


        add_check(

            checks,

            "PASS",

            "full_report_transaction_count",

            (
                f"{len(full_transactions)} full-report "
                "transactions preserved."
            ),
        )


    else:


        add_check(

            checks,

            "FAIL",

            "full_report_transaction_count",

            (
                f"Expected "
                f"{expected['full_report_transactions']}, "
                f"got {len(full_transactions)}."
            ),
        )


    # ========================================================
    # BANK ACCOUNT COUNT
    # ========================================================

    if (
        len(
            account_summary
        )
        == expected[
            "bank_accounts"
        ]
    ):


        add_check(

            checks,

            "PASS",

            "bank_account_count",

            (
                f"{len(account_summary)} bank accounts "
                "preserved."
            ),
        )


    else:


        add_check(

            checks,

            "FAIL",

            "bank_account_count",

            (
                f"Expected "
                f"{expected['bank_accounts']} bank accounts, "
                f"got {len(account_summary)}."
            ),
        )


    # ========================================================
    # CONTROL / HELPER ROW COUNT
    # ========================================================

    if (
        len(
            control_rows
        )
        == expected[
            "control_rows"
        ]
    ):


        add_check(

            checks,

            "PASS",

            "control_row_count",

            (
                f"{len(control_rows)} control/helper "
                "row(s), matching inspection."
            ),
        )


    else:


        add_check(

            checks,

            "FAIL",

            "control_row_count",

            (
                f"Expected "
                f"{expected['control_rows']} helper rows, "
                f"got {len(control_rows)}."
            ),
        )


    # ========================================================
    # EXTRA / DERIVED SHEETS
    # ========================================================

    extra_sheets = validation.get(

        "extra_sheet_names",

        [],
    )


    if (
        len(
            extra_sheets
        )
        == expected[
            "extra_sheets"
        ]
    ):


        add_check(

            checks,

            "PASS",

            "extra_sheet_count",

            (
                f"{len(extra_sheets)} extra/derived "
                "sheet(s), matching source inspection."
            ),
        )


    else:


        add_check(

            checks,

            "FAIL",

            "extra_sheet_count",

            (
                f"Expected "
                f"{expected['extra_sheets']} extra sheets, "
                f"got {len(extra_sheets)}."
            ),
        )


    # ========================================================
    # AIC TRANSACTION COUNT
    # ========================================================

    if (
        len(
            aic_transactions
        )
        == expected[
            "aic_total"
        ]
    ):


        add_check(

            checks,

            "PASS",

            "aic_transaction_count",

            (
                f"{len(aic_transactions)} AIC Disbursement "
                "transactions preserved."
            ),
        )


    else:


        add_check(

            checks,

            "FAIL",

            "aic_transaction_count",

            (
                f"Expected {expected['aic_total']} AIC "
                f"transactions, got "
                f"{len(aic_transactions)}."
            ),
        )


    # ========================================================
    # AIC ACCOUNT NUMBER CONSISTENCY
    # ========================================================

    incorrect_accounts = [

        transaction

        for transaction
        in aic_transactions

        if (
            transaction.get(
                "account_number"
            )
            != AIC_ACCOUNT
        )
    ]


    if incorrect_accounts:


        add_check(

            checks,

            "FAIL",

            "aic_account_number",

            (
                f"{len(incorrect_accounts)} filtered AIC "
                "rows do not have account 4062522693."
            ),
        )


    else:


        add_check(

            checks,

            "PASS",

            "aic_account_number",

            (
                "Every filtered AIC transaction belongs "
                "to account 4062522693."
            ),
        )


    # ========================================================
    # MAIN / ZBA / SWEEP COUNTS
    # ========================================================

    main_count = sum(

        transaction.get(
            "aic_section"
        )
        == "main_cash_activity"

        for transaction
        in aic_transactions
    )


    zba_count = sum(

        to_bool(
            transaction.get(
                "is_zba"
            )
        )

        for transaction
        in aic_transactions
    )


    sweep_count = sum(

        to_bool(
            transaction.get(
                "is_sweep"
            )
        )

        for transaction
        in aic_transactions
    )


    zba_sweep_count = sum(

        to_bool(
            transaction.get(
                "is_zba_or_sweep"
            )
        )

        for transaction
        in aic_transactions
    )


    section_expectations = {

        "main_cash_activity":
            (
                main_count,
                expected[
                    "aic_main"
                ],
            ),

        "zba":
            (
                zba_count,
                expected[
                    "aic_zba"
                ],
            ),

        "sweep":
            (
                sweep_count,
                expected[
                    "aic_sweep"
                ],
            ),

        "zba_sweep":
            (
                zba_sweep_count,
                expected[
                    "aic_zba_sweep"
                ],
            ),
    }


    for (
        name,
        (
            actual_value,
            expected_value,
        ),
    ) in section_expectations.items():


        if actual_value == expected_value:


            add_check(

                checks,

                "PASS",

                f"aic_{name}_count",

                (
                    f"{name}: {actual_value}, "
                    "matching direct inspection."
                ),
            )


        else:


            add_check(

                checks,

                "FAIL",

                f"aic_{name}_count",

                (
                    f"Expected {expected_value}, "
                    f"got {actual_value}."
                ),
            )


    # ========================================================
    # EXACT ZBA / SWEEP SOURCE TYPES
    # ========================================================

    incorrect_zba_sweep_types = []


    for transaction in aic_transactions:


        tagged = to_bool(

            transaction.get(
                "is_zba_or_sweep"
            )
        )


        transaction_type = (
            transaction.get(
                "transaction_type"
            )
        )


        if (

            tagged

            and transaction_type
            not in ZBA_SWEEP_TYPES
        ):

            incorrect_zba_sweep_types.append(
                transaction
            )


    if incorrect_zba_sweep_types:


        add_check(

            checks,

            "FAIL",

            "zba_sweep_source_types",

            (
                f"{len(incorrect_zba_sweep_types)} tagged "
                "rows use an unexpected Tran Desc."
            ),
        )


    else:


        add_check(

            checks,

            "PASS",

            "zba_sweep_source_types",

            (
                "Every ZBA/sweep tag is supported by one "
                "of the four directly observed Tran Desc "
                "values."
            ),
        )


    # ========================================================
    # DEBIT / CREDIT STRUCTURE
    # ========================================================

    invalid_debit_credit_rows = []


    for transaction in full_transactions:


        debit = to_float(

            transaction.get(
                "debit_amount"
            )
        )


        credit = to_float(

            transaction.get(
                "credit_amount"
            )
        )


        debit_nonzero = (

            debit is not None

            and abs(
                debit
            ) > TOLERANCE
        )


        credit_nonzero = (

            credit is not None

            and abs(
                credit
            ) > TOLERANCE
        )


        # XOR:
        #
        # exactly one side must be nonzero.
        if debit_nonzero == credit_nonzero:


            invalid_debit_credit_rows.append(
                transaction
            )


    if invalid_debit_credit_rows:


        add_check(

            checks,

            "FAIL",

            "debit_credit_structure",

            (
                f"{len(invalid_debit_credit_rows)} "
                "transaction(s) do not contain exactly "
                "one nonzero Debit/Credit."
            ),
        )


    else:


        add_check(

            checks,

            "PASS",

            "debit_credit_structure",

            (
                "Every source transaction contains exactly "
                "one nonzero Debit/Credit."
            ),
        )


    # ========================================================
    # INDEPENDENT NET-AMOUNT RECOMPUTATION
    # ========================================================
    #
    # This is one of the most important checks.
    #
    # We deliberately recompute:
    #
    #       Debit - Credit
    #
    # rather than relying on source column G.
    # ========================================================

    net_amount_failures = []


    for transaction in full_transactions:


        debit = (

            to_float(
                transaction.get(
                    "debit_amount"
                )
            )

            or 0.0
        )


        credit = (

            to_float(
                transaction.get(
                    "credit_amount"
                )
            )

            or 0.0
        )


        expected_net = (

            debit

            - credit
        )


        actual_net = to_float(

            transaction.get(
                "bank_net_amount"
            )
        )


        if (

            actual_net is None

            or abs(
                actual_net
                - expected_net
            ) > TOLERANCE
        ):


            net_amount_failures.append(

                {
                    "transaction_id":
                        transaction.get(
                            "transaction_id"
                        ),

                    "source_row":
                        transaction.get(
                            "source_row"
                        ),

                    "expected_net":
                        expected_net,

                    "actual_net":
                        actual_net,
                }
            )


    if net_amount_failures:


        add_check(

            checks,

            "FAIL",

            "derived_bank_net_amount",

            (
                f"{len(net_amount_failures)} transaction(s) "
                "have an incorrect derived net amount."
            ),
        )


    else:


        add_check(

            checks,

            "PASS",

            "derived_bank_net_amount",

            (
                "Every bank_net_amount independently equals "
                "Debit - Credit."
            ),
        )


    # ========================================================
    # TRANSACTION ID UNIQUENESS
    # ========================================================

    transaction_ids = [

        transaction.get(
            "transaction_id"
        )

        for transaction
        in full_transactions
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
                "Duplicate transaction IDs were produced."
            ),
        )


    else:


        add_check(

            checks,

            "PASS",

            "transaction_id_uniqueness",

            (
                "Every Previous Day transaction has a "
                "unique source-based transaction ID."
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
        in full_transactions
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
                "More than one normalized transaction was "
                "created from the same source row."
            ),
        )


    else:


        add_check(

            checks,

            "PASS",

            "source_row_uniqueness",

            (
                "Each normalized transaction maps to one "
                "unique source row."
            ),
        )


    # ========================================================
    # VISIBLE DUPLICATE PRESERVATION
    # ========================================================

    actual_visible_duplicates = validation.get(

        "aic_visible_duplicate_extra_row_count",

        0,
    )


    if (

        actual_visible_duplicates
        == expected[
            "visible_duplicate_extra_rows"
        ]
    ):


        add_check(

            checks,

            "PASS",

            "visible_duplicate_preservation",

            (
                f"{actual_visible_duplicates} identical-visible "
                "extra row(s), matching actual source data "
                "and preserved without deduplication."
            ),
        )


    else:


        add_check(

            checks,

            "FAIL",

            "visible_duplicate_preservation",

            (
                f"Expected "
                f"{expected['visible_duplicate_extra_rows']} "
                f"identical-visible extra row(s), "
                f"got {actual_visible_duplicates}."
            ),
        )


    # ========================================================
    # AIC CLIENT ANALYSIS FEE
    # ========================================================

    actual_fee_count = validation.get(

        "aic_client_analysis_fee_count",

        0,
    )


    if (

        actual_fee_count
        == expected[
            "aic_analysis_fees"
        ]
    ):


        add_check(

            checks,

            "PASS",

            "aic_client_analysis_fee_count",

            (
                "No AIC Disbursement client-analysis fee "
                "was found, matching actual Jan–Jul data."
            ),
        )


    else:


        add_check(

            checks,

            "FAIL",

            "aic_client_analysis_fee_count",

            (
                f"Expected "
                f"{expected['aic_analysis_fees']}, "
                f"got {actual_fee_count}."
            ),
        )


    # ========================================================
    # STRUCTURAL WARNINGS
    # ========================================================

    structural_warnings = validation.get(

        "structural_warning_count",

        0,
    )


    if structural_warnings == 0:


        add_check(

            checks,

            "PASS",

            "structural_warnings",

            "No structural warnings were generated.",
        )


    else:


        add_check(

            checks,

            "FAIL",

            "structural_warnings",

            (
                f"{structural_warnings} structural "
                "warning(s) were generated."
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

        "full_report_transaction_count":
            len(
                full_transactions
            ),

        "aic_transaction_count":
            len(
                aic_transactions
            ),

        "aic_main_cash_activity_count":
            main_count,

        "aic_zba_sweep_count":
            zba_sweep_count,

        "checks":
            checks,
    }


# ============================================================
# MAIN QA PROGRAM
# ============================================================

def main():

    print(
        "ASCOT WF PREVIOUS DAY SANITIZER — STRUCTURAL QA"
    )


    # ========================================================
    # MANIFEST MUST EXIST
    # ========================================================

    if not MANIFEST_PATH.exists():


        raise FileNotFoundError(

            "Could not find:\n"
            "data/processed/"
            "wf_previous_day_processing_manifest.json\n\n"
            "Run sanitize_previous_day.py first."
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

            "All 7 expected Previous Day files were sanitized.",
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
                "Previous Day periods are in correct "
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
    # OVERALL STATUS
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
    # WRITE QA REPORT
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

            f"Full report: "
            f"{month['full_report_transaction_count']} | "
            f"AIC: "
            f"{month['aic_transaction_count']} | "
            f"Main: "
            f"{month['aic_main_cash_activity_count']} | "
            f"ZBA/Sweep: "
            f"{month['aic_zba_sweep_count']}"
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
        "wf_previous_day_qa_report.json"
    )


    if overall_status == "PASS":


        print(
            "\n✓ Previous Day sanitizer is structurally "
            "ready for cross-source reconciliation."
        )


    elif overall_status == "PASS_WITH_WARNINGS":


        print(
            "\n✓ No structural failures, but warnings "
            "should be reviewed first."
        )


    else:


        print(
            "\n✗ Previous Day QA failed. "
            "Do not proceed to WF reconciliation yet."
        )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
    