import os
import tempfile
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from brain import AbdullahBrain

app = FastAPI(title="Abdullah AI Backend Engine")

# Enable CORS so frontend can connect cleanly
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Brain
brain = AbdullahBrain()

class ChatPayload(BaseModel):
    message: str

@app.get("/")
def home():
    return {"status": "online", "system": "Abdullah AI Brain Active & Listening"}

# 1. 💬 Chat Endpoint
@app.post("/chat")
async def chat_endpoint(payload: ChatPayload):
    sana_text = payload.message.strip()
    if not sana_text:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    reply = brain.generate_chat_response(sana_text)
    return {"response": reply}

# 2. 🎙️ Voice-To-Text Endpoint (STT)
@app.post("/transcribe")
async def transcribe_endpoint(file: UploadFile = File(...)):
    if not file:
        raise HTTPException(status_code=400, detail="Audio file required.")

    # Save temp audio file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio.write(await file.read())
        temp_audio_path = temp_audio.name

    try:
        text = brain.transcribe_audio(temp_audio_path)
        return {"transcription": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)

# 3. 🔊 Text-To-Voice Endpoint (Live Realistic Voice)
@app.post("/speak")
async def speak_endpoint(payload: ChatPayload):
    text = payload.message.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    try:
        await brain.text_to_speech_file(text, output_path)
        return FileResponse(
            path=output_path,
            media_type="audio/mpeg",
            filename="abdullah_voice.mp3"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice synthesis failed: {str(e)}")

# To run locally: uvicorn app:app --reload
