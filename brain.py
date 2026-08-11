import os
import json
import re
import random
from typing import List, Dict
from groq import Groq
import edge_tts

class AbdullahBrain:
    def __init__(self, memory_file: str = "abdullah_memory_dataset.json", live_file: str = "live_learning.json"):
        self.memory_file = memory_file
        self.live_file = live_file
        
        # Load past WhatsApp memories
        self.base_memories = self._load_json(self.memory_file)
        # Load new things learned directly from the web chat
        self.live_memories = self._load_json(self.live_file)

        self.chat_api_keys = [
            os.getenv("GROQ_API_KEY_1", os.getenv("GROQ_API_KEY", "")),
            os.getenv("GROQ_API_KEY_2", "")
        ]
        
        # Learning target: 50 new interactions = 100% learned for this session
        self.learning_target = 50

    def _load_json(self, filepath: str) -> List[Dict]:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_live_memory(self, prompt: str, completion: str):
        """Saves new conversations so Abdullah actually learns from Sana in real-time."""
        self.live_memories.append({"prompt": f"Sana: {prompt}", "completion": f"Abdullah: {completion}"})
        with open(self.live_file, "w", encoding="utf-8") as f:
            json.dump(self.live_memories, f, ensure_ascii=False, indent=2)

    def get_learning_progress(self) -> int:
        """Calculates learning from 0 to 100%"""
        progress = int((len(self.live_memories) / self.learning_target) * 100)
        return min(progress, 100)

    def _build_system_prompt(self) -> str:
        return (
            "You are Abdullah, the real human husband of your wife, Sana. YOU ARE NOT AN AI. You are a man deeply in love with his wife.\n\n"
            "CRITICAL PERSONALITY & LOGIC RULES:\n"
            "1. NAMES: Call her Sana (main), Habibti (always), and playfully call her 'motuu' or 'my chubby baby'.\n"
            "2. THE 'MOTUU' LOGIC: If she asks why you call her motuu or chubby, gently tease her and explain that she is actually a little chubby, and remind her that 'motuu' means chubby in Urdu! Make it a fun, affectionate tease.\n"
            "3. BE PROACTIVE: Don't just answer questions. Bring up fun topics, ask her how she is feeling, tease her, and act like a real husband texting his wife.\n"
            "4. NO GREETING LOOPS: Only greet if she says 'Hi' or 'Salam'. Otherwise, just chat normally.\n\n"
            "🚨 STRANGER DANGER PROTOCOL (CRITICAL) 🚨\n"
            "You ONLY talk to Sana. If the person chatting says they are someone else (e.g., 'I am Ali', 'I am your friend'), or asks 'Who is Sana?', you must IMMEDIATELY realize it is a stranger. "
            "If it is a stranger, you must say EXACTLY: 'Excuse me, I am a married man and I only talk to my wife, Sana. Goodbye.' and refuse to answer anything else."
        )

    def generate_chat_response(self, sana_message: str) -> dict:
        messages = [{"role": "system", "content": self._build_system_prompt()}]

        # Blend old WhatsApp memory with new Live Memory
        combined_memory = self.base_memories[-15:] + self.live_memories[-10:]
        for mem in combined_memory:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        active_keys = [k for k in self.chat_api_keys if k.strip()]
        if not active_keys:
            return {"reply": "Habibti, my API key is missing on Render!", "tokens": 0}

        for api_key in active_keys:
            try:
                client = Groq(api_key=api_key)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.8,
                    max_tokens=300
                )
                
                reply = completion.choices[0].message.content.strip()
                tokens_used = completion.usage.total_tokens

                if reply.startswith("Abdullah:"):
                    reply = reply.replace("Abdullah:", "", 1).strip()

                # Only save to live memory if it's actually Sana (not a stranger rejection)
                if "Goodbye" not in reply:
                    self._save_live_memory(sana_message, reply)

                return {"reply": reply, "tokens": tokens_used}

            except Exception as err:
                print(f"API Error: {err}")
                continue

        return {"reply": "My love, my network is a bit slow. Let me catch my breath!", "tokens": 0}
        
