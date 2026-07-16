from langchain_ollama import ChatOllama
from langchain_core.messages import SystemMessage, HumanMessage

llm = ChatOllama(
    model="tinyllama"
)

prompt_file = open("prompts/intent_prompt.txt", "r")
system_prompt = prompt_file.read()
prompt_file.close()


def classify_intent(user_query):

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_query)
    ]

    response = llm.invoke(messages)

    return response.content.strip().lower()