from config.llm import llm
from langchain_core.messages import SystemMessage, HumanMessage

with open("prompts/billing_prompt.txt", "r") as prompt_file:
    billing_prompt = prompt_file.read()


def handle_billing(user_query):

    messages = [
        SystemMessage(content=billing_prompt),
        HumanMessage(content=user_query)
    ]

    response = llm.invoke(messages)

    return response.content