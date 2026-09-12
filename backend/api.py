from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from graph.workflow import workflow

app = FastAPI(
    title="ABC Technologies AI Customer Support API"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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

    result = workflow.invoke(state)

    return ChatResponse(
        intent=result["intent"],
        response=result["response"]
    )