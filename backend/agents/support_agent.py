from langchain_core.messages import HumanMessage
from langchain.agents import create_agent

from config.llm import llm


SUPPORT_SYSTEM_PROMPT = """
You are the General Support Agent for ABC Technologies.

You handle general customer-support questions that do not require a
specialized billing, refund, order, or shopping workflow.

Rules:
- Be concise, polite, professional, and helpful.
- Use previous conversation context when it helps understand the customer.
- Do not invent company policies, prices, order details, payment information,
  refund eligibility, delivery status, or product specifications.
- If the customer's question belongs to a specialized workflow, explain what
  information is needed rather than pretending to perform an action.
- Never claim an action was completed unless the system actually performed it.
- Clearly distinguish known information from unavailable information.
"""


support_agent = create_agent(
    model=llm,
    tools=[],
    system_prompt=SUPPORT_SYSTEM_PROMPT,
)


def handle_support(
    user_query: str,
    customer_id: str | None = None,
    conversation_history: list[dict] | None = None,
) -> str:

    context = ""

    if customer_id:
        context += (
            "System-provided customer context:\n"
            f"customer_id = {customer_id}\n\n"
        )

    history = conversation_history or []

    if history:
        context += "Previous conversation:\n"

        for message in history[-10:]:
            role = message.get("role", "unknown")
            content = message.get("content", "")
            context += f"{role}: {content}\n"

        context += "\n"

    context += f"Current customer message:\n{user_query}"

    result = support_agent.invoke({
        "messages": [
            HumanMessage(content=context)
        ]
    })

    return result["messages"][-1].content
