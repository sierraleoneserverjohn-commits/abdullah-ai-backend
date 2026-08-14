import os
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Tuple

import httpx
from sqlalchemy import create_engine, Column, Integer, Text, DateTime, func
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
BRAIN_DIR = BASE_DIR / "brain_data"

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
    def __init__(self):
        self.brain = self.load("brain.json", {})
        self.chat_archive = self.load("chat_archive.json", [])
        self.memory_candidates = self.load("memory_candidates.json", [])
        self.db_active = False
        self.engine = None
        self.SessionLocal = None

        if DATABASE_URL:
            try:
                self.engine = create_engine(DATABASE_URL, pool_pre_ping=True)
                Base.metadata.create_all(self.engine)
                self.SessionLocal = sessionmaker(bind=self.engine)
                self.db_active = True
            except Exception as e:
                print("Database error:", e)

        self.providers = [
            {"id":"API_1","env":"GROQ_API_KEY","provider":"Groq","model":"llama-3.3-70b-versatile"},
            {"id":"API_2","env":"CEREBRAS_API_KEY","provider":"Cerebras","model":"llama3.3-70b"},
            {"id":"API_3","env":"GEMINI_API_KEY","provider":"Gemini","model":"gemini-2.5-flash"},
            {"id":"API_4","env":"OPENROUTER_API_KEY","provider":"OpenRouter","model":"meta-llama/llama-3.3-70b-instruct"},
            {"id":"API_5","env":"DEEPSEEK_API_KEY","provider":"DeepSeek","model":"deepseek-chat"},
        ]
        self.stats = {
            p["id"]: {"tokens_used":0, "status":"Connected & Active" if os.getenv(p["env"]) else "Awaiting API Key", "cooldown":0}
            for p in self.providers
        }

    def load(self, name, default):
        path = BRAIN_DIR / name
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Could not load {path}: {e}")
            return default

    def normalize(self, text):
        return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", str(text).lower())).strip()

    def score(self, query, text):
        q = set(w for w in self.normalize(query).split() if len(w) > 2)
        t = set(w for w in self.normalize(text).split() if len(w) > 2)
        return len(q & t) / max(1, len(q))

    def search_whatsapp(self, query, limit=8):
        results = []
        for m in self.chat_archive:
            s = self.score(query, m.get("message",""))
            if s > 0:
                item = dict(m)
                item["score"] = round(s, 4)
                results.append(item)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def search_candidates(self, query, limit=5):
        results = []
        for m in self.memory_candidates:
            s = self.score(query, m.get("message",""))
            if s > 0:
                item = dict(m)
                item["score"] = round(s, 4)
                results.append(item)
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    def recent_live(self, limit=4):
        if not self.db_active:
            return []
        s = self.SessionLocal()
        try:
            rows = s.query(LiveMemory).order_by(LiveMemory.id.desc()).limit(limit).all()
            return [{"prompt":r.prompt,"completion":r.completion} for r in reversed(rows)]
        finally:
            s.close()

    def save_live(self, prompt, completion):
        if not self.db_active:
            return
        s = self.SessionLocal()
        try:
            s.add(LiveMemory(prompt=f"Sana: {prompt}", completion=f"Abdullah: {completion}"))
            s.commit()
        except Exception:
            s.rollback()
        finally:
            s.close()

    def build_messages(self, user_message):
        system = (
            "You are Abdullah. You are chatting with Sana. "
            "Be warm, natural, respectful and supportive. "
            "Use the supplied historical memories only when relevant. "
            "Never invent memories or claim something happened unless the supplied "
            "conversation supports it. If memory is uncertain, say so naturally."
        )
        messages = [{"role":"system","content":system}]

        historical = self.search_whatsapp(user_message, 8)
        candidates = self.search_candidates(user_message, 5)

        if historical:
            context = "\n".join(
                f"[{m.get('date')} {m.get('time')}] {m.get('sender')}: {m.get('message')}"
                for m in historical
            )
            messages.append({"role":"system","content":"Relevant historical chat:\n"+context})

        if candidates:
            context = "\n".join(f"- {m.get('message')}" for m in candidates)
            messages.append({"role":"system","content":"Potential memory candidates:\n"+context})

        for m in self.recent_live():
            messages.append({"role":"user","content":m["prompt"]})
            messages.append({"role":"assistant","content":m["completion"]})

        messages.append({"role":"user","content":user_message})
        return messages

    async def call(self, provider, messages):
        key = os.getenv(provider["env"])
        if not key:
            raise Exception("API key missing")

        async with httpx.AsyncClient(timeout=30) as client:
            if provider["provider"] == "Gemini":
                prompt = "\n".join(f"{m['role']}: {m['content']}" for m in messages)
                r = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/{provider['model']}:generateContent?key={key}",
                    json={"contents":[{"parts":[{"text":prompt}]}]}
                )
                r.raise_for_status()
                d = r.json()
                reply = d["candidates"][0]["content"]["parts"][0]["text"]
                tokens = d.get("usageMetadata",{}).get("totalTokenCount", len(prompt+reply)//4)
                return reply.strip(), tokens

            urls = {
                "Groq":"https://api.groq.com/openai/v1/chat/completions",
                "Cerebras":"https://api.cerebras.ai/v1/chat/completions",
                "OpenRouter":"https://openrouter.ai/api/v1/chat/completions",
                "DeepSeek":"https://api.deepseek.com/chat/completions",
            }
            r = await client.post(
                urls[provider["provider"]],
                headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"},
                json={"model":provider["model"],"messages":messages,"temperature":0.7}
            )
            r.raise_for_status()
            d = r.json()
            reply = d["choices"][0]["message"]["content"]
            tokens = d.get("usage",{}).get("total_tokens", len(reply)//4)
            return reply.strip(), tokens

    async def chat(self, message, selected_api="auto"):
        messages = self.build_messages(message)
        providers = self.providers[:]

        if selected_api.lower() != "auto":
            providers.sort(key=lambda p: 0 if (
                p["id"].lower() == selected_api.lower() or
                p["provider"].lower() == selected_api.lower()
            ) else 1)

        for p in providers:
            if self.stats[p["id"]]["status"] not in ("Connected & Active","Rate Limited"):
                continue
            if self.stats[p["id"]]["status"] == "Rate Limited" and time.time() < self.stats[p["id"]]["cooldown"]:
                continue
            try:
                reply, tokens = await self.call(p, messages)
                self.stats[p["id"]]["tokens_used"] += tokens
                self.stats[p["id"]]["status"] = "Connected & Active"
                self.save_live(message, reply)
                return {
                    "status":"success",
                    "active_api":p["id"],
                    "provider":p["provider"],
                    "reply":reply,
                    "tokens":tokens,
                    "brain":{"historical_search":True,"database":self.db_active}
                }
            except Exception as e:
                print(f"[Abdullah Brain] {p['provider']}: {e}")
                self.stats[p["id"]]["status"] = "Rate Limited" if "429" in str(e) else "Error"
                self.stats[p["id"]]["cooldown"] = time.time()+60

        return {"status":"error","reply":"No configured AI provider is available right now.","tokens":0,"provider":"None"}

    def status(self):
        return {
            "name":"Abdullah",
            "online":True,
            "whatsapp_messages":len(self.chat_archive),
            "memory_candidates":len(self.memory_candidates),
            "participants":self.brain.get("source",{}).get("participants",[]),
            "database_connected":self.db_active,
            "apis":self.stats
        }

    def dashboard(self):
        return self.status()

abdullah_brain = AbdullahBrain()
