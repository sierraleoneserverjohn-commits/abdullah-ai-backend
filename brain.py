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
        
        self.base_memories = self._load_json(self.memory_file)
        self.live_memories = self._load_json(self.live_file)
        self.learning_target = 50

        # Dynamically load and track all Groq API keys
        self.api_keys = {}
        for env_name, env_val in os.environ.items():
            if env_name.startswith("GROQ_API_KEY") and env_val.strip():
                key_str = env_val.strip()
                # Mask the key for security (e.g., gsk_1234...abcd)
                masked = key_str[:7] + "..." + key_str[-4:] if len(key_str) > 10 else "Invalid Key"
                
                self.api_keys[key_str] = {
                    "name": env_name,
                    "masked": masked,
                    "tokens_used": 0,
                    "status": "Working", # Can be 'Working', 'Rate Limited', or 'Offline'
                    "cooldown_until": 0
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
        """Returns real-time data on all APIs for the frontend."""
        current_time = time.time()
        total_active_tokens = 0
        working_count = 0
        key_details = []

        for key, data in self.api_keys.items():
            # Check if a rate-limited key has finished its 60-second cooldown
            if data["status"] == "Rate Limited" and current_time >= data["cooldown_until"]:
                data["status"] = "Working"

            if data["status"] == "Working":
                working_count += 1
                total_active_tokens += data["tokens_used"]

            key_details.append({
                "api_name": data["name"],
                "key_preview": data["masked"],
                "status": data["status"],
                "tokens_used": data["tokens_used"]
            })

        return {
            "total_keys_configured": len(self.api_keys),
            "active_working_keys": working_count,
            "combined_active_tokens": total_active_tokens,
            "api_list": key_details
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

        combined_memory = self.base_memories[-4:] + self.live_memories[-2:]
        for mem in combined_memory:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        if not self.api_keys:
            return {"reply": "Habibti, my API keys are missing on the server!", "tokens": 0, "model_used": "none"}

        current_time = time.time()
        
        # Automatic API Routing
        for key, data in self.api_keys.items():
            if data["status"] == "Rate Limited" and current_time < data["cooldown_until"]:
                continue # Skip this key, try the next one
                
            try:
                client = Groq(api_key=key)
                completion = client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    temperature=0.8,
                    max_tokens=300
                )
                
                reply = completion.choices[0].message.content.strip()
                tokens = completion.usage.total_tokens

                # Success! Update this key's stats
                self.api_keys[key]["tokens_used"] += tokens
                self.api_keys[key]["status"] = "Working"

                if reply.startswith("Abdullah:"):
                    reply = reply.replace("Abdullah:", "", 1).strip()

                if "Goodbye" not in reply:
                    self._save_live_memory(sana_message, reply)

                return {"reply": reply, "tokens": tokens, "model_used": selected_model}

            except Exception as err:
                error_msg = str(err).lower()
                if "rate limit" in error_msg or "429" in error_msg:
                    self.api_keys[key]["status"] = "Rate Limited"
                    self.api_keys[key]["cooldown_until"] = time.time() + 60
                else:
                    self.api_keys[key]["status"] = "Offline"
                continue # Loop back and instantly try the next key
        
        # If all keys fail
        return {"reply": "My love, my network is completely overloaded right now. Give me a minute to breathe!", "tokens": 0, "model_used": "none"}
                    
