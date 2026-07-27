from config.llm import llm
from backend.agents.utils.prompt_loader import load_prompt

from langchain_core.messages import SystemMessage, HumanMessage


support_prompt = load_prompt("support_prompt.txt")


def handle_support(user_query: str) -> str:
    """
    Handle general customer support queries.
    """

    messages = [
        SystemMessage(content=support_prompt),
        HumanMessage(content=user_query)
    ]

    response = llm.invoke(messages)

    return response.content