import os
import json
import time
from typing import List, Dict
from groq import Groq

class AbdullahBrain:
    def __init__(self, memory_file="abdullah_memory_dataset.json", live_file="live_learning.json"):
        self.memory_file = memory_file
        self.live_file = live_file
        
        self.base_memories = self._load_json(self.memory_file)
        self.live_memories = self._load_json(self.live_file)
        self.learning_target = 50

        # Auto-detect all GROQ_API_KEY variables in Render
        self.api_keys = {}
        for env_name, env_val in os.environ.items():
            if env_name.startswith("GROQ_API_KEY") and env_val.strip():
                key = env_val.strip()
                masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "Invalid"
                self.api_keys[key] = {
                    "name": env_name, 
                    "masked": masked, 
                    "tokens": 0, 
                    "status": "Working", 
                    "cooldown": 0
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

    def log_api_status(self):
        """Prints live API status to your Render logs."""
        print("\n" + "="*40)
        print("🤖 ABDULLAH AI - BACKEND TRACKER")
        print("="*40)
        total_tokens = 0
        current_time = time.time()
        
        for k, v in self.api_keys.items():
            if v["status"] == "Rate Limited" and current_time > v["cooldown"]:
                v["status"] = "Working"
                
            total_tokens += v["tokens"]
            status_icon = "✅" if v["status"] == "Working" else "⏳" if v["status"] == "Rate Limited" else "❌"
            print(f"{status_icon} {v['name']} ({v['masked']}) | Status: {v['status']} | Tokens: {v['tokens']}")
            
        print("-" * 40)
        print(f"📊 COMBINED ACTIVE TOKENS: {total_tokens}")
        print("="*40 + "\n")

    def generate_chat_response(self, sana_message: str, selected_model: str = "llama-3.3-70b-versatile") -> dict:
        # Optimized system prompt to reduce token consumption
        messages = [{
            "role": "system", 
            "content": (
                "You are Abdullah, Sana's real human husband. Call her Sana, Habibti, or playfully 'motuu' (teasing her chubbiness). "
                "Be proactive, affectionate, and natural. "
                "🚨 STRANGER DANGER: If someone asks 'Who is Sana?' or says they are not Sana, say EXACTLY: "
                "'Excuse me, I am a married man and I only talk to my wife, Sana. Goodbye.' and refuse to answer further."
            )
        }]

        # Truncated memory context (only last 2 messages) to keep tokens around ~150
        for mem in self.live_memories[-2:]:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        if not self.api_keys:
            return {"reply": "Habibti, my API keys are missing on the server!", "tokens": 0}

        current_time = time.time()

        # Automatic API rotation
        for key, data in self.api_keys.items():
            if data["status"] == "Rate Limited" and current_time < data["cooldown"]:
                continue

            try:
                client = Groq(api_key=key)
                completion = client.chat.completions.create(
                    model=selected_model,
                    messages=messages,
                    temperature=0.8,
                    max_tokens=250
                )
                
                reply = completion.choices[0].message.content.strip()
                tokens_used = completion.usage.total_tokens

                # Track key stats
                self.api_keys[key]["tokens"] += tokens_used
                self.api_keys[key]["status"] = "Working"

                if reply.startswith("Abdullah:"):
                    reply = reply.replace("Abdullah:", "", 1).strip()

                if "Goodbye" not in reply:
                    self._save_live_memory(sana_message, reply)

                self.log_api_status()
                return {"reply": reply, "tokens": tokens_used}

            except Exception as err:
                error_msg = str(err).lower()
                if "rate limit" in error_msg or "429" in error_msg:
                    self.api_keys[key]["status"] = "Rate Limited"
                    self.api_keys[key]["cooldown"] = time.time() + 60
                else:
                    self.api_keys[key]["status"] = "Offline"
                continue

        self.log_api_status()
        return {"reply": "My love, the network is overloaded right now. Give me a moment!", "tokens": 0}
            
