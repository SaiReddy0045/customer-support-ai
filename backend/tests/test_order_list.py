import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from agents.intent_classifier import classify_request
from agents import order_agent as order_agent_module
from database.db import Base
from database.models import Customer, Order, Payment


class OrderListWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "order_list_test.sqlite"
        self.engine = create_engine(
            f"sqlite:///{self.database_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        patcher = patch.object(order_agent_module, "SessionLocal", self.session_factory)
        patcher.start()
        self.addCleanup(patcher.stop)

        with self.session_factory() as db:
            customer = Customer(
                customer_id="CUST1004",
                name="List Test",
                email="list-test@example.test",
                password_hash="test",
            )
            empty_customer = Customer(
                customer_id="CUST_EMPTY",
                name="Empty Test",
                email="empty-test@example.test",
                password_hash="test",
            )
            other_customer = Customer(
                customer_id="CUST_OTHER",
                name="Other Test",
                email="other-list-test@example.test",
                password_hash="test",
            )
            db.add_all([customer, empty_customer, other_customer])
            db.flush()
            self.customer_pk = customer.id
            self.other_customer_pk = other_customer.id
            self.add_order(db, customer.id, "ORDDBF6CE13", "Cancelled", 3)
            self.add_order(db, customer.id, "ORD1012C991", "Packing", 2)
            self.add_order(db, customer.id, "ORD9690FC8B", "Shipped", 30)
            self.add_order(db, other_customer.id, "ORDOTHER001", "Packing", 2)
            db.commit()

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    @staticmethod
    def add_order(db, customer_pk, order_id, status, age_hours):
        order = Order(
            order_id=order_id,
            customer_id=customer_pk,
            order_status=status,
            total_amount=100,
            shipping_address="Test address",
            created_at=datetime.utcnow() - timedelta(hours=age_hours),
        )
        db.add(order)
        db.flush()
        db.add(Payment(
            order_id=order.id,
            transaction_id=f"TX-{order_id}",
            amount=100,
            payment_method="Card",
            payment_status="Paid",
        ))

    def respond(self, message, customer_id="CUST1004"):
        return order_agent_module._fast_order_response(message, customer_id)

    def test_all_orders_phrases_use_the_dedicated_list_action(self):
        for phrase in ("list my orders", "list all the orders", "show all my orders"):
            with self.subTest(phrase=phrase):
                self.assertEqual(classify_request(phrase)["action"], "list_orders")
                response = self.respond(phrase)
                self.assertIn("ORDDBF6CE13", response)
                self.assertIn("ORD1012C991", response)
                self.assertIn("ORD9690FC8B", response)

    def test_list_returns_all_customer_orders_across_statuses_only(self):
        response = self.respond("list all the orders")
        self.assertIn("ORDDBF6CE13: Cancelled", response)
        self.assertIn("ORD1012C991: Packing", response)
        self.assertIn("ORD9690FC8B: Shipped", response)
        self.assertNotIn("ORDOTHER001", response)

    def test_customer_without_orders_gets_empty_result(self):
        response = self.respond("list all the orders", "CUST_EMPTY")
        self.assertEqual(response, "I checked customer CUST_EMPTY and there are no orders on file.")

    def test_explicit_single_order_status_lookup_still_works(self):
        response = self.respond("what is the status of my order ORD1012C991")
        self.assertIn("ORD1012C991", response)
        self.assertIn("Packing", response)
        self.assertNotIn("ORDDBF6CE13", response)


if __name__ == "__main__":
    unittest.main()