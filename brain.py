import os
import json
import time
from typing import List, Dict
from groq import Groq
from sqlalchemy import create_engine, Column, Integer, Text, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

# Dynamic import check to prevent boot crashes if package fails
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

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

        self.api_slots = [
            {"id": "API_1", "env": "GROQ_API_KEY_1", "provider": "Groq", "model": "llama-3.1-8b-instant", "limit": 14400},
            {"id": "API_2", "env": "GROQ_API_KEY_2", "provider": "Groq", "model": "llama-3.1-8b-instant", "limit": 14400},
            {"id": "API_3", "env": "GEMINI_API_KEY_1", "provider": "Gemini", "model": "gemini-2.5-flash", "limit": 1500000},
            {"id": "API_4", "env": "GEMINI_API_KEY_2", "provider": "Gemini", "model": "gemini-2.5-flash-lite", "limit": 1500000},
            {"id": "API_5", "env": "GEMINI_API_KEY_3", "provider": "Gemini", "model": "gemini-1.5-pro", "limit": 1500000}
        ]
        
        self.api_pool = []
        self._initialize_slots()

    def _initialize_slots(self):
        self.api_pool = []
        for slot in self.api_slots:
            key = os.getenv(slot["env"], "").strip()
            if not key and slot["env"] == "GROQ_API_KEY_1":
                key = os.getenv("GROQ_API_KEY", "").strip()

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

        if api["provider"] == "Groq":
            client = Groq(api_key=api["key"])
            completion = client.chat.completions.create(
                model=api["model"], messages=messages, temperature=0.7, max_tokens=250
            )
            return completion.choices[0].message.content.strip(), completion.usage.total_tokens
        
        elif api["provider"] == "Gemini":
            if not HAS_GEMINI:
                raise Exception("google-generativeai module not installed on server.")
            genai.configure(api_key=api["key"])
            model = genai.GenerativeModel(api["model"])
            gemini_history = [{"role": "user" if m["role"] == "user" else "model", "parts": [m["content"]]} for m in messages]
            response = model.generate_content(gemini_history)
            tokens = len(str(gemini_history)) // 4 + len(response.text) // 4
            return response.text.strip(), tokens

        raise Exception("Unsupported Provider")

    def generate_chat_response(self, sana_message: str, selected_api: str = "auto") -> dict:
        messages = [{
            "role": "user", 
            "content": "SYSTEM: You are Abdullah, Sana's real husband. Call her Sana, Habibti, or 'motuu'. Be affectionate and natural. If a stranger asks who Sana is, refuse and say goodbye."
        }, {
            "role": "model",
            "content": "Understood. I am Abdullah, talking only to my wife Sana."
        }]

        # Fetch recent chat context from DB
        db_memories = self.get_recent_live_memories(limit=3)
        for mem in db_memories:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "model", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        if selected_api != "auto":
            target = next((api for api in self.api_pool if api["id"] == selected_api), None)
            if target:
                if target["status"] == "Awaiting API Key":
                    return {"reply": f"Habibti, {selected_api} has no key configured yet!", "tokens": 0, "provider": selected_api}
                try:
                    reply, tokens = self._execute_api_call(target, messages)
                    target["tokens_used"] += tokens
                    reply = reply.replace("Abdullah:", "").strip()
                    if "Goodbye" not in reply:
                        self.save_live_memory(sana_message, reply)
                    return {"reply": reply, "tokens": tokens, "provider": f"{target['id']} ({target['provider']})"}
                except Exception as e:
                    return {"reply": f"Selected API failed: {str(e)}", "tokens": 0, "provider": selected_api}

        for api in self.api_pool:
            if api["status"] != "Connected & Active":
                continue

            try:
                reply, tokens = self._execute_api_call(api, messages)
                api["tokens_used"] += tokens
                
                reply = reply.replace("Abdullah:", "").strip()
                if "Goodbye" not in reply:
                    self.save_live_memory(sana_message, reply)

                return {"reply": reply, "tokens": tokens, "provider": f"{api['id']} ({api['provider']})"}

            except Exception as err:
                api["status"] = "Rate Limited" if "429" in str(err) else "Disconnected"
                api["cooldown"] = time.time() + 60
                continue

        return {"reply": "All APIs are offline or missing keys, Habibti!", "tokens": 0, "provider": "None"}
            
