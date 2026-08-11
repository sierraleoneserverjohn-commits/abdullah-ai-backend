import json
import re
import os
import glob

def find_whatsapp_file() -> str:
    """Automatically finds any WhatsApp export .txt file in the directory."""
    txt_files = glob.glob("*.txt")
    for f in txt_files:
        if "whatsapp" in f.lower() or "chat" in f.lower() or "messi" in f.lower():
            return f
    # Fallback to the first non-requirements text file found
    for f in txt_files:
        if f != "requirements.txt":
            return f
    return ""

def parse_whatsapp_chat(txt_file_path: str = None, output_json_path: str = "abdullah_memory_dataset.json"):
    if not txt_file_path or not os.path.exists(txt_file_path):
        txt_file_path = find_whatsapp_file()

    if not txt_file_path or not os.path.exists(txt_file_path):
        print("❌ No WhatsApp .txt file found in the directory!")
        return

    print(f"📂 Auto-detected WhatsApp chat file: '{txt_file_path}'")
    
    with open(txt_file_path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()

    memories = []
    
    # Flexible pattern for lines like: "[12/08/2025, 14:30] Speaker: Message" or "12/08/2025, 14:30 - Speaker: Message"
    pattern = r"(?:\[?.*?\]?|\d{1,2}/\d{1,2}/\d{2,4},?\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM|am|pm)?\s*[-–]?)\s*([^:]+):\s*(.*)"

    last_sana_msg = None

    for line in lines:
        line = line.strip()
        match = re.search(pattern, line)
        if match:
            sender = match.group(1).strip()
            message = match.group(2).strip()

            # Ignore system messages and media attachment markers
            if "<Media omitted>" in message or "omitted" in message or "end-to-end encrypted" in message:
                continue

            # Identify Sana vs Abdullah (handles variations & emojis in names)
            sender_lower = sender.lower()
            if "sana" in sender_lower or "wife" in sender_lower:
                last_sana_msg = message
            elif ("abdullah" in sender_lower or "messi" in sender_lower or "goat" in sender_lower) and last_sana_msg:
                # Pair found: Sana spoke, Abdullah replied
                memories.append({
                    "prompt": f"Sana: {last_sana_msg}",
                    "completion": f"Abdullah: {message}"
                })
                last_sana_msg = None

    if not memories:
        print("⚠️ No direct Sana/Abdullah message pairs matched the default pattern. Storing raw non-system lines...")

    # Load existing JSON if present to merge
    existing_data = []
    if os.path.exists(output_json_path):
        try:
            with open(output_json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            existing_data = []

    combined = existing_data + memories

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

    print(f"✅ Successfully parsed {len(memories)} new chat pairs.")
    print(f"🧠 Total memories saved to '{output_json_path}': {len(combined)}")

if __name__ == "__main__":
    import sys
    file_arg = sys.argv[1] if len(sys.argv) > 1 else None
    parse_whatsapp_chat(file_arg)
    
