from config.llm import llm
from utils.prompt_loader import load_prompt

from langchain_core.messages import SystemMessage, HumanMessage


refund_prompt = load_prompt("refund_prompt.txt")


def handle_refund(user_query: str) -> str:
    """
    Handle refund-related customer queries.
    """

    messages = [
        SystemMessage(content=refund_prompt),
        HumanMessage(content=user_query)
    ]

    response = llm.invoke(messages)

    return response.content