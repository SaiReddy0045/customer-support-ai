from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Customer, Order, SupportTicket


def create_support_ticket(
    db: Session,
    customer_id: str,
    category: str,
    description: str,
    order_id: str | None = None,
    conversation_id: str | None = None,
) -> SupportTicket:
    customer = db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    ).scalar_one_or_none()
    if not customer:
        raise LookupError("Customer not found.")
    if order_id:
        order = db.execute(select(Order).where(Order.order_id == order_id)).scalar_one_or_none()
        if not order or order.customer_id != customer.id:
            raise LookupError("Order was not found in this customer account.")

    if conversation_id:
        existing = db.execute(
            select(SupportTicket).where(
                SupportTicket.customer_id == customer.id,
                SupportTicket.conversation_id == conversation_id,
                SupportTicket.status == "OPEN",
            )
        ).scalar_one_or_none()
        if existing:
            return existing

    ticket = SupportTicket(
        ticket_id=f"TKT-{uuid4().hex[:10].upper()}",
        customer_id=customer.id,
        category=category.strip()[:80] or "General Support",
        description=description.strip()[:4000],
        order_id=order_id,
        conversation_id=conversation_id,
        status="OPEN",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


def ticket_to_dict(ticket: SupportTicket) -> dict:
    return {
        "ticketId": ticket.ticket_id,
        "category": ticket.category,
        "description": ticket.description,
        "orderId": ticket.order_id,
        "status": ticket.status,
        "createdAt": ticket.created_at.isoformat(),
        "demo": True,
    }


def get_support_ticket_for_customer(
    db: Session,
    customer_id: str,
    ticket_id: str,
) -> SupportTicket | None:
    return db.execute(
        select(SupportTicket)
        .join(Customer, SupportTicket.customer_id == Customer.id)
        .where(
            SupportTicket.ticket_id == ticket_id,
            Customer.customer_id == customer_id,
        )
    ).scalar_one_or_none()
