import os
import json
from openai import OpenAI

# Initialize the OpenAI client (picks up OPENAI_API_KEY from environment)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

class AbdullahBrain:
    def __init__(self, memory_file="abdullah_memory_dataset.json"):
        self.memory_file = memory_file
        self.memories = self._load_memories()
        self.system_prompt = (
            "You are Abdullah. You are talking directly to your beloved wife, Sana. "
            "Respond naturally, warmly, and authentically as her husband based on your personality "
            "and shared conversational history. Never mention you are an AI."
        )

    def _load_memories(self):
        """Loads structured chat memories from JSON."""
        try:
            with open(self.memory_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"🧠 Brain loaded {len(data)} memory pairs successfully.")
                return data
        except FileNotFoundError:
            print(f"⚠️ Memory file '{self.memory_file}' not found. Initializing empty brain.")
            return []

    def generate_response(self, sana_message: str) -> str:
        """Processes Sana's input message and returns Abdullah's reply."""
        messages = [{"role": "system", "content": self.system_prompt}]

        # Append recent memory context (last 20 pairs)
        recent_memories = self.memories[-20:] if len(self.memories) > 20 else self.memories
        for mem in recent_memories:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        # Append Sana's new incoming message
        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini", # Fast, smart, and cost-effective
                messages=messages,
                temperature=0.7
            )
            reply = response.choices[0].message.content.strip()
            
            # Clean out prefix if model outputs "Abdullah:"
            if reply.startswith("Abdullah:"):
                reply = reply.replace("Abdullah:", "", 1).strip()
                
            return reply

        except Exception as e:
            print(f"❌ Brain Error: {e}")
            return "Hey babe, give me a second, my phone is acting up!"
          
