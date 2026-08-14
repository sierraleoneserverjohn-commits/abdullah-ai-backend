import os
import json
import re
import time
from pathlib import Path
from typing import List, Dict, Tuple

import httpx
from sqlalchemy import create_engine, Column, Integer, Text, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
BRAIN_DATA_DIR = Path(os.getenv("ABDULLAH_BRAIN_DIR", BASE_DIR / "brain_data"))
CHAT_ARCHIVE_FILE = BRAIN_DATA_DIR / "chat_archive.json"
MEMORY_CANDIDATES_FILE = BRAIN_DATA_DIR / "memory_candidates.json"
BRAIN_FILE = BRAIN_DATA_DIR / "brain.json"

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

Base = declarative_base()

class LiveMemory(Base):
    __tablename__ = "live_memories"
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt = Column(Text, nullable=False)
    completion = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AbdullahBrain:
    def __init__(self, memory_file="abdullah_memory_dataset.json"):
        self.memory_file = memory_file
        self.base_memories = self._load_json(self.memory_file)
        self.brain_data_dir = BRAIN_DATA_DIR
        self.chat_archive = self._load_json(CHAT_ARCHIVE_FILE)
        self.memory_candidates = self._load_json(MEMORY_CANDIDATES_FILE)
        self.brain_profile = self._load_json(BRAIN_FILE)

        print("==========================================")
        print("🧠 ABDULLAH BRAIN STARTING...")
        print(f"📁 Brain directory: {self.brain_data_dir}")
        print(f"💬 WhatsApp messages: {len(self.chat_archive):,}")
        print(f"🧠 Memory candidates: {len(self.memory_candidates):,}")
        print("==========================================")

        self.db_active = False
        self.engine = None
        self.SessionLocal = None

        if DATABASE_URL:
            try:
                self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)
                Base.metadata.create_all(self.engine)
                self.SessionLocal = sessionmaker(bind=self.engine)
                self.db_active = True
                print("🗄️ PostgreSQL: CONNECTED")
            except Exception as error:
                print("❌ PostgreSQL connection error:", error)
        else:
            print("⚠️ DATABASE_URL is not configured")

        self.api_slots = [
            {"id": "API_1", "env": "GROQ_API_KEY", "provider": "Groq", "model": "llama-3.3-70b-versatile", "limit": 14400},
            {"id": "API_2", "env": "CEREBRAS_API_KEY", "provider": "Cerebras", "model": "llama3.3-70b", "limit": 14400},
            {"id": "API_3", "env": "GEMINI_API_KEY", "provider": "Gemini", "model": "gemini-2.5-flash", "limit": 1500000},
            {"id": "API_4", "env": "OPENROUTER_API_KEY", "provider": "OpenRouter", "model": "meta-llama/llama-3.3-70b-instruct", "limit": 100000},
            {"id": "API_5", "env": "DEEPSEEK_API_KEY", "provider": "DeepSeek", "model": "deepseek-chat", "limit": 1000000},
        ]
        self.api_pool = []
        self._initialize_slots()

    def _load_json(self, filepath):
        filepath = Path(filepath)
        if not filepath.exists():
            print(f"⚠️ File not found: {filepath}")
            return []
        try:
            with open(filepath, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception as error:
            print(f"❌ Could not load {filepath}: {error}")
            return []

    def _initialize_slots(self):
        self.api_pool = []
        for slot in self.api_slots:
            key = os.getenv(slot["env"], "").strip()
            if key:
                status = "Connected & Active"
                masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "Valid Key"
            else:
                key = None
                status = "Awaiting API Key"
                masked = "Pending..."
            self.api_pool.append({
                "id": slot["id"], "env_name": slot["env"], "key": key,
                "provider": slot["provider"], "model": slot["model"],
                "masked": masked, "tokens_used": 0,
                "daily_limit": slot["limit"], "status": status, "cooldown": 0
            })

    def _normalize(self, text: str) -> str:
        text = str(text or "").lower()
        text = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
        return re.sub(r"\s+", " ", text).strip()

    def _get_words(self, text: str):
        return {word for word in self._normalize(text).split() if len(word) > 2}

    def _relevance(self, query: str, stored_text: str) -> float:
        query_words = self._get_words(query)
        stored_words = self._get_words(stored_text)
        if not query_words or not stored_words:
            return 0.0
        return len(query_words & stored_words) / len(query_words)

    def search_whatsapp(self, query: str, limit: int = 8):
        results = []
        if not self.chat_archive:
            return results
        for message in self.chat_archive:
            if not isinstance(message, dict):
                continue
            message_text = message.get("message", "")
            score = self._relevance(query, message_text)
            if score <= 0:
                continue
            results.append({
                "score": score, "id": message.get("id"),
                "date": message.get("date"), "time": message.get("time"),
                "sender": message.get("sender"), "message": message_text
            })
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]

    def search_memory_candidates(self, query: str, limit: int = 5):
        results = []
        if not self.memory_candidates:
            return results
        for memory in self.memory_candidates:
            if not isinstance(memory, dict):
                continue
            text = memory.get("message", "")
            score = self._relevance(query, text)
            if score <= 0:
                continue
            result = dict(memory)
            result["score"] = score
            results.append(result)
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]

    def build_whatsapp_context(self, sana_message: str, limit: int = 8):
        results = self.search_whatsapp(sana_message, limit)
        if not results:
            return ""
        return "\n".join(
            f"[{item.get('date', '')} {item.get('time', '')}] "
            f"{item.get('sender', 'Unknown')}: {item.get('message', '')}"
            for item in results
        )

    def get_recent_live_memories(self, limit: int = 5) -> List[Dict]:
        if not self.db_active:
            return []
        session = self.SessionLocal()
        try:
            records = session.query(LiveMemory).order_by(LiveMemory.id.desc()).limit(limit).all()
            return [{"prompt": r.prompt, "completion": r.completion} for r in reversed(records)]
        except Exception as error:
            print("❌ Failed to fetch live memories:", error)
            return []
        finally:
            session.close()

    def save_live_memory(self, prompt: str, completion: str):
        if not self.db_active:
            return
        session = self.SessionLocal()
        try:
            session.add(LiveMemory(prompt=f"Sana: {prompt}", completion=f"Abdullah: {completion}"))
            session.commit()
        except Exception as error:
            session.rollback()
            print("❌ Failed to save memory:", error)
        finally:
            session.close()

    def get_dashboard_metrics(self):
        current_time = time.time()
        total_used = 0
        total_capacity = 0
        connected_count = 0
        api_details = []
        for api in self.api_pool:
            if api["status"] == "Rate Limited" and current_time > api["cooldown"]:
                api["status"] = "Connected & Active"
            total_used += api["tokens_used"]
            total_capacity += api["daily_limit"]
            if api["status"] == "Connected & Active":
                connected_count += 1
            api_details.append({
                "id": api["id"], "env_name": api["env_name"],
                "provider": api["provider"], "model": api["model"],
                "status": api["status"], "tokens_used": api["tokens_used"],
                "remaining": max(0, api["daily_limit"] - api["tokens_used"])
            })
        return {
            "total_apis": 5, "connected_apis": connected_count,
            "db_connected": self.db_active,
            "whatsapp_brain": len(self.chat_archive),
            "memory_candidates": len(self.memory_candidates),
            "combined_tokens_used": total_used,
            "combined_tokens_remaining": max(0, total_capacity - total_used),
            "api_breakdown": api_details
        }

    def _execute_api_call(self, api, messages) -> Tuple[str, int]:
        if not api["key"]:
            raise Exception(f"Key missing for {api['env_name']}")
        provider, model, key = api["provider"], api["model"], api["key"]

        with httpx.Client(timeout=20.0) as client:
            if provider in ("Groq", "Cerebras", "OpenRouter", "DeepSeek"):
                urls = {
                    "Groq": "https://api.groq.com/openai/v1/chat/completions",
                    "Cerebras": "https://api.cerebras.ai/v1/chat/completions",
                    "OpenRouter": "https://openrouter.ai/api/v1/chat/completions",
                    "DeepSeek": "https://api.deepseek.com/chat/completions"
                }
                response = client.post(
                    urls[provider],
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "temperature": 0.7}
                )
                response.raise_for_status()
                data = response.json()
                reply = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", len(reply) // 4)
                return reply.strip(), tokens

            if provider == "Gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                prompt_text = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
                response = client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt_text}]}]}
                )
                response.raise_for_status()
                data = response.json()
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
                tokens = data.get("usageMetadata", {}).get("totalTokenCount", (len(prompt_text) + len(reply)) // 4)
                return reply.strip(), tokens

        raise Exception("Unsupported Provider")

    def generate_chat_response(self, sana_message: str, selected_api: str = "auto") -> dict:
        if not sana_message.strip():
            return {"reply": "Tell me something, Sana ❤️", "tokens": 0, "provider": "None"}

        system_prompt = """
You are Abdullah AI.

You are chatting with Sana.

Your personality is warm, natural, supportive, respectful,
emotionally aware, and affectionate when appropriate.

Address her naturally as Sana.

You have access to historical WhatsApp memories and recent
conversation memories.

Use memories only when relevant.
Never invent a memory.
Never claim something happened if the provided memory does not support it.
If you cannot find enough information, answer normally.
"""

        messages = [{"role": "system", "content": system_prompt}]

        whatsapp_context = self.build_whatsapp_context(sana_message, limit=8)
        if whatsapp_context:
            messages.append({
                "role": "system",
                "content": f"Relevant historical WhatsApp messages:\n\n{whatsapp_context}\n\nUse these only when relevant."
            })

        candidate_results = self.search_memory_candidates(sana_message, limit=5)
        if candidate_results:
            candidate_text = "\n".join(f"- {item.get('message', '')}" for item in candidate_results)
            messages.append({
                "role": "system",
                "content": f"Potential important memory references:\n\n{candidate_text}"
            })

        for memory in self.get_recent_live_memories(limit=3):
            messages.append({"role": "user", "content": memory.get("prompt", "")})
            messages.append({"role": "assistant", "content": memory.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        if selected_api.lower() != "auto":
            target = next(
                (api for api in self.api_pool if api["id"].lower() == selected_api.lower()),
                None
            )
            if not target:
                return {"reply": f"{selected_api} is not available.", "tokens": 0, "provider": selected_api}
            if target["status"] == "Awaiting API Key":
                return {"reply": f"{selected_api} has no API key configured yet.", "tokens": 0, "provider": selected_api}
            try:
                reply, tokens = self._execute_api_call(target, messages)
                target["tokens_used"] += tokens
                reply = reply.replace("Abdullah:", "").strip()
                self.save_live_memory(sana_message, reply)
                return {"reply": reply, "tokens": tokens, "provider": f"{target['id']} ({target['provider']})"}
            except Exception as error:
                return {"reply": f"Selected API failed: {error}", "tokens": 0, "provider": selected_api}

        for api in self.api_pool:
            if api["status"] != "Connected & Active":
                continue
            try:
                reply, tokens = self._execute_api_call(api, messages)
                api["tokens_used"] += tokens
                reply = reply.replace("Abdullah:", "").strip()
                self.save_live_memory(sana_message, reply)
                return {"reply": reply, "tokens": tokens, "provider": f"{api['id']} ({api['provider']})"}
            except Exception as error:
                print(f"[Brain Engine] {api['id']} ({api['provider']}) failed: {error}")
                api["status"] = "Rate Limited" if "429" in str(error) else "Disconnected"
                api["cooldown"] = time.time() + 60

        return {
            "reply": "All 5 APIs are currently offline or missing keys, Sana.",
            "tokens": 0,
            "provider": "None"
        }


abdullah_brain = AbdullahBrain()
