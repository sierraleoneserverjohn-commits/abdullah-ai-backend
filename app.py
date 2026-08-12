import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from brain import AbdullahBrain
from upload_whatsapp import parse_whatsapp_chat

app = FastAPI(title="Abdullah AI Backend Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("⚡ Checking memory files...")
parse_whatsapp_chat()

brain = AbdullahBrain()

class ChatPayload(BaseModel):
    message: str
    model: str = "llama-3.3-70b-versatile"

@app.get("/")
def home():
    """Real-time health check endpoint to prove backend is connected."""
    return {
        "status": "online",
        "backend_connected": True,
        "system": "Abdullah AI Brain Active",
        "learning_score": brain.get_learning_progress(),
        "api_diagnostics": brain.get_api_diagnostics()
    }

@app.post("/chat")
async def chat_endpoint(payload: ChatPayload):
    sana_text = payload.message.strip()
    if not sana_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Generate response via the auto-routing brain
    result = brain.generate_chat_response(sana_text, payload.model)
    
    return {
        "response": result["reply"],
        "tokens_used": result["tokens"], # Fixed variable name to prevent NaN on frontend
        "model_used": result["model_used"],
        "learning_progress": brain.get_learning_progress(),
        "api_diagnostics": brain.get_api_diagnostics()
    }
    
