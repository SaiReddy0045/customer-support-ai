from langchain_core.messages import HumanMessage
from langchain.agents import create_agent
from sqlalchemy import select

from config.llm import llm
from database.db import SessionLocal
from database.models import Customer, Order, Payment
from tools.order_tools import (
    get_customer_orders,
    get_order_details,
    check_payment,
)

BILLING_SYSTEM_PROMPT = """
You are the Billing Agent for ABC Technologies.

Your job is to help customers with billing, payments, invoices, charges,
duplicate charges, and payment-related questions.

Available tools:
- get_customer_orders: find orders belonging to a customer
- get_order_details: inspect an order and its payment information
- check_payment: inspect payment status and transaction information

Rules:
- Use the tools whenever the customer asks about an actual order,
  payment, charge, transaction, or billing record.
- If a customer ID is provided and the customer has not specified an order,
  use get_customer_orders to identify their orders.
- If an order ID is provided, use get_order_details or check_payment.
- Never invent payment status, transaction IDs, amounts, invoices,
  billing policies, or refund information.
- For duplicate-charge questions, verify the actual payment information
  before giving a conclusion.
- If the available database information is insufficient, clearly say so
  and ask for the specific missing information.
- Never claim that a duplicate charge has been confirmed unless the
  available data supports that conclusion.
- Previous conversation is context only. Never treat it as database evidence.
- Be concise, professional, and transparent.
"""

billing_agent = create_agent(
    model=llm,
    tools=[
        get_customer_orders,
        get_order_details,
        check_payment,
    ],
    system_prompt=BILLING_SYSTEM_PROMPT,
)


def _fast_billing_response(user_query: str, customer_id: str | None = None) -> str | None:
    text = (user_query or "").lower()
    billing_terms = (
        "why was i charged",
        "why did i get charged",
        "why was i charged for this order",
        "why is there a payment",
        "what happened to my payment",
        "payment status",
        "show my payment",
        "why did you charge me",
        "payment failed",
        "charge",
        "charged",
        "payment",
        "billing",
        "transaction",
        "invoice",
    )
    duplicate_charge_terms = (
        "charged twice",
        "double charged",
        "duplicate charge",
        "charged more than once",
        "charged twice for",
        "two charges",
        "i have been charged twice",
        "was i charged twice",
    )

    if not customer_id:
        if any(term in text for term in billing_terms):
            return "I can verify that from your payment records once I have your customer ID."
        return None

    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()

        if not customer:
            return f"I could not find a customer record for {customer_id}. Please confirm the ID and I’ll verify the payment history."

        orders = db.execute(
            select(Order)
            .where(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
        ).scalars().all()

        if not orders:
            return f"I checked the records for {customer_id}, and there are no recent orders or payment records to verify."

        payment_records = []
        for order in orders:
            payment = db.execute(
                select(Payment).where(Payment.order_id == order.id)
            ).scalar_one_or_none()
            if payment:
                payment_records.append({
                    "order_id": order.order_id,
                    "status": payment.payment_status,
                    "method": payment.payment_method,
                    "amount": payment.amount,
                    "transaction_id": payment.transaction_id,
                })

        if not payment_records:
            return "I checked the payment records and there are no matching payment entries for this customer yet."

        if any(term in text for term in duplicate_charge_terms):
            duplicate_records = []
            seen = set()
            for entry in payment_records:
                key = (entry["order_id"], round(entry["amount"], 2))
                if key in seen:
                    duplicate_records.append(entry)
                seen.add(key)

            if duplicate_records:
                evidence = payment_records[:3]
                return (
                    "Yes, I found duplicate payment records for this customer. "
                    + "\n".join(
                        f"- Order {entry['order_id']}: {entry['status']} via {entry['method']} · ₹{entry['amount']:.0f} · {entry['transaction_id']}"
                        for entry in evidence
                    )
                    + "\nThe duplicate charge has been detected from the stored payment records."
                )
            return (
                "I checked your payment records and found no duplicate charge for your account. "
                "The available payments belong to separate order records."
            )

        summary = "\n".join(
            f"- Order {entry['order_id']}: {entry['status']} via {entry['method']} · ₹{entry['amount']:.0f} · {entry['transaction_id']}"
            for entry in payment_records[:3]
        )
        return (
            f"I checked your recent payment records for {customer_id}:\n{summary}\n"
            "This is based on the payment records currently available in the account."
        )
    finally:
        db.close()


def handle_billing(
    user_query: str,
    customer_id: str | None = None,
    conversation_history: list[dict] | None = None,
) -> str:

    fast_response = _fast_billing_response(user_query, customer_id)
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

    result = billing_agent.invoke({
        "messages": [
            HumanMessage(content=context)
        ]
    })

    return result["messages"][-1].content
