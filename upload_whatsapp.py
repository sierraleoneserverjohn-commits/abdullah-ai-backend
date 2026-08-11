import json
import re
import os
import glob

def find_chat_file() -> str:
    """Finds any exported WhatsApp txt file regardless of name or emojis."""
    txt_files = glob.glob("*.txt")
    for f in txt_files:
        if f.lower() != "requirements.txt":
            return f
    return ""

def parse_whatsapp_chat(txt_file_path: str = None, output_json_path: str = "abdullah_memory_dataset.json"):
    if not txt_file_path or not os.path.exists(txt_file_path):
        txt_file_path = find_chat_file()

    if not txt_file_path or not os.path.exists(txt_file_path):
        print("❌ No WhatsApp chat file found in directory!")
        return []

    print(f"📂 Found chat file: '{txt_file_path}'")

    with open(txt_file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    memories = []
    # Matches WhatsApp line timestamp format across Android & iOS
    pattern = r"^\[?.*?\]?\s*([^:]+):\s*(.*)$"

    last_sana_msg = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        match = re.search(pattern, line)
        if match:
            sender = match.group(1).strip().lower()
            message = match.group(2).strip()

            # Skip system lines and omitted media
            if "media omitted" in message.lower() or "end-to-end encrypted" in message.lower():
                continue

            # Check for Sana or Abdullah
            if "sana" in sender or "wife" in sender:
                last_sana_msg = message
            elif ("abdullah" in sender or "messi" in sender or "goat" in sender) and last_sana_msg:
                memories.append({
                    "prompt": f"Sana: {last_sana_msg}",
                    "completion": f"Abdullah: {message}"
                })
                last_sana_msg = None

    print(f"🧠 Parsed {len(memories)} conversation pairs from WhatsApp chat.")

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(memories, f, ensure_ascii=False, indent=2)

    print(f"✅ Successfully created '{output_json_path}'!")
    return memories

if __name__ == "__main__":
    parse_whatsapp_chat()
    
