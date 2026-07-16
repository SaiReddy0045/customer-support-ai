from config.llm import llm
from langchain_core.messages import SystemMessage, HumanMessage

from billing_agent import handle_billing
from refund_agent import handle_refund


# Read the system prompt
with open("prompts/support_prompt.txt", "r") as prompt_file:
    system_prompt = prompt_file.read()


while True:

    user_query = input("\nCustomer: ")

    # Exit
    if user_query.lower() == "exit":
        print("\nThank you for using ABC Technologies Customer Support.")
        break

    # ---------- ROUTER ----------

    if any(word in user_query.lower() for word in
           ["payment", "invoice", "subscription", "billing"]):

        response = handle_billing(user_query)

    elif any(word in user_query.lower() for word in
             ["refund", "money back", "return"]):

        response = handle_refund(user_query)

    else:

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_query)
        ]

        ai_response = llm.invoke(messages)
        response = ai_response.content

    print("\nAI:", response)