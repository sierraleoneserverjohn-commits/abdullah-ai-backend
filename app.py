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
    model: str = "llama-3.3-70b-versatile" # Receives model choice from frontend

@app.get("/")
def home():
    diagnostics = brain.get_api_diagnostics()
    return {
        "status": "online",
        "system": "Abdullah AI Brain Active",
        "learning_score": brain.get_learning_progress(),
        "api_diagnostics": diagnostics
    }

@app.post("/chat")
async def chat_endpoint(payload: ChatPayload):
    sana_text = payload.message.strip()
    if not sana_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Pass the message and the requested model to the brain
    result = brain.generate_chat_response(sana_text, payload.model)
    
    # Get fresh diagnostics after the chat
    diagnostics = brain.get_api_diagnostics()
    
    return {
        "response": result["reply"],
        "tokens_used_this_msg": result["tokens"],
        "model_used": result["model_used"],
        "learning_progress": brain.get_learning_progress(),
        "api_diagnostics": diagnostics
        }
    
