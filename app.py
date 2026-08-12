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

print("⚡ Starting Abdullah Backend...")
parse_whatsapp_chat()

brain = AbdullahBrain()

class ChatPayload(BaseModel):
    message: str

@app.get("/")
def home():
    return {"status": "online", "system": "Abdullah AI Brain Active"}

@app.post("/chat")
async def chat_endpoint(payload: ChatPayload):
    sana_text = payload.message.strip()
    if not sana_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Generate response
    result = brain.generate_chat_response(sana_text)
    
    return {
        "response": result["reply"],
        "tokens_used": result["tokens_used"],
        "learning_progress": brain.get_learning_progress()
    }
    
