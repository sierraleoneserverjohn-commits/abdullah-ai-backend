import time
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from brain import abdullah_brain

app = FastAPI(title="Abdullah AI Backend Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    selected_api: str = "auto"


@app.get("/", response_class=HTMLResponse)
def home():
    import os

    if os.path.exists("index.html"):
        return FileResponse("index.html")

    return "<h1>Abdullah AI Backend Running 🧠</h1>"


@app.get("/api/brain/status")
def brain_status():
    return abdullah_brain.status()


@app.get("/api/brain/search")
def brain_search(q: str, limit: int = 8):
    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty"
        )

    return abdullah_brain.search_brain(
        q,
        max(1, min(limit, 50))
    )


@app.get("/dashboard")
@app.get("/api/dashboard")
def dashboard():
    return abdullah_brain.dashboard()


@app.post("/chat")
@app.post("/api/chat")
async def chat(req: ChatRequest):

    if not req.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty"
        )

    started = time.time()

    result = await abdullah_brain.chat(
        req.message,
        req.selected_api
    )

    result["latency"] = (
        f"{round((time.time() - started) * 1000)}ms"
    )

    return result
