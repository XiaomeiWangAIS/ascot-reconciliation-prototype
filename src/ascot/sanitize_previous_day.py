# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# WF PREVIOUS DAY TRANSACTIONS SANITIZER
# ============================================================
#
# IMPORTANT
# ------------------------------------------------------------
#
# This sanitizer was designed AFTER direct inspection of the
# actual January–July 2026 WF Previous Day Transactions files.
#
# It does NOT infer spreadsheet structure from the SOP or
# process documentation.
#
#
# ACTUAL DATA STRUCTURE OBSERVED
# ------------------------------------------------------------
#
# Authoritative sheet:
#
#     DEP_1101_TRAN
#
#
# Stable 9-column schema:
#
#   A  As-Of Date
#   B  Acct No
#   C  Acct Name
#   D  Tran Desc
#   E  Debit Amt
#   F  Credit Amt
#   G  0 Day Flt Amt
#   H  Customer Ref No
#   I  Descriptive Text 1
#
#
# IMPORTANT MONTH-TO-MONTH DIFFERENCES
# ------------------------------------------------------------
#
# HEADER:
#
#     Jan  row 1
#     Feb  row 1
#     Mar  row 2  <-- row 1 contains summary formulas
#     Apr  row 1
#     May  row 1
#     Jun  row 1
#     Jul  row 1
#
#
# COLUMN G:
#
# Despite the header "0 Day Flt Amt", this column is NOT
# semantically stable.
#
# In April / May / July it is essentially:
#
#     Debit - Credit
#
# for every transaction.
#
# June uses this formula selectively.
#
# Jan / Feb / Mar largely contain original float values / zero.
#
# Therefore:
#
#     NEVER use column G as the authoritative amount.
#
# Instead derive:
#
#     bank_net_amount = debit - credit
#
# from columns E/F.
#
#
# TRANSACTION ROW:
#
# Across every actual transaction inspected:
#
#     exactly one of Debit or Credit is nonzero.
#
# None had both.
# None had neither.
#
#
# AIC DISBURSEMENT ACCOUNT:
#
#     4062522693
#     AIC - Disbursement Account
#
# Its rows are distributed throughout the report rather than
# existing as one contiguous Excel block.
#
#
# AIC ZBA / SWEEP TYPES:
#
#     ZBA DEBIT TRANSFER
#     ZBA CREDIT TRANSFER
#     SWEEP PRINCIPAL BUY
#     SWEEP PRINCIPAL SELL
#
# These four exact Tran Desc values reproduce the validated
# AIC WF ZBA/sweep populations for every Jan–Jul month.
#
#
# CUSTOMER REF:
#
# Jan–Mar often contain strings preserving leading zeros.
#
# Apr–Jul often store identifiers as numeric values.
#
# Therefore we preserve:
#
#     customer_ref_raw
#
# and separately derive:
#
#     customer_ref_text
#     customer_ref_match_key
#
#
# DUPLICATES:
#
# July contains two legitimate source rows whose visible
# fields are completely identical.
#
# Therefore:
#
#     NEVER automatically deduplicate based on field values.
#
# Source workbook + source row are part of transaction identity.
#
#
# OUTPUTS
# ------------------------------------------------------------
#
# Per month:
#
#   wf_previous_day_transactions.csv
#       all bank transactions from DEP_1101_TRAN
#
#   aic_previous_day_transactions.csv
#       filtered account 4062522693
#
#   wf_previous_day_control_rows.csv
#       helper / summary rows
#
#   wf_previous_day_account_summary.csv
#       account-level counts/totals
#
#   wf_previous_day_validation.json
#
#
# Consolidated:
#
#   wf_previous_day_all_months_transactions.csv
#   aic_previous_day_all_months_transactions.csv
#   wf_previous_day_all_months_control_rows.csv
#   wf_previous_day_all_months_account_summary.csv
#   wf_previous_day_processing_manifest.json
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import csv
import json
import re

from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook


# ============================================================
# PROJECT PATHS
# ============================================================

RAW_FOLDER = Path(
    "data/raw"
)


PROCESSED_FOLDER = Path(
    "data/processed"
)


PROCESSED_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# SOURCE / TARGET DEFINITIONS
# ============================================================

SOURCE_SHEET = (
    "DEP_1101_TRAN"
)


AIC_DISBURSEMENT_ACCOUNT = (
    "4062522693"
)


AIC_DISBURSEMENT_NAME = (
    "AIC - Disbursement Account"
)


# ============================================================
# EXPECTED SOURCE HEADER
# ============================================================

EXPECTED_HEADER = [

    "As-Of Date",

    "Acct No",

    "Acct Name",

    "Tran Desc",

    "Debit Amt",

    "Credit Amt",

    "0 Day Flt Amt",

    "Customer Ref No",

    "Descriptive Text 1",
]


# ============================================================
# EXACT ZBA / SWEEP TYPES OBSERVED
# ============================================================

ZBA_TRANSACTION_TYPES = {

    "ZBA DEBIT TRANSFER",

    "ZBA CREDIT TRANSFER",
}


SWEEP_TRANSACTION_TYPES = {

    "SWEEP PRINCIPAL BUY",

    "SWEEP PRINCIPAL SELL",
}


ZBA_SWEEP_TRANSACTION_TYPES = (

    ZBA_TRANSACTION_TYPES

    | SWEEP_TRANSACTION_TYPES
)


# ============================================================
# TEXT HELPERS
# ============================================================

def normalize_text(value):
    """
    Convert a value into clean text while preserving case.
    """

    if value is None:

        return ""


    return re.sub(

        r"\s+",

        " ",

        str(value).strip(),
    )


def normalize_upper(value):
    """
    Normalize text and uppercase it for comparison.
    """

    return normalize_text(
        value
    ).upper()


# ============================================================
# SAFE NUMERIC CONVERSION
# ============================================================

def normalize_number(value):
    """
    Convert Excel numeric values into Python floats.

    Blank cells remain None.
    """

    if value is None:

        return None


    if isinstance(
        value,
        bool,
    ):

        return None


    if isinstance(
        value,
        (int, float),
    ):

        return float(
            value
        )


    text = (
        str(value)
        .strip()
        .replace("$", "")
        .replace(",", "")
    )


    if text == "":

        return None


    try:

        return float(
            text
        )


    except ValueError:

        return None


# ============================================================
# ACCOUNTING PERIOD FROM FILENAME
# ============================================================

def extract_accounting_period(
    file_path,
):
    """
    Previous Day filenames look like:

        WF Previous Day Transactions January 2026.xlsx

    or:

        WF Previous day transactions July 2026.xlsx

    We extract the final Month + Year rather than relying
    on capitalization.
    """

    match = re.search(

        r"\b("
        r"January|February|March|April|May|June|"
        r"July|August|September|October|November|December"
        r")\s+(\d{4})\b",

        file_path.stem,

        flags=re.IGNORECASE,
    )


    if not match:

        raise ValueError(

            "Cannot identify accounting period from "
            f"filename: {file_path.name}"
        )


    month_name = (
        match.group(1).title()
    )


    year = (
        match.group(2)
    )


    return datetime.strptime(

        f"{month_name} {year}",

        "%B %Y",
    )


def accounting_period_label(
    file_path,
):
    """
    Convert period into YYYY-MM.
    """

    return extract_accounting_period(
        file_path
    ).strftime(
        "%Y-%m"
    )


# ============================================================
# DATE NORMALIZATION
# ============================================================

def normalize_as_of_date(
    value,
):
    """
    Actual Previous Day files store dates as text:

        YYYY/MM/DD

    We preserve the raw date separately but convert the
    machine-readable date to:

        YYYY-MM-DD
    """

    text = normalize_text(
        value
    )


    if not text:

        return None


    try:

        parsed = datetime.strptime(

            text,

            "%Y/%m/%d",
        )


        return parsed.date().isoformat()


    except ValueError:

        return None


# ============================================================
# IDENTIFIER NORMALIZATION
# ============================================================

def normalize_identifier_text(
    value,
):
    """
    Convert identifiers into a stable text representation.

    Examples:

        3330005430
            -> "3330005430"

        "03330005430"
            -> "03330005430"

        0
            -> "0"

    Raw value is preserved separately.
    """

    if value is None:

        return None


    if isinstance(
        value,
        bool,
    ):

        return str(
            value
        )


    if isinstance(
        value,
        int,
    ):

        return str(
            value
        )


    if isinstance(
        value,
        float,
    ):


        if value.is_integer():

            return str(
                int(value)
            )


        return str(
            value
        )


    text = str(
        value
    ).strip()


    return (
        text
        if text
        else None
    )


def identifier_match_key(
    value,
):
    """
    Create a comparison key useful for future WF <-> IMS
    reconciliation.

    We preserve the original identifier elsewhere.

    Numeric identifiers have leading zeros removed so:

        03330005430
        3330005430

    can potentially match.

    A value containing only zeros is treated as unavailable,
    because zero is a generic placeholder in these files.
    """

    text = normalize_identifier_text(
        value
    )


    if text is None:

        return None


    if re.fullmatch(
        r"\d+",
        text,
    ):


        if set(
            text
        ) == {
            "0"
        }:

            return None


        stripped = text.lstrip(
            "0"
        )


        return (
            stripped
            if stripped
            else None
        )


    # Non-numeric identifier:
    # normalize case/spacing only.
    return normalize_upper(
        text
    )


# ============================================================
# WRITE CSV
# ============================================================

def write_csv(
    path,
    records,
):
    """
    Write records without pandas.
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
# FIND HEADER ROW
# ============================================================

def find_header_row(
    worksheet,
):
    """
    Detect the header from actual cell contents.

    This correctly handles March, where the header occurs
    at row 2 rather than row 1.
    """

    expected_normalized = [

        normalize_upper(
            value
        )

        for value
        in EXPECTED_HEADER
    ]


    for row_number, row in enumerate(

        worksheet.iter_rows(

            min_row=1,

            max_row=10,

            max_col=9,

            values_only=True,
        ),

        start=1,
    ):


        actual = [

            normalize_upper(
                value
            )

            for value
            in row
        ]


        if actual == expected_normalized:

            return row_number


    raise ValueError(

        "Could not find the expected "
        "DEP_1101_TRAN header."
    )


# ============================================================
# IDENTIFY TRUE TRANSACTION ROW
# ============================================================

def classify_transaction_row(
    values,
):
    """
    Determine whether a row is a real bank transaction.

    Actual Jan–Jul evidence shows that every true transaction:

      - has As-Of Date,
      - has Acct No,
      - has Tran Desc,
      - has exactly one nonzero Debit/Credit.

    Returns:

        is_transaction
        structural_warning
    """

    as_of_date = values[
        0
    ]


    account_number = values[
        1
    ]


    transaction_description = values[
        3
    ]


    debit = normalize_number(
        values[
            4
        ]
    )


    credit = normalize_number(
        values[
            5
        ]
    )


    identity_present = (

        normalize_text(
            as_of_date
        ) != ""

        and

        normalize_text(
            account_number
        ) != ""

        and

        normalize_text(
            transaction_description
        ) != ""
    )


    has_debit = (

        debit is not None

        and abs(
            debit
        ) > 0
    )


    has_credit = (

        credit is not None

        and abs(
            credit
        ) > 0
    )


    if (

        identity_present

        and (
            has_debit
            != has_credit
        )
    ):

        return (
            True,
            None,
        )


    # The row has transaction identity fields, but the
    # debit/credit structure differs from the Jan–Jul pattern.
    if identity_present:

        return (

            False,

            (
                "Row has transaction identifiers but does not "
                "contain exactly one nonzero Debit/Credit."
            ),
        )


    return (
        False,
        None,
    )


# ============================================================
# PARSE ZBA COUNTERPARTY ACCOUNT
# ============================================================

def parse_zba_counterparty(
    descriptive_text,
):
    """
    Actual ZBA descriptions contain patterns such as:

        ZBA FUNDING ACCOUNT TRANSFER FROM 4062522685

        ZBA FUNDING ACCOUNT TRANSFER TO 4943372037
    """

    text = normalize_upper(
        descriptive_text
    )


    match = re.search(

        r"\b(FROM|TO)\s+(\d{6,})\b",

        text,
    )


    if not match:

        return (
            None,
            None,
        )


    direction = (
        match.group(1)
    )


    account = (
        match.group(2)
    )


    return (
        direction,
        account,
    )


# ============================================================
# SANITIZE ONE MONTH
# ============================================================

def sanitize_one_workbook(
    workbook_path,
    processing_sequence,
):

    period = accounting_period_label(
        workbook_path
    )


    print(
        "\n========================================"
    )


    print(
        f"Processing #{processing_sequence}: "
        f"{workbook_path.name}"
    )


    print(
        f"Accounting period: {period}"
    )


    print(
        "========================================"
    )


    # ========================================================
    # OPEN TWO STREAMING VIEWS OF THE SAME FILE
    # ========================================================
    #
    # FORMULA workbook:
    #
    #     lets us see whether a cell contains a formula.
    #
    # VALUE workbook:
    #
    #     gives us the last calculated numeric value.
    #
    # This matters because column G is formula-driven in some
    # months but not others.
    # ========================================================

    workbook_formula = load_workbook(

        workbook_path,

        read_only=True,

        data_only=False,

        keep_links=False,
    )


    workbook_value = load_workbook(

        workbook_path,

        read_only=True,

        data_only=True,

        keep_links=False,
    )


    try:

        # ====================================================
        # AUTHORITATIVE SOURCE SHEET
        # ====================================================

        if SOURCE_SHEET not in (
            workbook_formula.sheetnames
        ):

            raise ValueError(

                f"{SOURCE_SHEET} not found in "
                f"{workbook_path.name}."
            )


        sheet_formula = (
            workbook_formula[
                SOURCE_SHEET
            ]
        )


        sheet_value = (
            workbook_value[
                SOURCE_SHEET
            ]
        )


        # Record extra/derived worksheets but do not ingest
        # them as source transactions.
        extra_sheet_names = [

            sheet_name

            for sheet_name
            in workbook_formula.sheetnames

            if sheet_name
            != SOURCE_SHEET
        ]


        # ====================================================
        # FIND HEADER
        # ====================================================

        header_row = find_header_row(
            sheet_value
        )


        print(
            f"Detected header row: "
            f"{header_row}"
        )


        print(
            f"Extra/derived sheets: "
            f"{len(extra_sheet_names)}"
        )


        # ====================================================
        # OUTPUT COLLECTIONS
        # ====================================================

        transactions = []

        aic_transactions = []

        control_rows = []

        warnings = []


        formula_counts = Counter()


        # Account-level aggregation.
        account_summary = defaultdict(

            lambda: {

                "transaction_count":
                    0,

                "debit_total":
                    0.0,

                "credit_total":
                    0.0,

                "net_total":
                    0.0,

                "client_analysis_fee_count":
                    0,

                "client_analysis_fee_debit_total":
                    0.0,
            }
        )


        # ====================================================
        # ITERATE BOTH VIEWS IN PARALLEL
        # ====================================================

        formula_rows = sheet_formula.iter_rows(

            min_row=1,

            max_col=9,
        )


        value_rows = sheet_value.iter_rows(

            min_row=1,

            max_col=9,
        )


        for source_row, (
            formula_row,
            value_row,
        ) in enumerate(

            zip(
                formula_rows,
                value_rows,
            ),

            start=1,
        ):


            # =================================================
            # READ CACHED VALUES A:I
            # =================================================

            values = [

                cell.value

                for cell
                in value_row
            ]


            # =================================================
            # CAPTURE FORMULAS A:I
            # =================================================

            formulas = []


            for column_number, cell in enumerate(

                formula_row,

                start=1,
            ):


                value = cell.value


                if (

                    isinstance(
                        value,
                        str,
                    )

                    and value.startswith(
                        "="
                    )
                ):

                    formulas.append(

                        {
                            "column":
                                column_number,

                            "formula":
                                value,
                        }
                    )


                    formula_counts[
                        column_number
                    ] += 1


            # =================================================
            # HEADER ROW IS NOT DATA
            # =================================================

            if source_row == header_row:

                continue


            # =================================================
            # CLASSIFY TRANSACTION STRUCTURE
            # =================================================

            (
                is_transaction,
                structural_warning,
            ) = classify_transaction_row(
                values
            )


            # =================================================
            # NON-TRANSACTION / CONTROL ROW
            # =================================================

            if not is_transaction:


                meaningful = any(

                    normalize_text(
                        value
                    ) != ""

                    for value
                    in values
                )


                if meaningful:


                    control_rows.append(

                        {
                            "accounting_period":
                                period,

                            "processing_sequence":
                                processing_sequence,

                            "source_workbook":
                                workbook_path.name,

                            "source_sheet":
                                SOURCE_SHEET,

                            "source_row":
                                source_row,

                            "relative_to_header":
                                (
                                    "before_header"

                                    if source_row
                                    < header_row

                                    else
                                    "after_header"
                                ),

                            "values_json":
                                json.dumps(

                                    values,

                                    default=str,
                                ),

                            "formulas_json":
                                json.dumps(
                                    formulas
                                ),
                        }
                    )


                if structural_warning:


                    warnings.append(

                        {
                            "source_row":
                                source_row,

                            "warning_type":
                                "transaction_structure",

                            "message":
                                structural_warning,

                            "values":
                                values,
                        }
                    )


                continue


            # =================================================
            # UNPACK SOURCE DATA
            # =================================================

            (
                as_of_date_raw,
                account_number_raw,
                account_name,
                transaction_description,
                debit_raw,
                credit_raw,
                column_g_raw,
                customer_ref_raw,
                descriptive_text,
            ) = values


            # =================================================
            # NORMALIZE AMOUNTS
            # =================================================

            debit = normalize_number(
                debit_raw
            )


            credit = normalize_number(
                credit_raw
            )


            # Actual Jan–Jul structure guarantees exactly one
            # nonzero side for real transaction rows.
            if (

                debit is not None

                and abs(
                    debit
                ) > 0
            ):

                bank_direction = (
                    "debit"
                )


                bank_amount = abs(
                    debit
                )


            else:

                bank_direction = (
                    "credit"
                )


                bank_amount = abs(
                    credit
                )


            # =================================================
            # DERIVE MACHINE NET AMOUNT
            # ========================================================
            #
            # Positive = debit
            # Negative = credit
            #
            # We calculate this ourselves and do NOT trust
            # source column G.
            # =================================================

            bank_net_amount = (

                (debit or 0.0)

                - (credit or 0.0)
            )


            # =================================================
            # DATE
            # =================================================

            as_of_date = normalize_as_of_date(
                as_of_date_raw
            )


            if as_of_date is None:


                warnings.append(

                    {
                        "source_row":
                            source_row,

                        "warning_type":
                            "date_parse",

                        "message":
                            (
                                "Could not parse As-Of Date "
                                f"value: {as_of_date_raw}"
                            ),
                    }
                )


            # =================================================
            # ACCOUNT NUMBER
            # =================================================

            account_number = (
                normalize_identifier_text(
                    account_number_raw
                )
            )


            # =================================================
            # TRANSACTION DESCRIPTION
            # =================================================

            transaction_type = (
                normalize_upper(
                    transaction_description
                )
            )


            # =================================================
            # CUSTOMER REFERENCE
            # =================================================

            customer_ref_text = (
                normalize_identifier_text(
                    customer_ref_raw
                )
            )


            customer_ref_key = (
                identifier_match_key(
                    customer_ref_raw
                )
            )


            # =================================================
            # ZBA / SWEEP
            # =================================================

            is_zba = (

                transaction_type
                in ZBA_TRANSACTION_TYPES
            )


            is_sweep = (

                transaction_type
                in SWEEP_TRANSACTION_TYPES
            )


            is_zba_or_sweep = (

                transaction_type
                in ZBA_SWEEP_TRANSACTION_TYPES
            )


            # =================================================
            # ZBA COUNTERPARTY
            # =================================================

            (
                zba_transfer_direction,
                zba_counterparty_account,
            ) = parse_zba_counterparty(
                descriptive_text
            )


            # =================================================
            # SWEEP DIRECTION
            # =================================================

            if (
                transaction_type
                == "SWEEP PRINCIPAL BUY"
            ):

                sweep_direction = (
                    "to_investment"
                )


            elif (
                transaction_type
                == "SWEEP PRINCIPAL SELL"
            ):

                sweep_direction = (
                    "from_investment"
                )


            else:

                sweep_direction = None


            # =================================================
            # BANK ANALYSIS FEE SIGNAL
            # =================================================

            is_client_analysis_fee = (

                "CLIENT ANALYSIS SRVC CHRG"

                in normalize_upper(
                    descriptive_text
                )
            )


            # =================================================
            # RETURN / NSF SIGNAL
            # ========================================================
            #
            # Ascot explicitly told us rejection descriptions
            # are not consistent.
            #
            # Therefore this is ONLY a search signal, not a
            # definitive rejection classification.
            # =================================================

            return_keyword_signal = any(

                keyword
                in normalize_upper(
                    descriptive_text
                )

                for keyword in [

                    "RETURN",

                    "NSF",
                ]
            )


            # =================================================
            # COLUMN G FORMULA
            # =================================================

            column_g_formula = None


            formula_cell_g = formula_row[
                6
            ]


            if (

                isinstance(
                    formula_cell_g.value,
                    str,
                )

                and formula_cell_g.value.startswith(
                    "="
                )
            ):

                column_g_formula = (
                    formula_cell_g.value
                )


            # =================================================
            # SOURCE TRANSACTION ID
            # ========================================================
            #
            # Source row is part of identity.
            #
            # Do NOT deduplicate field-identical rows.
            # =================================================

            transaction_id = (

                f"PD-{period}-R{source_row}"
            )


            # =================================================
            # AIC SECTION
            # =================================================

            is_aic_disbursement = (

                account_number
                == AIC_DISBURSEMENT_ACCOUNT
            )


            if is_aic_disbursement:


                if is_zba_or_sweep:

                    aic_section = (
                        "zba_sweep_transfers"
                    )


                else:

                    aic_section = (
                        "main_cash_activity"
                    )


            else:

                aic_section = None


            # =================================================
            # NORMALIZED TRANSACTION
            # =================================================

            transaction = {

                "transaction_id":
                    transaction_id,

                "accounting_period":
                    period,

                "processing_sequence":
                    processing_sequence,

                "source_workbook":
                    workbook_path.name,

                "source_sheet":
                    SOURCE_SHEET,

                "source_row":
                    source_row,

                "as_of_date_raw":
                    normalize_text(
                        as_of_date_raw
                    ),

                "as_of_date":
                    as_of_date,

                "account_number_raw":
                    normalize_identifier_text(
                        account_number_raw
                    ),

                "account_number":
                    account_number,

                "account_name":
                    normalize_text(
                        account_name
                    ),

                "transaction_description":
                    normalize_text(
                        transaction_description
                    ),

                "transaction_type":
                    transaction_type,

                "debit_amount":
                    debit,

                "credit_amount":
                    credit,

                "bank_direction":
                    bank_direction,

                "bank_amount":
                    bank_amount,

                "bank_net_amount":
                    bank_net_amount,

                # Column G is intentionally preserved but
                # NEVER treated as authoritative transaction
                # amount.
                "source_column_g_raw":
                    column_g_raw,

                "source_column_g_formula":
                    column_g_formula,

                "customer_ref_raw":
                    customer_ref_raw,

                "customer_ref_text":
                    customer_ref_text,

                "customer_ref_match_key":
                    customer_ref_key,

                "descriptive_text_1":
                    normalize_text(
                        descriptive_text
                    ),

                "is_aic_disbursement":
                    is_aic_disbursement,

                "aic_section":
                    aic_section,

                "is_zba":
                    is_zba,

                "is_sweep":
                    is_sweep,

                "is_zba_or_sweep":
                    is_zba_or_sweep,

                "zba_transfer_direction":
                    zba_transfer_direction,

                "zba_counterparty_account":
                    zba_counterparty_account,

                "sweep_direction":
                    sweep_direction,

                "is_client_analysis_fee":
                    is_client_analysis_fee,

                # Only a signal.
                "return_or_nsf_keyword_signal":
                    return_keyword_signal,
            }


            transactions.append(
                transaction
            )


            if is_aic_disbursement:

                aic_transactions.append(
                    transaction
                )


            # =================================================
            # ACCOUNT SUMMARY
            # =================================================

            account_key = (

                account_number,

                normalize_text(
                    account_name
                ),
            )


            account_summary[
                account_key
            ][
                "transaction_count"
            ] += 1


            account_summary[
                account_key
            ][
                "debit_total"
            ] += (
                debit
                or 0.0
            )


            account_summary[
                account_key
            ][
                "credit_total"
            ] += (
                credit
                or 0.0
            )


            account_summary[
                account_key
            ][
                "net_total"
            ] += bank_net_amount


            if is_client_analysis_fee:


                account_summary[
                    account_key
                ][
                    "client_analysis_fee_count"
                ] += 1


                account_summary[
                    account_key
                ][
                    "client_analysis_fee_debit_total"
                ] += (
                    debit
                    or 0.0
                )


        # ====================================================
        # BUILD ACCOUNT-SUMMARY RECORDS
        # ====================================================

        account_summary_records = []


        for (
            account_number,
            account_name,
        ), summary in sorted(

            account_summary.items(),

            key=lambda item: (
                item[
                    0
                ][
                    0
                ]
                or ""
            ),
        ):


            account_summary_records.append(

                {
                    "accounting_period":
                        period,

                    "processing_sequence":
                        processing_sequence,

                    "source_workbook":
                        workbook_path.name,

                    "account_number":
                        account_number,

                    "account_name":
                        account_name,

                    **summary,
                }
            )


        # ====================================================
        # TARGET-AIC VALIDATION METRICS
        # ====================================================

        aic_zba_count = sum(

            transaction[
                "is_zba"
            ]

            for transaction
            in aic_transactions
        )


        aic_sweep_count = sum(

            transaction[
                "is_sweep"
            ]

            for transaction
            in aic_transactions
        )


        aic_zba_sweep_count = (

            aic_zba_count

            + aic_sweep_count
        )


        aic_main_count = (

            len(
                aic_transactions
            )

            - aic_zba_sweep_count
        )


        # ====================================================
        # IDENTICAL-VISIBLE-ROW DIAGNOSTIC
        # ========================================================
        #
        # This is NOT a deduplication routine.
        #
        # We merely report visible duplicates so we know they
        # exist while preserving every source row.
        # ====================================================

        visible_key_counts = Counter()


        for transaction in (
            aic_transactions
        ):


            visible_key = (

                transaction[
                    "as_of_date"
                ],

                transaction[
                    "account_number"
                ],

                transaction[
                    "transaction_type"
                ],

                transaction[
                    "debit_amount"
                ],

                transaction[
                    "credit_amount"
                ],

                transaction[
                    "customer_ref_text"
                ],

                transaction[
                    "descriptive_text_1"
                ],
            )


            visible_key_counts[
                visible_key
            ] += 1


        duplicate_visible_extra_rows = sum(

            count - 1

            for count
            in visible_key_counts.values()

            if count > 1
        )


        # ====================================================
        # CLIENT ANALYSIS FEE COUNTS
        # ====================================================

        full_report_fee_count = sum(

            transaction[
                "is_client_analysis_fee"
            ]

            for transaction
            in transactions
        )


        aic_fee_count = sum(

            transaction[
                "is_client_analysis_fee"
            ]

            for transaction
            in aic_transactions
        )


        # ====================================================
        # VALIDATION REPORT
        # ====================================================

        validation = {

            "accounting_period":
                period,

            "processing_sequence":
                processing_sequence,

            "source_workbook":
                workbook_path.name,

            "source_sheet":
                SOURCE_SHEET,

            "header_row":
                header_row,

            "schema_matches_expected":
                True,

            "extra_sheet_names":
                extra_sheet_names,

            "full_report_transaction_count":
                len(
                    transactions
                ),

            "account_count":
                len(
                    account_summary_records
                ),

            "control_row_count":
                len(
                    control_rows
                ),

            "structural_warning_count":
                len(
                    warnings
                ),

            "warnings":
                warnings,

            "formula_count_by_column":
                {

                    str(
                        column_number
                    ):
                        count

                    for (
                        column_number,
                        count,
                    ) in sorted(
                        formula_counts.items()
                    )
                },

            "aic_disbursement_account":
                AIC_DISBURSEMENT_ACCOUNT,

            "aic_disbursement_name":
                AIC_DISBURSEMENT_NAME,

            "aic_transaction_count":
                len(
                    aic_transactions
                ),

            "aic_main_cash_activity_count":
                aic_main_count,

            "aic_zba_count":
                aic_zba_count,

            "aic_sweep_count":
                aic_sweep_count,

            "aic_zba_sweep_count":
                aic_zba_sweep_count,

            "aic_visible_duplicate_extra_row_count":
                duplicate_visible_extra_rows,

            "full_report_client_analysis_fee_count":
                full_report_fee_count,

            "aic_client_analysis_fee_count":
                aic_fee_count,
        }


        # ====================================================
        # OUTPUT FOLDER
        # ====================================================

        output_folder = (

            PROCESSED_FOLDER

            / workbook_path.stem
        )


        output_folder.mkdir(

            parents=True,

            exist_ok=True,
        )


        # ====================================================
        # WRITE MONTHLY OUTPUTS
        # ====================================================

        write_csv(

            output_folder
            / "wf_previous_day_transactions.csv",

            transactions,
        )


        write_csv(

            output_folder
            / "aic_previous_day_transactions.csv",

            aic_transactions,
        )


        write_csv(

            output_folder
            / "wf_previous_day_control_rows.csv",

            control_rows,
        )


        write_csv(

            output_folder
            / "wf_previous_day_account_summary.csv",

            account_summary_records,
        )


        with (
            output_folder
            / "wf_previous_day_validation.json"
        ).open(

            "w",

            encoding="utf-8",

        ) as file:


            json.dump(

                validation,

                file,

                indent=2,

                ensure_ascii=False,

                default=str,
            )


        # ====================================================
        # TERMINAL SUMMARY
        # ====================================================

        print(
            f"Full report transactions: "
            f"{len(transactions)}"
        )


        print(
            f"Bank accounts: "
            f"{len(account_summary_records)}"
        )


        print(
            f"Control/helper rows: "
            f"{len(control_rows)}"
        )


        print(
            f"AIC Disbursement transactions: "
            f"{len(aic_transactions)}"
        )


        print(
            f"  Main cash activity: "
            f"{aic_main_count}"
        )


        print(
            f"  ZBA: "
            f"{aic_zba_count}"
        )


        print(
            f"  Sweep: "
            f"{aic_sweep_count}"
        )


        print(
            f"  ZBA + Sweep: "
            f"{aic_zba_sweep_count}"
        )


        print(
            f"AIC client analysis fees: "
            f"{aic_fee_count}"
        )


        print(
            "AIC identical-visible extra rows "
            f"(preserved, NOT deduplicated): "
            f"{duplicate_visible_extra_rows}"
        )


        print(
            f"Structural warnings: "
            f"{len(warnings)}"
        )


        return (

            transactions,

            aic_transactions,

            control_rows,

            account_summary_records,

            validation,
        )


    finally:

        workbook_formula.close()

        workbook_value.close()


# ============================================================
# MAIN PROGRAM
# ============================================================

def main():

    print(
        "ASCOT WF PREVIOUS DAY SANITIZER"
    )


    print(
        "Evidence-based on actual Jan–Jul data"
    )


    # ========================================================
    # FIND PREVIOUS DAY WORKBOOKS
    # ========================================================

    files = list(

        RAW_FOLDER.glob(
            "WF Previous*2026.xlsx"
        )
    )


    if not files:

        raise FileNotFoundError(

            "No WF Previous Day transaction files "
            "were found in data/raw/."
        )


    # ========================================================
    # CHRONOLOGICAL ORDER
    # ========================================================

    files = sorted(

        files,

        key=extract_accounting_period,
    )


    print(
        f"\nFound {len(files)} workbook(s)."
    )


    print(
        "\nChronological processing order:"
    )


    for sequence, file_path in enumerate(

        files,

        start=1,
    ):


        print(

            f"  {sequence}. "
            f"{file_path.name}"
        )


    # ========================================================
    # CONSOLIDATED OUTPUT COLLECTIONS
    # ========================================================

    all_transactions = []

    all_aic_transactions = []

    all_control_rows = []

    all_account_summaries = []

    manifest = []


    # ========================================================
    # PROCESS EACH MONTH
    # ========================================================

    for sequence, workbook_path in enumerate(

        files,

        start=1,
    ):


        try:

            (
                transactions,

                aic_transactions,

                control_rows,

                account_summary,

                validation,

            ) = sanitize_one_workbook(

                workbook_path,

                sequence,
            )


            all_transactions.extend(
                transactions
            )


            all_aic_transactions.extend(
                aic_transactions
            )


            all_control_rows.extend(
                control_rows
            )


            all_account_summaries.extend(
                account_summary
            )


            manifest.append(

                {
                    "processing_sequence":
                        sequence,

                    "accounting_period":
                        accounting_period_label(
                            workbook_path
                        ),

                    "source_workbook":
                        workbook_path.name,

                    "status":
                        "success",

                    "header_row":
                        validation[
                            "header_row"
                        ],

                    "full_report_transaction_count":
                        validation[
                            "full_report_transaction_count"
                        ],

                    "account_count":
                        validation[
                            "account_count"
                        ],

                    "aic_transaction_count":
                        validation[
                            "aic_transaction_count"
                        ],

                    "aic_main_cash_activity_count":
                        validation[
                            "aic_main_cash_activity_count"
                        ],

                    "aic_zba_sweep_count":
                        validation[
                            "aic_zba_sweep_count"
                        ],

                    "aic_client_analysis_fee_count":
                        validation[
                            "aic_client_analysis_fee_count"
                        ],

                    "structural_warning_count":
                        validation[
                            "structural_warning_count"
                        ],
                }
            )


        except Exception as error:


            print(
                "\nERROR while processing "
                f"{workbook_path.name}:"
            )


            print(
                f"{type(error).__name__}: "
                f"{error}"
            )


            manifest.append(

                {
                    "processing_sequence":
                        sequence,

                    "accounting_period":
                        accounting_period_label(
                            workbook_path
                        ),

                    "source_workbook":
                        workbook_path.name,

                    "status":
                        "error",

                    "error_type":
                        type(error).__name__,

                    "error":
                        str(error),
                }
            )


    # ========================================================
    # CHRONOLOGICAL SORT OF CONSOLIDATED DATA
    # ========================================================

    all_transactions.sort(

        key=lambda record: (

            record[
                "processing_sequence"
            ],

            record[
                "source_row"
            ],
        )
    )


    all_aic_transactions.sort(

        key=lambda record: (

            record[
                "processing_sequence"
            ],

            record[
                "source_row"
            ],
        )
    )


    all_control_rows.sort(

        key=lambda record: (

            record[
                "processing_sequence"
            ],

            record[
                "source_row"
            ],
        )
    )


    all_account_summaries.sort(

        key=lambda record: (

            record[
                "processing_sequence"
            ],

            record[
                "account_number"
            ]
            or "",
        )
    )


    # ========================================================
    # WRITE CONSOLIDATED OUTPUTS
    # ========================================================

    write_csv(

        PROCESSED_FOLDER
        / "wf_previous_day_all_months_transactions.csv",

        all_transactions,
    )


    write_csv(

        PROCESSED_FOLDER
        / "aic_previous_day_all_months_transactions.csv",

        all_aic_transactions,
    )


    write_csv(

        PROCESSED_FOLDER
        / "wf_previous_day_all_months_control_rows.csv",

        all_control_rows,
    )


    write_csv(

        PROCESSED_FOLDER
        / "wf_previous_day_all_months_account_summary.csv",

        all_account_summaries,
    )


    with (
        PROCESSED_FOLDER
        / "wf_previous_day_processing_manifest.json"
    ).open(

        "w",

        encoding="utf-8",

    ) as file:


        json.dump(

            manifest,

            file,

            indent=2,

            ensure_ascii=False,
        )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    successful_months = sum(

        entry[
            "status"
        ] == "success"

        for entry
        in manifest
    )


    failed_months = (

        len(
            manifest
        )

        - successful_months
    )


    total_warnings = sum(

        entry.get(
            "structural_warning_count",
            0,
        )

        for entry
        in manifest

        if entry[
            "status"
        ] == "success"
    )


    print(
        "\n========================================"
    )


    print(
        "PREVIOUS DAY SANITIZATION COMPLETE"
    )


    print(
        "========================================"
    )


    print(
        f"Successful months: "
        f"{successful_months}"
    )


    print(
        f"Failed months: "
        f"{failed_months}"
    )


    print(
        f"Total bank transactions: "
        f"{len(all_transactions)}"
    )


    print(
        f"Total AIC Disbursement transactions: "
        f"{len(all_aic_transactions)}"
    )


    print(
        f"Total structural warnings: "
        f"{total_warnings}"
    )


    print(
        "\nConsolidated outputs:"
    )


    print(
        "data/processed/"
        "wf_previous_day_all_months_transactions.csv"
    )


    print(
        "data/processed/"
        "aic_previous_day_all_months_transactions.csv"
    )


    print(
        "data/processed/"
        "wf_previous_day_all_months_control_rows.csv"
    )


    print(
        "data/processed/"
        "wf_previous_day_all_months_account_summary.csv"
    )


    print(
        "data/processed/"
        "wf_previous_day_processing_manifest.json"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()