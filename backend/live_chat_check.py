import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL = os.getenv("ABC_TEST_EMAIL", "demo@abc-technologies.com")
PASSWORD = os.getenv("ABC_TEST_PASSWORD", "demo123")
QUERIES = (
    "Where is my order?",
    "Check my payment",
    "What are the steps to get a refund?",
    "Talk to a human",
)


def post_json(path: str, payload: dict, headers: dict | None = None) -> dict:
    request_headers = {"Content-Type": "application/json", **(headers or {})}
    request = Request(
        f"{API_BASE_URL}{path}",
        data=json.dumps(payload).encode("utf-8"),
        headers=request_headers,
        method="POST",
    )
    with urlopen(request, timeout=25) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    try:
        session = post_json("/auth/login", {"email": EMAIL, "password": PASSWORD})
        customer_id = session["customerId"]
        headers = {
            "X-Customer-Id": customer_id,
            "Authorization": f"Bearer {session['sessionToken']}",
        }
        for query in QUERIES:
            response = post_json(
                "/chat",
                {"message": query, "customer_id": customer_id},
                headers,
            )
            print(f"{query} => {response.get('response', '')}")
        return 0
    except HTTPError as exc:
        print(f"API returned HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')}")
    except (URLError, TimeoutError, KeyError, ValueError) as exc:
        print(f"Chat check failed: {exc}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
