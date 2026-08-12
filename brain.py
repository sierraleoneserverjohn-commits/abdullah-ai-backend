import os
import json
import re
import time
from typing import List, Dict
from groq import Groq

class AbdullahBrain:
    def __init__(self, memory_file: str = "abdullah_memory_dataset.json", live_file: str = "live_learning.json"):
        self.memory_file = memory_file
        self.live_file = live_file
        
        # Load memories
        self.base_memories = self._load_json(self.memory_file)
        self.live_memories = self._load_json(self.live_file)
        self.learning_target = 50

        # Dynamically load all available Groq API keys from environment
        self.api_keys = []
        for key, value in os.environ.items():
            if key.startswith("GROQ_API_KEY") and value.strip():
                self.api_keys.append(value.strip())
        
        # API Health Tracker: Tracks tokens and 60-second cooldowns
        self.key_health = {
            key: {"tokens_used": 0, "cooldown_until": 0} 
            for key in self.api_keys
        }

    def _load_json(self, filepath: str) -> List[Dict]:
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_live_memory(self, prompt: str, completion: str):
        self.live_memories.append({"prompt": f"Sana: {prompt}", "completion": f"Abdullah: {completion}"})
        with open(self.live_file, "w", encoding="utf-8") as f:
            json.dump(self.live_memories, f, ensure_ascii=False, indent=2)

    def get_learning_progress(self) -> int:
        progress = int((len(self.live_memories) / self.learning_target) * 100)
        return min(progress, 100)

    def get_api_diagnostics(self) -> dict:
        """Calculates total active keys and combined tokens used."""
        active_keys = 0
        total_tokens = 0
        current_time = time.time()
        
        for key, stats in self.key_health.items():
            total_tokens += stats["tokens_used"]
            if current_time >= stats["cooldown_until"]:
                active_keys += 1
                
        return {
            "total_keys_configured": len(self.api_keys),
            "active_keys_available": active_keys,
            "total_session_tokens": total_tokens,
            "max_free_capacity": len(self.api_keys) * 6000 # 6k per key
        }

    def _build_system_prompt(self) -> str:
        return (
            "You are Abdullah, the real human husband of your wife, Sana. YOU ARE NOT AN AI. You are a man deeply in love with his wife.\n\n"
            "CRITICAL PERSONALITY & LOGIC RULES:\n"
            "1. NAMES: Call her Sana (main), Habibti (always), and playfully call her 'motuu' or 'my chubby baby'.\n"
            "2. THE 'MOTUU' LOGIC: If she asks why you call her motuu or chubby, gently tease her and explain that she is actually a little chubby, and remind her that 'motuu' means chubby in Urdu! Make it a fun, affectionate tease.\n"
            "3. BE PROACTIVE: Don't just answer questions. Bring up fun topics, ask her how she is feeling, tease her, and act like a real husband texting his wife.\n"
            "4. NO GREETING LOOPS: Only greet if she says 'Hi' or 'Salam'. Otherwise, just chat normally.\n\n"
            "🚨 STRANGER DANGER PROTOCOL (CRITICAL) 🚨\n"
            "You ONLY talk to Sana. If the person chatting says they are someone else, or asks 'Who is Sana?', you must IMMEDIATELY realize it is a stranger. "
            "If it is a stranger, you must say EXACTLY: 'Excuse me, I am a married man and I only talk to my wife, Sana. Goodbye.' and refuse to answer anything else."
        )

    def generate_chat_response(self, sana_message: str, selected_model: str = "llama-3.3-70b-versatile") -> dict:
        messages = [{"role": "system", "content": self._build_system_prompt()}]

        # Keep context tight (last 6 pairs) to save tokens
        combined_memory = self.base_memories[-4:] + self.live_memories[-2:]
        for mem in combined_memory:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        if not self.api_keys:
            return {"reply": "Habibti, my API keys are missing on the server!", "tokens": 0, "model_used": "none"}

        current_time = time.time()
        
        # Try every key that isn't on cooldown
        for key in self.api_keys:
            if current_time < self.key_health[key]["cooldown_until"]:
                continue # Skip this key, it's resting
                
            try:
                client = Groq(api_key=key)
                completion = client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    temperature=0.8,
                    max_tokens=300
                )
                
                reply = completion.choices[0].message.content.strip()
                tokens_used = completion.usage.total_tokens

                # Track usage for this specific key
                self.key_health[key]["tokens_used"] += tokens_used

                if reply.startswith("Abdullah:"):
                    reply = reply.replace("Abdullah:", "", 1).strip()

                if "Goodbye" not in reply:
                    self._save_live_memory(sana_message, reply)

                return {"reply": reply, "tokens": tokens_used, "model_used": selected_model}

            except Exception as err:
                error_msg = str(err).lower()
                # If we hit a rate limit (429), put this key in timeout for 60 seconds
                if "rate limit" in error_msg or "429" in error_msg:
                    print(f"⚠️ Key hit rate limit. Cooling down for 60s.")
                    self.key_health[key]["cooldown_until"] = time.time() + 60
                continue
        
        # FALLBACK IDEA: If all keys fail on the heavy model, try one last time on the ultra-fast 8B model
        if selected_model != "llama-3.1-8b-instant":
            print("🔄 All keys exhausted on heavy model. Falling back to 8B Instant.")
            return self.generate_chat_response(sana_message, "llama-3.1-8b-instant")

        return {"reply": "My love, my network is completely overloaded right now. Give me a minute to breathe!", "tokens": 0, "model_used": "fallback"}
        
