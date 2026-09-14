# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
#
# PRODUCTION CONTROL:
#
#     reconcile_current_month_ims_to_wf()
#
# ============================================================
#
# BUSINESS CONTROL
# ------------------------------------------------------------
#
# Ascot's human control is:
#
# AIC WF
#     transactions classified as "IMS"
#     ↓
#     SUM WF control amount
#
# compared with
#
# AIC IMS
#     current accounting-period transactions
#     whose normalized cleared_status indicates an actual
#     clearing date
#     ↓
#     SUM Credit
#     ↓
#     convert cash-disbursement total to positive outflow
#
#
# EMPIRICALLY VALIDATED HUMAN RULE
# ------------------------------------------------------------
#
# INCLUDE IMS statuses:
#
#     cleared
#     multiple_cleared_dates
#
# EXCLUDE:
#
#     outstanding
#     returned
#     same_month_void
#     void_reference
#     blank / other narrative statuses
#
#
# IMPORTANT ARCHITECTURE RULE
# ------------------------------------------------------------
#
# THIS MODULE DOES NOT READ EXCEL COLORS.
#
# Historical Excel color has already been converted upstream
# into explicit category metadata.
#
# Inside the reconciliation core, the WF transaction contains:
#
#     category = "IMS"
#
# The IMS transaction contains:
#
#     cleared_status
#     source_signed_amount
#
#
# OUTPUT
# ------------------------------------------------------------
#
# data/processed/reconciliation/current_month_ims_to_wf/
#
#     monthly_reconciliation.csv
#     exceptions.csv
#     wf_ims_population.csv
#     ims_cleared_population.csv
#     reconciliation_report.json
#
#
# EXPECTED HISTORICAL BACKTEST
# ------------------------------------------------------------
#
# Based on empirical inspection:
#
#     2026-01    FAIL     +300.00
#     2026-02    FAIL    -2220.00
#     2026-03    PASS        0.00
#     2026-04    PASS        0.00
#     2026-05    PASS        0.00
#     2026-06    PASS        0.00
#     2026-07    PASS        0.00
#
# January and February are genuine historical exceptions.
#
# We DO NOT hard-code them as acceptable exceptions.
# The control should detect them.
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import argparse
import csv
import json

from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


# ============================================================
# INPUT PATHS
# ============================================================

PROCESSED_FOLDER = Path(
    "data/processed"
)


WF_CATEGORY_PATH = (
    PROCESSED_FOLDER
    / "aic_wf_legacy_categories_all_months.csv"
)


IMS_TRANSACTION_PATH = (
    PROCESSED_FOLDER
    / "aic_ims_all_months_transactions.csv"
)


# ============================================================
# OUTPUT PATHS
# ============================================================

OUTPUT_FOLDER = (
    PROCESSED_FOLDER
    / "reconciliation"
    / "current_month_ims_to_wf"
)


MONTHLY_OUTPUT_PATH = (
    OUTPUT_FOLDER
    / "monthly_reconciliation.csv"
)


EXCEPTION_OUTPUT_PATH = (
    OUTPUT_FOLDER
    / "exceptions.csv"
)


WF_POPULATION_OUTPUT_PATH = (
    OUTPUT_FOLDER
    / "wf_ims_population.csv"
)


IMS_POPULATION_OUTPUT_PATH = (
    OUTPUT_FOLDER
    / "ims_cleared_population.csv"
)


REPORT_OUTPUT_PATH = (
    OUTPUT_FOLDER
    / "reconciliation_report.json"
)


# ============================================================
# ACCOUNTING CONSTANTS
# ============================================================

CENT = Decimal(
    "0.01"
)


ZERO = Decimal(
    "0.00"
)


# Exact equality is currently required.
#
# We use Decimal rather than float, so ordinary binary
# floating-point error is not a reason to introduce a
# reconciliation tolerance.
DEFAULT_TOLERANCE = Decimal(
    "0.00"
)


# ============================================================
# IMS NORMALIZED STATUSES INCLUDED IN THIS CONTROL
# ============================================================
#
# These statuses came from the normalized IMS sanitizer.
#
# A row with multiple dates is still one IMS transaction and
# therefore contributes its Credit only ONCE.
# ============================================================

CLEARED_IMS_STATUSES = {

    "cleared",

    "multiple_cleared_dates",
}


# ============================================================
# BASIC HELPERS
# ============================================================

def normalize_text(value):
    """
    Convert a value to trimmed text.

    None becomes "".
    """

    if value is None:

        return ""


    return str(
        value
    ).strip()


def normalize_lower(value):
    """
    Normalized lower-case text for machine comparisons.
    """

    return normalize_text(
        value
    ).lower()


def normalize_upper(value):
    """
    Normalized upper-case text for category comparisons.
    """

    return normalize_text(
        value
    ).upper()


# ============================================================
# DECIMAL HELPERS
# ============================================================

def to_decimal(
    value,
    *,
    allow_blank=True,
):
    """
    Convert a CSV value to Decimal.

    Financial calculations must not use float.

    When allow_blank=True:
        blank -> None

    Otherwise:
        blank raises ValueError.
    """

    text = normalize_text(
        value
    )


    if not text:

        if allow_blank:

            return None


        raise ValueError(
            "Expected numeric value but found blank."
        )


    # Allow ordinary accounting formatting if it ever appears
    # in a normalized CSV.
    text = (
        text
        .replace(
            ",",
            "",
        )
        .replace(
            "$",
            "",
        )
    )


    # Also support:
    #
    #     (300.00)
    #
    # as negative 300.
    if (
        text.startswith(
            "("
        )
        and text.endswith(
            ")"
        )
    ):

        text = (
            "-"
            + text[1:-1]
        )


    try:

        return Decimal(
            text
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )


    except InvalidOperation as error:

        raise ValueError(
            f"Could not convert to Decimal: {value!r}"
        ) from error


def money_text(value):
    """
    Produce a stable two-decimal representation.
    """

    if value is None:

        return ""


    return format(

        value.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        ),

        ".2f",
    )


# ============================================================
# CSV HELPERS
# ============================================================

def read_csv(path):
    """
    Read one CSV into dictionaries.

    These processed files are small enough that holding their
    rows in memory is appropriate.
    """

    if not path.exists():

        raise FileNotFoundError(
            f"Required input file does not exist:\n{path}"
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


def write_csv(
    path,
    records,
):
    """
    Write dictionaries to CSV while preserving all discovered
    fields.
    """

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


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
# STRUCTURAL VALIDATION
# ============================================================

def require_columns(
    rows,
    required_columns,
    dataset_name,
):
    """
    Fail loudly if our normalized input schema is not what the
    production control expects.

    We do NOT silently guess alternative business fields.
    """

    if not rows:

        raise ValueError(
            f"{dataset_name} contains no rows."
        )


    actual_columns = set(
        rows[0].keys()
    )


    missing = [

        column

        for column
        in required_columns

        if column not in actual_columns
    ]


    if missing:

        raise ValueError(

            f"{dataset_name} is missing required column(s): "
            f"{missing}\n\n"
            f"Actual columns:\n"
            f"{sorted(actual_columns)}"
        )


def assert_unique_ids(
    rows,
    id_field,
    dataset_name,
):
    """
    Canonical transaction IDs must be unique.

    A duplicated canonical ID is a structural data problem,
    not a reconciliation exception.
    """

    counts = Counter(

        normalize_text(
            row.get(
                id_field
            )
        )

        for row
        in rows

        if normalize_text(
            row.get(
                id_field
            )
        )
    )


    duplicates = {

        transaction_id:
            count

        for transaction_id, count
        in counts.items()

        if count > 1
    }


    if duplicates:

        example = list(
            duplicates.items()
        )[:10]


        raise ValueError(

            f"{dataset_name} contains duplicate "
            f"{id_field} values.\n"
            f"Examples: {example}"
        )


# ============================================================
# CANONICAL WF ADAPTER
# ============================================================
#
# Upstream historical extraction currently stores:
#
#     legacy_category
#
# because its provenance is the historical workpaper.
#
# The reconciliation core should not know that.
#
# This adapter creates the canonical machine field:
#
#     category
#
# After this boundary, the core sees category="IMS".
# ============================================================

def canonicalize_wf_rows(
    raw_rows,
):
    """
    Convert the explicit historical category dataset into the
    canonical WF representation used by the control.

    NO Excel fill/color is consulted here.
    """

    require_columns(

        raw_rows,

        required_columns=[
            "transaction_id",
            "accounting_period",
            "legacy_category",
            "wf_control_amount",
        ],

        dataset_name=(
            "AIC WF explicit category dataset"
        ),
    )


    assert_unique_ids(

        raw_rows,

        id_field="transaction_id",

        dataset_name=(
            "AIC WF explicit category dataset"
        ),
    )


    canonical_rows = []


    for row in raw_rows:


        category = normalize_upper(

            row.get(
                "legacy_category"
            )
        )


        amount = to_decimal(

            row.get(
                "wf_control_amount"
            )
        )


        canonical_rows.append(

            {
                # --------------------------------------------
                # CANONICAL CONTROL FIELDS
                # --------------------------------------------

                "transaction_id":
                    normalize_text(
                        row.get(
                            "transaction_id"
                        )
                    ),

                "accounting_period":
                    normalize_text(
                        row.get(
                            "accounting_period"
                        )
                    ),

                "category":
                    category,

                "control_amount":
                    amount,

                # --------------------------------------------
                # PROVENANCE / REVIEW CONTEXT
                # --------------------------------------------

                "source_workbook":
                    normalize_text(
                        row.get(
                            "source_workbook"
                        )
                    ),

                "source_sheet":
                    normalize_text(
                        row.get(
                            "source_sheet"
                        )
                    ),

                "source_row":
                    normalize_text(
                        row.get(
                            "source_row"
                        )
                    ),

                "as_of_date":
                    normalize_text(
                        row.get(
                            "as_of_date_raw"
                        )
                    ),

                "transaction_description":
                    normalize_text(
                        row.get(
                            "transaction_description"
                        )
                    ),

                "check_number":
                    normalize_text(
                        row.get(
                            "check_number"
                        )
                    ),

                "descriptive_text_1":
                    normalize_text(
                        row.get(
                            "descriptive_text_1"
                        )
                    ),

                "category_source":
                    normalize_text(
                        row.get(
                            "category_source"
                        )
                    ),
            }
        )


    return canonical_rows


# ============================================================
# CANONICAL IMS ADAPTER
# ============================================================
#
# The normalized IMS sanitizer already provides:
#
#     transaction_id
#     accounting_period
#     cleared_status
#     source_signed_amount
#
# source_signed_amount represents the source transaction:
#
#     debit side  -> positive
#     credit side -> negative
#
# Since the human control sums IMS column G Credit:
#
#     negative source_signed_amount contributes to Credit
#     positive source_signed_amount contributes 0 to Credit
#
# We preserve that distinction explicitly.
# ============================================================

def canonicalize_ims_rows(
    raw_rows,
):
    """
    Build the canonical normalized IMS transaction structure.
    """

    require_columns(

        raw_rows,

        required_columns=[
            "transaction_id",
            "accounting_period",
            "cleared_status",
            "source_signed_amount",
        ],

        dataset_name=(
            "AIC IMS normalized transaction dataset"
        ),
    )


    assert_unique_ids(

        raw_rows,

        id_field="transaction_id",

        dataset_name=(
            "AIC IMS normalized transaction dataset"
        ),
    )


    canonical_rows = []


    for row in raw_rows:


        source_signed_amount = to_decimal(

            row.get(
                "source_signed_amount"
            )
        )


        # ----------------------------------------------------
        # RECONSTRUCT HUMAN "COLUMN G CREDIT" COMPONENT
        # ----------------------------------------------------
        #
        # Human procedure sums Credit only.
        #
        # In normalized source_signed_amount:
        #
        #     negative value = credit-side cash disbursement
        #
        # Therefore:
        #
        #     -100 source signed amount
        #         -> Credit = -100
        #
        #     +100 source signed amount
        #         -> Credit contribution = 0
        #
        # We DO NOT take abs(row amount) here because that would
        # incorrectly turn debit-side transactions into Credit.
        # ----------------------------------------------------

        if (
            source_signed_amount is not None

            and

            source_signed_amount < ZERO
        ):

            credit_component = (
                source_signed_amount
            )


        else:

            credit_component = ZERO


        canonical_rows.append(

            {
                # --------------------------------------------
                # CANONICAL CONTROL FIELDS
                # --------------------------------------------

                "transaction_id":
                    normalize_text(
                        row.get(
                            "transaction_id"
                        )
                    ),

                "accounting_period":
                    normalize_text(
                        row.get(
                            "accounting_period"
                        )
                    ),

                "cleared_status":
                    normalize_lower(
                        row.get(
                            "cleared_status"
                        )
                    ),

                "source_signed_amount":
                    source_signed_amount,

                "credit_component":
                    credit_component,

                # --------------------------------------------
                # PROVENANCE / REVIEW CONTEXT
                # --------------------------------------------

                "source_row":
                    normalize_text(
                        row.get(
                            "source_row"
                        )
                    ),

                "row_kind":
                    normalize_text(
                        row.get(
                            "row_kind"
                        )
                    ),

                "transaction_date":
                    normalize_text(
                        row.get(
                            "transaction_datetime"
                        )
                    ),

                "check_or_ref":
                    normalize_text(
                        row.get(
                            "check_or_ref"
                        )
                    ),

                "method":
                    normalize_text(
                        row.get(
                            "method"
                        )
                    ),

                "payment_type":
                    normalize_text(
                        row.get(
                            "payment_type"
                        )
                    ),

                "description":
                    normalize_text(
                        row.get(
                            "source_description"
                        )
                    ),

                "date_cleared_raw":
                    normalize_text(
                        row.get(
                            "date_cleared_raw"
                        )
                    ),

                "cleared_dates":
                    normalize_text(
                        row.get(
                            "cleared_dates"
                        )
                    ),
            }
        )


    return canonical_rows


# ============================================================
# WF CONTROL POPULATION
# ============================================================

def select_wf_ims_population(
    wf_rows,
    accounting_period,
):
    """
    Production WF population:

        same accounting period
        AND
        category == "IMS"

    There is NO color logic here.
    """

    selected = []


    for row in wf_rows:


        if (
            row[
                "accounting_period"
            ]
            != accounting_period
        ):

            continue


        if (
            row[
                "category"
            ]
            != "IMS"
        ):

            continue


        selected.append(
            row
        )


    return selected


# ============================================================
# IMS CONTROL POPULATION
# ============================================================

def select_ims_cleared_population(
    ims_rows,
    accounting_period,
):
    """
    Production IMS population:

        same accounting period
        AND
        cleared_status in the empirically established
        current-month-cleared statuses.

    Multiple clearing dates remain ONE transaction.
    """

    selected = []


    for row in ims_rows:


        if (
            row[
                "accounting_period"
            ]
            != accounting_period
        ):

            continue


        if (
            row[
                "cleared_status"
            ]
            not in CLEARED_IMS_STATUSES
        ):

            continue


        selected.append(
            row
        )


    return selected


# ============================================================
# RECONCILE ONE ACCOUNTING PERIOD
# ============================================================

def reconcile_period(
    accounting_period,
    wf_rows,
    ims_rows,
    tolerance=DEFAULT_TOLERANCE,
):
    """
    Perform the actual deterministic control for one month.

    CONTROL:

        WF IMS category total
            -
        ABS(IMS cleared Credit total)

    PASS when absolute variance <= tolerance.
    """

    # --------------------------------------------------------
    # SELECT THE TWO BUSINESS POPULATIONS
    # --------------------------------------------------------

    wf_population = select_wf_ims_population(

        wf_rows,

        accounting_period,
    )


    ims_population = select_ims_cleared_population(

        ims_rows,

        accounting_period,
    )


    # --------------------------------------------------------
    # WF DATA-QUALITY CHECK
    # --------------------------------------------------------

    wf_missing_amount = [

        row

        for row
        in wf_population

        if row[
            "control_amount"
        ]
        is None
    ]


    # --------------------------------------------------------
    # IMS DATA-QUALITY CHECK
    # --------------------------------------------------------

    ims_missing_source_amount = [

        row

        for row
        in ims_population

        if row[
            "source_signed_amount"
        ]
        is None
    ]


    # These are not necessarily errors.
    #
    # They simply contribute zero to Credit because the human
    # sums column G Credit only.
    ims_non_credit_rows = [

        row

        for row
        in ims_population

        if (
            row[
                "source_signed_amount"
            ]
            is not None

            and

            row[
                "source_signed_amount"
            ]
            >= ZERO
        )
    ]


    # --------------------------------------------------------
    # CALCULATE WF TOTAL
    # --------------------------------------------------------

    wf_total = sum(

        (
            row[
                "control_amount"
            ]

            for row
            in wf_population

            if row[
                "control_amount"
            ]
            is not None
        ),

        ZERO,
    )


    # --------------------------------------------------------
    # CALCULATE IMS CREDIT TOTAL
    # --------------------------------------------------------
    #
    # This recreates the human Excel SUM of Credit.
    #
    # Credit values are signed negative cash disbursements.
    # --------------------------------------------------------

    ims_signed_credit_total = sum(

        (
            row[
                "credit_component"
            ]

            for row
            in ims_population
        ),

        ZERO,
    )


    # Human compares the magnitude of the cash-disbursement
    # Credit population to the positive WF outflow population.
    ims_outflow_total = abs(

        ims_signed_credit_total
    )


    # --------------------------------------------------------
    # CONTROL VARIANCE
    # --------------------------------------------------------

    variance = (

        wf_total

        - ims_outflow_total
    )


    # --------------------------------------------------------
    # STATUS
    # --------------------------------------------------------
    #
    # Missing normalized amounts are DATA problems and prevent
    # us from claiming the aggregate control passed.
    # --------------------------------------------------------

    has_data_quality_exception = bool(

        wf_missing_amount

        or ims_missing_source_amount
    )


    amount_reconciles = (

        abs(
            variance
        )
        <= tolerance
    )


    if (
        amount_reconciles

        and not has_data_quality_exception
    ):

        status = "PASS"


    else:

        status = "FAIL"


    # --------------------------------------------------------
    # SUMMARY RECORD
    # --------------------------------------------------------

    summary = {

        "accounting_period":
            accounting_period,

        "status":
            status,

        "wf_ims_transaction_count":
            len(
                wf_population
            ),

        "wf_ims_total":
            money_text(
                wf_total
            ),

        "ims_cleared_transaction_count":
            len(
                ims_population
            ),

        "ims_signed_credit_total":
            money_text(
                ims_signed_credit_total
            ),

        "ims_normalized_outflow_total":
            money_text(
                ims_outflow_total
            ),

        "variance":
            money_text(
                variance
            ),

        "tolerance":
            money_text(
                tolerance
            ),

        "amount_reconciles":
            amount_reconciles,

        "wf_missing_amount_count":
            len(
                wf_missing_amount
            ),

        "ims_missing_source_amount_count":
            len(
                ims_missing_source_amount
            ),

        "ims_cleared_non_credit_row_count":
            len(
                ims_non_credit_rows
            ),
    }


    # --------------------------------------------------------
    # EXPLICIT EXCEPTIONS
    # --------------------------------------------------------

    exceptions = []


    if not amount_reconciles:

        exceptions.append(

            {
                "accounting_period":
                    accounting_period,

                "exception_type":
                    "AGGREGATE_VARIANCE",

                "severity":
                    "REVIEW_REQUIRED",

                "wf_ims_total":
                    money_text(
                        wf_total
                    ),

                "ims_normalized_outflow_total":
                    money_text(
                        ims_outflow_total
                    ),

                "variance":
                    money_text(
                        variance
                    ),

                "description":
                    (
                        "The AIC WF population explicitly "
                        "classified as IMS does not equal the "
                        "normalized current-month-cleared IMS "
                        "Credit population."
                    ),
            }
        )


    for row in wf_missing_amount:

        exceptions.append(

            {
                "accounting_period":
                    accounting_period,

                "exception_type":
                    "WF_IMS_MISSING_CONTROL_AMOUNT",

                "severity":
                    "DATA_QUALITY",

                "transaction_id":
                    row[
                        "transaction_id"
                    ],

                "source_row":
                    row[
                        "source_row"
                    ],

                "description":
                    (
                        "WF transaction is explicitly classified "
                        "as IMS but has no normalized control "
                        "amount."
                    ),
            }
        )


    for row in ims_missing_source_amount:

        exceptions.append(

            {
                "accounting_period":
                    accounting_period,

                "exception_type":
                    "IMS_CLEARED_MISSING_SOURCE_AMOUNT",

                "severity":
                    "DATA_QUALITY",

                "transaction_id":
                    row[
                        "transaction_id"
                    ],

                "source_row":
                    row[
                        "source_row"
                    ],

                "description":
                    (
                        "IMS transaction is classified as cleared "
                        "but its normalized source amount is "
                        "missing."
                    ),
            }
        )


    # --------------------------------------------------------
    # AUDITABLE POPULATION OUTPUTS
    # --------------------------------------------------------

    wf_population_output = []


    for row in wf_population:

        wf_population_output.append(

            {
                "accounting_period":
                    accounting_period,

                "transaction_id":
                    row[
                        "transaction_id"
                    ],

                "category":
                    row[
                        "category"
                    ],

                "control_amount":
                    money_text(
                        row[
                            "control_amount"
                        ]
                    ),

                "as_of_date":
                    row[
                        "as_of_date"
                    ],

                "transaction_description":
                    row[
                        "transaction_description"
                    ],

                "check_number":
                    row[
                        "check_number"
                    ],

                "descriptive_text_1":
                    row[
                        "descriptive_text_1"
                    ],

                "source_row":
                    row[
                        "source_row"
                    ],

                "category_source":
                    row[
                        "category_source"
                    ],
            }
        )


    ims_population_output = []


    for row in ims_population:

        ims_population_output.append(

            {
                "accounting_period":
                    accounting_period,

                "transaction_id":
                    row[
                        "transaction_id"
                    ],

                "cleared_status":
                    row[
                        "cleared_status"
                    ],

                "source_signed_amount":
                    money_text(
                        row[
                            "source_signed_amount"
                        ]
                    ),

                "credit_component":
                    money_text(
                        row[
                            "credit_component"
                        ]
                    ),

                "transaction_date":
                    row[
                        "transaction_date"
                    ],

                "check_or_ref":
                    row[
                        "check_or_ref"
                    ],

                "description":
                    row[
                        "description"
                    ],

                "date_cleared_raw":
                    row[
                        "date_cleared_raw"
                    ],

                "cleared_dates":
                    row[
                        "cleared_dates"
                    ],

                "source_row":
                    row[
                        "source_row"
                    ],
            }
        )


    return {

        "summary":
            summary,

        "exceptions":
            exceptions,

        "wf_population":
            wf_population_output,

        "ims_population":
            ims_population_output,
    }


# ============================================================
# MAIN PRODUCTION FUNCTION
# ============================================================

def reconcile_current_month_ims_to_wf(
    accounting_period=None,
    tolerance=DEFAULT_TOLERANCE,
):
    """
    Run the current-month IMS -> WF aggregate control.

    Parameters
    ----------
    accounting_period:
        Optional YYYY-MM.

        When supplied:
            reconcile only that month.

        When omitted:
            run all accounting periods present in either
            normalized dataset. This is useful for historical
            validation/backtesting.

    tolerance:
        Decimal accounting tolerance.

        Default = exact reconciliation, $0.00.

    Returns
    -------
    dict containing:
        overall_status
        monthly_results
        exceptions
        wf_population
        ims_population
    """

    # --------------------------------------------------------
    # LOAD EXPLICIT/NORMALIZED INPUTS ONLY
    # --------------------------------------------------------

    raw_wf_rows = read_csv(
        WF_CATEGORY_PATH
    )


    raw_ims_rows = read_csv(
        IMS_TRANSACTION_PATH
    )


    # --------------------------------------------------------
    # ADAPT TO CANONICAL INTERNAL STRUCTURES
    # --------------------------------------------------------

    wf_rows = canonicalize_wf_rows(
        raw_wf_rows
    )


    ims_rows = canonicalize_ims_rows(
        raw_ims_rows
    )


    # --------------------------------------------------------
    # DETERMINE ACCOUNTING PERIODS
    # --------------------------------------------------------

    available_periods = sorted(

        {

            row[
                "accounting_period"
            ]

            for row
            in (
                wf_rows
                + ims_rows
            )

            if row[
                "accounting_period"
            ]
        }
    )


    if accounting_period is not None:


        if accounting_period not in available_periods:

            raise ValueError(

                f"Accounting period {accounting_period!r} "
                f"was not found.\n"
                f"Available periods: {available_periods}"
            )


        periods_to_run = [
            accounting_period
        ]


    else:

        periods_to_run = (
            available_periods
        )


    # --------------------------------------------------------
    # RUN EACH PERIOD
    # --------------------------------------------------------

    monthly_results = []

    all_exceptions = []

    all_wf_population = []

    all_ims_population = []


    for period in periods_to_run:


        result = reconcile_period(

            accounting_period=period,

            wf_rows=wf_rows,

            ims_rows=ims_rows,

            tolerance=tolerance,
        )


        monthly_results.append(

            result[
                "summary"
            ]
        )


        all_exceptions.extend(

            result[
                "exceptions"
            ]
        )


        all_wf_population.extend(

            result[
                "wf_population"
            ]
        )


        all_ims_population.extend(

            result[
                "ims_population"
            ]
        )


    # --------------------------------------------------------
    # OVERALL STATUS
    # --------------------------------------------------------

    overall_status = (

        "PASS"

        if all(

            row[
                "status"
            ]
            == "PASS"

            for row
            in monthly_results
        )

        else "FAIL"
    )


    return {

        "control_name":
            "reconcile_current_month_ims_to_wf",

        "overall_status":
            overall_status,

        "periods_run":
            periods_to_run,

        "monthly_results":
            monthly_results,

        "exceptions":
            all_exceptions,

        "wf_population":
            all_wf_population,

        "ims_population":
            all_ims_population,
    }


# ============================================================
# WRITE PRODUCTION OUTPUTS
# ============================================================

def write_outputs(
    result,
):
    """
    Persist audit trail and exception outputs.
    """

    OUTPUT_FOLDER.mkdir(
        parents=True,
        exist_ok=True,
    )


    write_csv(

        MONTHLY_OUTPUT_PATH,

        result[
            "monthly_results"
        ],
    )


    write_csv(

        EXCEPTION_OUTPUT_PATH,

        result[
            "exceptions"
        ],
    )


    write_csv(

        WF_POPULATION_OUTPUT_PATH,

        result[
            "wf_population"
        ],
    )


    write_csv(

        IMS_POPULATION_OUTPUT_PATH,

        result[
            "ims_population"
        ],
    )


    report = {

        "control_name":
            result[
                "control_name"
            ],

        "overall_status":
            result[
                "overall_status"
            ],

        "periods_run":
            result[
                "periods_run"
            ],

        "business_rule": {

            "wf_population":
                (
                    "Same-period AIC WF transactions with "
                    "canonical category='IMS'."
                ),

            "ims_population":
                (
                    "Same-period normalized AIC IMS "
                    "transactions whose cleared_status is "
                    "'cleared' or "
                    "'multiple_cleared_dates'."
                ),

            "ims_amount_rule":
                (
                    "Reconstruct column-G Credit from negative "
                    "source_signed_amount values only; debit-side "
                    "rows contribute zero to the Credit sum."
                ),

            "control_formula":
                (
                    "variance = WF IMS total - "
                    "ABS(IMS cleared Credit total)"
                ),

            "pass_rule":
                (
                    "Absolute variance must be within tolerance "
                    "and no required normalized amount may be "
                    "missing."
                ),
        },

        "monthly_results":
            result[
                "monthly_results"
            ],

        "exceptions":
            result[
                "exceptions"
            ],
    }


    with REPORT_OUTPUT_PATH.open(

        "w",

        encoding="utf-8",

    ) as file:


        json.dump(

            report,

            file,

            indent=2,

            ensure_ascii=False,
        )


# ============================================================
# TERMINAL SUMMARY
# ============================================================

def print_summary(
    result,
):
    """
    Human-readable run result.
    """

    print(
        "ASCOT CURRENT-MONTH IMS -> WF RECONCILIATION"
    )


    print(
        "Deterministic aggregate completeness/control check"
    )


    print(
        "\n========================================"
    )


    print(
        "MONTHLY RESULTS"
    )


    print(
        "========================================"
    )


    for row in result[
        "monthly_results"
    ]:


        print(

            f"{row['accounting_period']} | "
            f"{row['status']} | "
            f"WF IMS rows "
            f"{row['wf_ims_transaction_count']} | "
            f"WF total "
            f"{row['wf_ims_total']} | "
            f"IMS cleared rows "
            f"{row['ims_cleared_transaction_count']} | "
            f"IMS outflow "
            f"{row['ims_normalized_outflow_total']} | "
            f"variance "
            f"{row['variance']}"
        )


    print(
        "\n========================================"
    )


    print(
        "EXCEPTIONS"
    )


    print(
        "========================================"
    )


    if not result[
        "exceptions"
    ]:


        print(
            "None."
        )


    else:


        for exception in result[
            "exceptions"
        ]:


            print(
                "\n---"
            )


            print(

                f"{exception.get('accounting_period')} | "
                f"{exception.get('exception_type')} | "
                f"{exception.get('severity')}"
            )


            if (
                exception.get(
                    "exception_type"
                )
                == "AGGREGATE_VARIANCE"
            ):


                print(

                    f"WF IMS total: "
                    f"{exception.get('wf_ims_total')}"
                )


                print(

                    f"IMS outflow total: "
                    f"{exception.get('ims_normalized_outflow_total')}"
                )


                print(

                    f"Variance: "
                    f"{exception.get('variance')}"
                )


            else:


                print(

                    f"Transaction: "
                    f"{exception.get('transaction_id')}"
                )


                print(

                    f"Source row: "
                    f"{exception.get('source_row')}"
                )


    print(
        "\n========================================"
    )


    print(

        "OVERALL STATUS: "
        f"{result['overall_status']}"
    )


    print(
        "========================================"
    )


    print(
        "\nOutputs:"
    )


    print(
        MONTHLY_OUTPUT_PATH
    )


    print(
        EXCEPTION_OUTPUT_PATH
    )


    print(
        WF_POPULATION_OUTPUT_PATH
    )


    print(
        IMS_POPULATION_OUTPUT_PATH
    )


    print(
        REPORT_OUTPUT_PATH
    )


# ============================================================
# COMMAND-LINE INTERFACE
# ============================================================

def parse_arguments():

    parser = argparse.ArgumentParser(

        description=(
            "Reconcile current-month AIC IMS cleared Credit "
            "population to AIC WF transactions explicitly "
            "classified as IMS."
        )
    )


    parser.add_argument(

        "--period",

        help=(
            "Optional accounting period YYYY-MM. "
            "If omitted, all available periods are run."
        ),
    )


    parser.add_argument(

        "--tolerance",

        default="0.00",

        help=(
            "Accounting tolerance in dollars. "
            "Default: 0.00."
        ),
    )


    return parser.parse_args()


# ============================================================
# RUN
# ============================================================

def main():

    args = parse_arguments()


    tolerance = to_decimal(

        args.tolerance,

        allow_blank=False,
    )


    if tolerance < ZERO:

        raise ValueError(
            "Tolerance cannot be negative."
        )


    result = reconcile_current_month_ims_to_wf(

        accounting_period=args.period,

        tolerance=tolerance,
    )


    write_outputs(
        result
    )


    print_summary(
        result
    )


if __name__ == "__main__":

    main()