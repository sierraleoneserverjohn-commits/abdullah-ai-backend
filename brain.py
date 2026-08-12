import os
import json
import time
from typing import List, Dict
from groq import Groq

class AbdullahBrain:
    def __init__(self, memory_file="abdullah_memory.json", live_file="live_learning.json"):
        self.live_file = live_file
        self.live_memories = self._load_json(self.live_file)
        
        # Load and track all Groq APIs
        self.api_keys = {}
        for env_name, env_val in os.environ.items():
            if env_name.startswith("GROQ_API_KEY") and env_val.strip():
                key = env_val.strip()
                masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "Invalid"
                self.api_keys[key] = {
                    "name": env_name, "masked": masked, "tokens": 0, 
                    "status": "Working", "cooldown": 0
                }

    def _load_json(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return []

    def _save_live_memory(self, prompt, completion):
        self.live_memories.append({"prompt": f"Sana: {prompt}", "completion": f"Abdullah: {completion}"})
        with open(self.live_file, "w", encoding="utf-8") as f:
            json.dump(self.live_memories, f, ensure_ascii=False, indent=2)

    def print_backend_tracker(self):
        """Prints the real-time API status directly to the Render server logs."""
        print("\n" + "="*40)
        print("🤖 ABDULLAH AI - BACKEND TRACKER")
        print("="*40)
        
        total_tokens = 0
        current_time = time.time()
        
        for k, v in self.api_keys.items():
            if v["status"] == "Rate Limited" and current_time > v["cooldown"]:
                v["status"] = "Working"
                
            total_tokens += v["tokens"]
            status_symbol = "✅" if v["status"] == "Working" else "⏳" if v["status"] == "Rate Limited" else "❌"
            print(f"{status_symbol} {v['name']} ({v['masked']}) | Status: {v['status']} | Tokens: {v['tokens']}")
            
        print("-" * 40)
        print(f"📊 COMBINED TOKENS USED: {total_tokens}")
        print("="*40 + "\n")

    def generate_chat_response(self, sana_message, selected_model="llama-3.3-70b-versatile"):
        # OPTIMIZED SYSTEM PROMPT (Saves ~100 tokens)
        messages = [{"role": "system", "content": "You are Abdullah, Sana's real husband. Call her Sana, Habibti, or playfully 'motuu' (teasing her chubbiness). Be proactive and natural. If someone asks 'Who is Sana?', say: 'I only talk to my wife, Sana. Goodbye.' and stop."}]

        # OPTIMIZED MEMORY: Only last 2 messages (Saves ~200 tokens)
        for mem in self.live_memories[-2:]:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        # AUTO-ROUTING API LOGIC
        for key, data in self.api_keys.items():
            if data["status"] == "Rate Limited" and time.time() < data["cooldown"]:
                continue
                
            try:
                client = Groq(api_key=key)
                completion = client.chat.completions.create(model=selected_model, messages=messages, temperature=0.7, max_tokens=200)
                reply = completion.choices[0].message.content.replace("Abdullah:", "").strip()
                tokens = completion.usage.total_tokens

                self.api_keys[key]["tokens"] += tokens
                self.api_keys[key]["status"] = "Working"
                
                if "Goodbye" not in reply:
                    self._save_live_memory(sana_message, reply)

                self.print_backend_tracker() # Log to server
                return {"reply": reply, "tokens_used": tokens}
                
            except Exception as e:
                self.api_keys[key]["status"] = "Rate Limited" if "429" in str(e) else "Offline"
                self.api_keys[key]["cooldown"] = time.time() + 60
                continue
        
        self.print_backend_tracker()
        return {"reply": "Network overloaded, Habibti!", "tokens_used": 0}
                
