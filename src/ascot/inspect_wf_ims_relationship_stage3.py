# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# AIC WF <-> AIC IMS
#
# STAGE 3 TARGETED RELATIONSHIP INSPECTION
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# Stages 1 and 2 showed that WF <-> IMS is NOT a simple
# one-to-one population reconciliation.
#
# Stage 3 focuses on the relationships that determine the
# eventual production architecture:
#
#   1. IMS status x accounting-period lag
#   2. IMS status x candidate basis
#   3. the 3 IMS transactions reused by multiple WF rows
#   4. IMS support rate by WF transaction type
#   5. CHECK PAID rows with no strong candidate
#   6. multiple-cleared-date IMS transactions
#   7. void / returned IMS transactions
#   8. tokenized GL correspondence
#
#
# THIS IS STILL INSPECTION.
#
# It does NOT create reconcile_wf_to_ims().
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import csv
import json
import re

from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path


# ============================================================
# PATHS
# ============================================================

PROCESSED_FOLDER = Path(
    "data/processed"
)


INSPECTION_FOLDER = (
    PROCESSED_FOLDER
    / "inspection"
    / "wf_to_ims"
)


WF_PROFILE_PATH = (
    INSPECTION_FOLDER
    / "wf_candidate_profile.csv"
)


IMS_PROFILE_PATH = (
    INSPECTION_FOLDER
    / "ims_candidate_profile.csv"
)


UNIQUE_PAIRS_PATH = (
    INSPECTION_FOLDER
    / "unique_strong_candidate_pairs.csv"
)


WF_PATH = (
    PROCESSED_FOLDER
    / "aic_wf_all_months_transactions.csv"
)


IMS_PATH = (
    PROCESSED_FOLDER
    / "aic_ims_all_months_transactions.csv"
)


IMS_ALLOCATIONS_PATH = (
    PROCESSED_FOLDER
    / "aic_ims_all_months_allocations.csv"
)


REPORT_PATH = (
    INSPECTION_FOLDER
    / "wf_ims_relationship_stage3.json"
)


COLLISION_PATH = (
    INSPECTION_FOLDER
    / "stage3_candidate_collisions.csv"
)


TYPE_SUPPORT_PATH = (
    INSPECTION_FOLDER
    / "stage3_wf_type_support.csv"
)


CHECK_PAID_PATH = (
    INSPECTION_FOLDER
    / "stage3_check_paid_no_strong.csv"
)


MULTIPLE_CLEAR_PATH = (
    INSPECTION_FOLDER
    / "stage3_multiple_cleared_dates.csv"
)


VOID_RETURN_PATH = (
    INSPECTION_FOLDER
    / "stage3_void_return_ims.csv"
)


GL_ANALYSIS_PATH = (
    INSPECTION_FOLDER
    / "stage3_gl_correspondence.csv"
)


# ============================================================
# BASIC FILE HELPERS
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
# SIMPLE HELPERS
# ============================================================

def to_int(value):

    try:

        return int(
            value
        )

    except (
        TypeError,
        ValueError,
    ):

        return 0


def to_decimal(value):

    if value in {
        None,
        "",
    }:

        return None


    try:

        return Decimal(
            str(value)
        )


    except InvalidOperation:

        return None


def month_index(period):
    """
    Convert YYYY-MM to one comparable integer.
    """

    year, month = period.split(
        "-"
    )


    return (
        int(year) * 12
        + int(month)
    )


def period_lag(
    wf_period,
    ims_period,
):
    """
    Positive:
        IMS period occurred BEFORE WF period.

    Zero:
        same period.

    Negative:
        IMS period occurred AFTER WF period.
    """

    return (

        month_index(
            wf_period
        )

        - month_index(
            ims_period
        )
    )


# ============================================================
# NORMALIZATION
# ============================================================

def normalize_text(value):

    if value is None:

        return ""


    return re.sub(
        r"\s+",
        " ",
        str(value).strip(),
    ).upper()


def normalize_identifier(value):

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


def identifier_key(value):
    """
    Same basic identifier principle already validated earlier:
    remove irrelevant numeric leading zeros.
    """

    text = normalize_identifier(
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

        if set(compact) == {
            "0"
        }:

            return None


        result = compact.lstrip(
            "0"
        )


        return (
            result
            if result
            else None
        )


    return normalize_text(
        text
    )


# ============================================================
# TOKENIZE WF GL VALUES
# ============================================================
#
# WF sometimes contains:
#
#     1020857/1020862
#
# or:
#
#     3023037/3023035/1020857
#
# Comparing the whole cell against a single IMS GL produces a
# false mismatch.
#
# We therefore inspect individual tokens.
# ============================================================

def gl_tokens(value):

    text = str(
        value or ""
    ).strip()


    if not text:

        return set()


    parts = re.split(
        r"[/,;|\s]+",
        text,
    )


    return {

        part.strip()

        for part
        in parts

        if part.strip()
    }


# ============================================================
# LOAD DATA
# ============================================================

def main():

    print(
        "ASCOT AIC WF <-> AIC IMS"
    )


    print(
        "STAGE 3 TARGETED INSPECTION"
    )


    wf_profiles = read_csv(
        WF_PROFILE_PATH
    )


    ims_profiles = read_csv(
        IMS_PROFILE_PATH
    )


    unique_pairs = read_csv(
        UNIQUE_PAIRS_PATH
    )


    wf_raw = read_csv(
        WF_PATH
    )


    ims_raw = read_csv(
        IMS_PATH
    )


    allocation_raw = read_csv(
        IMS_ALLOCATIONS_PATH
    )


    wf_raw_by_id = {


        (
            f"WF-"
            f"{row.get('accounting_period')}"
            f"-R{row.get('source_row')}"
        ):
            row

        for row
        in wf_raw
    }


    ims_raw_by_id = {

        row.get(
            "transaction_id"
        ):
            row

        for row
        in ims_raw
    }


    # ========================================================
    # ALLOCATIONS BY IMS TRANSACTION
    # ========================================================

    allocations_by_transaction = defaultdict(
        list
    )


    for allocation in allocation_raw:


        transaction_id = allocation.get(
            "transaction_id"
        )


        if transaction_id:

            allocations_by_transaction[
                transaction_id
            ].append(
                allocation
            )


    # ========================================================
    # 1. STATUS x PERIOD LAG
    # ========================================================
    #
    # This is especially important because Stage 2 showed:
    #
    #     cross-period candidate pairs = 257
    #     outstanding candidate pairs  = 256
    #
    # We now determine whether they are effectively the same
    # population.
    # ========================================================

    status_lag_matrix = Counter()


    basis_lag_matrix = Counter()


    status_basis_matrix = Counter()


    for pair in unique_pairs:


        lag = period_lag(

            pair[
                "wf_accounting_period"
            ],

            pair[
                "ims_accounting_period"
            ],
        )


        status = pair[
            "ims_cleared_status"
        ]


        basis = pair[
            "candidate_basis"
        ]


        status_lag_matrix[
            (
                status,
                lag,
            )
        ] += 1


        basis_lag_matrix[
            (
                basis,
                lag,
            )
        ] += 1


        status_basis_matrix[
            (
                status,
                basis,
            )
        ] += 1


    # ========================================================
    # 2. IMS CANDIDATE COLLISIONS
    # ========================================================
    #
    # Stage 2:
    #
    #     628 strong candidate pairs
    #     625 distinct IMS transactions
    #
    # Therefore exactly three IMS transactions are reused.
    #
    # We inspect ALL of them.
    # ========================================================

    pairs_by_ims = defaultdict(
        list
    )


    for pair in unique_pairs:


        pairs_by_ims[
            pair[
                "ims_transaction_id"
            ]
        ].append(
            pair
        )


    collision_rows = []


    collision_groups = {

        ims_id:
            pairs

        for ims_id, pairs
        in pairs_by_ims.items()

        if len(
            pairs
        ) > 1
    }


    for ims_id, pairs in (
        collision_groups.items()
    ):


        ims = ims_raw_by_id.get(
            ims_id,
            {}
        )


        for pair in pairs:


            collision_rows.append(

                {
                    "ims_transaction_id":
                        ims_id,

                    "number_of_wf_candidates":
                        len(
                            pairs
                        ),

                    "ims_period":
                        ims.get(
                            "accounting_period"
                        ),

                    "ims_source_row":
                        ims.get(
                            "source_row"
                        ),

                    "ims_transaction_date":
                        ims.get(
                            "transaction_datetime"
                        ),

                    "ims_check_or_ref":
                        ims.get(
                            "check_or_ref"
                        ),

                    "ims_description":
                        ims.get(
                            "source_description"
                        ),

                    "ims_source_signed_amount":
                        ims.get(
                            "source_signed_amount"
                        ),

                    "ims_cleared_status":
                        ims.get(
                            "cleared_status"
                        ),

                    "ims_date_cleared_raw":
                        ims.get(
                            "date_cleared_raw"
                        ),

                    "wf_transaction_id":
                        pair[
                            "wf_transaction_id"
                        ],

                    "wf_period":
                        pair[
                            "wf_accounting_period"
                        ],

                    "wf_date":
                        pair[
                            "wf_date"
                        ],

                    "wf_transaction_description":
                        pair[
                            "wf_transaction_description"
                        ],

                    "wf_amount":
                        pair[
                            "wf_amount"
                        ],

                    "wf_check":
                        pair[
                            "wf_check_raw"
                        ],

                    "candidate_basis":
                        pair[
                            "candidate_basis"
                        ],
                }
            )


    # ========================================================
    # 3. SUPPORT RATE BY WF TRANSACTION TYPE
    # ========================================================

    main_wf = [

        row

        for row
        in wf_profiles

        if row[
            "section"
        ] == "main_cash_activity"
    ]


    rows_by_type = defaultdict(
        list
    )


    for row in main_wf:


        rows_by_type[
            row[
                "transaction_description"
            ]
        ].append(
            row
        )


    type_support = []


    for transaction_type, rows in (
        rows_by_type.items()
    ):


        classes = Counter(

            row[
                "candidate_class"
            ]

            for row
            in rows
        )


        strong_unique = (

            classes[
                "UNIQUE_REFERENCE_PLUS_AMOUNT"
            ]

            + classes[
                "UNIQUE_AMOUNT_PLUS_CLEARED_DATE"
            ]
        )


        no_strong = classes[
            "NO_STRONG_CANDIDATE"
        ]


        other = (

            len(
                rows
            )

            - strong_unique

            - no_strong
        )


        type_support.append(

            {
                "transaction_description":
                    transaction_type,

                "total_main_wf_rows":
                    len(
                        rows
                    ),

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

                "no_strong_candidate_count":
                    no_strong,

                "other_candidate_class_count":
                    other,

                "unique_reference_plus_amount":
                    classes[
                        "UNIQUE_REFERENCE_PLUS_AMOUNT"
                    ],

                "unique_amount_plus_cleared_date":
                    classes[
                        "UNIQUE_AMOUNT_PLUS_CLEARED_DATE"
                    ],

                "unique_reference_different_amount":
                    classes[
                        "UNIQUE_REFERENCE_DIFFERENT_AMOUNT"
                    ],

                "unique_amount_plus_transaction_date":
                    classes[
                        "UNIQUE_AMOUNT_PLUS_TRANSACTION_DATE"
                    ],
            }
        )


    type_support.sort(

        key=lambda row: (
            -row[
                "total_main_wf_rows"
            ],
            row[
                "transaction_description"
            ],
        )
    )


    # ========================================================
    # 4. CHECK PAID WITH NO STRONG CANDIDATE
    # ========================================================
    #
    # CHECK PAID is especially important because it is likely
    # to be one of the cleanest IMS-supported transaction
    # families.
    #
    # We inspect every unresolved CHECK PAID row instead of
    # treating it as an exception automatically.
    # ========================================================

    unresolved_checks = []


    # Build IMS reference index.
    ims_by_reference = defaultdict(
        list
    )


    for ims in ims_raw:


        key = identifier_key(
            ims.get(
                "check_or_ref"
            )
        )


        if key:

            ims_by_reference[
                key
            ].append(
                ims
            )


    for profile in main_wf:


        if (
            profile[
                "transaction_description"
            ]
            != "CHECK PAID"
        ):

            continue


        if (
            profile[
                "candidate_class"
            ]
            != "NO_STRONG_CANDIDATE"
        ):

            continue


        wf_id = profile[
            "wf_transaction_id"
        ]


        wf = wf_raw_by_id.get(
            wf_id,
            {}
        )


        reference = profile[
            "check_key"
        ]


        same_ref_ims = (

            ims_by_reference.get(
                reference,
                []
            )

            if reference

            else []
        )


        if not same_ref_ims:


            unresolved_checks.append(

                {
                    "wf_transaction_id":
                        wf_id,

                    "wf_period":
                        profile[
                            "accounting_period"
                        ],

                    "wf_date":
                        profile[
                            "date"
                        ],

                    "wf_amount":
                        profile[
                            "amount"
                        ],

                    "wf_check_raw":
                        profile[
                            "check_raw"
                        ],

                    "wf_check_key":
                        reference,

                    "same_reference_ims_count":
                        0,
                }
            )


        else:


            for ims in same_ref_ims:


                signed_amount = to_decimal(

                    ims.get(
                        "source_signed_amount"
                    )
                )


                if signed_amount is not None:

                    signed_amount = abs(
                        signed_amount
                    )


                unresolved_checks.append(

                    {
                        "wf_transaction_id":
                            wf_id,

                        "wf_period":
                            profile[
                                "accounting_period"
                            ],

                        "wf_date":
                            profile[
                                "date"
                            ],

                        "wf_amount":
                            profile[
                                "amount"
                            ],

                        "wf_check_raw":
                            profile[
                                "check_raw"
                            ],

                        "wf_check_key":
                            reference,

                        "same_reference_ims_count":
                            len(
                                same_ref_ims
                            ),

                        "ims_transaction_id":
                            ims.get(
                                "transaction_id"
                            ),

                        "ims_period":
                            ims.get(
                                "accounting_period"
                            ),

                        "ims_transaction_date":
                            ims.get(
                                "transaction_datetime"
                            ),

                        "ims_amount":
                            (
                                str(
                                    signed_amount
                                )

                                if signed_amount
                                is not None

                                else None
                            ),

                        "ims_status":
                            ims.get(
                                "cleared_status"
                            ),

                        "ims_date_cleared_raw":
                            ims.get(
                                "date_cleared_raw"
                            ),

                        "ims_description":
                            ims.get(
                                "source_description"
                            ),
                    }
                )


    # ========================================================
    # 5. MULTIPLE-CLEARED-DATE IMS ITEMS
    # ========================================================

    multiple_clear_rows = []


    for ims in ims_raw:


        if (
            ims.get(
                "cleared_status"
            )
            != "multiple_cleared_dates"
        ):

            continue


        ims_id = ims[
            "transaction_id"
        ]


        profile = next(

            (
                row

                for row
                in ims_profiles

                if row[
                    "ims_transaction_id"
                ]
                == ims_id
            ),

            None,
        )


        allocation_count = len(

            allocations_by_transaction.get(
                ims_id,
                []
            )
        )


        multiple_clear_rows.append(

            {
                "ims_transaction_id":
                    ims_id,

                "accounting_period":
                    ims.get(
                        "accounting_period"
                    ),

                "source_row":
                    ims.get(
                        "source_row"
                    ),

                "transaction_date":
                    ims.get(
                        "transaction_datetime"
                    ),

                "check_or_ref":
                    ims.get(
                        "check_or_ref"
                    ),

                "description":
                    ims.get(
                        "source_description"
                    ),

                "source_signed_amount":
                    ims.get(
                        "source_signed_amount"
                    ),

                "date_cleared_raw":
                    ims.get(
                        "date_cleared_raw"
                    ),

                "cleared_dates":
                    ims.get(
                        "cleared_dates"
                    ),

                "allocation_count":
                    allocation_count,

                "wf_reference_plus_amount_candidate_count":
                    (
                        profile.get(
                            "wf_reference_plus_amount_candidate_count"
                        )

                        if profile

                        else None
                    ),

                "wf_amount_plus_cleared_date_candidate_count":
                    (
                        profile.get(
                            "wf_amount_plus_cleared_date_candidate_count"
                        )

                        if profile

                        else None
                    ),
            }
        )


    # ========================================================
    # 6. VOID / RETURN IMS ITEMS
    # ========================================================

    void_return_rows = []


    target_statuses = {

        "returned",

        "same_month_void",

        "void_reference",
    }


    pair_usage_count = Counter(

        pair[
            "ims_transaction_id"
        ]

        for pair
        in unique_pairs
    )


    for ims in ims_raw:


        status = ims.get(
            "cleared_status"
        )


        if status not in target_statuses:

            continue


        ims_id = ims[
            "transaction_id"
        ]


        profile = next(

            (
                row

                for row
                in ims_profiles

                if row[
                    "ims_transaction_id"
                ]
                == ims_id
            ),

            None,
        )


        void_return_rows.append(

            {
                "ims_transaction_id":
                    ims_id,

                "accounting_period":
                    ims.get(
                        "accounting_period"
                    ),

                "source_row":
                    ims.get(
                        "source_row"
                    ),

                "row_kind":
                    ims.get(
                        "row_kind"
                    ),

                "transaction_date":
                    ims.get(
                        "transaction_datetime"
                    ),

                "check_or_ref":
                    ims.get(
                        "check_or_ref"
                    ),

                "description":
                    ims.get(
                        "source_description"
                    ),

                "source_signed_amount":
                    ims.get(
                        "source_signed_amount"
                    ),

                "cleared_status":
                    status,

                "date_cleared_raw":
                    ims.get(
                        "date_cleared_raw"
                    ),

                "strong_candidate_pair_usage":
                    pair_usage_count[
                        ims_id
                    ],

                "wf_reference_plus_amount_candidate_count":
                    (
                        profile.get(
                            "wf_reference_plus_amount_candidate_count"
                        )

                        if profile

                        else None
                    ),

                "wf_amount_plus_cleared_date_candidate_count":
                    (
                        profile.get(
                            "wf_amount_plus_cleared_date_candidate_count"
                        )

                        if profile

                        else None
                    ),
            }
        )


    # ========================================================
    # 7. TOKENIZED GL CORRESPONDENCE
    # ========================================================

    gl_analysis = []


    exact_match = 0

    token_overlap_match = 0

    genuine_no_overlap = 0


    for pair in unique_pairs:


        wf_gl = str(
            pair.get(
                "wf_gl_account"
            )
            or ""
        ).strip()


        if not wf_gl:

            continue


        ims_accounts = {

            item

            for item
            in str(
                pair.get(
                    "ims_allocation_accounts"
                )
                or ""
            ).split("|")

            if item
        }


        wf_token_set = gl_tokens(
            wf_gl
        )


        # Exact whole-cell equality.
        whole_cell_exact = (

            wf_gl in ims_accounts
        )


        # More appropriate comparison for slash-delimited WF
        # accounting fields.
        overlap = (

            wf_token_set

            & ims_accounts
        )


        if whole_cell_exact:

            relationship = (
                "EXACT"
            )

            exact_match += 1


        elif overlap:

            relationship = (
                "TOKEN_OVERLAP"
            )

            token_overlap_match += 1


        else:

            relationship = (
                "NO_OVERLAP"
            )

            genuine_no_overlap += 1


        gl_analysis.append(

            {
                "wf_transaction_id":
                    pair[
                        "wf_transaction_id"
                    ],

                "wf_period":
                    pair[
                        "wf_accounting_period"
                    ],

                "wf_date":
                    pair[
                        "wf_date"
                    ],

                "wf_amount":
                    pair[
                        "wf_amount"
                    ],

                "wf_transaction_description":
                    pair[
                        "wf_transaction_description"
                    ],

                "ims_transaction_id":
                    pair[
                        "ims_transaction_id"
                    ],

                "candidate_basis":
                    pair[
                        "candidate_basis"
                    ],

                "wf_gl_raw":
                    wf_gl,

                "wf_gl_tokens":
                    "|".join(
                        sorted(
                            wf_token_set
                        )
                    ),

                "ims_allocation_accounts":
                    "|".join(
                        sorted(
                            ims_accounts
                        )
                    ),

                "overlap":
                    "|".join(
                        sorted(
                            overlap
                        )
                    ),

                "relationship":
                    relationship,
            }
        )


    # ========================================================
    # WRITE FILES
    # ========================================================

    write_csv(
        COLLISION_PATH,
        collision_rows,
    )


    write_csv(
        TYPE_SUPPORT_PATH,
        type_support,
    )


    write_csv(
        CHECK_PAID_PATH,
        unresolved_checks,
    )


    write_csv(
        MULTIPLE_CLEAR_PATH,
        multiple_clear_rows,
    )


    write_csv(
        VOID_RETURN_PATH,
        void_return_rows,
    )


    write_csv(
        GL_ANALYSIS_PATH,
        gl_analysis,
    )


    # ========================================================
    # JSON REPORT
    # ========================================================

    report = {

        "status_lag_matrix": [

            {
                "ims_status":
                    status,

                "lag":
                    lag,

                "count":
                    count,
            }

            for (
                status,
                lag,
            ), count
            in sorted(
                status_lag_matrix.items()
            )
        ],

        "candidate_basis_lag_matrix": [

            {
                "candidate_basis":
                    basis,

                "lag":
                    lag,

                "count":
                    count,
            }

            for (
                basis,
                lag,
            ), count
            in sorted(
                basis_lag_matrix.items()
            )
        ],

        "status_candidate_basis_matrix": [

            {
                "ims_status":
                    status,

                "candidate_basis":
                    basis,

                "count":
                    count,
            }

            for (
                status,
                basis,
            ), count
            in sorted(
                status_basis_matrix.items()
            )
        ],

        "collision_group_count":
            len(
                collision_groups
            ),

        "wf_type_support":
            type_support,

        "check_paid_no_strong_candidate_rows":
            len(
                unresolved_checks
            ),

        "multiple_cleared_date_ims_count":
            len(
                multiple_clear_rows
            ),

        "void_return_ims_count":
            len(
                void_return_rows
            ),

        "gl_correspondence": {

            "exact":
                exact_match,

            "token_overlap":
                token_overlap_match,

            "no_overlap":
                genuine_no_overlap,
        },
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
    # TERMINAL OUTPUT
    # ========================================================

    print(
        "\n========================================"
    )

    print(
        "1. IMS STATUS x PERIOD LAG"
    )

    print(
        "========================================"
    )


    for (
        status,
        lag,
    ), count in sorted(
        status_lag_matrix.items()
    ):


        print(

            f"{status:20} | "
            f"lag {lag}: "
            f"{count}"
        )


    print(
        "\n========================================"
    )

    print(
        "2. CANDIDATE BASIS x IMS STATUS"
    )

    print(
        "========================================"
    )


    for (
        status,
        basis,
    ), count in sorted(
        status_basis_matrix.items()
    ):


        print(

            f"{status:20} | "
            f"{basis:35} | "
            f"{count}"
        )


    print(
        "\n========================================"
    )

    print(
        "3. REUSED IMS CANDIDATES"
    )

    print(
        "========================================"
    )


    print(
        f"Collision groups: "
        f"{len(collision_groups)}"
    )


    for ims_id, pairs in (
        collision_groups.items()
    ):


        ims = ims_raw_by_id.get(
            ims_id,
            {}
        )


        print(
            "\n---"
        )


        print(

            f"{ims_id} | "
            f"status={ims.get('cleared_status')} | "
            f"ref={ims.get('check_or_ref')} | "
            f"amount={ims.get('source_signed_amount')} | "
            f"cleared={ims.get('date_cleared_raw')}"
        )


        for pair in pairs:


            print(

                "  WF "
                f"{pair['wf_transaction_id']} | "
                f"{pair['wf_date']} | "
                f"{pair['wf_transaction_description']} | "
                f"{pair['wf_amount']} | "
                f"basis={pair['candidate_basis']}"
            )


    print(
        "\n========================================"
    )

    print(
        "4. WF MAIN-CASH SUPPORT BY TRANSACTION TYPE"
    )

    print(
        "========================================"
    )


    for row in type_support:


        print(

            f"{row['transaction_description']}: "
            f"total={row['total_main_wf_rows']} | "
            f"strong={row['strong_unique_candidate_count']} "
            f"({row['strong_unique_candidate_pct']}%) | "
            f"no-strong={row['no_strong_candidate_count']} | "
            f"other={row['other_candidate_class_count']}"
        )


    print(
        "\n========================================"
    )

    print(
        "5. CHECK PAID WITH NO STRONG CANDIDATE"
    )

    print(
        "========================================"
    )


    unresolved_check_ids = {

        row[
            "wf_transaction_id"
        ]

        for row
        in unresolved_checks
    }


    print(
        f"Distinct WF CHECK PAID rows: "
        f"{len(unresolved_check_ids)}"
    )


    for row in unresolved_checks[
        :30
    ]:


        print(
            "\n---"
        )


        print(

            f"WF {row['wf_transaction_id']} | "
            f"{row['wf_date']} | "
            f"{row['wf_amount']} | "
            f"check={row['wf_check_raw']} | "
            f"same-ref IMS="
            f"{row['same_reference_ims_count']}"
        )


        if row.get(
            "ims_transaction_id"
        ):


            print(

                f"IMS {row['ims_transaction_id']} | "
                f"period={row['ims_period']} | "
                f"amount={row['ims_amount']} | "
                f"status={row['ims_status']} | "
                f"cleared={row['ims_date_cleared_raw']}"
            )


    print(
        "\n========================================"
    )

    print(
        "6. MULTIPLE-CLEARED-DATE IMS"
    )

    print(
        "========================================"
    )


    print(
        f"Count: "
        f"{len(multiple_clear_rows)}"
    )


    for row in multiple_clear_rows:


        print(
            "\n---"
        )


        print(

            f"{row['ims_transaction_id']} | "
            f"ref={row['check_or_ref']} | "
            f"amount={row['source_signed_amount']} | "
            f"cleared={row['date_cleared_raw']} | "
            f"allocations={row['allocation_count']} | "
            f"WF ref+amt candidates="
            f"{row['wf_reference_plus_amount_candidate_count']} | "
            f"WF amt+clear candidates="
            f"{row['wf_amount_plus_cleared_date_candidate_count']}"
        )


    print(
        "\n========================================"
    )

    print(
        "7. VOID / RETURN IMS SUMMARY"
    )

    print(
        "========================================"
    )


    status_counts = Counter(

        row[
            "cleared_status"
        ]

        for row
        in void_return_rows
    )


    for status, count in (
        status_counts.items()
    ):


        used = sum(

            row[
                "strong_candidate_pair_usage"
            ] > 0

            for row
            in void_return_rows

            if row[
                "cleared_status"
            ] == status
        )


        print(

            f"{status}: "
            f"{count} IMS rows | "
            f"{used} used by strong candidate(s)"
        )


    print(
        "\n========================================"
    )

    print(
        "8. TOKENIZED GL CORRESPONDENCE"
    )

    print(
        "========================================"
    )


    print(
        f"Exact whole-cell matches: "
        f"{exact_match}"
    )


    print(
        f"Additional token-overlap matches: "
        f"{token_overlap_match}"
    )


    print(
        f"Remaining no-overlap cases: "
        f"{genuine_no_overlap}"
    )


    if genuine_no_overlap:


        print(
            "\nFirst no-overlap cases:"
        )


        no_overlap_rows = [

            row

            for row
            in gl_analysis

            if row[
                "relationship"
            ] == "NO_OVERLAP"
        ]


        for row in no_overlap_rows[
            :15
        ]:


            print(

                f"  {row['wf_transaction_id']} | "
                f"WF={row['wf_gl_raw']} | "
                f"IMS={row['ims_allocation_accounts']} | "
                f"{row['wf_transaction_description']}"
            )


    print(
        "\n========================================"
    )

    print(
        "STAGE 3 INSPECTION COMPLETE"
    )

    print(
        "========================================"
    )


    print(
        "\nNo production WF -> IMS reconciliation "
        "rule has yet been created."
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()