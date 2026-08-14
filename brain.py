import os
import json
import time
import httpx
from typing import List, Dict
from sqlalchemy import create_engine, Column, Integer, Text, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

# Database Setup
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
        
        # PostgreSQL Setup
        self.db_active = False
        if DATABASE_URL:
            try:
                self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)
                Base.metadata.create_all(self.engine)
                self.SessionLocal = sessionmaker(bind=self.engine)
                self.db_active = True
            except Exception as e:
                print(f"Database Connection Error: {e}")

        # 5-API Architecture Slots
        self.api_slots = [
            {"id": "API_1", "env": "GROQ_API_KEY", "provider": "Groq", "model": "llama-3.3-70b-versatile", "limit": 14400},
            {"id": "API_2", "env": "CEREBRAS_API_KEY", "provider": "Cerebras", "model": "llama3.3-70b", "limit": 14400},
            {"id": "API_3", "env": "GEMINI_API_KEY", "provider": "Gemini", "model": "gemini-2.5-flash", "limit": 1500000},
            {"id": "API_4", "env": "OPENROUTER_API_KEY", "provider": "OpenRouter", "model": "meta-llama/llama-3.3-70b-instruct", "limit": 100000},
            {"id": "API_5", "env": "DEEPSEEK_API_KEY", "provider": "DeepSeek", "model": "deepseek-chat", "limit": 1000000}
        ]
        
        self.api_pool = []
        self._initialize_slots()

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
                "id": slot["id"],
                "env_name": slot["env"],
                "key": key,
                "provider": slot["provider"],
                "model": slot["model"],
                "masked": masked,
                "tokens_used": 0,
                "daily_limit": slot["limit"],
                "status": status,
                "cooldown": 0
            })

    def _load_json(self, filepath: str) -> List[Dict]:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return []
        return []

    def get_recent_live_memories(self, limit: int = 5) -> List[Dict]:
        """Fetch recent memories from PostgreSQL database."""
        if not self.db_active:
            return []
        
        session = self.SessionLocal()
        try:
            records = session.query(LiveMemory).order_by(LiveMemory.id.desc()).limit(limit).all()
            return [{"prompt": r.prompt, "completion": r.completion} for r in reversed(records)]
        except Exception as e:
            print(f"Failed to fetch memories: {e}")
            return []
        finally:
            session.close()

    def save_live_memory(self, prompt: str, completion: str):
        """Save a new interaction directly into PostgreSQL."""
        if not self.db_active:
            return
            
        session = self.SessionLocal()
        try:
            new_mem = LiveMemory(prompt=f"Sana: {prompt}", completion=f"Abdullah: {completion}")
            session.add(new_mem)
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Failed to save memory to DB: {e}")
        finally:
            session.close()

    def get_dashboard_metrics(self) -> dict:
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
                "id": api["id"],
                "env_name": api["env_name"],
                "provider": api["provider"],
                "status": api["status"],
                "tokens_used": api["tokens_used"],
                "remaining": max(0, api["daily_limit"] - api["tokens_used"])
            })

        return {
            "total_apis": 5,
            "connected_apis": connected_count,
            "db_connected": self.db_active,
            "combined_tokens_used": total_used,
            "combined_tokens_remaining": max(0, total_capacity - total_used),
            "api_breakdown": api_details
        }

    def _execute_api_call(self, api, messages):
        if not api["key"]:
            raise Exception(f"Key missing for {api['env_name']}.")

        provider = api["provider"]
        model = api["model"]
        key = api["key"]

        with httpx.Client(timeout=12.0) as client:
            # 1. GROQ
            if provider == "Groq":
                res = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "temperature": 0.7}
                )
                res.raise_for_status()
                data = res.json()
                reply = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", len(reply) // 4)
                return reply.strip(), tokens

            # 2. CEREBRAS
            elif provider == "Cerebras":
                res = client.post(
                    "https://api.cerebras.ai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "temperature": 0.7}
                )
                res.raise_for_status()
                data = res.json()
                reply = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", len(reply) // 4)
                return reply.strip(), tokens

            # 3. GEMINI
            elif provider == "Gemini":
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                # Format system prompt and context for Gemini
                prompt_text = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
                res = client.post(
                    url,
                    headers={"Content-Type": "application/json"},
                    json={"contents": [{"parts": [{"text": prompt_text}]}]}
                )
                res.raise_for_status()
                data = res.json()
                reply = data["candidates"][0]["content"]["parts"][0]["text"]
                tokens = len(prompt_text) // 4 + len(reply) // 4
                return reply.strip(), tokens

            # 4. OPENROUTER
            elif provider == "OpenRouter":
                res = client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "temperature": 0.7}
                )
                res.raise_for_status()
                data = res.json()
                reply = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", len(reply) // 4)
                return reply.strip(), tokens

            # 5. DEEPSEEK
            elif provider == "DeepSeek":
                res = client.post(
                    "https://api.deepseek.com/chat/completions",
                    headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                    json={"model": model, "messages": messages, "temperature": 0.7}
                )
                res.raise_for_status()
                data = res.json()
                reply = data["choices"][0]["message"]["content"]
                tokens = data.get("usage", {}).get("total_tokens", len(reply) // 4)
                return reply.strip(), tokens

        raise Exception("Unsupported Provider")

    def generate_chat_response(self, sana_message: str, selected_api: str = "auto") -> dict:
        messages = [{
            "role": "system", 
            "content": "You are Abdullah. You are chatting with Sana. Address her as Sana. Be affectionate, clear, warm, and natural."
        }]

        # Fetch recent chat context from DB
        db_memories = self.get_recent_live_memories(limit=3)
        for mem in db_memories:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        # Manual API Selection Routing
        if selected_api != "auto":
            target = next((api for api in self.api_pool if api["id"] == selected_api), None)
            if target:
                if target["status"] == "Awaiting API Key":
                    return {"reply": f"Sana, {selected_api} has no key configured yet!", "tokens": 0, "provider": selected_api}
                try:
                    reply, tokens = self._execute_api_call(target, messages)
                    target["tokens_used"] += tokens
                    reply = reply.replace("Abdullah:", "").strip()
                    self.save_live_memory(sana_message, reply)
                    return {"reply": reply, "tokens": tokens, "provider": f"{target['id']} ({target['provider']})"}
                except Exception as e:
                    return {"reply": f"Selected API failed: {str(e)}", "tokens": 0, "provider": selected_api}

        # Auto Failover Loop through API Pool
        for api in self.api_pool:
            if api["status"] != "Connected & Active":
                continue

            try:
                reply, tokens = self._execute_api_call(api, messages)
                api["tokens_used"] += tokens
                
                reply = reply.replace("Abdullah:", "").strip()
                self.save_live_memory(sana_message, reply)

                return {"reply": reply, "tokens": tokens, "provider": f"{api['id']} ({api['provider']})"}

            except Exception as err:
                print(f"[Brain Engine] {api['id']} ({api['provider']}) Error: {err}")
                api["status"] = "Rate Limited" if "429" in str(err) else "Disconnected"
                api["cooldown"] = time.time() + 60
                continue

        return {"reply": "All 5 APIs are currently offline or missing keys, Sana.", "tokens": 0, "provider": "None"}
    
