from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from brain import AbdullahBrain

app = FastAPI(title="Johnny Tec AI - 5 API Hub")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Safely attempt dataset import if script exists, otherwise skip to prevent deployment failure
try:
    from upload_whatsapp import parse_whatsapp_chat
    parse_whatsapp_chat()
except Exception as e:
    print(f"Skipping upload_whatsapp script on startup: {str(e)}")

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
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    result = brain.generate_chat_response(sana_text, payload.api_choice)
    
    return {
        "response": result["reply"],
        "tokens_used": result["tokens"],
        "provider_used": result["provider"],
        "dashboard": brain.get_dashboard_metrics()
    }
    
