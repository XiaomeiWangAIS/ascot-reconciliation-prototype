# ============================================================
# ASCOT RECONCILIATION PROTOTYPE
# VERSION: SHARED EPISODE-LEVEL ACCOUNTABILITY RECORD
#
# DESIGN IDEA
# ------------------------------------------------------------
#
# This prototype does NOT record every machine action.
#
# Instead, one shared record is maintained for the complete
# reconciliation episode.
#
# The record preserves only information needed for:
#
# 1. understanding the accounting case,
# 2. understanding what evidence was relied upon,
# 3. understanding the machine's assessment,
# 4. identifying important exceptions,
# 5. recording material human judgment,
# 6. identifying the person responsible for the episode,
# 7. recording the final disposition and approval.
#
# One human remains responsible for the reconciliation episode
# even when substantial parts of the work are performed
# automatically.
#
# IMPORTANT:
# We are still using synthetic data only.
# ============================================================


# ============================================================
# IMPORTS
# ============================================================

# os lets Python work with environment variables.
# We use it for the Groq API key.
import os


# getpass lets us enter an API key without displaying
# the characters in the terminal.
import getpass


# json lets us save the final shared reconciliation record
# as a readable JSON file.
import json


# deepcopy lets us safely make a copy of our shared record
# before modifying it inside a workflow node.
#
# This avoids accidentally changing the existing state object
# directly.
from copy import deepcopy


# Path gives us a convenient way to create folders
# and save files.
from pathlib import Path


# Literal restricts the LLM to predefined categories.
from typing import Literal


# TypedDict describes the structure of LangGraph state.
from typing_extensions import TypedDict


# Pydantic gives us structured LLM output.
from pydantic import BaseModel, Field


# LangGraph workflow components.
from langgraph.graph import StateGraph, START, END


# InMemorySaver lets LangGraph preserve the current state
# when an interrupt pauses the workflow.
from langgraph.checkpoint.memory import InMemorySaver


# interrupt() pauses workflow execution for human judgment.
#
# Command(resume=...) resumes the same reconciliation episode.
from langgraph.types import interrupt, Command


# LangChain integration with Groq.
from langchain_groq import ChatGroq


# ============================================================
# 1. GET GROQ API KEY
# ============================================================

# Check whether GROQ_API_KEY already exists
# in the current Codespace environment.
if not os.environ.get("GROQ_API_KEY"):

    # Ask for the API key.
    #
    # getpass hides the value while you type or paste.
    api_key = getpass.getpass(
        "Paste your Groq API key here "
        "(input will be hidden): "
    )

    # Remove accidental spaces.
    api_key = api_key.strip()

    # Stop if no API key was entered.
    if not api_key:
        raise ValueError(
            "No Groq API key was entered."
        )

    # Store the key temporarily in the environment.
    os.environ["GROQ_API_KEY"] = api_key


# ============================================================
# 2. IDENTIFY THE PERSON RESPONSIBLE FOR THE EPISODE
# ============================================================

# Our design assumes that one identifiable person remains
# responsible for the overall reconciliation episode.
#
# Therefore, before the workflow starts,
# we require a responsible person to be assigned.
while True:

    responsible_person = input(
        "Enter the responsible person for this "
        "reconciliation episode: "
    ).strip()

    # Do not allow an unassigned episode.
    if responsible_person:
        break

    print(
        "A responsible person must be assigned."
    )


# ============================================================
# 3. DEFINE THE STRUCTURED OUTPUT FROM THE LLM
# ============================================================

# The model must return a predictable structure
# rather than arbitrary prose.
class TransactionClassification(BaseModel):

    # The model must select exactly one category.
    category: Literal[
        "state_payment",
        "payroll",
        "vendor_expense",
        "unknown",
    ] = Field(
        description=(
            "The most likely transaction category "
            "based only on the available evidence."
        )
    )

    # Model-reported confidence between 0 and 1.
    #
    # Remember:
    # this is NOT yet a statistically calibrated probability.
    confidence: float = Field(
        ge=0,
        le=1,
        description=(
            "Model-reported confidence between 0 and 1."
        ),
    )

    # Short explanation of the classification.
    explanation: str = Field(
        description=(
            "Brief explanation based only on "
            "the available evidence."
        )
    )


# ============================================================
# 4. DEFINE LANGGRAPH STATE
# ============================================================

# Notice that the LangGraph state now contains ONE main object:
#
# episode_record
#
# Instead of creating a separate record for every node,
# every part of the workflow works on the same shared record.
class ReconciliationState(TypedDict):

    # Complete shared reconciliation record.
    episode_record: dict


# ============================================================
# 5. HELPER FUNCTION FOR UPDATING THE SHARED RECORD
# ============================================================

# Every node receives the current state.
#
# This helper creates a safe copy of the shared record
# before a node modifies it.
def get_record_copy(state):

    return deepcopy(
        state["episode_record"]
    )


# ============================================================
# 6. CREATE THE LANGUAGE MODEL
# ============================================================

# Create the Groq-hosted LLM.
llm = ChatGroq(

    # Model used for this learning prototype.
    model="openai/gpt-oss-20b",

    # We prefer consistency rather than creativity
    # for accounting classification.
    temperature=0,

    # Retry temporary API/network failures.
    max_retries=2,
)


# Require the model to follow the
# TransactionClassification structure.
structured_llm = llm.with_structured_output(
    TransactionClassification
)


# ============================================================
# 7. NODE 1: RECEIVE THE RECONCILIATION EPISODE
# ============================================================

def receive_episode(state):

    # Make a safe copy of the shared record.
    record = get_record_copy(state)

    print("\n========================================")
    print("1. RECONCILIATION EPISODE RECEIVED")
    print("========================================")

    print(
        f"Episode ID: "
        f"{record['episode_id']}"
    )

    print(
        f"Responsible person: "
        f"{record['responsible_person']}"
    )

    print(
        f"Description: "
        f"{record['transaction']['description']}"
    )

    print(
        f"Amount: "
        f"${record['transaction']['amount']:.2f}"
    )


    # Update only the overall episode status.
    #
    # We are NOT creating an event log.
    record["status"] = "in_progress"


    # Return the updated shared record.
    return {
        "episode_record": record
    }


# ============================================================
# 8. NODE 2: MACHINE ASSESSMENT
# ============================================================

def machine_assessment(state):

    # Copy the shared record.
    record = get_record_copy(state)


    # Extract the transaction information
    # so the code is easier to read.
    transaction = record[
        "transaction"
    ]


    # Extract the evidence section.
    evidence = record[
        "evidence"
    ]


    # Build a readable summary of evidence sources.
    #
    # Example:
    #
    # IMS: no_match
    # Supporting document: unavailable
    evidence_sources_text = "\n".join(

        f"- {item['source']}: {item['result']}"

        for item in evidence["sources"]
    )


    # Construct the prompt.
    prompt = f"""
You are assisting with an accounting reconciliation.

Classify the transaction using ONLY the information supplied.

Allowed categories:

1. state_payment
   Payment involving a state government or state agency.

2. payroll
   Payment related to employee compensation or payroll.

3. vendor_expense
   Payment to a supplier or vendor for goods or services.

4. unknown
   Use this when the evidence is insufficient,
   ambiguous, or inconsistent.

Do not invent missing information.

TRANSACTION

Description:
{transaction["description"]}

Amount:
{transaction["amount"]}

EVIDENCE SUMMARY

{evidence["summary"]}

EVIDENCE SOURCES

{evidence_sources_text}
"""


    print("\n========================================")
    print("2. MACHINE ASSESSMENT")
    print("========================================")


    # Ask the Groq-hosted model to classify the transaction.
    result = structured_llm.invoke(
        prompt
    )


    # --------------------------------------------------------
    # DETERMINE WHETHER HUMAN JUDGMENT IS NEEDED
    # --------------------------------------------------------

    # Start by assuming human judgment is not required.
    requires_human_judgment = False

    # Start with no exception.
    exception = ""

    # Start with a normal routing reason.
    routing_reason = (
        "Machine assessment is sufficiently clear "
        "under the current prototype rule."
    )


    # If the model cannot classify the transaction,
    # we treat that as an important exception.
    if result.category == "unknown":

        requires_human_judgment = True

        exception = (
            "Insufficient evidence for reliable classification."
        )

        routing_reason = (
            "Machine could not determine a supported "
            "classification."
        )


    # If confidence is below our illustrative threshold,
    # human judgment is also required.
    #
    # 0.80 is still ONLY a prototype threshold.
    #
    # It is NOT an Ascot accounting policy.
    elif result.confidence < 0.80:

        requires_human_judgment = True

        exception = (
            "Machine classification has low confidence."
        )

        routing_reason = (
            "Machine confidence is below the current "
            "prototype threshold."
        )


    # --------------------------------------------------------
    # UPDATE THE SHARED MACHINE-ASSESSMENT SECTION
    # --------------------------------------------------------

    # Instead of creating multiple log events,
    # we store the material machine conclusion
    # in one shared section.
    record["machine_assessment"] = {

        # What the machine concluded.
        "classification":
            result.category,

        # Machine-reported confidence.
        "confidence":
            result.confidence,

        # Short reasoning.
        "explanation":
            result.explanation,

        # Whether judgment must shift to the human.
        "requires_human_judgment":
            requires_human_judgment,

        # Material exception, if one exists.
        "exception":
            exception,

        # Why the system selected the current route.
        "routing_reason":
            routing_reason,
    }


    print(
        f"Classification: "
        f"{result.category}"
    )

    print(
        f"Confidence: "
        f"{result.confidence:.2f}"
    )

    print(
        f"Explanation: "
        f"{result.explanation}"
    )

    print(
        f"Human judgment required: "
        f"{requires_human_judgment}"
    )


    # Update overall episode status.
    record["status"] = (
        "machine_assessment_completed"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 9. ROUTE THE DECISION INSTANCE
# ============================================================

# This function does not create documentation.
#
# It simply reads the shared record and determines
# whether control remains with the machine
# or shifts to the human.
def route_after_machine_assessment(state):

    record = state[
        "episode_record"
    ]

    machine = record[
        "machine_assessment"
    ]


    # If an important exception exists,
    # transfer this decision instance to the human.
    if machine[
        "requires_human_judgment"
    ]:

        return "human_judgment"


    # Otherwise continue automatically.
    return "machine_continue"


# ============================================================
# 10. MACHINE-CONTINUE PATH
# ============================================================

def machine_continue(state):

    record = get_record_copy(state)


    print("\n========================================")
    print("3. AUTOMATION CONTINUES")
    print("========================================")

    print(
        "No exception currently requires "
        "human intervention."
    )


    # Because human intervention was not required
    # at this decision instance, the machine's
    # classification becomes the proposed final classification.
    record["human_judgment"] = {

        "required":
            False,

        "decision":
            "not_required",

        "rationale":
            "",
    }


    # Store the proposed disposition.
    #
    # Notice that this is NOT yet approved.
    #
    # The responsible person still owns the episode.
    record["final_disposition"][
        "classification"
    ] = record[
        "machine_assessment"
    ][
        "classification"
    ]


    record["status"] = (
        "awaiting_final_approval"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 11. HUMAN JUDGMENT NODE
# ============================================================

def human_judgment(state):

    record = get_record_copy(state)

    machine = record[
        "machine_assessment"
    ]


    # --------------------------------------------------------
    # PAUSE THE WORKFLOW
    # --------------------------------------------------------
    #
    # We provide the human with the shared information
    # necessary to exercise judgment.
    #
    # We do NOT show a click-by-click machine history.
    human_response = interrupt(
        {
            "review_type":
                "exception_review",

            "episode_id":
                record["episode_id"],

            "responsible_person":
                record["responsible_person"],

            "transaction":
                record["transaction"],

            "evidence":
                record["evidence"],

            "machine_assessment":
                machine,

            "allowed_actions": [
                "accept_machine_assessment",
                "correct_classification",
                "escalate",
            ],
        }
    )


    # --------------------------------------------------------
    # EXECUTION RESUMES HERE AFTER HUMAN INPUT
    # --------------------------------------------------------

    action = human_response[
        "action"
    ]


    rationale = human_response.get(
        "rationale",
        "",
    )


    # --------------------------------------------------------
    # OPTION 1:
    # HUMAN ACCEPTS MACHINE ASSESSMENT
    # --------------------------------------------------------

    if action == "accept_machine_assessment":

        record["human_judgment"] = {

            "required":
                True,

            "decision":
                "accepted_machine_assessment",

            # We preserve only the material rationale,
            # not every action the reviewer performed.
            "rationale":
                rationale,
        }


        # The machine classification becomes
        # the proposed final classification.
        record[
            "final_disposition"
        ][
            "classification"
        ] = machine[
            "classification"
        ]


    # --------------------------------------------------------
    # OPTION 2:
    # HUMAN CORRECTS MACHINE ASSESSMENT
    # --------------------------------------------------------

    elif action == "correct_classification":

        corrected_classification = (
            human_response[
                "corrected_classification"
            ]
        )


        record["human_judgment"] = {

            "required":
                True,

            "decision":
                "corrected_machine_assessment",

            "machine_classification":
                machine["classification"],

            "corrected_classification":
                corrected_classification,

            # Because a material judgment changed
            # the machine conclusion,
            # the rationale is useful accountability information.
            "rationale":
                rationale,
        }


        # Human judgment determines the proposed
        # final classification.
        record[
            "final_disposition"
        ][
            "classification"
        ] = corrected_classification


    # --------------------------------------------------------
    # OPTION 3:
    # HUMAN ESCALATES THE CASE
    # --------------------------------------------------------

    elif action == "escalate":

        record["human_judgment"] = {

            "required":
                True,

            "decision":
                "escalated",

            "rationale":
                rationale,
        }


        # The case does not yet have a resolved classification.
        record[
            "final_disposition"
        ][
            "classification"
        ] = "unresolved"


    else:

        raise ValueError(
            f"Unexpected human action: {action}"
        )


    # After judgment, the episode moves to final approval.
    record["status"] = (
        "awaiting_final_approval"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 12. FINAL EPISODE APPROVAL
# ============================================================

# This node is reached by BOTH:
#
# - machine-led cases
# - cases involving human judgment
#
# This is important to our design:
#
# machine execution does NOT eliminate
# human responsibility for the complete episode.
def final_approval(state):

    record = get_record_copy(state)


    # Pause again so the responsible person can review
    # the complete shared record.
    approval_response = interrupt(
        {
            "review_type":
                "final_episode_approval",

            "episode_id":
                record["episode_id"],

            "responsible_person":
                record["responsible_person"],

            "transaction":
                record["transaction"],

            "evidence":
                record["evidence"],

            "machine_assessment":
                record["machine_assessment"],

            "human_judgment":
                record["human_judgment"],

            "proposed_final_classification":
                record[
                    "final_disposition"
                ][
                    "classification"
                ],
        }
    )


    # Read the responsible person's final decision.
    decision = approval_response[
        "decision"
    ]


    note = approval_response.get(
        "note",
        "",
    )


    # --------------------------------------------------------
    # RESPONSIBLE PERSON APPROVES THE FINAL DISPOSITION
    # --------------------------------------------------------

    if decision == "approve":

        record[
            "final_disposition"
        ][
            "approved"
        ] = True


        record[
            "final_disposition"
        ][
            "approval_decision"
        ] = (
            "approved_by_responsible_person"
        )


        record[
            "final_disposition"
        ][
            "approval_note"
        ] = note


    # --------------------------------------------------------
    # RESPONSIBLE PERSON DOES NOT APPROVE
    # --------------------------------------------------------

    elif decision == "escalate":

        record[
            "final_disposition"
        ][
            "approved"
        ] = False


        record[
            "final_disposition"
        ][
            "approval_decision"
        ] = (
            "not_approved_escalated"
        )


        record[
            "final_disposition"
        ][
            "approval_note"
        ] = note


    else:

        raise ValueError(
            f"Unexpected approval decision: {decision}"
        )


    return {
        "episode_record": record
    }


# ============================================================
# 13. FINALIZE THE RECONCILIATION EPISODE
# ============================================================

def finalize_episode(state):

    record = get_record_copy(state)

    final_disposition = record[
        "final_disposition"
    ]


    print("\n========================================")
    print("FINALIZATION")
    print("========================================")


    # If the responsible person did not approve,
    # the case remains escalated.
    if not final_disposition[
        "approved"
    ]:

        record["status"] = (
            "escalated_for_further_review"
        )


    # A classification such as "unknown" or "unresolved"
    # also means the accounting issue remains unresolved,
    # even if the responsible person acknowledges that outcome.
    elif final_disposition[
        "classification"
    ] in {
        "unknown",
        "unresolved",
    }:

        record["status"] = (
            "escalated_for_further_review"
        )


    # Otherwise the reconciliation episode is complete.
    else:

        record["status"] = (
            "completed"
        )


    print(
        f"Final classification: "
        f"{final_disposition['classification']}"
    )

    print(
        f"Approved by responsible person: "
        f"{final_disposition['approved']}"
    )

    print(
        f"Final status: "
        f"{record['status']}"
    )


    return {
        "episode_record": record
    }


# ============================================================
# 14. CREATE CHECKPOINTER
# ============================================================

# This allows LangGraph to pause and resume
# the same reconciliation episode.
checkpointer = InMemorySaver()


# ============================================================
# 15. BUILD THE WORKFLOW
# ============================================================

builder = StateGraph(
    ReconciliationState
)


# Register each function as a LangGraph node.
builder.add_node(
    "receive_episode",
    receive_episode,
)

builder.add_node(
    "machine_assessment",
    machine_assessment,
)

builder.add_node(
    "machine_continue",
    machine_continue,
)

builder.add_node(
    "human_judgment",
    human_judgment,
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
# 16. CONNECT THE WORKFLOW
# ============================================================

# START
#   ↓
# receive episode
builder.add_edge(
    START,
    "receive_episode",
)


# receive episode
#   ↓
# machine assessment
builder.add_edge(
    "receive_episode",
    "machine_assessment",
)


# After the machine assessment,
# determine whether judgment should remain with the machine
# or shift to the human.
builder.add_conditional_edges(

    "machine_assessment",

    route_after_machine_assessment,

    {
        "machine_continue":
            "machine_continue",

        "human_judgment":
            "human_judgment",
    },
)


# Both paths converge again before final approval.
builder.add_edge(
    "machine_continue",
    "final_approval",
)

builder.add_edge(
    "human_judgment",
    "final_approval",
)


# Final approval is followed by finalization.
builder.add_edge(
    "final_approval",
    "finalize_episode",
)


# Finalization ends the episode.
builder.add_edge(
    "finalize_episode",
    END,
)


# ============================================================
# 17. COMPILE THE GRAPH
# ============================================================

graph = builder.compile(
    checkpointer=checkpointer
)


# ============================================================
# 18. CREATE ONE SYNTHETIC SHARED EPISODE RECORD
# ============================================================

# Notice the structure:
#
# ONE episode
# ONE responsible person
# ONE shared evidence section
# ONE machine-assessment section
# ONE human-judgment section
# ONE final-disposition section
#
# This is our shared accountability record.
episode_record = {

    # Unique reconciliation episode ID.
    "episode_id":
        "TX001",


    # One identifiable human remains accountable
    # for the complete episode.
    "responsible_person":
        responsible_person,


    # --------------------------------------------------------
    # TRANSACTION
    # --------------------------------------------------------

    "transaction": {

        "description":
            "PAYMENT 4821",

        "amount":
            1250.00,
    },


    # --------------------------------------------------------
    # EVIDENCE
    # --------------------------------------------------------

    # Instead of recording every search/click,
    # we preserve the evidence that matters to the judgment.
    "evidence": {

        "summary":
            (
                "No supporting documentation currently "
                "establishes the nature of this payment."
            ),

        # Evidence provenance can still be preserved
        # at a useful level.
        "sources": [

            {
                "source":
                    "IMS",

                "result":
                    "no_match",
            },

            {
                "source":
                    "supporting_document",

                "result":
                    "not_available",
            },

            {
                "source":
                    "email_confirmation",

                "result":
                    "not_available",
            },
        ],
    },


    # --------------------------------------------------------
    # MACHINE ASSESSMENT
    # --------------------------------------------------------

    # The machine will populate this section.
    "machine_assessment": {

        "classification":
            "",

        "confidence":
            0.0,

        "explanation":
            "",

        "requires_human_judgment":
            False,

        "exception":
            "",

        "routing_reason":
            "",
    },


    # --------------------------------------------------------
    # HUMAN JUDGMENT
    # --------------------------------------------------------

    # Human judgment will populate this section
    # only when it is materially relevant.
    "human_judgment": {

        "required":
            False,

        "decision":
            "",

        "rationale":
            "",
    },


    # --------------------------------------------------------
    # FINAL DISPOSITION
    # --------------------------------------------------------

    # Final outcome belongs to the complete episode,
    # not to an isolated machine node.
    "final_disposition": {

        "classification":
            "",

        "approved":
            False,

        "approval_decision":
            "",

        "approval_note":
            "",
    },


    # Overall case status.
    "status":
        "new",
}


# ============================================================
# 19. CREATE LANGGRAPH STATE
# ============================================================

initial_state = {

    "episode_record":
        episode_record
}


# ============================================================
# 20. CREATE THREAD ID
# ============================================================

# The thread ID identifies THIS reconciliation episode
# when LangGraph pauses and resumes it.
config = {

    "configurable": {

        "thread_id":
            episode_record[
                "episode_id"
            ]
    }
}


# ============================================================
# 21. START THE WORKFLOW
# ============================================================

result = graph.invoke(
    initial_state,
    config=config,
)


# ============================================================
# 22. HANDLE INTERRUPTS
# ============================================================

# There can now be MORE THAN ONE human interaction:
#
# 1. exception review, if needed
# 2. final episode approval, always
#
# Therefore we use a loop:
#
# while the graph is paused,
# inspect what kind of human judgment is requested,
# collect the response,
# and resume the SAME episode.
while "__interrupt__" in result:

    # Get the information supplied by interrupt().
    request = result[
        "__interrupt__"
    ][0].value


    # Determine which type of review is required.
    review_type = request[
        "review_type"
    ]


    # ========================================================
    # HUMAN REVIEW TYPE 1:
    # EXCEPTION / JUDGMENT REVIEW
    # ========================================================

    if review_type == "exception_review":

        print("\n========================================")
        print("HUMAN JUDGMENT REQUIRED")
        print("========================================")

        print(
            f"Episode: "
            f"{request['episode_id']}"
        )

        print(
            f"Responsible person: "
            f"{request['responsible_person']}"
        )


        machine = request[
            "machine_assessment"
        ]


        print("\n--- MACHINE ASSESSMENT ---")

        print(
            f"Classification: "
            f"{machine['classification']}"
        )

        print(
            f"Confidence: "
            f"{machine['confidence']:.2f}"
        )

        print(
            f"Explanation: "
            f"{machine['explanation']}"
        )

        print(
            f"Exception: "
            f"{machine['exception']}"
        )


        print("\n--- HUMAN DECISION ---")

        print(
            "1 = Accept machine assessment"
        )

        print(
            "2 = Correct classification"
        )

        print(
            "3 = Escalate / leave unresolved"
        )


        # Require valid input.
        while True:

            choice = input(
                "Choose 1, 2, or 3: "
            ).strip()

            if choice in {
                "1",
                "2",
                "3",
            }:
                break

            print(
                "Please enter 1, 2, or 3."
            )


        # ----------------------------------------------------
        # ACCEPT MACHINE ASSESSMENT
        # ----------------------------------------------------

        if choice == "1":

            rationale = input(
                "Optional rationale: "
            ).strip()


            human_response = {

                "action":
                    "accept_machine_assessment",

                "rationale":
                    rationale,
            }


        # ----------------------------------------------------
        # CORRECT MACHINE ASSESSMENT
        # ----------------------------------------------------

        elif choice == "2":

            print("\nClassification options:")

            print(
                "1 = state_payment"
            )

            print(
                "2 = payroll"
            )

            print(
                "3 = vendor_expense"
            )

            print(
                "4 = unknown"
            )


            category_map = {

                "1":
                    "state_payment",

                "2":
                    "payroll",

                "3":
                    "vendor_expense",

                "4":
                    "unknown",
            }


            while True:

                category_choice = input(
                    "Choose corrected classification: "
                ).strip()

                if (
                    category_choice
                    in category_map
                ):
                    break

                print(
                    "Please enter 1, 2, 3, or 4."
                )


            corrected_classification = (
                category_map[
                    category_choice
                ]
            )


            # When judgment changes the machine result,
            # recording the reason is useful.
            rationale = input(
                "Brief rationale for correction: "
            ).strip()


            human_response = {

                "action":
                    "correct_classification",

                "corrected_classification":
                    corrected_classification,

                "rationale":
                    rationale,
            }


        # ----------------------------------------------------
        # ESCALATE
        # ----------------------------------------------------

        else:

            rationale = input(
                "Reason for escalation: "
            ).strip()


            human_response = {

                "action":
                    "escalate",

                "rationale":
                    rationale,
            }


    # ========================================================
    # HUMAN REVIEW TYPE 2:
    # FINAL EPISODE APPROVAL
    # ========================================================

    elif review_type == "final_episode_approval":

        print("\n========================================")
        print("FINAL EPISODE APPROVAL")
        print("========================================")


        print(
            f"Responsible person: "
            f"{request['responsible_person']}"
        )


        print("\n--- TRANSACTION ---")

        print(
            request[
                "transaction"
            ]
        )


        print("\n--- EVIDENCE ---")

        print(
            request[
                "evidence"
            ]
        )


        print("\n--- MACHINE ASSESSMENT ---")

        print(
            request[
                "machine_assessment"
            ]
        )


        print("\n--- HUMAN JUDGMENT ---")

        print(
            request[
                "human_judgment"
            ]
        )


        print("\n--- PROPOSED OUTCOME ---")

        print(
            f"Classification: "
            f"{request['proposed_final_classification']}"
        )


        print("\n1 = Approve final disposition")

        print(
            "2 = Do not approve / escalate"
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


        # Responsible person approves.
        if choice == "1":

            note = input(
                "Optional approval note: "
            ).strip()


            human_response = {

                "decision":
                    "approve",

                "note":
                    note,
            }


        # Responsible person does not approve.
        else:

            note = input(
                "Reason for escalation: "
            ).strip()


            human_response = {

                "decision":
                    "escalate",

                "note":
                    note,
            }


    # ========================================================
    # SAFETY CHECK
    # ========================================================

    else:

        raise ValueError(
            f"Unknown review type: {review_type}"
        )


    # ========================================================
    # RESUME THE SAME RECONCILIATION EPISODE
    # ========================================================

    result = graph.invoke(

        Command(
            resume=human_response
        ),

        # SAME thread ID means:
        #
        # continue the same saved episode,
        # rather than starting a new one.
        config=config,
    )


# ============================================================
# 23. GET THE FINAL SHARED RECORD
# ============================================================

final_record = result[
    "episode_record"
]


# ============================================================
# 24. DISPLAY THE FINAL SHARED RECORD
# ============================================================

print("\n========================================")
print("SHARED RECONCILIATION RECORD")
print("========================================")


# json.dumps(..., indent=2)
# prints the record in a readable structured format.
print(
    json.dumps(
        final_record,
        indent=2,
        ensure_ascii=False,
    )
)


# ============================================================
# 25. SAVE THE SHARED RECORD
# ============================================================

# Create a folder for final shared records.
record_folder = Path(
    "shared_records"
)


# Create it if it does not already exist.
record_folder.mkdir(
    exist_ok=True
)


# Each episode gets ONE shared record.
#
# Example:
#
# shared_records/TX001.json
record_file = (

    record_folder

    / (
        f"{final_record['episode_id']}.json"
    )
)


# Save only the shared episode-level record.
#
# There is no node-by-node event history here.
with record_file.open(
    "w",
    encoding="utf-8",
) as file:

    json.dump(
        final_record,
        file,
        indent=2,
        ensure_ascii=False,
    )


print("\n========================================")
print("SHARED RECORD SAVED")
print("========================================")

print(
    f"Saved to: {record_file}"
)