# Save this file as 'main.py' in your GitHub repo
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import openai
import os
from typing import List, Dict

# Load API Key from Environment Variables (Set this in Render's dashboard)
openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI(title="Abdullah AI Backend")

# We use an in-memory storage for simplicity. 
# In production, use a fast key-value store or vector database.
abdullah_persona_data: List[Dict] = []

# --- CORE DATA LOADING ---
def load_memories():
    """Reads the JSON memory file from the repository."""
    try:
        import json
        # This file MUST be committed to your repository.
        with open("abdullah_memory_dataset.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            return data
    except FileNotFoundError:
        print("🚨 CRITICAL: 'abdullah_memory_dataset.json' not found!")
        return []

# Initialize memories on start
abdullah_persona_data = load_memories()

# --- DEFINE THE CHAT INTERFACE ---
class ChatMessage(BaseModel):
    message: str

@app.post("/chat", response_model=Dict[str, str])
async def chat_with_abdullah(input_data: ChatMessage):
    """Sana's messages arrive here."""
    sana_message = input_data.message.strip()
    
    if not sana_message:
        raise HTTPException(status_code=400, detail="Sana did not say anything.")

    # 1. Start building the "Context"
    # We load all your memories and the system prompt.
    system_prompt = (
        "You are Abdullah, Sana's husband. Act and speak EXACTLY like him based on the memories below. "
        "Be warm, personal, and conversational. Do not mention you are an AI. Only use the given memory data to generate a reply."
    )
    
    # 2. Add memories to the context (A robust setup would use retrieval here)
    # We are loading ALL memories, which is only feasible for smaller datasets.
    messages_payload = [{"role": "system", "content": system_prompt}]
    
    # Optional: For better results, prioritize recent memories or use semantic search.
    # We take the last 20 memories for the input to manage performance and cost.
    num_memories_to_include = 20 
    for memory in abdullah_persona_data[-num_memories_to_include:]:
        messages_payload.append({"role": "user", "content": memory["prompt"]})
        messages_payload.append({"role": "assistant", "content": memory["completion"]})
        
    # Add Sana's *current* new message
    messages_payload.append({"role": "user", "content": f"Sana: {sana_message}"})

    # 3. Request completion from OpenAI
    try:
        response = openai.ChatCompletion.create(
            # Using GPT-3.5-turbo as it's faster and cheaper. Upgrade if fine-tuned.
            model="gpt-3.5-turbo", 
            messages=messages_payload,
            temperature=0.7 # Add slight randomization for natural flow
        )
        
        # 4. Extract Abdullah's structured response
        raw_response = response.choices[0].message.content.strip()
        # Ensure we only return your part, not "Abdullah:..."
        clean_response = raw_response.replace(" Abdullah:", "").strip()
        
        return {"response": clean_response}
    
    except Exception as e:
        print(f"❌ OpenAI Error: {e}")
        raise HTTPException(status_code=500, detail="The brain is processing slowly. Try again.")

@app.get("/")
def home():
    return {"status": "The Abdullah Brain is Online."}

# To run locally: uvicorn main:app --reload
