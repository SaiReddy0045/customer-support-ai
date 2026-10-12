from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from sqlalchemy import select
import re
from datetime import datetime, timedelta

from config.llm import llm
from database.db import SessionLocal
from agents.intent_classifier import classify_request
from database.models import Conversation, Customer, Order, Payment, Refund
from services.tracking_service import REFUND_WINDOW_HOURS, calculate_tracking, refund_ineligibility_reason
from tools.order_tools import get_order_details, get_customer_orders
from tools.refund_tools import ACTIVE_REFUND_STATUSES, create_refund_for_customer


REFUND_SYSTEM_PROMPT = """
You are the Refund Agent for ABC Technologies.

Your job is to help customers with refund requests for ABC Technologies orders.

Available tools:
- get_customer_orders: find orders belonging to a customer
- get_order_details: inspect a specific order
- create_refund_request: create an actual refund request in the database

IMPORTANT:
Creating a refund request is a real action.

Rules:
- Never invent refund policies, eligibility rules, timeframes, amounts, or order information.
- If a customer ID is provided, use get_customer_orders when the customer has not
  identified a specific order.
- If the customer provides an order ID, use get_order_details first.
- Before creating a refund request, make sure the target order exists.
- Never create a refund request for an order that cannot be verified.
- Never create a duplicate active refund request.
- Use create_refund_request only when the customer has clearly requested a refund
  and the required order information and reason are available.
- If the customer has not clearly asked to initiate a refund, provide information
  and ask what they want to do.
- If a refund reason is missing when needed, ask for it.
- Clearly tell the customer when a refund request has actually been created.
- Previous conversation is context only. Never treat it as database evidence.
- Be concise, professional, and transparent.
"""


refund_agent = create_agent(
    model=llm,
    tools=[
        get_customer_orders,
        get_order_details,
    ],
    system_prompt=REFUND_SYSTEM_PROMPT,
)


def _fast_refund_response(
    user_query: str,
    customer_id: str | None = None,
    conversation_history: list[dict] | None = None,
    conversation_id: str | None = None,
) -> str | None:
    if not customer_id:
        return None

    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            return "I could not verify your customer account. Please sign in again."

        conversation = None
        if conversation_id:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == conversation_id)
            ).scalar_one_or_none()
            if conversation and conversation.customer_id != customer.id:
                return "I could not verify this conversation belongs to your account."

        request = classify_request(
            user_query,
            conversation_history or [],
            pending_action=conversation.pending_action if conversation else None,
            awaiting_confirmation=bool(conversation and conversation.awaiting_confirmation),
        )
        if request.get("domain") != "refund":
            return None

        action = request.get("action")
        normalized_query = (user_query or "").lower()
        if action == "refund_process_information":
            return (
                "To request a refund: 1. Select the order. 2. Check that it is paid and eligible under the refund policy. "
                f"The configured demonstration request window is {REFUND_WINDOW_HOURS:g} hours from order placement. "
                "3. Confirm submission. 4. Track the simulated request from your refund details; no funds are returned by this demo."
            )

        if action == "refund_status":
            refund = db.execute(
                select(Refund)
                .join(Order, Refund.order_id == Order.id)
                .where(Order.customer_id == customer.id)
                .order_by(Refund.created_at.desc())
            ).scalars().first()
            if not refund:
                return "I checked your account and could not find a refund request."
            return (
                f"Refund {_refund_display_id(refund)} for order {refund.order.order_id}: "
                f"{refund.status}. The recorded amount is ₹{refund.refund_amount:.0f}."
            )

        if action in {"refund_confirmation", "refund_reject"}:
            if not conversation or conversation.pending_action != "refund_request" or not conversation.awaiting_confirmation:
                return None
            pending_order_id = conversation.pending_order_id
            if action == "refund_reject":
                conversation.pending_action = None
                conversation.pending_order_id = None
                conversation.awaiting_confirmation = False
                conversation.pending_expires_at = None
                db.commit()
                suffix = f" for order {pending_order_id}" if pending_order_id else ""
                return f"Okay. I did not submit a refund request{suffix}."
            if not pending_order_id:
                conversation.pending_action = None
                conversation.awaiting_confirmation = False
                conversation.pending_order_id = None
                conversation.pending_expires_at = None
                db.commit()
                return "There is no pending refund request to confirm."

            explicit_confirmation_order = re.search(
                r"\b(ORD(?!ER\b)[A-Z0-9]+)\b",
                user_query or "",
                re.IGNORECASE,
            )
            if (
                explicit_confirmation_order
                and explicit_confirmation_order.group(1).upper() != pending_order_id.upper()
            ):
                return (
                    f"Your pending refund request is for order {pending_order_id}, but you mentioned "
                    f"{explicit_confirmation_order.group(1).upper()}. Please confirm which order you mean."
                )

            try:
                result = create_refund_for_customer(
                    customer_id,
                    pending_order_id,
                    "Customer confirmed a refund request.",
                )
            except Exception:
                db.rollback()
                return (
                    f"I couldn't submit the refund for order {pending_order_id} because the database operation failed. "
                    "Your request is still awaiting confirmation; please retry."
                )
            conversation.pending_action = None
            conversation.pending_order_id = None
            conversation.awaiting_confirmation = False
            conversation.pending_expires_at = None
            db.commit()
            if result.get("created"):
                return (
                    f"{result['message']} Order: {result['order_id']}. Refund ID: {result['refund_id']}. "
                    f"Amount: ₹{result['amount']:.0f}. Status: {result['status']}."
                )
            if result.get("duplicate"):
                return (
                    f"A refund request already exists for order {result['order_id']}. "
                    f"Refund ID: {result['refund_id']}. Status: {result['status']}."
                )
            return result.get("message", "The refund request could not be submitted.")

        orders = db.execute(
            select(Order)
            .where(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
        ).scalars().all()
        if not orders:
            return "I checked your account and there are no orders on file to evaluate for a refund."

        explicit_match = re.search(r"\b(ORD(?!ER\b)[A-Z0-9]+)\b", user_query or "", re.IGNORECASE)
        selected = None
        if explicit_match:
            requested_id = explicit_match.group(1).upper()
            selected = next((order for order in orders if order.order_id.upper() == requested_id), None)
            if not selected:
                exists = db.execute(select(Order.id).where(Order.order_id == requested_id)).scalar_one_or_none()
                if exists:
                    return f"Access denied. Order {requested_id} does not belong to your account."
                return f"Order {requested_id} was not found."
        elif "latest" in normalized_query and orders:
            selected = orders[0]
        elif conversation and conversation.current_order_id:
            selected = next(
                (order for order in orders if order.order_id == conversation.current_order_id),
                None,
            )
        elif len(orders) == 1:
            selected = orders[0]
        if not selected:
            order_ids = "\n".join(f"- {order.order_id}" for order in orders)
            return f"Which order would you like me to check for a refund?\n{order_ids}"

        existing_refund = db.execute(
            select(Refund)
            .where(
                Refund.order_id == selected.id,
                Refund.status.in_(ACTIVE_REFUND_STATUSES),
            )
            .order_by(Refund.created_at.desc())
        ).scalars().first()
        if existing_refund:
            return (
                f"A refund request already exists for order {selected.order_id}. "
                f"Refund ID: {_refund_display_id(existing_refund)}. Status: {existing_refund.status}."
            )

        payment = db.execute(
            select(Payment).where(Payment.order_id == selected.id)
        ).scalar_one_or_none()
        tracking = calculate_tracking(selected, payment)
        ineligibility_reason = refund_ineligibility_reason(selected, payment=payment)
        if ineligibility_reason:
            return (
                f"Order {selected.order_id} is currently {tracking['status']} and is not eligible for a refund: "
                f"{ineligibility_reason}"
            )

        if conversation:
            conversation.current_order_id = selected.order_id
            conversation.pending_action = "refund_request"
            conversation.pending_order_id = selected.order_id
            conversation.awaiting_confirmation = True
            conversation.pending_expires_at = datetime.utcnow() + timedelta(minutes=15)
            db.commit()
        return (
            f"Order {selected.order_id} is currently {tracking['status']} and is eligible for a refund. "
            f"The configured request window is {REFUND_WINDOW_HOURS:g} hours for this demonstration. "
            "Would you like me to submit this simulated refund request?"
        )
    finally:
        db.close()


def _refund_display_id(refund: Refund) -> str:
    return f"REF-{refund.id:06d}"


def handle_refund(
    user_query: str,
    customer_id: str | None = None,
    conversation_history: list[dict] | None = None,
    conversation_id: str | None = None,
) -> str:

    fast_response = _fast_refund_response(
        user_query,
        customer_id,
        conversation_history,
        conversation_id,
    )
    if fast_response:
        return fast_response

    context = ""

    if customer_id:
        context += (
            "System-provided customer context:\n"
            f"customer_id = {customer_id}\n\n"
        )

    history = conversation_history or []

    if history:
        context += "Previous conversation:\n"

        for message in history[-10:]:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            context += f"{role}: {content}\n"

        context += "\n"

    context += f"Current customer message:\n{user_query}"

    result = refund_agent.invoke({
        "messages": [
            HumanMessage(content=context)
        ]
    })

    return result["messages"][-1].content
