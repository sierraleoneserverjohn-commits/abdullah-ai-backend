import os
import re
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel
from brain import AbdullahBrain, LiveMemory

app = FastAPI(title="Abdullah AI Backend")

# Enable CORS for frontend requests
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

# -------------------------------------------------------------
# 1. HOME ROUTE
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def serve_home():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return "<h1>Abdullah AI Engine Active</h1>"

# -------------------------------------------------------------
# 2. DASHBOARD ROUTES (Handles /dashboard and /api/dashboard)
# -------------------------------------------------------------
@app.get("/dashboard")
@app.get("/api/dashboard")
def get_dashboard():
    return brain.get_dashboard_metrics()

# -------------------------------------------------------------
# 3. CHAT ROUTES (Handles /chat and /api/chat)
# -------------------------------------------------------------
@app.post("/chat")
@app.post("/api/chat")
def process_chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    return brain.generate_chat_response(sana_message=req.message, selected_api=req.selected_api)

# -------------------------------------------------------------
# 4. MEMORY INSPECTOR ROUTE
# -------------------------------------------------------------
@app.get("/memories")
@app.get("/api/memories")
def inspect_memories():
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

# -------------------------------------------------------------
# 5. WHATSAPP CHAT FILE UPLOADER (Web Page)
# -------------------------------------------------------------
@app.get("/upload", response_class=HTMLResponse)
def upload_page():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Upload WhatsApp Chat</title>
        <style>
            body { font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #fff; padding: 20px; text-align: center; }
            .card { background: #1e293b; padding: 30px; border-radius: 12px; max-width: 400px; margin: 40px auto; box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
            h2 { margin-bottom: 8px; color: #f8fafc; }
            p { color: #94a3b8; font-size: 14px; margin-bottom: 24px; }
            input[type="file"] { margin: 15px 0; width: 100%; color: #cbd5e1; }
            button { background: #8b5cf6; color: white; border: none; padding: 12px 24px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 100%; font-size: 16px; }
            button:hover { background: #7c3aed; }
        </style>
    </head>
    <body>
        <div class="card">
            <h2>Upload chat.txt</h2>
            <p>Upload your exported WhatsApp chat file directly to store memories in Supabase.</p>
            <form action="/api/upload-chat" method="post" enctype="multipart/form-data">
                <input type="file" name="file" accept=".txt" required>
                <button type="submit">Process & Save to Supabase</button>
            </form>
        </div>
    </body>
    </html>
    """

# -------------------------------------------------------------
# 6. WHATSAPP CHAT PROCESSOR ENDPOINT
# -------------------------------------------------------------
@app.post("/api/upload-chat")
async def process_chat_file(file: UploadFile = File(...)):
    if not hasattr(brain, 'SessionLocal') or not brain.db_active:
        return {"error": "Database not connected. Check DATABASE_URL in Render settings."}
    
    contents = await file.read()
    text_content = contents.decode("utf-8", errors="ignore")
    lines = text_content.splitlines()

    session = brain.SessionLocal()
    memories_to_insert = []
    last_sana_msg = None
    pattern = re.compile(r"^\[?.*?\]?\s*([^:]+):\s*(.+)$")

    for line in lines:
        line = line.strip()
        match = pattern.search(line)
        if match:
            sender = match.group(1).lower()
            text = match.group(2).strip()

            if any(w in text.lower() for w in ["omitted", "end-to-end", "call"]):
                continue

            if "sana" in sender:
                last_sana_msg = text
            elif ("abdullah" in sender or "you" in sender) and last_sana_msg:
                memories_to_insert.append(
                    LiveMemory(
                        prompt=f"Sana: {last_sana_msg}",
                        completion=f"Abdullah: {text}"
                    )
                )
                last_sana_msg = None

    total = len(memories_to_insert)
    if total > 0:
        batch_size = 500
        for i in range(0, total, batch_size):
            batch = memories_to_insert[i:i + batch_size]
            session.bulk_save_objects(batch)
            session.commit()
        session.close()
        return {"status": "Success", "message": f"Successfully stored {total} chat memories into Supabase!"}
    
    session.close()
    return {"status": "Warning", "message": "No matching conversation pairs found. Ensure speaker names in chat.txt include Sana and Abdullah."}
            
