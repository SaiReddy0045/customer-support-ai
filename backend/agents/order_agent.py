import re
from datetime import datetime, timedelta

from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from sqlalchemy import select

from agents.intent_classifier import classify_request
from config.llm import llm
from database.db import SessionLocal
from database.models import Conversation, Customer, Order, Payment
from services.order_cancellation_service import cancellation_block_reason, cancel_order
from services.tracking_service import calculate_tracking, effective_order_status
from tools.order_tools import (
    count_customer_orders,
    get_customer_orders,
    get_latest_order,
    get_order_by_id,
    get_order_details,
    get_order_status,
    get_order_tracking,
    get_order_invoice,
    check_payment,
)


ORDER_SYSTEM_PROMPT = """
You are the Order Support Agent for ABC Technologies.

You help customers with their existing ABC Technologies orders and payments.

Available tools:
- get_customer_orders: list the customer's orders
- get_latest_order: fetch the newest order
- get_order_status: inspect one order's current status
- get_order_tracking: read the current tracking stage for one order
- get_order_by_id: inspect a specific order for a customer
- get_order_invoice: read invoice/payment summary for one order
- get_order_details: inspect a specific order in detail
- check_payment: inspect payment status and transaction information

Rules:
- Select the tool based on the requested action, not a universal latest-order fallback.
- If the user asks how many orders they have placed, count their orders.
- If the user asks to show all orders, list all orders.
- If they ask for the latest order, fetch only the latest order.
- For status or tracking questions, inspect the correct order and use current database data.
- Never invent order, payment, transaction, shipping, or delivery information.
- Previous conversation is context only and must not override database results.
- Be concise, professional, and helpful.
"""


order_agent = create_agent(
    model=llm,
    tools=[
        get_customer_orders,
        get_latest_order,
        get_order_by_id,
        get_order_status,
        get_order_tracking,
        get_order_invoice,
        get_order_details,
        count_customer_orders,
        check_payment,
    ],
    system_prompt=ORDER_SYSTEM_PROMPT,
)

CONVERSATION_ORDER_MEMORY: dict[str, str] = {}


def _extract_order_ids_from_history(conversation_history: list[dict] | None) -> list[str]:
    ids: list[str] = []
    for message in conversation_history or []:
        content = str(message.get("content", "") or "")
        ids.extend(match.upper() for match in re.findall(r"\bORD(?!ER\b)[A-Z0-9]+\b", content, flags=re.IGNORECASE))
    return ids


def _get_current_order_id_from_history(conversation_history: list[dict] | None, orders: list[Order] | None = None) -> str | None:
    explicit_match = None
    for message in reversed(conversation_history or []):
        content = str(message.get("content", "") or "")
        explicit = re.search(r"current_order_id\s*=\s*(ORD(?!ER\b)[A-Z0-9]+)", content, flags=re.IGNORECASE)
        if explicit:
            return explicit.group(1).upper()

    last_order_list = []
    for message in reversed(conversation_history or []):
        content = str(message.get("content", "") or "")
        ids = re.findall(r"\bORD(?!ER\b)[A-Z0-9]+\b", content, flags=re.IGNORECASE)
        if ids:
            last_order_list = [item.upper() for item in ids]
            break

    if last_order_list:
        if orders:
            for order in orders:
                if order.order_id.upper() == last_order_list[0]:
                    return order.order_id.upper()
        return last_order_list[0].upper()

    if orders and len(orders) == 1:
        return orders[0].order_id.upper()
    return None


def _resolve_contextual_order(customer_id: str, orders: list[Order], user_query: str, conversation_history: list[dict] | None = None, conversation_id: str | None = None) -> Order | None:
    text = (user_query or "").lower()
    current_order_id = CONVERSATION_ORDER_MEMORY.get(conversation_id or "") if conversation_id else None
    if not current_order_id:
        current_order_id = _get_current_order_id_from_history(conversation_history, orders)

    if "other order" in text or "another order" in text or "other one" in text:
        if current_order_id:
            candidates = [order for order in orders if order.order_id.upper() != current_order_id]
            if len(candidates) == 1:
                return candidates[0]
            if len(candidates) > 1:
                return None
        if len(orders) > 1:
            return None
        return orders[0] if orders else None

    if "this order" in text or "that order" in text or "this" in text or "that" in text or "it" in text:
        if current_order_id:
            for order in orders:
                if order.order_id.upper() == current_order_id:
                    return order
        if len(orders) >= 1:
            return orders[0]

    if "second order" in text or "order number 2" in text:
        if len(orders) >= 2:
            return orders[1]
    if "first order" in text or "order number 1" in text or "previous order" in text or "earlier order" in text:
        if len(orders) >= 1:
            return orders[-1]
    if "latest order" in text or "last order" in text:
        return orders[0]

    if "order number" in text:
        match = re.search(r"order number\s+(\d+)", text)
        if match:
            n = int(match.group(1))
            if 1 <= n <= len(orders):
                return orders[n - 1]

    if current_order_id:
        return next(
            (order for order in orders if order.order_id.upper() == current_order_id),
            None,
        )
    if len(orders) == 1:
        return orders[0]
    return None


def _select_order_for_query(customer_id: str, orders: list[Order], user_query: str, conversation_history: list[dict] | None = None, conversation_id: str | None = None) -> Order | None:
    return _resolve_contextual_order(customer_id, orders, user_query, conversation_history, conversation_id)


def _fast_order_response(user_query: str, customer_id: str | None = None, conversation_history: list[dict] | None = None, conversation_id: str | None = None) -> str | None:
    if not customer_id:
        return None
    db = SessionLocal()
    try:
        conversation = None
        if conversation_id:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == conversation_id)
            ).scalar_one_or_none()
        if conversation and conversation.current_order_id:
            CONVERSATION_ORDER_MEMORY[conversation_id] = conversation.current_order_id

        request = classify_request(
            user_query,
            conversation_history or [],
            pending_action=conversation.pending_action if conversation else None,
            awaiting_confirmation=bool(conversation and conversation.awaiting_confirmation),
        )
        if request.get("domain") != "order":
            return None

        action = request.get("action", "track")
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            return f"I could not find customer {customer_id}. Please confirm your customer ID so I can look up the correct order history."

        orders = db.execute(
            select(Order)
            .where(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
        ).scalars().all()

        if action in {"cancel_confirmation", "cancel_reject"}:
            if not conversation or conversation.pending_action != "cancel_order" or not conversation.awaiting_confirmation:
                return None
            pending_order_id = conversation.pending_order_id
            if not pending_order_id:
                conversation.pending_action = None
                conversation.pending_order_id = None
                conversation.awaiting_confirmation = False
                conversation.pending_expires_at = None
                db.commit()
                return "There is no pending cancellation to confirm."
            if action == "cancel_reject":
                conversation.pending_action = None
                conversation.pending_order_id = None
                conversation.awaiting_confirmation = False
                conversation.pending_expires_at = None
                db.commit()
                return f"Okay. Order {pending_order_id} was not cancelled."

            result, cancelled_order = cancel_order(db, customer_id, pending_order_id)
            conversation.pending_action = None
            conversation.pending_order_id = None
            conversation.awaiting_confirmation = False
            conversation.pending_expires_at = None
            db.commit()
            if result == "cancelled" and cancelled_order:
                return (
                    f"Order {cancelled_order.order_id} has been cancelled successfully. "
                    f"Current status: {cancelled_order.order_status}."
                )
            if result == "already_cancelled":
                return f"Order {pending_order_id} is already cancelled."
            if result == "outside_window":
                return f"Order {pending_order_id} was placed more than 24 hours ago and is no longer eligible for cancellation."
            if result == "terminal_status":
                return f"Order {pending_order_id} has status {cancelled_order.order_status if cancelled_order else 'that status'} and is no longer eligible for cancellation."
            return f"Order {pending_order_id} could not be cancelled. Please verify the order and try again."
        if not orders and action not in {"cancel", "cancellation_eligibility"}:
            return f"I checked customer {customer_id} and there are no orders on file."

        if action == "count_orders":
            return f"You have placed {len(orders)} orders."

        if action == "list_orders":
            summary = "\n".join(
                f"- {order.order_id}: {effective_order_status(order, order.payment)} · ₹{order.total_amount:.0f} · {order.created_at.date()}"
                for order in orders
            )
            if conversation_id:
                CONVERSATION_ORDER_MEMORY[conversation_id] = orders[0].order_id
            if conversation:
                conversation.current_order_id = orders[0].order_id
                db.commit()
            return f"Here are your orders for {customer_id}:\n{summary}"

        if action == "latest_order":
            latest = orders[0]
            latest_tracking = calculate_tracking(latest, latest.payment)
            if conversation_id:
                CONVERSATION_ORDER_MEMORY[conversation_id] = latest.order_id
            if conversation:
                conversation.current_order_id = latest.order_id
                db.commit()
            return (
                f"Your latest order is {latest.order_id}. "
                f"Its current status is {latest_tracking['status']}. "
                f"Amount: ₹{latest.total_amount:.0f}."
            )

        if action in {"track", "order_status", "delivery_eta", "delivery_delay"}:
            explicit_match = re.search(
                r"\b(ORD(?!ER\b)-?[A-Z0-9]+)\b",
                user_query,
                flags=re.IGNORECASE,
            )
            if explicit_match:
                requested_order_id = explicit_match.group(1).replace("-", "").upper()
                selected = db.execute(
                    select(Order).where(Order.order_id == requested_order_id)
                ).scalar_one_or_none()
                if selected is None:
                    exists = db.execute(
                        select(Order.id).where(Order.order_id == requested_order_id)
                    ).scalar_one_or_none()
                    if exists:
                        return f"I could not find order {explicit_match.group(1).upper()} in customer {customer_id}'s account."
                    return f"Order {explicit_match.group(1).upper()} was not found in customer {customer_id}'s account."
                if selected.customer_id != customer.id:
                    return (
                        f"Order {explicit_match.group(1).upper()} was not found "
                        f"in customer {customer_id}'s account."
                    )
            else:
                selected = _select_order_for_query(customer_id, orders, user_query, conversation_history, conversation_id)
            if conversation_id:
                CONVERSATION_ORDER_MEMORY[conversation_id] = selected.order_id
            if conversation:
                conversation.current_order_id = selected.order_id
                db.commit()
            tracking = calculate_tracking(selected, selected.payment)
            if action == "delivery_delay":
                next_stage = next(
                    (stage["name"] for stage in tracking["stages"] if not stage["completed"] and not stage["current"]),
                    None,
                )
                next_stage_message = (
                    f" The next simulated stage is {next_stage}; these stages are a demo timeline, not a delivery guarantee."
                    if next_stage else " This is the final recorded delivery stage."
                )
                return (
                    f"I checked the tracking timeline for {selected.order_id}. "
                    f"It is currently at {tracking['status']}. "
                    f"This status is derived from the order and payment records."
                    f"{next_stage_message}"
                )
            if action == "delivery_eta":
                return (
                    f"Your order {selected.order_id} is currently {tracking['status']}. "
                    f"The expected delivery window is based on the current tracking stage in the system."
                )
            return (
                f"Your order {selected.order_id} is currently {tracking['status']}. "
                f"Tracking stage: {tracking['status']}."
            )

        if action in {"cancel", "cancellation_eligibility"}:
            explicit_match = re.search(
                r"\b(ORD(?!ER\b)-?[A-Z0-9]+)\b",
                user_query,
                flags=re.IGNORECASE,
            )
            if explicit_match:
                requested_order_id = explicit_match.group(1).replace("-", "").upper()
                selected = db.execute(
                    select(Order).where(Order.order_id == requested_order_id)
                ).scalar_one_or_none()
                if selected is None:
                    return f"Order {requested_order_id} was not found."
                if selected.customer_id != customer.id:
                    return f"Access denied. Order {requested_order_id} does not belong to your account."
            else:
                selected = _select_order_for_query(customer_id, orders, user_query, conversation_history, conversation_id)
                normalized_query = (user_query or "").lower()
                if any(phrase in normalized_query for phrase in ("other order", "another order", "other one")):
                    current_order_id = (
                        conversation.current_order_id
                        if conversation and conversation.current_order_id
                        else CONVERSATION_ORDER_MEMORY.get(conversation_id or "")
                    )
                    alternatives = [
                        order for order in orders
                        if order.order_id != current_order_id
                        and cancellation_block_reason(order) is None
                    ]
                    if len(alternatives) == 1:
                        selected = alternatives[0]
                    elif len(alternatives) > 1:
                        options = "\n".join(f"- {order.order_id}" for order in alternatives)
                        return f"Which other order would you like to cancel?\n{options}"
                if not explicit_match and "cancel my order" in normalized_query and not any(
                    term in normalized_query for term in ("that", "this", "it", "other", "another")
                ):
                    eligible_orders = [order for order in orders if cancellation_block_reason(order) is None]
                    if len(eligible_orders) == 1:
                        selected = eligible_orders[0]
                    elif len(eligible_orders) > 1:
                        options = "\n".join(f"- {order.order_id}" for order in eligible_orders)
                        return f"Which order would you like to cancel?\n{options}"
                    elif eligible_orders == [] and orders:
                        selected = orders[0]
            if selected is None:
                candidates = [order for order in orders if cancellation_block_reason(order) is None]
                options = "\n".join(f"- {order.order_id}" for order in candidates or orders)
                if not options:
                    return "I could not find an order in your account to check."
                question = "Which order would you like me to check?" if action == "cancellation_eligibility" else "Which order do you want to cancel?"
                return f"{question}\n{options}"
            if conversation_id:
                CONVERSATION_ORDER_MEMORY[conversation_id] = selected.order_id
            if conversation:
                conversation.current_order_id = selected.order_id
            block_reason = cancellation_block_reason(selected)
            if block_reason == "already_cancelled":
                return f"Order {selected.order_id} is already cancelled."
            if block_reason == "outside_window":
                return f"Order {selected.order_id} was placed more than 24 hours ago and is no longer eligible for cancellation."
            if block_reason == "terminal_status":
                return f"Order {selected.order_id} has status {selected.order_status} and is no longer eligible for cancellation."
            if action == "cancellation_eligibility":
                if conversation:
                    conversation.pending_action = "cancel_order"
                    conversation.pending_order_id = selected.order_id
                    conversation.awaiting_confirmation = True
                    conversation.pending_expires_at = datetime.utcnow() + timedelta(minutes=15)
                    db.commit()
                return (
                    f"Order {selected.order_id} is eligible for cancellation. "
                    "Reply 'yes, cancel it' to proceed."
                )

            result, cancelled_order = cancel_order(db, customer_id, selected.order_id)
            if conversation:
                conversation.pending_action = None
                conversation.pending_order_id = None
                conversation.awaiting_confirmation = False
                conversation.pending_expires_at = None
                db.commit()
            if result == "cancelled" and cancelled_order:
                return (
                    f"Order {cancelled_order.order_id} has been cancelled successfully. "
                    f"Current status: {cancelled_order.order_status}."
                )
            if result == "already_cancelled":
                return f"Order {selected.order_id} is already cancelled."
            if result == "outside_window":
                return f"Order {selected.order_id} was placed more than 24 hours ago and is no longer eligible for cancellation."
            if result == "terminal_status":
                return f"Order {selected.order_id} has status {cancelled_order.order_status if cancelled_order else 'that status'} and is no longer eligible for cancellation."
            if result == "access_denied":
                return f"Access denied. Order {selected.order_id} does not belong to your account."
            return f"Order {selected.order_id} could not be cancelled. Please verify the order and try again."

        if action == "cancellation_status":
            selected = _select_order_for_query(customer_id, orders, user_query, conversation_history, conversation_id)
            if conversation_id:
                CONVERSATION_ORDER_MEMORY[conversation_id] = selected.order_id
            return (
                f"I checked order {selected.order_id}. Its current status is {effective_order_status(selected, selected.payment)}. "
                "The status is based on the current order and payment records."
            )

        if action == "order_details":
            selected = _select_order_for_query(customer_id, orders, user_query, conversation_history, conversation_id)
            if conversation_id:
                CONVERSATION_ORDER_MEMORY[conversation_id] = selected.order_id
            return (
                f"Order {selected.order_id}: {effective_order_status(selected, selected.payment)} • ₹{selected.total_amount:.0f} • {selected.created_at.date()}"
            )

        if action == "order_invoice":
            selected = _select_order_for_query(customer_id, orders, user_query, conversation_history, conversation_id)
            if conversation_id:
                CONVERSATION_ORDER_MEMORY[conversation_id] = selected.order_id
            payment = db.execute(select(Payment).where(Payment.order_id == selected.id)).scalar_one_or_none()
            payment_line = "No payment record found." if not payment else f"Payment status: {payment.payment_status} · ₹{payment.amount:.0f}"
            return f"Invoice for {selected.order_id}: Amount ₹{selected.total_amount:.0f}. {payment_line}"

        return None
    finally:
        db.close()


def handle_order(
    user_query: str,
    customer_id: str | None = None,
    conversation_history: list[dict] | None = None,
    conversation_id: str | None = None,
) -> str:

    fast_response = _fast_order_response(user_query, customer_id, conversation_history, conversation_id)
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

    result = order_agent.invoke({
        "messages": [
            HumanMessage(content=context)
        ]
    })

    return result["messages"][-1].content
