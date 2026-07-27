from config.llm import llm
from backend.agents.utils.prompt_loader import load_prompt

from langchain_core.messages import SystemMessage, HumanMessage


intent_prompt = load_prompt("intent_prompt.txt")


def classify_intent(user_query: str) -> str:
    """
    Classify the user's intent as:
    billing, refund, or support.
    """

    messages = [
        SystemMessage(content=intent_prompt),
        HumanMessage(content=user_query)
    ]

    response = llm.invoke(messages)

    return response.content.strip().lower()