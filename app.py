from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from brain import AbdullahBrain
import os

app = FastAPI(title="Johnny Tec - 5 API Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

brain = AbdullahBrain()

class ChatPayload(BaseModel):
    message: str
    api_choice: str = "auto"

@app.get("/")
def home():
    return {"status": "online", "backend_connected": True}

@app.get("/dashboard")
def get_dashboard():
    return brain.get_dashboard_metrics()

@app.post("/chat")
async def chat_endpoint(payload: ChatPayload):
    sana_text = payload.message.strip()
    if not sana_text:
        raise HTTPException(status_code=400, detail="Message empty.")

    # Run the chat through the engine
    result = brain.generate_chat_response(sana_text, payload.api_choice)
    
    # Return the AI response AND the fresh dashboard stats
    return {
        "response": result["reply"],
        "tokens_used": result["tokens"],
        "provider_used": result["provider"],
        "dashboard": brain.get_dashboard_metrics()
    }
    
