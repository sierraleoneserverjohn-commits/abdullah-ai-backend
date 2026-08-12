import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from brain import AbdullahBrain, LiveMemory

app = FastAPI(title="Abdullah AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

brain = AbdullahBrain()

class ChatRequest(BaseModel):
    message: str
    selected_api: str = "auto"

@app.get("/", response_class=HTMLResponse)
def serve_home():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return "<h1>Abdullah AI Engine Active</h1>"

@app.get("/api/dashboard")
def get_dashboard():
    return brain.get_dashboard_metrics()

@app.post("/api/chat")
def process_chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    return brain.generate_chat_response(sana_message=req.message, selected_api=req.selected_api)

@app.get("/api/memories")
def inspect_memories():
    """Endpoint to verify stored database memories directly from your browser."""
    if hasattr(brain, 'SessionLocal') and brain.db_active:
        session = brain.SessionLocal()
        try:
            records = session.query(LiveMemory).order_by(LiveMemory.id.desc()).limit(20).all()
            return {
                "db_status": "Connected to Supabase",
                "total_fetched": len(records),
                "memories": [
                    {
                        "id": r.id, 
                        "prompt": r.prompt, 
                        "completion": r.completion, 
                        "time": str(r.created_at)
                    } for r in records
                ]
            }
        except Exception as e:
            return {"db_status": "Error reading database", "details": str(e)}
        finally:
            session.close()
    return {"db_status": "Database not connected. Check DATABASE_URL on Render."}
    
