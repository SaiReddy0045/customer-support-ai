import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from agents.intent_classifier import classify_request
from database.db import Base
from database.models import Conversation, Customer, Message, Order
import graph.workflow as workflow_module
from agents import order_agent as order_agent_module
from services.order_cancellation_service import cancellation_block_reason


class OrderCancellationWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "cancellation_test.sqlite"
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
        self.patches = [
            patch.object(order_agent_module, "SessionLocal", self.session_factory),
            patch.object(workflow_module, "SessionLocal", self.session_factory),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)

        with self.session_factory() as db:
            self.customer = Customer(
                customer_id="CUST_TEST_1",
                name="Cancellation Test",
                email="cancel-test@example.test",
                password_hash="test",
            )
            self.other_customer = Customer(
                customer_id="CUST_TEST_2",
                name="Other Test",
                email="other-test@example.test",
                password_hash="test",
            )
            db.add_all([self.customer, self.other_customer])
            db.flush()
            self.customer_pk = self.customer.id
            self.other_customer_pk = self.other_customer.id
            self.conversation_id = "conversation-test"
            db.add(Conversation(
                conversation_id=self.conversation_id,
                customer_id=self.customer_pk,
            ))
            db.add_all([
                self.order("ORDTESTA", self.customer_pk, datetime.utcnow() - timedelta(hours=5)),
                self.order("ORDTESTB", self.customer_pk, datetime.utcnow() - timedelta(hours=6)),
                self.order("ORDTESTOLD", self.customer_pk, datetime.utcnow() - timedelta(hours=25)),
                self.order("ORDTESTFOREIGN", self.other_customer_pk, datetime.utcnow() - timedelta(hours=2)),
            ])
            db.commit()

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    @staticmethod
    def order(order_id, customer_pk, created_at):
        return Order(
            order_id=order_id,
            customer_id=customer_pk,
            order_status="Order Confirmed",
            total_amount=100,
            shipping_address="Test address",
            created_at=created_at,
        )

    def send(self, message):
        with self.session_factory() as db:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            history = [
                {"role": row.role, "content": row.content}
                for row in db.execute(
                    select(Message)
                    .where(Message.conversation_id == conversation.id)
                    .order_by(Message.id)
                ).scalars().all()
            ]
        result = workflow_module.workflow.invoke({
            "query": message,
            "customer_id": "CUST_TEST_1",
            "conversation_id": self.conversation_id,
            "conversation_history": history,
        })
        with self.session_factory() as db:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            db.add(Message(conversation_id=conversation.id, role="user", content=message))
            db.add(Message(
                conversation_id=conversation.id,
                role="assistant",
                content=result["response"],
                agent=result.get("intent"),
            ))
            db.commit()
        return result["response"]

    def status(self, order_id):
        with self.session_factory() as db:
            order = db.execute(select(Order).where(Order.order_id == order_id)).scalar_one()
            return order.order_status

    def test_a_eligibility_question_is_read_only_and_confirmation_persists_status(self):
        response = self.send("Can I cancel my latest order?")
        self.assertIn("ORDTESTA", response)
        self.assertIn("eligible for cancellation", response)
        self.assertEqual(self.status("ORDTESTA"), "Order Confirmed")
        with self.session_factory() as db:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            self.assertEqual(conversation.pending_action, "cancel_order")
            self.assertEqual(conversation.pending_order_id, "ORDTESTA")
            self.assertTrue(conversation.awaiting_confirmation)

        confirmation = self.send("Yes, cancel it")
        self.assertIn("Order ORDTESTA has been cancelled successfully", confirmation)
        self.assertIn("Current status: Cancelled", confirmation)
        self.assertEqual(self.status("ORDTESTA"), "Cancelled")
        self.assertIn("ORDTESTA: Cancelled", self.send("show my orders"))
        with self.session_factory() as db:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            self.assertIsNone(conversation.pending_action)
            self.assertIsNone(conversation.pending_order_id)
            self.assertFalse(conversation.awaiting_confirmation)

    def test_b_order_older_than_24_hours_is_not_cancelled(self):
        response = self.send("cancel ORDTESTOLD")
        self.assertIn("ORDTESTOLD was placed more than 24 hours ago", response)
        self.assertEqual(self.status("ORDTESTOLD"), "Order Confirmed")

    def test_c_explicit_order_command_cancels_and_reports_saved_status(self):
        response = self.send("Cancel order ORDTESTB")
        self.assertIn("Order ORDTESTB has been cancelled successfully", response)
        self.assertIn("Current status: Cancelled", response)
        self.assertEqual(self.status("ORDTESTB"), "Cancelled")

    def test_d_rejection_clears_pending_without_changing_status(self):
        self.send("Can I cancel order ORDTESTA?")
        response = self.send("no")
        self.assertEqual(response, "Okay. Order ORDTESTA was not cancelled.")
        self.assertEqual(self.status("ORDTESTA"), "Order Confirmed")
        with self.session_factory() as db:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            self.assertIsNone(conversation.pending_action)
            self.assertIsNone(conversation.pending_order_id)
            self.assertFalse(conversation.awaiting_confirmation)

    def test_e_foreign_order_is_never_modified(self):
        response = self.send("cancel order ORDTESTFOREIGN")
        self.assertIn("Access denied", response)
        self.assertEqual(self.status("ORDTESTFOREIGN"), "Order Confirmed")

    def test_f_repeat_request_reports_already_cancelled(self):
        self.send("cancel ORDTESTA")
        self.send("yes")
        response = self.send("cancel ORDTESTA")
        self.assertEqual(response, "Order ORDTESTA is already cancelled.")

    def test_g_ambiguous_request_lists_candidate_ids(self):
        response = self.send("cancel my order")
        self.assertIn("Which order would you like to cancel?", response)
        self.assertIn("ORDTESTA", response)
        self.assertIn("ORDTESTB", response)
        self.assertEqual(self.status("ORDTESTA"), "Order Confirmed")
        self.assertEqual(self.status("ORDTESTB"), "Order Confirmed")

    def test_other_order_uses_list_context_and_confirmation_vocabulary_routes(self):
        self.send("show my orders")
        response = self.send("Can I cancel the other order?")
        self.assertIn("ORDTESTB", response)
        with self.session_factory() as db:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            self.assertEqual(conversation.pending_order_id, "ORDTESTB")
        confirmation = self.send("proceed with cancellation")
        self.assertIn("Order ORDTESTB has been cancelled successfully", confirmation)
        self.assertIn("Current status: Cancelled", confirmation)

        for phrase in ("yes", "yes cancel it", "cancel it", "proceed", "proceed with cancellation", "confirm", "confirm cancellation"):
            with self.subTest(phrase=phrase):
                self.assertEqual(
                    classify_request(
                        phrase,
                        pending_action="cancel_order",
                        awaiting_confirmation=True,
                    )["action"],
                    "cancel_confirmation",
                )

    def test_unknown_order_id_is_reported_without_selecting_another_order(self):
        response = self.send("cancel order ORDMISSING")
        self.assertEqual(response, "Order ORDMISSING was not found.")
        self.assertEqual(self.status("ORDTESTA"), "Order Confirmed")

    def test_phrase_terminal_states_are_blocked(self):
        with self.session_factory() as db:
            order = db.execute(select(Order).where(Order.order_id == "ORDTESTA")).scalar_one()
            for status in ("Order Delivered", "Refund Requested", "Refunded", "Order Cancelled"):
                order.order_status = status
                reason = cancellation_block_reason(order)
                expected = "already_cancelled" if "cancelled" in status.lower() else "terminal_status"
                self.assertEqual(reason, expected, status)

    def test_exact_24_hour_boundary_is_not_eligible_and_timezone_is_safe(self):
        with self.session_factory() as db:
            order = db.execute(select(Order).where(Order.order_id == "ORDTESTA")).scalar_one()
            order.created_at = datetime(2026, 10, 8, 12, 0, 0)
            db.commit()
            at_cutoff = datetime(2026, 10, 9, 12, 0, 0, tzinfo=timezone.utc)
            self.assertEqual(cancellation_block_reason(order, at_cutoff), "outside_window")
            just_before = at_cutoff - timedelta(seconds=1)
            self.assertIsNone(cancellation_block_reason(order, just_before))

    def test_follow_up_uses_previously_discussed_latest_order(self):
        self.send("Can I cancel my latest order?")
        response = self.send("Yes, cancel it")
        self.assertIn("Order ORDTESTA has been cancelled successfully", response)
        self.assertEqual(self.status("ORDTESTA"), "Cancelled")

    def test_latest_order_details_query_still_returns_order(self):
        response = self.send("What is my latest order?")
        self.assertIn("ORDTESTA", response)
        self.assertIn("current status", response)

    def test_explicit_valid_order_id_uses_that_exact_order(self):
        response = self.send("Tell me about order ORDTESTB.")
        self.assertIn("ORDTESTB", response)
        self.assertNotIn("ORDTESTA", response)

    def test_hyphenated_invalid_order_id_does_not_fall_back_to_latest(self):
        response = self.send("Tell me about order ORD-INVALID123.")
        self.assertIn("ORD-INVALID123", response)
        self.assertIn("not found", response.lower())
        self.assertNotIn("ORDTESTA", response)

    def test_foreign_order_id_is_not_disclosed_or_replaced_with_latest(self):
        response = self.send("Tell me about order ORDTESTFOREIGN.")
        self.assertIn("ORDTESTFOREIGN", response)
        self.assertIn("not found", response.lower())
        self.assertNotIn("ORDTESTA", response)

    def test_latest_order_still_resolves_without_explicit_id(self):
        response = self.send("Tell me about my latest order.")
        self.assertIn("ORDTESTA", response)

    def test_direct_cancel_with_multiple_orders_does_not_guess(self):
        response = self.send("Cancel my order")
        self.assertIn("Which order would you like to cancel?", response)
        self.assertEqual(self.status("ORDTESTA"), "Order Confirmed")
        self.assertEqual(self.status("ORDTESTB"), "Order Confirmed")


if __name__ == "__main__":
    unittest.main()
