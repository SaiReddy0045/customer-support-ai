from typing import Optional

from langchain_core.tools import tool
from sqlalchemy import select

from database.db import SessionLocal
from database.models import (
    Customer,
    Order,
    OrderItem,
    Payment,
    Product,
)
from services.tracking_service import calculate_tracking, effective_order_status


@tool
def get_customer_orders(customer_id: str) -> str:
    """Retrieve all orders for a customer."""

    db = SessionLocal()

    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()

        if not customer:
            return f"No customer was found with customer ID {customer_id}."

        orders = db.execute(
            select(Order)
            .where(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
        ).scalars().all()

        if not orders:
            return f"No orders were found for customer {customer_id}."

        results = []
        for order in orders:
            results.append(
                f"Order ID: {order.order_id}\n"
                f"Status: {effective_order_status(order, order.payment)}\n"
                f"Total: ₹{order.total_amount:.0f}\n"
                f"Created: {order.created_at.date()}"
            )
        return "\n\n".join(results)
    finally:
        db.close()


@tool
def count_customer_orders(customer_id: str) -> str:
    """Return the total number of orders belonging to a customer."""
    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            return f"No customer was found with customer ID {customer_id}."
        count = db.execute(
            select(Order).where(Order.customer_id == customer.id)
        ).scalars().count()
        return f"Customer {customer_id} has placed {count} order(s)."
    finally:
        db.close()


@tool
def get_latest_order(customer_id: str) -> str:
    """Retrieve the newest order for a customer."""
    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            return f"No customer was found with customer ID {customer_id}."
        order = db.execute(
            select(Order)
            .where(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
            .limit(1)
        ).scalar_one_or_none()
        if not order:
            return f"No orders were found for customer {customer_id}."
        payment = db.execute(select(Payment).where(Payment.order_id == order.id)).scalar_one_or_none()
        tracking = calculate_tracking(order, payment)
        return (
            f"Latest order: {order.order_id}\n"
            f"Status: {tracking['status']}\n"
            f"Amount: ₹{order.total_amount:.0f}\n"
            f"Created: {order.created_at.date()}"
        )
    finally:
        db.close()


@tool
def get_order_by_id(customer_id: str, order_id: str) -> str:
    """Fetch a specific order for a customer."""
    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            return f"No customer was found with customer ID {customer_id}."
        order = db.execute(
            select(Order).where(Order.order_id == order_id, Order.customer_id == customer.id)
        ).scalar_one_or_none()
        if not order:
            return f"No order {order_id} was found for customer {customer_id}."
        payment = db.execute(select(Payment).where(Payment.order_id == order.id)).scalar_one_or_none()
        tracking = calculate_tracking(order, payment)
        return (
            f"Order ID: {order.order_id}\n"
            f"Status: {tracking['status']}\n"
            f"Total: ₹{order.total_amount:.0f}\n"
            f"Created: {order.created_at.date()}"
        )
    finally:
        db.close()


@tool
def get_order_status(customer_id: str, order_id: str) -> str:
    """Return the order status for a specific order."""
    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            return f"No customer was found with customer ID {customer_id}."
        order = db.execute(
            select(Order).where(Order.order_id == order_id, Order.customer_id == customer.id)
        ).scalar_one_or_none()
        if not order:
            return f"No order {order_id} was found for customer {customer_id}."
        return f"Order {order.order_id} is currently {effective_order_status(order, order.payment)}."
    finally:
        db.close()


@tool
def get_order_tracking(customer_id: str, order_id: str) -> str:
    """Return the tracking status for a specific order."""
    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            return f"No customer was found with customer ID {customer_id}."
        order = db.execute(
            select(Order).where(Order.order_id == order_id, Order.customer_id == customer.id)
        ).scalar_one_or_none()
        if not order:
            return f"No order {order_id} was found for customer {customer_id}."
        payment = db.execute(select(Payment).where(Payment.order_id == order.id)).scalar_one_or_none()
        tracking = calculate_tracking(order, payment)
        return (
            f"Order {order.order_id}\n"
            f"Tracking status: {tracking['status']}\n"
            f"Stage: {tracking['stage']}\n"
            f"Delivery period: {tracking['delivery_period_hours']} hours"
        )
    finally:
        db.close()


@tool
def get_order_invoice(customer_id: str, order_id: str) -> str:
    """Return invoice details for a customer order."""
    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            return f"No customer was found with customer ID {customer_id}."
        order = db.execute(
            select(Order).where(Order.order_id == order_id, Order.customer_id == customer.id)
        ).scalar_one_or_none()
        if not order:
            return f"No order {order_id} was found for customer {customer_id}."
        payment = db.execute(
            select(Payment).where(Payment.order_id == order.id)
        ).scalar_one_or_none()
        payment_line = "No payment record found." if not payment else f"Payment status: {payment.payment_status} (₹{payment.amount:.0f})"
        return (
            f"Invoice for {order.order_id}\n"
            f"Amount: ₹{order.total_amount:.0f}\n"
            f"Status: {effective_order_status(order, payment)}\n"
            f"{payment_line}"
        )
    finally:
        db.close()


@tool
def get_order_details(order_id: str) -> str:
    """Retrieve complete information about a specific ABC order, including products and payment information."""

    db = SessionLocal()

    try:
        order = db.execute(
            select(Order).where(Order.order_id == order_id)
        ).scalar_one_or_none()

        if not order:
            return f"No order was found with order ID {order_id}."

        items = db.execute(
            select(OrderItem, Product)
            .join(Product, OrderItem.product_id == Product.id)
            .where(OrderItem.order_id == order.id)
        ).all()

        lines = [
            f"Order ID: {order.order_id}",
            f"Order Status: {effective_order_status(order, order.payment)}",
            f"Total Amount: ₹{order.total_amount:.0f}",
            f"Shipping Address: {order.shipping_address}",
        ]

        if items:
            lines.append("Items:")
            for item, product in items:
                lines.append(f"- {product.name} × {item.quantity} at ₹{item.unit_price:.0f} each")

        payment = db.execute(
            select(Payment).where(Payment.order_id == order.id)
        ).scalar_one_or_none()

        if payment:
            lines.extend([
                "Payment:",
                f"- Method: {payment.payment_method}",
                f"- Amount: ₹{payment.amount:.0f}",
                f"- Status: {payment.payment_status}",
                f"- Transaction ID: {payment.transaction_id}",
            ])

        return "\n".join(lines)
    finally:
        db.close()


@tool
def check_payment(order_id: str) -> str:
    """Check payment status and transaction information for an ABC order."""

    db = SessionLocal()

    try:
        order = db.execute(
            select(Order).where(Order.order_id == order_id)
        ).scalar_one_or_none()

        if not order:
            return f"No order was found with order ID {order_id}."

        payment = db.execute(
            select(Payment).where(Payment.order_id == order.id)
        ).scalar_one_or_none()

        if not payment:
            return f"No payment record was found for order {order_id}."

        return (
            f"Order: {order.order_id}\n"
            f"Payment Status: {payment.payment_status}\n"
            f"Amount: ₹{payment.amount:.0f}\n"
            f"Payment Method: {payment.payment_method}\n"
            f"Transaction ID: {payment.transaction_id}"
        )
    finally:
        db.close()


