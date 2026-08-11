import json
import re
import os

def parse_whatsapp_chat(txt_file_path: str, output_json_path: str = "abdullah_memory_dataset.json"):
    if not os.path.exists(txt_file_path):
        print(f"❌ File '{txt_file_path}' not found!")
        return

    print(f"📂 Reading WhatsApp chat from '{txt_file_path}'...")
    
    with open(txt_file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    memories = []
    
    # Regex pattern to match standard WhatsApp lines (e.g., "[12/08/2025, 14:30] Sana: Hello")
    pattern = r"\[?.*?\]?\s*([^:]+):\s*(.*)"

    last_sana_msg = None

    for line in lines:
        line = line.strip()
        match = re.search(pattern, line)
        if match:
            sender = match.group(1).strip()
            message = match.group(2).strip()

            # Ignore system messages / media omitted
            if "<Media omitted>" in message or "Messages and calls are end-to-end encrypted" in message:
                continue

            # Identify Sana or Abdullah (case insensitive matching)
            if "sana" in sender.lower():
                last_sana_msg = message
            elif "abdullah" in sender.lower() and last_sana_msg:
                # Pair found
                memories.append({
                    "prompt": f"Sana: {last_sana_msg}",
                    "completion": f"Abdullah: {message}"
                })
                last_sana_msg = None  # Reset for next pair

    # Append to existing dataset if present
    existing_data = []
    if os.path.exists(output_json_path):
        try:
            with open(output_json_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        except Exception:
            existing_data = []

    combined_data = existing_data + memories

    with open(output_json_path, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Success! Parsed {len(memories)} message pairs.")
    print(f"🧠 Total memories in '{output_json_path}': {len(combined_data)}")

if __name__ == "__main__":
    import sys
    # Usage: python upload_whatsapp.py _chat.txt
    file_input = sys.argv[1] if len(sys.argv) > 1 else "_chat.txt"
    parse_whatsapp_chat(file_input)
  
