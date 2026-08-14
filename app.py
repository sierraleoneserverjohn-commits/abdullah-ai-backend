import os
import time
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

app = FastAPI(title="Abdullah AI Backend Engine")

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    selected_api: str = "auto"

# 🔑 Load API Keys from Environment Variables
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
CEREBRAS_API_KEY = os.getenv("CEREBRAS_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")

# 1. HOME ROUTE
@app.get("/", response_class=HTMLResponse)
def serve_home():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return "<h1>Abdullah AI 5-Engine Active</h1>"

# 2. DASHBOARD STATUS ROUTE
@app.get("/dashboard")
@app.get("/api/dashboard")
def get_dashboard():
    keys = {
        "Groq": bool(GROQ_API_KEY),
        "Cerebras": bool(CEREBRAS_API_KEY),
        "Gemini": bool(GEMINI_API_KEY),
        "OpenRouter": bool(OPENROUTER_API_KEY),
        "DeepSeek": bool(DEEPSEEK_API_KEY),
    }
    active_count = sum(keys.values())
    return {
        "status": "Connected & Working",
        "active_apis": f"{active_count} / 5",
        "providers_configured": keys
    }

# -------------------------------------------------------------
# ⚡ 5-PROVIDER ASYNC FETCH FUNCTIONS
# -------------------------------------------------------------
async def call_groq(client: httpx.AsyncClient, message: str) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not configured")
    res = await client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": message}]
        },
        timeout=10.0
    )
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

async def call_cerebras(client: httpx.AsyncClient, message: str) -> str:
    if not CEREBRAS_API_KEY:
        raise ValueError("CEREBRAS_API_KEY not configured")
    res = await client.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {CEREBRAS_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "llama3.3-70b",
            "messages": [{"role": "user", "content": message}]
        },
        timeout=10.0
    )
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

async def call_gemini(client: httpx.AsyncClient, message: str) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GEMINI_API_KEY}"
    res = await client.post(
        url,
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": message}]}]},
        timeout=10.0
    )
    res.raise_for_status()
    return res.json()["candidates"][0]["content"]["parts"][0]["text"]

async def call_openrouter(client: httpx.AsyncClient, message: str) -> str:
    if not OPENROUTER_API_KEY:
        raise ValueError("OPENROUTER_API_KEY not configured")
    res = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "meta-llama/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": message}]
        },
        timeout=10.0
    )
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

async def call_deepseek(client: httpx.AsyncClient, message: str) -> str:
    if not DEEPSEEK_API_KEY:
        raise ValueError("DEEPSEEK_API_KEY not configured")
    res = await client.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": message}]
        },
        timeout=10.0
    )
    res.raise_for_status()
    return res.json()["choices"][0]["message"]["content"]

# -------------------------------------------------------------
# 3. CHAT ROUTE (5-API AUTO FAILOVER PIPELINE)
# -------------------------------------------------------------
@app.post("/chat")
@app.post("/api/chat")
async def process_chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    start_time = time.time()
    providers = [
        ("API_1", "Groq", call_groq),
        ("API_2", "Cerebras", call_cerebras),
        ("API_3", "Gemini", call_gemini),
        ("API_4", "OpenRouter", call_openrouter),
        ("API_5", "DeepSeek", call_deepseek),
    ]

    async with httpx.AsyncClient() as client:
        for api_id, name, func in providers:
            try:
                reply = await func(client, req.message)
                latency = round((time.time() - start_time) * 1000)
                return {
                    "status": "success",
                    "active_api": api_id,
                    "provider": name,
                    "reply": reply,
                    "latency": f"{latency}ms"
                }
            except Exception as e:
                print(f"[Failover Engine] {api_id} ({name}) failed: {e}")
                continue

    raise HTTPException(
        status_code=500,
        detail="All 5 API services failed or had unconfigured keys."
    )
    
