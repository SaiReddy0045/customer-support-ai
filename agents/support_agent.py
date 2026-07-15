from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOllama(
    model="tinyllama"
)

prompt_file = open("prompts/support_prompt.txt", "r")
system_prompt = prompt_file.read()
prompt_file.close()

while True:
    user_query = input("Customer: ")

    if user_query.lower() == "exit":
        print("Goodbye!")
        break

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_query)
    ]

    response = llm.invoke(messages)
    print("\nAI:", response.content)
