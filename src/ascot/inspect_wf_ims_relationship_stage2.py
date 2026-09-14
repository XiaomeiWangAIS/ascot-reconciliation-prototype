# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# AIC WF <-> AIC IMS RELATIONSHIP
#
# STAGE 2 EMPIRICAL INSPECTION
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# Stage 1 established:
#
#   WF total                = 1,514
#   WF main cash            =   952
#   WF ZBA/sweep            =   562
#
#   IMS transactions        = 1,099
#
#   strong unique candidates = 628
#
# But these are still CANDIDATES, not production matches.
#
#
# STAGE 2 asks:
#
# 1. Does any IMS transaction get selected by MORE THAN ONE
#    WF transaction?
#
# 2. For cross-period candidates, does IMS normally originate
#    before the WF bank-clearing period?
#
# 3. Which IMS statuses appear among the 628 candidates?
#
# 4. What kinds of main-cash WF transactions make up the
#    320 "NO_STRONG_CANDIDATE" cases?
#
# 5. What exactly are the unusual:
#
#       UNIQUE_REFERENCE_DIFFERENT_AMOUNT
#       UNIQUE_AMOUNT_PLUS_TRANSACTION_DATE
#
#    cases?
#
# 6. What explains the GL mismatches?
#
# 7. What do WF and IMS cost-center values actually look like?
#
# 8. How are outstanding / void / returned IMS transactions
#    related to WF?
#
#
# IMPORTANT
# ------------------------------------------------------------
#
# This script DOES NOT:
#
#   - create production matching rules;
#   - force unresolved transactions together;
#   - use fuzzy matching;
#   - use an LLM;
#   - assume unmatched means error.
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

import csv
import json

from collections import Counter, defaultdict
from datetime import datetime
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


IMS_TRANSACTIONS_PATH = (
    PROCESSED_FOLDER
    / "aic_ims_all_months_transactions.csv"
)


STAGE2_REPORT_PATH = (
    INSPECTION_FOLDER
    / "wf_ims_relationship_stage2.json"
)


NO_STRONG_BY_TYPE_PATH = (
    INSPECTION_FOLDER
    / "main_no_strong_by_transaction_type.csv"
)


COLLISION_PATH = (
    INSPECTION_FOLDER
    / "candidate_collision_details.csv"
)


SPECIAL_CASE_PATH = (
    INSPECTION_FOLDER
    / "special_candidate_cases.csv"
)


GL_MISMATCH_PATH = (
    INSPECTION_FOLDER
    / "gl_mismatch_examples.csv"
)


COST_PATTERN_PATH = (
    INSPECTION_FOLDER
    / "cost_center_pair_patterns.csv"
)


# ============================================================
# CSV HELPERS
# ============================================================

def read_csv(path):

    if not path.exists():

        raise FileNotFoundError(
            f"Required file does not exist: {path}"
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
# BASIC HELPERS
# ============================================================

def to_bool(value):

    return str(
        value
    ).strip().lower() == "true"


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


def split_pipe(value):

    text = str(
        value or ""
    ).strip()


    if not text:

        return []


    return [

        item

        for item
        in text.split("|")

        if item
    ]


# ============================================================
# PERIOD DIFFERENCE
# ============================================================

def month_index(period):
    """
    Convert YYYY-MM into a sortable month number.
    """

    year, month = period.split(
        "-"
    )


    return (
        int(year) * 12
        + int(month)
    )


def month_lag(
    wf_period,
    ims_period,
):
    """
    Positive:
        IMS record is from an EARLIER accounting period than WF.

    Zero:
        same accounting period.

    Negative:
        IMS record is from a FUTURE period relative to WF.

    Negative relationships deserve special scrutiny.
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
# DATE HELPERS
# ============================================================

def parse_date(value):

    text = str(
        value or ""
    ).strip()


    if not text:

        return None


    text = text[:10]


    try:

        return datetime.strptime(
            text,
            "%Y-%m-%d",
        ).date()


    except ValueError:

        return None


# ============================================================
# LOAD DATA
# ============================================================

def main():

    print(
        "ASCOT AIC WF <-> AIC IMS"
    )


    print(
        "STAGE 2 RELATIONSHIP INSPECTION"
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


    ims_transactions = read_csv(
        IMS_TRANSACTIONS_PATH
    )


    ims_by_id = {

        row[
            "transaction_id"
        ]:
            row

        for row
        in ims_transactions
    }


    print(
        f"\nWF profiles: "
        f"{len(wf_profiles)}"
    )


    print(
        f"IMS profiles: "
        f"{len(ims_profiles)}"
    )


    print(
        f"Unique strong candidate pairs: "
        f"{len(unique_pairs)}"
    )


    # ========================================================
    # 1. GLOBAL CANDIDATE COLLISION CHECK
    # ========================================================
    #
    # Stage 1 classified candidates independently for each WF
    # transaction.
    #
    # We now ask:
    #
    #     Does the SAME IMS transaction appear as the unique
    #     candidate for multiple WF transactions?
    #
    # If yes, 628 cannot simply be called 628 one-to-one
    # matches.
    # ========================================================

    ims_candidate_usage = Counter(

        row[
            "ims_transaction_id"
        ]

        for row
        in unique_pairs
    )


    reused_ims_ids = {

        ims_id:
            count

        for ims_id, count
        in ims_candidate_usage.items()

        if count > 1
    }


    collision_details = []


    for pair in unique_pairs:


        ims_id = pair[
            "ims_transaction_id"
        ]


        if ims_id not in reused_ims_ids:

            continue


        collision_details.append(

            {
                "ims_transaction_id":
                    ims_id,

                "ims_usage_count":
                    reused_ims_ids[
                        ims_id
                    ],

                "wf_transaction_id":
                    pair[
                        "wf_transaction_id"
                    ],

                "wf_accounting_period":
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

                "candidate_basis":
                    pair[
                        "candidate_basis"
                    ],

                "ims_accounting_period":
                    pair[
                        "ims_accounting_period"
                    ],

                "ims_cleared_status":
                    pair[
                        "ims_cleared_status"
                    ],
            }
        )


    # ========================================================
    # 2. CROSS-PERIOD DIRECTION
    # ========================================================

    period_lag_counts = Counter()


    future_period_pairs = []


    for pair in unique_pairs:


        lag = month_lag(

            pair[
                "wf_accounting_period"
            ],

            pair[
                "ims_accounting_period"
            ],
        )


        period_lag_counts[
            lag
        ] += 1


        # A negative lag means the candidate IMS record comes
        # from a FUTURE workbook relative to the WF period.
        #
        # That does not automatically prove it is wrong, but
        # it deserves inspection.
        if lag < 0:


            future_period_pairs.append(

                {
                    "wf_transaction_id":
                        pair[
                            "wf_transaction_id"
                        ],

                    "wf_accounting_period":
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

                    "ims_transaction_id":
                        pair[
                            "ims_transaction_id"
                        ],

                    "ims_accounting_period":
                        pair[
                            "ims_accounting_period"
                        ],

                    "ims_transaction_date":
                        pair[
                            "ims_transaction_date"
                        ],

                    "ims_cleared_dates":
                        pair[
                            "ims_cleared_dates"
                        ],

                    "candidate_basis":
                        pair[
                            "candidate_basis"
                        ],
                }
            )


    # ========================================================
    # 3. TRANSACTION-DATE CHRONOLOGY
    # ========================================================

    chronology_comparable = 0

    ims_transaction_before_or_equal_wf = 0

    ims_transaction_after_wf = 0


    for pair in unique_pairs:


        wf_date = parse_date(
            pair[
                "wf_date"
            ]
        )


        ims_date = parse_date(
            pair[
                "ims_transaction_date"
            ]
        )


        if (
            wf_date is None
            or ims_date is None
        ):

            continue


        chronology_comparable += 1


        if ims_date <= wf_date:

            ims_transaction_before_or_equal_wf += 1


        else:

            ims_transaction_after_wf += 1


    # ========================================================
    # 4. CANDIDATE BASIS x IMS STATUS
    # ========================================================

    candidate_status_matrix = Counter()


    for pair in unique_pairs:


        candidate_status_matrix[
            (
                pair[
                    "candidate_basis"
                ],

                pair[
                    "ims_cleared_status"
                ],
            )
        ] += 1


    # ========================================================
    # 5. STRONG CANDIDATES BY IMS STATUS
    # ========================================================

    strong_candidate_ids = {

        pair[
            "ims_transaction_id"
        ]

        for pair
        in unique_pairs
    }


    strong_status_counts = Counter(

        pair[
            "ims_cleared_status"
        ]

        for pair
        in unique_pairs
    )


    # ========================================================
    # 6. IMS STATUS COVERAGE
    # ========================================================
    #
    # Looking from IMS toward WF:
    #
    # How many cleared / outstanding / void transactions have
    # ANY reference+amount or amount+cleared-date candidate?
    # ========================================================

    ims_status_total = Counter()

    ims_status_any_candidate = Counter()

    ims_status_strong_candidate = Counter()


    for profile in ims_profiles:


        status = profile[
            "cleared_status"
        ]


        ims_status_total[
            status
        ] += 1


        has_any_candidate = (

            to_int(
                profile[
                    "wf_reference_plus_amount_candidate_count"
                ]
            ) > 0

            or

            to_int(
                profile[
                    "wf_amount_plus_cleared_date_candidate_count"
                ]
            ) > 0
        )


        if has_any_candidate:

            ims_status_any_candidate[
                status
            ] += 1


        if (
            profile[
                "ims_transaction_id"
            ]
            in strong_candidate_ids
        ):

            ims_status_strong_candidate[
                status
            ] += 1


    # ========================================================
    # 7. MAIN-CASH NO-STRONG CANDIDATES BY TRAN DESC
    # ========================================================

    main_no_strong = [

        row

        for row
        in wf_profiles

        if (

            row[
                "section"
            ]
            == "main_cash_activity"

            and

            row[
                "candidate_class"
            ]
            == "NO_STRONG_CANDIDATE"
        )
    ]


    no_strong_type_counter = Counter(

        row[
            "transaction_description"
        ]

        for row
        in main_no_strong
    )


    no_strong_by_type = []


    for (
        transaction_type,
        count,
    ) in no_strong_type_counter.most_common():


        rows = [

            row

            for row
            in main_no_strong

            if row[
                "transaction_description"
            ]
            == transaction_type
        ]


        with_reference = sum(

            bool(
                row[
                    "check_key"
                ]
            )

            for row
            in rows
        )


        without_reference = (

            count
            - with_reference
        )


        no_strong_by_type.append(

            {
                "transaction_description":
                    transaction_type,

                "no_strong_candidate_count":
                    count,

                "with_normalized_reference":
                    with_reference,

                "without_normalized_reference":
                    without_reference,
            }
        )


    # ========================================================
    # 8. SPECIAL CANDIDATE CASES
    # ========================================================
    #
    # Stage 1 found:
    #
    #   2 UNIQUE_REFERENCE_DIFFERENT_AMOUNT
    #   2 UNIQUE_AMOUNT_PLUS_TRANSACTION_DATE
    #
    # We print the exact underlying relationship rather than
    # creating rules from these four rows.
    # ========================================================

    special_classes = {

        "UNIQUE_REFERENCE_DIFFERENT_AMOUNT",

        "UNIQUE_AMOUNT_PLUS_TRANSACTION_DATE",

        "MULTIPLE_REFERENCE_PLUS_AMOUNT",

        "MULTIPLE_AMOUNT_PLUS_CLEARED_DATE",

        "MULTIPLE_REFERENCE_DIFFERENT_AMOUNT",

        "MULTIPLE_AMOUNT_PLUS_TRANSACTION_DATE",
    }


    special_cases = []


    for wf in wf_profiles:


        if (
            wf[
                "candidate_class"
            ]
            not in special_classes
        ):

            continue


        candidate_ids = split_pipe(

            wf[
                "strongest_candidate_ids"
            ]
        )


        if not candidate_ids:


            special_cases.append(

                {
                    "wf_transaction_id":
                        wf[
                            "wf_transaction_id"
                        ],

                    "wf_period":
                        wf[
                            "accounting_period"
                        ],

                    "wf_date":
                        wf[
                            "date"
                        ],

                    "wf_type":
                        wf[
                            "transaction_description"
                        ],

                    "wf_amount":
                        wf[
                            "amount"
                        ],

                    "wf_check":
                        wf[
                            "check_raw"
                        ],

                    "candidate_class":
                        wf[
                            "candidate_class"
                        ],
                }
            )


            continue


        for ims_id in candidate_ids:


            ims = ims_by_id.get(
                ims_id,
                {}
            )


            ims_amount = to_decimal(

                ims.get(
                    "source_signed_amount"
                )
            )


            if ims_amount is not None:

                ims_amount = abs(
                    ims_amount
                )


            special_cases.append(

                {
                    "wf_transaction_id":
                        wf[
                            "wf_transaction_id"
                        ],

                    "wf_period":
                        wf[
                            "accounting_period"
                        ],

                    "wf_date":
                        wf[
                            "date"
                        ],

                    "wf_type":
                        wf[
                            "transaction_description"
                        ],

                    "wf_amount":
                        wf[
                            "amount"
                        ],

                    "wf_check":
                        wf[
                            "check_raw"
                        ],

                    "candidate_class":
                        wf[
                            "candidate_class"
                        ],

                    "ims_transaction_id":
                        ims_id,

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

                    "ims_check":
                        ims.get(
                            "check_or_ref"
                        ),

                    "ims_amount":
                        (
                            str(
                                ims_amount
                            )

                            if ims_amount is not None

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

                    "ims_method":
                        ims.get(
                            "method"
                        ),

                    "ims_payment_type":
                        ims.get(
                            "payment_type"
                        ),
                }
            )


    # ========================================================
    # 9. ALLOCATION MULTIPLICITY AMONG STRONG CANDIDATES
    # ========================================================

    strong_allocation_distribution = Counter(

        to_int(
            pair[
                "ims_allocation_count"
            ]
        )

        for pair
        in unique_pairs
    )


    # ========================================================
    # 10. GL MISMATCH EXAMPLES
    # ========================================================

    gl_mismatches = []


    for pair in unique_pairs:


        if not pair[
            "wf_gl_account"
        ]:

            continue


        if to_bool(
            pair[
                "wf_gl_matches_any_ims_allocation"
            ]
        ):

            continue


        gl_mismatches.append(

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

                "candidate_basis":
                    pair[
                        "candidate_basis"
                    ],

                "ims_transaction_id":
                    pair[
                        "ims_transaction_id"
                    ],

                "ims_status":
                    pair[
                        "ims_cleared_status"
                    ],

                "ims_allocation_count":
                    pair[
                        "ims_allocation_count"
                    ],

                "wf_gl_account":
                    pair[
                        "wf_gl_account"
                    ],

                "ims_allocation_accounts":
                    pair[
                        "ims_allocation_accounts"
                    ],
            }
        )


    # ========================================================
    # 11. COST-CENTER VALUE PAIRS
    # ========================================================
    #
    # Stage 1 gave:
    #
    #     WF cost center present: 110
    #     exact IMS allocation match: 0
    #
    # Do NOT interpret this yet.
    #
    # Here we inspect the actual value combinations.
    # ========================================================

    cost_pair_counter = Counter()


    for pair in unique_pairs:


        wf_cost = str(
            pair[
                "wf_cost_center"
            ]
            or ""
        ).strip()


        ims_costs = str(
            pair[
                "ims_allocation_cost_centers"
            ]
            or ""
        ).strip()


        if not wf_cost:

            continue


        cost_pair_counter[
            (
                wf_cost,
                ims_costs,
            )
        ] += 1


    cost_patterns = [

        {
            "wf_cost_center":
                wf_cost,

            "ims_allocation_cost_centers":
                ims_costs,

            "pair_count":
                count,
        }

        for (
            wf_cost,
            ims_costs,
        ), count
        in cost_pair_counter.most_common()
    ]


    # ========================================================
    # WRITE DETAIL OUTPUTS
    # ========================================================

    write_csv(

        NO_STRONG_BY_TYPE_PATH,

        no_strong_by_type,
    )


    write_csv(

        COLLISION_PATH,

        collision_details,
    )


    write_csv(

        SPECIAL_CASE_PATH,

        special_cases,
    )


    write_csv(

        GL_MISMATCH_PATH,

        gl_mismatches,
    )


    write_csv(

        COST_PATTERN_PATH,

        cost_patterns,
    )


    # ========================================================
    # JSON REPORT
    # ========================================================

    report = {

        "candidate_collision_analysis": {

            "unique_strong_pair_count":
                len(
                    unique_pairs
                ),

            "distinct_ims_transactions_used":
                len(
                    ims_candidate_usage
                ),

            "ims_transactions_reused_by_multiple_wf_rows":
                len(
                    reused_ims_ids
                ),

            "maximum_wf_rows_per_ims_candidate":
                (
                    max(
                        ims_candidate_usage.values()
                    )

                    if ims_candidate_usage

                    else 0
                ),
        },

        "cross_period_analysis": {

            "month_lag_distribution":
                {

                    str(
                        lag
                    ):
                        count

                    for lag, count
                    in sorted(
                        period_lag_counts.items()
                    )
                },

            "future_period_candidate_count":
                len(
                    future_period_pairs
                ),
        },

        "transaction_date_chronology": {

            "comparable_pairs":
                chronology_comparable,

            "ims_transaction_date_before_or_equal_wf_date":
                ims_transaction_before_or_equal_wf,

            "ims_transaction_date_after_wf_date":
                ims_transaction_after_wf,
        },

        "strong_candidate_status_counts":
            dict(
                strong_status_counts
            ),

        "ims_status_coverage": {

            status: {

                "total":
                    ims_status_total[
                        status
                    ],

                "has_any_candidate_signal":
                    ims_status_any_candidate[
                        status
                    ],

                "used_as_unique_strong_candidate":
                    ims_status_strong_candidate[
                        status
                    ],
            }

            for status
            in sorted(
                ims_status_total
            )
        },

        "main_no_strong_candidate_count":
            len(
                main_no_strong
            ),

        "main_no_strong_by_transaction_type":
            no_strong_by_type,

        "strong_candidate_allocation_distribution":
            {

                str(
                    count
                ):
                    number

                for count, number
                in sorted(
                    strong_allocation_distribution.items()
                )
            },

        "gl_mismatch_count":
            len(
                gl_mismatches
            ),

        "cost_center_distinct_pair_patterns":
            len(
                cost_patterns
            ),

        "special_candidate_case_count":
            len(
                special_cases
            ),
    }


    with STAGE2_REPORT_PATH.open(

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
        "1. CANDIDATE COLLISIONS"
    )

    print(
        "========================================"
    )


    print(
        "Strong candidate pairs: "
        f"{len(unique_pairs)}"
    )


    print(
        "Distinct IMS transactions used: "
        f"{len(ims_candidate_usage)}"
    )


    print(
        "IMS transactions reused by >1 WF row: "
        f"{len(reused_ims_ids)}"
    )


    if reused_ims_ids:


        print(
            "Maximum WF rows sharing one IMS candidate: "
            f"{max(reused_ims_ids.values())}"
        )


    print(
        "\n========================================"
    )

    print(
        "2. CROSS-PERIOD DIRECTION"
    )

    print(
        "========================================"
    )


    for lag, count in sorted(
        period_lag_counts.items()
    ):


        if lag == 0:

            interpretation = (
                "same period"
            )


        elif lag > 0:

            interpretation = (
                f"IMS {lag} month(s) earlier than WF"
            )


        else:

            interpretation = (
                f"IMS {abs(lag)} month(s) AFTER WF"
            )


        print(

            f"Lag {lag}: "
            f"{count} "
            f"({interpretation})"
        )


    print(
        "\nFuture-period candidates: "
        f"{len(future_period_pairs)}"
    )


    print(
        "\n========================================"
    )

    print(
        "3. TRANSACTION-DATE CHRONOLOGY"
    )

    print(
        "========================================"
    )


    print(
        "Comparable pairs: "
        f"{chronology_comparable}"
    )


    print(
        "IMS transaction date <= WF date: "
        f"{ims_transaction_before_or_equal_wf}"
    )


    print(
        "IMS transaction date > WF date: "
        f"{ims_transaction_after_wf}"
    )


    print(
        "\n========================================"
    )

    print(
        "4. STRONG CANDIDATES BY IMS STATUS"
    )

    print(
        "========================================"
    )


    for status, count in (
        strong_status_counts.most_common()
    ):


        print(
            f"{status}: {count}"
        )


    print(
        "\n========================================"
    )

    print(
        "5. IMS STATUS COVERAGE"
    )

    print(
        "========================================"
    )


    for status in sorted(
        ims_status_total
    ):


        print(
            f"\n{status}"
        )


        print(
            f"  IMS transactions: "
            f"{ims_status_total[status]}"
        )


        print(
            "  Has any candidate signal: "
            f"{ims_status_any_candidate[status]}"
        )


        print(
            "  Used as unique strong candidate: "
            f"{ims_status_strong_candidate[status]}"
        )


    print(
        "\n========================================"
    )

    print(
        "6. MAIN-CASH WF WITH NO STRONG IMS CANDIDATE"
    )

    print(
        "========================================"
    )


    print(
        f"Total: "
        f"{len(main_no_strong)}"
    )


    print(
        "\nTop transaction descriptions:"
    )


    for row in no_strong_by_type[
        :20
    ]:


        print(

            f"  "
            f"{row['transaction_description']}: "
            f"{row['no_strong_candidate_count']} "
            f"| with ref "
            f"{row['with_normalized_reference']} "
            f"| without ref "
            f"{row['without_normalized_reference']}"
        )


    print(
        "\n========================================"
    )

    print(
        "7. SPECIAL CANDIDATE CASES"
    )

    print(
        "========================================"
    )


    print(
        f"Cases written to detail file: "
        f"{len(special_cases)}"
    )


    for case in special_cases[
        :20
    ]:


        print(
            "\n---"
        )


        print(

            f"WF {case.get('wf_transaction_id')} | "
            f"{case.get('candidate_class')}"
        )


        print(

            f"WF: "
            f"{case.get('wf_date')} | "
            f"{case.get('wf_type')} | "
            f"{case.get('wf_amount')} | "
            f"ref={case.get('wf_check')}"
        )


        if case.get(
            "ims_transaction_id"
        ):


            print(

                f"IMS: "
                f"{case.get('ims_transaction_id')} | "
                f"{case.get('ims_transaction_date')} | "
                f"{case.get('ims_amount')} | "
                f"ref={case.get('ims_check')} | "
                f"status={case.get('ims_status')}"
            )


            print(

                "IMS cleared field: "
                f"{case.get('ims_date_cleared_raw')}"
            )


    print(
        "\n========================================"
    )

    print(
        "8. ALLOCATION MULTIPLICITY AMONG STRONG CANDIDATES"
    )

    print(
        "========================================"
    )


    for (
        allocation_count,
        transaction_count,
    ) in sorted(
        strong_allocation_distribution.items()
    ):


        print(

            f"{allocation_count} allocation(s): "
            f"{transaction_count} candidate pair(s)"
        )


    print(
        "\n========================================"
    )

    print(
        "9. GL MISMATCHES"
    )

    print(
        "========================================"
    )


    print(
        f"GL mismatch count: "
        f"{len(gl_mismatches)}"
    )


    for row in gl_mismatches[
        :15
    ]:


        print(

            f"  {row['wf_transaction_id']} | "
            f"WF GL={row['wf_gl_account']} | "
            f"IMS={row['ims_allocation_accounts']} | "
            f"allocations={row['ims_allocation_count']}"
        )


    print(
        "\n========================================"
    )

    print(
        "10. COST-CENTER VALUE PATTERNS"
    )

    print(
        "========================================"
    )


    print(
        f"Distinct WF/IMS patterns: "
        f"{len(cost_patterns)}"
    )


    for row in cost_patterns[
        :20
    ]:


        print(

            f"  WF={row['wf_cost_center']} | "
            f"IMS={row['ims_allocation_cost_centers']} | "
            f"count={row['pair_count']}"
        )


    print(
        "\n========================================"
    )

    print(
        "STAGE 2 INSPECTION COMPLETE"
    )

    print(
        "========================================"
    )


    print(
        "\nNo production reconciliation logic "
        "has been created."
    )


    print(
        "\nDetailed outputs:"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "wf_ims_relationship_stage2.json"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "main_no_strong_by_transaction_type.csv"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "candidate_collision_details.csv"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "special_candidate_cases.csv"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "gl_mismatch_examples.csv"
    )


    print(
        "data/processed/inspection/wf_to_ims/"
        "cost_center_pair_patterns.csv"
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()