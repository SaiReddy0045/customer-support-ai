from config.llm import llm
from backend.agents.utils.prompt_loader import load_prompt

from langchain_core.messages import SystemMessage, HumanMessage


billing_prompt = load_prompt("billing_prompt.txt")


def handle_billing(user_query: str) -> str:
    """
    Handle billing-related customer queries.
    """

    messages = [
        SystemMessage(content=billing_prompt),
        HumanMessage(content=user_query)
    ]

    response = llm.invoke(messages)

    return response.content