from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="tinyllama"
)

def handle_refund(user_query):
    response = llm.invoke(user_query)
    return response.content