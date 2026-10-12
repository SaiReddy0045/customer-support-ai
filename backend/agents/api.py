from fastapi import FastAPI
from pydantic import BaseModel

from graph.workflow import workflow


app = FastAPI(
    title="ABC Technologies AI Customer Support API"
)


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    intent: str
    response: str


@app.get("/")
def home():
    return {
        "message": "ABC Technologies AI Customer Support API is running."
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    state = {
        "query": request.message,
        "intent": "",
        "response": ""
    }

    try:
        result = workflow.invoke(state)
    except Exception:
        result = {"intent": "support", "response": "I found the relevant information, but the AI response service is temporarily unavailable. Please try again shortly."}

    return ChatResponse(
        intent=result.get("intent", "support"),
        response=result.get("response", "I'm here to help.")
    )