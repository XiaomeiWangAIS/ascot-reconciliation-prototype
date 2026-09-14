# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
#
# MEMORY-SAFE RECONSTRUCTION OF HUMAN CONTROL:
#
#     AIC WF YELLOW / IMS CATEGORY
#               vs
#     AIC IMS CLEARED CREDIT
#
# ============================================================
#
# WHY THIS VERSION EXISTS
# ------------------------------------------------------------
#
# The first version successfully inspected January but was
# terminated while opening February because it retained whole
# worksheet structures in memory.
#
# This version STREAMS worksheet rows one at a time.
#
# It also investigates nonzero monthly variances rather than
# assuming they are errors in the code.
#
# ============================================================


import csv
import json
import posixpath
import re
import zipfile

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
import xml.etree.ElementTree as ET


# ============================================================
# PATHS
# ============================================================

RAW_FOLDER = Path("data/raw")

OUTPUT_FOLDER = (
    Path("data/processed")
    / "inspection"
    / "current_month_ims_to_wf"
)

OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)

MONTHLY_OUTPUT = (
    OUTPUT_FOLDER
    / "monthly_control_reconstruction.csv"
)

REPORT_OUTPUT = (
    OUTPUT_FOLDER
    / "current_month_ims_wf_inspection.json"
)

VARIANCE_CANDIDATES_OUTPUT = (
    OUTPUT_FOLDER
    / "variance_candidate_rows.csv"
)


# ============================================================
# XML NAMESPACES
# ============================================================

MAIN_NS = (
    "http://schemas.openxmlformats.org/"
    "spreadsheetml/2006/main"
)

OFFICE_REL_NS = (
    "http://schemas.openxmlformats.org/"
    "officeDocument/2006/relationships"
)

PACKAGE_REL_NS = (
    "http://schemas.openxmlformats.org/"
    "package/2006/relationships"
)


# ============================================================
# MONEY
# ============================================================

CENT = Decimal("0.01")
ZERO = Decimal("0.00")


def to_decimal(value):
    """
    Safely convert a raw Excel value to Decimal.
    """

    if value in {
        None,
        "",
    }:
        return None

    try:
        return Decimal(
            str(value)
        ).quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        )

    except InvalidOperation:
        return None


def money_text(value):
    """
    Stable two-decimal display.
    """

    if value is None:
        return None

    return format(
        value.quantize(
            CENT,
            rounding=ROUND_HALF_UP,
        ),
        ".2f",
    )


# ============================================================
# TEXT
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    )


def upper_text(value):

    return clean_text(
        value
    ).upper()


# ============================================================
# PERIOD FROM FILENAME
# ============================================================

def extract_period(path):

    match = re.search(
        r"\b("
        r"January|February|March|April|May|June|"
        r"July|August|September|October|November|December"
        r")\s+(\d{4})\b",
        path.stem,
        flags=re.IGNORECASE,
    )

    if not match:
        return None

    months = {
        "JANUARY": 1,
        "FEBRUARY": 2,
        "MARCH": 3,
        "APRIL": 4,
        "MAY": 5,
        "JUNE": 6,
        "JULY": 7,
        "AUGUST": 8,
        "SEPTEMBER": 9,
        "OCTOBER": 10,
        "NOVEMBER": 11,
        "DECEMBER": 12,
    }

    year = int(
        match.group(2)
    )

    month = months[
        match.group(1).upper()
    ]

    return f"{year:04d}-{month:02d}"


# ============================================================
# SHARED STRINGS
# ============================================================

def read_shared_strings(archive):

    path = "xl/sharedStrings.xml"

    if path not in archive.namelist():
        return []

    root = ET.fromstring(
        archive.read(path)
    )

    output = []

    for item in root.findall(
        f"{{{MAIN_NS}}}si"
    ):

        output.append(
            "".join(
                node.text or ""
                for node in item.iter(
                    f"{{{MAIN_NS}}}t"
                )
            )
        )

    return output


# ============================================================
# STYLE -> FILL SIGNATURE
# ============================================================

def color_signature(node):

    if node is None:
        return None

    return tuple(
        sorted(
            node.attrib.items()
        )
    )


def read_style_fills(archive):

    root = ET.fromstring(
        archive.read(
            "xl/styles.xml"
        )
    )

    fills = []

    fills_node = root.find(
        f"{{{MAIN_NS}}}fills"
    )

    if fills_node is not None:

        for fill in fills_node:

            pattern = fill.find(
                f"{{{MAIN_NS}}}patternFill"
            )

            if pattern is None:

                fills.append(
                    ("NO_PATTERN",)
                )

                continue

            foreground = pattern.find(
                f"{{{MAIN_NS}}}fgColor"
            )

            background = pattern.find(
                f"{{{MAIN_NS}}}bgColor"
            )

            fills.append(
                (
                    pattern.attrib.get(
                        "patternType"
                    ),
                    color_signature(
                        foreground
                    ),
                    color_signature(
                        background
                    ),
                )
            )

    style_map = {}

    cell_xfs = root.find(
        f"{{{MAIN_NS}}}cellXfs"
    )

    if cell_xfs is not None:

        for style_index, xf in enumerate(
            cell_xfs
        ):

            fill_id = int(
                xf.attrib.get(
                    "fillId",
                    "0",
                )
            )

            style_map[
                style_index
            ] = (
                fills[fill_id]
                if 0 <= fill_id < len(fills)
                else None
            )

    return style_map


# ============================================================
# WORKBOOK SHEET PATHS
# ============================================================

def normalize_target(target):

    target = target.replace(
        "\\",
        "/",
    )

    if target.startswith("/"):
        return target.lstrip("/")

    if target.startswith("xl/"):
        return target

    return posixpath.normpath(
        posixpath.join(
            "xl",
            target,
        )
    )


def read_sheet_paths(archive):

    workbook = ET.fromstring(
        archive.read(
            "xl/workbook.xml"
        )
    )

    relationships = ET.fromstring(
        archive.read(
            "xl/_rels/workbook.xml.rels"
        )
    )

    rel_map = {}

    for relationship in relationships.findall(
        f"{{{PACKAGE_REL_NS}}}Relationship"
    ):

        rel_map[
            relationship.attrib["Id"]
        ] = normalize_target(
            relationship.attrib["Target"]
        )

    output = {}

    sheets = workbook.find(
        f"{{{MAIN_NS}}}sheets"
    )

    for sheet in sheets:

        name = sheet.attrib[
            "name"
        ]

        rel_id = sheet.attrib[
            f"{{{OFFICE_REL_NS}}}id"
        ]

        output[name] = rel_map[
            rel_id
        ]

    return output


# ============================================================
# CELL DECODING
# ============================================================

def get_column(reference):

    match = re.match(
        r"([A-Z]+)",
        reference or "",
    )

    return (
        match.group(1)
        if match
        else None
    )


def decode_cell(
    cell,
    shared_strings,
    style_map,
):

    cell_type = cell.attrib.get(
        "t"
    )

    value_node = cell.find(
        f"{{{MAIN_NS}}}v"
    )

    if cell_type == "inlineStr":

        inline = cell.find(
            f"{{{MAIN_NS}}}is"
        )

        value = (
            "".join(
                node.text or ""
                for node in inline.iter(
                    f"{{{MAIN_NS}}}t"
                )
            )
            if inline is not None
            else ""
        )

    elif cell_type == "s":

        if (
            value_node is None
            or value_node.text is None
        ):

            value = ""

        else:

            value = shared_strings[
                int(
                    value_node.text
                )
            ]

    else:

        value = (
            value_node.text
            if value_node is not None
            else None
        )

    style_index = int(
        cell.attrib.get(
            "s",
            "0",
        )
    )

    return {
        "value": value,
        "type": cell_type,
        "style_index": style_index,
        "fill": style_map.get(
            style_index
        ),
    }


# ============================================================
# STREAM WORKSHEET ROWS
# ============================================================

def stream_rows(
    archive,
    sheet_path,
    shared_strings,
    style_map,
):
    """
    Yield one worksheet row at a time.

    Nothing accumulates in memory.
    """

    with archive.open(
        sheet_path
    ) as file:

        for event, element in ET.iterparse(
            file,
            events=("end",),
        ):

            if element.tag != (
                f"{{{MAIN_NS}}}row"
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
                f"{{{MAIN_NS}}}c"
            ):

                reference = cell.attrib.get(
                    "r"
                )

                column = get_column(
                    reference
                )

                if column is None:
                    continue

                cells[column] = decode_cell(
                    cell,
                    shared_strings,
                    style_map,
                )

            yield (
                row_number,
                cells,
            )

            element.clear()


# ============================================================
# VALUE HELPER
# ============================================================

def value(cells, column):

    cell = cells.get(
        column
    )

    if cell is None:
        return None

    return cell.get(
        "value"
    )


# ============================================================
# DATE-CLEARED CLASSIFICATION
# ============================================================

def classify_date_cleared(cell):
    """
    Return:

        include, reason

    This deliberately separates actual date values from
    narrative statuses.

    IMPORTANT:
    A text such as RETURNED 4/28/26 is NOT treated as a
    normal cleared date merely because it contains numbers.
    """

    if cell is None:

        return (
            False,
            "blank",
        )

    raw = cell.get(
        "value"
    )

    if raw in {
        None,
        "",
    }:

        return (
            False,
            "blank",
        )

    text = clean_text(
        raw
    )

    upper = text.upper()

    # --------------------------------------------------------
    # KNOWN NARRATIVE NON-CLEARED STATUS
    # --------------------------------------------------------

    if "OUTSTANDING" in upper:

        return (
            False,
            "outstanding",
        )

    if "RETURN" in upper:

        return (
            False,
            "returned",
        )

    if "VOID" in upper:

        return (
            False,
            "void",
        )

    if "PRIOR MONTH" in upper:

        return (
            False,
            "prior_month_text",
        )

    if "SAME MONTH" in upper:

        return (
            False,
            "same_month_text",
        )

    # --------------------------------------------------------
    # NUMERIC EXCEL DATE
    # --------------------------------------------------------

    if cell.get(
        "type"
    ) in {
        None,
        "n",
    }:

        try:

            number = Decimal(
                str(raw)
            )

            if number > 0:

                return (
                    True,
                    "numeric_date",
                )

        except InvalidOperation:
            pass

    # --------------------------------------------------------
    # TEXT DATE / MULTIPLE DATES
    # --------------------------------------------------------

    # If alphabetic narrative remains, do not silently call it
    # a clearing date.
    if re.search(
        r"[A-Za-z]",
        text,
    ):

        return (
            False,
            "other_text",
        )

    date_patterns = [

        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b",

        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
    ]

    if any(
        re.search(
            pattern,
            text,
        )
        for pattern in date_patterns
    ):

        return (
            True,
            "text_date",
        )

    return (
        False,
        "other",
    )


# ============================================================
# FIRST PASS:
# DISCOVER WF HEADER + IMS YELLOW LEGEND FILL
# ============================================================

def discover_wf_structure(
    archive,
    sheet_path,
    shared_strings,
    style_map,
):

    header_row = None

    ims_fill = None

    ims_legend_cell = None

    for row_number, cells in stream_rows(
        archive,
        sheet_path,
        shared_strings,
        style_map,
    ):

        # Legend appears above transaction header.
        for column, cell in cells.items():

            if upper_text(
                cell.get(
                    "value"
                )
            ) == "IMS":

                ims_fill = cell.get(
                    "fill"
                )

                ims_legend_cell = (
                    f"{column}{row_number}"
                )

        if (
            upper_text(
                value(
                    cells,
                    "A",
                )
            )
            == "AS-OF DATE"

            and

            upper_text(
                value(
                    cells,
                    "D",
                )
            )
            == "TRAN DESC"

            and

            upper_text(
                value(
                    cells,
                    "G",
                )
            )
            == "0 DAY FLT AMT"
        ):

            header_row = row_number

            break

    if header_row is None:

        raise ValueError(
            "Could not find AIC WF header."
        )

    if ims_fill is None:

        raise ValueError(
            "Could not find IMS legend fill."
        )

    return (
        header_row,
        ims_fill,
        ims_legend_cell,
    )


# ============================================================
# PROCESS WF YELLOW POPULATION
# ============================================================

def process_wf(
    archive,
    sheet_path,
    shared_strings,
    style_map,
):

    (
        header_row,
        ims_fill,
        ims_legend_cell,
    ) = discover_wf_structure(
        archive,
        sheet_path,
        shared_strings,
        style_map,
    )

    total = ZERO

    rows = []

    for row_number, cells in stream_rows(
        archive,
        sheet_path,
        shared_strings,
        style_map,
    ):

        if row_number <= header_row:
            continue

        # Genuine transaction rows need bank date + Tran Desc.
        if not clean_text(
            value(
                cells,
                "A",
            )
        ):

            continue

        if not clean_text(
            value(
                cells,
                "D",
            )
        ):

            continue

        g_cell = cells.get(
            "G"
        )

        if g_cell is None:
            continue

        # Historical IMS classification = same fill as the
        # legend cell labelled IMS.
        if g_cell.get(
            "fill"
        ) != ims_fill:

            continue

        amount = to_decimal(
            g_cell.get(
                "value"
            )
        )

        if amount is None:
            continue

        total += amount

        rows.append(
            {
                "source_row": row_number,
                "as_of_date": value(
                    cells,
                    "A",
                ),
                "tran_desc": value(
                    cells,
                    "D",
                ),
                "debit": value(
                    cells,
                    "E",
                ),
                "credit": value(
                    cells,
                    "F",
                ),
                "wf_amount": money_text(
                    amount
                ),
                "check_number": value(
                    cells,
                    "H",
                ),
                "descriptive_text": value(
                    cells,
                    "I",
                ),
            }
        )

    return {
        "header_row": header_row,
        "ims_legend_cell": ims_legend_cell,
        "row_count": len(
            rows
        ),
        "total": total,
        "rows": rows,
    }


# ============================================================
# PROCESS IMS
# ============================================================

def process_ims(
    archive,
    sheet_path,
    shared_strings,
    style_map,
):

    header_row = None

    included_rows = []

    excluded_rows = []

    signed_credit_total = ZERO

    absolute_credit_total = ZERO

    for row_number, cells in stream_rows(
        archive,
        sheet_path,
        shared_strings,
        style_map,
    ):

        # Detect header.
        if (
            upper_text(
                value(
                    cells,
                    "A",
                )
            )
            == "TRANSACTIONDATE"

            and

            upper_text(
                value(
                    cells,
                    "G",
                )
            )
            == "CREDIT"

            and

            upper_text(
                value(
                    cells,
                    "H",
                )
            )
            == "DATE CLEARED"
        ):

            header_row = row_number

            continue

        if header_row is None:
            continue

        if row_number <= header_row:
            continue

        # Ignore genuinely empty rows.
        if not any(
            clean_text(
                value(
                    cells,
                    column,
                )
            )
            for column in (
                "A",
                "B",
                "C",
                "D",
                "E",
                "F",
                "G",
                "H",
            )
        ):

            continue

        date_cell = cells.get(
            "H"
        )

        (
            include,
            reason,
        ) = classify_date_cleared(
            date_cell
        )

        credit = to_decimal(
            value(
                cells,
                "G",
            )
        )

        record = {
            "source_row": row_number,
            "transaction_date": value(
                cells,
                "A",
            ),
            "check_or_ref": value(
                cells,
                "B",
            ),
            "method": value(
                cells,
                "C",
            ),
            "payment_type": value(
                cells,
                "D",
            ),
            "description": value(
                cells,
                "E",
            ),
            "debit": value(
                cells,
                "F",
            ),
            "credit": money_text(
                credit
            ),
            "date_cleared": value(
                cells,
                "H",
            ),
            "date_cleared_class": reason,
        }

        if include:

            included_rows.append(
                record
            )

            if credit is not None:

                signed_credit_total += credit

                absolute_credit_total += abs(
                    credit
                )

        else:

            excluded_rows.append(
                record
            )

    return {
        "header_row": header_row,
        "included_rows": included_rows,
        "excluded_rows": excluded_rows,
        "included_count": len(
            included_rows
        ),
        "signed_credit_total": signed_credit_total,
        "absolute_credit_total": absolute_credit_total,
    }


# ============================================================
# VARIANCE DIAGNOSTICS
# ============================================================

def find_variance_candidates(
    period,
    variance,
    wf_rows,
    excluded_ims_rows,
):

    candidates = []

    target = abs(
        variance
    )

    if target == ZERO:
        return candidates

    # --------------------------------------------------------
    # YELLOW WF ROW EXACTLY EQUAL TO VARIANCE
    # --------------------------------------------------------

    for row in wf_rows:

        amount = to_decimal(
            row.get(
                "wf_amount"
            )
        )

        if (
            amount is not None
            and abs(
                amount
            ) == target
        ):

            candidates.append(
                {
                    "accounting_period": period,
                    "candidate_source": "WF_YELLOW",
                    "reason":
                        "WF yellow amount equals absolute variance",
                    **row,
                }
            )

    # --------------------------------------------------------
    # EXCLUDED IMS CREDIT EXACTLY EQUAL TO VARIANCE
    # --------------------------------------------------------

    for row in excluded_ims_rows:

        credit = to_decimal(
            row.get(
                "credit"
            )
        )

        if (
            credit is not None
            and abs(
                credit
            ) == target
        ):

            candidates.append(
                {
                    "accounting_period": period,
                    "candidate_source": "IMS_EXCLUDED",
                    "reason":
                        "Excluded IMS Credit equals absolute variance",
                    **row,
                }
            )

    return candidates


# ============================================================
# FIND RESOURCE PRO FILES
# ============================================================

def find_workbooks():

    files = []

    for path in RAW_FOLDER.glob(
        "*.xlsx"
    ):

        if path.name.startswith(
            "~$"
        ):
            continue

        period = extract_period(
            path
        )

        if period is None:
            continue

        try:

            with zipfile.ZipFile(
                path,
                "r",
            ) as archive:

                sheets = read_sheet_paths(
                    archive
                )

                if (
                    "AIC WF" in sheets
                    and "AIC IMS" in sheets
                ):

                    files.append(
                        (
                            period,
                            path,
                        )
                    )

        except zipfile.BadZipFile:
            continue

    return sorted(
        files,
        key=lambda item: item[0],
    )


# ============================================================
# WRITE CSV
# ============================================================

def write_csv(
    path,
    records,
):

    if not records:

        with path.open(
            "w",
            encoding="utf-8-sig",
        ):
            pass

        return

    fields = []

    for record in records:

        for key in record:

            if key not in fields:
                fields.append(
                    key
                )

    with path.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fields,
        )

        writer.writeheader()

        writer.writerows(
            records
        )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "ASCOT CURRENT-MONTH IMS <-> YELLOW WF"
    )

    print(
        "MEMORY-SAFE HUMAN CONTROL RECONSTRUCTION"
    )

    workbooks = find_workbooks()

    print(
        f"\nFound {len(workbooks)} workbook(s)."
    )

    monthly_results = []

    all_variance_candidates = []

    for period, path in workbooks:

        print(
            "\n========================================"
        )

        print(
            f"{period} | {path.name}"
        )

        print(
            "========================================"
        )

        with zipfile.ZipFile(
            path,
            "r",
        ) as archive:

            shared_strings = read_shared_strings(
                archive
            )

            style_map = read_style_fills(
                archive
            )

            sheets = read_sheet_paths(
                archive
            )

            wf = process_wf(
                archive,
                sheets["AIC WF"],
                shared_strings,
                style_map,
            )

            ims = process_ims(
                archive,
                sheets["AIC IMS"],
                shared_strings,
                style_map,
            )

        ims_abs_total = abs(
            ims[
                "signed_credit_total"
            ]
        )

        variance = (
            wf[
                "total"
            ]
            - ims_abs_total
        )

        candidates = find_variance_candidates(
            period,
            variance,
            wf[
                "rows"
            ],
            ims[
                "excluded_rows"
            ],
        )

        all_variance_candidates.extend(
            candidates
        )

        result = {
            "accounting_period": period,
            "source_workbook": path.name,
            "wf_ims_legend_cell":
                wf["ims_legend_cell"],
            "wf_yellow_row_count":
                wf["row_count"],
            "wf_yellow_total":
                money_text(
                    wf["total"]
                ),
            "ims_cleared_row_count":
                ims["included_count"],
            "ims_signed_credit_total":
                money_text(
                    ims[
                        "signed_credit_total"
                    ]
                ),
            "ims_absolute_credit_total":
                money_text(
                    ims_abs_total
                ),
            "variance_wf_minus_abs_ims":
                money_text(
                    variance
                ),
            "variance_candidate_count":
                len(
                    candidates
                ),
        }

        monthly_results.append(
            result
        )

        print(
            f"WF yellow rows: "
            f"{wf['row_count']}"
        )

        print(
            f"WF yellow total: "
            f"{money_text(wf['total'])}"
        )

        print(
            f"IMS cleared rows: "
            f"{ims['included_count']}"
        )

        print(
            "IMS signed Credit total: "
            f"{money_text(ims['signed_credit_total'])}"
        )

        print(
            "ABS(IMS Credit total): "
            f"{money_text(ims_abs_total)}"
        )

        print(
            f"Variance: "
            f"{money_text(variance)}"
        )

        if variance != ZERO:

            print(
                "\nPossible rows explaining the variance:"
            )

            if not candidates:

                print(
                    "  No single row exactly equals the variance."
                )

            for candidate in candidates:

                if (
                    candidate[
                        "candidate_source"
                    ]
                    == "WF_YELLOW"
                ):

                    print(
                        "  WF YELLOW | "
                        f"row {candidate['source_row']} | "
                        f"{candidate['tran_desc']} | "
                        f"{candidate['wf_amount']} | "
                        f"check={candidate['check_number']}"
                    )

                else:

                    print(
                        "  IMS EXCLUDED | "
                        f"row {candidate['source_row']} | "
                        f"{candidate['description']} | "
                        f"credit={candidate['credit']} | "
                        f"Date Cleared="
                        f"{candidate['date_cleared']} | "
                        f"class={candidate['date_cleared_class']}"
                    )

    # ========================================================
    # OUTPUT
    # ========================================================

    write_csv(
        MONTHLY_OUTPUT,
        monthly_results,
    )

    write_csv(
        VARIANCE_CANDIDATES_OUTPUT,
        all_variance_candidates,
    )

    report = {
        "monthly_results":
            monthly_results,
        "variance_candidates":
            all_variance_candidates,
    }

    with REPORT_OUTPUT.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            report,
            file,
            indent=2,
            ensure_ascii=False,
            default=str,
        )

    print(
        "\n========================================"
    )

    print(
        "CROSS-MONTH SUMMARY"
    )

    print(
        "========================================"
    )

    for result in monthly_results:

        print(
            f"{result['accounting_period']} | "
            f"WF={result['wf_yellow_total']} | "
            f"IMS={result['ims_absolute_credit_total']} | "
            f"variance={result['variance_wf_minus_abs_ims']} | "
            f"candidates={result['variance_candidate_count']}"
        )

    print(
        "\nOutputs:"
    )

    print(
        MONTHLY_OUTPUT
    )

    print(
        VARIANCE_CANDIDATES_OUTPUT
    )


if __name__ == "__main__":

    main()