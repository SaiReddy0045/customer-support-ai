from sqlalchemy import select
from sqlalchemy.orm import Session
from decimal import Decimal, ROUND_HALF_UP

from database.models import Product

TAX_RATE = 0.18
FREE_SHIPPING_THRESHOLD = 2000.0
SHIPPING_FEE = 99.0


def calculate_checkout(db: Session, requested_items: list[dict]) -> tuple[list[dict], dict]:
    if not requested_items:
        raise ValueError("At least one product is required.")

    validated_items: list[dict] = []
    subtotal = Decimal("0.00")
    for item in requested_items:
        product_id = str(item.get("id") or item.get("productId") or "").strip()
        try:
            quantity = int(item.get("quantity", 1))
        except (TypeError, ValueError) as exc:
            raise ValueError("Product quantity must be a positive whole number.") from exc
        if not product_id or quantity <= 0:
            raise ValueError("Product ID and a positive whole-number quantity are required.")

        product = db.execute(
            select(Product).where(Product.product_id == product_id)
        ).scalar_one_or_none()
        if not product:
            raise LookupError(f"Product {product_id} was not found.")
        if product.stock < quantity:
            raise ValueError(f"Insufficient stock for {product.name}.")

        unit_price_decimal = Decimal(str(product.price)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        unit_price = float(unit_price_decimal)
        subtotal += unit_price_decimal * quantity
        validated_items.append({
            "id": product.product_id,
            "name": product.name,
            "quantity": quantity,
            "price": unit_price,
        })

    subtotal = subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    tax = (subtotal * Decimal(str(TAX_RATE))).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    shipping = Decimal("0.00") if subtotal == 0 or subtotal >= Decimal(str(FREE_SHIPPING_THRESHOLD)) else Decimal(str(SHIPPING_FEE))
    total = (subtotal + tax + shipping).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return validated_items, {
        "subtotal": float(subtotal),
        "tax": float(tax),
        "shipping": float(shipping),
        "total": float(total),
        "taxRate": TAX_RATE,
    }
