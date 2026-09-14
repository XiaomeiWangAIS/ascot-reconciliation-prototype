# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# FAILURE-MODE TESTS FOR:
#
#     reconcile_previous_day_to_wf()
#
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# Our historical January-July data all reconcile successfully.
#
# That proves the control can recognize a correct population.
#
# But a real control must also prove that it FAILS when:
#
#   1. a bank transaction is missing from WF;
#
#   2. WF contains a transaction not supported by the
#      Previous Day bank population;
#
#   3. duplicate-group counts differ;
#
#   4. WF places a transaction into the wrong logical section;
#
#   5. identifier formatting changes but the economic
#      transaction is still the same.
#
#
# IMPORTANT
# ------------------------------------------------------------
#
# This script NEVER modifies:
#
#     data/raw/
#
# or the sanitized CSV files.
#
# Python makes temporary copies in memory and deliberately
# changes those copies for testing.
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================
import pytest
import copy
import csv
import sys

from collections import Counter
from pathlib import Path


# ============================================================
# MAKE src/ IMPORTABLE
# ============================================================
#
# Repository structure:
#
#     repository/
#         src/
#             ascot/
#                 reconcile_previous_day_to_wf.py
#
#         tests/
#             test_reconcile_previous_day_to_wf.py
#
# We add src/ to Python's import path.
# ============================================================

PROJECT_ROOT = Path(
    __file__
).resolve().parents[1]


SRC_FOLDER = (
    PROJECT_ROOT
    / "src"
)


sys.path.insert(
    0,
    str(
        SRC_FOLDER
    ),
)


# ============================================================
# IMPORT THE ACTUAL PRODUCTION CONTROL
# ============================================================
#
# We are NOT rewriting reconciliation logic in the test.
#
# The test calls the exact production functions we just built.
# ============================================================

from ascot.reconcile_previous_day_to_wf import (  # noqa: E402

    reconcile_previous_day_to_wf,

    standardize_transaction,
)


# ============================================================
# INPUT FILES
# ============================================================

PROCESSED_FOLDER = (
    PROJECT_ROOT
    / "data"
    / "processed"
)


PREVIOUS_DAY_PATH = (

    PROCESSED_FOLDER

    / "aic_previous_day_all_months_transactions.csv"
)


AIC_WF_PATH = (

    PROCESSED_FOLDER

    / "aic_wf_all_months_transactions.csv"
)


# ============================================================
# READ CSV
# ============================================================

def read_csv(path):
    """
    Read our already-validated sanitized input.
    """

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
# FILTER ONE ACCOUNTING PERIOD
# ============================================================

def period_rows(
    rows,
    period,
):
    """
    Return only one accounting month's rows.

    copy.deepcopy() ensures our test can safely modify them
    without touching the original in-memory population.
    """

    return copy.deepcopy(

        [

            row

            for row
            in rows

            if row.get(
                "accounting_period"
            )
            == period
        ]
    )


# ============================================================
# GET SIGNATURE
# ============================================================

def get_signature(
    row,
    source_type,
):
    """
    Use the PRODUCTION standardization logic to calculate the
    transaction signature.

    This ensures our tests use exactly the same normalization
    rules as the real control.
    """

    standardized = standardize_transaction(

        row,

        source_type,
    )


    return standardized[
        "signature_tuple"
    ]


# ============================================================
# FIND ONE UNIQUELY MATCHED TRANSACTION
# ============================================================

def find_unique_pair(
    previous_rows,
    wf_rows,
):
    """
    Find a transaction signature occurring exactly once on
    each side.

    This avoids hard-coding a particular Excel row.
    """

    previous_counter = Counter(

        get_signature(
            row,
            "PREVIOUS_DAY",
        )

        for row
        in previous_rows
    )


    wf_counter = Counter(

        get_signature(
            row,
            "AIC_WF",
        )

        for row
        in wf_rows
    )


    for signature in previous_counter:


        if (

            previous_counter[
                signature
            ] == 1

            and

            wf_counter[
                signature
            ] == 1
        ):


            previous_row = next(

                row

                for row
                in previous_rows

                if get_signature(
                    row,
                    "PREVIOUS_DAY",
                )
                == signature
            )


            wf_row = next(

                row

                for row
                in wf_rows

                if get_signature(
                    row,
                    "AIC_WF",
                )
                == signature
            )


            return (

                signature,

                previous_row,

                wf_row,
            )


    raise AssertionError(

        "Could not find a unique matched transaction."
    )


# ============================================================
# FIND THE REAL DUPLICATE GROUP
# ============================================================

def find_duplicate_group(
    previous_rows,
    wf_rows,
):
    """
    Find a signature appearing more than once on both sides.

    In our actual Jan-Jul evidence this should locate the
    legitimate July duplicate group.
    """

    previous_counter = Counter(

        get_signature(
            row,
            "PREVIOUS_DAY",
        )

        for row
        in previous_rows
    )


    wf_counter = Counter(

        get_signature(
            row,
            "AIC_WF",
        )

        for row
        in wf_rows
    )


    for signature in previous_counter:


        if (

            previous_counter[
                signature
            ] > 1

            and

            previous_counter[
                signature
            ]
            == wf_counter[
                signature
            ]
        ):


            previous_group = [

                row

                for row
                in previous_rows

                if get_signature(
                    row,
                    "PREVIOUS_DAY",
                )
                == signature
            ]


            wf_group = [

                row

                for row
                in wf_rows

                if get_signature(
                    row,
                    "AIC_WF",
                )
                == signature
            ]


            return (

                signature,

                previous_group,

                wf_group,
            )


    raise AssertionError(

        "Could not find a matched duplicate group."
    )


# ============================================================
# HELPER:
# CHECK WHETHER AN EXCEPTION TYPE EXISTS
# ============================================================

def has_exception(
    exceptions,
    exception_type,
):

    return any(

        exception.get(
            "exception_type"
        )
        == exception_type

        for exception
        in exceptions
    )

@pytest.fixture(scope="session")
def all_previous_rows():
    return read_csv(
        PREVIOUS_DAY_PATH
    )


@pytest.fixture(scope="session")
def all_wf_rows():
    return read_csv(
        AIC_WF_PATH
    )
# ============================================================
# TEST 1
# BASELINE HISTORICAL DATA MUST PASS
# ============================================================

def test_baseline(
    all_previous_rows,
    all_wf_rows,
):
    """
    All actual Jan-Jul historical populations should PASS.
    """

    print(
        "\nTEST 1 — HISTORICAL BASELINE"
    )


    periods = [

        "2026-01",
        "2026-02",
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
        "2026-07",
    ]


    for period in periods:


        previous_rows = period_rows(

            all_previous_rows,

            period,
        )


        wf_rows = period_rows(

            all_wf_rows,

            period,
        )


        (
            summary,
            groups,
            exceptions,
        ) = reconcile_previous_day_to_wf(

            previous_rows,

            wf_rows,

            period,
        )


        assert (
            summary[
                "control_status"
            ]
            == "PASS"
        )


        assert (
            summary[
                "exception_count"
            ]
            == 0
        )


        assert (
            len(
                exceptions
            )
            == 0
        )


        print(
            f"  ✓ {period}: PASS"
        )


# ============================================================
# TEST 2
# REMOVE ONE WF TRANSACTION
# ============================================================

def test_missing_in_wf(
    all_previous_rows,
    all_wf_rows,
):
    """
    Simulate Resource Pro/WF accidentally omitting one
    transaction that exists in the bank population.

    Expected:

        FAIL
        MISSING_IN_WF = 1
    """

    period = (
        "2026-01"
    )


    previous_rows = period_rows(

        all_previous_rows,

        period,
    )


    wf_rows = period_rows(

        all_wf_rows,

        period,
    )


    (
        signature,
        previous_row,
        wf_row,
    ) = find_unique_pair(

        previous_rows,

        wf_rows,
    )


    print(
        "\nTEST 2 — MISSING TRANSACTION IN WF"
    )


    print(

        "  Removing WF source row "
        f"{wf_row.get('source_row')}"
    )


    # Remove precisely that one matching WF transaction.
    wf_rows = [

        row

        for row
        in wf_rows

        if row is not wf_row
    ]


    (
        summary,
        groups,
        exceptions,
    ) = reconcile_previous_day_to_wf(

        previous_rows,

        wf_rows,

        period,
    )


    assert (
        summary[
            "control_status"
        ]
        == "FAIL"
    )


    assert (
        summary[
            "missing_in_wf_transaction_count"
        ]
        == 1
    )


    assert has_exception(

        exceptions,

        "MISSING_IN_WF",
    )


    print(
        "  ✓ Control FAILED correctly."
    )


    print(
        "  ✓ MISSING_IN_WF detected."
    )


# ============================================================
# TEST 3
# REMOVE ONE PREVIOUS DAY TRANSACTION
# ============================================================

def test_unsupported_in_wf(
    all_previous_rows,
    all_wf_rows,
):
    """
    Simulate WF containing a transaction unsupported by the
    underlying Previous Day bank population.

    We create this condition by removing the corresponding
    Previous Day row from our temporary copy.

    Expected:

        FAIL
        UNSUPPORTED_IN_WF = 1
    """

    period = (
        "2026-02"
    )


    previous_rows = period_rows(

        all_previous_rows,

        period,
    )


    wf_rows = period_rows(

        all_wf_rows,

        period,
    )


    (
        signature,
        previous_row,
        wf_row,
    ) = find_unique_pair(

        previous_rows,

        wf_rows,
    )


    print(
        "\nTEST 3 — UNSUPPORTED WF TRANSACTION"
    )


    print(

        "  Removing Previous Day source row "
        f"{previous_row.get('source_row')}"
    )


    previous_rows = [

        row

        for row
        in previous_rows

        if row is not previous_row
    ]


    (
        summary,
        groups,
        exceptions,
    ) = reconcile_previous_day_to_wf(

        previous_rows,

        wf_rows,

        period,
    )


    assert (
        summary[
            "control_status"
        ]
        == "FAIL"
    )


    assert (
        summary[
            "unsupported_in_wf_transaction_count"
        ]
        == 1
    )


    assert has_exception(

        exceptions,

        "UNSUPPORTED_IN_WF",
    )


    print(
        "  ✓ Control FAILED correctly."
    )


    print(
        "  ✓ UNSUPPORTED_IN_WF detected."
    )


# ============================================================
# TEST 4
# DUPLICATE A UNIQUE WF TRANSACTION
# ============================================================

def test_count_mismatch(
    all_previous_rows,
    all_wf_rows,
):
    """
    Simulate WF containing two copies of a transaction while
    Previous Day contains only one.

    This should be a duplicate-count mismatch.

    Expected:

        FAIL
        COUNT_MISMATCH
    """

    period = (
        "2026-04"
    )


    previous_rows = period_rows(

        all_previous_rows,

        period,
    )


    wf_rows = period_rows(

        all_wf_rows,

        period,
    )


    (
        signature,
        previous_row,
        wf_row,
    ) = find_unique_pair(

        previous_rows,

        wf_rows,
    )


    print(
        "\nTEST 4 — DUPLICATE COUNT MISMATCH"
    )


    duplicate_row = copy.deepcopy(
        wf_row
    )


    # Give the synthetic row a fake source location only for
    # test readability.
    duplicate_row[
        "source_row"
    ] = "TEST_DUPLICATE"


    wf_rows.append(
        duplicate_row
    )


    (
        summary,
        groups,
        exceptions,
    ) = reconcile_previous_day_to_wf(

        previous_rows,

        wf_rows,

        period,
    )


    assert (
        summary[
            "control_status"
        ]
        == "FAIL"
    )


    assert has_exception(

        exceptions,

        "COUNT_MISMATCH",
    )


    print(
        "  ✓ Control FAILED correctly."
    )


    print(
        "  ✓ COUNT_MISMATCH detected."
    )


# ============================================================
# TEST 5
# CHANGE WF LOGICAL SECTION
# ============================================================

def test_section_mismatch(
    all_previous_rows,
    all_wf_rows,
):
    """
    The underlying bank transaction remains the same, but we
    deliberately give WF the wrong logical section.

    Example:

        main_cash_activity
              ↓
        zba_sweep_transfers

    Expected:

        FAIL
        SECTION_MISMATCH
    """

    period = (
        "2026-05"
    )


    previous_rows = period_rows(

        all_previous_rows,

        period,
    )


    wf_rows = period_rows(

        all_wf_rows,

        period,
    )


    (
        signature,
        previous_row,
        wf_row,
    ) = find_unique_pair(

        previous_rows,

        wf_rows,
    )


    print(
        "\nTEST 5 — SECTION MISMATCH"
    )


    original_section = wf_row.get(
        "section"
    )


    if (
        original_section
        == "main_cash_activity"
    ):


        wf_row[
            "section"
        ] = "zba_sweep_transfers"


    else:


        wf_row[
            "section"
        ] = "main_cash_activity"


    (
        summary,
        groups,
        exceptions,
    ) = reconcile_previous_day_to_wf(

        previous_rows,

        wf_rows,

        period,
    )


    assert (
        summary[
            "control_status"
        ]
        == "FAIL"
    )


    assert has_exception(

        exceptions,

        "SECTION_MISMATCH",
    )


    print(
        "  ✓ Control FAILED correctly."
    )


    print(
        "  ✓ SECTION_MISMATCH detected."
    )


# ============================================================
# TEST 6
# REAL JULY DUPLICATE GROUP
# ============================================================

def test_real_duplicate_group(
    all_previous_rows,
    all_wf_rows,
):
    """
    Verify that the actual July duplicate is handled as a
    GROUP rather than arbitrarily assigning individual rows.

    Expected:

        PASS

        1 duplicate group

        2 transactions inside that group
    """

    period = (
        "2026-07"
    )


    previous_rows = period_rows(

        all_previous_rows,

        period,
    )


    wf_rows = period_rows(

        all_wf_rows,

        period,
    )


    (
        signature,
        previous_group,
        wf_group,
    ) = find_duplicate_group(

        previous_rows,

        wf_rows,
    )


    print(
        "\nTEST 6 — REAL JULY DUPLICATE GROUP"
    )


    print(

        f"  Previous Day occurrences: "
        f"{len(previous_group)}"
    )


    print(

        f"  WF occurrences: "
        f"{len(wf_group)}"
    )


    (
        summary,
        groups,
        exceptions,
    ) = reconcile_previous_day_to_wf(

        previous_rows,

        wf_rows,

        period,
    )


    assert (
        summary[
            "control_status"
        ]
        == "PASS"
    )


    assert (
        summary[
            "duplicate_match_group_count"
        ]
        == 1
    )


    assert (
        summary[
            "duplicate_group_transaction_count"
        ]
        == 2
    )


    print(
        "  ✓ Duplicate group reconciled 2-to-2."
    )


    print(
        "  ✓ No false individual identity asserted."
    )


# ============================================================
# TEST 7
# BREAK THE JULY DUPLICATE GROUP
# ============================================================

def test_broken_duplicate_group(
    all_previous_rows,
    all_wf_rows,
):
    """
    Now remove one member from the real July WF duplicate
    group.

    Previous Day:

        2 occurrences

    WF:

        1 occurrence

    Expected:

        FAIL
        COUNT_MISMATCH
    """

    period = (
        "2026-07"
    )


    previous_rows = period_rows(

        all_previous_rows,

        period,
    )


    wf_rows = period_rows(

        all_wf_rows,

        period,
    )


    (
        signature,
        previous_group,
        wf_group,
    ) = find_duplicate_group(

        previous_rows,

        wf_rows,
    )


    print(
        "\nTEST 7 — BROKEN JULY DUPLICATE GROUP"
    )


    row_to_remove = (
        wf_group[
            0
        ]
    )


    wf_rows = [

        row

        for row
        in wf_rows

        if row is not row_to_remove
    ]


    (
        summary,
        groups,
        exceptions,
    ) = reconcile_previous_day_to_wf(

        previous_rows,

        wf_rows,

        period,
    )


    assert (
        summary[
            "control_status"
        ]
        == "FAIL"
    )


    assert has_exception(

        exceptions,

        "COUNT_MISMATCH",
    )


    print(
        "  ✓ Control FAILED correctly."
    )


    print(
        "  ✓ 2-to-1 duplicate mismatch detected."
    )


# ============================================================
# TEST 8
# IDENTIFIER FORMAT SHOULD NOT CREATE FALSE EXCEPTION
# ============================================================

def test_reference_normalization(
    all_previous_rows,
    all_wf_rows,
):
    """
    Test the empirical issue we discovered in the real data:

        03330005430

    versus:

        3330005430

    should represent the same reference.

    We deliberately prepend zeros to one WF check number.

    Expected:

        PASS
    """

    period = (
        "2026-06"
    )


    previous_rows = period_rows(

        all_previous_rows,

        period,
    )


    wf_rows = period_rows(

        all_wf_rows,

        period,
    )


    # Find a uniquely matched row whose check number is
    # numeric and nonempty.
    target_wf_row = None


    for wf_row in wf_rows:


        check_number = str(

            wf_row.get(
                "check_number"
            )
            or ""
        ).strip()


        if not check_number.isdigit():

            continue


        signature = get_signature(

            wf_row,

            "AIC_WF",
        )


        previous_occurrences = sum(

            get_signature(
                row,
                "PREVIOUS_DAY",
            )
            == signature

            for row
            in previous_rows
        )


        wf_occurrences = sum(

            get_signature(
                row,
                "AIC_WF",
            )
            == signature

            for row
            in wf_rows
        )


        if (

            previous_occurrences == 1

            and wf_occurrences == 1
        ):


            target_wf_row = (
                wf_row
            )

            break


    assert (
        target_wf_row
        is not None
    )


    original_reference = str(

        target_wf_row[
            "check_number"
        ]
    )


    print(
        "\nTEST 8 — REFERENCE NORMALIZATION"
    )


    print(

        f"  Original WF reference: "
        f"{original_reference}"
    )


    # Add leading zeros.
    target_wf_row[
        "check_number"
    ] = (

        "000"

        + original_reference
    )


    print(

        f"  Test WF reference: "
        f"{target_wf_row['check_number']}"
    )


    (
        summary,
        groups,
        exceptions,
    ) = reconcile_previous_day_to_wf(

        previous_rows,

        wf_rows,

        period,
    )


    assert (
        summary[
            "control_status"
        ]
        == "PASS"
    )


    assert (
        len(
            exceptions
        )
        == 0
    )


    print(
        "  ✓ Formatting difference did not create "
        "a false exception."
    )


# ============================================================
# MAIN TEST RUNNER
# ============================================================

def main():

    print(
        "ASCOT TEST SUITE"
    )


    print(
        "reconcile_previous_day_to_wf()"
    )


    # ========================================================
    # LOAD ACTUAL SANITIZED HISTORICAL DATA
    # ========================================================

    all_previous_rows = read_csv(
        PREVIOUS_DAY_PATH
    )


    all_wf_rows = read_csv(
        AIC_WF_PATH
    )


    # ========================================================
    # RUN TESTS
    # ========================================================

    tests = [

        (
            "Historical baseline",
            test_baseline,
        ),

        (
            "Missing in WF",
            test_missing_in_wf,
        ),

        (
            "Unsupported in WF",
            test_unsupported_in_wf,
        ),

        (
            "Count mismatch",
            test_count_mismatch,
        ),

        (
            "Section mismatch",
            test_section_mismatch,
        ),

        (
            "Real duplicate group",
            test_real_duplicate_group,
        ),

        (
            "Broken duplicate group",
            test_broken_duplicate_group,
        ),

        (
            "Reference normalization",
            test_reference_normalization,
        ),
    ]


    passed = 0


    failed = 0


    failures = []


    for (
        test_name,
        test_function,
    ) in tests:


        try:


            test_function(

                all_previous_rows,

                all_wf_rows,
            )


            passed += 1


        except Exception as error:


            failed += 1


            failures.append(

                {
                    "test":
                        test_name,

                    "error":
                        str(
                            error
                        ),
                }
            )


            print(

                f"\n✗ TEST FAILED: "
                f"{test_name}"
            )


            print(
                f"  {type(error).__name__}: "
                f"{error}"
            )


    # ========================================================
    # FINAL TEST RESULT
    # ========================================================

    print(
        "\n========================================"
    )


    print(
        "TEST SUITE COMPLETE"
    )


    print(
        "========================================"
    )


    print(
        f"Passed: {passed}"
    )


    print(
        f"Failed: {failed}"
    )


    if failed == 0:


        print(
            "\n✓ ALL TESTS PASSED"
        )


        print(
            "\nreconcile_previous_day_to_wf() is now "
            "validated for both successful reconciliation "
            "and major exception conditions."
        )


    else:


        print(
            "\n✗ SOME TESTS FAILED"
        )


        for failure in failures:


            print(

                f"  {failure['test']}: "
                f"{failure['error']}"
            )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()