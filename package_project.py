import os
import zipfile

OUTPUT_ZIP = r"c:\Users\mayan\.gemini\antigravity\scratch\resonance_dj_bot\MoggerAI_Cloud_Package.zip"
BASE_DIR = r"c:\Users\mayan\.gemini\antigravity\scratch\resonance_dj_bot"

EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "env", "venv"}
EXCLUDE_FILES = {".env", "MoggerAI_Cloud_Package.zip"}

print(f">> Packaging project for 1-click cloud upload...")

with zipfile.ZipFile(OUTPUT_ZIP, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for file in files:
            if file in EXCLUDE_FILES or file.endswith('.pyc') or file.endswith('.log'):
                continue
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, BASE_DIR)
            zipf.write(full_path, rel_path)
            print(f"  + Added: {rel_path}")

print(f"\n✅ Package successfully created at:\n{OUTPUT_ZIP}")
