from typing import TypedDict
from datetime import datetime, timedelta, timezone
import re

from langgraph.graph import StateGraph, END
from sqlalchemy import select

from agents.intent_classifier import detect_intents, classify_request
from agents.billing_agent import handle_billing
from agents.refund_agent import handle_refund
from agents.support_agent import handle_support
from agents.shopping_agent import handle_shopping
from agents.order_agent import handle_order
from database.db import SessionLocal
from database.models import Conversation
from services.support_ticket_service import (
    create_support_ticket,
    get_support_ticket_for_customer,
    ticket_to_dict,
)


class SupportState(TypedDict, total=False):
    query: str
    intent: str
    domain: str
    action: str
    response: str
    customer_id: str
    conversation_id: str
    conversation_history: list
    intents: list[str]


def classify_node(state: SupportState):
    db = SessionLocal()
    try:
        conversation = None
        if state.get("conversation_id"):
            conversation = db.execute(
                select(Conversation).where(
                    Conversation.conversation_id == state["conversation_id"]
                )
            ).scalar_one_or_none()
        if conversation and conversation.awaiting_confirmation and conversation.pending_expires_at:
            expires_at = conversation.pending_expires_at
            if expires_at.tzinfo is not None:
                expires_at = expires_at.astimezone(timezone.utc).replace(tzinfo=None)
            if expires_at <= datetime.now(timezone.utc).replace(tzinfo=None):
                conversation.pending_action = None
                conversation.pending_order_id = None
                conversation.awaiting_confirmation = False
                conversation.pending_expires_at = None
                db.commit()
                conversation = None
        request = classify_request(
            state["query"],
            state.get("conversation_history") or [],
            pending_action=conversation.pending_action if conversation else None,
            awaiting_confirmation=bool(conversation and conversation.awaiting_confirmation),
        )
    finally:
        db.close()
    domain = request.get("domain", "support")
    action = request.get("action", "fallback")
    intents = detect_intents(state["query"], state.get("conversation_history") or [])
    return {
        "intent": domain,
        "domain": domain,
        "action": action,
        "intents": intents,
    }


def shopping_node(state: SupportState):
    return {"response": handle_shopping(state["query"]) }


def order_node(state: SupportState):
    return {
        "response": handle_order(
            state["query"],
            state.get("customer_id") or None,
            state.get("conversation_history") or [],
            state.get("conversation_id") or None,
        )
    }


def billing_node(state: SupportState):
    return {
        "response": handle_billing(
            state["query"],
            state.get("customer_id") or None,
            state.get("conversation_history") or [],
        )
    }


def refund_node(state: SupportState):
    return {
        "response": handle_refund(
            state["query"],
            state.get("customer_id") or None,
            state.get("conversation_history") or [],
            state.get("conversation_id") or None,
        )
    }


def multi_node(state: SupportState):
    query = state["query"]
    history = state.get("conversation_history") or []
    customer_id = state.get("customer_id") or None
    responses: list[str] = []
    intents = state.get("intents") or detect_intents(query, history)

    if "order" in intents:
        responses.append(f"Order: {handle_order(query, customer_id, history, state.get('conversation_id') or None)}")
    if "billing" in intents:
        responses.append(f"Billing: {handle_billing(query, customer_id, history)}")
    if "refund" in intents:
        responses.append(f"Refund: {handle_refund(query, customer_id, history, state.get('conversation_id') or None)}")
    if "shopping" in intents:
        responses.append(f"Shopping: {handle_shopping(query)}")

    if not responses:
        responses.append(handle_support(query, customer_id, history))

    return {"response": "\n\n".join(responses)}


def support_node(state: SupportState):
    if state.get("action") == "unbound_confirmation":
        return {"response": "I don't have a pending action to confirm. What would you like help with?"}
    if state.get("action") == "support_ticket_lookup":
        customer_id = state.get("customer_id") or ""
        if not customer_id:
            return {"response": "Please sign in so I can look up a support ticket linked to your account."}
        ticket_match = re.search(r"\b(TKT-[A-Z0-9]+)\b", state["query"], re.IGNORECASE)
        if not ticket_match:
            return {"response": "Please provide the support ticket ID you want me to look up."}
        db = SessionLocal()
        try:
            ticket = get_support_ticket_for_customer(
                db,
                customer_id,
                ticket_match.group(1).upper(),
            )
            if not ticket:
                return {"response": f"Support ticket {ticket_match.group(1).upper()} was not found in your account."}
            ticket_data = ticket_to_dict(ticket)
            order_detail = f" Order: {ticket_data['orderId']}." if ticket_data["orderId"] else ""
            return {
                "response": (
                    f"Support ticket {ticket_data['ticketId']} has status {ticket_data['status']}. "
                    f"Category: {ticket_data['category']}.{order_detail} "
                    f"Details: {ticket_data['description']}"
                )
            }
        finally:
            db.close()
    if state.get("action") == "create_support_ticket":
        customer_id = state.get("customer_id") or ""
        if not customer_id:
            return {"response": "Please sign in so I can create a support ticket linked to your account."}
        db = SessionLocal()
        try:
            explicit_order = re.search(r"\b(ORD(?!ER\b)[A-Z0-9]+)\b", state["query"], re.IGNORECASE)
            ticket = create_support_ticket(
                db,
                customer_id,
                "Human Support Escalation",
                state["query"],
                explicit_order.group(1).upper() if explicit_order else None,
                state.get("conversation_id"),
            )
            ticket_data = ticket_to_dict(ticket)
            return {
                "response": (
                    f"I created demo support ticket {ticket_data['ticketId']} with status {ticket_data['status']}. "
                    "This records your request internally; it does not contact a live representative."
                )
            }
        except LookupError as exc:
            return {"response": str(exc)}
        finally:
            db.close()
    return {"response": handle_support(state["query"], state.get("customer_id") or None, state.get("conversation_history") or [])}


def router(state: SupportState):
    return state.get("domain") or state.get("intent") or "support"


builder = StateGraph(SupportState)

builder.add_node("classifier", classify_node)
builder.add_node("shopping", shopping_node)
builder.add_node("order", order_node)
builder.add_node("billing", billing_node)
builder.add_node("refund", refund_node)
builder.add_node("multi", multi_node)
builder.add_node("support", support_node)

builder.set_entry_point("classifier")

builder.add_conditional_edges(
    "classifier",
    router,
    {
        "shopping": "shopping",
        "order": "order",
        "billing": "billing",
        "refund": "refund",
        "multi": "multi",
        "support": "support",
    },
)

builder.add_edge("shopping", END)
builder.add_edge("order", END)
builder.add_edge("billing", END)
builder.add_edge("refund", END)
builder.add_edge("multi", END)
builder.add_edge("support", END)

workflow = builder.compile()
