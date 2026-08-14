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

# 🔑 5-Provider Architecture Configuration & Limits
PROVIDERS_CONFIG = [
    {"id": "API_1", "env": "GROQ_API_KEY", "provider": "Groq", "model": "llama-3.3-70b-versatile", "limit": 14400},
    {"id": "API_2", "env": "CEREBRAS_API_KEY", "provider": "Cerebras", "model": "llama3.3-70b", "limit": 14400},
    {"id": "API_3", "env": "GEMINI_API_KEY", "provider": "Gemini", "model": "gemini-2.5-flash", "limit": 1500000},
    {"id": "API_4", "env": "OPENROUTER_API_KEY", "provider": "OpenRouter", "model": "meta-llama/llama-3.3-70b-instruct", "limit": 100000},
    {"id": "API_5", "env": "DEEPSEEK_API_KEY", "provider": "DeepSeek", "model": "deepseek-chat", "limit": 1000000},
]

# Real-time state tracker for tokens and provider health
PROVIDER_STATS = {
    p["id"]: {
        "tokens_used": 0,
        "status": "Connected & Active" if os.getenv(p["env"]) else "Awaiting API Key",
        "cooldown": 0
    }
    for p in PROVIDERS_CONFIG
}

# 1. HOME ROUTE
@app.get("/", response_class=HTMLResponse)
def serve_home():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return "<h1>Abdullah AI 5-Engine Active</h1>"

# 2. DASHBOARD STATUS ROUTE (Provides real-time stats to index.html)
@app.get("/dashboard")
@app.get("/api/dashboard")
def get_dashboard():
    current_time = time.time()
    api_breakdown = []
    total_used = 0
    total_capacity = 0
    connected_count = 0

    for p in PROVIDERS_CONFIG:
        p_id = p["id"]
        env_key = os.getenv(p["env"])
        stats = PROVIDER_STATS[p_id]

        # Dynamic Status Evaluation
        if env_key and stats["status"] == "Awaiting API Key":
            stats["status"] = "Connected & Active"
        elif not env_key:
            stats["status"] = "Awaiting API Key"

        if stats["status"] == "Rate Limited" and current_time > stats["cooldown"]:
            stats["status"] = "Connected & Active"

        if stats["status"] == "Connected & Active":
            connected_count += 1

        used = stats["tokens_used"]
        remaining = max(0, p["limit"] - used)
        total_used += used
        total_capacity += p["limit"]

        api_breakdown.append({
            "id": p_id,
            "provider": p["provider"],
            "env_name": p["env"],
            "model": p["model"],
            "status": stats["status"],
            "tokens_used": used,
            "remaining": remaining
        })

    return {
        "status": "Connected & Working",
        "connected_apis": connected_count,
        "total_apis": 5,
        "combined_tokens_used": total_used,
        "combined_tokens_remaining": max(0, total_capacity - total_used),
        "api_breakdown": api_breakdown
    }

# -------------------------------------------------------------
# ⚡ 5-PROVIDER ASYNC FETCH FUNCTIONS WITH TOKEN EXTRACTORS
# -------------------------------------------------------------
async def call_groq(client: httpx.AsyncClient, message: str) -> tuple[str, int]:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise ValueError("GROQ_API_KEY not configured")
    res = await client.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "llama-3.3-70b-versatile",
            "messages": [{"role": "user", "content": message}]
        },
        timeout=12.0
    )
    res.raise_for_status()
    data = res.json()
    reply = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", (len(message) + len(reply)) // 4)
    return reply, tokens

async def call_cerebras(client: httpx.AsyncClient, message: str) -> tuple[str, int]:
    key = os.getenv("CEREBRAS_API_KEY")
    if not key:
        raise ValueError("CEREBRAS_API_KEY not configured")
    res = await client.post(
        "https://api.cerebras.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "llama3.3-70b",
            "messages": [{"role": "user", "content": message}]
        },
        timeout=12.0
    )
    res.raise_for_status()
    data = res.json()
    reply = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", (len(message) + len(reply)) // 4)
    return reply, tokens

async def call_gemini(client: httpx.AsyncClient, message: str) -> tuple[str, int]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        raise ValueError("GEMINI_API_KEY not configured")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}"
    res = await client.post(
        url,
        headers={"Content-Type": "application/json"},
        json={"contents": [{"parts": [{"text": message}]}]},
        timeout=12.0
    )
    res.raise_for_status()
    data = res.json()
    reply = data["candidates"][0]["content"]["parts"][0]["text"]
    usage = data.get("usageMetadata", {})
    tokens = usage.get("totalTokenCount", (len(message) + len(reply)) // 4)
    return reply, tokens

async def call_openrouter(client: httpx.AsyncClient, message: str) -> tuple[str, int]:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise ValueError("OPENROUTER_API_KEY not configured")
    res = await client.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "meta-llama/llama-3.3-70b-instruct",
            "messages": [{"role": "user", "content": message}]
        },
        timeout=12.0
    )
    res.raise_for_status()
    data = res.json()
    reply = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", (len(message) + len(reply)) // 4)
    return reply, tokens

async def call_deepseek(client: httpx.AsyncClient, message: str) -> tuple[str, int]:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise ValueError("DEEPSEEK_API_KEY not configured")
    res = await client.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={
            "model": "deepseek-chat",
            "messages": [{"role": "user", "content": message}]
        },
        timeout=12.0
    )
    res.raise_for_status()
    data = res.json()
    reply = data["choices"][0]["message"]["content"]
    tokens = data.get("usage", {}).get("total_tokens", (len(message) + len(reply)) // 4)
    return reply, tokens

# -------------------------------------------------------------
# 3. CHAT ROUTE (SMART MANUAL OVERRIDE + AUTO FAILOVER PIPELINE)
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

    # Handle Manual Override Routing if specified
    selected = req.selected_api.lower()
    if selected != "auto":
        providers = [p for p in providers if p[0].lower() == selected or p[1].lower() in selected] + \
                    [p for p in providers if p[0].lower() != selected and p[1].lower() not in selected]

    async with httpx.AsyncClient() as client:
        for api_id, name, func in providers:
            try:
                reply, tokens = await func(client, req.message)
                latency = round((time.time() - start_time) * 1000)

                # Record Tokens Used in Global Tracker
                PROVIDER_STATS[api_id]["tokens_used"] += tokens
                PROVIDER_STATS[api_id]["status"] = "Connected & Active"

                return {
                    "status": "success",
                    "active_api": api_id,
                    "provider": name,
                    "provider_used": name,
                    "reply": reply,
                    "tokens": tokens,
                    "latency": f"{latency}ms"
                }
            except Exception as e:
                print(f"[Failover Engine] {api_id} ({name}) failed: {e}")
                PROVIDER_STATS[api_id]["status"] = "Rate Limited" if "429" in str(e) else "Error"
                PROVIDER_STATS[api_id]["cooldown"] = time.time() + 60
                continue

    raise HTTPException(
        status_code=500,
        detail="All 5 API services failed or had unconfigured keys."
    )
    
