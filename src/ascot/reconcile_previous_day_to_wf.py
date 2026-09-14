# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# PRODUCTION CONTROL:
# reconcile_previous_day_to_wf()
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# This is the first genuine reconciliation automation
# component in the Ascot prototype.
#
# It answers:
#
#     Is every AIC bank transaction in the Previous Day
#     population represented in AIC WF, and does AIC WF
#     contain any unsupported additional bank transaction?
#
#
# EMPIRICAL BASIS
# ------------------------------------------------------------
#
# Direct inspection of January-July 2026 showed:
#
#   Previous Day AIC rows = 1,514
#   AIC WF rows           = 1,514
#
# All 1,514 transactions reconcile under:
#
#   accounting period
#   + date
#   + debit/credit direction
#   + amount
#   + Tran Desc
#   + normalized reference
#   + Descriptive Text 1
#
#
# IMPORTANT:
#
# Raw reference formatting is NOT reliable.
#
# Only 774 / 1,514 raw references were literally equal.
#
# After normalizing leading-zero and numeric/text differences:
#
#   1,514 / 1,514 matched.
#
#
# DUPLICATE HANDLING
# ------------------------------------------------------------
#
# One July signature occurs twice on both sides.
#
# Therefore we must NOT arbitrarily claim:
#
#     PD row X = WF row Y
#
# when two records are economically indistinguishable.
#
# Instead:
#
#     2 Previous Day transactions
#     =
#     2 AIC WF transactions
#
# becomes:
#
#     DUPLICATE_GROUP_MATCH
#
#
# EXCEPTION TYPES
# ------------------------------------------------------------
#
#   MISSING_IN_WF
#
#       Present in Previous Day but absent from AIC WF.
#
#
#   UNSUPPORTED_IN_WF
#
#       Present in AIC WF but absent from Previous Day.
#
#
#   COUNT_MISMATCH
#
#       Same transaction signature exists on both sides,
#       but occurrence counts differ.
#
#
#   SECTION_MISMATCH
#
#       Bank identity reconciles, but AIC WF Main/ZBA-Sweep
#       section differs from the deterministic Previous Day
#       section.
#
#
# OUTPUT
# ------------------------------------------------------------
#
# data/processed/reconciliation/previous_day_to_wf/
#
#   YYYY-MM/
#       reconciliation_groups.csv
#       reconciliation_exceptions.csv
#       reconciliation_summary.json
#
#   all_months_reconciliation_groups.csv
#   all_months_reconciliation_exceptions.csv
#   all_months_summary.json
#
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import csv
import hashlib
import json
import re

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


# ============================================================
# INPUT PATHS
# ============================================================

PROCESSED_FOLDER = Path(
    "data/processed"
)


PREVIOUS_DAY_PATH = (
    PROCESSED_FOLDER
    / "aic_previous_day_all_months_transactions.csv"
)


AIC_WF_PATH = (
    PROCESSED_FOLDER
    / "aic_wf_all_months_transactions.csv"
)


# ============================================================
# OUTPUT PATH
# ============================================================

OUTPUT_ROOT = (
    PROCESSED_FOLDER
    / "reconciliation"
    / "previous_day_to_wf"
)


OUTPUT_ROOT.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# ACCOUNTING CONSTANTS
# ============================================================

AIC_DISBURSEMENT_ACCOUNT = (
    "4062522693"
)


CENT = Decimal(
    "0.01"
)


ZERO = Decimal(
    "0.00"
)


# ============================================================
# READ CSV
# ============================================================

def read_csv(path):
    """
    Read a CSV file into a list of dictionaries.
    """

    if not path.exists():

        raise FileNotFoundError(
            f"Required input does not exist: {path}"
        )


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
# WRITE CSV
# ============================================================

def write_csv(
    path,
    records,
):
    """
    Write dictionaries to CSV.

    Empty output still creates an empty file.
    """

    if not records:

        with path.open(
            "w",
            encoding="utf-8-sig",
        ):
            pass

        return


    fieldnames = []


    for record in records:

        for key in record.keys():

            if key not in fieldnames:

                fieldnames.append(
                    key
                )


    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        writer.writerows(
            records
        )


# ============================================================
# TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Normalize ordinary comparison text.

    We remove irrelevant spacing differences and compare
    case-insensitively.
    """

    if value is None:

        return ""


    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    ).upper()


# ============================================================
# DATE NORMALIZATION
# ============================================================

def normalize_date(value):
    """
    Normalize dates to YYYY-MM-DD.
    """

    text = str(
        value or ""
    ).strip()


    if not text:

        return None


    text = text.replace(
        "/",
        "-",
    )


    return text[:10]


# ============================================================
# MONEY NORMALIZATION
# ============================================================

def money_decimal(value):
    """
    Convert a CSV monetary value to Decimal with two decimals.

    Blank = 0.00.
    """

    if value in {
        None,
        "",
    }:

        return ZERO


    try:

        result = Decimal(
            str(value)
        )


    except InvalidOperation as error:

        raise ValueError(
            f"Invalid monetary value: {value}"
        ) from error


    return result.quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def money_text(value):
    """
    Convert Decimal to stable two-decimal text.
    """

    return format(
        value.quantize(
            CENT
        ),
        ".2f",
    )


# ============================================================
# IDENTIFIER NORMALIZATION
# ============================================================

def normalize_identifier_text(value):
    """
    Preserve identifier meaning while removing Excel's
    trailing '.0' numeric representation.
    """

    if value is None:

        return None


    text = str(
        value
    ).strip()


    if not text:

        return None


    if re.fullmatch(
        r"\d+\.0",
        text,
    ):

        text = text[:-2]


    return text


def identifier_match_key(value):
    """
    Create the deterministic reference matching key.

    Numeric identifiers have leading zeros removed.

    Example:

        03330005430
        3330005430

    both become:

        3330005430

    All-zero values are treated as unavailable placeholders.
    """

    text = normalize_identifier_text(
        value
    )


    if text is None:

        return None


    compact = re.sub(
        r"\s+",
        "",
        text,
    )


    if re.fullmatch(
        r"\d+",
        compact,
    ):

        if set(
            compact
        ) == {
            "0"
        }:

            return None


        stripped = compact.lstrip(
            "0"
        )


        return (
            stripped
            if stripped
            else None
        )


    return normalize_text(
        text
    )


# ============================================================
# DERIVE DEBIT/CREDIT MOVEMENT
# ============================================================

def derive_bank_movement(row):
    """
    Derive direction and absolute amount from source
    Debit/Credit fields.

    We deliberately recompute this rather than trusting
    derived columns produced earlier.
    """

    debit = money_decimal(
        row.get(
            "debit_amount"
        )
    )


    credit = money_decimal(
        row.get(
            "credit_amount"
        )
    )


    has_debit = (
        debit != ZERO
    )


    has_credit = (
        credit != ZERO
    )


    # A valid bank transaction should have exactly one side.
    if has_debit == has_credit:

        raise ValueError(

            "Transaction does not contain exactly one "
            f"nonzero Debit/Credit: {row}"
        )


    if has_debit:

        return (
            "DEBIT",
            abs(
                debit
            ),
        )


    return (
        "CREDIT",
        abs(
            credit
        ),
    )


# ============================================================
# BUILD STANDARDIZED TRANSACTION RECORD
# ============================================================

def standardize_transaction(
    row,
    source_type,
):
    """
    Convert Previous Day and AIC WF records into the same
    comparison structure.
    """

    period = row.get(
        "accounting_period"
    )


    source_row = row.get(
        "source_row"
    )


    date = normalize_date(
        row.get(
            "as_of_date"
        )
    )


    (
        direction,
        amount,
    ) = derive_bank_movement(
        row
    )


    transaction_description = normalize_text(

        row.get(
            "transaction_description"
        )
    )


    descriptive_text = normalize_text(

        row.get(
            "descriptive_text_1"
        )
    )


    # --------------------------------------------------------
    # REFERENCE FIELD DIFFERS BY SOURCE
    # --------------------------------------------------------

    if source_type == "PREVIOUS_DAY":

        reference_raw = (

            row.get(
                "customer_ref_text"
            )

            or row.get(
                "customer_ref_raw"
            )
        )


        section = row.get(
            "aic_section"
        )


        transaction_id = (

            row.get(
                "transaction_id"
            )

            or
            f"PD-{period}-R{source_row}"
        )


    elif source_type == "AIC_WF":

        reference_raw = row.get(
            "check_number"
        )


        section = row.get(
            "section"
        )


        transaction_id = (
            f"WF-{period}-R{source_row}"
        )


    else:

        raise ValueError(
            f"Unknown source_type: {source_type}"
        )


    reference_key = identifier_match_key(
        reference_raw
    )


    account_number = normalize_identifier_text(

        row.get(
            "account_number"
        )
    )


    # --------------------------------------------------------
    # CANONICAL SIGNATURE
    # --------------------------------------------------------
    #
    # This exact signature was empirically validated against
    # all 1,514 Jan-Jul transactions.
    # --------------------------------------------------------

    signature_fields = {

        "accounting_period":
            period,

        "date":
            date,

        "direction":
            direction,

        "amount":
            money_text(
                amount
            ),

        "transaction_description":
            transaction_description,

        "reference_key":
            reference_key,

        "descriptive_text":
            descriptive_text,
    }


    signature_tuple = (

        signature_fields[
            "accounting_period"
        ],

        signature_fields[
            "date"
        ],

        signature_fields[
            "direction"
        ],

        signature_fields[
            "amount"
        ],

        signature_fields[
            "transaction_description"
        ],

        signature_fields[
            "reference_key"
        ],

        signature_fields[
            "descriptive_text"
        ],
    )


    # --------------------------------------------------------
    # HUMAN-READABLE STABLE GROUP ID
    # --------------------------------------------------------

    canonical_json = json.dumps(

        signature_fields,

        sort_keys=True,

        ensure_ascii=False,
    )


    signature_hash = hashlib.sha256(

        canonical_json.encode(
            "utf-8"
        )

    ).hexdigest()[:16]


    return {

        "source_type":
            source_type,

        "transaction_id":
            transaction_id,

        "source_workbook":
            row.get(
                "source_workbook"
            ),

        "source_row":
            source_row,

        "accounting_period":
            period,

        "account_number":
            account_number,

        "date":
            date,

        "direction":
            direction,

        "amount_decimal":
            amount,

        "amount":
            money_text(
                amount
            ),

        "transaction_description":
            transaction_description,

        "reference_raw":
            normalize_identifier_text(
                reference_raw
            ),

        "reference_key":
            reference_key,

        "descriptive_text":
            descriptive_text,

        "section":
            section,

        "signature_tuple":
            signature_tuple,

        "signature_hash":
            signature_hash,
    }


# ============================================================
# SUM SOURCE MONEY
# ============================================================

def calculate_source_totals(
    rows,
):
    """
    Independently calculate debit, credit, and net totals.

    Net definition:

        debit - credit
    """

    debit_total = ZERO

    credit_total = ZERO


    for row in rows:

        debit_total += money_decimal(

            row.get(
                "debit_amount"
            )
        )


        credit_total += money_decimal(

            row.get(
                "credit_amount"
            )
        )


    net_total = (

        debit_total

        - credit_total
    )


    return {

        "debit_total":
            debit_total,

        "credit_total":
            credit_total,

        "net_total":
            net_total,
    }


# ============================================================
# JOIN VALUES FOR CSV OUTPUT
# ============================================================

def join_values(values):
    """
    Join source IDs/rows without pretending duplicate records
    have a specific one-to-one relationship.
    """

    return "|".join(

        str(value)

        for value
        in values
    )


# ============================================================
# CORE RECONCILIATION FUNCTION
# ============================================================

def reconcile_previous_day_to_wf(
    previous_day_rows,
    wf_rows,
    accounting_period,
):
    """
    Deterministically reconcile one accounting period.

    Returns:

        summary
        reconciliation_groups
        exceptions
    """

    # ========================================================
    # STANDARDIZE BOTH POPULATIONS
    # ========================================================

    previous_records = [

        standardize_transaction(
            row,
            "PREVIOUS_DAY",
        )

        for row
        in previous_day_rows

        if row.get(
            "accounting_period"
        ) == accounting_period
    ]


    wf_records = [

        standardize_transaction(
            row,
            "AIC_WF",
        )

        for row
        in wf_rows

        if row.get(
            "accounting_period"
        ) == accounting_period
    ]


    # ========================================================
    # BASIC ACCOUNT VALIDATION
    # ========================================================

    incorrect_previous_accounts = [

        record

        for record
        in previous_records

        if (
            record[
                "account_number"
            ]
            != AIC_DISBURSEMENT_ACCOUNT
        )
    ]


    incorrect_wf_accounts = [

        record

        for record
        in wf_records

        if (
            record[
                "account_number"
            ]
            != AIC_DISBURSEMENT_ACCOUNT
        )
    ]


    if incorrect_previous_accounts:

        raise ValueError(

            f"{accounting_period}: Previous Day input "
            "contains non-AIC-Disbursement transactions."
        )


    if incorrect_wf_accounts:

        raise ValueError(

            f"{accounting_period}: AIC WF input contains "
            "unexpected account numbers."
        )


    # ========================================================
    # GROUP BY FULL NORMALIZED SIGNATURE
    # ========================================================

    previous_groups = defaultdict(
        list
    )


    wf_groups = defaultdict(
        list
    )


    for record in previous_records:

        previous_groups[
            record[
                "signature_tuple"
            ]
        ].append(
            record
        )


    for record in wf_records:

        wf_groups[
            record[
                "signature_tuple"
            ]
        ].append(
            record
        )


    all_signatures = sorted(

        set(
            previous_groups
        )

        | set(
            wf_groups
        ),

        key=lambda value: str(
            value
        ),
    )


    reconciliation_groups = []

    exceptions = []


    # ========================================================
    # PROCESS EACH TRANSACTION SIGNATURE
    # ========================================================

    for group_sequence, signature in enumerate(

        all_signatures,

        start=1,
    ):


        previous_group = previous_groups.get(
            signature,
            [],
        )


        wf_group = wf_groups.get(
            signature,
            [],
        )


        previous_count = len(
            previous_group
        )


        wf_count = len(
            wf_group
        )


        # At least one side exists, so use it to obtain the
        # signature metadata.
        representative = (

            previous_group[0]

            if previous_group

            else wf_group[0]
        )


        group_id = (

            f"PDWF-{accounting_period}-"
            f"{representative['signature_hash']}"
        )


        # ====================================================
        # DETERMINE GROUP STATUS
        # ====================================================

        if (
            previous_count == 1

            and wf_count == 1
        ):

            status = (
                "UNIQUE_MATCH"
            )


        elif (

            previous_count > 1

            and previous_count == wf_count
        ):

            status = (
                "DUPLICATE_GROUP_MATCH"
            )


        elif (

            previous_count > 0

            and wf_count == 0
        ):

            status = (
                "MISSING_IN_WF"
            )


        elif (

            previous_count == 0

            and wf_count > 0
        ):

            status = (
                "UNSUPPORTED_IN_WF"
            )


        else:

            status = (
                "COUNT_MISMATCH"
            )


        # ====================================================
        # SECTION COMPARISON
        # ====================================================

        previous_sections = sorted(

            {

                record[
                    "section"
                ]

                for record
                in previous_group

                if record[
                    "section"
                ]
            }
        )


        wf_sections = sorted(

            {

                record[
                    "section"
                ]

                for record
                in wf_group

                if record[
                    "section"
                ]
            }
        )


        section_match = (

            bool(
                previous_group
            )

            and bool(
                wf_group
            )

            and previous_sections
            == wf_sections
        )


        # ====================================================
        # GROUP RECORD
        # ====================================================

        group_record = {

            "group_id":
                group_id,

            "accounting_period":
                accounting_period,

            "status":
                status,

            "signature_hash":
                representative[
                    "signature_hash"
                ],

            "date":
                representative[
                    "date"
                ],

            "direction":
                representative[
                    "direction"
                ],

            "amount":
                representative[
                    "amount"
                ],

            "transaction_description":
                representative[
                    "transaction_description"
                ],

            "reference_key":
                representative[
                    "reference_key"
                ],

            "descriptive_text":
                representative[
                    "descriptive_text"
                ],

            "previous_day_count":
                previous_count,

            "aic_wf_count":
                wf_count,

            "previous_day_transaction_ids":
                join_values(

                    [
                        record[
                            "transaction_id"
                        ]

                        for record
                        in previous_group
                    ]
                ),

            "previous_day_source_rows":
                join_values(

                    [
                        record[
                            "source_row"
                        ]

                        for record
                        in previous_group
                    ]
                ),

            "aic_wf_transaction_ids":
                join_values(

                    [
                        record[
                            "transaction_id"
                        ]

                        for record
                        in wf_group
                    ]
                ),

            "aic_wf_source_rows":
                join_values(

                    [
                        record[
                            "source_row"
                        ]

                        for record
                        in wf_group
                    ]
                ),

            "previous_day_sections":
                "|".join(
                    previous_sections
                ),

            "aic_wf_sections":
                "|".join(
                    wf_sections
                ),

            "section_match":
                section_match,

            # Only populate direct IDs when identity is
            # genuinely unique on both sides.
            "unique_previous_day_transaction_id":
                (
                    previous_group[0][
                        "transaction_id"
                    ]

                    if status
                    == "UNIQUE_MATCH"

                    else None
                ),

            "unique_aic_wf_transaction_id":
                (
                    wf_group[0][
                        "transaction_id"
                    ]

                    if status
                    == "UNIQUE_MATCH"

                    else None
                ),
        }


        reconciliation_groups.append(
            group_record
        )


        # ====================================================
        # EXPLICIT POPULATION EXCEPTIONS
        # ====================================================

        if status in {

            "MISSING_IN_WF",

            "UNSUPPORTED_IN_WF",

            "COUNT_MISMATCH",
        }:


            exceptions.append(

                {
                    "exception_id":
                        (
                            f"{group_id}-"
                            f"{status}"
                        ),

                    "accounting_period":
                        accounting_period,

                    "exception_type":
                        status,

                    "group_id":
                        group_id,

                    "date":
                        representative[
                            "date"
                        ],

                    "direction":
                        representative[
                            "direction"
                        ],

                    "amount":
                        representative[
                            "amount"
                        ],

                    "transaction_description":
                        representative[
                            "transaction_description"
                        ],

                    "reference_key":
                        representative[
                            "reference_key"
                        ],

                    "descriptive_text":
                        representative[
                            "descriptive_text"
                        ],

                    "previous_day_count":
                        previous_count,

                    "aic_wf_count":
                        wf_count,

                    "previous_day_source_rows":
                        group_record[
                            "previous_day_source_rows"
                        ],

                    "aic_wf_source_rows":
                        group_record[
                            "aic_wf_source_rows"
                        ],

                    "resolution_status":
                        "OPEN",
                }
            )


        # ====================================================
        # SECTION EXCEPTION
        # ====================================================

        if (

            previous_group

            and wf_group

            and not section_match
        ):


            exceptions.append(

                {
                    "exception_id":
                        (
                            f"{group_id}-"
                            "SECTION_MISMATCH"
                        ),

                    "accounting_period":
                        accounting_period,

                    "exception_type":
                        "SECTION_MISMATCH",

                    "group_id":
                        group_id,

                    "date":
                        representative[
                            "date"
                        ],

                    "direction":
                        representative[
                            "direction"
                        ],

                    "amount":
                        representative[
                            "amount"
                        ],

                    "transaction_description":
                        representative[
                            "transaction_description"
                        ],

                    "reference_key":
                        representative[
                            "reference_key"
                        ],

                    "descriptive_text":
                        representative[
                            "descriptive_text"
                        ],

                    "previous_day_sections":
                        group_record[
                            "previous_day_sections"
                        ],

                    "aic_wf_sections":
                        group_record[
                            "aic_wf_sections"
                        ],

                    "previous_day_source_rows":
                        group_record[
                            "previous_day_source_rows"
                        ],

                    "aic_wf_source_rows":
                        group_record[
                            "aic_wf_source_rows"
                        ],

                    "resolution_status":
                        "OPEN",
                }
            )


    # ========================================================
    # INDEPENDENT MONEY TOTALS
    # ========================================================

    previous_totals = calculate_source_totals(

        [
            row

            for row
            in previous_day_rows

            if row.get(
                "accounting_period"
            ) == accounting_period
        ]
    )


    wf_totals = calculate_source_totals(

        [
            row

            for row
            in wf_rows

            if row.get(
                "accounting_period"
            ) == accounting_period
        ]
    )


    debit_variance = (

        wf_totals[
            "debit_total"
        ]

        - previous_totals[
            "debit_total"
        ]
    )


    credit_variance = (

        wf_totals[
            "credit_total"
        ]

        - previous_totals[
            "credit_total"
        ]
    )


    net_variance = (

        wf_totals[
            "net_total"
        ]

        - previous_totals[
            "net_total"
        ]
    )


    # ========================================================
    # MATCH COUNTS
    # ========================================================

    unique_match_groups = [

        group

        for group
        in reconciliation_groups

        if group[
            "status"
        ] == "UNIQUE_MATCH"
    ]


    duplicate_match_groups = [

        group

        for group
        in reconciliation_groups

        if group[
            "status"
        ] == "DUPLICATE_GROUP_MATCH"
    ]


    unique_match_transactions = len(
        unique_match_groups
    )


    duplicate_group_transactions = sum(

        group[
            "previous_day_count"
        ]

        for group
        in duplicate_match_groups
    )


    missing_in_wf_transactions = sum(

        max(

            group[
                "previous_day_count"
            ]

            - group[
                "aic_wf_count"
            ],

            0,
        )

        for group
        in reconciliation_groups
    )


    unsupported_in_wf_transactions = sum(

        max(

            group[
                "aic_wf_count"
            ]

            - group[
                "previous_day_count"
            ],

            0,
        )

        for group
        in reconciliation_groups
    )


    section_mismatch_count = sum(

        1

        for group
        in reconciliation_groups

        if (

            group[
                "previous_day_count"
            ] > 0

            and group[
                "aic_wf_count"
            ] > 0

            and not group[
                "section_match"
            ]
        )
    )


    # ========================================================
    # PASS / FAIL CONTROL
    # ========================================================

    population_reconciled = (

        len(
            exceptions
        ) == 0

        and len(
            previous_records
        )
        == len(
            wf_records
        )

        and debit_variance
        == ZERO

        and credit_variance
        == ZERO

        and net_variance
        == ZERO
    )


    control_status = (

        "PASS"

        if population_reconciled

        else "FAIL"
    )


    # ========================================================
    # SUMMARY
    # ========================================================

    summary = {

        "control_name":
            "reconcile_previous_day_to_wf",

        "accounting_period":
            accounting_period,

        "control_status":
            control_status,

        "population_reconciled":
            population_reconciled,

        # Population counts.
        "previous_day_transaction_count":
            len(
                previous_records
            ),

        "aic_wf_transaction_count":
            len(
                wf_records
            ),

        "transaction_count_variance":
            (
                len(
                    wf_records
                )

                - len(
                    previous_records
                )
            ),

        # Matching structure.
        "unique_match_group_count":
            len(
                unique_match_groups
            ),

        "unique_match_transaction_count":
            unique_match_transactions,

        "duplicate_match_group_count":
            len(
                duplicate_match_groups
            ),

        "duplicate_group_transaction_count":
            duplicate_group_transactions,

        "missing_in_wf_transaction_count":
            missing_in_wf_transactions,

        "unsupported_in_wf_transaction_count":
            unsupported_in_wf_transactions,

        "section_mismatch_group_count":
            section_mismatch_count,

        "exception_count":
            len(
                exceptions
            ),

        # Previous Day totals.
        "previous_day_debit_total":
            money_text(
                previous_totals[
                    "debit_total"
                ]
            ),

        "previous_day_credit_total":
            money_text(
                previous_totals[
                    "credit_total"
                ]
            ),

        "previous_day_net_total":
            money_text(
                previous_totals[
                    "net_total"
                ]
            ),

        # AIC WF totals.
        "aic_wf_debit_total":
            money_text(
                wf_totals[
                    "debit_total"
                ]
            ),

        "aic_wf_credit_total":
            money_text(
                wf_totals[
                    "credit_total"
                ]
            ),

        "aic_wf_net_total":
            money_text(
                wf_totals[
                    "net_total"
                ]
            ),

        # Variances.
        "debit_variance_wf_minus_previous_day":
            money_text(
                debit_variance
            ),

        "credit_variance_wf_minus_previous_day":
            money_text(
                credit_variance
            ),

        "net_variance_wf_minus_previous_day":
            money_text(
                net_variance
            ),
    }


    return (

        summary,

        reconciliation_groups,

        exceptions,
    )


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print(
        "ASCOT CONTROL: "
        "reconcile_previous_day_to_wf()"
    )


    # ========================================================
    # LOAD VALIDATED SANITIZED INPUTS
    # ========================================================

    previous_day_rows = read_csv(
        PREVIOUS_DAY_PATH
    )


    wf_rows = read_csv(
        AIC_WF_PATH
    )


    # ========================================================
    # DETERMINE ACCOUNTING PERIODS
    # ========================================================

    previous_periods = {

        row.get(
            "accounting_period"
        )

        for row
        in previous_day_rows
    }


    wf_periods = {

        row.get(
            "accounting_period"
        )

        for row
        in wf_rows
    }


    periods = sorted(

        previous_periods

        | wf_periods
    )


    print(
        f"\nAccounting periods: "
        f"{', '.join(periods)}"
    )


    # ========================================================
    # CONSOLIDATED RESULTS
    # ========================================================

    all_summaries = []

    all_groups = []

    all_exceptions = []


    # ========================================================
    # RUN CONTROL MONTH BY MONTH
    # ========================================================

    for period in periods:


        (
            summary,
            groups,
            exceptions,
        ) = reconcile_previous_day_to_wf(

            previous_day_rows,

            wf_rows,

            period,
        )


        all_summaries.append(
            summary
        )


        all_groups.extend(
            groups
        )


        all_exceptions.extend(
            exceptions
        )


        # ====================================================
        # WRITE MONTH-SPECIFIC OUTPUT
        # ====================================================

        period_folder = (

            OUTPUT_ROOT

            / period
        )


        period_folder.mkdir(

            parents=True,

            exist_ok=True,
        )


        write_csv(

            period_folder
            / "reconciliation_groups.csv",

            groups,
        )


        write_csv(

            period_folder
            / "reconciliation_exceptions.csv",

            exceptions,
        )


        with (
            period_folder
            / "reconciliation_summary.json"
        ).open(

            "w",

            encoding="utf-8",

        ) as file:


            json.dump(

                summary,

                file,

                indent=2,

                ensure_ascii=False,
            )


        # ====================================================
        # TERMINAL SUMMARY
        # ====================================================

        print(
            "\n----------------------------------------"
        )


        print(
            f"{period} | "
            f"{summary['control_status']}"
        )


        print(
            "Previous Day / WF: "
            f"{summary['previous_day_transaction_count']} / "
            f"{summary['aic_wf_transaction_count']}"
        )


        print(
            "Unique matches: "
            f"{summary['unique_match_transaction_count']}"
        )


        print(
            "Duplicate groups: "
            f"{summary['duplicate_match_group_count']} "
            f"("
            f"{summary['duplicate_group_transaction_count']} "
            "transactions)"
        )


        print(
            "Missing in WF: "
            f"{summary['missing_in_wf_transaction_count']}"
        )


        print(
            "Unsupported in WF: "
            f"{summary['unsupported_in_wf_transaction_count']}"
        )


        print(
            "Section mismatches: "
            f"{summary['section_mismatch_group_count']}"
        )


        print(
            "Net variance: "
            f"{summary['net_variance_wf_minus_previous_day']}"
        )


        print(
            "Exceptions: "
            f"{summary['exception_count']}"
        )


    # ========================================================
    # WRITE CONSOLIDATED GROUPS
    # ========================================================

    write_csv(

        OUTPUT_ROOT
        / "all_months_reconciliation_groups.csv",

        all_groups,
    )


    # ========================================================
    # WRITE CONSOLIDATED EXCEPTIONS
    # ========================================================

    write_csv(

        OUTPUT_ROOT
        / "all_months_reconciliation_exceptions.csv",

        all_exceptions,
    )


    # ========================================================
    # OVERALL SUMMARY
    # ========================================================

    overall_status = (

        "PASS"

        if all(

            summary[
                "control_status"
            ] == "PASS"

            for summary
            in all_summaries
        )

        else "FAIL"
    )


    overall_summary = {

        "control_name":
            "reconcile_previous_day_to_wf",

        "overall_status":
            overall_status,

        "period_count":
            len(
                all_summaries
            ),

        "periods_passed":
            sum(

                summary[
                    "control_status"
                ] == "PASS"

                for summary
                in all_summaries
            ),

        "periods_failed":
            sum(

                summary[
                    "control_status"
                ] == "FAIL"

                for summary
                in all_summaries
            ),

        "total_previous_day_transactions":
            sum(

                summary[
                    "previous_day_transaction_count"
                ]

                for summary
                in all_summaries
            ),

        "total_aic_wf_transactions":
            sum(

                summary[
                    "aic_wf_transaction_count"
                ]

                for summary
                in all_summaries
            ),

        "total_unique_match_transactions":
            sum(

                summary[
                    "unique_match_transaction_count"
                ]

                for summary
                in all_summaries
            ),

        "total_duplicate_match_groups":
            sum(

                summary[
                    "duplicate_match_group_count"
                ]

                for summary
                in all_summaries
            ),

        "total_duplicate_group_transactions":
            sum(

                summary[
                    "duplicate_group_transaction_count"
                ]

                for summary
                in all_summaries
            ),

        "total_missing_in_wf_transactions":
            sum(

                summary[
                    "missing_in_wf_transaction_count"
                ]

                for summary
                in all_summaries
            ),

        "total_unsupported_in_wf_transactions":
            sum(

                summary[
                    "unsupported_in_wf_transaction_count"
                ]

                for summary
                in all_summaries
            ),

        "total_section_mismatch_groups":
            sum(

                summary[
                    "section_mismatch_group_count"
                ]

                for summary
                in all_summaries
            ),

        "total_exceptions":
            len(
                all_exceptions
            ),

        "period_summaries":
            all_summaries,
    }


    with (
        OUTPUT_ROOT
        / "all_months_summary.json"
    ).open(

        "w",

        encoding="utf-8",

    ) as file:


        json.dump(

            overall_summary,

            file,

            indent=2,

            ensure_ascii=False,
        )


    # ========================================================
    # FINAL TERMINAL OUTPUT
    # ========================================================

    print(
        "\n========================================"
    )


    print(
        "PREVIOUS DAY -> AIC WF CONTROL COMPLETE"
    )


    print(
        "========================================"
    )


    print(
        f"Overall status: "
        f"{overall_status}"
    )


    print(
        "Previous Day transactions: "
        f"{overall_summary['total_previous_day_transactions']}"
    )


    print(
        "AIC WF transactions: "
        f"{overall_summary['total_aic_wf_transactions']}"
    )


    print(
        "Unique match transactions: "
        f"{overall_summary['total_unique_match_transactions']}"
    )


    print(
        "Duplicate match groups: "
        f"{overall_summary['total_duplicate_match_groups']}"
    )


    print(
        "Transactions inside duplicate groups: "
        f"{overall_summary['total_duplicate_group_transactions']}"
    )


    print(
        "Missing in WF: "
        f"{overall_summary['total_missing_in_wf_transactions']}"
    )


    print(
        "Unsupported in WF: "
        f"{overall_summary['total_unsupported_in_wf_transactions']}"
    )


    print(
        "Section mismatches: "
        f"{overall_summary['total_section_mismatch_groups']}"
    )


    print(
        "Exceptions: "
        f"{overall_summary['total_exceptions']}"
    )


    print(
        "\nOutputs:"
    )


    print(
        "data/processed/reconciliation/"
        "previous_day_to_wf/"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()