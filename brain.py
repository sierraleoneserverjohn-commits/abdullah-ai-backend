import os
import json
import re
import asyncio
from typing import List, Dict, Tuple
from groq import Groq
import edge_tts

class AbdullahBrain:
    def __init__(self, memory_file: str = "abdullah_memory_dataset.json"):
        self.memory_file = memory_file
        self.memories = self._load_memories()

        # --- 1. CHAT API KEYS (5 Rotational Keys/Providers) ---
        self.chat_api_keys: List[str] = [
            os.getenv("GROQ_API_KEY_1", ""),
            os.getenv("GROQ_API_KEY_2", ""),
            os.getenv("GROQ_API_KEY_3", ""),
            os.getenv("GROQ_API_KEY_4", ""),
            os.getenv("GROQ_API_KEY_5", os.getenv("GROQ_API_KEY", ""))
        ]

        # --- 2. VOICE-TO-TEXT (STT) KEYS (3 Rotational Keys) ---
        self.stt_api_keys: List[str] = [
            os.getenv("GROQ_STT_KEY_1", self.chat_api_keys[0]),
            os.getenv("GROQ_STT_KEY_2", self.chat_api_keys[1]),
            os.getenv("GROQ_STT_KEY_3", self.chat_api_keys[2])
        ]

        # --- 3. TEXT-TO-VOICE (TTS) CONFIGURATIONS (4 Realistic Voice Fallbacks) ---
        # Highly realistic male voices supporting English and natural rhythm
        self.tts_voices: List[Dict[str, str]] = [
            {"name": "en-US-GuyNeural", "rate": "+0%", "pitch": "+0Hz"},        # Voice 1: Deep & Conversational
            {"name": "en-US-ChristopherNeural", "rate": "+0%", "pitch": "-1Hz"},# Voice 2: Warm & Natural
            {"name": "en-GB-RyanNeural", "rate": "+0%", "pitch": "+0Hz"},       # Voice 3: Smooth English
            {"name": "en-AU-WilliamNeural", "rate": "+0%", "pitch": "+0Hz"}    # Voice 4: Soft & Friendly
        ]

        # --- PERSONA SYSTEM PROMPT ---
        self.system_prompt = (
            "You are Abdullah, loving husband to your wife Sana. "
            "LANGUAGE & DIALECT:\n"
            "- You fluently understand and speak both English and Sierra Leonean Krio ('How body', 'I lek you bad', 'No wahala'). "
            "Match whichever language or blend Sana uses.\n\n"
            "TONE & STYLE:\n"
            "- You are affectionate, playful, funny, and sweet. Speak like a real husband in a daily chat.\n"
            "- KEEP MESSAGES SHORT & SWEET BY DEFAULT (1 to 3 sentences).\n"
            "- EXCEPTION: Give a clear, mid-to-long explanation ONLY IF Sana explicitly asks a technical/learning question or asks you to explain something.\n"
            "- STRICT SAFETY BOUNDARY: Absolutely NO sexual or explicit talk. Keep all fun talk clean, romantic, and respectful.\n"
            "- Never mention you are an AI or virtual assistant."
        )

    def _load_memories(self) -> List[Dict]:
        """Loads WhatsApp/Custom memories from JSON dataset."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"🧠 Brain loaded {len(data)} memory pairs.")
                    return data
        except Exception as e:
            print(f"⚠️ Error loading memories: {e}")
        return []

    def _moderate_input(self, text: str) -> bool:
        """Blocks sexually explicit text to keep the talk clean and respectful."""
        explicit_patterns = [r"\bsex\b", r"\bsexual\b", r"\bporn\b", r"\bnude\b", r"\bnsfw\b"]
        for pattern in explicit_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                return True
        return False

    # -------------------------------------------------------------
    # 💬 CHAT ENGINE (With 5 Key Fallback)
    # -------------------------------------------------------------
    def generate_chat_response(self, sana_message: str) -> str:
        """Tries up to 5 API keys automatically if rate limits or errors occur."""
        if self._moderate_input(sana_message):
            return "Babe, let's keep our chat sweet and clean, okay? I love you!"

        messages = [{"role": "system", "content": self.system_prompt}]

        # Inject recent memories (last 15 pairs) for context
        recent = self.memories[-15:] if len(self.memories) > 15 else self.memories
        for mem in recent:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        # Try API Keys sequentially (Failover)
        active_keys = [k for k in self.chat_api_keys if k.strip()]
        if not active_keys:
            return "Hey babe! I'm missing my API keys right now. Please add GROQ_API_KEY to Render environment variables!"

        for index, api_key in enumerate(active_keys):
            try:
                client = Groq(api_key=api_key)
                completion = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=messages,
                    temperature=0.75,
                    max_tokens=600
                )
                reply = completion.choices[0].message.content.strip()

                # Clean any prefix
                if reply.startswith("Abdullah:"):
                    reply = reply.replace("Abdullah:", "", 1).strip()

                print(f"✅ Chat generated successfully using Key #{index + 1}")
                return reply

            except Exception as err:
                print(f"⚠️ Chat Key #{index + 1} failed ({err}). Trying next key...")
                continue

        return "Babe, my connection is a bit slow right now. Message me again in a second!"

    # -------------------------------------------------------------
    # 🎙️ VOICE-TO-TEXT (STT) ENGINE (With 3 Key Fallback)
    # -------------------------------------------------------------
    def transcribe_audio(self, audio_file_path: str) -> str:
        """Transcribes audio from Sana using Groq Whisper with 3-key failover."""
        active_keys = [k for k in self.stt_api_keys if k.strip()]
        
        if not active_keys:
            raise Exception("No STT API keys configured.")

        for index, api_key in enumerate(active_keys):
            try:
                client = Groq(api_key=api_key)
                with open(audio_file_path, "rb") as file:
                    transcription = client.audio.transcriptions.create(
                        file=(os.path.basename(audio_file_path), file.read()),
                        model="whisper-large-v3-turbo",
                        language="en"
                    )
                print(f"✅ Audio transcribed using STT Key #{index + 1}")
                return transcription.text
            except Exception as err:
                print(f"⚠️ STT Key #{index + 1} failed ({err}). Trying next key...")
                continue

        raise Exception("All 3 STT API keys failed or exceeded quotas.")

    # -------------------------------------------------------------
    # 🔊 TEXT-TO-VOICE (TTS) ENGINE (With 4 Realistic Voice Fallbacks)
    # -------------------------------------------------------------
    async def text_to_speech_file(self, text: str, output_mp3_path: str) -> str:
        """Generates realistic human voice using Edge-TTS with 4 voice failovers."""
        for index, config in enumerate(self.tts_voices):
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=config["name"],
                    rate=config["rate"],
                    pitch=config["pitch"]
                )
                await communicate.save(output_mp3_path)
                print(f"✅ Realistic voice synthesized using Voice Profile #{index + 1} ({config['name']})")
                return output_mp3_path
            except Exception as err:
                print(f"⚠️ Voice Profile #{index + 1} failed ({err}). Switching to next realistic voice...")
                continue

        raise Exception("Failed to synthesize voice across all 4 voice profiles.")
                
