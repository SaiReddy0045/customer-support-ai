from typing import TypedDict

from langgraph.graph import StateGraph, END

from agents.supervisor_agent import supervisor_agent
from agents.billing_agent import handle_billing
from agents.refund_agent import handle_refund
from agents.support_agent import handle_support


class SupportState(TypedDict):
    query: str
    intent: str
    response: str


# -----------------------------
# Supervisor Agent
# -----------------------------

def supervisor_node(state: SupportState):

    intent = supervisor_agent(state["query"])

    return {
        "intent": intent
    }


# -----------------------------
# Specialist Agents
# -----------------------------

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
# Supervisor Router
# -----------------------------

def route_to_agent(state: SupportState):

    if state["intent"] == "billing":
        return "billing"

    if state["intent"] == "refund":
        return "refund"

    return "support"


# -----------------------------
# Build LangGraph
# -----------------------------

builder = StateGraph(SupportState)

builder.add_node("supervisor", supervisor_node)

builder.add_node("billing", billing_node)
builder.add_node("refund", refund_node)
builder.add_node("support", support_node)

builder.set_entry_point("supervisor")

builder.add_conditional_edges(
    "supervisor",
    route_to_agent,
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