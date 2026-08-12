from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from brain import AbdullahBrain
from upload_whatsapp import parse_whatsapp_chat

app = FastAPI(title="Abdullah AI - Johnny Tec Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

parse_whatsapp_chat()
brain = AbdullahBrain()

class ChatPayload(BaseModel):
    message: str
    api_choice: str = "auto" # Accepts 'auto' or a specific key name like 'GROQ_API_KEY_1'

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
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    result = brain.generate_chat_response(sana_text, payload.api_choice)
    
    return {
        "response": result["reply"],
        "tokens_used": result["tokens"],
        "provider_used": result["provider"],
        "learning_progress": brain.get_dashboard_metrics(), # Safe passing
        "dashboard": brain.get_dashboard_metrics()
    }
    
