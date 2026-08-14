import os
import time
from typing import Tuple

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

# 🧠 Abdullah Brain Engine
from brain import abdullah_brain

app = FastAPI(title="Abdullah AI Backend Engine")

# CORS Setup - Allows frontend calls from GitHub Pages
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


# 🔑 5-Provider Configuration & Quotas
PROVIDERS_CONFIG = [
    {
        "id": "API_1",
        "env": "GROQ_API_KEY",
        "provider": "Groq",
        "model": "llama-3.3-70b-versatile",
        "limit": 14400,
    },
    {
        "id": "API_2",
        "env": "CEREBRAS_API_KEY",
        "provider": "Cerebras",
        "model": "llama3.3-70b",
        "limit": 14400,
    },
    {
        "id": "API_3",
        "env": "GEMINI_API_KEY",
        "provider": "Gemini",
        "model": "gemini-2.5-flash",
        "limit": 1500000,
    },
    {
        "id": "API_4",
        "env": "OPENROUTER_API_KEY",
        "provider": "OpenRouter",
        "model": "meta-llama/llama-3.3-70b-instruct",
        "limit": 100000,
    },
    {
        "id": "API_5",
        "env": "DEEPSEEK_API_KEY",
        "provider": "DeepSeek",
        "model": "deepseek-chat",
        "limit": 1000000,
    },
]


# State tracker for dashboard compatibility
PROVIDER_STATS = {
    p["id"]: {
        "tokens_used": 0,
        "status": (
            "Connected & Active"
            if os.getenv(p["env"])
            else "Awaiting API Key"
        ),
        "cooldown": 0,
    }
    for p in PROVIDERS_CONFIG
}


@app.get("/", response_class=HTMLResponse)
def serve_home():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return "<h1>Abdullah AI Backend Running 🧠</h1>"


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

        if env_key and stats["status"] == "Awaiting API Key":
            stats["status"] = "Connected & Active"
        elif not env_key:
            stats["status"] = "Awaiting API Key"

        if (
            stats["status"] == "Rate Limited"
            and current_time > stats["cooldown"]
        ):
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
            "remaining": remaining,
        })

    # 🧠 Add Abdullah Brain information
    brain_metrics = abdullah_brain.get_dashboard_metrics()

    return {
        "status": "Connected & Working",
        "connected_apis": connected_count,
        "total_apis": 5,
        "combined_tokens_used": total_used,
        "combined_tokens_remaining": max(
            0, total_capacity - total_used
        ),
        "api_breakdown": api_breakdown,

        # Brain status
        "brain": {
            "status": "Online",
            "whatsapp_messages": brain_metrics.get(
                "whatsapp_brain", 0
            ),
            "memory_candidates": brain_metrics.get(
                "memory_candidates", 0
            ),
            "database_connected": brain_metrics.get(
                "db_connected", False
            ),
        },
    }


# -------------------------------------------------------------
# 🧠 ABDULLAH BRAIN CHAT
# -------------------------------------------------------------
@app.post("/chat")
@app.post("/api/chat")
async def process_chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(
            status_code=400,
            detail="Message cannot be empty",
        )

    start_time = time.time()

    # The Brain Engine now:
    # 1. Searches WhatsApp chat_archive.json
    # 2. Searches memory_candidates.json
    # 3. Loads recent PostgreSQL memories
    # 4. Sends relevant memories to the selected AI
    # 5. Saves the new Sana ↔ Abdullah conversation
    # 6. Uses API failover
    result = abdullah_brain.generate_chat_response(
        sana_message=req.message,
        selected_api=req.selected_api,
    )

    latency = round((time.time() - start_time) * 1000)

    # Keep dashboard token/status information synchronized
    provider = result.get("provider", "")
    tokens = result.get("tokens", 0)

    for api in PROVIDERS_CONFIG:
        if api["provider"] in provider or api["id"] in provider:
            PROVIDER_STATS[api["id"]]["tokens_used"] += tokens
            PROVIDER_STATS[api["id"]]["status"] = (
                "Connected & Active"
            )
            break

    return {
        "status": "success",
        "active_api": provider,
        "provider": provider,
        "provider_used": provider,
        "reply": result.get("reply", ""),
        "tokens": tokens,
        "latency": f"{latency}ms",

        # 🧠 Brain information for frontend/debugging
        "brain": {
            "online": True,
            "whatsapp_memory": True,
            "database_memory": abdullah_brain.db_active,
        },
    }


# -------------------------------------------------------------
# 🧠 BRAIN SEARCH ENDPOINT
# -------------------------------------------------------------
@app.get("/api/brain/search")
def search_brain(q: str, limit: int = 8):
    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query cannot be empty",
        )

    limit = max(1, min(limit, 50))

    whatsapp = abdullah_brain.search_whatsapp(
        q,
        limit=limit,
    )

    memories = abdullah_brain.search_memory_candidates(
        q,
        limit=min(limit, 20),
    )

    return {
        "status": "success",
        "query": q,
        "whatsapp_results": whatsapp,
        "memory_results": memories,
    }


# -------------------------------------------------------------
# 🧠 BRAIN STATUS
# -------------------------------------------------------------
@app.get("/api/brain/status")
def brain_status():
    metrics = abdullah_brain.get_dashboard_metrics()

    return {
        "status": "online",
        "name": "Abdullah",
        "brain": {
            "whatsapp_messages": metrics.get(
                "whatsapp_brain", 0
            ),
            "memory_candidates": metrics.get(
                "memory_candidates", 0
            ),
            "postgresql": metrics.get(
                "db_connected", False
            ),
        },
        "apis": metrics.get(
            "api_breakdown", []
        ),
    }
