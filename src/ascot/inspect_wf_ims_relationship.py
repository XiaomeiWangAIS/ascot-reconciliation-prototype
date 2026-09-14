# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# EMPIRICAL INSPECTION:
# AIC WF <-> AIC IMS RELATIONSHIP
# ============================================================
#
# THIS IS NOT A RECONCILIATION MODULE.
#
# PURPOSE
# ------------------------------------------------------------
#
# Before writing reconcile_wf_to_ims(), inspect the actual
# relationship between the two independently sanitized data
# sources.
#
# Questions:
#
# 1. Does WF Check Number correspond to IMS CheckOrRef?
#
# 2. Does the bank amount correspond to the absolute IMS
#    transaction amount?
#
# 3. Does the WF bank date correspond to IMS Date Cleared?
#
# 4. Are matches usually within the same monthly workbook,
#    or do transactions clear across months?
#
# 5. Which WF transaction types appear in IMS?
#
# 6. Are ZBA/sweep transactions represented in IMS?
#
# 7. What happens to IMS outstanding items?
#
# 8. What happens to IMS voids / returned items?
#
# 9. How often does one IMS transaction contain multiple
#    accounting allocation lines?
#
# 10. Do WF GL/cost-center fields agree with one of the IMS
#     allocations?
#
# IMPORTANT
# ------------------------------------------------------------
#
# This script deliberately does NOT:
#
#     - force one-to-one matching,
#     - use fuzzy matching,
#     - use an LLM,
#     - decide that an unmatched row is an error,
#     - assume same-month matching,
#     - assume every WF row should exist in IMS.
#
# It profiles candidate relationships first.
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import csv
import json
import re

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROCESSED_FOLDER = Path(
    "data/processed"
)


WF_PATH = (
    PROCESSED_FOLDER
    / "aic_wf_all_months_transactions.csv"
)


IMS_TRANSACTION_PATH = (
    PROCESSED_FOLDER
    / "aic_ims_all_months_transactions.csv"
)


IMS_ALLOCATION_PATH = (
    PROCESSED_FOLDER
    / "aic_ims_all_months_allocations.csv"
)


OUTPUT_FOLDER = (
    PROCESSED_FOLDER
    / "inspection"
    / "wf_to_ims"
)


OUTPUT_FOLDER.mkdir(
    parents=True,
    exist_ok=True,
)


REPORT_PATH = (
    OUTPUT_FOLDER
    / "wf_ims_relationship_inspection.json"
)


WF_PROFILE_PATH = (
    OUTPUT_FOLDER
    / "wf_candidate_profile.csv"
)


IMS_PROFILE_PATH = (
    OUTPUT_FOLDER
    / "ims_candidate_profile.csv"
)


UNIQUE_CANDIDATES_PATH = (
    OUTPUT_FOLDER
    / "unique_strong_candidate_pairs.csv"
)


WF_TYPE_SUMMARY_PATH = (
    OUTPUT_FOLDER
    / "wf_transaction_type_summary.csv"
)


IMS_STATUS_SUMMARY_PATH = (
    OUTPUT_FOLDER
    / "ims_status_summary.csv"
)


# ============================================================
# MONEY
# ============================================================

CENT = Decimal(
    "0.01"
)


ZERO = Decimal(
    "0.00"
)


def money_decimal(value):
    """
    Convert monetary values to two-decimal Decimal.

    Blank -> 0.00.
    """

    if value in {
        None,
        "",
    }:

        return ZERO


    try:

        value = Decimal(
            str(value)
        )


    except InvalidOperation:

        return ZERO


    return value.quantize(
        CENT,
        rounding=ROUND_HALF_UP,
    )


def money_text(value):
    """
    Stable money representation.
    """

    return format(
        value.quantize(
            CENT
        ),
        ".2f",
    )


# ============================================================
# BASIC TEXT NORMALIZATION
# ============================================================

def normalize_text(value):
    """
    Trim spaces and compare case-insensitively.
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
    Normalize:

        YYYY/MM/DD
        YYYY-MM-DD
        YYYY-MM-DD HH:MM:SS

    into:

        YYYY-MM-DD
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


    if len(text) >= 10:

        return text[:10]


    return text


# ============================================================
# IDENTIFIER NORMALIZATION
# ============================================================

def normalize_identifier_text(value):
    """
    Preserve identifier text while removing Excel's simple
    trailing '.0' artifact.
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
    Normalize check/reference formatting.

    Leading zeros are removed for numeric identifiers.

    All-zero placeholders become None.

    This is the same principle empirically validated in the
    Previous Day -> WF relationship.
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
# FILE HELPERS
# ============================================================

def read_csv(path):

    if not path.exists():

        raise FileNotFoundError(
            f"Required file not found: {path}"
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
# WF FEATURES
# ============================================================

def standardize_wf(row):
    """
    Standardize one AIC WF bank transaction.
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


    if debit != ZERO:

        direction = (
            "DEBIT"
        )

        amount = abs(
            debit
        )


    elif credit != ZERO:

        direction = (
            "CREDIT"
        )

        amount = abs(
            credit
        )


    else:

        direction = None

        amount = ZERO


    period = row.get(
        "accounting_period"
    )


    source_row = row.get(
        "source_row"
    )


    transaction_id = (

        f"WF-{period}-R{source_row}"
    )


    return {

        "transaction_id":
            transaction_id,

        "accounting_period":
            period,

        "source_row":
            source_row,

        "date":
            normalize_date(
                row.get(
                    "as_of_date"
                )
            ),

        "direction":
            direction,

        "amount":
            amount,

        "amount_text":
            money_text(
                amount
            ),

        "check_raw":
            normalize_identifier_text(
                row.get(
                    "check_number"
                )
            ),

        "check_key":
            identifier_match_key(
                row.get(
                    "check_number"
                )
            ),

        "transaction_description":
            normalize_text(
                row.get(
                    "transaction_description"
                )
            ),

        "descriptive_text":
            normalize_text(
                row.get(
                    "descriptive_text_1"
                )
            ),

        "section":
            row.get(
                "section"
            ),

        "gl_account":
            normalize_identifier_text(
                row.get(
                    "gl_account"
                )
            ),

        "cost_center":
            normalize_identifier_text(
                row.get(
                    "cost_center"
                )
            ),

        "accounting_description":
            normalize_text(
                row.get(
                    "accounting_description"
                )
            ),

        "backup":
            normalize_text(
                row.get(
                    "backup"
                )
            ),
    }


# ============================================================
# IMS CLEARED DATES
# ============================================================

def parse_cleared_dates(value):
    """
    Sanitizer stores multiple parsed dates separated by |.

    Return a set of normalized dates.
    """

    text = str(
        value or ""
    ).strip()


    if not text:

        return set()


    return {

        normalize_date(
            part
        )

        for part
        in text.split(
            "|"
        )

        if normalize_date(
            part
        )
    }


# ============================================================
# IMS FEATURES
# ============================================================

def standardize_ims(row):
    """
    Standardize one actual IMS source transaction.

    NOTE:
    IMS Debit/Credit semantics differ from the bank report.

    Therefore this inspection compares ABSOLUTE AMOUNT rather
    than assuming the source-side direction has the same
    accounting meaning.
    """

    signed_amount = money_decimal(

        row.get(
            "source_signed_amount"
        )
    )


    amount = abs(
        signed_amount
    )


    transaction_id = row.get(
        "transaction_id"
    )


    return {

        "transaction_id":
            transaction_id,

        "accounting_period":
            row.get(
                "accounting_period"
            ),

        "source_row":
            row.get(
                "source_row"
            ),

        "row_kind":
            row.get(
                "row_kind"
            ),

        "transaction_date":
            normalize_date(
                row.get(
                    "transaction_datetime"
                )
            ),

        "check_raw":
            normalize_identifier_text(
                row.get(
                    "check_or_ref"
                )
            ),

        "check_key":
            identifier_match_key(
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

        "signed_amount":
            signed_amount,

        "amount":
            amount,

        "amount_text":
            money_text(
                amount
            ),

        "date_cleared_raw":
            row.get(
                "date_cleared_raw"
            ),

        "cleared_status":
            row.get(
                "cleared_status"
            ),

        "cleared_dates":
            parse_cleared_dates(
                row.get(
                    "cleared_dates"
                )
            ),

        "account_raw":
            normalize_identifier_text(
                row.get(
                    "account_raw"
                )
            ),

        "cost_center_raw":
            normalize_identifier_text(
                row.get(
                    "cost_center_raw"
                )
            ),

        "workpaper_description":
            normalize_text(
                row.get(
                    "workpaper_description_raw"
                )
            ),
    }


# ============================================================
# IMS ALLOCATION SUMMARY
# ============================================================

def build_allocation_summary(
    allocation_rows,
):
    """
    Aggregate all IMS accounting allocations by transaction.

    This lets us inspect whether WF GL/cost-center values appear
    anywhere inside the IMS allocation structure.
    """

    grouped = defaultdict(
        list
    )


    for row in allocation_rows:

        transaction_id = row.get(
            "transaction_id"
        )


        if transaction_id:

            grouped[
                transaction_id
            ].append(
                row
            )


    summary = {}


    for (
        transaction_id,
        rows,
    ) in grouped.items():


        accounts = {

            normalize_identifier_text(
                row.get(
                    "account"
                )
            )

            for row
            in rows

            if normalize_identifier_text(
                row.get(
                    "account"
                )
            )
        }


        cost_centers = {

            normalize_identifier_text(
                row.get(
                    "cost_center"
                )
            )

            for row
            in rows

            if normalize_identifier_text(
                row.get(
                    "cost_center"
                )
            )
        }


        numeric_amounts = []


        for row in rows:


            raw_amount = row.get(
                "allocation_amount_numeric"
            )


            if raw_amount not in {
                None,
                "",
            }:


                numeric_amounts.append(

                    money_decimal(
                        raw_amount
                    )
                )


        summary[
            transaction_id
        ] = {

            "allocation_count":
                len(
                    rows
                ),

            "accounts":
                accounts,

            "cost_centers":
                cost_centers,

            "allocation_total":
                sum(
                    numeric_amounts,
                    ZERO,
                ),

            "allocation_rows":
                rows,
        }


    return summary


# ============================================================
# CREATE INDEXES
# ============================================================

def build_indexes(
    ims_records,
):
    """
    Build deterministic candidate indexes.

    These are used only for relationship inspection.
    """

    by_ref_amount = defaultdict(
        list
    )


    by_ref = defaultdict(
        list
    )


    by_amount_cleared_date = defaultdict(
        list
    )


    by_amount_transaction_date = defaultdict(
        list
    )


    by_amount = defaultdict(
        list
    )


    for ims in ims_records:


        amount_text = ims[
            "amount_text"
        ]


        reference = ims[
            "check_key"
        ]


        # ----------------------------------------------------
        # REFERENCE + AMOUNT
        # ----------------------------------------------------

        if reference:

            by_ref_amount[
                (
                    reference,
                    amount_text,
                )
            ].append(
                ims
            )


            by_ref[
                reference
            ].append(
                ims
            )


        # ----------------------------------------------------
        # AMOUNT + CLEARED DATE
        # ----------------------------------------------------

        for cleared_date in ims[
            "cleared_dates"
        ]:


            by_amount_cleared_date[
                (
                    amount_text,
                    cleared_date,
                )
            ].append(
                ims
            )


        # ----------------------------------------------------
        # AMOUNT + TRANSACTION DATE
        # ----------------------------------------------------

        if ims[
            "transaction_date"
        ]:


            by_amount_transaction_date[
                (
                    amount_text,
                    ims[
                        "transaction_date"
                    ],
                )
            ].append(
                ims
            )


        # ----------------------------------------------------
        # AMOUNT ONLY
        # ----------------------------------------------------

        by_amount[
            amount_text
        ].append(
            ims
        )


    return {

        "ref_amount":
            by_ref_amount,

        "ref":
            by_ref,

        "amount_cleared_date":
            by_amount_cleared_date,

        "amount_transaction_date":
            by_amount_transaction_date,

        "amount":
            by_amount,
    }


# ============================================================
# CANDIDATE IDS
# ============================================================

def unique_candidate_ids(records):
    """
    Prevent the same IMS transaction appearing multiple times
    in one candidate list.
    """

    return sorted(

        {

            record[
                "transaction_id"
            ]

            for record
            in records
        }
    )


# ============================================================
# BUILD WF CANDIDATE PROFILE
# ============================================================

def profile_wf_transactions(
    wf_records,
    ims_records,
    indexes,
    ims_by_id,
    allocation_summary,
):
    """
    Profile every WF transaction against the full IMS
    population across ALL months.

    No candidate is declared a production match.
    """

    profiles = []


    unique_strong_pairs = []


    for wf in wf_records:


        # ====================================================
        # CANDIDATE SETS
        # ====================================================

        ref_amount_candidates = []


        if wf[
            "check_key"
        ]:


            ref_amount_candidates = (

                indexes[
                    "ref_amount"
                ].get(

                    (
                        wf[
                            "check_key"
                        ],

                        wf[
                            "amount_text"
                        ],
                    ),

                    [],
                )
            )


        ref_candidates = []


        if wf[
            "check_key"
        ]:


            ref_candidates = (

                indexes[
                    "ref"
                ].get(

                    wf[
                        "check_key"
                    ],

                    [],
                )
            )


        amount_clear_candidates = (

            indexes[
                "amount_cleared_date"
            ].get(

                (
                    wf[
                        "amount_text"
                    ],

                    wf[
                        "date"
                    ],
                ),

                [],
            )
        )


        amount_transaction_date_candidates = (

            indexes[
                "amount_transaction_date"
            ].get(

                (
                    wf[
                        "amount_text"
                    ],

                    wf[
                        "date"
                    ],
                ),

                [],
            )
        )


        amount_candidates = (

            indexes[
                "amount"
            ].get(

                wf[
                    "amount_text"
                ],

                [],
            )
        )


        ref_amount_ids = unique_candidate_ids(
            ref_amount_candidates
        )


        ref_ids = unique_candidate_ids(
            ref_candidates
        )


        amount_clear_ids = unique_candidate_ids(
            amount_clear_candidates
        )


        amount_transaction_date_ids = (
            unique_candidate_ids(

                amount_transaction_date_candidates
            )
        )


        amount_ids = unique_candidate_ids(
            amount_candidates
        )


        # ====================================================
        # INSPECTION CLASSIFICATION
        # ========================================================
        #
        # Again: "candidate", NOT final "match".
        # ====================================================

        if len(
            ref_amount_ids
        ) == 1:

            candidate_class = (
                "UNIQUE_REFERENCE_PLUS_AMOUNT"
            )


            strongest_ids = (
                ref_amount_ids
            )


        elif len(
            ref_amount_ids
        ) > 1:

            candidate_class = (
                "MULTIPLE_REFERENCE_PLUS_AMOUNT"
            )


            strongest_ids = (
                ref_amount_ids
            )


        elif len(
            amount_clear_ids
        ) == 1:

            candidate_class = (
                "UNIQUE_AMOUNT_PLUS_CLEARED_DATE"
            )


            strongest_ids = (
                amount_clear_ids
            )


        elif len(
            amount_clear_ids
        ) > 1:

            candidate_class = (
                "MULTIPLE_AMOUNT_PLUS_CLEARED_DATE"
            )


            strongest_ids = (
                amount_clear_ids
            )


        elif len(
            ref_ids
        ) == 1:

            candidate_class = (
                "UNIQUE_REFERENCE_DIFFERENT_AMOUNT"
            )


            strongest_ids = (
                ref_ids
            )


        elif len(
            ref_ids
        ) > 1:

            candidate_class = (
                "MULTIPLE_REFERENCE_DIFFERENT_AMOUNT"
            )


            strongest_ids = (
                ref_ids
            )


        elif len(
            amount_transaction_date_ids
        ) == 1:

            candidate_class = (
                "UNIQUE_AMOUNT_PLUS_TRANSACTION_DATE"
            )


            strongest_ids = (
                amount_transaction_date_ids
            )


        elif len(
            amount_transaction_date_ids
        ) > 1:

            candidate_class = (
                "MULTIPLE_AMOUNT_PLUS_TRANSACTION_DATE"
            )


            strongest_ids = (
                amount_transaction_date_ids
            )


        else:

            candidate_class = (
                "NO_STRONG_CANDIDATE"
            )


            strongest_ids = []


        # ====================================================
        # PROFILE A UNIQUE STRONG CANDIDATE
        # ====================================================

        unique_candidate = None


        if (

            candidate_class
            in {
                "UNIQUE_REFERENCE_PLUS_AMOUNT",
                "UNIQUE_AMOUNT_PLUS_CLEARED_DATE",
            }

            and len(
                strongest_ids
            ) == 1
        ):


            unique_candidate = ims_by_id[
                strongest_ids[
                    0
                ]
            ]


        # ====================================================
        # DATE RELATIONSHIP
        # ====================================================

        if unique_candidate:


            wf_date_in_cleared_dates = (

                wf[
                    "date"
                ]
                in unique_candidate[
                    "cleared_dates"
                ]
            )


            transaction_date_equal = (

                wf[
                    "date"
                ]
                == unique_candidate[
                    "transaction_date"
                ]
            )


            same_accounting_period = (

                wf[
                    "accounting_period"
                ]

                == unique_candidate[
                    "accounting_period"
                ]
            )


            ims_status = (
                unique_candidate[
                    "cleared_status"
                ]
            )


            ims_row_kind = (
                unique_candidate[
                    "row_kind"
                ]
            )


            ims_method = (
                unique_candidate[
                    "method"
                ]
            )


            ims_payment_type = (
                unique_candidate[
                    "payment_type"
                ]
            )


            allocation_info = allocation_summary.get(

                unique_candidate[
                    "transaction_id"
                ],

                {
                    "allocation_count":
                        0,

                    "accounts":
                        set(),

                    "cost_centers":
                        set(),

                    "allocation_total":
                        ZERO,
                },
            )


            wf_gl_matches_any_ims_allocation = (

                bool(
                    wf[
                        "gl_account"
                    ]
                )

                and

                wf[
                    "gl_account"
                ]
                in allocation_info[
                    "accounts"
                ]
            )


            wf_cost_matches_any_ims_allocation = (

                bool(
                    wf[
                        "cost_center"
                    ]
                )

                and

                wf[
                    "cost_center"
                ]
                in allocation_info[
                    "cost_centers"
                ]
            )


            unique_strong_pairs.append(

                {
                    "wf_transaction_id":
                        wf[
                            "transaction_id"
                        ],

                    "wf_accounting_period":
                        wf[
                            "accounting_period"
                        ],

                    "wf_source_row":
                        wf[
                            "source_row"
                        ],

                    "wf_date":
                        wf[
                            "date"
                        ],

                    "wf_section":
                        wf[
                            "section"
                        ],

                    "wf_transaction_description":
                        wf[
                            "transaction_description"
                        ],

                    "wf_amount":
                        wf[
                            "amount_text"
                        ],

                    "wf_check_raw":
                        wf[
                            "check_raw"
                        ],

                    "wf_check_key":
                        wf[
                            "check_key"
                        ],

                    "ims_transaction_id":
                        unique_candidate[
                            "transaction_id"
                        ],

                    "ims_accounting_period":
                        unique_candidate[
                            "accounting_period"
                        ],

                    "ims_source_row":
                        unique_candidate[
                            "source_row"
                        ],

                    "ims_transaction_date":
                        unique_candidate[
                            "transaction_date"
                        ],

                    "ims_check_raw":
                        unique_candidate[
                            "check_raw"
                        ],

                    "ims_check_key":
                        unique_candidate[
                            "check_key"
                        ],

                    "ims_amount":
                        unique_candidate[
                            "amount_text"
                        ],

                    "ims_cleared_status":
                        ims_status,

                    "ims_cleared_dates":
                        "|".join(

                            sorted(
                                unique_candidate[
                                    "cleared_dates"
                                ]
                            )
                        ),

                    "candidate_basis":
                        candidate_class,

                    "same_accounting_period":
                        same_accounting_period,

                    "wf_date_in_ims_cleared_dates":
                        wf_date_in_cleared_dates,

                    "wf_date_equals_ims_transaction_date":
                        transaction_date_equal,

                    "ims_row_kind":
                        ims_row_kind,

                    "ims_method":
                        ims_method,

                    "ims_payment_type":
                        ims_payment_type,

                    "ims_allocation_count":
                        allocation_info[
                            "allocation_count"
                        ],

                    "wf_gl_account":
                        wf[
                            "gl_account"
                        ],

                    "ims_allocation_accounts":
                        "|".join(

                            sorted(
                                allocation_info[
                                    "accounts"
                                ]
                            )
                        ),

                    "wf_gl_matches_any_ims_allocation":
                        wf_gl_matches_any_ims_allocation,

                    "wf_cost_center":
                        wf[
                            "cost_center"
                        ],

                    "ims_allocation_cost_centers":
                        "|".join(

                            sorted(
                                allocation_info[
                                    "cost_centers"
                                ]
                            )
                        ),

                    "wf_cost_matches_any_ims_allocation":
                        wf_cost_matches_any_ims_allocation,
                }
            )


        # ====================================================
        # WF PROFILE OUTPUT
        # ====================================================

        profiles.append(

            {
                "wf_transaction_id":
                    wf[
                        "transaction_id"
                    ],

                "accounting_period":
                    wf[
                        "accounting_period"
                    ],

                "source_row":
                    wf[
                        "source_row"
                    ],

                "date":
                    wf[
                        "date"
                    ],

                "section":
                    wf[
                        "section"
                    ],

                "transaction_description":
                    wf[
                        "transaction_description"
                    ],

                "amount":
                    wf[
                        "amount_text"
                    ],

                "check_raw":
                    wf[
                        "check_raw"
                    ],

                "check_key":
                    wf[
                        "check_key"
                    ],

                "reference_plus_amount_candidate_count":
                    len(
                        ref_amount_ids
                    ),

                "reference_only_candidate_count":
                    len(
                        ref_ids
                    ),

                "amount_plus_cleared_date_candidate_count":
                    len(
                        amount_clear_ids
                    ),

                "amount_plus_transaction_date_candidate_count":
                    len(
                        amount_transaction_date_ids
                    ),

                "amount_only_candidate_count":
                    len(
                        amount_ids
                    ),

                "candidate_class":
                    candidate_class,

                "strongest_candidate_ids":
                    "|".join(
                        strongest_ids
                    ),
            }
        )


    return (
        profiles,
        unique_strong_pairs,
    )


# ============================================================
# IMS-SIDE PROFILE
# ============================================================

def profile_ims_transactions(
    ims_records,
    wf_records,
):
    """
    Look from IMS toward WF.

    This is especially useful for:

        outstanding checks,
        voids,
        returned items,
        IMS items that never cleared.
    """

    wf_by_ref_amount = defaultdict(
        list
    )


    wf_by_amount_date = defaultdict(
        list
    )


    for wf in wf_records:


        if wf[
            "check_key"
        ]:


            wf_by_ref_amount[

                (
                    wf[
                        "check_key"
                    ],

                    wf[
                        "amount_text"
                    ],
                )

            ].append(
                wf
            )


        wf_by_amount_date[

            (
                wf[
                    "amount_text"
                ],

                wf[
                    "date"
                ],
            )

        ].append(
            wf
        )


    profiles = []


    for ims in ims_records:


        ref_amount_candidates = []


        if ims[
            "check_key"
        ]:


            ref_amount_candidates = (

                wf_by_ref_amount.get(

                    (
                        ims[
                            "check_key"
                        ],

                        ims[
                            "amount_text"
                        ],
                    ),

                    [],
                )
            )


        clear_date_candidate_ids = set()


        for cleared_date in ims[
            "cleared_dates"
        ]:


            for wf in wf_by_amount_date.get(

                (
                    ims[
                        "amount_text"
                    ],

                    cleared_date,
                ),

                [],
            ):


                clear_date_candidate_ids.add(

                    wf[
                        "transaction_id"
                    ]
                )


        profiles.append(

            {
                "ims_transaction_id":
                    ims[
                        "transaction_id"
                    ],

                "accounting_period":
                    ims[
                        "accounting_period"
                    ],

                "source_row":
                    ims[
                        "source_row"
                    ],

                "row_kind":
                    ims[
                        "row_kind"
                    ],

                "transaction_date":
                    ims[
                        "transaction_date"
                    ],

                "check_raw":
                    ims[
                        "check_raw"
                    ],

                "check_key":
                    ims[
                        "check_key"
                    ],

                "amount":
                    ims[
                        "amount_text"
                    ],

                "method":
                    ims[
                        "method"
                    ],

                "payment_type":
                    ims[
                        "payment_type"
                    ],

                "cleared_status":
                    ims[
                        "cleared_status"
                    ],

                "cleared_dates":
                    "|".join(

                        sorted(
                            ims[
                                "cleared_dates"
                            ]
                        )
                    ),

                "wf_reference_plus_amount_candidate_count":
                    len(
                        {
                            wf[
                                "transaction_id"
                            ]

                            for wf
                            in ref_amount_candidates
                        }
                    ),

                "wf_amount_plus_cleared_date_candidate_count":
                    len(
                        clear_date_candidate_ids
                    ),
            }
        )


    return profiles


# ============================================================
# WF TRANSACTION-TYPE SUMMARY
# ============================================================

def build_wf_type_summary(
    wf_profiles,
):
    """
    Which kinds of WF bank activity appear to have strong IMS
    candidate relationships?
    """

    grouped = defaultdict(
        list
    )


    for profile in wf_profiles:

        key = (

            profile[
                "section"
            ],

            profile[
                "transaction_description"
            ],
        )


        grouped[
            key
        ].append(
            profile
        )


    output = []


    for (
        section,
        transaction_description,
    ), rows in sorted(

        grouped.items(),

        key=lambda item: (

            str(
                item[
                    0
                ][
                    0
                ]
            ),

            str(
                item[
                    0
                ][
                    1
                ]
            ),
        ),
    ):


        class_counts = Counter(

            row[
                "candidate_class"
            ]

            for row
            in rows
        )


        unique_ref_amount = (
            class_counts[
                "UNIQUE_REFERENCE_PLUS_AMOUNT"
            ]
        )


        unique_amount_clear = (
            class_counts[
                "UNIQUE_AMOUNT_PLUS_CLEARED_DATE"
            ]
        )


        strong_unique = (

            unique_ref_amount

            + unique_amount_clear
        )


        output.append(

            {
                "section":
                    section,

                "transaction_description":
                    transaction_description,

                "wf_transaction_count":
                    len(
                        rows
                    ),

                "unique_reference_plus_amount":
                    unique_ref_amount,

                "unique_amount_plus_cleared_date":
                    unique_amount_clear,

                "strong_unique_candidate_count":
                    strong_unique,

                "strong_unique_candidate_pct":
                    round(

                        strong_unique
                        / len(
                            rows
                        )
                        * 100,

                        2,
                    ),

                "multiple_reference_plus_amount":
                    class_counts[
                        "MULTIPLE_REFERENCE_PLUS_AMOUNT"
                    ],

                "multiple_amount_plus_cleared_date":
                    class_counts[
                        "MULTIPLE_AMOUNT_PLUS_CLEARED_DATE"
                    ],

                "unique_reference_different_amount":
                    class_counts[
                        "UNIQUE_REFERENCE_DIFFERENT_AMOUNT"
                    ],

                "no_strong_candidate":
                    class_counts[
                        "NO_STRONG_CANDIDATE"
                    ],
            }
        )


    return output


# ============================================================
# IMS STATUS SUMMARY
# ============================================================

def build_ims_status_summary(
    ims_profiles,
):
    """
    Inspect candidate coverage by IMS status / row kind.
    """

    grouped = defaultdict(
        list
    )


    for profile in ims_profiles:


        key = (

            profile[
                "row_kind"
            ],

            profile[
                "cleared_status"
            ],
        )


        grouped[
            key
        ].append(
            profile
        )


    output = []


    for (
        row_kind,
        cleared_status,
    ), rows in sorted(

        grouped.items(),

        key=lambda item: str(
            item[
                0
            ]
        ),
    ):


        ref_amount_candidate = sum(

            row[
                "wf_reference_plus_amount_candidate_count"
            ] > 0

            for row
            in rows
        )


        clear_date_candidate = sum(

            row[
                "wf_amount_plus_cleared_date_candidate_count"
            ] > 0

            for row
            in rows
        )


        no_candidate = sum(

            (
                row[
                    "wf_reference_plus_amount_candidate_count"
                ] == 0

                and

                row[
                    "wf_amount_plus_cleared_date_candidate_count"
                ] == 0
            )

            for row
            in rows
        )


        output.append(

            {
                "row_kind":
                    row_kind,

                "cleared_status":
                    cleared_status,

                "ims_transaction_count":
                    len(
                        rows
                    ),

                "has_reference_plus_amount_candidate":
                    ref_amount_candidate,

                "has_amount_plus_cleared_date_candidate":
                    clear_date_candidate,

                "no_candidate_by_either_signal":
                    no_candidate,
            }
        )


    return output


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "ASCOT AIC WF <-> AIC IMS RELATIONSHIP INSPECTION"
    )


    print(
        "No production matching assumptions are made."
    )


    # ========================================================
    # LOAD ACTUAL SANITIZED DATA
    # ========================================================

    wf_raw = read_csv(
        WF_PATH
    )


    ims_raw = read_csv(
        IMS_TRANSACTION_PATH
    )


    allocation_raw = read_csv(
        IMS_ALLOCATION_PATH
    )


    wf_records = [

        standardize_wf(
            row
        )

        for row
        in wf_raw
    ]


    ims_records = [

        standardize_ims(
            row
        )

        for row
        in ims_raw
    ]


    ims_by_id = {

        record[
            "transaction_id"
        ]:
            record

        for record
        in ims_records
    }


    allocation_summary = (
        build_allocation_summary(
            allocation_raw
        )
    )


    indexes = build_indexes(
        ims_records
    )


    print(
        f"\nWF transactions: "
        f"{len(wf_records)}"
    )


    print(
        f"  Main cash activity: "
        f"{sum(row['section'] == 'main_cash_activity' for row in wf_records)}"
    )


    print(
        f"  ZBA/sweep: "
        f"{sum(row['section'] == 'zba_sweep_transfers' for row in wf_records)}"
    )


    print(
        f"\nIMS source transactions: "
        f"{len(ims_records)}"
    )


    print(
        f"IMS allocation lines: "
        f"{len(allocation_raw)}"
    )


    # ========================================================
    # PROFILE WF -> IMS
    # ========================================================

    (
        wf_profiles,
        unique_strong_pairs,
    ) = profile_wf_transactions(

        wf_records,

        ims_records,

        indexes,

        ims_by_id,

        allocation_summary,
    )


    # ========================================================
    # PROFILE IMS -> WF
    # ========================================================

    ims_profiles = profile_ims_transactions(

        ims_records,

        wf_records,
    )


    # ========================================================
    # SUMMARIES
    # ========================================================

    wf_type_summary = build_wf_type_summary(
        wf_profiles
    )


    ims_status_summary = build_ims_status_summary(
        ims_profiles
    )


    candidate_class_counts = Counter(

        profile[
            "candidate_class"
        ]

        for profile
        in wf_profiles
    )


    # ========================================================
    # SECTION-LEVEL CANDIDATE COUNTS
    # ========================================================

    section_summary = {}


    for section in [

        "main_cash_activity",

        "zba_sweep_transfers",
    ]:


        rows = [

            row

            for row
            in wf_profiles

            if row[
                "section"
            ] == section
        ]


        class_counts = Counter(

            row[
                "candidate_class"
            ]

            for row
            in rows
        )


        strong_unique = (

            class_counts[
                "UNIQUE_REFERENCE_PLUS_AMOUNT"
            ]

            + class_counts[
                "UNIQUE_AMOUNT_PLUS_CLEARED_DATE"
            ]
        )


        section_summary[
            section
        ] = {

            "transaction_count":
                len(
                    rows
                ),

            "unique_reference_plus_amount":
                class_counts[
                    "UNIQUE_REFERENCE_PLUS_AMOUNT"
                ],

            "unique_amount_plus_cleared_date":
                class_counts[
                    "UNIQUE_AMOUNT_PLUS_CLEARED_DATE"
                ],

            "strong_unique_candidate_count":
                strong_unique,

            "no_strong_candidate":
                class_counts[
                    "NO_STRONG_CANDIDATE"
                ],
        }


    # ========================================================
    # UNIQUE STRONG PAIR RELATIONSHIPS
    # ========================================================

    unique_pair_count = len(
        unique_strong_pairs
    )


    same_period_count = sum(

        str(
            row[
                "same_accounting_period"
            ]
        ).lower()
        == "true"

        for row
        in unique_strong_pairs
    )


    cross_period_count = (

        unique_pair_count

        - same_period_count
    )


    wf_date_is_clear_date_count = sum(

        str(
            row[
                "wf_date_in_ims_cleared_dates"
            ]
        ).lower()
        == "true"

        for row
        in unique_strong_pairs
    )


    wf_date_is_transaction_date_count = sum(

        str(
            row[
                "wf_date_equals_ims_transaction_date"
            ]
        ).lower()
        == "true"

        for row
        in unique_strong_pairs
    )


    # ========================================================
    # IMS ALLOCATION MULTIPLICITY
    # ========================================================

    allocation_count_distribution = Counter()


    for ims in ims_records:


        allocation_count = allocation_summary.get(

            ims[
                "transaction_id"
            ],

            {
                "allocation_count":
                    0
            },
        )[
            "allocation_count"
        ]


        allocation_count_distribution[
            allocation_count
        ] += 1


    # ========================================================
    # GL / COST AGREEMENT AMONG UNIQUE STRONG PAIRS
    # ========================================================

    pairs_with_wf_gl = [

        pair

        for pair
        in unique_strong_pairs

        if pair[
            "wf_gl_account"
        ]
    ]


    wf_gl_match_count = sum(

        str(
            pair[
                "wf_gl_matches_any_ims_allocation"
            ]
        ).lower()
        == "true"

        for pair
        in pairs_with_wf_gl
    )


    pairs_with_wf_cost = [

        pair

        for pair
        in unique_strong_pairs

        if pair[
            "wf_cost_center"
        ]
    ]


    wf_cost_match_count = sum(

        str(
            pair[
                "wf_cost_matches_any_ims_allocation"
            ]
        ).lower()
        == "true"

        for pair
        in pairs_with_wf_cost
    )


    # ========================================================
    # IMS STATUS COUNTS
    # ========================================================

    ims_cleared_status_counts = Counter(

        ims[
            "cleared_status"
        ]

        for ims
        in ims_records
    )


    ims_row_kind_counts = Counter(

        ims[
            "row_kind"
        ]

        for ims
        in ims_records
    )


    # ========================================================
    # MONTHLY WF CANDIDATE SUMMARY
    # ========================================================

    monthly_summary = []


    periods = sorted(

        {
            row[
                "accounting_period"
            ]

            for row
            in wf_records
        }
    )


    for period in periods:


        monthly_wf = [

            row

            for row
            in wf_profiles

            if row[
                "accounting_period"
            ] == period
        ]


        class_counts = Counter(

            row[
                "candidate_class"
            ]

            for row
            in monthly_wf
        )


        main_rows = [

            row

            for row
            in monthly_wf

            if row[
                "section"
            ] == "main_cash_activity"
        ]


        main_class_counts = Counter(

            row[
                "candidate_class"
            ]

            for row
            in main_rows
        )


        monthly_summary.append(

            {
                "accounting_period":
                    period,

                "wf_total":
                    len(
                        monthly_wf
                    ),

                "wf_main_cash":
                    len(
                        main_rows
                    ),

                "wf_zba_sweep":
                    (
                        len(
                            monthly_wf
                        )
                        - len(
                            main_rows
                        )
                    ),

                "all_wf_unique_reference_plus_amount":
                    class_counts[
                        "UNIQUE_REFERENCE_PLUS_AMOUNT"
                    ],

                "all_wf_unique_amount_plus_cleared_date":
                    class_counts[
                        "UNIQUE_AMOUNT_PLUS_CLEARED_DATE"
                    ],

                "all_wf_no_strong_candidate":
                    class_counts[
                        "NO_STRONG_CANDIDATE"
                    ],

                "main_unique_reference_plus_amount":
                    main_class_counts[
                        "UNIQUE_REFERENCE_PLUS_AMOUNT"
                    ],

                "main_unique_amount_plus_cleared_date":
                    main_class_counts[
                        "UNIQUE_AMOUNT_PLUS_CLEARED_DATE"
                    ],

                "main_no_strong_candidate":
                    main_class_counts[
                        "NO_STRONG_CANDIDATE"
                    ],
            }
        )


    # ========================================================
    # SAVE CSV OUTPUTS
    # ========================================================

    write_csv(

        WF_PROFILE_PATH,

        wf_profiles,
    )


    write_csv(

        IMS_PROFILE_PATH,

        ims_profiles,
    )


    write_csv(

        UNIQUE_CANDIDATES_PATH,

        unique_strong_pairs,
    )


    write_csv(

        WF_TYPE_SUMMARY_PATH,

        wf_type_summary,
    )


    write_csv(

        IMS_STATUS_SUMMARY_PATH,

        ims_status_summary,
    )


    # ========================================================
    # FULL JSON REPORT
    # ========================================================

    report = {

        "purpose":
            (
                "Empirical inspection of actual Jan-Jul "
                "AIC WF and AIC IMS relationships prior "
                "to defining production reconciliation rules."
            ),

        "population": {

            "wf_total":
                len(
                    wf_records
                ),

            "wf_main_cash_activity":
                sum(

                    row[
                        "section"
                    ] == "main_cash_activity"

                    for row
                    in wf_records
                ),

            "wf_zba_sweep":
                sum(

                    row[
                        "section"
                    ] == "zba_sweep_transfers"

                    for row
                    in wf_records
                ),

            "ims_source_transactions":
                len(
                    ims_records
                ),

            "ims_allocation_lines":
                len(
                    allocation_raw
                ),
        },

        "wf_candidate_class_counts":
            dict(
                candidate_class_counts
            ),

        "wf_section_candidate_summary":
            section_summary,

        "unique_strong_candidate_relationships": {

            "pair_count":
                unique_pair_count,

            "same_accounting_period_count":
                same_period_count,

            "cross_accounting_period_count":
                cross_period_count,

            "wf_date_is_ims_cleared_date_count":
                wf_date_is_clear_date_count,

            "wf_date_is_ims_transaction_date_count":
                wf_date_is_transaction_date_count,
        },

        "ims_cleared_status_counts":
            dict(
                ims_cleared_status_counts
            ),

        "ims_row_kind_counts":
            dict(
                ims_row_kind_counts
            ),

        "ims_allocation_count_distribution":
            {

                str(
                    key
                ):
                    value

                for key, value
                in sorted(
                    allocation_count_distribution.items()
                )
            },

        "gl_cost_correspondence_on_unique_strong_candidates": {

            "pairs_with_wf_gl":
                len(
                    pairs_with_wf_gl
                ),

            "wf_gl_found_in_ims_allocations":
                wf_gl_match_count,

            "pairs_with_wf_cost_center":
                len(
                    pairs_with_wf_cost
                ),

            "wf_cost_found_in_ims_allocations":
                wf_cost_match_count,
        },

        "monthly_wf_candidate_summary":
            monthly_summary,
    }


    with REPORT_PATH.open(

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
    # TERMINAL SUMMARY
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "WF CANDIDATE RELATIONSHIP"
    )

    print(
        "========================================"
    )


    for (
        candidate_class,
        count,
    ) in candidate_class_counts.most_common():


        print(

            f"{candidate_class}: "
            f"{count}"
        )


    print(
        "\n========================================"
    )

    print(
        "BY WF SECTION"
    )

    print(
        "========================================"
    )


    for (
        section,
        result,
    ) in section_summary.items():


        print(
            f"\n{section}"
        )


        print(
            f"  Transactions: "
            f"{result['transaction_count']}"
        )


        print(
            "  Unique reference + amount: "
            f"{result['unique_reference_plus_amount']}"
        )


        print(
            "  Unique amount + cleared date: "
            f"{result['unique_amount_plus_cleared_date']}"
        )


        print(
            "  Strong unique candidates: "
            f"{result['strong_unique_candidate_count']}"
        )


        print(
            "  No strong candidate: "
            f"{result['no_strong_candidate']}"
        )


    print(
        "\n========================================"
    )

    print(
        "UNIQUE STRONG CANDIDATE RELATIONSHIPS"
    )

    print(
        "========================================"
    )


    print(
        f"Unique strong candidates: "
        f"{unique_pair_count}"
    )


    print(
        f"Same accounting period: "
        f"{same_period_count}"
    )


    print(
        f"Cross accounting period: "
        f"{cross_period_count}"
    )


    print(
        "WF date appears in IMS cleared date(s): "
        f"{wf_date_is_clear_date_count}"
    )


    print(
        "WF date equals IMS transaction date: "
        f"{wf_date_is_transaction_date_count}"
    )


    print(
        "\n========================================"
    )

    print(
        "IMS STATUS"
    )

    print(
        "========================================"
    )


    for (
        status,
        count,
    ) in ims_cleared_status_counts.most_common():


        print(
            f"{status}: {count}"
        )


    print(
        "\nIMS row kinds:"
    )


    for (
        row_kind,
        count,
    ) in ims_row_kind_counts.most_common():


        print(
            f"  {row_kind}: {count}"
        )


    print(
        "\n========================================"
    )

    print(
        "IMS ALLOCATION MULTIPLICITY"
    )

    print(
        "========================================"
    )


    for (
        allocation_count,
        transaction_count,
    ) in sorted(

        allocation_count_distribution.items()
    ):


        print(

            f"{allocation_count} allocation(s): "
            f"{transaction_count} IMS transaction(s)"
        )


    print(
        "\n========================================"
    )

    print(
        "WF GL / COST vs IMS ALLOCATIONS"
    )

    print(
        "========================================"
    )


    print(
        "Unique candidate pairs with WF GL: "
        f"{len(pairs_with_wf_gl)}"
    )


    print(
        "WF GL found among IMS allocations: "
        f"{wf_gl_match_count}"
    )


    print(
        "Unique candidate pairs with WF cost center: "
        f"{len(pairs_with_wf_cost)}"
    )


    print(
        "WF cost center found among IMS allocations: "
        f"{wf_cost_match_count}"
    )


    print(
        "\n========================================"
    )

    print(
        "MONTHLY WF PROFILE"
    )

    print(
        "========================================"
    )


    for month in monthly_summary:


        print(

            f"{month['accounting_period']} | "
            f"WF {month['wf_total']} | "
            f"Main {month['wf_main_cash']} | "
            f"ZBA/Sweep {month['wf_zba_sweep']} | "
            f"Main ref+amt "
            f"{month['main_unique_reference_plus_amount']} | "
            f"Main amt+clear "
            f"{month['main_unique_amount_plus_cleared_date']} | "
            f"Main no strong "
            f"{month['main_no_strong_candidate']}"
        )


    print(
        "\n========================================"
    )

    print(
        "INSPECTION COMPLETE"
    )

    print(
        "========================================"
    )


    print(
        "\nOutputs:"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "wf_ims_relationship_inspection.json"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "wf_transaction_type_summary.csv"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "ims_status_summary.csv"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "unique_strong_candidate_pairs.csv"
    )


    print(
        "\nNo production reconciliation rule has "
        "been assumed or written."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()