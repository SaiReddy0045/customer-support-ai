import re

ORDER_KEYWORDS = (
    "order",
    "track",
    "tracking",
    "shipment",
    "deliver",
    "delivery",
    "ship",
    "late",
    "delay",
    "status",
    "when will it arrive",
    "when will my order arrive",
    "where is my order",
    "where is it",
    "order status",
    "my order",
)

BILLING_KEYWORDS = (
    "payment",
    "charged",
    "charge",
    "billing",
    "invoice",
    "transaction",
    "transaction id",
    "paid",
    "paymnt",
    "paymnet",
    "card",
    "upi",
    "bank",
    "payments",
)

REFUND_KEYWORDS = (
    "refund",
    "rfund",
    "return",
    "money back",
    "eligible for refund",
    "refund status",
    "refund request",
)

SHOPPING_KEYWORDS = (
    "earphone",
    "earbuds",
    "headphone",
    "speaker",
    "watch",
    "camera",
    "laptop",
    "product",
    "products",
    "recommend",
    "buy",
    "under",
    "cheap",
    "smart home",
)

TYPO_MAP = {
    "waht": "what",
    "wher": "where",
    "ordr": "order",
    "rfund": "refund",
    "chek": "check",
    "paymnt": "payment",
    "paymnet": "payment",
    "i wnt": "i want",
    "whats": "what",
    "cant": "can t",
    "cansel": "cancel",
    "delivry": "delivery",
    "payemnt": "payment",
    "ordrs": "orders",
}


def normalize_query(user_query: str) -> str:
    text = (user_query or "").lower().replace("₹", " rs ").replace("₨", " rs ")
    text = text.replace("\n", " ")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    for bad, good in TYPO_MAP.items():
        text = text.replace(bad, good)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _match_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text for phrase in phrases)


def _extract_order_ids_from_history(conversation_history: list | None) -> list[str]:
    found: list[str] = []
    for message in conversation_history or []:
        content = str(message.get("content", "") or "")
        for match in re.findall(r"\bORD(?!ER\b)[A-Z0-9]+\b", content, flags=re.IGNORECASE):
            found.append(match.upper())
    return found


def classify_request(
    user_query: str,
    conversation_history: list | None = None,
    pending_action: str | None = None,
    awaiting_confirmation: bool = False,
) -> dict:
    """Return a domain + action pair for deterministic agent routing."""
    text = normalize_query(user_query or "")
    if not text and conversation_history:
        previous = next(
            (msg.get("content", "") for msg in reversed(conversation_history) if msg.get("role") == "user"),
            "",
        )
        text = normalize_query(previous)

    if not text:
        return {"domain": "support", "action": "fallback"}

    explicit_ticket_id = re.search(r"\bTKT-[A-Z0-9]+\b", user_query or "", flags=re.IGNORECASE)
    ticket_lookup_phrases = (
        "support ticket",
        "track ticket",
        "look up ticket",
        "lookup ticket",
        "ticket status",
    )
    if explicit_ticket_id and any(phrase in text for phrase in ticket_lookup_phrases):
        return {"domain": "support", "action": "support_ticket_lookup"}

    cancellation_eligibility_phrases = (
        "can i cancel my order",
        "can i cancel this",
        "can i cancel",
        "is my order eligible for cancellation",
        "can this be cancelled",
    )
    if _match_any(text, cancellation_eligibility_phrases):
        return {"domain": "order", "action": "cancellation_eligibility"}

    order_ids = _extract_order_ids_from_history(conversation_history)
    has_order_context = bool(order_ids)

    explicit_order_id = re.search(
        r"\bORD(?!ER\b)-?[A-Z0-9]+\b",
        user_query or "",
        flags=re.IGNORECASE,
    )
    if explicit_order_id and "cancel" in text:
        return {"domain": "order", "action": "cancel"}

    if pending_action == "cancel_order" and awaiting_confirmation:
        if text in {"no", "no cancel", "dont", "dont cancel", "don t", "don t cancel", "do not cancel", "never mind", "nevermind", "cancel that request"}:
            return {"domain": "order", "action": "cancel_reject"}
        if text in {
            "yes", "yes cancel", "yes cancel it", "cancel it", "cancel that", "cancel this",
            "yes please", "proceed", "proceed with cancellation", "confirm", "confirm cancellation",
            "yes proceed", "please proceed", "go ahead",
        }:
            return {"domain": "order", "action": "cancel_confirmation"}

    if pending_action == "refund_request" and awaiting_confirmation:
        if text in {"no", "no refund", "dont", "dont refund", "don t", "don t refund", "do not", "do not refund", "never mind", "nevermind", "cancel that request"}:
            return {"domain": "refund", "action": "refund_reject"}
        if text in {"yes", "yes please", "proceed", "confirm", "submit it", "go ahead", "yes submit", "submit refund", "proceed with refund"} or (
            re.match(r"^(yes|yeah|yep|sure|okay|ok|please|proceed|confirm)\b", text)
            and "refund" in text
            and any(verb in text for verb in ("submit", "proceed", "confirm"))
        ):
            return {"domain": "refund", "action": "refund_confirmation"}

    human_support_phrases = (
        "human",
        "live agent",
        "live representative",
        "customer representative",
        "customer support representative",
        "support representative",
        "talk to someone",
        "speak to someone",
    )
    if any(phrase in text for phrase in human_support_phrases) and any(
        term in text for term in ("agent", "representative", "person", "human", "someone")
    ):
        return {"domain": "support", "action": "create_support_ticket"}

    if text in {"yes", "yes please", "proceed", "confirm", "go ahead", "no", "no thanks", "never mind", "nevermind"}:
        return {"domain": "support", "action": "unbound_confirmation"}

    if "cancel that" in text or "cancel this" in text or "cancel it" in text:
        if has_order_context or "order" in text:
            return {"domain": "order", "action": "cancel"}

    if any(phrase in text for phrase in ("other order", "another order", "other one", "other order also")):
        return {"domain": "order", "action": "cancel"}

    cancel_phrases = (
        "cancel my order",
        "cancel order",
        "cancel this order",
        "cancel my latest order",
        "cancel the latest order",
        "i want to cancel",
        "cancel it",
        "cancel my order now",
        "cancel the order",
    )
    if _match_any(text, cancel_phrases):
        return {"domain": "order", "action": "cancel"}

    if any(phrase in text for phrase in ("first order", "second order", "order number 1", "order number 2", "previous order", "earlier order")):
        return {"domain": "order", "action": "track"}

    count_phrases = (
        "how many orders",
        "how many order",
        "count my orders",
        "count orders",
        "number of orders",
        "orders i have placed",
        "how many orders i have placed",
        "how many have i placed",
    )
    if _match_any(text, count_phrases) or ("how many" in text and "order" in text):
        return {"domain": "order", "action": "count_orders"}

    list_phrases = (
        "show my orders",
        "show all my orders",
        "show all the orders",
        "list my orders",
        "list all the orders",
        "list all orders",
        "list orders",
        "my orders",
        "all my orders",
    )
    if _match_any(text, list_phrases) or ("orders" in text and any(verb in text for verb in ("list", "show"))):
        return {"domain": "order", "action": "list_orders"}

    latest_phrases = (
        "latest order",
        "most recent order",
        "what is my latest order",
        "latest one",
    )
    if _match_any(text, latest_phrases):
        return {"domain": "order", "action": "latest_order"}

    cancellation_status_phrases = (
        "i cancelled my order",
        "my order was cancelled",
        "order cancelled",
        "cancellation status",
        "cancelled my order",
    )
    if _match_any(text, cancellation_status_phrases):
        return {"domain": "order", "action": "cancellation_status"}

    delay_phrases = (
        "why is my order delayed",
        "why this much delay to delivery",
        "why is it delayed",
        "my order is late",
        "delay to delivery",
        "delivery delay",
        "why is delivery delayed",
    )
    if _match_any(text, delay_phrases) or ("delay" in text and "order" in text):
        return {"domain": "order", "action": "delivery_delay"}

    eta_phrases = (
        "when will my order arrive",
        "when will it arrive",
        "delivery eta",
        "expected delivery",
        "estimated delivery",
    )
    if _match_any(text, eta_phrases):
        return {"domain": "order", "action": "delivery_eta"}

    track_phrases = (
        "where is my order",
        "track my order",
        "track order",
        "where is it",
        "where is my shipment",
        "what is the status of my order",
    )
    if _match_any(text, track_phrases) or ("order" in text and ("track" in text or "where" in text)):
        return {"domain": "order", "action": "track"}

    status_phrases = (
        "what is my order status",
        "order status",
        "status of my order",
        "what is my status",
        "what is my order",
    )
    if _match_any(text, status_phrases) or ("order" in text and "status" in text):
        return {"domain": "order", "action": "order_status"}

    invoice_phrases = (
        "order invoice",
        "invoice for my order",
        "my invoice",
        "get my invoice",
        "what is my invoice",
    )
    if _match_any(text, invoice_phrases):
        return {"domain": "order", "action": "order_invoice"}

    details_phrases = (
        "order details",
        "details of my order",
        "show order details",
    )
    if _match_any(text, details_phrases):
        return {"domain": "order", "action": "order_details"}

    if "payment" in text or "charged" in text or "billing" in text or "invoice" in text:
        if "show my payments" in text or "payment history" in text or ("show" in text and "payments" in text):
            return {"domain": "billing", "action": "payment_history"}
        if "how much did i pay" in text or "how much did i pay for" in text or "amount paid" in text:
            return {"domain": "billing", "action": "payment_amount"}
        if "charged twice" in text or "duplicate charge" in text or "double charged" in text:
            return {"domain": "billing", "action": "duplicate_charge"}
        if "check my payment" in text or "payment status" in text or "what is my payment status" in text:
            return {"domain": "billing", "action": "payment_status"}
        return {"domain": "billing", "action": "payment_status"}

    if "refund" in text or "return" in text or "money back" in text:
        process_phrases = (
            "refund policy",
            "refund policies",
            "refund rule",
            "refund rules",
            "refund time limit",
            "refund time limits",
            "refund window",
            "time limit for refund",
            "time limits for refund",
            "how long do i have to request a refund",
            "what are the refund terms",
            "what are the steps to get refund",
            "what are the steps to get a refund",
            "how do i get a refund",
            "how can i get refund",
            "what is the refund process",
            "how does refund work",
            "what do i need to do for refund",
            "how do refunds work",
            "steps to get refund",
            "steps to get a refund",
            "how can i get my money back",
        )
        if _match_any(text, process_phrases):
            return {"domain": "refund", "action": "refund_process_information"}
        if "status" in text and ("refund" in text or "return" in text):
            return {"domain": "refund", "action": "refund_status"}
        if "can i get a refund" in text or "refund eligibility" in text or "eligible for refund" in text or "am i eligible" in text or "is this order eligible" in text:
            return {"domain": "refund", "action": "refund_eligibility"}
        if any(phrase in text for phrase in ("i want a refund", "i need a refund", "refund my order", "request refund", "refund this order", "submit my refund", "refund it")):
            return {"domain": "refund", "action": "refund_request"}
        if "refund" in text and "how" in text:
            return {"domain": "refund", "action": "refund_process_information"}
        return {"domain": "refund", "action": "refund_eligibility"}

    if "earphone" in text or "earbuds" in text or "headphone" in text or "speaker" in text or "product" in text:
        if "under" in text and "rs" in text:
            return {"domain": "shopping", "action": "filtered_product_search"}
        if "how many products" in text or "count products" in text:
            return {"domain": "shopping", "action": "product_count"}
        if "show products" in text or "list products" in text:
            return {"domain": "shopping", "action": "product_list"}
        return {"domain": "shopping", "action": "product_search"}

    if "order" in text and "payment" in text:
        return {"domain": "multi", "action": "mixed_intent"}
    if "order" in text and "refund" in text:
        return {"domain": "multi", "action": "mixed_intent"}
    if "order" in text and "billing" in text:
        return {"domain": "multi", "action": "mixed_intent"}

    intents = detect_intents(text, conversation_history)
    if len(intents) > 1:
        return {"domain": "multi", "action": "mixed_intent"}
    if intents and intents[0] == "order":
        return {"domain": "order", "action": "track"}
    if intents and intents[0] == "billing":
        return {"domain": "billing", "action": "payment_status"}
    if intents and intents[0] == "refund":
        return {"domain": "refund", "action": "refund_eligibility"}
    if intents and intents[0] == "shopping":
        return {"domain": "shopping", "action": "product_search"}
    return {"domain": "support", "action": "fallback"}


def detect_intents(user_query: str, conversation_history: list | None = None) -> list[str]:
    text = normalize_query(user_query)
    if not text:
        if conversation_history:
            previous = next(
                (msg.get("content", "") for msg in reversed(conversation_history) if msg.get("role") == "user"),
                "",
            )
            if previous:
                return detect_intents(previous, None)
        return ["support"]

    if not any(token in text for token in ("order", "payment", "refund", "product", "track", "status", "help", "hello", "hi")):
        if conversation_history:
            previous = next(
                (msg.get("content", "") for msg in reversed(conversation_history) if msg.get("role") == "user"),
                "",
            )
            if previous:
                return detect_intents(previous + " " + text, None)

    intents: list[str] = []
    ordered_tokens = [
        ("order", ORDER_KEYWORDS),
        ("billing", BILLING_KEYWORDS),
        ("refund", REFUND_KEYWORDS),
        ("shopping", SHOPPING_KEYWORDS),
    ]

    for intent_name, keywords in ordered_tokens:
        if any(keyword in text for keyword in keywords):
            intents.append(intent_name)

    if "why" in text and "order" not in text and "payment" not in text and "refund" not in text:
        if conversation_history:
            recent = " ".join(msg.get("content", "") for msg in conversation_history[-4:])
            recent_text = normalize_query(recent)
            if "order" in recent_text:
                intents.append("order")
            elif "payment" in recent_text:
                intents.append("billing")
            elif "refund" in recent_text:
                intents.append("refund")

    return list(dict.fromkeys(intents)) or ["support"]


def classify_intent(user_query: str, conversation_history: list | None = None) -> str:
    """Compatibility wrapper for callers expecting a single domain label."""
    request = classify_request(user_query, conversation_history)
    return request.get("domain", "support")