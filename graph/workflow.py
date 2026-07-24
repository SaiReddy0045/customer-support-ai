from typing import TypedDict

from langgraph.graph import StateGraph, END

from agents.intent_classifier import classify_intent
from agents.billing_agent import handle_billing
from agents.refund_agent import handle_refund
from agents.support_agent import handle_support


class SupportState(TypedDict):
    query: str
    intent: str
    response: str


# -----------------------------
# Nodes
# -----------------------------

def classify_node(state: SupportState):
    intent = classify_intent(state["query"])
    return {
        "intent": intent
    }


def billing_node(state: SupportState):
    response = handle_billing(state["query"])
    return {
        "response": response
    }


def refund_node(state: SupportState):
    response = handle_refund(state["query"])
    return {
        "response": response
    }


def support_node(state: SupportState):
    response = handle_support(state["query"])
    return {
        "response": response
    }


# -----------------------------
# Router
# -----------------------------

def router(state: SupportState):

    if state["intent"] == "billing":
        return "billing"

    elif state["intent"] == "refund":
        return "refund"

    return "support"


# -----------------------------
# Graph
# -----------------------------

builder = StateGraph(SupportState)

builder.add_node("classifier", classify_node)
builder.add_node("billing", billing_node)
builder.add_node("refund", refund_node)
builder.add_node("support", support_node)

builder.set_entry_point("classifier")

builder.add_conditional_edges(
    "classifier",
    router,
    {
        "billing": "billing",
        "refund": "refund",
        "support": "support"
    }
)

builder.add_edge("billing", END)
builder.add_edge("refund", END)
builder.add_edge("support", END)

workflow = builder.compile()