import os
import json
import time
import requests
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

        # Define the 5 APIs from your Johnny Tec architecture
        self.api_models = {
            "Groq": "llama-3.1-8b-instant",
            "Gemini_Flash": "gemini-2.5-flash",
            "Gemini_Flash_Lite": "gemini-2.5-flash-lite",
            "Gemini_Live": "gemini-live-api", # For future voice integration
            "Gemini_Audio": "gemini-native-audio" # For future voice integration
        }

        # Auto-detect and categorize all API keys
        self.api_pool = []
        self._load_keys()

    def _load_keys(self):
        """Scans environment variables for Groq and Gemini keys."""
        for env_name, env_val in os.environ.items():
            key = env_val.strip()
            if not key:
                continue
                
            provider = None
            if env_name.startswith("GROQ_API_KEY"):
                provider = "Groq"
                daily_limit = 14400 # Groq rough daily free limit
            elif env_name.startswith("GEMINI_API_KEY"):
                provider = "Gemini"
                daily_limit = 1500000 # Gemini Flash rough daily free limit
                
            if provider:
                masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "Invalid"
                self.api_pool.append({
                    "name": env_name,
                    "key": key,
                    "provider": provider,
                    "masked": masked,
                    "tokens_used": 0,
                    "daily_limit": daily_limit,
                    "status": "Working",
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
        """Generates the full backend diagnostic dashboard data."""
        current_time = time.time()
        total_used = 0
        total_capacity = 0
        working_count = 0
        api_details = []

        for api in self.api_pool:
            if api["status"] == "Rate Limited" and current_time > api["cooldown"]:
                api["status"] = "Working"
                
            total_used += api["tokens_used"]
            total_capacity += api["daily_limit"]
            if api["status"] == "Working":
                working_count += 1
                
            api_details.append({
                "name": api["name"],
                "provider": api["provider"],
                "status": api["status"],
                "tokens_used": api["tokens_used"],
                "remaining": api["daily_limit"] - api["tokens_used"]
            })

        return {
            "backend_connected": True,
            "total_apis": len(self.api_pool),
            "working_apis": working_count,
            "combined_tokens_used": total_used,
            "combined_tokens_remaining": total_capacity - total_used,
            "api_breakdown": api_details
        }

    def _call_groq(self, api_data, messages):
        client = Groq(api_key=api_data["key"])
        completion = client.chat.completions.create(
            model=self.api_models["Groq"],
            messages=messages,
            temperature=0.7,
            max_tokens=250
        )
        return completion.choices[0].message.content.strip(), completion.usage.total_tokens

    def _call_gemini(self, api_data, messages):
        genai.configure(api_key=api_data["key"])
        model = genai.GenerativeModel(self.api_models["Gemini_Flash"])
        
        # Convert Groq/OpenAI message format to Gemini format
        gemini_history = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            gemini_history.append({"role": role, "parts": [msg["content"]]})
            
        response = model.generate_content(gemini_history)
        
        # Estimate tokens for Gemini (1 token ~= 4 characters)
        estimated_tokens = len(str(gemini_history)) // 4 + len(response.text) // 4
        return response.text.strip(), estimated_tokens

    def generate_chat_response(self, sana_message: str) -> dict:
        # Core Husband Logic
        messages = [{
            "role": "user", # Using user role here for better cross-compatibility with Gemini
            "content": "SYSTEM: You are Abdullah, Sana's real husband. Call her Sana, Habibti, or playfully 'motuu'. Be proactive and affectionate. If someone asks who Sana is, refuse to answer and say goodbye."
        }, {
            "role": "model",
            "content": "Understood. I am Abdullah, and I will only talk to my wife, Sana."
        }]

        for mem in self.live_memories[-2:]:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "model", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        if not self.api_pool:
            return {"reply": "Habibti, no APIs are configured on the server!", "tokens": 0, "provider": "None"}

        current_time = time.time()

        # 🚀 AUTO-SWITCHING LOGIC
        for api in self.api_pool:
            if api["status"] == "Rate Limited" and current_time < api["cooldown"]:
                continue

            try:
                if api["provider"] == "Groq":
                    reply, tokens = self._call_groq(api, messages)
                elif api["provider"] == "Gemini":
                    reply, tokens = self._call_gemini(api, messages)

                # Update API Stats
                api["tokens_used"] += tokens
                api["status"] = "Working"

                reply = reply.replace("Abdullah:", "").strip()
                if "Goodbye" not in reply:
                    self._save_live_memory(sana_message, reply)

                # Print to backend console for debugging
                print(f"✅ Success via {api['name']} | Tokens: {tokens}")
                return {"reply": reply, "tokens": tokens, "provider": api["provider"]}

            except Exception as err:
                print(f"❌ {api['name']} Failed: {str(err)}. Auto-switching to next API...")
                api["status"] = "Rate Limited" if "429" in str(err) or "exhausted" in str(err).lower() else "Offline"
                api["cooldown"] = time.time() + 60
                continue

        return {"reply": "Network overloaded, Habibti! All 5 APIs are maxed out.", "tokens": 0, "provider": "None"}
        
