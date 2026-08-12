import os
import json
import time
from typing import List, Dict
from groq import Groq
import google.generativeai as genai

class AbdullahBrain:
    def __init__(self, memory_file="abdullah_memory_dataset.json", live_file="live_learning.json"):
        self.memory_file = memory_file
        self.live_file = live_file
        
        self.base_memories = self._load_json(self.memory_file)
        self.live_memories = self._load_json(self.live_file)
        self.learning_target = 50

        # Map API keys/indices to their specific models
        self.api_pool = []
        self._load_keys()

    def _load_keys(self):
        """Scans environment variables and maps all available APIs."""
        for env_name, env_val in os.environ.items():
            key = env_val.strip()
            if not key:
                continue
                
            provider = "Unknown"
            model_name = "unknown-model"
            daily_limit = 10000

            if "GROQ" in env_name:
                provider = "Groq"
                model_name = "llama-3.1-8b-instant"
                daily_limit = 14400
            elif "GEMINI" in env_name:
                provider = "Gemini"
                model_name = "gemini-2.5-flash"
                daily_limit = 1500000

            masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "Invalid"
            self.api_pool.append({
                "id": env_name, # e.g. GROQ_API_KEY_1, GEMINI_API_KEY_2
                ,
                "provider": provider,
                "model": model_name,
                "masked": masked,
                "tokens_used": 0,
                "daily_limit": daily_limit,
                "status": "Connected & Active",
                "cooldown": 0
            })

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
                "provider": api["provider"],
                "status": api["status"],
                "tokens_used": api["tokens_used"],
                "remaining": api["daily_limit"] - api["tokens_used"]
            })

        return {
            "backend_connected": True,
            "total_apis": len(self.api_pool),
            "connected_apis": connected_count,
            "combined_tokens_used": total_used,
            "combined_tokens_remaining": total_capacity - total_used,
            "api_breakdown": api_details
        }

    def _execute_api_call(self, api, messages):
        if api["provider"] == "Groq":
            client = Groq(api_key=api["key"])
            completion = client.chat.completions.create(
                model=api["model"], messages=messages, temperature=0.7, max_tokens=250
            )
            return completion.choices[0].message.content.strip(), completion.usage.total_tokens
        
        elif api["provider"] == "Gemini":
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

        for mem in self.live_memories[-2:]:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "model", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        if not self.api_pool:
            return {"reply": "Habibti, no APIs configured!", "tokens": 0, "provider": "None"}

        current_time = time.time()

        # CASE 1: User chose a specific API manually from the frontend dropdown
        if selected_api != "auto":
            target = next((api for api in self.api_pool if api["id"] == selected_api), None)
            if target:
                try:
                    reply, tokens = self._execute_api_call(target, messages)
                    target["tokens_used"] += tokens
                    reply = reply.replace("Abdullah:", "").strip()
                    if "Goodbye" not in reply:
                        self._save_live_memory(sana_message, reply)
                    return {"reply": reply, "tokens": tokens, "provider": f"{target['id']} ({target['provider']})"}
                except Exception as e:
                    target["status"] = "Failed / Rate Limited"
                    return {"reply": f"Selected API ({selected_api}) failed: {str(e)}", "tokens": 0, "provider": selected_api}

        # CASE 2: Auto Mode (Iterates through available active APIs with automatic failover)
        for api in self.api_pool:
            if api["status"] == "Rate Limited" and current_time < api["cooldown"]:
                continue

            try:
                reply, tokens = self._execute_api_call(api, messages)
                api["tokens_used"] += tokens
                api["status"] = "Connected & Active"

                reply = reply.replace("Abdullah:", "").strip()
                if "Goodbye" not in reply:
                    self._save_live_memory(sana_message, reply)

                return {"reply": reply, "tokens": tokens, "provider": f"{api['id']} ({api['provider']})"}

            except Exception as err:
                api["status"] = "Rate Limited" if "429" in str(err) else "Disconnected"
                api["cooldown"] = time.time() + 60
                continue

        return {"reply": "All APIs are currently rate-limited or offline, Habibti!", "tokens": 0, "provider": "None"}
            
