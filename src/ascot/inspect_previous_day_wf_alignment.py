# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# INSPECT PREVIOUS DAY <-> AIC WF ALIGNMENT
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# We now have two independently sanitized populations:
#
#   1. Previous Day Composite Report
#      filtered to AIC Disbursement account 4062522693
#
#   2. Resource Pro AIC WF workpaper
#
#
# Across Jan-Jul:
#
#       Previous Day AIC transactions = 1,514
#       AIC WF transactions           = 1,514
#
# Their monthly Main / ZBA / Sweep counts also agree.
#
#
# HOWEVER:
#
# Equal counts do NOT prove that the rows match
# transaction-for-transaction.
#
# Before writing the real reconciliation algorithm, we inspect
# the relationship between the two data sets.
#
#
# QUESTIONS THIS SCRIPT ANSWERS
# ------------------------------------------------------------
#
# 1. Do date + direction + amount agree?
#
# 2. Does Tran Desc agree?
#
# 3. Does Previous Day Customer Ref No correspond to
#    AIC WF Check Number?
#
# 4. Does Descriptive Text 1 agree?
#
# 5. How many transactions can be identified using a strong
#    combination of these fields?
#
# 6. Are there duplicate signatures where two transactions
#    look identical?
#
# 7. Are there transactions that cannot yet be uniquely linked?
#
# 8. Does the Main vs ZBA/Sweep classification agree after
#    transaction-level pairing?
#
#
# IMPORTANT
# ------------------------------------------------------------
#
# This script is DIAGNOSTIC.
#
# It deliberately does NOT yet say:
#
#       "This is the final reconciliation key."
#
# We first inspect the empirical results.
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
# INPUT / OUTPUT PATHS
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


SUMMARY_PATH = (

    PROCESSED_FOLDER
    / "previous_day_wf_alignment_inspection.json"
)


PAIRS_PATH = (

    PROCESSED_FOLDER
    / "previous_day_wf_alignment_pairs.csv"
)


UNRESOLVED_PATH = (

    PROCESSED_FOLDER
    / "previous_day_wf_alignment_unresolved.csv"
)


# ============================================================
# BASIC FILE READING
# ============================================================

def read_csv(path):
    """
    Read a CSV file into a list of dictionaries.
    """

    if not path.exists():

        raise FileNotFoundError(
            f"Could not find required file: {path}"
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

def write_csv(path, records):
    """
    Write dictionaries to CSV without pandas.
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

    Example:

        "  ZBA Debit Transfer  "

    becomes:

        "ZBA DEBIT TRANSFER"
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
    Make common date representations comparable.

    Examples:

        2026/03/15
        2026-03-15

    both become:

        2026-03-15
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


    # If a datetime accidentally appears, keep only date.
    if len(text) >= 10:

        return text[:10]


    return text


# ============================================================
# MONEY NORMALIZATION
# ============================================================

def normalize_money(value):
    """
    Normalize monetary amounts to two decimal places.

    Decimal is used instead of binary floating point.
    """

    if value in {
        None,
        "",
    }:

        return None


    try:

        amount = Decimal(
            str(value)
        )


    except InvalidOperation:

        return None


    amount = amount.quantize(

        Decimal("0.01"),

        rounding=ROUND_HALF_UP,
    )


    return format(
        amount,
        ".2f",
    )


# ============================================================
# IDENTIFIER DISPLAY NORMALIZATION
# ============================================================

def normalize_identifier_text(value):
    """
    Preserve most identifier formatting but remove artifacts
    such as a trailing .0 created by Excel numeric storage.

    This is useful for comparing:

        12345

    with:

        12345.0
    """

    if value is None:

        return None


    text = str(
        value
    ).strip()


    if not text:

        return None


    # Excel-style numeric representation.
    if re.fullmatch(
        r"\d+\.0",
        text,
    ):

        text = text[:-2]


    return text


# ============================================================
# IDENTIFIER MATCH KEY
# ============================================================

def identifier_match_key(value):
    """
    Create a comparison key for bank/check/reference IDs.

    Numeric values have leading zeros removed.

    This allows:

        03330005430

    and:

        3330005430

    to be considered the same normalized identifier.

    IMPORTANT:
    We preserve raw identifiers separately.
    """

    text = normalize_identifier_text(
        value
    )


    if text is None:

        return None


    # Remove simple spaces sometimes introduced by formatting.
    compact = re.sub(
        r"\s+",
        "",
        text,
    )


    if re.fullmatch(
        r"\d+",
        compact,
    ):

        # All-zero values are generic placeholders,
        # not useful transaction identifiers.
        if set(compact) == {
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


    # Non-numeric references:
    # normalize case/spacing but do not invent transformations.
    return normalize_text(
        text
    )


# ============================================================
# DERIVE BANK DIRECTION / AMOUNT
# ============================================================

def derive_bank_movement(row):
    """
    Both sanitized data sets preserve Debit and Credit.

    We create the same comparison representation for each:

        direction = debit / credit
        amount    = absolute monetary amount
    """

    debit = normalize_money(
        row.get(
            "debit_amount"
        )
    )


    credit = normalize_money(
        row.get(
            "credit_amount"
        )
    )


    debit_decimal = (

        Decimal(debit)

        if debit is not None

        else Decimal("0.00")
    )


    credit_decimal = (

        Decimal(credit)

        if credit is not None

        else Decimal("0.00")
    )


    if debit_decimal != 0:

        return (
            "DEBIT",
            format(
                abs(debit_decimal),
                ".2f",
            ),
        )


    if credit_decimal != 0:

        return (
            "CREDIT",
            format(
                abs(credit_decimal),
                ".2f",
            ),
        )


    return (
        None,
        None,
    )


# ============================================================
# CREATE COMPARISON FEATURES
# ============================================================

def build_features(
    row,
    source_type,
):
    """
    Convert Previous Day and WF rows into the same conceptual
    comparison structure.
    """

    period = row.get(
        "accounting_period"
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


    # --------------------------------------------------------
    # TRANSACTION DESCRIPTION
    # --------------------------------------------------------

    if source_type == "PREVIOUS_DAY":

        transaction_type = normalize_text(

            row.get(
                "transaction_description"
            )

            or row.get(
                "transaction_type"
            )
        )


    else:

        transaction_type = normalize_text(

            row.get(
                "transaction_description"
            )
        )


    # --------------------------------------------------------
    # REFERENCE / CHECK NUMBER
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


    else:

        reference_raw = row.get(
            "check_number"
        )


    reference_text = (
        normalize_identifier_text(
            reference_raw
        )
    )


    reference_key = (
        identifier_match_key(
            reference_raw
        )
    )


    # --------------------------------------------------------
    # DESCRIPTIVE TEXT
    # --------------------------------------------------------

    descriptive_text = normalize_text(

        row.get(
            "descriptive_text_1"
        )
    )


    # --------------------------------------------------------
    # SECTION
    # --------------------------------------------------------

    if source_type == "PREVIOUS_DAY":

        section = row.get(
            "aic_section"
        )


    else:

        section = row.get(
            "section"
        )


    # --------------------------------------------------------
    # SOURCE-BASED ID
    # --------------------------------------------------------

    source_row = row.get(
        "source_row"
    )


    existing_id = row.get(
        "transaction_id"
    )


    if existing_id:

        transaction_id = (
            existing_id
        )


    else:

        prefix = (

            "PD"

            if source_type
            == "PREVIOUS_DAY"

            else "WF"
        )


        transaction_id = (

            f"{prefix}-{period}-R{source_row}"
        )


    return {

        "source_type":
            source_type,

        "transaction_id":
            transaction_id,

        "accounting_period":
            period,

        "source_workbook":
            row.get(
                "source_workbook"
            ),

        "source_row":
            source_row,

        "date":
            date,

        "direction":
            direction,

        "amount":
            amount,

        "transaction_type":
            transaction_type,

        "reference_raw":
            reference_text,

        "reference_key":
            reference_key,

        "descriptive_text":
            descriptive_text,

        "section":
            section,
    }


# ============================================================
# SIGNATURE DEFINITIONS
# ============================================================
#
# We deliberately examine matching at progressively more
# informative levels.
#
#
# LEVEL 1:
#
#     date + direction + amount
#
#
# LEVEL 2:
#
#     + transaction description
#
#
# LEVEL 3:
#
#     + normalized reference
#
#
# LEVEL 4:
#
#     + descriptive text
#
#
# FULL:
#
#     transaction type
#     reference
#     descriptive text
#     date
#     amount
#     direction
#
#
# This allows us to see which fields add useful information.
# ============================================================

def signature_date_amount(record):

    return (

        record[
            "accounting_period"
        ],

        record[
            "date"
        ],

        record[
            "direction"
        ],

        record[
            "amount"
        ],
    )


def signature_core(record):

    return (

        *signature_date_amount(
            record
        ),

        record[
            "transaction_type"
        ],
    )


def signature_core_ref(record):

    return (

        *signature_core(
            record
        ),

        record[
            "reference_key"
        ],
    )


def signature_core_detail(record):

    return (

        *signature_core(
            record
        ),

        record[
            "descriptive_text"
        ],
    )


def signature_full(record):

    return (

        *signature_core(
            record
        ),

        record[
            "reference_key"
        ],

        record[
            "descriptive_text"
        ],
    )


# ============================================================
# MULTISET COVERAGE
# ============================================================
#
# A simple set comparison would mishandle duplicate
# transactions.
#
# Example:
#
# Previous Day contains two identical $1.50 rows.
#
# Therefore we compare COUNTS of each signature.
# ============================================================

def calculate_multiset_coverage(
    previous_day_records,
    wf_records,
    signature_function,
):

    previous_counter = Counter(

        signature_function(
            record
        )

        for record
        in previous_day_records
    )


    wf_counter = Counter(

        signature_function(
            record
        )

        for record
        in wf_records
    )


    matched_rows = sum(

        min(
            previous_counter[
                signature
            ],

            wf_counter[
                signature
            ],
        )

        for signature
        in (
            set(
                previous_counter
            )

            | set(
                wf_counter
            )
        )
    )


    duplicate_previous_signatures = sum(

        1

        for count
        in previous_counter.values()

        if count > 1
    )


    duplicate_wf_signatures = sum(

        1

        for count
        in wf_counter.values()

        if count > 1
    )


    denominator = max(

        len(
            previous_day_records
        ),

        len(
            wf_records
        ),

        1,
    )


    return {

        "matched_rows":
            matched_rows,

        "previous_day_rows":
            len(
                previous_day_records
            ),

        "wf_rows":
            len(
                wf_records
            ),

        "coverage_pct":
            round(

                matched_rows

                / denominator

                * 100,

                2,
            ),

        "duplicate_previous_day_signatures":
            duplicate_previous_signatures,

        "duplicate_wf_signatures":
            duplicate_wf_signatures,
    }


# ============================================================
# DIAGNOSTIC ONE-TO-ONE MATCHING
# ============================================================
#
# Again, this is NOT yet our production reconciliation.
#
# We use a hierarchy only to inspect what can currently be
# paired from the actual data.
# ============================================================

def diagnostic_pairing(
    previous_day_records,
    wf_records,
):

    # Give every list record a stable internal array index.
    previous_indexes = set(

        range(
            len(
                previous_day_records
            )
        )
    )


    wf_indexes = set(

        range(
            len(
                wf_records
            )
        )
    )


    pairs = []


    # --------------------------------------------------------
    # MATCHING HELPER
    # --------------------------------------------------------

    def match_level(
        level_name,
        signature_function,
        allow_duplicate_multiset,
    ):

        previous_map = defaultdict(
            list
        )


        wf_map = defaultdict(
            list
        )


        for index in previous_indexes:

            key = signature_function(

                previous_day_records[
                    index
                ]
            )


            previous_map[
                key
            ].append(
                index
            )


        for index in wf_indexes:

            key = signature_function(

                wf_records[
                    index
                ]
            )


            wf_map[
                key
            ].append(
                index
            )


        matches_to_make = []


        common_keys = (

            set(
                previous_map
            )

            & set(
                wf_map
            )
        )


        for key in common_keys:


            previous_candidates = sorted(

                previous_map[
                    key
                ]
            )


            wf_candidates = sorted(

                wf_map[
                    key
                ]
            )


            # ------------------------------------------------
            # FULL SIGNATURE
            # ------------------------------------------------
            #
            # If two transactions have all visible comparison
            # fields identical, we preserve the duplicate
            # group and pair occurrences for diagnostic
            # purposes.
            #
            # But we explicitly record that individual identity
            # within the duplicate group is not uniquely known.
            # ------------------------------------------------

            if allow_duplicate_multiset:


                number_to_match = min(

                    len(
                        previous_candidates
                    ),

                    len(
                        wf_candidates
                    ),
                )


                duplicate_signature = (

                    len(
                        previous_candidates
                    ) > 1

                    or

                    len(
                        wf_candidates
                    ) > 1
                )


                for position in range(
                    number_to_match
                ):


                    matches_to_make.append(

                        (
                            previous_candidates[
                                position
                            ],

                            wf_candidates[
                                position
                            ],

                            duplicate_signature,
                        )
                    )


            # ------------------------------------------------
            # WEAKER SIGNATURES
            # ------------------------------------------------
            #
            # For weaker evidence, we only pair when there is
            # exactly ONE candidate on each side.
            #
            # We do not guess among multiple possibilities.
            # ------------------------------------------------

            else:


                if (

                    len(
                        previous_candidates
                    ) == 1

                    and

                    len(
                        wf_candidates
                    ) == 1
                ):


                    matches_to_make.append(

                        (
                            previous_candidates[
                                0
                            ],

                            wf_candidates[
                                0
                            ],

                            False,
                        )
                    )


        # ----------------------------------------------------
        # APPLY MATCHES AFTER MAP ITERATION
        # ----------------------------------------------------

        for (
            previous_index,
            wf_index,
            duplicate_signature,
        ) in matches_to_make:


            # The record might already have been removed by
            # another match in this level.
            if (

                previous_index
                not in previous_indexes

                or

                wf_index
                not in wf_indexes
            ):

                continue


            pairs.append(

                {
                    "match_level":
                        level_name,

                    "duplicate_full_signature":
                        duplicate_signature,

                    "previous_index":
                        previous_index,

                    "wf_index":
                        wf_index,
                }
            )


            previous_indexes.remove(
                previous_index
            )


            wf_indexes.remove(
                wf_index
            )


    # ========================================================
    # LEVEL 1:
    # FULL NORMALIZED SIGNATURE
    # ========================================================

    match_level(

        "full_normalized_signature",

        signature_full,

        True,
    )


    # ========================================================
    # LEVEL 2:
    # CORE + REFERENCE
    # ========================================================
    #
    # Descriptive text may have been manually modified.
    # ========================================================

    match_level(

        "unique_core_plus_reference",

        signature_core_ref,

        False,
    )


    # ========================================================
    # LEVEL 3:
    # CORE + DESCRIPTIVE TEXT
    # ========================================================
    #
    # Useful where reference is absent or reformatted.
    # ========================================================

    match_level(

        "unique_core_plus_descriptive_text",

        signature_core_detail,

        False,
    )


    # ========================================================
    # LEVEL 4:
    # DATE + AMOUNT + DIRECTION + TRAN DESC
    # ========================================================

    match_level(

        "unique_core_signature",

        signature_core,

        False,
    )


    # ========================================================
    # LEVEL 5:
    # DATE + AMOUNT + DIRECTION
    # ========================================================
    #
    # This is intentionally weak and only accepted when the
    # remaining candidate is unique on both sides.
    # ========================================================

    match_level(

        "unique_date_amount_direction",

        signature_date_amount,

        False,
    )


    return (

        pairs,

        previous_indexes,

        wf_indexes,
    )


# ============================================================
# BUILD HUMAN-READABLE PAIR OUTPUT
# ============================================================

def build_pair_output(
    pairs,
    previous_day_records,
    wf_records,
):

    output = []


    for pair_number, pair in enumerate(

        pairs,

        start=1,
    ):


        previous = previous_day_records[

            pair[
                "previous_index"
            ]
        ]


        wf = wf_records[

            pair[
                "wf_index"
            ]
        ]


        # ----------------------------------------------------
        # REFERENCE COMPARISONS
        # ----------------------------------------------------

        previous_raw_ref = (
            previous[
                "reference_raw"
            ]
        )


        wf_raw_ref = (
            wf[
                "reference_raw"
            ]
        )


        raw_reference_equal = (

            previous_raw_ref
            == wf_raw_ref
        )


        normalized_reference_equal = (

            previous[
                "reference_key"
            ]

            == wf[
                "reference_key"
            ]
        )


        # ----------------------------------------------------
        # SECTION COMPARISON
        # ----------------------------------------------------

        section_equal = (

            previous[
                "section"
            ]

            == wf[
                "section"
            ]
        )


        output.append(

            {
                "pair_number":
                    pair_number,

                "accounting_period":
                    previous[
                        "accounting_period"
                    ],

                "match_level":
                    pair[
                        "match_level"
                    ],

                "duplicate_full_signature":
                    pair[
                        "duplicate_full_signature"
                    ],

                "previous_day_transaction_id":
                    previous[
                        "transaction_id"
                    ],

                "previous_day_source_row":
                    previous[
                        "source_row"
                    ],

                "wf_transaction_id":
                    wf[
                        "transaction_id"
                    ],

                "wf_source_row":
                    wf[
                        "source_row"
                    ],

                "date":
                    previous[
                        "date"
                    ],

                "direction":
                    previous[
                        "direction"
                    ],

                "amount":
                    previous[
                        "amount"
                    ],

                "transaction_type_previous_day":
                    previous[
                        "transaction_type"
                    ],

                "transaction_type_wf":
                    wf[
                        "transaction_type"
                    ],

                "transaction_type_equal":
                    (
                        previous[
                            "transaction_type"
                        ]
                        == wf[
                            "transaction_type"
                        ]
                    ),

                "previous_day_reference_raw":
                    previous_raw_ref,

                "wf_check_number_raw":
                    wf_raw_ref,

                "raw_reference_equal":
                    raw_reference_equal,

                "normalized_reference_equal":
                    normalized_reference_equal,

                "previous_day_reference_key":
                    previous[
                        "reference_key"
                    ],

                "wf_reference_key":
                    wf[
                        "reference_key"
                    ],

                "previous_day_descriptive_text":
                    previous[
                        "descriptive_text"
                    ],

                "wf_descriptive_text":
                    wf[
                        "descriptive_text"
                    ],

                "descriptive_text_equal":
                    (
                        previous[
                            "descriptive_text"
                        ]
                        == wf[
                            "descriptive_text"
                        ]
                    ),

                "previous_day_section":
                    previous[
                        "section"
                    ],

                "wf_section":
                    wf[
                        "section"
                    ],

                "section_equal":
                    section_equal,
            }
        )


    return output


# ============================================================
# BUILD UNRESOLVED OUTPUT
# ============================================================

def build_unresolved_output(
    previous_day_records,
    wf_records,
    unresolved_previous_indexes,
    unresolved_wf_indexes,
):

    output = []


    # --------------------------------------------------------
    # Candidate counters among remaining rows
    # --------------------------------------------------------

    remaining_previous_core = Counter(

        signature_core(
            previous_day_records[
                index
            ]
        )

        for index
        in unresolved_previous_indexes
    )


    remaining_wf_core = Counter(

        signature_core(
            wf_records[
                index
            ]
        )

        for index
        in unresolved_wf_indexes
    )


    remaining_previous_weak = Counter(

        signature_date_amount(
            previous_day_records[
                index
            ]
        )

        for index
        in unresolved_previous_indexes
    )


    remaining_wf_weak = Counter(

        signature_date_amount(
            wf_records[
                index
            ]
        )

        for index
        in unresolved_wf_indexes
    )


    # --------------------------------------------------------
    # PREVIOUS DAY UNRESOLVED
    # --------------------------------------------------------

    for index in sorted(
        unresolved_previous_indexes
    ):


        record = previous_day_records[
            index
        ]


        output.append(

            {
                "source_type":
                    "PREVIOUS_DAY",

                "transaction_id":
                    record[
                        "transaction_id"
                    ],

                "accounting_period":
                    record[
                        "accounting_period"
                    ],

                "source_row":
                    record[
                        "source_row"
                    ],

                "date":
                    record[
                        "date"
                    ],

                "direction":
                    record[
                        "direction"
                    ],

                "amount":
                    record[
                        "amount"
                    ],

                "transaction_type":
                    record[
                        "transaction_type"
                    ],

                "reference_raw":
                    record[
                        "reference_raw"
                    ],

                "reference_key":
                    record[
                        "reference_key"
                    ],

                "descriptive_text":
                    record[
                        "descriptive_text"
                    ],

                "section":
                    record[
                        "section"
                    ],

                "opposite_core_candidate_count":
                    remaining_wf_core[

                        signature_core(
                            record
                        )
                    ],

                "opposite_date_amount_candidate_count":
                    remaining_wf_weak[

                        signature_date_amount(
                            record
                        )
                    ],
            }
        )


    # --------------------------------------------------------
    # WF UNRESOLVED
    # --------------------------------------------------------

    for index in sorted(
        unresolved_wf_indexes
    ):


        record = wf_records[
            index
        ]


        output.append(

            {
                "source_type":
                    "AIC_WF",

                "transaction_id":
                    record[
                        "transaction_id"
                    ],

                "accounting_period":
                    record[
                        "accounting_period"
                    ],

                "source_row":
                    record[
                        "source_row"
                    ],

                "date":
                    record[
                        "date"
                    ],

                "direction":
                    record[
                        "direction"
                    ],

                "amount":
                    record[
                        "amount"
                    ],

                "transaction_type":
                    record[
                        "transaction_type"
                    ],

                "reference_raw":
                    record[
                        "reference_raw"
                    ],

                "reference_key":
                    record[
                        "reference_key"
                    ],

                "descriptive_text":
                    record[
                        "descriptive_text"
                    ],

                "section":
                    record[
                        "section"
                    ],

                "opposite_core_candidate_count":
                    remaining_previous_core[

                        signature_core(
                            record
                        )
                    ],

                "opposite_date_amount_candidate_count":
                    remaining_previous_weak[

                        signature_date_amount(
                            record
                        )
                    ],
            }
        )


    return output


# ============================================================
# FIELD AGREEMENT SUMMARY
# ============================================================

def calculate_field_agreement(
    pair_records,
):

    total_pairs = len(
        pair_records
    )


    if total_pairs == 0:

        return {}


    transaction_type_equal = sum(

        str(
            pair[
                "transaction_type_equal"
            ]
        ).lower()
        == "true"

        for pair
        in pair_records
    )


    descriptive_text_equal = sum(

        str(
            pair[
                "descriptive_text_equal"
            ]
        ).lower()
        == "true"

        for pair
        in pair_records
    )


    section_equal = sum(

        str(
            pair[
                "section_equal"
            ]
        ).lower()
        == "true"

        for pair
        in pair_records
    )


    # Only compare reference equality where at least one side
    # actually contains a reference.
    comparable_reference_pairs = [

        pair

        for pair
        in pair_records

        if (

            pair[
                "previous_day_reference_raw"
            ]

            or

            pair[
                "wf_check_number_raw"
            ]
        )
    ]


    raw_ref_equal = sum(

        pair[
            "raw_reference_equal"
        ]

        for pair
        in comparable_reference_pairs
    )


    normalized_ref_equal = sum(

        pair[
            "normalized_reference_equal"
        ]

        for pair
        in comparable_reference_pairs
    )


    raw_diff_but_normalized_equal = sum(

        (
            not pair[
                "raw_reference_equal"
            ]

            and pair[
                "normalized_reference_equal"
            ]
        )

        for pair
        in comparable_reference_pairs
    )


    return {

        "paired_transactions":
            total_pairs,

        "transaction_type_equal_count":
            transaction_type_equal,

        "transaction_type_equal_pct":
            round(

                transaction_type_equal
                / total_pairs
                * 100,

                2,
            ),

        "descriptive_text_equal_count":
            descriptive_text_equal,

        "descriptive_text_equal_pct":
            round(

                descriptive_text_equal
                / total_pairs
                * 100,

                2,
            ),

        "section_equal_count":
            section_equal,

        "section_equal_pct":
            round(

                section_equal
                / total_pairs
                * 100,

                2,
            ),

        "reference_comparable_pairs":
            len(
                comparable_reference_pairs
            ),

        "raw_reference_equal_count":
            raw_ref_equal,

        "normalized_reference_equal_count":
            normalized_ref_equal,

        "raw_reference_diff_but_normalized_equal_count":
            raw_diff_but_normalized_equal,
    }


# ============================================================
# MONTHLY SUMMARY
# ============================================================

def build_monthly_summary(
    previous_day_records,
    wf_records,
    pair_records,
    unresolved_records,
):

    periods = sorted(

        set(

            record[
                "accounting_period"
            ]

            for record
            in previous_day_records
        )

        | set(

            record[
                "accounting_period"
            ]

            for record
            in wf_records
        )
    )


    summary = []


    for period in periods:


        previous_count = sum(

            record[
                "accounting_period"
            ]
            == period

            for record
            in previous_day_records
        )


        wf_count = sum(

            record[
                "accounting_period"
            ]
            == period

            for record
            in wf_records
        )


        paired_count = sum(

            record[
                "accounting_period"
            ]
            == period

            for record
            in pair_records
        )


        unresolved_previous = sum(

            record[
                "source_type"
            ]
            == "PREVIOUS_DAY"

            and record[
                "accounting_period"
            ]
            == period

            for record
            in unresolved_records
        )


        unresolved_wf = sum(

            record[
                "source_type"
            ]
            == "AIC_WF"

            and record[
                "accounting_period"
            ]
            == period

            for record
            in unresolved_records
        )


        section_mismatches = sum(

            record[
                "accounting_period"
            ]
            == period

            and not record[
                "section_equal"
            ]

            for record
            in pair_records
        )


        summary.append(

            {
                "accounting_period":
                    period,

                "previous_day_rows":
                    previous_count,

                "aic_wf_rows":
                    wf_count,

                "diagnostically_paired":
                    paired_count,

                "unresolved_previous_day":
                    unresolved_previous,

                "unresolved_aic_wf":
                    unresolved_wf,

                "paired_section_mismatches":
                    section_mismatches,
            }
        )


    return summary


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "ASCOT PREVIOUS DAY <-> AIC WF ALIGNMENT INSPECTION"
    )


    # ========================================================
    # LOAD SANITIZED DATA
    # ========================================================

    previous_day_raw = read_csv(
        PREVIOUS_DAY_PATH
    )


    wf_raw = read_csv(
        AIC_WF_PATH
    )


    print(
        f"\nPrevious Day AIC rows: "
        f"{len(previous_day_raw)}"
    )


    print(
        f"AIC WF rows: "
        f"{len(wf_raw)}"
    )


    # ========================================================
    # CONVERT BOTH SOURCES INTO COMPARABLE FEATURES
    # ========================================================

    previous_day_records = [

        build_features(
            row,
            "PREVIOUS_DAY",
        )

        for row
        in previous_day_raw
    ]


    wf_records = [

        build_features(
            row,
            "AIC_WF",
        )

        for row
        in wf_raw
    ]


    # ========================================================
    # MULTISET COVERAGE
    # ========================================================
    #
    # This tells us how much of the population agrees under
    # each candidate combination of matching fields.
    # ========================================================

    coverage = {

        "date_direction_amount":
            calculate_multiset_coverage(

                previous_day_records,

                wf_records,

                signature_date_amount,
            ),

        "plus_transaction_description":
            calculate_multiset_coverage(

                previous_day_records,

                wf_records,

                signature_core,
            ),

        "plus_normalized_reference":
            calculate_multiset_coverage(

                previous_day_records,

                wf_records,

                signature_core_ref,
            ),

        "plus_descriptive_text":
            calculate_multiset_coverage(

                previous_day_records,

                wf_records,

                signature_core_detail,
            ),

        "full_normalized_signature":
            calculate_multiset_coverage(

                previous_day_records,

                wf_records,

                signature_full,
            ),
    }


    # ========================================================
    # DIAGNOSTIC PAIRING
    # ========================================================

    (
        pairs,
        unresolved_previous_indexes,
        unresolved_wf_indexes,
    ) = diagnostic_pairing(

        previous_day_records,

        wf_records,
    )


    pair_records = build_pair_output(

        pairs,

        previous_day_records,

        wf_records,
    )


    unresolved_records = (
        build_unresolved_output(

            previous_day_records,

            wf_records,

            unresolved_previous_indexes,

            unresolved_wf_indexes,
        )
    )


    # ========================================================
    # MATCH-LEVEL COUNTS
    # ========================================================

    match_level_counts = Counter(

        pair[
            "match_level"
        ]

        for pair
        in pair_records
    )


    # ========================================================
    # FIELD AGREEMENT
    # ========================================================

    field_agreement = (
        calculate_field_agreement(
            pair_records
        )
    )


    # ========================================================
    # MONTHLY RESULTS
    # ========================================================

    monthly_summary = (
        build_monthly_summary(

            previous_day_records,

            wf_records,

            pair_records,

            unresolved_records,
        )
    )


    # ========================================================
    # EXAMPLES OF REFERENCE FORMAT TRANSFORMATION
    # ========================================================
    #
    # These are cases where:
    #
    #       raw reference differs
    #
    # but:
    #
    #       normalized reference matches
    #
    # This will show us whether leading-zero / numeric storage
    # differences are empirically important.
    # ========================================================

    reference_transformation_examples = []


    for pair in pair_records:


        if (

            not pair[
                "raw_reference_equal"
            ]

            and pair[
                "normalized_reference_equal"
            ]

            and (

                pair[
                    "previous_day_reference_raw"
                ]

                or pair[
                    "wf_check_number_raw"
                ]
            )
        ):


            reference_transformation_examples.append(

                {
                    "accounting_period":
                        pair[
                            "accounting_period"
                        ],

                    "previous_day_source_row":
                        pair[
                            "previous_day_source_row"
                        ],

                    "wf_source_row":
                        pair[
                            "wf_source_row"
                        ],

                    "previous_day_reference":
                        pair[
                            "previous_day_reference_raw"
                        ],

                    "wf_check_number":
                        pair[
                            "wf_check_number_raw"
                        ],

                    "normalized_key":
                        pair[
                            "previous_day_reference_key"
                        ],
                }
            )


    # Keep report readable.
    reference_transformation_examples = (
        reference_transformation_examples[
            :20
        ]
    )


    # ========================================================
    # SECTION MISMATCH EXAMPLES
    # ========================================================

    section_mismatch_examples = [

        {
            "accounting_period":
                pair[
                    "accounting_period"
                ],

            "previous_day_source_row":
                pair[
                    "previous_day_source_row"
                ],

            "wf_source_row":
                pair[
                    "wf_source_row"
                ],

            "transaction_type":
                pair[
                    "transaction_type_previous_day"
                ],

            "amount":
                pair[
                    "amount"
                ],

            "previous_day_section":
                pair[
                    "previous_day_section"
                ],

            "wf_section":
                pair[
                    "wf_section"
                ],
        }

        for pair
        in pair_records

        if not pair[
            "section_equal"
        ]
    ][
        :20
    ]


    # ========================================================
    # SAVE PAIRS / UNRESOLVED
    # ========================================================

    write_csv(

        PAIRS_PATH,

        pair_records,
    )


    write_csv(

        UNRESOLVED_PATH,

        unresolved_records,
    )


    # ========================================================
    # SAVE FULL INSPECTION REPORT
    # ========================================================

    report = {

        "purpose":
            (
                "Empirical inspection of the relationship "
                "between sanitized Previous Day AIC "
                "transactions and AIC WF transactions before "
                "locking production reconciliation logic."
            ),

        "population": {

            "previous_day_aic_rows":
                len(
                    previous_day_records
                ),

            "aic_wf_rows":
                len(
                    wf_records
                ),
        },

        "multiset_signature_coverage":
            coverage,

        "diagnostic_pairing": {

            "paired_count":
                len(
                    pair_records
                ),

            "unresolved_previous_day_count":
                len(
                    unresolved_previous_indexes
                ),

            "unresolved_aic_wf_count":
                len(
                    unresolved_wf_indexes
                ),

            "match_level_counts":
                dict(
                    match_level_counts
                ),
        },

        "field_agreement":
            field_agreement,

        "monthly_summary":
            monthly_summary,

        "reference_transformation_examples":
            reference_transformation_examples,

        "section_mismatch_examples":
            section_mismatch_examples,
    }


    with SUMMARY_PATH.open(

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
    # TERMINAL REPORT
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "MULTISET SIGNATURE COVERAGE"
    )

    print(
        "========================================"
    )


    for name, result in coverage.items():


        print(

            f"{name}: "
            f"{result['matched_rows']} / "
            f"{max(result['previous_day_rows'], result['wf_rows'])} "
            f"({result['coverage_pct']}%)"
        )


        print(

            "  Duplicate signatures — "
            f"Previous Day: "
            f"{result['duplicate_previous_day_signatures']} | "
            f"WF: "
            f"{result['duplicate_wf_signatures']}"
        )


    print(
        "\n========================================"
    )

    print(
        "DIAGNOSTIC ONE-TO-ONE PAIRING"
    )

    print(
        "========================================"
    )


    for (
        level,
        count,
    ) in match_level_counts.items():


        print(

            f"{level}: "
            f"{count}"
        )


    print(
        f"\nTotal paired: "
        f"{len(pair_records)}"
    )


    print(
        f"Unresolved Previous Day: "
        f"{len(unresolved_previous_indexes)}"
    )


    print(
        f"Unresolved AIC WF: "
        f"{len(unresolved_wf_indexes)}"
    )


    # ========================================================
    # FIELD AGREEMENT
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "FIELD AGREEMENT AMONG PAIRED TRANSACTIONS"
    )

    print(
        "========================================"
    )


    if field_agreement:


        print(

            "Transaction description equal: "
            f"{field_agreement['transaction_type_equal_count']} "
            f"({field_agreement['transaction_type_equal_pct']}%)"
        )


        print(

            "Descriptive Text 1 equal: "
            f"{field_agreement['descriptive_text_equal_count']} "
            f"({field_agreement['descriptive_text_equal_pct']}%)"
        )


        print(

            "Main/ZBA-Sweep section equal: "
            f"{field_agreement['section_equal_count']} "
            f"({field_agreement['section_equal_pct']}%)"
        )


        print(

            "Reference-comparable pairs: "
            f"{field_agreement['reference_comparable_pairs']}"
        )


        print(

            "Raw reference equal: "
            f"{field_agreement['raw_reference_equal_count']}"
        )


        print(

            "Normalized reference equal: "
            f"{field_agreement['normalized_reference_equal_count']}"
        )


        print(

            "Raw ref differs but normalized ref agrees: "
            f"{field_agreement['raw_reference_diff_but_normalized_equal_count']}"
        )


    # ========================================================
    # MONTHLY SUMMARY
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "MONTHLY ALIGNMENT"
    )

    print(
        "========================================"
    )


    for month in monthly_summary:


        print(

            f"{month['accounting_period']} | "
            f"Previous Day: {month['previous_day_rows']} | "
            f"WF: {month['aic_wf_rows']} | "
            f"Paired: {month['diagnostically_paired']} | "
            f"PD unresolved: "
            f"{month['unresolved_previous_day']} | "
            f"WF unresolved: "
            f"{month['unresolved_aic_wf']} | "
            f"Section mismatches: "
            f"{month['paired_section_mismatches']}"
        )


    # ========================================================
    # OUTPUT PATHS
    # ========================================================

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
        "\nFull inspection report:"
    )


    print(
        "data/processed/"
        "previous_day_wf_alignment_inspection.json"
    )


    print(
        "\nDiagnostic transaction pairs:"
    )


    print(
        "data/processed/"
        "previous_day_wf_alignment_pairs.csv"
    )


    print(
        "\nUnresolved transactions:"
    )


    print(
        "data/processed/"
        "previous_day_wf_alignment_unresolved.csv"
    )


    print(
        "\nDo NOT yet treat the diagnostic hierarchy "
        "as the production matching rule."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()