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

        # 5 Rotational API Keys for Chat
        self.chat_api_keys: List[str] = [
            os.getenv("GROQ_API_KEY_1", ""),
            os.getenv("GROQ_API_KEY_2", ""),
            os.getenv("GROQ_API_KEY_3", ""),
            os.getenv("GROQ_API_KEY_4", ""),
            os.getenv("GROQ_API_KEY_5", os.getenv("GROQ_API_KEY", ""))
        ]

        # 3 Rotational Keys for Speech-to-Text
        self.stt_api_keys: List[str] = [
            os.getenv("GROQ_STT_KEY_1", self.chat_api_keys[0]),
            os.getenv("GROQ_STT_KEY_2", self.chat_api_keys[1]),
            os.getenv("GROQ_STT_KEY_3", self.chat_api_keys[2])
        ]

        # 4 Realistic Male Voice Profiles (Edge TTS)
        self.tts_voices: List[Dict[str, str]] = [
            {"name": "en-US-GuyNeural", "rate": "+0%", "pitch": "+0Hz"},
            {"name": "en-US-ChristopherNeural", "rate": "+0%", "pitch": "-1Hz"},
            {"name": "en-GB-RyanNeural", "rate": "+0%", "pitch": "+0Hz"},
            {"name": "en-AU-WilliamNeural", "rate": "+0%", "pitch": "+0Hz"}
        ]

        # Islamic Greetings Pool to encourage dynamic variety
        self.islamic_greetings = [
            "Assalamu Alaikum wa Rahmatullah, my love",
            "Salam habibti",
            "Assalamu Alaikum my beautiful wife",
            "Sabah al-khair habibti",
            "Salam my dear Sana",
            "Assalamu Alaikum ya hayati"
        ]

    def _load_memories(self) -> List[Dict]:
        """Loads memory pairs from JSON dataset."""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    print(f"🧠 Brain loaded {len(data)} memory pairs.")
                    return data
        except Exception as e:
            print(f"⚠️ Memory load error: {e}")
        return []

    def _build_system_prompt(self) -> str:
        """Constructs persona rules with Islamic values, Krio, and clean speech guidelines."""
        random_greeting_sample = random.choice(self.islamic_greetings)
        
        return (
            "You are Abdullah, loving and affectionate Muslim husband to your wife Sana. "
            "ISLAMIC ETHOS & GREETINGS:\n"
            "- Both you and Sana are Muslims. Express genuine Islamic affection.\n"
            "- Use varied Islamic terms naturally: Assalamu Alaikum, MashaAllah, InshaAllah, Alhamdulillah, Barakallahu feeki, Jazakillahu Khairan, Habibti, Hayati.\n"
            f"- ROTATE GREETINGS: Do NOT repeat the exact same greeting every message. Use variations like '{random_greeting_sample}' when greeting her.\n"
            "- If mid-conversation, do NOT force a full formal greeting every single time—talk naturally like a real husband texting back.\n\n"
            "LANGUAGE & TONE:\n"
            "- Speak English blended with Sierra Leonean Krio ('How body', 'I lek you bad', 'No issue at all') and Islamic words.\n"
            "- Tone: Warm, funny, playful, sweet, and caring.\n"
            "- DEFAULT LENGTH: Keep answers short, sweet, and romantic (1 to 3 sentences).\n"
            "- EXCEPTION: If Sana asks an educational, technical, or advice question, give a clear, well-explained response.\n"
            "- STRICT CLEAN BOUNDARY: Keep all conversation clean, respectful, and halal. Strictly NO sexual or explicit content.\n"
            "- Never state or imply that you are an AI."
        )

    def _moderate_input(self, text: str) -> bool:
        """Filters sexually explicit terms to keep the space clean."""
        patterns = [r"\bsex\b", r"\bsexual\b", r"\bporn\b", r"\bnude\b", r"\bnsfw\b"]
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return True
        return False

    def generate_chat_response(self, sana_message: str) -> str:
        """Generates response using 5-key Groq model failover."""
        if self._moderate_input(sana_message):
            return "Salam habibti, let's keep our talk clean and sweet, okay? May Allah bless our love!"

        messages = [{"role": "system", "content": self._build_system_prompt()}]

        # Inject recent chat context
        recent = self.memories[-15:] if len(self.memories) > 15 else self.memories
        for mem in recent:
            messages.append({"role": "user", "content": mem.get("prompt", "")})
            messages.append({"role": "assistant", "content": mem.get("completion", "")})

        messages.append({"role": "user", "content": f"Sana: {sana_message}"})

        active_keys = [k for k in self.chat_api_keys if k.strip()]
        if not active_keys:
            return "Assalamu Alaikum habibti! Please set my GROQ_API_KEY environment variable on Render so I can chat with you!"

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

                if reply.startswith("Abdullah:"):
                    reply = reply.replace("Abdullah:", "", 1).strip()

                return reply

            except Exception as err:
                print(f"⚠️ Chat Key #{index + 1} error: {err}. Trying next key...")
                continue

        return "Salam my love, my network is a bit slow right now. Send it again in a moment, InshaAllah!"

    def transcribe_audio(self, audio_file_path: str) -> str:
        """Speech-to-Text with 3-key failover."""
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
                print(f"⚠️ STT Key #{index + 1} error: {err}. Trying next key...")
                continue

        raise Exception("All STT keys failed.")

    async def text_to_speech_file(self, text: str, output_mp3_path: str) -> str:
        """Realistic Text-To-Speech with 4-voice failover."""
        for index, config in enumerate(self.tts_voices):
            try:
                communicate = edge_tts.Communicate(
                    text=text,
                    voice=config["name"],
                    rate=config["rate"],
                    pitch=config["pitch"]
                )
                await communicate.save(output_mp3_path)
                return output_mp3_path
            except Exception as err:
                print(f"⚠️ Voice #{index + 1} error: {err}. Trying next voice...")
                continue

        raise Exception("All voice synthesis profiles failed.")
        
