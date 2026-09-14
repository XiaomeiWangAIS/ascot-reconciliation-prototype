# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
#
# EXTRACT HISTORICAL AIC WF CATEGORY METADATA
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# Historically, Ascot encoded transaction categories using
# Excel fill colors.
#
# We now know specifically:
#
#     YELLOW = IMS
#
# Color is useful historical evidence, but it should NOT remain
# the machine's accounting logic.
#
# Therefore this script converts:
#
#     Excel yellow fill
#
# into an explicit field:
#
#     legacy_category = "IMS"
#
#
# OUTPUT:
#
# data/processed/
#     aic_wf_legacy_categories_all_months.csv
#
# data/processed/
#     aic_wf_legacy_category_manifest.json
#
#
# IMPORTANT
# ------------------------------------------------------------
#
# This script does NOT modify the original workbook.
#
# It does NOT infer IMS from transaction description.
#
# It uses the actual historical legend cell labelled "IMS"
# in each workbook and compares transaction-cell fills to that
# legend fill.
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import csv
import json
import sys
import zipfile

from decimal import Decimal
from pathlib import Path


# ============================================================
# MAKE THIS FOLDER IMPORTABLE
# ============================================================
#
# We reuse the memory-safe XLSX functions from:
#
#     inspect_current_month_ims_wf_control.py
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

    find_workbooks,

    read_shared_strings,

    read_style_fills,

    read_sheet_paths,

    stream_rows,

    value,

    discover_wf_structure,

    to_decimal,

    money_text,
)


# ============================================================
# OUTPUT PATHS
# ============================================================

PROCESSED_FOLDER = Path(
    "data/processed"
)


OUTPUT_PATH = (
    PROCESSED_FOLDER
    / "aic_wf_legacy_categories_all_months.csv"
)


MANIFEST_PATH = (
    PROCESSED_FOLDER
    / "aic_wf_legacy_category_manifest.json"
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
# EXTRACT ONE MONTH
# ============================================================

def extract_one_month(
    period,
    workbook_path,
):
    """
    Extract an explicit historical IMS classification from
    one AIC WF worksheet.
    """

    with zipfile.ZipFile(
        workbook_path,
        "r",
    ) as archive:


        # ----------------------------------------------------
        # XLSX SUPPORT STRUCTURES
        # ----------------------------------------------------

        shared_strings = read_shared_strings(
            archive
        )


        style_map = read_style_fills(
            archive
        )


        sheet_paths = read_sheet_paths(
            archive
        )


        wf_sheet_path = sheet_paths[
            "AIC WF"
        ]


        # ----------------------------------------------------
        # DISCOVER HEADER AND THE REAL HISTORICAL IMS FILL
        # ----------------------------------------------------
        #
        # We do not assume an RGB value for yellow.
        #
        # We locate the actual legend cell labelled:
        #
        #     IMS
        #
        # and use that cell's fill signature.
        # ----------------------------------------------------

        (
            header_row,
            ims_fill,
            ims_legend_cell,
        ) = discover_wf_structure(

            archive,

            wf_sheet_path,

            shared_strings,

            style_map,
        )


        records = []


        ims_count = 0

        ims_total = ZERO


        # ----------------------------------------------------
        # STREAM ALL TRANSACTION ROWS
        # ----------------------------------------------------

        for (
            row_number,
            cells,
        ) in stream_rows(

            archive,

            wf_sheet_path,

            shared_strings,

            style_map,
        ):


            if row_number <= header_row:

                continue


            # A transaction row must have an As-Of Date.
            if not clean_text(

                value(
                    cells,
                    "A",
                )
            ):

                continue


            # And a bank transaction description.
            if not clean_text(

                value(
                    cells,
                    "D",
                )
            ):

                continue


            # The human control uses column G.
            g_cell = cells.get(
                "G"
            )


            if g_cell is None:

                continue


            g_amount = to_decimal(

                g_cell.get(
                    "value"
                )
            )


            # Ignore nonnumeric control/helper rows.
            if g_amount is None:

                continue


            # ------------------------------------------------
            # EXPLICIT HISTORICAL CATEGORY
            # ------------------------------------------------

            is_legacy_ims = (

                g_cell.get(
                    "fill"
                )
                == ims_fill
            )


            legacy_category = (

                "IMS"

                if is_legacy_ims

                else ""
            )


            # ------------------------------------------------
            # CONTROL AMOUNT
            # ------------------------------------------------
            #
            # Keep the exact WF column-G amount used in the
            # historical human control.
            # ------------------------------------------------

            wf_control_amount = (
                g_amount
            )


            if is_legacy_ims:

                ims_count += 1

                ims_total += (
                    wf_control_amount
                )


            # ------------------------------------------------
            # BUILD MACHINE-READABLE RECORD
            # ------------------------------------------------

            records.append(

                {
                    # ----------------------------------------
                    # PROVENANCE
                    # ----------------------------------------

                    "transaction_id":
                        (
                            f"WF-{period}-"
                            f"R{row_number}"
                        ),

                    "accounting_period":
                        period,

                    "source_workbook":
                        workbook_path.name,

                    "source_sheet":
                        "AIC WF",

                    "source_row":
                        row_number,

                    # ----------------------------------------
                    # BANK TRANSACTION INFORMATION
                    # ----------------------------------------

                    "as_of_date_raw":
                        value(
                            cells,
                            "A",
                        ),

                    "transaction_description":
                        clean_text(

                            value(
                                cells,
                                "D",
                            )
                        ),

                    "debit_amount":
                        money_text(

                            to_decimal(

                                value(
                                    cells,
                                    "E",
                                )
                            )

                            or ZERO
                        ),

                    "credit_amount":
                        money_text(

                            to_decimal(

                                value(
                                    cells,
                                    "F",
                                )
                            )

                            or ZERO
                        ),

                    "wf_control_amount":
                        money_text(
                            wf_control_amount
                        ),

                    "check_number":
                        value(
                            cells,
                            "H",
                        ),

                    "descriptive_text_1":
                        clean_text(

                            value(
                                cells,
                                "I",
                            )
                        ),

                    # ----------------------------------------
                    # EXPLICIT CATEGORY LAYER
                    # ----------------------------------------

                    "legacy_category":
                        legacy_category,

                    "category_source":
                        (
                            "historical_wf_fill"

                            if is_legacy_ims

                            else ""
                        ),

                    "is_legacy_ims":
                        is_legacy_ims,

                    # ----------------------------------------
                    # AUDITABILITY ONLY
                    # ----------------------------------------
                    #
                    # Keep the legacy fill signature so the
                    # classification can be traced back to the
                    # workbook.
                    #
                    # The reconciliation logic should NOT use
                    # this field.
                    # ----------------------------------------

                    "legacy_fill_signature":
                        repr(

                            g_cell.get(
                                "fill"
                            )
                        ),
                }
            )


        return {

            "accounting_period":
                period,

            "source_workbook":
                workbook_path.name,

            "wf_header_row":
                header_row,

            "ims_legend_cell":
                ims_legend_cell,

            "transaction_count":
                len(
                    records
                ),

            "legacy_ims_transaction_count":
                ims_count,

            "legacy_ims_total":
                money_text(
                    ims_total
                ),

            "records":
                records,
        }


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "ASCOT AIC WF LEGACY CATEGORY EXTRACTION"
    )


    print(
        "Historical yellow -> explicit category = IMS"
    )


    # ========================================================
    # FIND THE ACTUAL JAN-JUL RESOURCE PRO WORKBOOKS
    # ========================================================

    workbooks = find_workbooks()


    if not workbooks:

        raise FileNotFoundError(

            "No Resource Pro workbooks containing both "
            "AIC WF and AIC IMS were found."
        )


    print(
        f"\nFound {len(workbooks)} workbook(s)."
    )


    # ========================================================
    # CONSOLIDATED RESULTS
    # ========================================================

    all_records = []

    manifest = []


    # ========================================================
    # PROCESS IN TRUE ACCOUNTING-PERIOD ORDER
    # ========================================================

    for (
        period,
        workbook_path,
    ) in workbooks:


        print(
            "\n========================================"
        )


        print(
            f"{period} | "
            f"{workbook_path.name}"
        )


        print(
            "========================================"
        )


        result = extract_one_month(

            period,

            workbook_path,
        )


        all_records.extend(

            result[
                "records"
            ]
        )


        manifest.append(

            {
                "accounting_period":
                    result[
                        "accounting_period"
                    ],

                "source_workbook":
                    result[
                        "source_workbook"
                    ],

                "wf_header_row":
                    result[
                        "wf_header_row"
                    ],

                "ims_legend_cell":
                    result[
                        "ims_legend_cell"
                    ],

                "transaction_count":
                    result[
                        "transaction_count"
                    ],

                "legacy_ims_transaction_count":
                    result[
                        "legacy_ims_transaction_count"
                    ],

                "legacy_ims_total":
                    result[
                        "legacy_ims_total"
                    ],
            }
        )


        print(

            "AIC WF transactions: "
            f"{result['transaction_count']}"
        )


        print(

            "Explicit legacy IMS transactions: "
            f"{result['legacy_ims_transaction_count']}"
        )


        print(

            "Explicit legacy IMS total: "
            f"{result['legacy_ims_total']}"
        )


        print(

            "IMS legend source: "
            f"{result['ims_legend_cell']}"
        )


    # ========================================================
    # WRITE CONSOLIDATED EXPLICIT CATEGORY TABLE
    # ========================================================

    write_csv(

        OUTPUT_PATH,

        all_records,
    )


    # ========================================================
    # WRITE MANIFEST
    # ========================================================

    overall = {

        "purpose":
            (
                "Convert historical AIC WF Excel IMS/yellow "
                "presentation classification into explicit "
                "machine-readable category metadata."
            ),

        "category_rule":
            (
                "legacy_category='IMS' when the AIC WF "
                "column-G cell has the same fill as the "
                "workbook legend cell labelled IMS."
            ),

        "important_design_rule":
            (
                "Legacy fill is provenance only after "
                "extraction. Downstream reconciliation must "
                "use legacy_category/is_legacy_ims rather "
                "than Excel color."
            ),

        "period_count":
            len(
                manifest
            ),

        "total_wf_transactions":
            len(
                all_records
            ),

        "total_legacy_ims_transactions":
            sum(

                month[
                    "legacy_ims_transaction_count"
                ]

                for month
                in manifest
            ),

        "monthly_results":
            manifest,
    }


    with MANIFEST_PATH.open(

        "w",

        encoding="utf-8",

    ) as file:


        json.dump(

            overall,

            file,

            indent=2,

            ensure_ascii=False,
        )


    # ========================================================
    # FINAL SUMMARY
    # ========================================================

    print(
        "\n========================================"
    )


    print(
        "LEGACY CATEGORY EXTRACTION COMPLETE"
    )


    print(
        "========================================"
    )


    print(

        "Total AIC WF transactions: "
        f"{len(all_records)}"
    )


    print(

        "Total transactions explicitly classified IMS: "
        f"{overall['total_legacy_ims_transactions']}"
    )


    print(
        "\nMonthly IMS category:"
    )


    for month in manifest:


        print(

            f"  {month['accounting_period']} | "
            f"IMS rows "
            f"{month['legacy_ims_transaction_count']} | "
            f"IMS total "
            f"{month['legacy_ims_total']}"
        )


    print(
        "\nOutputs:"
    )


    print(
        "data/processed/"
        "aic_wf_legacy_categories_all_months.csv"
    )


    print(
        "data/processed/"
        "aic_wf_legacy_category_manifest.json"
    )


    print(
        "\nDownstream code should now use "
        "legacy_category='IMS', not yellow color."
    )


if __name__ == "__main__":

    main()