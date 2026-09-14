# ============================================================
# ASCOT AIC CASH EXPENSE AUTOMATION
# VERSION 0: END-TO-END LANGGRAPH SKELETON
# ============================================================
#
# PURPOSE
# ------------------------------------------------------------
#
# This file represents the WHOLE AIC Cash Expense
# reconciliation episode rather than one isolated
# transaction-classification task.
#
# The purpose of this version is NOT yet to reproduce every
# accounting rule.
#
# Instead, we want to establish the architecture:
#
#   Inputs
#      ↓
#   Normalize data
#      ↓
#   Bank / reconciliation controls
#      ↓
#   Transaction-level resolution
#      ↓
#   Exception queue
#      ↓
#   Human judgment where needed
#      ↓
#   Proposed journal entry
#      ↓
#   Final controls
#      ↓
#   Responsible-person approval
#
# IMPORTANT DESIGN PRINCIPLES
# ------------------------------------------------------------
#
# 1. The complete reconciliation episode is the main
#    accountability unit.
#
# 2. Individual decision instances inside the episode may be
#    automated or sent to a human.
#
# 3. Routine work should continue when possible even when
#    some transactions become exceptions.
#
# 4. Some exceptions are NONBLOCKING.
#    Example: rejected payments can be excluded from the JE
#    while the rest of the process continues.
#
# 5. Some exceptions are BLOCKING at the JE stage.
#    Example: an unresolved Concur T-code prevents completion
#    of the final JE ("all or none").
#
# 6. We maintain ONE shared episode record.
#    We do NOT record every click or machine action.
#
# 7. The human responsible for the episode remains
#    accountable for the final disposition.
#
# 8. This version uses SYNTHETIC DATA ONLY.
#
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

# deepcopy lets each LangGraph node safely copy the shared
# episode record before modifying it.
from copy import deepcopy


# TypedDict lets us describe the structure of LangGraph state.
from typing_extensions import TypedDict


# Core LangGraph workflow components.
#
# StateGraph = builds the workflow.
# START = beginning of workflow.
# END = end of workflow.
from langgraph.graph import StateGraph, START, END


# InMemorySaver lets LangGraph remember the state when the
# workflow pauses for human input.
#
# Later we will replace this with persistent storage.
from langgraph.checkpoint.memory import InMemorySaver


# interrupt() pauses execution for human judgment.
#
# Command(resume=...) resumes the same episode afterwards.
from langgraph.types import interrupt, Command


# ============================================================
# 1. DEFINE THE LANGGRAPH STATE
# ============================================================

# The state contains ONE primary object:
#
# episode_record
#
# Every stage of the workflow reads and updates this same
# shared reconciliation record.
class AICReconciliationState(TypedDict):

    episode_record: dict


# ============================================================
# 2. HELPER: COPY THE SHARED RECORD
# ============================================================

# We use this repeatedly inside nodes.
#
# It prevents a node from accidentally modifying the original
# state object directly.
def get_record_copy(state):

    return deepcopy(
        state["episode_record"]
    )


# ============================================================
# 3. NODE: INITIALIZE THE RECONCILIATION EPISODE
# ============================================================

def initialize_episode(state):

    record = get_record_copy(state)

    print("\n========================================")
    print("AIC CASH EXPENSE RECONCILIATION")
    print("========================================")

    print(
        f"Episode ID: "
        f"{record['episode_id']}"
    )

    print(
        f"Period: "
        f"{record['period']}"
    )

    print(
        f"Responsible person: "
        f"{record['responsible_person']}"
    )


    # The episode has now started.
    record["status"] = "in_progress"


    return {
        "episode_record": record
    }


# ============================================================
# 4. NODE: VALIDATE REQUIRED INPUTS
# ============================================================

def validate_inputs(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("1. INPUT VALIDATION")
    print("========================================")


    # These are the main current data sources identified
    # for the AIC automation.
    #
    # Notice what is NOT included:
    #
    # - State-payment email inbox
    # - State Payment Journal Template
    #
    # Ascot said those are no longer the current procedure.
    required_inputs = [

        "wf",

        "ims",

        "composite",

        "concur_paid_invoices",

        "gl_master",

        "cost_master",

        "loss_fund_mapping",
    ]


    # Find any required source that is unavailable.
    missing_inputs = [

        name

        for name in required_inputs

        if not record["inputs"][name]["available"]
    ]


    # Store one concise result in the shared record.
    record["input_validation"] = {

        "passed":
            len(missing_inputs) == 0,

        "missing_inputs":
            missing_inputs,
    }


    if missing_inputs:

        print(
            "Missing required inputs:"
        )

        for item in missing_inputs:

            print(
                f"  - {item}"
            )


        record["status"] = (
            "blocked_missing_inputs"
        )


    else:

        print(
            "All required inputs are available."
        )

        record["status"] = (
            "inputs_validated"
        )


    return {
        "episode_record": record
    }


# ============================================================
# 5. ROUTE AFTER INPUT VALIDATION
# ============================================================

def route_after_input_validation(state):

    record = state[
        "episode_record"
    ]


    if record[
        "input_validation"
    ][
        "passed"
    ]:

        return "normalize_inputs"


    return "stop_missing_inputs"


# ============================================================
# 6. NODE: STOP IF REQUIRED INPUTS ARE MISSING
# ============================================================

def stop_missing_inputs(state):

    record = get_record_copy(state)


    print("\nEpisode cannot begin because required data are missing.")


    record["status"] = (
        "blocked_missing_inputs"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 7. NODE: NORMALIZE INPUT DATA
# ============================================================

def normalize_inputs(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("2. DATA NORMALIZATION")
    print("========================================")


    # --------------------------------------------------------
    # THIS WILL BECOME A MAJOR REAL IMPLEMENTATION MODULE.
    # --------------------------------------------------------
    #
    # Ascot's Excel files were built for human work,
    # not for direct automation.
    #
    # Eventually this node will:
    #
    # - identify the relevant sheets,
    # - locate headers,
    # - standardize column names,
    # - normalize dates,
    # - normalize amounts,
    # - preserve identifiers,
    # - handle blank / merged / formatting rows,
    # - convert Excel conventions into explicit fields,
    # - preserve source provenance.
    #
    # Example:
    #
    # human Excel convention:
    #
    #     yellow row
    #
    # becomes:
    #
    #     issued_current_month = True
    #     cleared = True
    #
    # rather than making our later accounting logic depend
    # directly on Excel colors.
    # --------------------------------------------------------


    # For Version 0, we simply mark the synthetic inputs
    # as normalized.
    record["normalization"] = {

        "completed":
            True,

        "note":
            (
                "Synthetic data normalized. "
                "Real Excel sanitization not yet implemented."
            ),
    }


    print(
        "Synthetic input data normalized."
    )


    record["status"] = (
        "inputs_normalized"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 8. NODE: WF VS COMPOSITE RECONCILIATION
# ============================================================

def reconcile_wf_to_composite(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("3. WF VS COMPOSITE CONTROL")
    print("========================================")


    # In the real implementation:
    #
    # 1. Read AIC WF activity.
    # 2. Read the relevant bank account from Composite.
    # 3. Remove sweep / ZBA / investment sweep items
    #    according to validated rules.
    # 4. Compare totals.
    #
    # Here we use synthetic aggregate values.
    wf_total = record[
        "demo_metrics"
    ][
        "wf_total"
    ]


    composite_adjusted_total = record[
        "demo_metrics"
    ][
        "composite_after_sweeps"
    ]


    variance = (
        wf_total
        - composite_adjusted_total
    )


    passed = (
        abs(variance) < 0.01
    )


    record[
        "reconciliation_controls"
    ][
        "wf_vs_composite"
    ] = {

        "wf_total":
            wf_total,

        "composite_after_sweeps":
            composite_adjusted_total,

        "variance":
            variance,

        "passed":
            passed,
    }


    print(
        f"WF total: "
        f"${wf_total:,.2f}"
    )

    print(
        f"Composite adjusted total: "
        f"${composite_adjusted_total:,.2f}"
    )

    print(
        f"Variance: "
        f"${variance:,.2f}"
    )


    # A bank-total mismatch is a material episode-level
    # control exception.
    if not passed:

        record[
            "exception_queue"
        ].append(

            {
                "exception_id":
                    "CONTROL-WF-COMPOSITE",

                "transaction_id":
                    None,

                "exception_type":
                    "bank_total_variance",

                "description":
                    (
                        "WF total does not reconcile "
                        "to adjusted Composite total."
                    ),

                "blocks_je":
                    True,

                "status":
                    "open",
            }
        )


    return {
        "episode_record": record
    }


# ============================================================
# 9. NODE: WF VS IMS RECONCILIATION
# ============================================================

def reconcile_wf_to_ims(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("4. WF VS IMS RECONCILIATION")
    print("========================================")


    # Important Ascot clarification:
    #
    # The WF tab is already made up of CLEARED items.
    #
    # Yellow does NOT mean "the only cleared items."
    #
    # Yellow means issued in the current month AND cleared.
    #
    # Therefore, our automation should not use yellow
    # highlighting as the primary cleared-item filter.
    # --------------------------------------------------------


    transactions = record[
        "transactions"
    ]


    # Count how many transactions currently have
    # an IMS match.
    matched = sum(

        1

        for tx in transactions

        if tx.get("ims_match")
    )


    unmatched = (
        len(transactions)
        - matched
    )


    record[
        "reconciliation_controls"
    ][
        "wf_vs_ims"
    ] = {

        "wf_transaction_count":
            len(transactions),

        "ims_matched_count":
            matched,

        "not_matched_to_ims":
            unmatched,
    }


    print(
        f"Transactions: {len(transactions)}"
    )

    print(
        f"IMS matched: {matched}"
    )

    print(
        f"Not matched to IMS: {unmatched}"
    )


    # IMPORTANT:
    #
    # An unmatched item does NOT automatically mean failure.
    #
    # It may be:
    #
    # - State payment now supported through Concur,
    # - Concur expense,
    # - Bank analysis fee,
    # - ACH,
    # - Rejection,
    # - One-off / Uncategorized item.
    #
    # Therefore unmatched items move into transaction
    # resolution instead of immediately stopping the graph.


    return {
        "episode_record": record
    }


# ============================================================
# 10. NODE: RESOLVE TRANSACTIONS
# ============================================================

def resolve_transactions(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("5. TRANSACTION RESOLUTION")
    print("========================================")


    resolved_transactions = []


    # Work through each transaction.
    #
    # In the real system, many of these decision instances
    # could later be handled independently / in parallel.
    for transaction in record[
        "transactions"
    ]:

        tx = deepcopy(
            transaction
        )


        # Default values.
        tx["include_in_je"] = True

        tx["accounting_ready"] = False

        tx["resolution_status"] = (
            "unresolved"
        )

        tx["category"] = (
            tx.get("category")
            or ""
        )


        # ====================================================
        # CASE A: REJECTED / RETURNED PAYMENT
        # ====================================================

        # Ascot told us rejection descriptions are NOT
        # consistent.
        #
        # They may say:
        #
        # Returned
        # NSF
        #
        # or simply look like an incoming transaction.
        #
        # Therefore real rejection identification cannot be
        # implemented using one keyword list alone.
        #
        # In this synthetic example, an upstream detector
        # has already marked is_rejection=True.
        if tx.get("is_rejection"):

            tx["category"] = (
                "rejection"
            )

            tx["include_in_je"] = False

            tx["accounting_ready"] = True

            tx["resolution_status"] = (
                "formally_dispositioned"
            )


            # Ascot explicitly said:
            #
            # continue the rest of the JE,
            # alert the stakeholder,
            # exclude rejection from JE.
            record[
                "exception_queue"
            ].append(

                {
                    "exception_id":
                        f"REJ-{tx['transaction_id']}",

                    "transaction_id":
                        tx["transaction_id"],

                    "exception_type":
                        "rejected_payment",

                    "description":
                        (
                            "Rejected payment excluded "
                            "from proposed JE and Cash "
                            "Team should be notified."
                        ),

                    "blocks_je":
                        False,

                    "status":
                        "formally_dispositioned",
                }
            )


            resolved_transactions.append(
                tx
            )

            continue


        # ====================================================
        # CASE B: NORMAL IMS-SUPPORTED TRANSACTION
        # ====================================================

        if tx.get("ims_match"):

            tx["category"] = (
                "ims_supported"
            )


            # If the GL and cost code are clear,
            # the transaction is accounting-ready.
            if tx.get(
                "gl_cost_assignment_clear"
            ):

                tx["accounting_ready"] = True

                tx["resolution_status"] = (
                    "resolved_by_machine"
                )


            # Ascot preference:
            #
            # If GL/cost assignment is uncertain,
            # FLAG AND KEEP GOING.
            #
            # Therefore we add an exception but do not stop
            # processing the remaining transactions.
            else:

                record[
                    "exception_queue"
                ].append(

                    {
                        "exception_id":
                            f"GLCOST-{tx['transaction_id']}",

                        "transaction_id":
                            tx["transaction_id"],

                        "exception_type":
                            "uncertain_gl_or_cost_code",

                        "description":
                            (
                                "GL/cost assignment "
                                "requires human review."
                            ),

                        # Processing continues now,
                        # but this must eventually be resolved
                        # before that transaction can enter
                        # the final JE.
                        "blocks_je":
                            True,

                        "status":
                            "open",
                    }
                )


            resolved_transactions.append(
                tx
            )

            continue


        # ====================================================
        # CASE C: STATE PAYMENT
        # ====================================================

        # IMPORTANT:
        #
        # We no longer search the Financial Reporting inbox
        # or use the old State Payment Journal Template.
        #
        # Ascot told us current state-payment information is
        # available through Concur reporting.
        if tx.get(
            "state_payment_in_concur"
        ):

            tx["category"] = (
                "state_payment"
            )

            tx["accounting_ready"] = (
                tx.get(
                    "gl_cost_assignment_clear",
                    False,
                )
            )


            if tx["accounting_ready"]:

                tx[
                    "resolution_status"
                ] = (
                    "resolved_from_concur"
                )


            else:

                record[
                    "exception_queue"
                ].append(

                    {
                        "exception_id":
                            f"STATE-{tx['transaction_id']}",

                        "transaction_id":
                            tx["transaction_id"],

                        "exception_type":
                            "state_payment_accounting_unclear",

                        "description":
                            (
                                "State payment found in "
                                "Concur but accounting "
                                "treatment remains unclear."
                            ),

                        "blocks_je":
                            True,

                        "status":
                            "open",
                    }
                )


            resolved_transactions.append(
                tx
            )

            continue


        # ====================================================
        # CASE D: CONCUR / PAID INVOICES FOR SUN
        # ====================================================

        if tx.get(
            "concur_item"
        ):

            tx["category"] = (
                "concur"
            )


            # T-code mappings should NOT be treated as a
            # permanent vendor -> T-code rule.
            #
            # Ascot said these change too frequently.
            #
            # The current Loss Fund Mapping can be consulted,
            # but ambiguity must become an exception.
            if tx.get(
                "tcode_clear"
            ):

                tx["accounting_ready"] = True

                tx["resolution_status"] = (
                    "resolved_from_current_tcode_reference"
                )


            else:

                # IMPORTANT:
                #
                # Ascot said unclear Concur T-code is
                # "all or none."
                #
                # Therefore the workflow may continue
                # processing other transactions,
                # but the FINAL JE cannot be completed
                # until this is resolved.
                record[
                    "exception_queue"
                ].append(

                    {
                        "exception_id":
                            f"TCODE-{tx['transaction_id']}",

                        "transaction_id":
                            tx["transaction_id"],

                        "exception_type":
                            "unclear_concur_tcode",

                        "description":
                            (
                                "Concur T-code unresolved. "
                                "Final JE is blocked until "
                                "this item is resolved."
                            ),

                        "blocks_je":
                            True,

                        "status":
                            "open",
                    }
                )


            resolved_transactions.append(
                tx
            )

            continue


        # ====================================================
        # CASE E: BANK ANALYSIS FEE
        # ====================================================

        if tx.get(
            "bank_analysis_fee"
        ):

            tx["category"] = (
                "bank_analysis_fee"
            )

            tx["accounting_ready"] = True

            tx["resolution_status"] = (
                "resolved_bank_fee"
            )


            # Ascot told us:
            #
            # - not every bank account has a fee,
            # - fees are added to the bottom of WF,
            # - and included at the TOP of the JE.
            #
            # We preserve the category now.
            # JE ordering is handled later.
            resolved_transactions.append(
                tx
            )

            continue


        # ====================================================
        # CASE F: ACH
        # ====================================================

        # Ascot identified the description:
        #
        # "Miscellaneous ACH Debit"
        #
        # but explicitly asked for further clarification
        # about what treatment we wanted to automate.
        if (
            "miscellaneous ach debit"
            in tx[
                "description"
            ].lower()
        ):

            tx["category"] = "ach"


            record[
                "exception_queue"
            ].append(

                {
                    "exception_id":
                        f"ACH-{tx['transaction_id']}",

                    "transaction_id":
                        tx["transaction_id"],

                    "exception_type":
                        "ach_treatment_not_yet_defined",

                    "description":
                        (
                            "ACH identified from description, "
                            "but downstream accounting rule "
                            "has not yet been confirmed."
                        ),

                    "blocks_je":
                        True,

                    "status":
                        "open",
                }
            )


            resolved_transactions.append(
                tx
            )

            continue


        # ====================================================
        # CASE G: EVERYTHING ELSE
        # ====================================================

        # Ascot explicitly said one-off / unique items may not
        # belong to any stable category.
        #
        # Therefore we do NOT force every transaction into a
        # predetermined taxonomy.
        tx["category"] = (
            "Uncategorized"
        )


        record[
            "exception_queue"
        ].append(

            {
                "exception_id":
                    f"UNCAT-{tx['transaction_id']}",

                "transaction_id":
                    tx["transaction_id"],

                "exception_type":
                    "uncategorized_transaction",

                "description":
                    (
                        "One-off or unique transaction "
                        "requires human judgment."
                    ),

                "blocks_je":
                    True,

                "status":
                    "open",
            }
        )


        resolved_transactions.append(
            tx
        )


    # Replace the original transaction population
    # with the enriched / resolved population.
    record[
        "transactions"
    ] = resolved_transactions


    record["status"] = (
        "transaction_resolution_completed"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 11. NODE: PREPARE THE EXCEPTION QUEUE
# ============================================================

def prepare_exception_queue(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("6. EXCEPTION QUEUE")
    print("========================================")


    # Open blocking exceptions must eventually be resolved
    # before the final JE can be completed.
    blocking_exceptions = [

        exception

        for exception
        in record["exception_queue"]

        if (
            exception["blocks_je"]
            and exception["status"] == "open"
        )
    ]


    # These exceptions are formally dispositioned and do not
    # stop the JE.
    #
    # Rejections are the main current example.
    nonblocking_exceptions = [

        exception

        for exception
        in record["exception_queue"]

        if not exception["blocks_je"]
    ]


    record[
        "exception_summary"
    ] = {

        "blocking_count":
            len(
                blocking_exceptions
            ),

        "nonblocking_count":
            len(
                nonblocking_exceptions
            ),

        "blocking_exception_ids":
            [
                item["exception_id"]

                for item
                in blocking_exceptions
            ],
    }


    print(
        f"Blocking exceptions: "
        f"{len(blocking_exceptions)}"
    )

    print(
        f"Nonblocking / formally dispositioned: "
        f"{len(nonblocking_exceptions)}"
    )


    record["status"] = (
        "exception_queue_prepared"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 12. ROUTE BEFORE JOURNAL-ENTRY CONSTRUCTION
# ============================================================

def route_before_je(state):

    record = state[
        "episode_record"
    ]


    blocking_open = [

        exception

        for exception
        in record["exception_queue"]

        if (
            exception["blocks_je"]
            and exception["status"] == "open"
        )
    ]


    # Human judgment is needed if blocking exceptions exist.
    if blocking_open:

        return "human_exception_review"


    # Otherwise we can build the proposed JE.
    return "build_proposed_je"


# ============================================================
# 13. NODE: HUMAN EXCEPTION REVIEW
# ============================================================

def human_exception_review(state):

    record = get_record_copy(state)


    blocking_exceptions = [

        exception

        for exception
        in record["exception_queue"]

        if (
            exception["blocks_je"]
            and exception["status"] == "open"
        )
    ]


    # --------------------------------------------------------
    # PAUSE LANGGRAPH.
    # --------------------------------------------------------
    #
    # Later this interrupt will be serviced by our
    # browser-based exception-review interface.
    #
    # For now, the terminal acts as the human interface.
    review_response = interrupt(
        {
            "review_type":
                "aic_exception_queue",

            "episode_id":
                record["episode_id"],

            "responsible_person":
                record[
                    "responsible_person"
                ],

            "blocking_exceptions":
                blocking_exceptions,
        }
    )


    # --------------------------------------------------------
    # RESUME AFTER HUMAN INPUT.
    # --------------------------------------------------------

    decisions = review_response[
        "decisions"
    ]


    # Convert decisions into an easy lookup:
    #
    # transaction_id -> decision
    decision_map = {

        decision[
            "transaction_id"
        ]:
            decision

        for decision
        in decisions
    }


    # Update exceptions.
    for exception in record[
        "exception_queue"
    ]:

        transaction_id = (
            exception.get(
                "transaction_id"
            )
        )


        # Ignore exceptions that were not part of
        # this human review.
        if (
            transaction_id
            not in decision_map
        ):

            continue


        decision = decision_map[
            transaction_id
        ]


        # Human resolved the exception.
        if decision[
            "decision"
        ] == "resolve":

            exception[
                "status"
            ] = "resolved"


        # Human cannot resolve it now.
        #
        # The episode remains blocked for later follow-up.
        elif decision[
            "decision"
        ] == "escalate":

            exception[
                "status"
            ] = "escalated_open"


    # Update the corresponding transactions.
    for tx in record[
        "transactions"
    ]:

        transaction_id = tx[
            "transaction_id"
        ]


        if (
            transaction_id
            not in decision_map
        ):

            continue


        decision = decision_map[
            transaction_id
        ]


        if decision[
            "decision"
        ] == "resolve":

            # This is intentionally generic in Version 0.
            #
            # Later the browser UI will capture the actual
            # relevant fields:
            #
            # GL code
            # cost code
            # T-code
            # classification
            # supporting evidence
            # etc.
            tx[
                "human_resolution"
            ] = decision.get(
                "resolution",
                "",
            )

            tx[
                "accounting_ready"
            ] = True

            tx[
                "resolution_status"
            ] = (
                "resolved_by_human"
            )


    # Store a concise episode-level summary rather than
    # a click-by-click human activity log.
    record[
        "human_exception_review"
    ] = {

        "reviewed":
            True,

        "responsible_person":
            record[
                "responsible_person"
            ],

        "decisions":
            decisions,
    }


    record["status"] = (
        "human_exception_review_completed"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 14. ROUTE AFTER HUMAN REVIEW
# ============================================================

def route_after_human_review(state):

    record = state[
        "episode_record"
    ]


    # If a blocking exception remains unresolved,
    # we cannot create a final JE yet.
    unresolved = [

        exception

        for exception
        in record["exception_queue"]

        if (
            exception["blocks_je"]
            and exception["status"]
            in {
                "open",
                "escalated_open",
            }
        )
    ]


    if unresolved:

        return "stop_unresolved"


    return "build_proposed_je"


# ============================================================
# 15. NODE: STOP WITH UNRESOLVED EXCEPTIONS
# ============================================================

def stop_unresolved(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("EPISODE PAUSED")
    print("========================================")


    print(
        "One or more blocking exceptions remain unresolved."
    )


    # In the future browser-based version,
    # these cases remain in the exception queue and the
    # workflow can resume later when the responsible person
    # provides the needed information.
    record["status"] = (
        "awaiting_exception_resolution"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 16. NODE: BUILD PROPOSED JOURNAL ENTRY
# ============================================================

def build_proposed_je(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("7. BUILD PROPOSED JOURNAL ENTRY")
    print("========================================")


    # IMPORTANT:
    #
    # This does NOT yet implement Ascot's actual debit/credit,
    # account, cost-code, T-code, and line-construction rules.
    #
    # It establishes the JE assembly boundary.
    #
    # We will implement real JE logic only after examining
    # the Excel data and the enacted JE construction.
    # --------------------------------------------------------


    eligible_transactions = [

        tx

        for tx
        in record["transactions"]

        if (
            tx["include_in_je"]
            and tx["accounting_ready"]
        )
    ]


    # Bank analysis fees should appear at the top of the JE.
    #
    # Therefore we sort them first.
    eligible_transactions.sort(

        key=lambda tx:
            0
            if tx[
                "category"
            ] == "bank_analysis_fee"
            else 1
    )


    # Create placeholder JE rows.
    proposed_lines = []


    for tx in eligible_transactions:

        proposed_lines.append(

            {
                "source_transaction_id":
                    tx[
                        "transaction_id"
                    ],

                "category":
                    tx[
                        "category"
                    ],

                "amount":
                    tx[
                        "amount"
                    ],

                # These are placeholders until we build the
                # real accounting transformation.
                "gl_code":
                    tx.get(
                        "gl_code"
                    ),

                "cost_code":
                    tx.get(
                        "cost_code"
                    ),

                "t_code":
                    tx.get(
                        "t_code"
                    ),

                "human_resolution":
                    tx.get(
                        "human_resolution",
                        "",
                    ),
            }
        )


    record[
        "journal_entry"
    ][
        "proposed_lines"
    ] = proposed_lines


    record[
        "journal_entry"
    ][
        "status"
    ] = "proposed"


    print(
        f"Proposed JE lines: "
        f"{len(proposed_lines)}"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 17. NODE: FINAL CONTROL CHECKS
# ============================================================

def run_final_controls(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("8. FINAL CONTROLS")
    print("========================================")


    # --------------------------------------------------------
    # CONTROL 1:
    # WF vs Composite must reconcile.
    # --------------------------------------------------------

    bank_control_passed = record[
        "reconciliation_controls"
    ][
        "wf_vs_composite"
    ][
        "passed"
    ]


    # --------------------------------------------------------
    # CONTROL 2:
    # No blocking accounting exceptions may remain open.
    # --------------------------------------------------------

    unresolved_blocking = [

        exception

        for exception
        in record["exception_queue"]

        if (
            exception["blocks_je"]
            and exception["status"]
            not in {
                "resolved",
                "formally_dispositioned",
            }
        )
    ]


    exceptions_cleared = (
        len(
            unresolved_blocking
        ) == 0
    )


    # --------------------------------------------------------
    # IMPORTANT DESIGN CORRECTION:
    #
    # We DO NOT create a rule saying:
    #
    # "GL accounts beginning with 3 are wrong."
    #
    # Ascot explicitly told us valid GL accounts may begin
    # with 3.
    # --------------------------------------------------------


    record[
        "journal_entry"
    ][
        "control_results"
    ] = {

        "wf_vs_composite_passed":
            bank_control_passed,

        "blocking_exceptions_cleared":
            exceptions_cleared,


        # Still waiting for Ascot's exact permitted
        # intercompany entity/code list.
        "intercompany_control":
            "pending_rule_from_ascot",


        # Prior-month voids do NOT live in WF.
        # Their proper automation treatment still needs
        # separate clarification.
        "prior_month_void_control":
            "pending_process_clarification",
    }


    # For the current skeleton we determine readiness
    # only from controls whose rules are actually known.
    known_controls_passed = (

        bank_control_passed
        and exceptions_cleared
    )


    record[
        "journal_entry"
    ][
        "known_controls_passed"
    ] = known_controls_passed


    if known_controls_passed:

        print(
            "Known implemented controls passed."
        )


    else:

        print(
            "One or more implemented controls failed."
        )


    return {
        "episode_record": record
    }


# ============================================================
# 18. ROUTE AFTER FINAL CONTROLS
# ============================================================

def route_after_final_controls(state):

    record = state[
        "episode_record"
    ]


    if record[
        "journal_entry"
    ][
        "known_controls_passed"
    ]:

        return "final_approval"


    return "stop_control_failure"


# ============================================================
# 19. NODE: STOP IF FINAL CONTROLS FAIL
# ============================================================

def stop_control_failure(state):

    record = get_record_copy(state)


    record["status"] = (
        "blocked_final_control_failure"
    )


    print(
        "\nEpisode stopped because a final "
        "implemented control failed."
    )


    return {
        "episode_record": record
    }


# ============================================================
# 20. NODE: RESPONSIBLE-PERSON FINAL APPROVAL
# ============================================================

def final_approval(state):

    record = get_record_copy(state)


    # One responsible person remains accountable for
    # the complete episode even though machine components
    # performed substantial work.
    approval_response = interrupt(
        {
            "review_type":
                "final_aic_episode_approval",

            "episode_id":
                record["episode_id"],

            "responsible_person":
                record[
                    "responsible_person"
                ],

            "exception_summary":
                record[
                    "exception_summary"
                ],

            "journal_entry_summary":
                {
                    "proposed_line_count":
                        len(
                            record[
                                "journal_entry"
                            ][
                                "proposed_lines"
                            ]
                        ),

                    "control_results":
                        record[
                            "journal_entry"
                        ][
                            "control_results"
                        ],
                },
        }
    )


    decision = approval_response[
        "decision"
    ]


    note = approval_response.get(
        "note",
        "",
    )


    if decision == "approve":

        record[
            "final_approval"
        ] = {

            "responsible_person":
                record[
                    "responsible_person"
                ],

            "decision":
                "approved",

            "note":
                note,
        }


        record["status"] = (
            "je_ready_for_output"
        )


    elif decision == "escalate":

        record[
            "final_approval"
        ] = {

            "responsible_person":
                record[
                    "responsible_person"
                ],

            "decision":
                "not_approved_escalated",

            "note":
                note,
        }


        record["status"] = (
            "escalated_after_final_review"
        )


    else:

        raise ValueError(
            f"Unexpected final approval decision: "
            f"{decision}"
        )


    return {
        "episode_record": record
    }


# ============================================================
# 21. NODE: FINALIZE EPISODE
# ============================================================

def finalize_episode(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("AIC EPISODE FINAL STATUS")
    print("========================================")


    print(
        f"Status: "
        f"{record['status']}"
    )


    print(
        f"Open / recorded exceptions: "
        f"{len(record['exception_queue'])}"
    )


    print(
        f"Proposed JE lines: "
        f"{len(record['journal_entry']['proposed_lines'])}"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 22. CREATE THE CHECKPOINTER
# ============================================================

checkpointer = InMemorySaver()


# ============================================================
# 23. BUILD THE LANGGRAPH
# ============================================================

builder = StateGraph(
    AICReconciliationState
)


# Register all workflow nodes.
builder.add_node(
    "initialize_episode",
    initialize_episode,
)

builder.add_node(
    "validate_inputs",
    validate_inputs,
)

builder.add_node(
    "stop_missing_inputs",
    stop_missing_inputs,
)

builder.add_node(
    "normalize_inputs",
    normalize_inputs,
)

builder.add_node(
    "reconcile_wf_to_composite",
    reconcile_wf_to_composite,
)

builder.add_node(
    "reconcile_wf_to_ims",
    reconcile_wf_to_ims,
)

builder.add_node(
    "resolve_transactions",
    resolve_transactions,
)

builder.add_node(
    "prepare_exception_queue",
    prepare_exception_queue,
)

builder.add_node(
    "human_exception_review",
    human_exception_review,
)

builder.add_node(
    "stop_unresolved",
    stop_unresolved,
)

builder.add_node(
    "build_proposed_je",
    build_proposed_je,
)

builder.add_node(
    "run_final_controls",
    run_final_controls,
)

builder.add_node(
    "stop_control_failure",
    stop_control_failure,
)

builder.add_node(
    "final_approval",
    final_approval,
)

builder.add_node(
    "finalize_episode",
    finalize_episode,
)


# ============================================================
# 24. CONNECT THE FULL AIC WORKFLOW
# ============================================================

builder.add_edge(
    START,
    "initialize_episode",
)


builder.add_edge(
    "initialize_episode",
    "validate_inputs",
)


builder.add_conditional_edges(

    "validate_inputs",

    route_after_input_validation,

    {
        "normalize_inputs":
            "normalize_inputs",

        "stop_missing_inputs":
            "stop_missing_inputs",
    },
)


builder.add_edge(
    "stop_missing_inputs",
    END,
)


builder.add_edge(
    "normalize_inputs",
    "reconcile_wf_to_composite",
)


builder.add_edge(
    "reconcile_wf_to_composite",
    "reconcile_wf_to_ims",
)


builder.add_edge(
    "reconcile_wf_to_ims",
    "resolve_transactions",
)


builder.add_edge(
    "resolve_transactions",
    "prepare_exception_queue",
)


builder.add_conditional_edges(

    "prepare_exception_queue",

    route_before_je,

    {
        "human_exception_review":
            "human_exception_review",

        "build_proposed_je":
            "build_proposed_je",
    },
)


builder.add_conditional_edges(

    "human_exception_review",

    route_after_human_review,

    {
        "stop_unresolved":
            "stop_unresolved",

        "build_proposed_je":
            "build_proposed_je",
    },
)


builder.add_edge(
    "stop_unresolved",
    END,
)


builder.add_edge(
    "build_proposed_je",
    "run_final_controls",
)


builder.add_conditional_edges(

    "run_final_controls",

    route_after_final_controls,

    {
        "final_approval":
            "final_approval",

        "stop_control_failure":
            "stop_control_failure",
    },
)


builder.add_edge(
    "stop_control_failure",
    END,
)


builder.add_edge(
    "final_approval",
    "finalize_episode",
)


builder.add_edge(
    "finalize_episode",
    END,
)


# ============================================================
# 25. COMPILE THE GRAPH
# ============================================================

graph = builder.compile(
    checkpointer=checkpointer
)


# ============================================================
# 26. CREATE A SYNTHETIC AIC EPISODE
# ============================================================

# Ask who owns this reconciliation episode.
while True:

    responsible_person = input(
        "Responsible person for this AIC episode: "
    ).strip()


    if responsible_person:

        break


    print(
        "A responsible person is required."
    )


# This synthetic record intentionally contains several
# different transaction situations so we can test
# the architecture.
episode_record = {

    "episode_id":
        "AIC-2026-07-DEMO",

    "period":
        "2026-07",

    "responsible_person":
        responsible_person,

    "status":
        "new",


    # --------------------------------------------------------
    # INPUT SOURCES
    # --------------------------------------------------------

    "inputs": {

        "wf": {
            "available": True
        },

        "ims": {
            "available": True
        },

        "composite": {
            "available": True
        },

        "concur_paid_invoices": {
            "available": True
        },

        "gl_master": {
            "available": True
        },

        "cost_master": {
            "available": True
        },

        "loss_fund_mapping": {
            "available": True
        },
    },


    # --------------------------------------------------------
    # SYNTHETIC CONTROL DATA
    # --------------------------------------------------------

    "demo_metrics": {

        "wf_total":
            100000.00,

        # Assume sweeps/ZBA items have already been removed
        # for this Version-0 synthetic example.
        "composite_after_sweeps":
            100000.00,
    },


    # --------------------------------------------------------
    # SHARED TRANSACTION POPULATION
    # --------------------------------------------------------

    "transactions": [

        # Normal IMS-supported transaction.
        {
            "transaction_id":
                "TX001",

            "description":
                "Vendor payment",

            "amount":
                1000.00,

            "ims_match":
                True,

            "gl_cost_assignment_clear":
                True,

            "gl_code":
                "610000",

            "cost_code":
                "C100",
        },


        # State payment now supported through Concur.
        {
            "transaction_id":
                "TX002",

            "description":
                "State regulatory payment",

            "amount":
                500.00,

            "ims_match":
                False,

            "state_payment_in_concur":
                True,

            "gl_cost_assignment_clear":
                True,

            "gl_code":
                "620000",

            "cost_code":
                "C200",
        },


        # Concur item with unclear T-code.
        #
        # This should become a BLOCKING exception
        # at JE completion.
        {
            "transaction_id":
                "TX003",

            "description":
                "Concur expense",

            "amount":
                750.00,

            "ims_match":
                False,

            "concur_item":
                True,

            "tcode_clear":
                False,
        },


        # Rejected payment.
        #
        # It should be excluded from the JE,
        # but should NOT block the rest of the process.
        {
            "transaction_id":
                "TX004",

            "description":
                "Incoming bank transaction",

            "amount":
                -200.00,

            "ims_match":
                False,

            "is_rejection":
                True,
        },


        # Bank analysis fee.
        {
            "transaction_id":
                "TX005",

            "description":
                "Client Analysis Fee",

            "amount":
                50.00,

            "ims_match":
                False,

            "bank_analysis_fee":
                True,

            "gl_code":
                "BANKFEE",

            "cost_code":
                "CASH",
        },


        # Known ACH description,
        # but accounting treatment still requires clarification.
        {
            "transaction_id":
                "TX006",

            "description":
                "Miscellaneous ACH Debit",

            "amount":
                300.00,

            "ims_match":
                False,
        },


        # One-off transaction.
        #
        # Ascot told us these may legitimately remain
        # outside a fixed category taxonomy.
        {
            "transaction_id":
                "TX007",

            "description":
                "Unique one-time payment",

            "amount":
                425.00,

            "ims_match":
                False,
        },
    ],


    # --------------------------------------------------------
    # SHARED EPISODE-LEVEL RECORD SECTIONS
    # --------------------------------------------------------

    "input_validation": {},

    "normalization": {},

    "reconciliation_controls": {},

    "exception_queue": [],

    "exception_summary": {},

    "human_exception_review": {},


    "journal_entry": {

        "proposed_lines": [],

        "status":
            "not_started",

        "control_results": {},

        "known_controls_passed":
            False,
    },


    "final_approval": {},


    # Known design questions that should not silently
    # become invented automation rules.
    "open_design_questions": [

        "Exact ACH accounting treatment",

        "Permitted intercompany entities/codes",

        "Prior-month void processing",

        "Existing GL/cost mapping rules from Jen",

        "Final Cash Team notification endpoint",
    ],
}


# ============================================================
# 27. CREATE LANGGRAPH INITIAL STATE
# ============================================================

initial_state = {

    "episode_record":
        episode_record
}


# ============================================================
# 28. CREATE THREAD ID
# ============================================================

# The thread ID identifies this specific reconciliation episode.
config = {

    "configurable": {

        "thread_id":
            episode_record[
                "episode_id"
            ]
    }
}


# ============================================================
# 29. START THE AIC WORKFLOW
# ============================================================

result = graph.invoke(
    initial_state,
    config=config,
)


# ============================================================
# 30. SERVICE HUMAN INTERRUPTS
# ============================================================

# In this first skeleton there are two potential human
# interaction points:
#
# 1. Exception review
# 2. Final episode approval
#
# Later Streamlit will replace this terminal interface.
while "__interrupt__" in result:

    request = result[
        "__interrupt__"
    ][0].value


    review_type = request[
        "review_type"
    ]


    # ========================================================
    # EXCEPTION QUEUE REVIEW
    # ========================================================

    if review_type == "aic_exception_queue":

        print("\n========================================")
        print("HUMAN EXCEPTION REVIEW")
        print("========================================")


        decisions = []


        # Review only the blocking exceptions.
        for exception in request[
            "blocking_exceptions"
        ]:

            print("\n----------------------------------------")

            print(
                f"Transaction: "
                f"{exception['transaction_id']}"
            )

            print(
                f"Exception type: "
                f"{exception['exception_type']}"
            )

            print(
                f"Description: "
                f"{exception['description']}"
            )


            print("\n1 = Resolve")

            print(
                "2 = Escalate / cannot resolve yet"
            )


            while True:

                choice = input(
                    "Choose 1 or 2: "
                ).strip()


                if choice in {
                    "1",
                    "2",
                }:

                    break


                print(
                    "Please enter 1 or 2."
                )


            if choice == "1":

                # For Version 0, we capture a generic
                # resolution description.
                #
                # The browser interface will later expose
                # structured fields appropriate to the
                # exception type.
                resolution = input(
                    "Enter the material resolution: "
                ).strip()


                decisions.append(

                    {
                        "transaction_id":
                            exception[
                                "transaction_id"
                            ],

                        "decision":
                            "resolve",

                        "resolution":
                            resolution,
                    }
                )


            else:

                decisions.append(

                    {
                        "transaction_id":
                            exception[
                                "transaction_id"
                            ],

                        "decision":
                            "escalate",

                        "resolution":
                            "",
                    }
                )


        human_response = {

            "decisions":
                decisions
        }


    # ========================================================
    # FINAL EPISODE APPROVAL
    # ========================================================

    elif review_type == "final_aic_episode_approval":

        print("\n========================================")
        print("FINAL AIC EPISODE REVIEW")
        print("========================================")


        print(
            f"Responsible person: "
            f"{request['responsible_person']}"
        )


        print(
            f"Proposed JE lines: "
            f"{request['journal_entry_summary']['proposed_line_count']}"
        )


        print(
            "\n1 = Approve proposed final disposition"
        )

        print(
            "2 = Escalate / do not approve"
        )


        while True:

            choice = input(
                "Choose 1 or 2: "
            ).strip()


            if choice in {
                "1",
                "2",
            }:

                break


            print(
                "Please enter 1 or 2."
            )


        note = input(
            "Optional review note: "
        ).strip()


        if choice == "1":

            human_response = {

                "decision":
                    "approve",

                "note":
                    note,
            }


        else:

            human_response = {

                "decision":
                    "escalate",

                "note":
                    note,
            }


    else:

        raise ValueError(
            f"Unknown review type: "
            f"{review_type}"
        )


    # Resume the SAME reconciliation episode.
    result = graph.invoke(

        Command(
            resume=human_response
        ),

        config=config,
    )


# ============================================================
# 31. DISPLAY FINAL EPISODE SUMMARY
# ============================================================

final_record = result[
    "episode_record"
]


print("\n========================================")
print("FINAL SHARED EPISODE RECORD SUMMARY")
print("========================================")


print(
    f"Episode: "
    f"{final_record['episode_id']}"
)

print(
    f"Status: "
    f"{final_record['status']}"
)

print(
    f"Exceptions recorded: "
    f"{len(final_record['exception_queue'])}"
)

print(
    f"Proposed JE lines: "
    f"{len(final_record['journal_entry']['proposed_lines'])}"
)

print(
    f"Final approval: "
    f"{final_record['final_approval']}"
)


print("\nOpen design questions:")

for question in final_record[
    "open_design_questions"
]:

    print(
        f"  - {question}"
    )