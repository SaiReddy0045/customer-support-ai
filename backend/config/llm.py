from langchain_ollama import ChatOllama
from config.settings import env_value

llm = ChatOllama(
    model=env_value("OLLAMA_MODEL", "llama3.2:1b"),
    base_url=env_value("OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
    temperature=0,
    request_timeout=float(env_value("OLLAMA_TIMEOUT_SECONDS", "12")),
    num_predict=int(env_value("OLLAMA_NUM_PREDICT", "192")),
)