import hashlib

from sqlalchemy import select

from database.db import DATABASE_PATH, engine, SessionLocal, Base
from database.models import Customer, Order, OrderItem, Payment, Product


def _hash_password(raw_password: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), b"abc-technologies", 200000).hex()


def initialize_database():
    db_path = DATABASE_PATH

    if db_path is not None and db_path.exists():
        with engine.begin() as conn:
            exists = conn.exec_driver_sql(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='customers'"
            ).fetchone()
            if exists:
                conversation_columns = conn.exec_driver_sql("PRAGMA table_info(conversations)").fetchall()
                if conversation_columns:
                    existing_conversation_columns = {column[1] for column in conversation_columns}
                    migrations = {
                        "updated_at": "ALTER TABLE conversations ADD COLUMN updated_at DATETIME",
                        "current_order_id": "ALTER TABLE conversations ADD COLUMN current_order_id VARCHAR(50)",
                        "pending_action": "ALTER TABLE conversations ADD COLUMN pending_action VARCHAR(50)",
                        "pending_order_id": "ALTER TABLE conversations ADD COLUMN pending_order_id VARCHAR(50)",
                        "awaiting_confirmation": "ALTER TABLE conversations ADD COLUMN awaiting_confirmation BOOLEAN NOT NULL DEFAULT 0",
                        "pending_expires_at": "ALTER TABLE conversations ADD COLUMN pending_expires_at DATETIME",
                    }
                    for column_name, statement in migrations.items():
                        if column_name not in existing_conversation_columns:
                            conn.exec_driver_sql(statement)
                order_columns = conn.exec_driver_sql("PRAGMA table_info(orders)").fetchall()
                if order_columns and "idempotency_key" not in {column[1] for column in order_columns}:
                    conn.exec_driver_sql("ALTER TABLE orders ADD COLUMN idempotency_key VARCHAR(100)")
                if order_columns:
                    conn.exec_driver_sql(
                        "CREATE UNIQUE INDEX IF NOT EXISTS ix_orders_idempotency_key ON orders(idempotency_key)"
                    )
                columns = conn.exec_driver_sql("PRAGMA table_info(customers)").fetchall()
                if "password_hash" not in {column[1] for column in columns}:
                    raise RuntimeError(
                        f"Database schema at {db_path} is incompatible (customers.password_hash is missing). "
                        "The database was preserved; back it up and apply an explicit migration."
                    )

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        product_seed = [
            {"product_id": "P1001", "name": "ABC AirPods Pro", "category": "Audio", "description": "Premium wireless earbuds with active noise cancellation.", "price": 2499, "stock": 25, "rating": 4.7, "image": "/images/earbuds.jpg", "featured": True},
            {"product_id": "P1002", "name": "ABC Buds Lite", "category": "Audio", "description": "Affordable wireless earbuds with clear sound and long battery life.", "price": 1499, "stock": 40, "rating": 4.4, "image": "/images/neckband.jpg", "featured": False},
            {"product_id": "P1003", "name": "ABC Smart Watch X", "category": "Wearables", "description": "Smart fitness watch with health tracking and notifications.", "price": 2999, "stock": 18, "rating": 4.6, "image": "/images/watch.jpg", "featured": True},
            {"product_id": "P1004", "name": "ABC SoundMax Speaker", "category": "Audio", "description": "Portable Bluetooth speaker with powerful sound.", "price": 1999, "stock": 30, "rating": 4.5, "image": "/images/speaker.jpg", "featured": False},
            {"product_id": "P1005", "name": "ABC Home Hub", "category": "Smart Home", "description": "Smart home controller for connected ABC devices.", "price": 3499, "stock": 12, "rating": 4.3, "image": "/images/camera.jpg", "featured": False},
            {"product_id": "P1006", "name": "ABC ChargeHub Power Bank", "category": "Accessories", "description": "Fast-charging 20,000 mAh power bank with USB-C ports.", "price": 1499, "stock": 64, "rating": 4.3, "image": "/images/powerbank.jpg", "featured": True},
            {"product_id": "P1007", "name": "ABC Studio Headphones", "category": "Audio", "description": "Over-ear wireless headphones with immersive sound and soft cushions.", "price": 3499, "stock": 22, "rating": 4.7, "image": "/images/headphones.jpg", "featured": False},
            {"product_id": "P1008", "name": "ABC Smart Plug Duo", "category": "Smart Home", "description": "Control lamps and appliances from your phone with energy monitoring.", "price": 1299, "stock": 50, "rating": 4.2, "image": "/images/plug.jpg", "featured": False},
            {"product_id": "P1009", "name": "ABC TypePro Keyboard", "category": "Accessories", "description": "Compact mechanical keyboard with hot-swappable switches.", "price": 2999, "stock": 17, "rating": 4.5, "image": "/images/keyboard.jpg", "featured": False},
            {"product_id": "P1010", "name": "ABC Fit Band Lite", "category": "Wearables", "description": "Fitness band with sleep tracking, step goals and a 10-day battery.", "price": 1999, "stock": 36, "rating": 4.1, "image": "/images/band.jpg", "featured": False},
            {"product_id": "P1011", "name": "ABC MagSafe Case Pack", "category": "Accessories", "description": "Protective phone cases with a magnetic charging ring.", "price": 899, "stock": 80, "rating": 4.0, "image": "/images/case.jpg", "featured": False},
            {"product_id": "P1012", "name": "ABC NightGlow Smart Lamp", "category": "Smart Home", "description": "Tunable white and color lamp with schedules and app control.", "price": 2199, "stock": 25, "rating": 4.6, "image": "/images/lamp.jpg", "featured": False},
            {"product_id": "P1013", "name": "ABC HomeCam 360", "category": "Smart Home", "description": "Indoor security camera with 360-degree pan and night vision.", "price": 4599, "stock": 12, "rating": 4.4, "image": "https://images.unsplash.com/photo-1558008258-3256797b43f3?auto=format&fit=crop&w=800&q=80", "featured": False},
            {"product_id": "P1014", "name": "ABC Desk Monitor Stand", "category": "Accessories", "description": "Aluminium monitor stand with a practical storage shelf.", "price": 1799, "stock": 20, "rating": 4.2, "image": "https://images.unsplash.com/photo-1616763355548-1b606f439f86?auto=format&fit=crop&w=800&q=80", "featured": False},
            {"product_id": "P1015", "name": "ABC USB-C Hub 7-in-1", "category": "Accessories", "description": "Compact USB-C hub with HDMI, USB and SD card connectivity.", "price": 2299, "stock": 32, "rating": 4.5, "image": "https://images.unsplash.com/photo-1625842268584-8f3296236761?auto=format&fit=crop&w=800&q=80", "featured": False},
            {"product_id": "P1016", "name": "ABC Tablet Stand", "category": "Accessories", "description": "Adjustable aluminum stand for tablets and phones while working.", "price": 999, "stock": 35, "rating": 4.1, "image": "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=80", "featured": False},
            {"product_id": "P1017", "name": "ABC Smart Plug Mini", "category": "Smart Home", "description": "Energy-efficient smart plug for lights and chargers.", "price": 899, "stock": 55, "rating": 4.2, "image": "https://images.unsplash.com/photo-1581578731548-c64695cc6952?auto=format&fit=crop&w=800&q=80", "featured": False},
            {"product_id": "P1018", "name": "ABC Portable SSD 1TB", "category": "Computer Accessories", "description": "Compact high-speed external SSD for content creators and professionals.", "price": 6999, "stock": 10, "rating": 4.8, "image": "https://images.unsplash.com/photo-1587825140708-dfaf72ae4b04?auto=format&fit=crop&w=800&q=80", "featured": True},
        ]

        for data in product_seed:
            existing = db.execute(select(Product).where(Product.product_id == data["product_id"])).scalar_one_or_none()
            if not existing:
                db.add(Product(**data))

        customers = [
            {"customer_id": "CUST1001", "name": "Demo Customer", "email": "demo@abc-technologies.com", "phone": "9999999999", "password_hash": _hash_password("demo123")},
            {"customer_id": "CUST1002", "name": "Interview Demo User", "email": "interview@abc-technologies.com", "phone": "8888888888", "password_hash": _hash_password("demo123")},
        ]

        for data in customers:
            existing = db.execute(select(Customer).where(Customer.customer_id == data["customer_id"])).scalar_one_or_none()
            if not existing:
                db.add(Customer(**data))

        db.flush()

        if not db.execute(select(Order).limit(1)).first():
            demo_customer_1 = db.execute(select(Customer).where(Customer.customer_id == "CUST1001")).scalar_one_or_none()
            demo_customer_2 = db.execute(select(Customer).where(Customer.customer_id == "CUST1002")).scalar_one_or_none()
            product_1 = db.execute(select(Product).where(Product.product_id == "P1001")).scalar_one_or_none()
            product_2 = db.execute(select(Product).where(Product.product_id == "P1003")).scalar_one_or_none()
            product_3 = db.execute(select(Product).where(Product.product_id == "P1006")).scalar_one_or_none()

            if not all([demo_customer_1, demo_customer_2, product_1, product_2, product_3]):
                raise RuntimeError("Seed data is incomplete after initialization.")

            order_1 = Order(order_id="ORD1001", customer_id=demo_customer_1.id, order_status="Shipped", total_amount=2499, shipping_address="12 Main Street, Bengaluru")
            order_2 = Order(order_id="ORD1002", customer_id=demo_customer_1.id, order_status="Delivered", total_amount=2999 + 1499, shipping_address="12 Main Street, Bengaluru")
            order_3 = Order(order_id="ORD1003", customer_id=demo_customer_2.id, order_status="Processing", total_amount=1499, shipping_address="9 Market Road, Mumbai")
            db.add_all([order_1, order_2, order_3])
            db.flush()

            db.add_all([
                OrderItem(order_id=order_1.id, product_id=product_1.id, quantity=1, unit_price=2499),
                OrderItem(order_id=order_2.id, product_id=product_2.id, quantity=1, unit_price=2999),
                OrderItem(order_id=order_2.id, product_id=product_3.id, quantity=1, unit_price=1499),
                OrderItem(order_id=order_3.id, product_id=product_1.id, quantity=1, unit_price=1499),
            ])
            db.add_all([
                Payment(order_id=order_1.id, transaction_id="TXN1001", amount=2499, payment_method="UPI", payment_status="Paid"),
                Payment(order_id=order_2.id, transaction_id="TXN1002", amount=4498, payment_method="Card", payment_status="Paid"),
                Payment(order_id=order_3.id, transaction_id="TXN1003", amount=1499, payment_method="Wallet", payment_status="Pending"),
            ])

        db.commit()
        print("Database initialized successfully.")

    finally:
        db.close()


if __name__ == "__main__":
    initialize_database()
