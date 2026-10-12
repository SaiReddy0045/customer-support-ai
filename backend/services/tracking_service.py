from datetime import datetime, timedelta, timezone
from config.settings import env_value


TRACKING_STAGES = (
    "Order Confirmed",
    "Packing",
    "Shipped",
    "Near Location",
    "Delivered",
)
TRACKING_MINUTES_ORDER_CONFIRMED = int(env_value("TRACKING_CONFIRMED_MINUTES", "30"))
TRACKING_HOURS_PACKING = int(env_value("TRACKING_PACKING_HOURS", "24"))
TRACKING_HOURS_SHIPPED = int(env_value("TRACKING_SHIPPED_HOURS", "36"))
TRACKING_HOURS_NEAR_LOCATION = int(env_value("TRACKING_NEAR_LOCATION_HOURS", "48"))
REFUND_WINDOW_HOURS = float(env_value("REFUND_WINDOW_HOURS", "12"))

TERMINAL_ORDER_STATUSES = {
    "cancelled",
    "delivered",
    "refund requested",
    "refund approved",
    "refunded",
    "refund completed",
    "refund processing",
    "refund rejected",
}
SUCCESSFUL_PAYMENT_STATUSES = {
    "paid",
    "payment successful",
    "success",
    "succeeded",
    "completed",
}
PENDING_PAYMENT_STATUSES = {"pending", "pending payment", "payment pending"}
FAILED_PAYMENT_STATUSES = {"failed", "payment failed", "declined"}


def payment_is_successful(payment) -> bool:
    return bool(
        payment
        and (payment.payment_status or "").strip().lower() in SUCCESSFUL_PAYMENT_STATUSES
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def effective_order_status(order, payment=None, now: datetime | None = None) -> str:
    """Return the canonical order status from persisted state and the demo lifecycle."""
    stored_status = (order.order_status or "").strip()
    normalized_status = stored_status.lower().replace("_", " ")
    payment = payment if payment is not None else getattr(order, "payment", None)
    payment_status = (getattr(payment, "payment_status", "") or "").strip().lower()
    active_refund_statuses = {"refund_requested", "refund_approved", "refund_processing", "requested", "approved", "processing"}
    refunds = getattr(order, "refunds", None) or []
    if any((refund.status or "").strip().lower() in active_refund_statuses for refund in refunds):
        return "Refund Requested"
    if any((refund.status or "").strip().lower() == "refunded" for refund in refunds):
        return "Refunded"

    non_delivery_terminal_states = TERMINAL_ORDER_STATUSES - {"delivered"}
    if any(terminal in normalized_status for terminal in non_delivery_terminal_states):
        if "cancelled" in normalized_status:
            return "Cancelled"
        if any(status in normalized_status for status in ("refund requested", "refund approved", "refund processing")):
            return "Refund Requested"
        if "refunded" in normalized_status or "refund completed" in normalized_status:
            return "Refunded"
        if "refund rejected" in normalized_status:
            return "Refund Rejected"
        return stored_status
    if payment_status in PENDING_PAYMENT_STATUSES:
        return "Pending Payment"
    if payment_status in FAILED_PAYMENT_STATUSES:
        return "Payment Failed"
    if not payment_is_successful(payment):
        return "Pending Payment"

    lifecycle_eligible_statuses = {
        "payment successful",
        "pending payment",
        "order confirmed",
        "processing",
        "packing",
        "shipped",
        "near your location",
        "delivered",
        "order delivered",
        "near location",
        "near your location",
    }
    if normalized_status not in lifecycle_eligible_statuses:
        return stored_status or "Pending Payment"

    created_at = _as_utc(order.created_at or datetime.now(timezone.utc))
    current_time = _as_utc(now or datetime.now(timezone.utc))
    age = max(current_time - created_at, timedelta(0))
    if age <= timedelta(minutes=TRACKING_MINUTES_ORDER_CONFIRMED):
        return "Order Confirmed"
    if age <= timedelta(hours=TRACKING_HOURS_PACKING):
        return "Packing"
    if age <= timedelta(hours=TRACKING_HOURS_SHIPPED):
        return "Shipped"
    if age < timedelta(hours=TRACKING_HOURS_NEAR_LOCATION):
        return "Near Location"
    return "Delivered"


def calculate_tracking(order, payment=None, now: datetime | None = None) -> dict:
    """Build tracking details while keeping delivery, order, payment, and refund states separate."""
    created_at = order.created_at or datetime.utcnow()
    order_status = effective_order_status(order, payment, now)
    payment = payment if payment is not None else getattr(order, "payment", None)
    payment_status = getattr(payment, "payment_status", None)
    refunds = getattr(order, "refunds", None) or []
    refund_status = next(
        (refund.status for refund in reversed(refunds) if getattr(refund, "status", None)),
        None,
    )

    if order_status in {"Pending Payment", "Payment Failed", "Cancelled"}:
        delivery_stage = order_status
    else:
        created_at_utc = _as_utc(created_at)
        current_time = _as_utc(now or datetime.now(timezone.utc))
        age = max(current_time - created_at_utc, timedelta(0))
        if age <= timedelta(minutes=TRACKING_MINUTES_ORDER_CONFIRMED):
            delivery_stage = "Order Confirmed"
        elif age <= timedelta(hours=TRACKING_HOURS_PACKING):
            delivery_stage = "Packing"
        elif age <= timedelta(hours=TRACKING_HOURS_SHIPPED):
            delivery_stage = "Shipped"
        elif age < timedelta(hours=TRACKING_HOURS_NEAR_LOCATION):
            delivery_stage = "Near Location"
        else:
            delivery_stage = "Delivered"

    lifecycle_stage = next(
        (index for index, stage_name in enumerate(TRACKING_STAGES) if stage_name == delivery_stage),
        None,
    )
    stage = lifecycle_stage if lifecycle_stage is not None else -1

    stages = [
        {
            "name": name,
            "completed": lifecycle_stage is not None and index < stage,
            "current": index == stage,
        }
        for index, name in enumerate(TRACKING_STAGES)
    ]

    return {
        "order_id": order.order_id,
        "status": delivery_stage,
        "delivery_stage": delivery_stage,
        "order_status": order_status,
        "payment_status": payment_status,
        "refund_status": refund_status,
        "stage": stage + 1 if stage >= 0 else 0,
        "stages": stages,
        "created_at": created_at.isoformat(),
        "delivery_period_hours": 48,
    }


def refund_status_is_final(status: str | None) -> bool:
    return status in {"REFUNDED", "REFUND_COMPLETED", "REFUND_REJECTED", "REFUND_CANCELLED", "Refunded", "Refund Completed"}


def refund_ineligibility_reason(order, refund_status: str | None = None, payment=None, now: datetime | None = None) -> str | None:
    if refund_status and not refund_status_is_final(refund_status):
        return "A refund request is already active for this order."
    if refund_status and refund_status.strip().upper() == "REFUNDED":
        return "This order has already been refunded."
    payment = payment if payment is not None else getattr(order, "payment", None)
    if not payment_is_successful(payment):
        return "A successful payment record is required."
    order_status = (order.order_status or "").strip().lower().replace("_", " ")
    if any(terminal in order_status for terminal in TERMINAL_ORDER_STATUSES):
        return f"The current order status is {order.order_status} and does not permit a refund request."
    existing_refunds = getattr(order, "refunds", None) or []
    if any((refund.status or "").strip().lower().replace("_", " ") in {"refunded", "refund completed"} for refund in existing_refunds):
        return "This order already has a completed refund."
    if any((refund.status or "").strip().lower().replace("_", " ") in {"refund requested", "refund approved", "refund processing", "requested", "approved", "processing"} for refund in existing_refunds):
        return "A refund request is already active for this order."
    created_at = _as_utc(order.created_at or datetime.now(timezone.utc))
    current_time = _as_utc(now or datetime.now(timezone.utc))
    age = current_time - created_at
    if age < timedelta(0):
        return "The order timestamp is in the future and cannot be evaluated for a refund."
    if age >= timedelta(hours=REFUND_WINDOW_HOURS):
        return f"The configured {REFUND_WINDOW_HOURS:g}-hour refund-request window has passed."
    return None


def refund_is_eligible(order, refund_status: str | None = None, payment=None, now: datetime | None = None) -> bool:
    return refund_ineligibility_reason(order, refund_status, payment, now) is None
