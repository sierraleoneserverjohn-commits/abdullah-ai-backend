from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from brain import AbdullahBrain
from upload_whatsapp import parse_whatsapp_chat

app = FastAPI(title="Abdullah AI - Johnny Tec 5-API Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("⚡ Booting Johnny Tec AI Engine...")
parse_whatsapp_chat()

brain = AbdullahBrain()

class ChatPayload(BaseModel):
    message: str

@app.get("/")
def home():
    """Health check to confirm backend is fully connected to frontend."""
    return {
        "status": "online",
        "backend_connected": True,
        "message": "Abdullah AI Backend is alive and waiting for requests."
    }

@app.get("/dashboard")
def get_dashboard():
    """Full breakdown of the 5 APIs, active status, and token math."""
    return brain.get_dashboard_metrics()

@app.post("/chat")
async def chat_endpoint(payload: ChatPayload):
    sana_text = payload.message.strip()
    if not sana_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Process through the 5-API auto-switch engine
    result = brain.generate_chat_response(sana_text)
    
    # Attach dashboard data to every chat response so frontend can update live
    return {
        "response": result["reply"],
        "tokens_used": result["tokens"],
        "provider_used": result["provider"],
        "learning_progress": min(int((len(brain.live_memories) / brain.learning_target) * 100), 100),
        "dashboard": brain.get_dashboard_metrics()
    }
    
