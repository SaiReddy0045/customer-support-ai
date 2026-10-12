from langchain_core.tools import tool
from sqlalchemy import select

from database.db import SessionLocal
from database.models import Customer, Order, Payment, Refund
from services.tracking_service import calculate_tracking, refund_ineligibility_reason


def _refund_id(refund: Refund) -> str:
    return f"REF-{refund.id:06d}"

ACTIVE_REFUND_STATUSES = (
    "REFUND_REQUESTED",
    "REFUND_APPROVED",
    "REFUND_PROCESSING",
    "REFUND_COMPLETED",
    "Requested",
    "Approved",
    "Processing",
    "Completed",
    "Refund Requested",
    "Refund Approved",
    "Refund Completed",
)


def create_refund_for_customer(
    customer_id: str,
    order_id: str,
    reason: str,
) -> dict:
    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        order = db.execute(
            select(Order).where(Order.order_id == order_id)
        ).scalar_one_or_none()

        if not customer or not order or order.customer_id != customer.id:
            return {"ok": False, "message": "Sorry, I couldn't find that order in your account."}

        existing_refund = db.execute(
            select(Refund)
            .where(
                Refund.order_id == order.id,
                Refund.status.in_(ACTIVE_REFUND_STATUSES),
            )
        ).scalar_one_or_none()
        if existing_refund:
            return {
                "ok": True,
                "duplicate": True,
                "refund_id": _refund_id(existing_refund),
                "order_id": order.order_id,
                "amount": existing_refund.refund_amount,
                "status": existing_refund.status,
                "message": "A refund request already exists for this order.",
            }

        payment = db.execute(
            select(Payment).where(Payment.order_id == order.id)
        ).scalar_one_or_none()
        tracking = calculate_tracking(order, payment)
        ineligibility_reason = refund_ineligibility_reason(order, payment=payment)
        if ineligibility_reason:
            return {
                "ok": False,
                "eligible": False,
                "order_id": order.order_id,
                "status": tracking["status"],
                "message": f"Order {order.order_id} is currently {tracking['status']} and is not eligible: {ineligibility_reason}",
            }

        refund = Refund(
            order_id=order.id,
            refund_amount=order.total_amount,
            reason=reason or "Customer requested a refund.",
            status="REFUND_REQUESTED",
        )
        order.order_status = "Refund Requested"
        db.add(refund)
        db.flush()
        db.commit()
        db.refresh(refund)

        return {
            "ok": True,
            "created": True,
            "refund_id": _refund_id(refund),
            "order_id": order.order_id,
            "amount": refund.refund_amount,
            "status": refund.status,
            "message": "Your simulated refund request has been recorded. No money has been returned by this demo.",
        }
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@tool
def create_refund_request(
    customer_id: str,
    order_id: str,
    reason: str,
) -> str:
    """
    Create a refund request for an existing ABC Technologies order.

    The tool validates that the order exists and prevents creating
    a duplicate active refund request.
    """

    db = SessionLocal()

    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        order = db.execute(
            select(Order).where(Order.order_id == order_id)
        ).scalar_one_or_none()

        if not customer or not order or order.customer_id != customer.id:
            return f"No order {order_id} was found in customer {customer_id}'s account."

        existing_refund = db.execute(
            select(Refund)
            .where(
                Refund.order_id == order.id,
                Refund.status.in_(ACTIVE_REFUND_STATUSES),
            )
        ).scalar_one_or_none()

        if existing_refund:
            return (
                f"A refund request already exists for order "
                f"{order_id}. Current refund status: "
                f"{existing_refund.status}."
            )

        payment = db.execute(
            select(Payment).where(Payment.order_id == order.id)
        ).scalar_one_or_none()
        ineligibility_reason = refund_ineligibility_reason(order, payment=payment)
        if ineligibility_reason:
            return (
                f"Order {order_id} is currently {calculate_tracking(order, payment)['status']} and is not eligible: {ineligibility_reason}"
            )

        refund = Refund(
            order_id=order.id,
            refund_amount=order.total_amount,
            reason=reason,
            status="REFUND_REQUESTED",
        )

        order.order_status = "Refund Requested"

        db.add(refund)
        db.commit()
        db.refresh(refund)

        return (
            f"Refund request created successfully.\n"
            f"Order ID: {order.order_id}\n"
            f"Refund Amount: ₹{refund.refund_amount:.0f}\n"
            f"Reason: {refund.reason}\n"
            f"Refund ID: {_refund_id(refund)}\n"
            f"Refund Status: {refund.status}"
        )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()

