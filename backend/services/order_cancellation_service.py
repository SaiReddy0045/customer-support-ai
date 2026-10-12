from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Customer, Order
from config.settings import env_value

CANCELLATION_WINDOW_HOURS = float(env_value("CANCELLATION_WINDOW_HOURS", "24"))
CANCELLABLE_STATUSES = {"order confirmed", "processing", "packing", "pending", "pending payment"}
TERMINAL_STATUSES = {"shipped", "delivered", "cancelled", "refund requested", "refunded"}


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def cancellation_block_reason(order: Order, now: datetime | None = None) -> str | None:
    status = (order.order_status or "").strip().lower()
    if "cancelled" in status:
        return "already_cancelled"
    if any(terminal_status in status for terminal_status in TERMINAL_STATUSES - {"cancelled"}):
        return "terminal_status"
    if status not in CANCELLABLE_STATUSES:
        return "terminal_status"

    current_time = _utc_datetime(now or datetime.now(timezone.utc))
    created_at = _utc_datetime(order.created_at)
    if current_time - created_at >= timedelta(hours=CANCELLATION_WINDOW_HOURS):
        return "outside_window"
    return None


def cancel_order(
    db: Session,
    customer_id: str,
    order_id: str,
    now: datetime | None = None,
) -> tuple[str, Order | None]:
    customer = db.execute(
        select(Customer).where(Customer.customer_id == customer_id)
    ).scalar_one_or_none()
    if not customer:
        return "customer_not_found", None

    order = db.execute(select(Order).where(Order.order_id == order_id)).scalar_one_or_none()
    if not order:
        return "order_not_found", None
    if order.customer_id != customer.id:
        return "access_denied", None

    block_reason = cancellation_block_reason(order, now)
    if block_reason:
        return block_reason, order

    order.order_status = "Cancelled"
    db.commit()
    db.refresh(order)
    return "cancelled", order
