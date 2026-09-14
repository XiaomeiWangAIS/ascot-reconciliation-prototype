# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
#
# TARGETED EXPLANATION OF NONZERO
# CURRENT-MONTH IMS <-> WF VARIANCES
# ============================================================
#
# We already reconstructed the human control:
#
#     WF yellow / IMS-coded column G total
#                  vs
#     ABS(sum of IMS Credit for actually-cleared rows))
#
# Results:
#
#     Jan  variance = +300.00
#     Feb  variance = -2220.00
#     Mar-Jul       = 0.00
#
# This script does NOT change the control.
#
# It inspects the exact source rows surrounding those
# nonzero variances so we can determine what they mean.
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import sys
import zipfile

from decimal import Decimal
from pathlib import Path


# ============================================================
# IMPORT THE MEMORY-SAFE XLSX HELPERS WE ALREADY BUILT
# ============================================================
#
# This avoids duplicating the XLSX/XML parser.
#
# Both scripts live in:
#
#     src/ascot/
#
# ============================================================

SCRIPT_FOLDER = Path(
    __file__
).resolve().parent


sys.path.insert(
    0,
    str(
        SCRIPT_FOLDER
    ),
)


from inspect_current_month_ims_wf_control import (  # noqa: E402

    ZERO,

    clean_text,

    upper_text,

    to_decimal,

    money_text,

    find_workbooks,

    read_shared_strings,

    read_style_fills,

    read_sheet_paths,

    stream_rows,

    value,

    discover_wf_structure,

    classify_date_cleared,
)


# ============================================================
# KNOWN NONZERO VARIANCES FROM THE HISTORICAL RECONSTRUCTION
# ============================================================
#
# We are not inventing these values.
#
# They came directly from the Jan-Jul historical inspection.
# ============================================================

TARGET_VARIANCES = {

    "2026-01":
        Decimal("300.00"),

    "2026-02":
        Decimal("-2220.00"),
}


# ============================================================
# ASCOT WF LEGEND LABELS
# ============================================================
#
# These are the actual categories used by the AIC WF legend.
#
# We map the legend CELL FILL to the category label.
#
# The color itself is presentation metadata;
# the human-readable label is what we report.
# ============================================================

KNOWN_WF_CATEGORIES = {

    "IMS",

    "BANK ITEMS",

    "PRIOR MONTH",

    "STATE PAYMENTS",

    "REINSURANCE",

    "INTERCO TRANSFERS",

    "INVESTMENT",

    "LOSS FUNDING/TPA",
}


# ============================================================
# DISCOVER ALL WF LEGEND COLORS
# ============================================================

def discover_legend_categories(
    archive,
    sheet_path,
    shared_strings,
    style_map,
):
    """
    Return:

        {
            fill_signature: "IMS",
            fill_signature: "BANK ITEMS",
            ...
        }

    We derive the mapping from the actual workbook legend.
    """

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


    fill_to_category = {}


    for (
        row_number,
        cells,
    ) in stream_rows(

        archive,
        sheet_path,
        shared_strings,
        style_map,
    ):


        # Legend is above the transaction header.
        if row_number >= header_row:

            break


        for (
            column,
            cell,
        ) in cells.items():


            label = upper_text(

                cell.get(
                    "value"
                )
            )


            if label not in KNOWN_WF_CATEGORIES:

                continue


            fill_to_category[

                cell.get(
                    "fill"
                )

            ] = label


    return (
        header_row,
        fill_to_category,
    )


# ============================================================
# INSPECT WF ROWS EQUAL TO THE VARIANCE AMOUNT
# ============================================================

def inspect_wf_variance_amount(
    archive,
    sheet_path,
    shared_strings,
    style_map,
    target_amount,
):
    """
    Find every genuine WF transaction whose absolute
    column-G amount equals the absolute control variance.

    We search ALL WF categories, not just yellow.
    """

    (
        header_row,
        fill_to_category,
    ) = discover_legend_categories(

        archive,
        sheet_path,
        shared_strings,
        style_map,
    )


    target_absolute = abs(
        target_amount
    )


    matches = []


    for (
        row_number,
        cells,
    ) in stream_rows(

        archive,
        sheet_path,
        shared_strings,
        style_map,
    ):


        if row_number <= header_row:

            continue


        # A normal WF transaction should have
        # an As-Of Date and Tran Desc.
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


        amount = to_decimal(

            g_cell.get(
                "value"
            )
        )


        if amount is None:

            continue


        if abs(
            amount
        ) != target_absolute:

            continue


        fill = g_cell.get(
            "fill"
        )


        category = fill_to_category.get(

            fill,

            "UNMAPPED / NO LEGEND CATEGORY",
        )


        matches.append(

            {
                "source_row":
                    row_number,

                "as_of_date":
                    value(
                        cells,
                        "A",
                    ),

                "tran_desc":
                    value(
                        cells,
                        "D",
                    ),

                "debit":
                    value(
                        cells,
                        "E",
                    ),

                "credit":
                    value(
                        cells,
                        "F",
                    ),

                "column_g":
                    money_text(
                        amount
                    ),

                "check_number":
                    value(
                        cells,
                        "H",
                    ),

                "descriptive_text":
                    value(
                        cells,
                        "I",
                    ),

                "wf_category":
                    category,
            }
        )


    return matches


# ============================================================
# INSPECT IMS ROWS EQUAL TO THE VARIANCE AMOUNT
# ============================================================

def inspect_ims_variance_amount(
    archive,
    sheet_path,
    shared_strings,
    style_map,
    target_amount,
):
    """
    Find all IMS rows whose absolute Credit equals the
    absolute control variance.

    For each row we also reproduce the Date Cleared
    include/exclude classification.
    """

    target_absolute = abs(
        target_amount
    )


    header_found = False


    matches = []


    for (
        row_number,
        cells,
    ) in stream_rows(

        archive,
        sheet_path,
        shared_strings,
        style_map,
    ):


        # ----------------------------------------------------
        # FIND IMS HEADER
        # ----------------------------------------------------

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


            header_found = True

            continue


        if not header_found:

            continue


        credit = to_decimal(

            value(
                cells,
                "G",
            )
        )


        if credit is None:

            continue


        if abs(
            credit
        ) != target_absolute:

            continue


        date_cleared_cell = cells.get(
            "H"
        )


        (
            included,
            classification,
        ) = classify_date_cleared(

            date_cleared_cell
        )


        matches.append(

            {
                "source_row":
                    row_number,

                "transaction_date":
                    value(
                        cells,
                        "A",
                    ),

                "check_or_ref":
                    value(
                        cells,
                        "B",
                    ),

                "method":
                    value(
                        cells,
                        "C",
                    ),

                "payment_type":
                    value(
                        cells,
                        "D",
                    ),

                "description":
                    value(
                        cells,
                        "E",
                    ),

                "debit":
                    value(
                        cells,
                        "F",
                    ),

                "credit":
                    money_text(
                        credit
                    ),

                "date_cleared":
                    value(
                        cells,
                        "H",
                    ),

                "included_in_human_control":
                    included,

                "date_cleared_class":
                    classification,
            }
        )


    return matches


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "ASCOT CURRENT-MONTH IMS <-> WF"
    )


    print(
        "TARGETED VARIANCE EXPLANATION"
    )


    workbooks = find_workbooks()


    workbook_by_period = {

        period:
            path

        for (
            period,
            path,
        ) in workbooks
    }


    # ========================================================
    # ONLY INSPECT MONTHS WITH NONZERO HISTORICAL VARIANCE
    # ========================================================

    for (
        period,
        variance,
    ) in TARGET_VARIANCES.items():


        path = workbook_by_period.get(
            period
        )


        if path is None:


            print(

                f"\nCould not find workbook for "
                f"{period}."
            )


            continue


        print(
            "\n========================================"
        )


        print(

            f"{period} | "
            f"control variance = "
            f"{money_text(variance)}"
        )


        print(
            f"{path.name}"
        )


        print(
            "========================================"
        )


        with zipfile.ZipFile(

            path,

            "r",

        ) as archive:


            shared_strings = (
                read_shared_strings(
                    archive
                )
            )


            style_map = read_style_fills(
                archive
            )


            sheet_paths = read_sheet_paths(
                archive
            )


            # =================================================
            # WF SIDE
            # =================================================

            wf_matches = (
                inspect_wf_variance_amount(

                    archive,

                    sheet_paths[
                        "AIC WF"
                    ],

                    shared_strings,

                    style_map,

                    variance,
                )
            )


            # =================================================
            # IMS SIDE
            # =================================================

            ims_matches = (
                inspect_ims_variance_amount(

                    archive,

                    sheet_paths[
                        "AIC IMS"
                    ],

                    shared_strings,

                    style_map,

                    variance,
                )
            )


        # ====================================================
        # PRINT WF CANDIDATES
        # ====================================================

        print(
            "\nWF transactions with this absolute amount:"
        )


        if not wf_matches:


            print(
                "  None."
            )


        for row in wf_matches:


            print(
                "\n  ---"
            )


            print(

                f"  WF row "
                f"{row['source_row']}"
            )


            print(

                f"  Date: "
                f"{row['as_of_date']}"
            )


            print(

                f"  Tran Desc: "
                f"{row['tran_desc']}"
            )


            print(

                f"  Debit: "
                f"{row['debit']}"
            )


            print(

                f"  Credit: "
                f"{row['credit']}"
            )


            print(

                f"  Column G: "
                f"{row['column_g']}"
            )


            print(

                f"  Check Number: "
                f"{row['check_number']}"
            )


            print(

                f"  Descriptive Text: "
                f"{row['descriptive_text']}"
            )


            print(

                f"  WF CATEGORY: "
                f"{row['wf_category']}"
            )


        # ====================================================
        # PRINT IMS CANDIDATES
        # ====================================================

        print(
            "\nIMS transactions with this absolute Credit:"
        )


        if not ims_matches:


            print(
                "  None."
            )


        for row in ims_matches:


            print(
                "\n  ---"
            )


            print(

                f"  IMS row "
                f"{row['source_row']}"
            )


            print(

                f"  Transaction Date: "
                f"{row['transaction_date']}"
            )


            print(

                f"  Check/Ref: "
                f"{row['check_or_ref']}"
            )


            print(

                f"  Description: "
                f"{row['description']}"
            )


            print(

                f"  Credit: "
                f"{row['credit']}"
            )


            print(

                f"  Date Cleared: "
                f"{row['date_cleared']}"
            )


            print(

                "  Included in human control: "
                f"{row['included_in_human_control']}"
            )


            print(

                f"  Classification: "
                f"{row['date_cleared_class']}"
            )


    print(
        "\n========================================"
    )


    print(
        "VARIANCE INSPECTION COMPLETE"
    )


    print(
        "========================================"
    )


    print(
        "\nNo source data or production logic "
        "was modified."
    )


if __name__ == "__main__":

    main()