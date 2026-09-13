# TypedDict lets us define the expected structure of the "state"
# that will travel through the reconciliation workflow.
from typing_extensions import TypedDict

# These are the main LangGraph building blocks we need:
# StateGraph = creates the workflow
# START = where the workflow begins
# END = where the workflow finishes
from langgraph.graph import StateGraph, START, END


# Define the information that one reconciliation case will contain.
# You can think of this as the "case file" that travels through the workflow.
class ReconciliationState(TypedDict):

    # Unique identifier for the transaction.
    transaction_id: str

    # Text description of the transaction.
    description: str

    # Transaction amount.
    amount: float

    # Whether we found a matching record in IMS.
    # bool means the value must be True or False.
    ims_match: bool

    # Whether supporting documentation/evidence is available.
    supporting_evidence: bool

    # This will store our evaluation of whether the evidence is sufficient.
    evidence_sufficient: bool

    # This records the current status of the reconciliation case.
    status: str


# This function represents the first step of the workflow:
# receiving a transaction.
#
# "state" contains all information currently known about the case.
def receive_transaction(state):

    # Print the transaction ID so we can observe what the workflow is doing.
    print(f"\nReceived: {state['transaction_id']}")

    # Print the transaction description.
    print(f"Description: {state['description']}")

    # Print the transaction amount.
    print(f"Amount: ${state['amount']}")

    # Return only the information we want to update.
    # LangGraph will merge this back into the existing state.
    return {"status": "received"}


# This function evaluates whether the available evidence is sufficient.
def check_evidence(state):

    # Here we define a very simple rule:
    #
    # evidence is sufficient only when:
    # 1. an IMS match exists
    # AND
    # 2. supporting evidence exists.
    #
    # This is only a learning example, not an actual Ascot accounting rule.
    sufficient = (
        state["ims_match"]
        and state["supporting_evidence"]
    )

    # Print what evidence was found.
    print(f"IMS match: {state['ims_match']}")
    print(f"Supporting evidence: {state['supporting_evidence']}")

    # Save the result of our evidence evaluation into the state.
    return {"evidence_sufficient": sufficient}


# This function decides which path the workflow should take next.
#
# It does not change the state.
# Its only job is routing.
def route_case(state):

    # If evidence_sufficient is True,
    # send the case to the automated processing path.
    if state["evidence_sufficient"]:
        return "auto_process"

    # Otherwise, send the case to human review.
    else:
        return "human_review"


# This function represents the automated processing path.
def auto_process(state):

    # For now, we simply print what happened.
    # Later, this node could perform real accounting actions.
    print("Evidence sufficient → automatically process.")

    # Update the case status.
    return {"status": "processed"}


# This function represents the human-review path.
def human_review(state):

    # For now, we simply mark the case as requiring human review.
    # Later, LangGraph can actually pause here and wait for a person.
    print("Evidence incomplete → send to human review.")

    # Update the case status.
    return {"status": "needs_human_review"}


# Create a new LangGraph workflow.
#
# ReconciliationState tells LangGraph what information
# will move through the workflow.
builder = StateGraph(ReconciliationState)


# Add the "receive_transaction" function as a node in the graph.
#
# First argument:
# the name we give the node inside LangGraph.
#
# Second argument:
# the Python function that should run at this node.
builder.add_node(
    "receive_transaction",
    receive_transaction
)


# Add the evidence-checking node.
builder.add_node(
    "check_evidence",
    check_evidence
)


# Add the automated-processing node.
builder.add_node(
    "auto_process",
    auto_process
)


# Add the human-review node.
builder.add_node(
    "human_review",
    human_review
)


# Tell LangGraph where the workflow begins.
#
# START → receive_transaction
builder.add_edge(
    START,
    "receive_transaction"
)


# After receiving the transaction,
# always move to the evidence-checking step.
#
# receive_transaction → check_evidence
builder.add_edge(
    "receive_transaction",
    "check_evidence"
)


# This is the branching part of the workflow.
#
# After "check_evidence",
# LangGraph runs route_case().
#
# route_case() will return either:
# "auto_process"
# or
# "human_review".
builder.add_conditional_edges(

    # The decision happens after this node.
    "check_evidence",

    # This function decides which route to take.
    route_case,

    # This tells LangGraph where each possible result should go.
    {
        "auto_process": "auto_process",
        "human_review": "human_review",
    },
)


# If the automated-processing path is used,
# finish the workflow afterward.
#
# auto_process → END
builder.add_edge(
    "auto_process",
    END
)


# If the human-review path is used,
# also finish the workflow afterward.
#
# human_review → END
builder.add_edge(
    "human_review",
    END
)


# Compile the workflow.
#
# Before this line, "builder" is essentially the workflow design.
# After compile(), "graph" becomes something we can actually run.
graph = builder.compile()


# Create one synthetic reconciliation case.
#
# This is the input that will travel through the workflow.
case = {

    # Transaction identifier.
    "transaction_id": "TX001",

    # Synthetic description.
    "description": "State payment",

    # Synthetic amount.
    "amount": 1250.00,

    # We pretend that an IMS match was found.
    "ims_match": True,

    # We pretend that supporting evidence was NOT found.
    "supporting_evidence": False,

    # Initial value before the evidence-checking node evaluates it.
    "evidence_sufficient": False,

    # Initial case status.
    "status": "new",
}


# Run the workflow once using the case above.
#
# "invoke" means:
# start at START,
# move through the graph,
# update the state,
# and stop at END.
result = graph.invoke(case)


# Print the final state after the workflow finishes.
print("\nFinal state:")
print(result)