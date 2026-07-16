from config.llm import llm
from langchain_core.messages import SystemMessage, HumanMessage


with open("prompts/refund_prompt.txt", "r") as prompt_file:
    refund_prompt = prompt_file.read()


def handle_refund(user_query):

    messages = [
        SystemMessage(content=refund_prompt),
        HumanMessage(content=user_query)
    ]

    response = llm.invoke(messages)

    return response.content