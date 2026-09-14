# ============================================================
# TEST SUITE:
#
#     reconcile_current_month_ims_to_wf()
#
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# These tests establish that the second production control:
#
#     AIC WF category="IMS"
#               vs
#     current-month cleared IMS Credit
#
# behaves correctly under:
#
#   1. historical Jan-Jul evidence;
#   2. clean synthetic reconciliation;
#   3. non-IMS WF transactions;
#   4. outstanding / void / returned IMS statuses;
#   5. multiple cleared dates;
#   6. debit-side IMS transactions;
#   7. extra WF IMS transaction;
#   8. extra cleared IMS transaction;
#   9. missing normalized WF amount;
#  10. missing normalized IMS amount.
#
#
# IMPORTANT
# ------------------------------------------------------------
#
# The production control is tested AFTER normalization.
#
# There is no Excel color logic in this test suite.
#
# ============================================================


from decimal import Decimal
from pathlib import Path

import pytest


from src.ascot.reconcile_current_month_ims_to_wf import (
    WF_CATEGORY_PATH,
    IMS_TRANSACTION_PATH,
    reconcile_current_month_ims_to_wf,
    reconcile_period,
)


# ============================================================
# CONSTANT TEST PERIOD
# ============================================================

TEST_PERIOD = "2099-01"


# ============================================================
# SYNTHETIC CANONICAL WF ROW
# ============================================================

def make_wf(
    transaction_id,
    amount,
    category="IMS",
    period=TEST_PERIOD,
):
    """
    Create one canonical WF transaction.

    This represents the state AFTER any historical Excel
    formatting has already been converted into an explicit
    category.

    The reconciliation core sees only:

        category="IMS"

    not yellow formatting.
    """

    return {
        "transaction_id": transaction_id,
        "accounting_period": period,
        "category": category,
        "control_amount": (
            Decimal(str(amount))
            if amount is not None
            else None
        ),

        # Review / audit fields expected by production output.
        "source_workbook": "synthetic.xlsx",
        "source_sheet": "AIC WF",
        "source_row": "1",
        "as_of_date": "2099-01-15",
        "transaction_description": "SYNTHETIC TEST",
        "check_number": "",
        "descriptive_text_1": "",
        "category_source": "test_fixture",
    }


# ============================================================
# SYNTHETIC CANONICAL IMS ROW
# ============================================================

def make_ims(
    transaction_id,
    source_signed_amount,
    status="cleared",
    period=TEST_PERIOD,
):
    """
    Create one canonical normalized IMS transaction.

    source_signed_amount convention:

        negative = Credit / cash disbursement
        positive = Debit

    The production control sums Credit only.
    """

    if source_signed_amount is None:

        signed_amount = None
        credit_component = Decimal("0.00")

    else:

        signed_amount = Decimal(
            str(source_signed_amount)
        )

        # Reproduce the canonical production rule:
        #
        # negative source amount -> Credit
        # positive source amount -> does not contribute to Credit
        credit_component = (
            signed_amount
            if signed_amount < Decimal("0.00")
            else Decimal("0.00")
        )


    return {
        "transaction_id": transaction_id,
        "accounting_period": period,
        "cleared_status": status,
        "source_signed_amount": signed_amount,
        "credit_component": credit_component,

        # Review / audit fields expected by production output.
        "source_row": "1",
        "row_kind": "source_transaction",
        "transaction_date": "2099-01-10",
        "check_or_ref": "",
        "method": "",
        "payment_type": "",
        "description": "SYNTHETIC TEST",
        "date_cleared_raw": "2099/01/15",
        "cleared_dates": "2099-01-15",
    }


# ============================================================
# HELPER: RUN ONE SYNTHETIC MONTH
# ============================================================

def run_month(
    wf_rows,
    ims_rows,
):
    """
    Run the deterministic production reconciliation directly
    against canonical in-memory records.
    """

    return reconcile_period(
        accounting_period=TEST_PERIOD,
        wf_rows=wf_rows,
        ims_rows=ims_rows,
        tolerance=Decimal("0.00"),
    )


# ============================================================
# 1. HISTORICAL JAN-JUL BACKTEST
# ============================================================

def test_historical_backtest():
    """
    Historical evidence already established:

        Jan   FAIL   +300
        Feb   FAIL  -2220
        Mar   PASS       0
        Apr   PASS       0
        May   PASS       0
        Jun   PASS       0
        Jul   PASS       0

    January and February are REAL historical exceptions.

    This test ensures future code changes do not silently make
    those exceptions disappear.

    If processed historical files are unavailable, e.g. in a
    clean CI environment because data/processed is gitignored,
    this test is skipped rather than failing for lack of data.
    """

    if (
        not Path(WF_CATEGORY_PATH).exists()
        or not Path(IMS_TRANSACTION_PATH).exists()
    ):

        pytest.skip(
            "Historical processed Ascot data are not available."
        )


    result = reconcile_current_month_ims_to_wf()


    monthly = {
        row["accounting_period"]: row
        for row in result["monthly_results"]
    }


    # --------------------------------------------------------
    # JANUARY
    # --------------------------------------------------------

    assert monthly["2026-01"]["status"] == "FAIL"

    assert (
        Decimal(
            monthly["2026-01"]["variance"]
        )
        == Decimal("300.00")
    )


    # --------------------------------------------------------
    # FEBRUARY
    # --------------------------------------------------------

    assert monthly["2026-02"]["status"] == "FAIL"

    assert (
        Decimal(
            monthly["2026-02"]["variance"]
        )
        == Decimal("-2220.00")
    )


    # --------------------------------------------------------
    # MARCH THROUGH JULY
    # --------------------------------------------------------

    for period in [
        "2026-03",
        "2026-04",
        "2026-05",
        "2026-06",
        "2026-07",
    ]:

        assert monthly[period]["status"] == "PASS"

        assert (
            Decimal(
                monthly[period]["variance"]
            )
            == Decimal("0.00")
        )


    # The historical seven-month backtest overall should FAIL
    # because two genuine historical exceptions exist.
    assert result["overall_status"] == "FAIL"


# ============================================================
# 2. CLEAN BASELINE
# ============================================================

def test_clean_baseline_passes():
    """
    WF IMS total:

        100 + 200 = 300

    IMS cleared Credit:

        -100 + -200 = -300

    Normalized outflow:

        ABS(-300) = 300

    Therefore variance = 0.
    """

    wf_rows = [
        make_wf(
            "WF-1",
            "100.00",
        ),
        make_wf(
            "WF-2",
            "200.00",
        ),
    ]


    ims_rows = [
        make_ims(
            "IMS-1",
            "-100.00",
        ),
        make_ims(
            "IMS-2",
            "-200.00",
        ),
    ]


    result = run_month(
        wf_rows,
        ims_rows,
    )


    summary = result[
        "summary"
    ]


    assert summary["status"] == "PASS"

    assert (
        Decimal(
            summary["wf_ims_total"]
        )
        == Decimal("300.00")
    )

    assert (
        Decimal(
            summary["ims_normalized_outflow_total"]
        )
        == Decimal("300.00")
    )

    assert (
        Decimal(
            summary["variance"]
        )
        == Decimal("0.00")
    )


# ============================================================
# 3. NON-IMS WF TRANSACTIONS MUST BE IGNORED
# ============================================================

def test_non_ims_wf_transaction_is_not_in_control():
    """
    A WF transaction belonging to another category must not
    enter the IMS aggregate control.

    This is critical because main-cash WF contains other
    evidence routes besides IMS.
    """

    wf_rows = [
        make_wf(
            "WF-IMS",
            "100.00",
            category="IMS",
        ),

        make_wf(
            "WF-OTHER",
            "9999.00",
            category="BANK ITEMS",
        ),
    ]


    ims_rows = [
        make_ims(
            "IMS-1",
            "-100.00",
        ),
    ]


    result = run_month(
        wf_rows,
        ims_rows,
    )


    summary = result[
        "summary"
    ]


    assert summary["status"] == "PASS"

    assert (
        summary[
            "wf_ims_transaction_count"
        ]
        == 1
    )

    assert (
        Decimal(
            summary["wf_ims_total"]
        )
        == Decimal("100.00")
    )


# ============================================================
# 4. NON-CLEARED IMS STATUSES MUST BE EXCLUDED
# ============================================================

@pytest.mark.parametrize(
    "excluded_status",
    [
        "outstanding",
        "returned",
        "same_month_void",
        "void_reference",
    ],
)
def test_noncleared_ims_status_is_excluded(
    excluded_status,
):
    """
    Only normalized actual-clearing statuses belong in this
    aggregate control.

    These statuses must contribute nothing:

        outstanding
        returned
        same_month_void
        void_reference
    """

    wf_rows = [
        make_wf(
            "WF-1",
            "100.00",
        ),
    ]


    ims_rows = [
        # Genuine cleared transaction.
        make_ims(
            "IMS-CLEARED",
            "-100.00",
            status="cleared",
        ),

        # Must NOT enter the control.
        make_ims(
            "IMS-EXCLUDED",
            "-5000.00",
            status=excluded_status,
        ),
    ]


    result = run_month(
        wf_rows,
        ims_rows,
    )


    summary = result[
        "summary"
    ]


    assert summary["status"] == "PASS"

    assert (
        summary[
            "ims_cleared_transaction_count"
        ]
        == 1
    )

    assert (
        Decimal(
            summary[
                "ims_normalized_outflow_total"
            ]
        )
        == Decimal("100.00")
    )


# ============================================================
# 5. MULTIPLE CLEARED DATES = ONE TRANSACTION, ONE AMOUNT
# ============================================================

def test_multiple_cleared_dates_counted_once():
    """
    An IMS row can contain multiple Date Cleared values.

    The human procedure sums the Credit CELL once.

    Therefore:

        one IMS transaction
        with multiple clearing dates

    must NOT be multiplied by the number of dates.
    """

    wf_rows = [
        make_wf(
            "WF-1",
            "250.00",
        ),
    ]


    ims_rows = [
        make_ims(
            "IMS-1",
            "-250.00",
            status="multiple_cleared_dates",
        ),
    ]


    result = run_month(
        wf_rows,
        ims_rows,
    )


    summary = result[
        "summary"
    ]


    assert summary["status"] == "PASS"

    assert (
        summary[
            "ims_cleared_transaction_count"
        ]
        == 1
    )

    assert (
        Decimal(
            summary[
                "ims_normalized_outflow_total"
            ]
        )
        == Decimal("250.00")
    )


# ============================================================
# 6. DEBIT-SIDE IMS ROW MUST NOT BECOME CREDIT
# ============================================================

def test_debit_side_ims_row_does_not_inflate_credit_total():
    """
    The human control sums IMS column G Credit.

    Therefore a positive source_signed_amount representing a
    Debit must NOT be converted to an outflow merely because
    the row is marked cleared.
    """

    wf_rows = [
        make_wf(
            "WF-1",
            "100.00",
        ),
    ]


    ims_rows = [
        # Real Credit / cash disbursement.
        make_ims(
            "IMS-CREDIT",
            "-100.00",
            status="cleared",
        ),

        # Cleared Debit-side transaction.
        # It contributes zero to column-G Credit.
        make_ims(
            "IMS-DEBIT",
            "500.00",
            status="cleared",
        ),
    ]


    result = run_month(
        wf_rows,
        ims_rows,
    )


    summary = result[
        "summary"
    ]


    assert summary["status"] == "PASS"

    assert (
        Decimal(
            summary[
                "ims_normalized_outflow_total"
            ]
        )
        == Decimal("100.00")
    )

    # The production control should also make this visible as
    # diagnostic metadata.
    assert (
        summary[
            "ims_cleared_non_credit_row_count"
        ]
        == 1
    )


# ============================================================
# 7. EXTRA WF IMS TRANSACTION MUST CREATE A VARIANCE
# ============================================================

def test_extra_wf_ims_transaction_fails():
    """
    Simulate an IMS-coded WF transaction that is not represented
    in the cleared IMS Credit population.

    Expected variance:

        WF       125
        IMS      100
        variance +25
    """

    wf_rows = [
        make_wf(
            "WF-1",
            "100.00",
        ),

        make_wf(
            "WF-EXTRA",
            "25.00",
        ),
    ]


    ims_rows = [
        make_ims(
            "IMS-1",
            "-100.00",
        ),
    ]


    result = run_month(
        wf_rows,
        ims_rows,
    )


    summary = result[
        "summary"
    ]


    assert summary["status"] == "FAIL"

    assert (
        Decimal(
            summary["variance"]
        )
        == Decimal("25.00")
    )


    exception_types = {
        exception[
            "exception_type"
        ]
        for exception in result[
            "exceptions"
        ]
    }


    assert (
        "AGGREGATE_VARIANCE"
        in exception_types
    )


# ============================================================
# 8. EXTRA CLEARED IMS CREDIT MUST CREATE A VARIANCE
# ============================================================

def test_extra_cleared_ims_transaction_fails():
    """
    Simulate a cleared IMS Credit not represented in the WF
    IMS population.

    Expected:

        WF       100
        IMS      125
        variance -25
    """

    wf_rows = [
        make_wf(
            "WF-1",
            "100.00",
        ),
    ]


    ims_rows = [
        make_ims(
            "IMS-1",
            "-100.00",
        ),

        make_ims(
            "IMS-EXTRA",
            "-25.00",
        ),
    ]


    result = run_month(
        wf_rows,
        ims_rows,
    )


    summary = result[
        "summary"
    ]


    assert summary["status"] == "FAIL"

    assert (
        Decimal(
            summary["variance"]
        )
        == Decimal("-25.00")
    )


# ============================================================
# 9. MISSING WF NORMALIZED AMOUNT MUST NOT PASS
# ============================================================

def test_missing_wf_control_amount_is_data_quality_failure():
    """
    Even if the remaining dollar totals happen to reconcile,
    an IMS-classified WF transaction with no control amount
    prevents the control from legitimately passing.
    """

    wf_rows = [
        make_wf(
            "WF-1",
            "100.00",
        ),

        make_wf(
            "WF-MISSING",
            None,
        ),
    ]


    ims_rows = [
        make_ims(
            "IMS-1",
            "-100.00",
        ),
    ]


    result = run_month(
        wf_rows,
        ims_rows,
    )


    summary = result[
        "summary"
    ]


    # Aggregate arithmetic alone is zero...
    assert (
        Decimal(
            summary["variance"]
        )
        == Decimal("0.00")
    )


    # ...but control must still FAIL because the population is
    # not fully measurable.
    assert summary["status"] == "FAIL"

    assert (
        summary[
            "wf_missing_amount_count"
        ]
        == 1
    )


    exception_types = {
        exception[
            "exception_type"
        ]
        for exception in result[
            "exceptions"
        ]
    }


    assert (
        "WF_IMS_MISSING_CONTROL_AMOUNT"
        in exception_types
    )


# ============================================================
# 10. MISSING IMS NORMALIZED AMOUNT MUST NOT PASS
# ============================================================

def test_missing_ims_source_amount_is_data_quality_failure():
    """
    A row classified as cleared without a normalized source
    amount is a structural/data-quality exception.

    It must not disappear silently from the total.
    """

    wf_rows = [
        make_wf(
            "WF-1",
            "100.00",
        ),
    ]


    ims_rows = [
        make_ims(
            "IMS-1",
            "-100.00",
        ),

        make_ims(
            "IMS-MISSING",
            None,
            status="cleared",
        ),
    ]


    result = run_month(
        wf_rows,
        ims_rows,
    )


    summary = result[
        "summary"
    ]


    assert summary["status"] == "FAIL"

    assert (
        summary[
            "ims_missing_source_amount_count"
        ]
        == 1
    )


    exception_types = {
        exception[
            "exception_type"
        ]
        for exception in result[
            "exceptions"
        ]
    }


    assert (
        "IMS_CLEARED_MISSING_SOURCE_AMOUNT"
        in exception_types
    )