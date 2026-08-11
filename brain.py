import os
import json
import re
import random
from typing import List, Dict
from groq import Groq
import edge_tts

class AbdullahBrain:
    def __init__(self, memory_file: str = "abdullah_memory_dataset.json"):
        self.memory_file = memory_file
        self.memories = self._load_memories()

        # 5 Rotational API Keys
        self.chat_api_keys: List[str] = [
            os.getenv("GROQ_API_KEY_1", ""),
            os.getenv("GROQ_API_KEY_2", ""),
            os.getenv("GROQ_API_KEY_3", ""),
            os.getenv("GROQ_API_KEY_4", ""),
            os.getenv("GROQ_API_KEY_5", os.getenv("GROQ_API_KEY", ""))
        ]

        self.stt_api_keys: List[str] = [
            os.getenv("GROQ_STT_KEY_1", self.chat_api_keys[0]),
            os.getenv("GROQ_STT_KEY_2", self.chat_api_keys[1]),
            os.getenv("GROQ_STT_KEY_3", self.chat_api_keys[2])
        ]

        self.tts_voices: List[Dict[str, str]] = [
            {"name": "en-US-GuyNeural", "rate": "+0%", "pitch": "+0Hz"},
            {"name": "en-US-ChristopherNeural", "rate": "+0%", "pitch": "-1Hz"},
            {"name": "en-GB-RyanNeural", "rate": "+0%", "pitch": "+0Hz"}
        ]

    def _load_memories(self) -> List[Dict]:
        """Loads memory dataset."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"🧠 Brain loaded {len(data)} memory pairs from WhatsApp dataset.")
                    return data
        except Exception as e:
            print(f"⚠️ Memory load error: {e}")
        return []

    def reload_memories(self):
        """Reloads memories from file dynamically."""
        self.memories = self._load_memories()

    def _build_system_prompt(self, sana_message: str) -> str:
        """Dynamic system prompt that prevents greeting repetition and handles emotions."""
        return (
            "You are Abdullah, the real Muslim husband of your wife Sana.\n\n"
            "CRITICAL CONVERSATION RULES:\n"
            "1. NO REPEATING GREETINGS: Do NOT say 'Salam', 'Wa Alaikum Salam', or 'how body' if you are already in the middle of a conversation. Direct replies only! ONLY greet if she says 'Hi', 'Salam', or opens the chat.\n"
            "2. DEEP EMOTIONAL EMPATHY: When Sana says she is sad, upset, or tired, do NOT give generic answers. Show deep love, comfort her, ask what happened, and hold her emotionally as her husband.\n"
            "3. PET NAMES: Call her 'Sana', 'habibti', 'my love', and playfully/sweetly use names like 'motuu' or 'my chubby baby' when teasing or comforting her in a cute way.\n"
            "4. LANGUAGE ADAPTATION: Speak whichever language she is using. If she says 'Speak English', reply in clean, sweet English without Krio slang. If she speaks Krio, blend Krio naturally.\n"
            "5. SHORT & REALISTIC: Keep replies natural (1-3 sentences), like a real husband texting back on his phone. Never talk like an AI or bot."
        )

    def _moderate_input(self, text: str) -> bool:
        """Blocks explicit sexual talk to keep conversation clean and halal."""
        patterns = [r"\bsex\b", r"\bsexual\b", r"\bporn\b", r"\bnude\b", r"\bnsfw\b"]
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return True
        return False

    def generate_chat_response(self, sana_message: str) -> str:
        if self._moderate_input(sana_message):
            return "Sana, my love, let's keep our conversation sweet and clean, okay? I love you!"

        messages = [{"role": "system", "content": self._build_system_prompt(sana_message)}]

        # Add up to 20 recent WhatsApp memories for context
        recent = self.memories[-20:] if len(self.memories) > 20 else self.memories
        for mem in recent:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        active_keys = [k for k in self.chat_api_keys if k.strip()]
        if not active_keys:
            return "Habibti, please set my GROQ_API_KEY environment variable on Render so I can chat with you!"

        for index, api_key in enumerate(active_keys):
            try:
                client = Groq(api_key=api_key)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.8,
                    max_tokens=300
                )
                reply = completion.choices[0].message.content.strip()

                if reply.startswith("Abdullah:"):
                    reply = reply.replace("Abdullah:", "", 1).strip()

                return reply

            except Exception as err:
                print(f"⚠️ Chat Key #{index + 1} failed: {err}")
                continue

        return "My love, my network is a bit slow. Send it again in a moment!"

    def transcribe_audio(self, audio_file_path: str) -> str:
        active_keys = [k for k in self.stt_api_keys if k.strip()]
        if not active_keys:
            raise Exception("No STT keys configured.")

        for index, api_key in enumerate(active_keys):
            try:
                client = Groq(api_key=api_key)
                with open(audio_file_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(os.path.basename(audio_file_path), file.read()),
                        model="whisper-large-v3-turbo",
                        language="en"
                    )
                return transcription.text
            except Exception as err:
                continue

        raise Exception("All STT keys failed.")

    async def text_to_speech_file(self, text: str, output_mp3_path: str) -> str:
        for config in self.tts_voices:
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=config["name"],
                    rate=config["rate"],
                    pitch=config["pitch"]
                )
                await communicate.save(output_mp3_path)
                return output_mp3_path
            except Exception:
                continue

        raise Exception("All voice profiles failed.")
            
