import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from starlette.requests import Request

from database.db import Base
from database.models import Conversation, Customer, Order, Payment, Product, Refund, SupportTicket
import agents.refund_agent as refund_agent_module
import agents.order_agent as order_agent_module
import agents.billing_agent as billing_agent_module
import graph.workflow as workflow_module
import tools.refund_tools as refund_tools_module
import tools.product_tools as product_tools_module
import api as api_module
from services.tracking_service import calculate_tracking, effective_order_status, refund_is_eligible
from tools.refund_tools import create_refund_for_customer
from agents.billing_agent import _fast_billing_response
from agents.shopping_agent import handle_shopping
from agents.refund_agent import _fast_refund_response
from agents.intent_classifier import classify_request
from services.support_ticket_service import create_support_ticket
import database.init_db as init_db_module


class OrderLifecycleRefundTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "lifecycle_test.sqlite"
        self.engine = __import__("sqlalchemy").create_engine(
            f"sqlite:///{self.database_path.as_posix()}",
            connect_args={"check_same_thread": False},
        )
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.patchers = [
            patch.object(refund_agent_module, "SessionLocal", self.session_factory),
            patch.object(order_agent_module, "SessionLocal", self.session_factory),
            patch.object(billing_agent_module, "SessionLocal", self.session_factory),
            patch.object(refund_tools_module, "SessionLocal", self.session_factory),
            patch.object(product_tools_module, "SessionLocal", self.session_factory),
            patch.object(workflow_module, "SessionLocal", self.session_factory),
            patch.object(api_module, "SessionLocal", self.session_factory),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)

        with self.session_factory() as db:
            owner = Customer(
                customer_id="CUST_LIFECYCLE_1",
                name="Lifecycle Test",
                email="lifecycle-test@example.test",
                password_hash=api_module.hash_password("test-pass-123"),
            )
            other = Customer(
                customer_id="CUST_LIFECYCLE_2",
                name="Other Lifecycle Test",
                email="lifecycle-other@example.test",
                password_hash=api_module.hash_password("other-pass-123"),
            )
            db.add_all([owner, other])
            db.flush()
            self.owner_pk = owner.id
            self.other_pk = other.id
            self.conversation_id = "refund-conversation"
            db.add(Conversation(conversation_id=self.conversation_id, customer_id=self.owner_pk))
            db.add(Product(
                product_id="P_TEST_EARBUDS",
                name="Test Earbuds",
                category="Audio",
                description="Test earbuds for isolated search regression.",
                price=2500,
                stock=5,
                rating=4.5,
            ))
            self.add_order(db, "ORDPAIDOLD", self.owner_pk, hours=50, payment_status="Paid", order_status="Order Confirmed")
            self.add_order(db, "ORDUNPAIDOLD", self.owner_pk, hours=96, payment_status="Pending Payment", order_status="Pending Payment")
            self.add_order(db, "ORDCANCELLED", self.owner_pk, hours=96, payment_status="Paid", order_status="Cancelled")
            self.add_order(db, "ORDREFUNDED", self.owner_pk, hours=96, payment_status="Paid", order_status="Refund Requested")
            self.add_order(db, "ORDREFUNDNEW", self.owner_pk, minutes=5, payment_status="Paid", order_status="Order Confirmed")
            self.add_order(db, "ORDFOREIGN", self.other_pk, minutes=5, payment_status="Paid", order_status="Order Confirmed")
            db.commit()

    def tearDown(self):
        self.engine.dispose()
        self.temp_dir.cleanup()

    @staticmethod
    def add_order(db, order_id, customer_pk, hours=0, minutes=0, payment_status="Paid", order_status="Order Confirmed"):
        order = Order(
            order_id=order_id,
            customer_id=customer_pk,
            order_status=order_status,
            total_amount=175.0,
            shipping_address="Test address",
            created_at=datetime.utcnow() - timedelta(hours=hours, minutes=minutes),
        )
        db.add(order)
        db.flush()
        if payment_status:
            db.add(Payment(
                order_id=order.id,
                transaction_id=f"TX-{order_id}",
                amount=175.0,
                payment_method="Card",
                payment_status=payment_status,
            ))
        return order

    @staticmethod
    def request_for(customer_id, session_token=None):
        return Request({
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [
                (b"x-customer-id", customer_id.encode()),
                (b"authorization", f"Bearer {session_token or api_module.issue_session_token(customer_id)}".encode()),
            ],
            "query_string": b"",
            "server": ("test", 80),
            "client": ("test", 123),
            "scheme": "http",
        })

    def workflow_turn(self, message):
        with self.session_factory() as db:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            history = []
            for row in conversation.messages:
                history.append({"role": row.role, "content": row.content})
        result = workflow_module.workflow.invoke({
            "query": message,
            "customer_id": "CUST_LIFECYCLE_1",
            "conversation_id": self.conversation_id,
            "conversation_history": history,
        })
        with self.session_factory() as db:
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            from database.models import Message
            db.add_all([
                Message(conversation_id=conversation.id, role="user", content=message),
                Message(conversation_id=conversation.id, role="assistant", content=result["response"]),
            ])
            db.commit()
        return result

    def test_lifecycle_and_pending_payment_gates(self):
        now = datetime.utcnow()
        order = Order(order_id="ORDTIME", order_status="Order Confirmed", created_at=now - timedelta(minutes=2))
        paid = Payment(payment_status="Paid")
        cases = [
            (timedelta(minutes=10), "Order Confirmed"),
            (timedelta(minutes=30), "Order Confirmed"),
            (timedelta(hours=24), "Packing"),
            (timedelta(hours=36), "Shipped"),
            (timedelta(hours=48), "Delivered"),
        ]
        for age, expected in cases:
            order.created_at = now - age
            self.assertEqual(calculate_tracking(order, paid, now)["status"], expected)

        with self.session_factory() as db:
            unpaid = db.execute(select(Order).where(Order.order_id == "ORDUNPAIDOLD")).scalar_one()
            self.assertEqual(effective_order_status(unpaid, unpaid.payment, now), "Pending Payment")
            self.assertEqual(calculate_tracking(unpaid, unpaid.payment, now)["status"], "Pending Payment")
            self.assertFalse(refund_is_eligible(unpaid, payment=unpaid.payment, now=now))
            cancelled = db.execute(select(Order).where(Order.order_id == "ORDCANCELLED")).scalar_one()
            refunded = db.execute(select(Order).where(Order.order_id == "ORDREFUNDED")).scalar_one()
            self.assertEqual(effective_order_status(cancelled, cancelled.payment, now), "Cancelled")
            self.assertEqual(effective_order_status(refunded, refunded.payment, now), "Refund Requested")

    def test_ai_list_and_tracking_endpoint_share_effective_status(self):
        customer_id = "CUST_LIFECYCLE_1"
        listed = api_module.get_orders(customer_id, self.request_for(customer_id))
        old_order = next(item for item in listed if item["orderId"] == "ORDPAIDOLD")
        self.assertEqual(old_order["orderStatus"], "Delivered")
        self.assertEqual(old_order["tracking"]["status"], "Delivered")

        tracking_rows = api_module.get_order_tracking(customer_id, self.request_for(customer_id))
        old_tracking = next(item for item in tracking_rows if item["order_id"] == "ORDPAIDOLD")
        self.assertEqual(old_tracking["status"], old_order["orderStatus"])

        agent_response = workflow_module.workflow.invoke({
            "query": "what is the status of my order ORDPAIDOLD",
            "customer_id": customer_id,
            "conversation_id": self.conversation_id,
            "conversation_history": [],
        })["response"]
        self.assertIn("ORDPAIDOLD", agent_response)
        self.assertIn("Delivered", agent_response)

    def test_yes_submits_pending_refund_and_persists_real_id(self):
        first = self.workflow_turn("Can I request a refund for order ORDREFUNDNEW?")
        self.assertIn("Would you like me to submit", first["response"])
        with self.session_factory() as db:
            conversation = db.execute(select(Conversation).where(Conversation.conversation_id == self.conversation_id)).scalar_one()
            self.assertEqual(conversation.pending_action, "refund_request")
            self.assertEqual(conversation.pending_order_id, "ORDREFUNDNEW")
            self.assertTrue(conversation.awaiting_confirmation)

        confirmation_message = "Yes, submit the refund request for order ORDREFUNDNEW."
        self.assertEqual(
            classify_request(
                confirmation_message,
                pending_action="refund_request",
                awaiting_confirmation=True,
            )["action"],
            "refund_confirmation",
        )
        confirmation = self.workflow_turn(confirmation_message)
        self.assertIn("Refund ID: REF-", confirmation["response"])
        self.assertIn("recorded", confirmation["response"])
        with self.session_factory() as db:
            refund = db.execute(
                select(Refund).join(Order).where(Order.order_id == "ORDREFUNDNEW")
            ).scalar_one()
            order = db.execute(select(Order).where(Order.order_id == "ORDREFUNDNEW")).scalar_one()
            conversation = db.execute(select(Conversation).where(Conversation.conversation_id == self.conversation_id)).scalar_one()
            self.assertEqual(order.order_status, "Refund Requested")
            self.assertTrue(confirmation["response"].find(f"REF-{refund.id:06d}") >= 0)
            self.assertIsNone(conversation.pending_action)
            self.assertIsNone(conversation.pending_order_id)
            self.assertFalse(conversation.awaiting_confirmation)

        repeated_confirmation = self.workflow_turn(confirmation_message)
        self.assertIn("refund request already exists", repeated_confirmation["response"].lower())
        self.assertIn(f"REF-{refund.id:06d}", repeated_confirmation["response"])
        with self.session_factory() as db:
            refunds = db.execute(
                select(Refund).join(Order).where(Order.order_id == "ORDREFUNDNEW")
            ).scalars().all()
            self.assertEqual(len(refunds), 1)

        duplicate = create_refund_for_customer("CUST_LIFECYCLE_1", "ORDREFUNDNEW", "duplicate test")
        self.assertTrue(duplicate["duplicate"])
        self.assertEqual(duplicate["refund_id"], f"REF-{refund.id:06d}")

    def test_general_refund_policy_question_is_informational_only(self):
        query = "What is your refund policy?"
        self.assertEqual(classify_request(query)["action"], "refund_process_information")

        response = _fast_refund_response(
            query,
            "CUST_LIFECYCLE_1",
            [],
            self.conversation_id,
        )

        self.assertIn("configured demonstration request window", response)
        self.assertNotIn("Would you like me to submit", response)
        with self.session_factory() as db:
            refunds = db.execute(select(Refund)).scalars().all()
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            self.assertEqual(refunds, [])
            self.assertIsNone(conversation.pending_action)
            self.assertIsNone(conversation.pending_order_id)
            self.assertFalse(conversation.awaiting_confirmation)

    def test_explicit_order_refund_eligibility_remains_order_specific_and_read_only(self):
        query = "Can I request a refund for order ORDREFUNDNEW?"
        self.assertEqual(classify_request(query)["action"], "refund_eligibility")

        response = _fast_refund_response(
            query,
            "CUST_LIFECYCLE_1",
            [],
            self.conversation_id,
        )

        self.assertIn("Order ORDREFUNDNEW", response)
        self.assertIn("eligible for a refund", response)
        with self.session_factory() as db:
            refunds = db.execute(select(Refund)).scalars().all()
            conversation = db.execute(
                select(Conversation).where(Conversation.conversation_id == self.conversation_id)
            ).scalar_one()
            self.assertEqual(refunds, [])
            self.assertEqual(conversation.pending_action, "refund_request")
            self.assertEqual(conversation.pending_order_id, "ORDREFUNDNEW")
            self.assertTrue(conversation.awaiting_confirmation)

    def test_no_clears_pending_refund_without_mutation(self):
        self.workflow_turn("I need a refund for ORDREFUNDNEW")
        response = self.workflow_turn("no")["response"]
        self.assertIn("did not submit", response)
        with self.session_factory() as db:
            refunds = db.execute(
                select(Refund).join(Order).where(Order.order_id == "ORDREFUNDNEW")
            ).scalars().all()
            conversation = db.execute(select(Conversation).where(Conversation.conversation_id == self.conversation_id)).scalar_one()
            order = db.execute(select(Order).where(Order.order_id == "ORDREFUNDNEW")).scalar_one()
            self.assertEqual(refunds, [])
            self.assertEqual(order.order_status, "Order Confirmed")
            self.assertIsNone(conversation.pending_action)
            self.assertFalse(conversation.awaiting_confirmation)

    def test_refund_confirmation_revalidates_payment_and_customer_ownership(self):
        self.assertFalse(create_refund_for_customer("CUST_LIFECYCLE_1", "ORDUNPAIDOLD", "test")["ok"])
        self.assertFalse(create_refund_for_customer("CUST_LIFECYCLE_1", "ORDFOREIGN", "test")["ok"])

    def test_yes_without_pending_refund_does_not_create_a_refund(self):
        self.assertEqual(classify_request("yes")["domain"], "support")
        with self.session_factory() as db:
            conversation = db.execute(select(Conversation).where(Conversation.conversation_id == self.conversation_id)).scalar_one()
            conversation.pending_action = None
            conversation.pending_order_id = None
            conversation.awaiting_confirmation = False
            db.commit()
        result = workflow_module.workflow.invoke({
            "query": "yes",
            "customer_id": "CUST_LIFECYCLE_1",
            "conversation_id": self.conversation_id,
            "conversation_history": [],
        })
        self.assertEqual(result["intent"], "support")
        with self.session_factory() as db:
            refunds = db.execute(select(Refund)).scalars().all()
            self.assertEqual(refunds, [])

    def test_existing_product_search_duplicate_charge_and_refund_process_routes(self):
        self.assertEqual(classify_request("what are the steps to get a refund")["action"], "refund_process_information")
        self.assertIn("To request a refund", _fast_refund_response("what are the steps to get a refund", "CUST_LIFECYCLE_1", [], self.conversation_id))
        billing_response = _fast_billing_response("I was charged twice", "CUST_LIFECYCLE_1")
        self.assertIn("no duplicate charge", billing_response.lower())
        self.assertIn("matching", handle_shopping("find earphones under 3000").lower())

    def test_signed_customer_scope_rejects_spoofed_identity(self):
        spoofed = self.request_for("CUST_LIFECYCLE_1", api_module.issue_session_token("CUST_LIFECYCLE_2"))
        with self.assertRaises(Exception):
            api_module.get_orders("CUST_LIFECYCLE_1", spoofed)

    def test_demo_payment_receipt_is_bound_to_customer_amount_and_transaction(self):
        receipt = api_module.issue_demo_payment_token(
            "CUST_LIFECYCLE_1", "DEMO-TX-1", 175, "Card"
        )
        self.assertTrue(api_module.verify_demo_payment_token(
            receipt, "CUST_LIFECYCLE_1", "DEMO-TX-1", 175, "Card"
        ))
        self.assertFalse(api_module.verify_demo_payment_token(
            receipt, "CUST_LIFECYCLE_2", "DEMO-TX-1", 175, "Card"
        ))
        self.assertFalse(api_module.verify_demo_payment_token(
            receipt, "CUST_LIFECYCLE_1", "DEMO-TX-1", 176, "Card"
        ))

    def test_refund_window_is_exactly_12_hours(self):
        with self.session_factory() as db:
            order = db.execute(select(Order).where(Order.order_id == "ORDREFUNDNEW")).scalar_one()
            order.created_at = datetime(2026, 10, 9, 0, 0, 0)
            before = datetime(2026, 10, 9, 11, 59, 59)
            cutoff = datetime(2026, 10, 9, 12, 0, 0)
            self.assertTrue(refund_is_eligible(order, payment=order.payment, now=before))
            self.assertFalse(refund_is_eligible(order, payment=order.payment, now=cutoff))

    def test_ticket_creation_is_persistent_owned_and_idempotent_per_conversation(self):
        with self.session_factory() as db:
            first = create_support_ticket(
                db, "CUST_LIFECYCLE_1", "General", "Please connect me to a person.",
                conversation_id=self.conversation_id,
            )
            replay = create_support_ticket(
                db, "CUST_LIFECYCLE_1", "General", "Repeated escalation.",
                conversation_id=self.conversation_id,
            )
            self.assertEqual(first.id, replay.id)
            with self.assertRaises(LookupError):
                create_support_ticket(
                    db, "CUST_LIFECYCLE_1", "Order", "Help with foreign order.",
                    order_id="ORDFOREIGN",
                )
            self.assertEqual(db.execute(select(SupportTicket)).scalars().all(), [first])

    def test_human_escalation_routes_through_workflow_and_returns_real_ticket_id(self):
        result = workflow_module.workflow.invoke({
            "query": "I need help from a human support agent because my order is delayed.",
            "customer_id": "CUST_LIFECYCLE_1",
            "conversation_id": self.conversation_id,
            "conversation_history": [],
        })
        self.assertIn("demo support ticket tkt-", result["response"].lower())
        self.assertIn("status OPEN", result["response"])
        self.assertNotIn("tracking timeline", result["response"].lower())
        with self.session_factory() as db:
            tickets = db.execute(select(SupportTicket)).scalars().all()
            self.assertEqual(len(tickets), 1)
            self.assertTrue(tickets[0].ticket_id.startswith("TKT-"))

    def test_support_ticket_creation_then_lookup_returns_persisted_status_and_details(self):
        created = workflow_module.workflow.invoke({
            "query": "I need help from a human support agent because my order is delayed.",
            "customer_id": "CUST_LIFECYCLE_1",
            "conversation_id": self.conversation_id,
            "conversation_history": [],
        })
        ticket_id_match = __import__("re").search(r"TKT-[A-Z0-9]+", created["response"])
        self.assertIsNotNone(ticket_id_match)
        ticket_id = ticket_id_match.group(0)

        lookup = workflow_module.workflow.invoke({
            "query": f"Show me the status of support ticket {ticket_id}.",
            "customer_id": "CUST_LIFECYCLE_1",
            "conversation_id": self.conversation_id,
            "conversation_history": [],
        })

        self.assertEqual(lookup["intent"], "support")
        self.assertIn(f"Support ticket {ticket_id} has status OPEN", lookup["response"])
        self.assertIn("Human Support Escalation", lookup["response"])
        self.assertNotIn("tracking", lookup["response"].lower())

    def test_invalid_support_ticket_id_does_not_fall_back_or_create_ticket(self):
        result = workflow_module.workflow.invoke({
            "query": "Track support ticket TKT-MISSING123.",
            "customer_id": "CUST_LIFECYCLE_1",
            "conversation_id": self.conversation_id,
            "conversation_history": [],
        })
        self.assertEqual(result["intent"], "support")
        self.assertIn("TKT-MISSING123 was not found", result["response"])
        with self.session_factory() as db:
            self.assertEqual(db.execute(select(SupportTicket)).scalars().all(), [])

    def test_ticket_lookup_classifier_precedes_order_tracking(self):
        for query in (
            "Show me the status of support ticket TKT-ABC123",
            "Track support ticket TKT-ABC123",
            "Look up ticket TKT-ABC123",
        ):
            with self.subTest(query=query):
                classified = classify_request(query)
                self.assertEqual(classified, {"domain": "support", "action": "support_ticket_lookup"})

    def test_refund_status_does_not_replace_delivery_tracking_stage(self):
        with self.session_factory() as db:
            order = db.execute(select(Order).where(Order.order_id == "ORDREFUNDNEW")).scalar_one()
            order.created_at = datetime.utcnow() - timedelta(hours=2)
            order.order_status = "Refund Requested"
            refund = Refund(
                order_id=order.id,
                refund_amount=order.total_amount,
                reason="Tracking separation test",
                status="REFUND_REQUESTED",
            )
            db.add(refund)
            db.commit()
            db.refresh(order)

            tracking = calculate_tracking(order, order.payment)

            self.assertEqual(tracking["status"], "Packing")
            self.assertEqual(tracking["order_status"], "Refund Requested")
            self.assertEqual(tracking["refund_status"], "REFUND_REQUESTED")
            self.assertEqual(tracking["payment_status"], "Paid")
            self.assertEqual(tracking["delivery_stage"], "Packing")

    def test_login_then_authenticated_chat_succeeds_and_guest_chat_is_rejected(self):
        class DeterministicWorkflow:
            @staticmethod
            def invoke(state):
                return {"intent": "order", "response": "Orders are available from your account."}

        with patch.object(api_module, "workflow", DeterministicWorkflow()), patch.object(api_module, "initialize_database", lambda: None):
            with TestClient(api_module.app) as client:
                guest = client.post("/chat", json={"message": "show my orders"})
                self.assertEqual(guest.status_code, 401)
                login = client.post("/auth/login", json={
                    "email": "lifecycle-test@example.test",
                    "password": "test-pass-123",
                })
                self.assertEqual(login.status_code, 200, login.text)
                session = login.json()
                headers = {
                    "X-Customer-Id": session["customerId"],
                    "Authorization": f"Bearer {session['sessionToken']}",
                }
                chat = client.post("/chat", headers=headers, json={
                    "message": "show my orders",
                    "customer_id": session["customerId"],
                    "conversation_id": "api-login-chat-test",
                })
                self.assertEqual(chat.status_code, 200, chat.text)
                self.assertEqual(chat.json()["response"], "Orders are available from your account.")

    def test_ready_reports_database_available_when_ollama_is_down(self):
        with patch.object(api_module, "urlopen", side_effect=OSError("offline")):
            result = api_module.ready()
        self.assertEqual(result["status"], "degraded")
        self.assertTrue(result["ready"])
        self.assertEqual(result["dependencies"]["ollama"], "unavailable")

    def test_server_checkout_recomputes_catalog_amount_and_replays_same_order(self):
        with patch.object(api_module, "initialize_database", lambda: None):
            with TestClient(api_module.app) as client:
                headers = {
                    "X-Customer-Id": "CUST_LIFECYCLE_1",
                    "Authorization": f"Bearer {api_module.issue_session_token('CUST_LIFECYCLE_1')}",
                }
                items = [{"id": "P_TEST_EARBUDS", "quantity": 1, "price": 0, "name": "Fake name"}]
                payment = client.post("/payment/demo", headers=headers, json={
                    "amount": 2950,
                    "paymentMethod": "Card",
                    "customerId": "CUST_LIFECYCLE_1",
                    "items": items,
                })
                self.assertEqual(payment.status_code, 200, payment.text)
                order_payload = {
                    "customerId": "CUST_LIFECYCLE_1",
                    "items": items,
                    "totals": {"total": 2950, "subtotal": 2500, "tax": 450, "shipping": 0},
                    "paymentMethod": "Card",
                    "paymentStatus": "Paid",
                    "orderStatus": "Order Confirmed",
                    "transactionId": payment.json()["transactionId"],
                    "paymentToken": payment.json()["paymentToken"],
                    "idempotencyKey": "test-checkout-key",
                    "shippingAddress": {"address": "Test"},
                }
                created = client.post("/orders", headers=headers, json=order_payload)
                self.assertEqual(created.status_code, 200, created.text)
                self.assertEqual(created.json()["totalAmount"], 2950)
                replay = client.post("/orders", headers=headers, json=order_payload)
                self.assertEqual(replay.status_code, 200, replay.text)
                self.assertTrue(replay.json()["idempotentReplay"])
                self.assertEqual(replay.json()["orderId"], created.json()["orderId"])

    def test_incompatible_database_schema_is_preserved(self):
        schema_dir = tempfile.TemporaryDirectory()
        self.addCleanup(schema_dir.cleanup)
        schema_path = Path(schema_dir.name) / "preserve_me.sqlite"
        schema_engine = __import__("sqlalchemy").create_engine(f"sqlite:///{schema_path.as_posix()}")
        with schema_engine.begin() as connection:
            connection.exec_driver_sql("CREATE TABLE customers (id INTEGER PRIMARY KEY)")
        with patch.object(init_db_module, "DATABASE_PATH", schema_path), patch.object(init_db_module, "engine", schema_engine):
            with self.assertRaises(RuntimeError):
                init_db_module.initialize_database()
        self.assertTrue(schema_path.exists())
        schema_engine.dispose()


if __name__ == "__main__":
    unittest.main()
