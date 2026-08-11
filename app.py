import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File
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

print("⚡ Auto-parsing WhatsApp Chat...")
parse_whatsapp_chat()

brain = AbdullahBrain()

class ChatPayload(BaseModel):
    message: str

@app.get("/")
def home():
    return {
        "status": "online",
        "system": "Abdullah AI Brain Active",
        "base_memories": len(brain.base_memories),
        "live_learning_score": brain.get_learning_progress()
    }

@app.post("/chat")
async def chat_endpoint(payload: ChatPayload):
    sana_text = payload.message.strip()
    if not sana_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Get reply and tokens from brain
    result = brain.generate_chat_response(sana_text)
    
    return {
        "response": result["reply"],
        "tokens_used": result["tokens"],
        "learning_progress": brain.get_learning_progress()
    }
    
