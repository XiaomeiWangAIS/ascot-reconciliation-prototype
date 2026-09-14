# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
#
# HUMAN REJECTION-REVIEW CONTROL
# ============================================================
#
# BUSINESS REQUIREMENT
# ------------------------------------------------------------
#
# Every rejection must:
#
#   1. be accounted for; and
#   2. be explained.
#
# If the rejection is UNKNOWN:
#
#   3. it must also be escalated before the journal entry
#      can be finalized.
#
#
# DESIGN DECISION
# ------------------------------------------------------------
#
# We intentionally DO NOT automate human recognition of a
# rejected transaction in the first prototype.
#
# The accountant can continue visually reviewing rejections.
#
# This module only provides the CONTROL LAYER:
#
#     rejection identified
#             ↓
#     human reviews it
#             ↓
#     "Has it been accounted for?"
#             ↓
#     explanation recorded
#             ↓
#     if unknown:
#         escalation must be documented
#             ↓
#     finalization gate
#
#
# IMPORTANT
# ------------------------------------------------------------
#
# An incomplete rejection review:
#
#     DOES NOT stop unaffected reconciliation work.
#
# But:
#
#     DOES block FINAL JOURNAL ENTRY FINALIZATION.
#
#
# FUTURE EXTENSIONS
# ------------------------------------------------------------
#
# We can later plug in:
#
#   - automatic rejection detection;
#   - historical-memory retrieval;
#   - automated backup requests;
#   - email / Teams integration;
#   - evidence retrieval;
#   - machine-assisted recognition.
#
# None of those are required for the current prototype.
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

from copy import deepcopy
from datetime import datetime, timezone


# ============================================================
# CONSTANTS
# ============================================================

REVIEW_TYPE = "REJECTION_REVIEW"

PENDING = "PENDING"

COMPLETE = "COMPLETE"

BLOCKED = "BLOCKED"


# ============================================================
# TIME HELPER
# ============================================================

def utc_now_iso():
    """
    Return the current UTC timestamp in an auditable,
    machine-readable ISO format.
    """

    return datetime.now(
        timezone.utc
    ).isoformat()


# ============================================================
# CREATE ONE REJECTION-REVIEW ITEM
# ============================================================

def create_rejection_review_item(
    transaction,
    review_reason="Rejection requires human confirmation",
):
    """
    Create a standardized rejection-review record.

    Parameters
    ----------
    transaction:
        Canonical transaction dictionary.

        It MUST contain:
            transaction_id

        Other transaction information is preserved so a future
        UI can display date, amount, description, reference,
        evidence, etc.

    review_reason:
        Why this transaction entered rejection review.

    Returns
    -------
    dict
        New rejection-review item.

    Important
    ---------
    This function does NOT decide whether the rejection has
    been handled correctly.

    It simply creates the human-control record.
    """

    transaction_id = str(
        transaction.get(
            "transaction_id",
            "",
        )
    ).strip()


    if not transaction_id:

        raise ValueError(
            "A rejection-review item requires transaction_id."
        )


    return {
        # ----------------------------------------------------
        # IDENTITY
        # ----------------------------------------------------

        "transaction_id":
            transaction_id,

        "review_type":
            REVIEW_TYPE,

        "review_reason":
            str(
                review_reason
            ).strip(),

        # ----------------------------------------------------
        # ORIGINAL TRANSACTION
        # ----------------------------------------------------
        #
        # Preserve the transaction for auditability and future
        # display in Streamlit / another review interface.
        # ----------------------------------------------------

        "transaction":
            deepcopy(
                transaction
            ),

        # ----------------------------------------------------
        # HUMAN CONFIRMATION
        # ----------------------------------------------------

        "accounted_for":
            False,

        "explanation":
            "",

        # ----------------------------------------------------
        # UNKNOWN-REJECTION CONTROL
        # ----------------------------------------------------

        "is_unknown":
            False,

        "escalated":
            False,

        "escalation_notes":
            "",

        # ----------------------------------------------------
        # REVIEW PROVENANCE
        # ----------------------------------------------------

        "reviewed_by":
            "",

        "reviewed_at":
            None,

        # ----------------------------------------------------
        # CONTROL STATE
        # ----------------------------------------------------

        "review_status":
            PENDING,

        "review_complete":
            False,

        # Why finalization is blocked, if incomplete.
        "blocking_reasons":
            [
                "Rejection has not yet been confirmed as "
                "accounted for.",
                "Rejection does not yet have an explanation.",
            ],

        # ----------------------------------------------------
        # WORKFLOW BEHAVIOR
        # ----------------------------------------------------
        #
        # The accountant can keep working on other
        # transactions.
        # ----------------------------------------------------

        "blocks_workflow":
            False,

        # But the final journal entry cannot yet be finalized.
        "blocks_finalization":
            True,
    }


# ============================================================
# EVALUATE ONE REJECTION REVIEW
# ============================================================

def evaluate_rejection_review(
    review_item,
):
    """
    Evaluate whether one rejection satisfies the finalization
    control.

    Rules
    -----
    Every rejection must:

        accounted_for == True

    AND

        explanation is nonblank

    Additionally, if:

        is_unknown == True

    then:

        escalated == True

    AND

        escalation_notes is nonblank

    Returns
    -------
    dict
        Evaluation result containing:

        review_complete
        review_status
        blocks_finalization
        blocking_reasons
    """

    blocking_reasons = []


    # --------------------------------------------------------
    # RULE 1:
    # EVERY REJECTION MUST BE ACCOUNTED FOR
    # --------------------------------------------------------

    if review_item.get(
        "accounted_for"
    ) is not True:

        blocking_reasons.append(
            "Rejection has not been confirmed as accounted for."
        )


    # --------------------------------------------------------
    # RULE 2:
    # EVERY REJECTION MUST BE EXPLAINED
    # --------------------------------------------------------

    explanation = str(
        review_item.get(
            "explanation",
            "",
        )
        or ""
    ).strip()


    if not explanation:

        blocking_reasons.append(
            "Rejection does not have an explanation."
        )


    # --------------------------------------------------------
    # RULE 3:
    # UNKNOWN REJECTIONS MUST BE ESCALATED
    # --------------------------------------------------------

    is_unknown = (
        review_item.get(
            "is_unknown"
        )
        is True
    )


    if is_unknown:

        if review_item.get(
            "escalated"
        ) is not True:

            blocking_reasons.append(
                "Unknown rejection has not been escalated."
            )


        # We require some evidence/note showing what escalation
        # occurred. This gives the control an audit trail.
        escalation_notes = str(
            review_item.get(
                "escalation_notes",
                "",
            )
            or ""
        ).strip()


        if not escalation_notes:

            blocking_reasons.append(
                "Unknown rejection does not contain "
                "escalation documentation."
            )


    # --------------------------------------------------------
    # DETERMINE COMPLETION
    # --------------------------------------------------------

    review_complete = (
        len(
            blocking_reasons
        )
        == 0
    )


    review_status = (

        COMPLETE

        if review_complete

        else BLOCKED
    )


    return {
        "review_complete":
            review_complete,

        "review_status":
            review_status,

        "blocks_finalization":
            not review_complete,

        "blocking_reasons":
            blocking_reasons,
    }


# ============================================================
# RECORD HUMAN CONFIRMATION
# ============================================================

def record_rejection_review(
    review_item,
    *,
    accounted_for,
    explanation,
    is_unknown,
    reviewed_by,
    escalated=False,
    escalation_notes="",
):
    """
    Record the accountant's review.

    This function deliberately allows incomplete reviews.

    Example:
        accounted_for=False

    The transaction can still be saved in the shared record,
    but evaluate_rejection_review() will keep finalization
    blocked.

    Parameters
    ----------
    accounted_for:
        Human confirmation:
            Has this rejection been accounted for?

    explanation:
        Human explanation of what happened / how it was handled.

    is_unknown:
        Whether the reviewer considers the rejection unknown.

    reviewed_by:
        Human responsible for the review.

    escalated:
        Required before finalization when is_unknown=True.

    escalation_notes:
        Documentation of escalation when is_unknown=True.

    Returns
    -------
    dict
        Updated rejection-review item.
    """

    reviewer = str(
        reviewed_by
    ).strip()


    if not reviewer:

        raise ValueError(
            "reviewed_by is required."
        )


    updated = deepcopy(
        review_item
    )


    # --------------------------------------------------------
    # RECORD HUMAN INPUT
    # --------------------------------------------------------

    updated[
        "accounted_for"
    ] = bool(
        accounted_for
    )


    updated[
        "explanation"
    ] = str(
        explanation
        or ""
    ).strip()


    updated[
        "is_unknown"
    ] = bool(
        is_unknown
    )


    updated[
        "escalated"
    ] = bool(
        escalated
    )


    updated[
        "escalation_notes"
    ] = str(
        escalation_notes
        or ""
    ).strip()


    updated[
        "reviewed_by"
    ] = reviewer


    updated[
        "reviewed_at"
    ] = utc_now_iso()


    # --------------------------------------------------------
    # EVALUATE THE CONTROL
    # --------------------------------------------------------

    evaluation = evaluate_rejection_review(
        updated
    )


    updated.update(
        evaluation
    )


    # --------------------------------------------------------
    # IMPORTANT:
    #
    # Rejection review never blocks unrelated reconciliation
    # work.
    #
    # Its control effect occurs at FINALIZATION.
    # --------------------------------------------------------

    updated[
        "blocks_workflow"
    ] = False


    return updated


# ============================================================
# WRITE / UPDATE REVIEW IN SHARED EPISODE RECORD
# ============================================================

def write_rejection_review_to_episode(
    episode_record,
    review_item,
):
    """
    Store one rejection-review item in the shared episode
    record.

    If the same transaction already has a rejection review,
    the existing version is replaced.

    The input episode_record is NOT mutated directly.
    """

    episode = deepcopy(
        episode_record
    )


    existing_reviews = list(
        episode.get(
            "rejection_reviews",
            []
        )
    )


    transaction_id = review_item[
        "transaction_id"
    ]


    # --------------------------------------------------------
    # REMOVE OLD VERSION OF THIS TRANSACTION'S REVIEW
    # --------------------------------------------------------

    existing_reviews = [

        existing

        for existing in existing_reviews

        if existing.get(
            "transaction_id"
        )
        != transaction_id
    ]


    # --------------------------------------------------------
    # ADD UPDATED REVIEW
    # --------------------------------------------------------

    existing_reviews.append(
        deepcopy(
            review_item
        )
    )


    episode[
        "rejection_reviews"
    ] = existing_reviews


    return episode


# ============================================================
# SUMMARIZE REJECTION REVIEW FOR DASHBOARD / GRAPH STATE
# ============================================================

def summarize_rejection_reviews(
    review_items,
):
    """
    Produce a concise episode-level summary.
    """

    summary = {
        "total_rejections": 0,
        "complete": 0,
        "incomplete": 0,
        "unknown": 0,
        "unknown_escalated": 0,
        "blocking_finalization": 0,
    }


    for review in review_items:

        summary[
            "total_rejections"
        ] += 1


        evaluation = evaluate_rejection_review(
            review
        )


        if evaluation[
            "review_complete"
        ]:

            summary[
                "complete"
            ] += 1


        else:

            summary[
                "incomplete"
            ] += 1


        if review.get(
            "is_unknown"
        ) is True:

            summary[
                "unknown"
            ] += 1


            if review.get(
                "escalated"
            ) is True:

                summary[
                    "unknown_escalated"
                ] += 1


        if evaluation[
            "blocks_finalization"
        ]:

            summary[
                "blocking_finalization"
            ] += 1


    return summary


# ============================================================
# EPISODE-LEVEL FINALIZATION GATE
# ============================================================

def check_rejection_finalization_gate(
    episode_record,
):
    """
    Determine whether rejection review permits the journal
    entry to be finalized.

    This is the key control.

    Returns
    -------
    dict

        can_finalize

        status

        blocking_transaction_ids

        blocking_items

        summary
    """

    reviews = list(
        episode_record.get(
            "rejection_reviews",
            []
        )
    )


    blocking_items = []


    # --------------------------------------------------------
    # EVALUATE EVERY IDENTIFIED REJECTION
    # --------------------------------------------------------

    for review in reviews:

        evaluation = evaluate_rejection_review(
            review
        )


        if not evaluation[
            "review_complete"
        ]:

            blocking_items.append(

                {
                    "transaction_id":
                        review.get(
                            "transaction_id"
                        ),

                    "blocking_reasons":
                        evaluation[
                            "blocking_reasons"
                        ],
                }
            )


    # --------------------------------------------------------
    # FINALIZATION DECISION
    # --------------------------------------------------------

    can_finalize = (
        len(
            blocking_items
        )
        == 0
    )


    status = (

        "PASS"

        if can_finalize

        else "BLOCKED_REJECTION_REVIEW"
    )


    return {
        "control_name":
            "rejection_finalization_gate",

        "can_finalize":
            can_finalize,

        "status":
            status,

        "blocking_transaction_ids":
            [

                item[
                    "transaction_id"
                ]

                for item
                in blocking_items
            ],

        "blocking_items":
            blocking_items,

        "summary":
            summarize_rejection_reviews(
                reviews
            ),
    }


# ============================================================
# APPLY FINALIZATION CONTROL TO SHARED EPISODE RECORD
# ============================================================

def apply_rejection_finalization_gate(
    episode_record,
):
    """
    Evaluate rejection review and write the result back into
    the shared episode record.

    This is useful immediately before final JE approval.
    """

    episode = deepcopy(
        episode_record
    )


    result = check_rejection_finalization_gate(
        episode
    )


    finalization_controls = deepcopy(

        episode.get(
            "finalization_controls",
            {}
        )
    )


    finalization_controls[
        "rejection_review"
    ] = result


    episode[
        "finalization_controls"
    ] = finalization_controls


    return episode


# ============================================================
# SMALL END-TO-END DEMONSTRATION
# ============================================================

def demo():
    """
    Demonstrate the complete logic using synthetic data.

    This does NOT use Ascot production data.
    """

    print(
        "ASCOT REJECTION REVIEW CONTROL DEMO"
    )


    # ========================================================
    # START ONE RECONCILIATION EPISODE
    # ========================================================

    episode = {
        "episode_id":
            "AIC-CASH-EXAMPLE",

        "status":
            "IN_PROGRESS",

        "rejection_reviews":
            [],
    }


    # ========================================================
    # EXAMPLE 1:
    # KNOWN REJECTION
    # ========================================================

    known_transaction = {
        "transaction_id":
            "WF-EXAMPLE-001",

        "accounting_period":
            "2026-07",

        "date":
            "2026-07-15",

        "amount":
            "1000.00",

        "transaction_description":
            "POSTING ERROR CORRECTION CREDIT",

        "reference":
            "12345",
    }


    known_review = create_rejection_review_item(
        known_transaction
    )


    # Human confirms:
    #
    #   yes, it has been accounted for;
    #   here is the explanation;
    #   it is not unknown.
    known_review = record_rejection_review(

        known_review,

        accounted_for=True,

        explanation=(
            "Known rejected payment; accounting treatment "
            "has been reflected in the reconciliation."
        ),

        is_unknown=False,

        reviewed_by="Example Reviewer",
    )


    episode = write_rejection_review_to_episode(

        episode,

        known_review,
    )


    # ========================================================
    # EXAMPLE 2:
    # UNKNOWN REJECTION - NOT YET ESCALATED
    # ========================================================

    unknown_transaction = {
        "transaction_id":
            "WF-EXAMPLE-002",

        "accounting_period":
            "2026-07",

        "date":
            "2026-07-20",

        "amount":
            "500.00",

        "transaction_description":
            "POSTING ERROR CORRECTION CREDIT",

        "reference":
            "67890",
    }


    unknown_review = create_rejection_review_item(
        unknown_transaction
    )


    # Human does not recognize it.
    #
    # The review can be recorded, but because escalation is
    # missing the JE finalization gate should remain blocked.
    unknown_review = record_rejection_review(

        unknown_review,

        accounted_for=True,

        explanation=(
            "Rejection identified but underlying reason is "
            "currently unknown."
        ),

        is_unknown=True,

        escalated=False,

        escalation_notes="",

        reviewed_by="Example Reviewer",
    )


    episode = write_rejection_review_to_episode(

        episode,

        unknown_review,
    )


    # ========================================================
    # CHECK FINALIZATION
    # ========================================================

    gate_before_escalation = (
        check_rejection_finalization_gate(
            episode
        )
    )


    print(
        "\n========================================"
    )

    print(
        "BEFORE UNKNOWN REJECTION IS ESCALATED"
    )

    print(
        "========================================"
    )


    print(
        "Can finalize JE:",
        gate_before_escalation[
            "can_finalize"
        ],
    )


    print(
        "Status:",
        gate_before_escalation[
            "status"
        ],
    )


    print(
        "Blocking transactions:",
        gate_before_escalation[
            "blocking_transaction_ids"
        ],
    )


    # ========================================================
    # HUMAN NOW ESCALATES THE UNKNOWN REJECTION
    # ========================================================

    unknown_review = record_rejection_review(

        unknown_review,

        accounted_for=True,

        explanation=(
            "Rejection identified; reason remains unknown "
            "and has been escalated for follow-up."
        ),

        is_unknown=True,

        escalated=True,

        escalation_notes=(
            "Escalated to Cash Team for investigation and "
            "supporting backup."
        ),

        reviewed_by="Example Reviewer",
    )


    episode = write_rejection_review_to_episode(

        episode,

        unknown_review,
    )


    # ========================================================
    # CHECK FINALIZATION AGAIN
    # ========================================================

    gate_after_escalation = (
        check_rejection_finalization_gate(
            episode
        )
    )


    print(
        "\n========================================"
    )

    print(
        "AFTER UNKNOWN REJECTION IS ESCALATED"
    )

    print(
        "========================================"
    )


    print(
        "Can finalize JE:",
        gate_after_escalation[
            "can_finalize"
        ],
    )


    print(
        "Status:",
        gate_after_escalation[
            "status"
        ],
    )


    print(
        "Summary:",
        gate_after_escalation[
            "summary"
        ],
    )


    # ========================================================
    # WRITE FINALIZATION CONTROL INTO EPISODE RECORD
    # ========================================================

    episode = apply_rejection_finalization_gate(
        episode
    )


    print(
        "\n========================================"
    )

    print(
        "FINAL EPISODE CONTROL STATE"
    )

    print(
        "========================================"
    )


    print(

        episode[
            "finalization_controls"
        ][
            "rejection_review"
        ]
    )


# ============================================================
# RUN DEMO
# ============================================================

if __name__ == "__main__":

    demo()