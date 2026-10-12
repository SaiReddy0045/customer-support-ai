import hashlib
import base64
import hmac
import json
import logging
import re
import time
from urllib.error import URLError
from urllib.request import urlopen
from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select, text

from graph.workflow import workflow
from database.db import SessionLocal
from database.models import (
    Customer,
    Order,
    OrderItem,
    Product,
    Payment,
    Refund,
    SupportTicket,
)
from services.conversation_service import (
    get_or_create_conversation,
    get_conversation_messages,
    save_message,
)
from database.init_db import initialize_database
from services.tracking_service import calculate_tracking, effective_order_status, refund_ineligibility_reason, refund_is_eligible
from services.order_cancellation_service import cancellation_block_reason
from tools.refund_tools import create_refund_for_customer
from config.settings import env_value
from services.checkout_service import calculate_checkout
from services.support_ticket_service import create_support_ticket, ticket_to_dict

logger = logging.getLogger("abc_support.api")

app = FastAPI(
    title="ABC Technologies AI Customer Support API",
    description="Agentic AI e-commerce customer support system",
    version="1.0.0",
)


def hash_password(raw_password: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", raw_password.encode("utf-8"), b"abc-technologies", 200000).hex()


def verify_password(raw_password: str, password_hash: str) -> bool:
    return hash_password(raw_password) == password_hash


def validate_email(email: str) -> str:
    if not email or "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(status_code=422, detail="A valid email address is required.")
    return email.strip().lower()


def validate_password(password: str) -> str:
    if len(password) < 6:
        raise HTTPException(status_code=422, detail="Password must be at least 6 characters long.")
    return password


def require_customer_scope(http_request: Request, customer_id: str):
    header_customer_id = (http_request.headers.get("x-customer-id") or "").strip()
    authorization = (http_request.headers.get("authorization") or "").strip()
    if not header_customer_id or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="A valid customer session is required.")
    token_customer_id = verify_session_token(authorization.removeprefix("Bearer ").strip())
    if not token_customer_id:
        raise HTTPException(status_code=401, detail="Your customer session expired. Please sign in again.")
    if token_customer_id != customer_id or header_customer_id != customer_id:
        raise HTTPException(status_code=403, detail="Customer mismatch.")


def issue_demo_payment_token(customer_id: str, transaction_id: str, amount: float, payment_method: str) -> str:
    payload = json.dumps(
        {
            "sub": customer_id,
            "transaction_id": transaction_id,
            "amount": round(float(amount), 2),
            "payment_method": payment_method,
            "exp": int(time.time()) + 15 * 60,
        },
        separators=(",", ":"),
    ).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signature = hmac.new(_session_secret(), b"payment:" + encoded_payload, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{encoded_payload.decode('ascii')}.{encoded_signature.decode('ascii')}"


def verify_demo_payment_token(token: str, customer_id: str, transaction_id: str, amount: float, payment_method: str) -> bool:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected_signature = hmac.new(
            _session_secret(), b"payment:" + encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        actual_signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        if not hmac.compare_digest(expected_signature, actual_signature):
            return False
        payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        claims = json.loads(payload)
        return (
            claims.get("sub") == customer_id
            and claims.get("transaction_id") == transaction_id
            and round(float(claims.get("amount", -1)), 2) == round(float(amount), 2)
            and claims.get("payment_method") == payment_method
            and int(claims.get("exp", 0)) > int(time.time())
        )
    except (ValueError, TypeError, json.JSONDecodeError):
        return False


def _session_secret() -> bytes:
    return env_value("ABC_AUTH_SECRET", env_value("SECRET_KEY", "abc-technologies-local-development-secret")).encode("utf-8")


def issue_session_token(customer_id: str) -> str:
    payload = json.dumps({"sub": customer_id, "exp": int(time.time()) + 60 * 60 * 24 * 7}, separators=(",", ":")).encode("utf-8")
    encoded_payload = base64.urlsafe_b64encode(payload).rstrip(b"=")
    signature = hmac.new(_session_secret(), encoded_payload, hashlib.sha256).digest()
    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=")
    return f"{encoded_payload.decode('ascii')}.{encoded_signature.decode('ascii')}"


def verify_session_token(token: str) -> str | None:
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected_signature = hmac.new(
            _session_secret(), encoded_payload.encode("ascii"), hashlib.sha256
        ).digest()
        actual_signature = base64.urlsafe_b64decode(
            encoded_signature + "=" * (-len(encoded_signature) % 4)
        )
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None
        payload = base64.urlsafe_b64decode(
            encoded_payload + "=" * (-len(encoded_payload) % 4)
        )
        claims = json.loads(payload)
        if int(claims.get("exp", 0)) <= int(time.time()):
            return None
        return str(claims.get("sub") or "") or None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None


app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in env_value("CORS_ORIGINS", "").split(",") if origin.strip()],
    allow_origin_regex=env_value("CORS_ORIGIN_REGEX", r"https?://(localhost|127\.0\.0\.1):\d+"),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup_database():
    try:
        initialize_database()
        if env_value("APP_ENV", "development").lower() == "production" and _session_secret() == b"abc-technologies-local-development-secret":
            raise RuntimeError("Set ABC_AUTH_SECRET to a strong secret before production startup.")
    except Exception:
        logger.exception("Backend startup initialization failed")
        raise


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class OrderItemInput(BaseModel):
    id: str
    quantity: int = Field(gt=0)


class DemoPaymentRequest(BaseModel):
    amount: float = Field(gt=0)
    paymentMethod: str = Field(min_length=1, max_length=40)
    customerId: str
    items: list[OrderItemInput]


class OrderRequest(BaseModel):
    customerId: str
    items: list[OrderItemInput]
    totals: dict
    paymentMethod: str
    paymentStatus: str
    orderStatus: str
    transactionId: Optional[str] = None
    shippingAddress: dict
    paymentToken: Optional[str] = None
    idempotencyKey: Optional[str] = None


class ChatRequest(BaseModel):
    message: str
    customer_id: Optional[str] = None
    conversation_id: Optional[str] = None
    metadata: Optional[dict] = None


class ChatResponse(BaseModel):
    intent: str
    response: str
    customer_id: Optional[str] = None
    conversation_id: Optional[str] = None


class SupportTicketRequest(BaseModel):
    category: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=4000)
    order_id: Optional[str] = None
    conversation_id: str = Field(min_length=1, max_length=100)


@app.get("/")
def home():
    return {
        "message": "ABC Technologies AI Customer Support API is running.",
        "status": "ok",
    }


@app.get("/health")
def health():
    return {"status": "alive"}


@app.get("/ready")
def ready():
    database_ready = False
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        database_ready = True
    except Exception:
        logger.exception("Database readiness check failed")

    ollama_base_url = env_value("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    ollama_model = env_value("OLLAMA_MODEL", "llama3.2:1b")
    ollama_ready = False
    ollama_error = None
    try:
        with urlopen(f"{ollama_base_url}/api/tags", timeout=float(env_value("OLLAMA_HEALTH_TIMEOUT_SECONDS", "2"))) as response:
            payload = json.loads(response.read().decode("utf-8"))
        available_models = {item.get("name", "") for item in payload.get("models", [])}
        ollama_ready = ollama_model in available_models or f"{ollama_model}:latest" in available_models
        if not ollama_ready:
            ollama_error = "Configured model is not present in Ollama."
    except (OSError, URLError, ValueError, TimeoutError):
        ollama_error = "Ollama is unavailable. Database-backed features remain available."

    return {
        "status": "ready" if database_ready and ollama_ready else "degraded" if database_ready else "unavailable",
        "ready": database_ready,
        "dependencies": {
            "database": "ready" if database_ready else "unavailable",
            "ollama": "ready" if ollama_ready else "unavailable",
        },
        "ollama_model": ollama_model,
        "ollama_message": ollama_error,
    }


@app.post("/auth/register")
def register(request: RegisterRequest):
    db = SessionLocal()

    try:
        name = request.name.strip()
        email = validate_email(request.email)
        password = validate_password(request.password)


        if not name:
            raise HTTPException(status_code=422, detail="Name is required.")

        existing = db.execute(select(Customer).where(Customer.email == email)).scalar_one_or_none()
        if existing:
            raise HTTPException(status_code=400, detail="An account with this email already exists.")

        count = db.execute(select(Customer)).scalars().all()
        customer_id = f"CUST{1001 + len(count):04d}"

        customer = Customer(
            customer_id=customer_id,
            name=name,
            email=email,
            password_hash=hash_password(password),
            phone=None,
        )

        db.add(customer)
        db.commit()
        db.refresh(customer)

        return {
            "customerId": customer.customer_id,
            "customer_id": customer.customer_id,
            "name": customer.name,
            "email": customer.email,
            "sessionToken": issue_session_token(customer.customer_id),
        }

    finally:
        db.close()


@app.post("/auth/login")
def login(request: LoginRequest):
    db = SessionLocal()

    try:
        email = validate_email(request.email)
        password = validate_password(request.password)

        customer = db.execute(select(Customer).where(Customer.email == email)).scalar_one_or_none()
        if not customer or not verify_password(password, customer.password_hash):
            raise HTTPException(status_code=401, detail="Invalid email or password.")

        return {
            "customerId": customer.customer_id,
            "customer_id": customer.customer_id,
            "name": customer.name,
            "email": customer.email,
            "sessionToken": issue_session_token(customer.customer_id),
        }

    finally:
        db.close()


@app.get("/auth/me")
def current_user(http_request: Request):
    customer_id = (http_request.headers.get("x-customer-id") or "").strip()
    if not customer_id:
        raise HTTPException(status_code=401, detail="Customer authentication is required.")
    require_customer_scope(http_request, customer_id)
    with SessionLocal() as db:
        customer = db.execute(select(Customer).where(Customer.customer_id == customer_id)).scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=401, detail="Customer session is no longer valid.")
        return {
            "customerId": customer.customer_id,
            "customer_id": customer.customer_id,
            "name": customer.name,
            "email": customer.email,
        }


@app.post("/orders")
def create_order(request: OrderRequest, http_request: Request):
    db = SessionLocal()

    try:
        require_customer_scope(http_request, request.customerId)

        customer = db.execute(
            select(Customer).where(
                Customer.customer_id == request.customerId
            )
        ).scalar_one_or_none()

        if not customer:
            raise HTTPException(
                status_code=404,
                detail=f"Customer {request.customerId} was not found.",
            )

        if request.idempotencyKey:
            existing_order = db.execute(
                select(Order).where(Order.idempotency_key == request.idempotencyKey)
            ).scalar_one_or_none()
            if existing_order:
                if existing_order.customer_id != customer.id:
                    raise HTTPException(status_code=409, detail="This checkout key has already been used.")
                existing_payment = db.execute(
                    select(Payment).where(Payment.order_id == existing_order.id)
                ).scalar_one_or_none()
                return {
                    "orderId": existing_order.order_id,
                    "customerId": customer.customer_id,
                    "totalAmount": existing_order.total_amount,
                    "orderStatus": effective_order_status(existing_order, existing_payment),
                    "paymentStatus": existing_payment.payment_status if existing_payment else "Pending Payment",
                    "transactionId": existing_payment.transaction_id if existing_payment else None,
                    "createdAt": existing_order.created_at.isoformat(),
                    "idempotentReplay": True,
                }

        input_items = [item.model_dump() for item in request.items]
        try:
            validated_items, checkout_totals = calculate_checkout(db, input_items)
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        order_id = f"ORD{uuid4().hex[:8].upper()}"

        address = request.shippingAddress

        shipping_address = ", ".join(
            str(value)
            for value in [
                address.get("fullName"),
                address.get("phone"),
                address.get("address"),
                address.get("city"),
                address.get("state"),
                address.get("pincode"),
            ]
            if value
        )

        requested_payment_status = (request.paymentStatus or "").strip()
        payment_amount = checkout_totals["total"]
        payment_is_paid = bool(
            request.transactionId
            and request.paymentToken
            and verify_demo_payment_token(
                request.paymentToken,
                request.customerId,
                request.transactionId,
                payment_amount,
                request.paymentMethod,
            )
        )
        if request.transactionId and not payment_is_paid:
            raise HTTPException(status_code=400, detail="The demo payment receipt is invalid or expired.")
        initial_order_status = "Order Confirmed" if payment_is_paid else "Pending Payment"
        order = Order(
            order_id=order_id,
            idempotency_key=request.idempotencyKey,
            customer_id=customer.id,
            order_status=initial_order_status,
            total_amount=payment_amount,
            shipping_address=shipping_address,
        )

        db.add(order)
        db.flush()

        for item in validated_items:
            product = db.execute(
                select(Product).where(
                    Product.product_id == item["id"]
                )
            ).scalar_one_or_none()

            if not product:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {item['id']} was not found.",
                )

            quantity = item["quantity"]

            if product.stock < quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient stock for {product.name}.",
                )

            product.stock -= quantity

            db.add(
                OrderItem(
                    order_id=order.id,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=float(product.price),
                )
            )

        payment = None
        if request.transactionId:
            payment = Payment(
                    order_id=order.id,
                    transaction_id=request.transactionId,
                    amount=payment_amount,
                    payment_method=request.paymentMethod,
                    payment_status="Paid",
                )
            db.add(payment)

        db.commit()
        db.refresh(order)

        return {
            "orderId": order.order_id,
            "customerId": request.customerId,
            "items": validated_items,
            "totals": checkout_totals,
            "totalAmount": order.total_amount,
            "paymentMethod": request.paymentMethod,
            "paymentStatus": "Paid" if payment_is_paid else "Pending Payment",
            "orderStatus": effective_order_status(order, payment),
            "transactionId": request.transactionId,
            "shippingAddress": request.shippingAddress,
            "createdAt": order.created_at.isoformat(),
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


@app.post("/payment/demo")
def process_demo_payment(request: DemoPaymentRequest, http_request: Request):
    requested_amount = request.amount
    payment_method = request.paymentMethod
    customer_id = request.customerId

    if not customer_id:
        raise HTTPException(status_code=401, detail="Customer authentication is required.")
    require_customer_scope(http_request, customer_id)
    db = SessionLocal()
    try:
        customer = db.execute(
            select(Customer).where(Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found.")
        try:
            _, totals = calculate_checkout(db, [item.model_dump() for item in request.items])
        except LookupError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        amount = totals["total"]
        if round(requested_amount, 2) != round(amount, 2):
            raise HTTPException(status_code=409, detail="Cart prices changed. Refresh your cart before payment.")
    finally:
        db.close()

    transaction_id = f"DEMO-{uuid4().hex[:12].upper()}"
    payment_token = issue_demo_payment_token(customer_id, transaction_id, amount, payment_method)
    return {
        "success": True,
        "transactionId": transaction_id,
        "amount": amount,
        "paymentMethod": payment_method,
        "paidAt": datetime.utcnow().isoformat(),
        "paymentToken": payment_token,
        "demo": True,
    }


@app.get("/orders/{customer_id}")
def get_orders(customer_id: str, http_request: Request):
    db = SessionLocal()

    try:
        require_customer_scope(http_request, customer_id)

        customer = db.execute(
            select(Customer).where(
                Customer.customer_id == customer_id
            )
        ).scalar_one_or_none()

        if not customer:
            raise HTTPException(
                status_code=404,
                detail="Customer not found.",
            )

        orders = db.execute(
            select(Order)
            .where(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
        ).scalars().all()

        result = []

        for order in orders:
            payment = db.execute(
                select(Payment).where(
                    Payment.order_id == order.id
                )
            ).scalar_one_or_none()

            tracking = calculate_tracking(order, payment)

            result.append({
                "orderId": order.order_id,
                "customerId": customer.customer_id,
                "totalAmount": order.total_amount,
                "orderStatus": tracking["status"],
                "paymentStatus": (
                    payment.payment_status
                    if payment else None
                ),
                "transactionId": (
                    payment.transaction_id
                    if payment else None
                ),
                "shippingAddress": order.shipping_address,
                "createdAt": order.created_at.isoformat(),
                "tracking": tracking,
                "refundEligible": refund_is_eligible(order, payment=payment),
                "cancellationEligible": cancellation_block_reason(order) is None,
            })

        return result

    finally:
        db.close()


@app.get("/orders/detail/{order_id}")
def get_order_detail(order_id: str, http_request: Request):
    db = SessionLocal()

    try:
        order = db.execute(
            select(Order).where(
                Order.order_id == order_id
            )
        ).scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        customer = db.get(Customer, order.customer_id)
        if not customer:
            raise HTTPException(status_code=403, detail="Customer mismatch.")
        require_customer_scope(http_request, customer.customer_id)

        items = db.execute(
            select(OrderItem, Product)
            .join(
                Product,
                OrderItem.product_id == Product.id,
            )
            .where(OrderItem.order_id == order.id)
        ).all()

        payment = db.execute(
            select(Payment).where(
                Payment.order_id == order.id
            )
        ).scalar_one_or_none()

        tracking = calculate_tracking(order, payment)

        return {
            "orderId": order.order_id,
            "customerId": customer.customer_id if customer else None,
            "orderStatus": tracking["status"],
            "totalAmount": order.total_amount,
            "shippingAddress": order.shipping_address,
            "createdAt": order.created_at.isoformat(),
            "items": [
                {
                    "id": product.product_id,
                    "name": product.name,
                    "quantity": item.quantity,
                    "price": item.unit_price,
                }
                for item, product in items
            ],
            "paymentStatus": (
                payment.payment_status
                if payment else None
            ),
            "paymentMethod": (
                payment.payment_method
                if payment else None
            ),
            "transactionId": (
                payment.transaction_id
                if payment else None
            ),
            "tracking": tracking,
            "refundEligible": refund_is_eligible(order, payment=payment),
            "cancellationEligible": cancellation_block_reason(order) is None,
        }

    finally:
        db.close()


@app.post("/refund")
def create_refund(request: dict, http_request: Request):
    db = SessionLocal()

    try:
        order_id = request.get("orderId")
        reason = request.get(
            "reason",
            "Customer requested a refund.",
        )

        order = db.execute(
            select(Order).where(
                Order.order_id == order_id
            )
        ).scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=404,
                detail="Order not found.",
            )

        customer = db.get(Customer, order.customer_id)
        if not customer:
            raise HTTPException(status_code=403, detail="Order owner not found.")
        require_customer_scope(http_request, customer.customer_id)

        existing = db.execute(
            select(Refund)
            .where(
                Refund.order_id == order.id,
                Refund.status.in_(
                    [
                        "Requested", "Approved", "Processing", "Completed",
                        "Refund Requested", "Refund Approved", "Refund Completed",
                        "REFUND_REQUESTED", "REFUND_APPROVED", "REFUND_PROCESSING", "REFUND_COMPLETED",
                    ]
                ),
            )
        ).scalar_one_or_none()

        if existing:
            return {
                "orderId": order.order_id,
                "refundId": f"REF-{existing.id:06d}",
                "status": existing.status,
                "message": "A refund request already exists.",
            }

        payment = db.execute(select(Payment).where(Payment.order_id == order.id)).scalar_one_or_none()
        tracking = calculate_tracking(order, payment)
        ineligibility_reason = refund_ineligibility_reason(order, payment=payment)
        if ineligibility_reason:
            raise HTTPException(
                status_code=409,
                detail=f"Order {order.order_id} is not eligible for a refund: {ineligibility_reason}",
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

        return {
            "orderId": order.order_id,
            "refundId": f"REF-{refund.id:06d}",
            "refundAmount": refund.refund_amount,
            "reason": refund.reason,
            "status": refund.status,
            "message": "Simulated refund request recorded; no money was returned by this demo.",
            "demo": True,
        }

    finally:
        db.close()


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, http_request: Request):
    db = SessionLocal()

    try:
        if not request.customer_id:
            raise HTTPException(status_code=401, detail="Customer authentication is required for support conversations.")
        require_customer_scope(http_request, request.customer_id)
        customer = db.execute(select(Customer).where(Customer.customer_id == request.customer_id)).scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found.")

        conversation_id = request.conversation_id or str(uuid4())
        conversation = get_or_create_conversation(
            db=db,
            conversation_id=conversation_id,
            customer_id=request.customer_id,
        )

        metadata = request.metadata or {}
        referenced_order_id = str(metadata.get("orderId") or "").strip()
        if referenced_order_id:
            referenced_order = db.execute(
                select(Order).where(
                    Order.order_id == referenced_order_id,
                    Order.customer_id == customer.id,
                )
            ).scalar_one_or_none()
            if referenced_order:
                conversation.current_order_id = referenced_order.order_id
                db.commit()

        history = get_conversation_messages(db=db, conversation=conversation)
        state = {
            "query": request.message,
            "intent": "",
            "response": "",
            "customer_id": request.customer_id,
            "conversation_id": conversation.conversation_id,
            "conversation_history": history,
            "context": metadata,
        }

        try:
            result = workflow.invoke(state)
            response_text = result.get("response") or "I can help with that."
            intent = result.get("intent") or "support"
        except Exception as exc:
            logger.warning("Support workflow failed (%s)", type(exc).__name__)
            response_text = "The AI assistant is temporarily unavailable. Database-backed order, payment, and refund operations remain available through their direct account pages. Please retry your support question shortly."
            intent = "support"

        save_message(db=db, conversation=conversation, role="user", content=request.message)
        save_message(db=db, conversation=conversation, role="assistant", content=response_text, agent=intent)

        return ChatResponse(
            intent=intent,
            response=response_text,
            customer_id=request.customer_id or conversation.customer_id and db.get(Customer, conversation.customer_id).customer_id,
            conversation_id=conversation.conversation_id,
        )

    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc))
    except HTTPException:
        db.rollback()
        raise
    except Exception as exc:
        db.rollback()
        logger.exception("Chat request failed (%s)", type(exc).__name__)
        raise HTTPException(status_code=500, detail="AI support request failed.") from exc
    finally:
        db.close()


@app.get("/orders/{customer_id}/tracking")
def get_order_tracking(customer_id: str, http_request: Request):
    db = SessionLocal()
    try:
        customer = db.execute(select(Customer).where(Customer.customer_id == customer_id)).scalar_one_or_none()
        if not customer:
            order = db.execute(select(Order).where(Order.order_id == customer_id)).scalar_one_or_none()
            if not order:
                raise HTTPException(status_code=404, detail="Sorry, I couldn't find that order in your account.")
            owner = db.get(Customer, order.customer_id)
            if not owner:
                raise HTTPException(status_code=403, detail="I couldn't access that order.")
            require_customer_scope(http_request, owner.customer_id)
            payment = db.execute(select(Payment).where(Payment.order_id == order.id)).scalar_one_or_none()
            return calculate_tracking(order, payment)

        require_customer_scope(http_request, customer.customer_id)

        orders = db.execute(
            select(Order)
            .where(Order.customer_id == customer.id)
            .order_by(Order.created_at.desc())
        ).scalars().all()

        tracking_results = []
        for order in orders:
            payment = db.execute(select(Payment).where(Payment.order_id == order.id)).scalar_one_or_none()
            tracking_results.append(calculate_tracking(order, payment))
        return tracking_results
    finally:
        db.close()


@app.get("/refunds")
def get_refunds(http_request: Request):
    customer_id = (http_request.headers.get("x-customer-id") or "").strip()
    if not customer_id:
        raise HTTPException(status_code=401, detail="Customer authentication is required.")
    require_customer_scope(http_request, customer_id)
    db = SessionLocal()
    try:
        customer = db.execute(select(Customer).where(Customer.customer_id == customer_id)).scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found.")
        refunds = db.execute(
            select(Refund, Order)
            .join(Order, Refund.order_id == Order.id)
            .where(Order.customer_id == customer.id)
            .order_by(Refund.created_at.desc())
        ).all()
        return [
            {
                "refundId": f"REF-{refund.id:06d}",
                "orderId": order.order_id,
                "amount": refund.refund_amount,
                "reason": refund.reason,
                "status": refund.status,
                "requestedAt": refund.created_at.isoformat(),
            }
            for refund, order in refunds
        ]
    finally:
        db.close()


@app.get("/refunds/{refund_id}")
def get_refund(refund_id: str, http_request: Request):
    customer_id = (http_request.headers.get("x-customer-id") or "").strip()
    if not customer_id:
        raise HTTPException(status_code=401, detail="Customer authentication is required.")
    require_customer_scope(http_request, customer_id)
    try:
        refund_pk = int(refund_id.removeprefix("REF-"))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Refund not found.") from exc

    db = SessionLocal()
    try:
        refund = db.get(Refund, refund_pk)
        if not refund:
            raise HTTPException(status_code=404, detail="Refund not found.")
        order = db.get(Order, refund.order_id)
        customer = db.get(Customer, order.customer_id) if order else None
        if not customer or customer.customer_id != customer_id:
            raise HTTPException(status_code=403, detail="I couldn't access that refund.")
        return {
            "refundId": f"REF-{refund.id:06d}",
            "orderId": order.order_id,
            "amount": refund.refund_amount,
            "reason": refund.reason,
            "status": refund.status,
            "requestedAt": refund.created_at.isoformat(),
        }
    finally:
        db.close()


@app.post("/support/tickets")
def create_ticket(request: SupportTicketRequest, http_request: Request):
    customer_id = (http_request.headers.get("x-customer-id") or "").strip()
    if not customer_id:
        raise HTTPException(status_code=401, detail="Customer authentication is required.")
    require_customer_scope(http_request, customer_id)
    db = SessionLocal()
    try:
        ticket = create_support_ticket(
            db,
            customer_id,
            request.category,
            request.description,
            request.order_id,
            request.conversation_id,
        )
        return ticket_to_dict(ticket)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    finally:
        db.close()


@app.get("/support/tickets")
def get_support_tickets(http_request: Request):
    customer_id = (http_request.headers.get("x-customer-id") or "").strip()
    if not customer_id:
        raise HTTPException(status_code=401, detail="Customer authentication is required.")
    require_customer_scope(http_request, customer_id)
    db = SessionLocal()
    try:
        customer = db.execute(select(Customer).where(Customer.customer_id == customer_id)).scalar_one_or_none()
        if not customer:
            raise HTTPException(status_code=401, detail="Customer session is no longer valid.")
        tickets = db.execute(
            select(SupportTicket)
            .where(SupportTicket.customer_id == customer.id)
            .order_by(SupportTicket.created_at.desc())
        ).scalars().all()
        return [ticket_to_dict(ticket) for ticket in tickets]
    finally:
        db.close()


@app.get("/support/tickets/{ticket_id}")
def get_support_ticket(ticket_id: str, http_request: Request):
    customer_id = (http_request.headers.get("x-customer-id") or "").strip()
    if not customer_id:
        raise HTTPException(status_code=401, detail="Customer authentication is required.")
    require_customer_scope(http_request, customer_id)
    db = SessionLocal()
    try:
        ticket = db.execute(
            select(SupportTicket)
            .join(Customer, SupportTicket.customer_id == Customer.id)
            .where(SupportTicket.ticket_id == ticket_id, Customer.customer_id == customer_id)
        ).scalar_one_or_none()
        if not ticket:
            raise HTTPException(status_code=404, detail="Support ticket not found.")
        return ticket_to_dict(ticket)
    finally:
        db.close()

@app.get("/products")
def get_products(search: Optional[str] = None, category: Optional[str] = None, max_price: Optional[float] = None, min_rating: Optional[float] = None, featured: Optional[bool] = None):
    db = SessionLocal()
    try:
        query = select(Product)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                (Product.name.ilike(pattern))
                | (Product.category.ilike(pattern))
                | (Product.description.ilike(pattern))
            )
        if category:
            query = query.where(Product.category.ilike(f"%{category.strip()}%"))
        if max_price is not None:
            query = query.where(Product.price <= max_price)
        if min_rating is not None:
            query = query.where(Product.rating >= min_rating)
        if featured is not None:
            query = query.where(Product.featured == featured)

        query = query.order_by(Product.featured.desc(), Product.rating.desc(), Product.price.asc())
        products = db.execute(query).scalars().all()

        return [
            {
                "id": product.product_id,
                "productId": product.product_id,
                "name": product.name,
                "category": product.category,
                "description": product.description,
                "price": product.price,
                "stock": product.stock,
                "rating": product.rating,
                "image": product.image,
                "featured": product.featured,
                "reviews": 0,
                "specs": {},
            }
            for product in products
        ]
    finally:
        db.close()


@app.get("/products/{product_id}")
def get_product(product_id: str):
    db = SessionLocal()
    try:
        if product_id.isdigit():
            product = db.execute(select(Product).where(Product.id == int(product_id))).scalar_one_or_none()
        else:
            product = db.execute(select(Product).where(Product.product_id == product_id)).scalar_one_or_none()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found.")

        return {
            "id": product.product_id,
            "productId": product.product_id,
            "name": product.name,
            "category": product.category,
            "description": product.description,
            "price": product.price,
            "stock": product.stock,
            "rating": product.rating,
            "reviews": 0,
            "image": product.image,
            "featured": product.featured,
            "specs": {},
        }
    finally:
        db.close()

