# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# AIC IMS SANITIZER
# ============================================================
#
# IMPORTANT:
#
# This sanitizer was designed AFTER inspecting the actual
# January–July 2026 AIC IMS worksheets.
#
# It does NOT infer spreadsheet structure from the SOP or
# process documentation.
#
#
# ACTUAL DATA STRUCTURE OBSERVED
# ------------------------------------------------------------
#
# AIC IMS contains 13 columns:
#
#   A  TransactionDate
#   B  CheckOrRef
#   C  Method
#   D  PaymentType
#   E  Description
#   F  Debit
#   G  Credit
#   H  Date Cleared
#   I  Account
#   J  Cost Center
#   K  Description
#   L  Amount
#   M  Backup
#
#
# The important distinction is:
#
#   F/G = SOURCE TRANSACTION AMOUNT
#
# while:
#
#   I/J/K/L/M = accounting/workpaper allocation information
#
#
# We observed THREE important kinds of rows:
#
# 1. SOURCE TRANSACTION
#
#    Has a real Debit or Credit.
#
#
# 2. SOURCE TRANSACTION WITH INHERITED METADATA
#
#    Observed in January.
#
#    Example:
#
#       A-D blank
#       E description populated
#       G credit populated
#       H cleared date populated
#       I/J accounting codes populated
#
#    These are real additional transaction lines.
#
#    They are NOT allocation rows.
#
#
# 3. ALLOCATION / SUPPLEMENTAL ROW
#
#    Has no Debit/Credit but contains accounting allocation
#    information in I-M.
#
#    These appear particularly from April onward.
#
#
# CRITICAL OBSERVATION
# ------------------------------------------------------------
#
# Allocation rows do NOT always belong to the row immediately
# above them.
#
# Example observed in June:
#
#   row 115
#       West Virginia allocation $17.50
#
# actually belongs to:
#
#   row 116
#       West Virginia source transaction $1,067.50
#
# not row 114.
#
#
# Therefore:
#
#       adjacency alone is NOT a safe linkage rule.
#
#
# We instead link an allocation block using:
#
#       source transaction amount
#               vs.
#       sum of workpaper allocation amounts
#
# If the amounts reconcile, that provides strong accounting
# evidence for the linkage.
#
#
# This exact method successfully resolves all observed
# allocation blocks from Jan–Jul with zero ambiguous blocks.
#
#
# OUTPUTS
# ------------------------------------------------------------
#
# For each month:
#
#   aic_ims_rows.csv
#       every meaningful IMS row, normalized
#
#   aic_ims_transactions.csv
#       actual source transactions
#
#   aic_ims_allocations.csv
#       accounting allocation lines linked to transactions
#
#   aic_ims_validation.json
#       structural QA results
#
#
# Across all months:
#
#   aic_ims_all_months_rows.csv
#   aic_ims_all_months_transactions.csv
#   aic_ims_all_months_allocations.csv
#   aic_ims_processing_manifest.json
#
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

# csv
#     writes our normalized machine-readable outputs.
import csv


# json
#     writes structural validation reports.
import json


# re
#     handles filename dates and text/date pattern matching.
import re


# zipfile
#     .xlsx files are actually ZIP archives containing XML.
#
# We intentionally read the workbook this way rather than
# loading the entire workbook into memory.
#
# The Resource Pro files are very large internally, and our
# earlier normal Excel-loading approach was terminated because
# of memory pressure.
import zipfile


# ElementTree
#     reads the XML inside the XLSX file.
import xml.etree.ElementTree as ET


# Counter
#     summarizes row types and formula patterns.
from collections import Counter


# datetime / timedelta
#     converts Excel serial dates into real dates.
from datetime import datetime, timedelta


# Path
#     handles project file paths.
from pathlib import Path


# ============================================================
# PROJECT FOLDERS
# ============================================================

# Original Resource Pro files.
RAW_FOLDER = Path(
    "data/raw"
)


# Sanitized outputs.
PROCESSED_FOLDER = Path(
    "data/processed"
)


PROCESSED_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# ACCOUNTING TOLERANCE
# ============================================================
#
# Excel floating-point values sometimes appear as:
#
#   260200.15000000002
#
# instead of:
#
#   260200.15
#
# Therefore we allow a two-cent tolerance when determining
# whether allocations reconcile to the source transaction.
# ============================================================

TOLERANCE = 0.02


# ============================================================
# EXPECTED HEADER
# ============================================================
#
# This is based on the ACTUAL Jan–Jul AIC IMS files.
#
# It was identical across every workbook inspected.
# ============================================================

EXPECTED_HEADERS = [

    "TransactionDate",

    "CheckOrRef",

    "Method",

    "PaymentType",

    "Description",

    "Debit",

    "Credit",

    "Date Cleared",

    "Account",

    "Cost Center",

    "Description",

    " Amount",

    "Backup",
]


# ============================================================
# XLSX XML NAMESPACES
# ============================================================

XML_NS = {

    "a":
        (
            "http://schemas.openxmlformats.org/"
            "spreadsheetml/2006/main"
        )
}


RELATIONSHIP_ID_ATTRIBUTE = (

    "{http://schemas.openxmlformats.org/"
    "officeDocument/2006/relationships}id"
)


# ============================================================
# 1. TEXT HELPERS
# ============================================================

def normalize_text(value):
    """
    Convert a value to trimmed text while preserving case.

    Multiple spaces become one space.
    """

    if value is None:

        return ""


    return re.sub(

        r"\s+",

        " ",

        str(value).strip(),
    )


def normalize_lower(value):
    """
    Same as normalize_text(), but lowercase.
    """

    return normalize_text(
        value
    ).lower()


# ============================================================
# 2. ACCOUNTING PERIOD
# ============================================================

def extract_accounting_period(
    file_path,
):
    """
    Extract the month/year from filenames such as:

        January 2026 Resource Pro Cash.xlsx

    and return a real datetime.

    This enforces the ASCOT-wide chronological processing
    rule we already locked in.
    """

    match = re.match(

        r"^([A-Za-z]+)\s+(\d{4})\b",

        file_path.stem,
    )


    if not match:

        raise ValueError(

            "Cannot determine accounting period from "
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
    Convert the accounting period to:

        YYYY-MM
    """

    return extract_accounting_period(
        file_path
    ).strftime(
        "%Y-%m"
    )


# ============================================================
# 3. EXCEL COLUMN NUMBER
# ============================================================

def column_number_from_reference(
    cell_reference,
):
    """
    Convert an Excel reference such as:

        A1
        G23
        M120

    into its numeric column:

        A -> 1
        G -> 7
        M -> 13
    """

    match = re.match(

        r"([A-Z]+)",

        cell_reference,
    )


    letters = match.group(1)


    number = 0


    for letter in letters:

        number = (

            number * 26

            + ord(letter)

            - 64
        )


    return number


# ============================================================
# 4. LOAD SHARED STRINGS
# ============================================================
#
# Excel often stores text values in:
#
#     xl/sharedStrings.xml
#
# worksheet cells then contain only a numeric reference to
# that text.
# ============================================================

def read_shared_strings(
    zip_file,
):

    shared_string_path = (
        "xl/sharedStrings.xml"
    )


    if (
        shared_string_path
        not in zip_file.namelist()
    ):

        return []


    shared_strings = []


    # Stream rather than loading the whole XML tree.
    with zip_file.open(
        shared_string_path
    ) as xml_file:


        for event, element in ET.iterparse(

            xml_file,

            events=("end",),
        ):


            if not element.tag.endswith(
                "}si"
            ):

                continue


            text_parts = []


            for text_element in element.iter(

                (
                    "{http://schemas.openxmlformats.org/"
                    "spreadsheetml/2006/main}t"
                )
            ):

                text_parts.append(
                    text_element.text
                    or ""
                )


            shared_strings.append(

                "".join(
                    text_parts
                )
            )


            element.clear()


    return shared_strings


# ============================================================
# 5. MAP SHEET NAMES TO XML FILES
# ============================================================

def get_sheet_map(
    zip_file,
):
    """
    Find the underlying XML file corresponding to each
    Excel worksheet name.
    """

    workbook_xml = ET.fromstring(

        zip_file.read(
            "xl/workbook.xml"
        )
    )


    relationships_xml = ET.fromstring(

        zip_file.read(
            "xl/_rels/workbook.xml.rels"
        )
    )


    relationship_map = {}


    for relationship in relationships_xml:

        relationship_map[
            relationship.attrib["Id"]
        ] = relationship.attrib[
            "Target"
        ]


    sheet_map = {}


    sheets_element = workbook_xml.find(

        "a:sheets",

        XML_NS,
    )


    for sheet in sheets_element:

        sheet_name = sheet.attrib[
            "name"
        ]


        relationship_id = sheet.attrib[
            RELATIONSHIP_ID_ATTRIBUTE
        ]


        target = relationship_map[
            relationship_id
        ]


        # Relationship paths may be relative.
        if target.startswith("/"):

            target = target.lstrip("/")


        else:

            target = (

                "xl/"

                + target.lstrip("/")
            )


        sheet_map[
            sheet_name
        ] = target


    return sheet_map


# ============================================================
# 6. READ ONE EXCEL CELL
# ============================================================

def read_cell(
    cell,
    shared_strings,
):
    """
    Extract:

        value
        formula information

    from one XLSX XML cell.

    We preserve formula metadata because K/L use formulas
    extensively, but formula presence will NOT determine
    transaction structure.
    """

    cell_type = cell.attrib.get(
        "t"
    )


    value_element = cell.find(

        "a:v",

        XML_NS,
    )


    formula_element = cell.find(

        "a:f",

        XML_NS,
    )


    inline_string = cell.find(

        "a:is",

        XML_NS,
    )


    value = None


    # --------------------------------------------------------
    # SHARED STRING
    # --------------------------------------------------------

    if (
        cell_type == "s"
        and value_element is not None
    ):

        index = int(
            value_element.text
        )


        if index < len(
            shared_strings
        ):

            value = (
                shared_strings[
                    index
                ]
            )


    # --------------------------------------------------------
    # INLINE STRING
    # --------------------------------------------------------

    elif (
        cell_type == "inlineStr"
        and inline_string is not None
    ):

        pieces = []


        for text_element in (
            inline_string.iter(

                (
                    "{http://schemas.openxmlformats.org/"
                    "spreadsheetml/2006/main}t"
                )
            )
        ):

            pieces.append(
                text_element.text
                or ""
            )


        value = "".join(
            pieces
        )


    # --------------------------------------------------------
    # FORMULA RETURNING TEXT
    # --------------------------------------------------------

    elif (
        cell_type == "str"
        and value_element is not None
    ):

        value = (
            value_element.text
        )


    # --------------------------------------------------------
    # BOOLEAN
    # --------------------------------------------------------

    elif (
        cell_type == "b"
        and value_element is not None
    ):

        value = bool(

            int(
                value_element.text
            )
        )


    # --------------------------------------------------------
    # NUMERIC
    # --------------------------------------------------------

    elif value_element is not None:

        try:

            value = float(
                value_element.text
            )


            # Keep clean integers as integers.
            if value.is_integer():

                value = int(
                    value
                )


        except Exception:

            value = (
                value_element.text
            )


    # --------------------------------------------------------
    # FORMULA METADATA
    # --------------------------------------------------------

    return {

        "value":
            value,

        "formula_text":
            (
                None
                if formula_element is None
                else formula_element.text
            ),

        "formula_type":
            (
                None
                if formula_element is None
                else formula_element.attrib.get(
                    "t"
                )
            ),

        "formula_shared_index":
            (
                None
                if formula_element is None
                else formula_element.attrib.get(
                    "si"
                )
            ),
    }


# ============================================================
# 7. READ AIC IMS ROWS
# ============================================================

def read_aic_ims_rows(
    workbook_path,
):
    """
    Stream the first 13 columns of the actual AIC IMS sheet.

    We do NOT load the entire workbook into memory.
    """

    with zipfile.ZipFile(
        workbook_path
    ) as zip_file:


        sheet_map = get_sheet_map(
            zip_file
        )


        if "AIC IMS" not in sheet_map:

            raise ValueError(

                f"{workbook_path.name} does not "
                "contain an AIC IMS sheet."
            )


        shared_strings = (
            read_shared_strings(
                zip_file
            )
        )


        sheet_xml_path = (
            sheet_map[
                "AIC IMS"
            ]
        )


        rows = []


        with zip_file.open(
            sheet_xml_path
        ) as xml_file:


            for event, element in (
                ET.iterparse(

                    xml_file,

                    events=("end",),
                )
            ):


                if not element.tag.endswith(
                    "}row"
                ):

                    continue


                row_number = int(

                    element.attrib.get(
                        "r",
                        "0",
                    )
                )


                cells = {}


                for cell in element.findall(

                    "a:c",

                    XML_NS,
                ):


                    reference = (
                        cell.attrib.get(
                            "r",
                            ""
                        )
                    )


                    column_number = (
                        column_number_from_reference(
                            reference
                        )
                    )


                    # AIC IMS uses A:M.
                    if column_number > 13:

                        continue


                    cells[
                        column_number
                    ] = read_cell(

                        cell,

                        shared_strings,
                    )


                rows.append(

                    (
                        row_number,
                        cells,
                    )
                )


                element.clear()


    return rows


# ============================================================
# 8. TURN CELL DICTIONARY INTO A:M VALUES
# ============================================================

def row_values(
    cells,
):
    """
    Return columns A through M in order.
    """

    return [

        cells.get(
            column_number,
            {},
        ).get(
            "value"
        )

        for column_number
        in range(
            1,
            14,
        )
    ]


# ============================================================
# 9. EXCEL SERIAL DATE
# ============================================================

def excel_serial_to_iso(
    value,
):
    """
    Convert Excel numeric date/time serial into an ISO string.

    Examples:

        46022
            -> 2025-12-31

        fractional dates
            -> YYYY-MM-DD HH:MM:SS
    """

    if not isinstance(
        value,
        (int, float),
    ):

        return None


    excel_origin = datetime(
        1899,
        12,
        30,
    )


    converted = (

        excel_origin

        + timedelta(
            days=float(
                value
            )
        )
    )


    if (
        converted.time()
        == datetime.min.time()
    ):

        return (
            converted.date()
            .isoformat()
        )


    return converted.isoformat(

        sep=" ",

        timespec="seconds",
    )


# ============================================================
# 10. NUMERIC CHECK
# ============================================================

def is_numeric(
    value,
):

    return (

        isinstance(
            value,
            (int, float),
        )

        and not isinstance(
            value,
            bool,
        )
    )


# ============================================================
# 11. SOURCE TRANSACTION AMOUNT
# ============================================================

def get_signed_source_amount(
    values,
):
    """
    Debit/Credit represent the actual source transaction.

    Observed convention:

        normal outgoing payment
            Credit is negative

        void
            Debit is positive
    """

    debit = values[5]

    credit = values[6]


    if is_numeric(
        debit
    ):

        return float(
            debit
        )


    if is_numeric(
        credit
    ):

        return float(
            credit
        )


    return None


# ============================================================
# 12. EXPECTED WORKPAPER AMOUNT
# ============================================================

def expected_workpaper_amount(
    values,
):
    """
    Column L normally reverses the sign of the source amount.

    Examples observed:

        source Credit = -100
        workpaper Amount = +100

        source Debit = +100  (void)
        workpaper Amount = -100
    """

    signed_source = (
        get_signed_source_amount(
            values
        )
    )


    if signed_source is None:

        return None


    return -signed_source


# ============================================================
# 13. WORKPAPER ALLOCATION AMOUNT
# ============================================================

def get_workpaper_amount(
    values,
):
    """
    Numeric value from column L.
    """

    amount = values[11]


    if is_numeric(
        amount
    ):

        return float(
            amount
        )


    return None


# ============================================================
# 14. CLASSIFY ACTUAL ROW TYPE
# ============================================================

def classify_row(
    values,
):
    """
    Classify the row based on the actual IMS data structure.

    THE KEY RULE:

        Debit/Credit determines whether a row carries a real
        source transaction.

    We do NOT use A-D alone.
    """

    (
        transaction_date,
        check_or_ref,
        method,
        payment_type,
        description,
        debit,
        credit,
        date_cleared,
        account,
        cost_center,
        workpaper_description,
        workpaper_amount,
        backup,
    ) = values


    # --------------------------------------------------------
    # BALANCE FORWARD
    # --------------------------------------------------------
    #
    # Position is NOT reliable.
    #
    # April places Balance Forward at row 168.
    # --------------------------------------------------------

    if (
        normalize_lower(
            description
        ) == "balance forward"

        or normalize_text(
            method
        ).upper() == "Z"
    ):

        return "balance_forward"


    # --------------------------------------------------------
    # SOURCE TRANSACTION
    # --------------------------------------------------------

    source_amount = (
        get_signed_source_amount(
            values
        )
    )


    if source_amount is not None:


        # ----------------------------------------------------
        # VOID
        # ----------------------------------------------------

        if (

            normalize_text(
                method
            ).upper() == "V"

            or normalize_lower(
                description
            ) == "void"

            or normalize_lower(
                check_or_ref
            ) == "void"
        ):

            return "void_transaction"


        # ----------------------------------------------------
        # NORMAL SOURCE TRANSACTION
        # ----------------------------------------------------

        if any(

            normalize_text(
                value
            ) != ""

            for value in [

                transaction_date,

                check_or_ref,

                method,

                payment_type,
            ]
        ):

            return "source_transaction"


        # ----------------------------------------------------
        # SOURCE TRANSACTION WITH INHERITED METADATA
        # ----------------------------------------------------
        #
        # Seen in January:
        #
        # A-D blank, but E/G/H/I/J contain a real transaction.
        # ----------------------------------------------------

        return (
            "source_transaction_inherited_metadata"
        )


    # --------------------------------------------------------
    # ALLOCATION / SUPPLEMENTAL ROW
    # --------------------------------------------------------
    #
    # No real Debit/Credit exists.
    #
    # Accounting information may be populated in I-M.
    #
    # Some rows also repeat fields such as PaymentType or
    # Date Cleared, so A-D cannot safely determine structure.
    # --------------------------------------------------------

    if any(

        normalize_text(
            value
        ) != ""

        for value in [

            transaction_date,

            check_or_ref,

            method,

            payment_type,

            description,

            date_cleared,

            account,

            cost_center,

            workpaper_description,

            workpaper_amount,

            backup,
        ]
    ):

        return (
            "allocation_or_supplemental"
        )


    return "blank"


# ============================================================
# 15. PARSE DATE CLEARED / STATUS FIELD
# ============================================================

def parse_date_cleared(
    raw_value,
):
    """
    Column H is NOT purely a date.

    Actual examples include:

        2026/07/29

        2026/06/17, 2026/06/18

        Outstanding Check

        Outstanding ACH

        Same Month Void

        January Month Void Check #...

        RETURNED 4/28/26

    Therefore we ALWAYS preserve the raw text.
    """

    text = normalize_text(
        raw_value
    )


    lowercase = text.lower()


    date_matches = re.findall(

        r"\b\d{4}/\d{2}/\d{2}\b",

        text,
    )


    if not text:

        status = "blank"


    elif "returned" in lowercase:

        status = "returned"


    elif "outstanding" in lowercase:

        status = "outstanding"


    elif "same month void" in lowercase:

        status = "same_month_void"


    elif date_matches:

        if len(
            date_matches
        ) == 1:

            status = "cleared"


        else:

            status = (
                "multiple_cleared_dates"
            )


    elif "void" in lowercase:

        status = "void_reference"


    else:

        status = "other_text"


    parsed_dates = (

        "|".join(
            date_matches
        )

        if date_matches

        else None
    )


    return (
        status,
        parsed_dates,
    )


# ============================================================
# 16. PRESERVE ACCOUNT/COST CODES AS TEXT
# ============================================================

def safe_code(
    value,
):
    """
    Codes should not be treated as arithmetic numbers.
    """

    if value is None:

        return None


    if (
        is_numeric(
            value
        )

        and float(
            value
        ).is_integer()
    ):

        return str(

            int(
                value
            )
        )


    text = str(
        value
    ).strip()


    return (
        text
        if text
        else None
    )


# ============================================================
# 17. WRITE CSV
# ============================================================

def write_csv(
    path,
    records,
):
    """
    Write a list of dictionaries to CSV.
    """

    if not records:

        path.write_text(

            "",

            encoding="utf-8-sig",
        )

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
# 18. SANITIZE ONE MONTH
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
    # READ ACTUAL AIC IMS XML
    # ========================================================

    raw_rows = read_aic_ims_rows(
        workbook_path
    )


    # ========================================================
    # VALIDATE ACTUAL HEADER
    # ========================================================

    header_row = None


    for row_number, cells in raw_rows[:5]:

        values = row_values(
            cells
        )


        if (

            [
                normalize_text(
                    value
                )

                for value in values
            ]

            ==

            [
                normalize_text(
                    value
                )

                for value
                in EXPECTED_HEADERS
            ]
        ):

            header_row = (
                row_number
            )

            break


    if header_row is None:

        raise ValueError(

            "Expected Jan–Jul AIC IMS "
            "13-column header was not found."
        )


    print(
        f"Detected header row: "
        f"{header_row}"
    )


    # ========================================================
    # FIRST PASS:
    # NORMALIZE EVERY MEANINGFUL ROW
    # ========================================================

    normalized_rows = []


    formula_columns = Counter()


    formula_status_k = Counter()

    formula_status_l = Counter()


    balance_forward_rows = []


    source_continuation_ambiguities = []


    unexpected_rows = []


    # Most recent normal source transaction.
    #
    # Used only for the January pattern where A-D are blank
    # but the row is still a real transaction.
    last_parent_metadata = None


    for row_number, cells in raw_rows:


        if row_number <= header_row:

            continue


        values = row_values(
            cells
        )


        # Ignore completely empty rows.
        if not any(

            normalize_text(
                value
            ) != ""

            for value
            in values
        ):

            continue


        row_kind = classify_row(
            values
        )


        if row_kind == "blank":

            continue


        # ====================================================
        # FORMULA OBSERVATION
        # ====================================================
        #
        # Actual files contain formulas only in K/L.
        #
        # We preserve their existence for QA but never use
        # them to determine transaction structure.
        # ====================================================

        for column_number, cell in (
            cells.items()
        ):


            formula_present = (

                cell.get(
                    "formula_text"
                ) is not None

                or

                cell.get(
                    "formula_type"
                ) is not None
            )


            if formula_present:

                formula_columns[
                    column_number
                ] += 1


        # ----------------------------------------------------
        # K formula/static/blank
        # ----------------------------------------------------

        for (
            column_number,
            status_counter,
        ) in [

            (
                11,
                formula_status_k,
            ),

            (
                12,
                formula_status_l,
            ),
        ]:


            cell = cells.get(
                column_number
            )


            if cell is None:

                status_counter[
                    "blank"
                ] += 1


            else:

                formula_present = (

                    cell.get(
                        "formula_text"
                    ) is not None

                    or

                    cell.get(
                        "formula_type"
                    ) is not None
                )


                value_present = (

                    normalize_text(
                        cell.get(
                            "value"
                        )
                    ) != ""
                )


                if formula_present:

                    status_counter[
                        "formula"
                    ] += 1


                elif value_present:

                    status_counter[
                        "static"
                    ] += 1


                else:

                    status_counter[
                        "blank"
                    ] += 1


        # ====================================================
        # UNPACK A:M
        # ====================================================

        (
            transaction_date,
            check_or_ref,
            method,
            payment_type,
            source_description,
            debit,
            credit,
            date_cleared,
            account,
            cost_center,
            workpaper_description,
            workpaper_amount,
            backup,
        ) = values


        inherited_from_row = None


        # ====================================================
        # BALANCE FORWARD
        # ====================================================

        if row_kind == "balance_forward":

            balance_forward_rows.append(
                row_number
            )


        # ====================================================
        # ORDINARY SOURCE ROW
        # ====================================================

        elif row_kind in {

            "source_transaction",

            "void_transaction",
        }:


            last_parent_metadata = {

                "row":
                    row_number,

                "transaction_date":
                    transaction_date,

                "check_or_ref":
                    check_or_ref,

                "method":
                    method,

                "payment_type":
                    payment_type,

                "description":
                    normalize_text(
                        source_description
                    ),
            }


        # ====================================================
        # JANUARY SOURCE CONTINUATION
        # ====================================================
        #
        # Actual January rows show:
        #
        # A-D blank
        # E/G/H/I/J populated
        #
        # In all six observed rows, E matches the immediately
        # preceding source transaction's description.
        #
        # Therefore we safely inherit A-D while preserving the
        # fact that this metadata was inherited.
        # ====================================================

        elif (
            row_kind
            == "source_transaction_inherited_metadata"
        ):


            if (

                last_parent_metadata

                and normalize_text(
                    source_description
                )
                == last_parent_metadata[
                    "description"
                ]
            ):


                inherited_from_row = (
                    last_parent_metadata[
                        "row"
                    ]
                )


                transaction_date = (
                    last_parent_metadata[
                        "transaction_date"
                    ]
                )


                check_or_ref = (
                    last_parent_metadata[
                        "check_or_ref"
                    ]
                )


                method = (
                    last_parent_metadata[
                        "method"
                    ]
                )


                payment_type = (
                    last_parent_metadata[
                        "payment_type"
                    ]
                )


            else:

                # Do NOT guess.
                source_continuation_ambiguities.append(
                    row_number
                )


        # ====================================================
        # CLEARED STATUS
        # ====================================================

        (
            cleared_status,
            cleared_dates,
        ) = parse_date_cleared(
            date_cleared
        )


        # ====================================================
        # TRANSACTION DATE
        # ====================================================

        if is_numeric(
            transaction_date
        ):

            transaction_datetime = (
                excel_serial_to_iso(
                    transaction_date
                )
            )


        else:

            transaction_datetime = (

                normalize_text(
                    transaction_date
                )

                or None
            )


        # ====================================================
        # SOURCE AMOUNT
        # ====================================================

        signed_source_amount = (
            get_signed_source_amount(
                values
            )
        )


        expected_amount = (
            expected_workpaper_amount(
                values
            )
        )


        # ====================================================
        # TRANSACTION ID
        # ====================================================

        if row_kind in {

            "source_transaction",

            "source_transaction_inherited_metadata",

            "void_transaction",
        }:


            transaction_id = (

                f"IMS-{period}-"
                f"R{row_number}"
            )


        else:

            transaction_id = None


        # ====================================================
        # FORMULA INFORMATION
        # ====================================================

        description_formula_cell = (
            cells.get(
                11
            )
        )


        amount_formula_cell = (
            cells.get(
                12
            )
        )


        description_formula_present = (

            bool(
                description_formula_cell
            )

            and (

                description_formula_cell.get(
                    "formula_text"
                ) is not None

                or

                description_formula_cell.get(
                    "formula_type"
                ) is not None
            )
        )


        amount_formula_present = (

            bool(
                amount_formula_cell
            )

            and (

                amount_formula_cell.get(
                    "formula_text"
                ) is not None

                or

                amount_formula_cell.get(
                    "formula_type"
                ) is not None
            )
        )


        # ====================================================
        # NORMALIZED ROW RECORD
        # ====================================================

        record = {

            "accounting_period":
                period,

            "processing_sequence":
                processing_sequence,

            "source_workbook":
                workbook_path.name,

            "source_sheet":
                "AIC IMS",

            "source_row":
                row_number,

            "row_kind":
                row_kind,

            "transaction_id":
                transaction_id,

            "inherited_metadata_from_row":
                inherited_from_row,

            "transaction_datetime":
                transaction_datetime,

            "check_or_ref":
                safe_code(
                    check_or_ref
                ),

            "method":
                (
                    normalize_text(
                        method
                    )
                    or None
                ),

            "payment_type":
                (
                    normalize_text(
                        payment_type
                    )
                    or None
                ),

            "source_description":
                (
                    normalize_text(
                        source_description
                    )
                    or None
                ),

            "source_debit":
                (
                    float(
                        debit
                    )
                    if is_numeric(
                        debit
                    )
                    else None
                ),

            "source_credit":
                (
                    float(
                        credit
                    )
                    if is_numeric(
                        credit
                    )
                    else None
                ),

            "source_signed_amount":
                signed_source_amount,

            "expected_workpaper_amount":
                expected_amount,

            # Preserve the raw H value.
            "date_cleared_raw":
                (
                    normalize_text(
                        date_cleared
                    )
                    or None
                ),

            "cleared_status":
                cleared_status,

            "cleared_dates":
                cleared_dates,

            "account_raw":
                safe_code(
                    account
                ),

            "cost_center_raw":
                safe_code(
                    cost_center
                ),

            "workpaper_description_raw":
                (
                    normalize_text(
                        workpaper_description
                    )
                    or None
                ),

            # Preserve raw value because it can contain N/A.
            "workpaper_amount_raw":
                workpaper_amount,

            "workpaper_amount_numeric":
                get_workpaper_amount(
                    values
                ),

            "backup_raw":
                (
                    normalize_text(
                        backup
                    )
                    or None
                ),

            "description_formula_present":
                description_formula_present,

            "description_formula_text":
                (
                    None
                    if not description_formula_cell
                    else description_formula_cell.get(
                        "formula_text"
                    )
                ),

            "amount_formula_present":
                amount_formula_present,

            "amount_formula_text":
                (
                    None
                    if not amount_formula_cell
                    else amount_formula_cell.get(
                        "formula_text"
                    )
                ),
        }


        normalized_rows.append(
            record
        )


    # ========================================================
    # SOURCE TRANSACTIONS
    # ========================================================
    #
    # Balance Forward is intentionally NOT a current-period
    # transaction.
    #
    # Allocation-only rows are also excluded here.
    # ========================================================

    transactions = [

        dict(
            record
        )

        for record
        in normalized_rows

        if record[
            "row_kind"
        ] in {

            "source_transaction",

            "source_transaction_inherited_metadata",

            "void_transaction",
        }
    ]


    # ========================================================
    # 19. LINK SUPPLEMENTAL ALLOCATION BLOCKS
    # ========================================================
    #
    # We observed that allocation rows form contiguous blocks
    # between source transactions.
    #
    # Usually the block belongs to the previous transaction.
    #
    # BUT June row 115 belongs to the NEXT transaction.
    #
    # Therefore we evaluate BOTH previous and next.
    #
    #
    # Evidence:
    #
    #     source expected workpaper amount
    #
    #             versus
    #
    #     parent-row L amount
    #       + allocation-block L amounts
    #
    #
    # If they reconcile within two cents, we have accounting
    # evidence for the linkage.
    # ========================================================

    source_positions = [

        index

        for index, record
        in enumerate(
            normalized_rows
        )

        if record[
            "row_kind"
        ] in {

            "source_transaction",

            "source_transaction_inherited_metadata",

            "void_transaction",
        }
    ]


    allocation_block_results = []


    index = 0


    while index < len(
        normalized_rows
    ):


        if (
            normalized_rows[
                index
            ][
                "row_kind"
            ]
            != "allocation_or_supplemental"
        ):

            index += 1

            continue


        # ----------------------------------------------------
        # FIND END OF THIS CONTIGUOUS BLOCK
        # ----------------------------------------------------

        end_index = index


        while (

            end_index
            < len(
                normalized_rows
            )

            and

            normalized_rows[
                end_index
            ][
                "row_kind"
            ]
            == "allocation_or_supplemental"
        ):

            end_index += 1


        allocation_block = (

            normalized_rows[
                index:end_index
            ]
        )


        # ----------------------------------------------------
        # PREVIOUS SOURCE TRANSACTION
        # ----------------------------------------------------

        previous_positions = [

            position

            for position
            in source_positions

            if position < index
        ]


        previous_position = (

            max(
                previous_positions
            )

            if previous_positions

            else None
        )


        previous_transaction = (

            normalized_rows[
                previous_position
            ]

            if previous_position
            is not None

            else None
        )


        # ----------------------------------------------------
        # NEXT SOURCE TRANSACTION
        # ----------------------------------------------------

        next_positions = [

            position

            for position
            in source_positions

            if position
            >= end_index
        ]


        next_position = (

            min(
                next_positions
            )

            if next_positions

            else None
        )


        next_transaction = (

            normalized_rows[
                next_position
            ]

            if next_position
            is not None

            else None
        )


        # ----------------------------------------------------
        # BLOCK TOTAL
        # ----------------------------------------------------

        block_amount_total = sum(

            (
                record[
                    "workpaper_amount_numeric"
                ]
                or 0.0
            )

            for record
            in allocation_block
        )


        # ----------------------------------------------------
        # DOES BLOCK RECONCILE TO A CANDIDATE TRANSACTION?
        # ----------------------------------------------------

        def candidate_reconciles(
            transaction,
        ):


            if transaction is None:

                return (
                    False,
                    None,
                )


            expected = transaction.get(
                "expected_workpaper_amount"
            )


            if expected is None:

                return (
                    False,
                    None,
                )


            primary_allocation = (

                transaction.get(
                    "workpaper_amount_numeric"
                )

                or 0.0
            )


            difference = (

                primary_allocation

                + block_amount_total

                - expected
            )


            return (

                abs(
                    difference
                )
                <= TOLERANCE,

                difference,
            )


        (
            previous_matches,
            previous_difference,
        ) = candidate_reconciles(
            previous_transaction
        )


        (
            next_matches,
            next_difference,
        ) = candidate_reconciles(
            next_transaction
        )


        target_transaction = None

        linkage_basis = None


        # ----------------------------------------------------
        # UNIQUE PREVIOUS MATCH
        # ----------------------------------------------------

        if (

            previous_matches

            and not next_matches
        ):

            target_transaction = (
                previous_transaction
            )

            linkage_basis = (
                "amount_reconciliation_previous"
            )


        # ----------------------------------------------------
        # UNIQUE NEXT MATCH
        # ----------------------------------------------------
        #
        # This captures June row 115 correctly.
        # ----------------------------------------------------

        elif (

            next_matches

            and not previous_matches
        ):

            target_transaction = (
                next_transaction
            )

            linkage_basis = (
                "amount_reconciliation_next"
            )


        # ----------------------------------------------------
        # BOTH MATCH
        # ----------------------------------------------------
        #
        # Not observed in Jan–Jul, but we handle it
        # conservatively.
        # ----------------------------------------------------

        elif (

            previous_matches

            and next_matches
        ):


            descriptions = [

                record[
                    "workpaper_description_raw"
                ]

                for record
                in allocation_block

                if record[
                    "workpaper_description_raw"
                ]
            ]


            previous_description = (

                previous_transaction.get(
                    "source_description"
                )

                or

                previous_transaction.get(
                    "workpaper_description_raw"
                )
            )


            next_description = (

                next_transaction.get(
                    "source_description"
                )

                or

                next_transaction.get(
                    "workpaper_description_raw"
                )
            )


            previous_description_matches = (

                bool(
                    descriptions
                )

                and all(

                    description
                    == previous_description

                    for description
                    in descriptions
                )
            )


            next_description_matches = (

                bool(
                    descriptions
                )

                and all(

                    description
                    == next_description

                    for description
                    in descriptions
                )
            )


            if (

                previous_description_matches

                and not
                next_description_matches
            ):

                target_transaction = (
                    previous_transaction
                )

                linkage_basis = (
                    "amount_and_description_previous"
                )


            elif (

                next_description_matches

                and not
                previous_description_matches
            ):

                target_transaction = (
                    next_transaction
                )

                linkage_basis = (
                    "amount_and_description_next"
                )


        # ----------------------------------------------------
        # APPLY LINKAGE
        # ----------------------------------------------------

        for allocation_record in (
            allocation_block
        ):

            allocation_record[
                "linked_transaction_id"
            ] = (

                None
                if target_transaction
                is None

                else target_transaction[
                    "transaction_id"
                ]
            )


            allocation_record[
                "allocation_link_basis"
            ] = (
                linkage_basis
            )


        allocation_block_results.append(

            {
                "source_rows":
                    [
                        record[
                            "source_row"
                        ]

                        for record
                        in allocation_block
                    ],

                "target_transaction_id":
                    (
                        None
                        if target_transaction
                        is None

                        else target_transaction[
                            "transaction_id"
                        ]
                    ),

                "target_source_row":
                    (
                        None
                        if target_transaction
                        is None

                        else target_transaction[
                            "source_row"
                        ]
                    ),

                "linkage_basis":
                    linkage_basis,

                "previous_difference":
                    previous_difference,

                "next_difference":
                    next_difference,
            }
        )


        index = end_index


    # ========================================================
    # 20. CREATE NORMALIZED ALLOCATION TABLE
    # ========================================================
    #
    # Every source transaction row may itself contain the first
    # accounting allocation in columns I-M.
    #
    # Supplemental rows add further allocations.
    # ========================================================

    allocations = []


    allocation_sequence = Counter()


    # ========================================================
    # PRIMARY ALLOCATION ON SOURCE TRANSACTION ROW
    # ========================================================

    for transaction in transactions:


        has_accounting_information = any(

            transaction.get(
                field_name
            )
            not in {
                None,
                "",
            }

            for field_name in [

                "account_raw",

                "cost_center_raw",

                "workpaper_description_raw",

                "workpaper_amount_raw",

                "backup_raw",
            ]
        )


        if not has_accounting_information:

            continue


        allocation_amount = (
            transaction[
                "workpaper_amount_numeric"
            ]
        )


        amount_source = (
            "workpaper_amount"
        )


        allocation_description = (
            transaction[
                "workpaper_description_raw"
            ]
        )


        description_source = (
            "workpaper_description"
        )


        # ----------------------------------------------------
        # JANUARY FALLBACK
        # ----------------------------------------------------
        #
        # Actual January inherited-metadata source lines have
        # real source amount/account/cost fields but K/L can
        # be blank.
        #
        # Because the row itself carries one real source
        # transaction and one account/cost combination, we
        # preserve that accounting line using the source
        # amount/description while marking the provenance of
        # the fallback explicitly.
        # ----------------------------------------------------

        if (

            allocation_amount is None

            and transaction[
                "row_kind"
            ]
            == (
                "source_transaction_"
                "inherited_metadata"
            )

            and transaction[
                "expected_workpaper_amount"
            ]
            is not None
        ):

            allocation_amount = (

                transaction[
                    "expected_workpaper_amount"
                ]
            )


            amount_source = (

                "source_amount_fallback_"
                "for_inherited_row"
            )


        if (

            not allocation_description

            and transaction[
                "row_kind"
            ]
            == (
                "source_transaction_"
                "inherited_metadata"
            )

            and transaction[
                "source_description"
            ]
        ):

            allocation_description = (

                transaction[
                    "source_description"
                ]
            )


            description_source = (

                "source_description_fallback_"
                "for_inherited_row"
            )


        transaction_id = (
            transaction[
                "transaction_id"
            ]
        )


        allocation_sequence[
            transaction_id
        ] += 1


        allocations.append(

            {
                "allocation_id":
                    (
                        f"{transaction_id}-A"
                        f"{allocation_sequence[transaction_id]}"
                    ),

                "transaction_id":
                    transaction_id,

                "allocation_sequence":
                    allocation_sequence[
                        transaction_id
                    ],

                "allocation_position":
                    "source_row",

                "allocation_link_basis":
                    "same_source_row",

                "accounting_period":
                    period,

                "processing_sequence":
                    processing_sequence,

                "source_workbook":
                    workbook_path.name,

                "source_sheet":
                    "AIC IMS",

                "source_row":
                    transaction[
                        "source_row"
                    ],

                "account":
                    transaction[
                        "account_raw"
                    ],

                "cost_center":
                    transaction[
                        "cost_center_raw"
                    ],

                "allocation_description":
                    allocation_description,

                "allocation_description_source":
                    description_source,

                "allocation_amount_raw":
                    transaction[
                        "workpaper_amount_raw"
                    ],

                "allocation_amount_numeric":
                    allocation_amount,

                "allocation_amount_source":
                    amount_source,

                "backup":
                    transaction[
                        "backup_raw"
                    ],
            }
        )


    # ========================================================
    # SUPPLEMENTAL ALLOCATION ROWS
    # ========================================================

    for record in normalized_rows:


        if (
            record[
                "row_kind"
            ]
            != "allocation_or_supplemental"
        ):

            continue


        transaction_id = record.get(
            "linked_transaction_id"
        )


        # Do not force ambiguous allocation links.
        if transaction_id is None:

            continue


        allocation_sequence[
            transaction_id
        ] += 1


        allocations.append(

            {
                "allocation_id":
                    (
                        f"{transaction_id}-A"
                        f"{allocation_sequence[transaction_id]}"
                    ),

                "transaction_id":
                    transaction_id,

                "allocation_sequence":
                    allocation_sequence[
                        transaction_id
                    ],

                "allocation_position":
                    "supplemental_row",

                "allocation_link_basis":
                    record.get(
                        "allocation_link_basis"
                    ),

                "accounting_period":
                    period,

                "processing_sequence":
                    processing_sequence,

                "source_workbook":
                    workbook_path.name,

                "source_sheet":
                    "AIC IMS",

                "source_row":
                    record[
                        "source_row"
                    ],

                "account":
                    record[
                        "account_raw"
                    ],

                "cost_center":
                    record[
                        "cost_center_raw"
                    ],

                "allocation_description":
                    record[
                        "workpaper_description_raw"
                    ],

                "allocation_description_source":
                    "workpaper_description",

                "allocation_amount_raw":
                    record[
                        "workpaper_amount_raw"
                    ],

                "allocation_amount_numeric":
                    record[
                        "workpaper_amount_numeric"
                    ],

                "allocation_amount_source":
                    "workpaper_amount",

                "backup":
                    record[
                        "backup_raw"
                    ],
            }
        )


    # ========================================================
    # 21. VALIDATE ALLOCATION TOTALS
    # ========================================================

    allocation_totals = {}


    for allocation in allocations:


        amount = allocation.get(
            "allocation_amount_numeric"
        )


        if amount is None:

            continue


        transaction_id = allocation[
            "transaction_id"
        ]


        allocation_totals.setdefault(

            transaction_id,

            0.0,
        )


        allocation_totals[
            transaction_id
        ] += amount


    allocation_mismatches = []


    for transaction in transactions:


        expected = transaction.get(
            "expected_workpaper_amount"
        )


        actual = allocation_totals.get(

            transaction[
                "transaction_id"
            ]
        )


        if (

            expected is None

            or actual is None
        ):

            continue


        difference = (

            actual

            - expected
        )


        if abs(
            difference
        ) > TOLERANCE:


            allocation_mismatches.append(

                {
                    "transaction_id":
                        transaction[
                            "transaction_id"
                        ],

                    "source_row":
                        transaction[
                            "source_row"
                        ],

                    "expected_workpaper_amount":
                        expected,

                    "allocation_total":
                        actual,

                    "difference":
                        difference,
                }
            )


    # ========================================================
    # 22. VALIDATION REPORT
    # ========================================================

    formula_cells_outside_k_l = sum(

        count

        for column_number, count
        in formula_columns.items()

        if column_number
        not in {
            11,
            12,
        }
    )


    ambiguous_allocation_blocks = [

        block

        for block
        in allocation_block_results

        if block[
            "target_transaction_id"
        ] is None
    ]


    validation = {

        "accounting_period":
            period,

        "processing_sequence":
            processing_sequence,

        "source_workbook":
            workbook_path.name,

        "header_row":
            header_row,

        "header_matches_expected":
            True,

        "last_meaningful_row":
            (
                max(

                    record[
                        "source_row"
                    ]

                    for record
                    in normalized_rows
                )

                if normalized_rows

                else None
            ),

        "row_kind_counts":
            dict(

                Counter(

                    record[
                        "row_kind"
                    ]

                    for record
                    in normalized_rows
                )
            ),

        "balance_forward_rows":
            balance_forward_rows,

        "source_transaction_count":
            len(
                transactions
            ),

        "allocation_line_count":
            len(
                allocations
            ),

        "supplemental_block_count":
            len(
                allocation_block_results
            ),

        "ambiguous_supplemental_block_count":
            len(
                ambiguous_allocation_blocks
            ),

        "ambiguous_supplemental_blocks":
            ambiguous_allocation_blocks,

        "source_continuation_inheritance_ambiguity_count":
            len(
                source_continuation_ambiguities
            ),

        "source_continuation_inheritance_ambiguity_rows":
            source_continuation_ambiguities,

        "allocation_reconciliation_mismatch_count":
            len(
                allocation_mismatches
            ),

        "allocation_reconciliation_mismatches":
            allocation_mismatches,

        # Formula inspection.
        "formula_columns":
            {

                str(
                    column_number
                ):
                    count

                for column_number, count
                in sorted(
                    formula_columns.items()
                )
            },

        "formula_cells_outside_K_L":
            formula_cells_outside_k_l,

        "column_K_formula_static_blank":
            dict(
                formula_status_k
            ),

        "column_L_formula_static_blank":
            dict(
                formula_status_l
            ),

        "unexpected_row_count":
            len(
                unexpected_rows
            ),

        "unexpected_rows":
            unexpected_rows,
    }


    # ========================================================
    # 23. WRITE MONTH-SPECIFIC OUTPUTS
    # ========================================================

    output_folder = (

        PROCESSED_FOLDER

        / workbook_path.stem
    )


    output_folder.mkdir(

        parents=True,

        exist_ok=True,
    )


    write_csv(

        output_folder
        / "aic_ims_rows.csv",

        normalized_rows,
    )


    write_csv(

        output_folder
        / "aic_ims_transactions.csv",

        transactions,
    )


    write_csv(

        output_folder
        / "aic_ims_allocations.csv",

        allocations,
    )


    with (
        output_folder
        / "aic_ims_validation.json"
    ).open(

        "w",

        encoding="utf-8",

    ) as file:


        json.dump(

            validation,

            file,

            indent=2,

            ensure_ascii=False,
        )


    # ========================================================
    # 24. TERMINAL SUMMARY
    # ========================================================

    print(
        f"Balance Forward row(s): "
        f"{balance_forward_rows}"
    )


    print(
        "Row types:"
    )


    for (
        row_type,
        count,
    ) in validation[
        "row_kind_counts"
    ].items():


        print(
            f"  {row_type}: {count}"
        )


    print(
        f"Source transactions: "
        f"{len(transactions)}"
    )


    print(
        f"Allocation lines: "
        f"{len(allocations)}"
    )


    print(
        f"Supplemental allocation blocks: "
        f"{len(allocation_block_results)}"
    )


    print(
        f"Ambiguous allocation blocks: "
        f"{len(ambiguous_allocation_blocks)}"
    )


    print(
        "Allocation reconciliation mismatches: "
        f"{len(allocation_mismatches)}"
    )


    print(
        "Inherited-metadata ambiguities: "
        f"{len(source_continuation_ambiguities)}"
    )


    print(
        "Formula cells outside K/L: "
        f"{formula_cells_outside_k_l}"
    )


    return (

        normalized_rows,

        transactions,

        allocations,

        validation,
    )


# ============================================================
# 25. MAIN PROGRAM
# ============================================================

def main():

    print(
        "ASCOT AIC IMS SANITIZER"
    )

    print(
        "Evidence-based on actual Jan–Jul IMS data"
    )


    # ========================================================
    # FIND RESOURCE PRO WORKBOOKS
    # ========================================================

    files = list(

        RAW_FOLDER.glob(
            "*Resource Pro Cash.xlsx"
        )
    )


    if not files:

        raise FileNotFoundError(

            "No Resource Pro Cash files were found "
            "inside data/raw/."
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
    # CONSOLIDATED DATA
    # ========================================================

    all_rows = []

    all_transactions = []

    all_allocations = []

    manifest = []


    # ========================================================
    # PROCESS MONTHS
    # ========================================================

    for sequence, workbook_path in enumerate(

        files,

        start=1,
    ):


        try:

            (
                rows,
                transactions,
                allocations,
                validation,
            ) = sanitize_one_workbook(

                workbook_path,

                sequence,
            )


            all_rows.extend(
                rows
            )


            all_transactions.extend(
                transactions
            )


            all_allocations.extend(
                allocations
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

                    "source_transaction_count":
                        validation[
                            "source_transaction_count"
                        ],

                    "allocation_line_count":
                        validation[
                            "allocation_line_count"
                        ],

                    "ambiguous_supplemental_block_count":
                        validation[
                            "ambiguous_supplemental_block_count"
                        ],

                    "allocation_reconciliation_mismatch_count":
                        validation[
                            "allocation_reconciliation_mismatch_count"
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
    # SORT CONSOLIDATED RESULTS CHRONOLOGICALLY
    # ========================================================

    all_rows.sort(

        key=lambda record: (

            record[
                "processing_sequence"
            ],

            record[
                "source_row"
            ],
        )
    )


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


    all_allocations.sort(

        key=lambda record: (

            record[
                "processing_sequence"
            ],

            record[
                "source_row"
            ],

            record[
                "allocation_sequence"
            ],
        )
    )


    # ========================================================
    # WRITE CONSOLIDATED OUTPUTS
    # ========================================================

    write_csv(

        PROCESSED_FOLDER
        / "aic_ims_all_months_rows.csv",

        all_rows,
    )


    write_csv(

        PROCESSED_FOLDER
        / "aic_ims_all_months_transactions.csv",

        all_transactions,
    )


    write_csv(

        PROCESSED_FOLDER
        / "aic_ims_all_months_allocations.csv",

        all_allocations,
    )


    with (
        PROCESSED_FOLDER
        / "aic_ims_processing_manifest.json"
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


    total_ambiguous_blocks = sum(

        entry.get(
            "ambiguous_supplemental_block_count",
            0,
        )

        for entry
        in manifest

        if entry[
            "status"
        ] == "success"
    )


    total_mismatches = sum(

        entry.get(
            "allocation_reconciliation_mismatch_count",
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
        "AIC IMS SANITIZATION COMPLETE"
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
        f"Total source transactions: "
        f"{len(all_transactions)}"
    )


    print(
        f"Total allocation lines: "
        f"{len(all_allocations)}"
    )


    print(
        f"Ambiguous allocation blocks: "
        f"{total_ambiguous_blocks}"
    )


    print(
        "Allocation reconciliation mismatches: "
        f"{total_mismatches}"
    )


    print(
        "\nConsolidated outputs:"
    )


    print(
        "data/processed/"
        "aic_ims_all_months_rows.csv"
    )


    print(
        "data/processed/"
        "aic_ims_all_months_transactions.csv"
    )


    print(
        "data/processed/"
        "aic_ims_all_months_allocations.csv"
    )


    print(
        "data/processed/"
        "aic_ims_processing_manifest.json"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()