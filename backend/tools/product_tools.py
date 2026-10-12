from typing import Optional

from langchain_core.tools import tool
from sqlalchemy import select, or_

from database.db import SessionLocal
from database.models import Product


SEARCH_SYNONYMS = {
    "earphones": ["earphones", "earbuds", "airpods", "headphones"],
    "earbud": ["earbud", "earbuds", "earphones", "airpods"],
    "earbuds": ["earbuds", "earbud", "earphones", "airpods"],
    "headphones": ["headphones", "earphones", "earbuds"],
    "headphone": ["headphone", "headphones", "earphones", "earbuds"],
    "watch": ["watch", "smart watch", "wearable"],
    "smartwatch": ["watch", "smart watch", "wearable"],
    "speaker": ["speaker", "audio"],
}

@tool
def search_products(
    search_term: Optional[str] = None,
    category: Optional[str] = None,
    max_price: Optional[float] = None,
    min_rating: Optional[float] = None,
) -> str:
    """
    Search ABC Technologies products.

    Use search_term for product types or keywords such as:
    earphones, earbuds, headphones, watch, speaker, audio, etc.

    Use category for known categories such as Audio, Wearables,
    or Smart Home.

    Use max_price for budget filtering and min_rating for rating filtering.
    """

    db = SessionLocal()

    try:
        query = select(Product).where(Product.stock > 0)

        if search_term:
            normalized = search_term.strip().lower()

            terms = SEARCH_SYNONYMS.get(
                normalized,
                [normalized]
            )

            conditions = []

            for term in terms:
                pattern = f"%{term}%"

                conditions.extend([
                    Product.name.ilike(pattern),
                    Product.category.ilike(pattern),
                    Product.description.ilike(pattern),
                ])

            query = query.where(or_(*conditions))

        if category:
            query = query.where(
                Product.category.ilike(f"%{category.strip()}%")
            )

        if max_price is not None:
            query = query.where(Product.price <= max_price)

        if min_rating is not None:
            query = query.where(Product.rating >= min_rating)

        query = query.order_by(
            Product.rating.desc(),
            Product.price.asc()
        )

        products = db.execute(query).scalars().all()

        if not products:
            return "No matching products were found."

        results = []

        for product in products:
            results.append(
                f"Product ID: {product.product_id}\n"
                f"Name: {product.name}\n"
                f"Category: {product.category}\n"
                f"Price: ₹{product.price:.0f}\n"
                f"Rating: {product.rating}/5\n"
                f"Stock: {product.stock}\n"
                f"Description: {product.description}"
            )

        return "\n\n".join(results)

    finally:
        db.close()
