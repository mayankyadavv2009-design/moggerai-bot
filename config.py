import os
from dotenv import load_dotenv

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
DEFAULT_PREFIX = os.getenv("DEFAULT_PREFIX", "!")
WEB_PORT = int(os.getenv("PORT", os.getenv("WEB_PORT", "5000")))
DEFAULT_VOLUME = float(os.getenv("DEFAULT_VOLUME", "0.8"))
YOUTUBE_STATUS_URL = os.getenv("YOUTUBE_STATUS_URL", "https://www.youtube.com/watch?v=1Ou9YGcQzls")
STATUS_TEXT = os.getenv("STATUS_TEXT", "🔴 LIVE • JOIN ME NOW ⚡")
def get_gemini_keys() -> list[str]:
    keys = []
    # 1. Check numbered keys: GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.
    for i in range(1, 101):
        k = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if k and k not in keys:
            keys.append(k)
        k_alt = os.getenv(f"GEMINI_KEY_{i}", "").strip()
        if k_alt and k_alt not in keys:
            keys.append(k_alt)

    # 2. Check comma-separated GEMINI_API_KEYS
    raw = os.getenv("GEMINI_API_KEYS", "") or os.getenv("GEMINI_API_KEY", "") or os.getenv("GOOGLE_API_KEY", "")
    if raw:
        for k in raw.replace(';', ',').replace('\n', ',').split(','):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys

def save_gemini_keys(keys_list: list[str]) -> list[str]:
    clean_keys = []
    for k in keys_list:
        k = k.strip()
        if k and k not in clean_keys:
            clean_keys.append(k)

    # Update environment variables
    for i in range(1, 101):
        if f"GEMINI_API_KEY_{i}" in os.environ:
            del os.environ[f"GEMINI_API_KEY_{i}"]
    for i, k in enumerate(clean_keys, start=1):
        os.environ[f"GEMINI_API_KEY_{i}"] = k
    os.environ["GEMINI_API_KEYS"] = ",".join(clean_keys)
    os.environ["GEMINI_API_KEY"] = clean_keys[0] if clean_keys else ""

    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        # Filter out old key lines
        new_lines = []
        for line in lines:
            trimmed = line.strip()
            if (trimmed.startswith("GEMINI_API_KEY_") or 
                trimmed.startswith("GEMINI_KEY_") or 
                trimmed.startswith("GEMINI_API_KEYS=") or 
                trimmed.startswith("GEMINI_API_KEY=")):
                continue
            new_lines.append(line)

        # Append cleanly formatted numbered keys
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        
        new_lines.append("\n# ==========================================================\n")
        new_lines.append(f"# 🔑 Gemini 2.5 Flash API Key Rotation Pool ({len(clean_keys)} Keys)\n")
        new_lines.append("# ==========================================================\n")
        for i, k in enumerate(clean_keys, start=1):
            new_lines.append(f"GEMINI_API_KEY_{i}={k}\n")
        
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
    return clean_keys

GEMINI_API_KEYS = get_gemini_keys()
GEMINI_API_KEY = GEMINI_API_KEYS[0] if GEMINI_API_KEYS else ""

def get_groq_keys() -> list[str]:
    keys = []
    for i in range(1, 51):
        k = os.getenv(f"GROQ_API_KEY_{i}", "").strip()
        if k and k not in keys:
            keys.append(k)
        k_alt = os.getenv(f"GROQ_KEY_{i}", "").strip()
        if k_alt and k_alt not in keys:
            keys.append(k_alt)
    raw = os.getenv("GROQ_API_KEYS", "") or os.getenv("GROQ_API_KEY", "")
    if raw:
        for k in raw.replace(';', ',').replace('\n', ',').split(','):
            k = k.strip()
            if k and k not in keys:
                keys.append(k)
    return keys

GROQ_API_KEYS = get_groq_keys()
GROQ_API_KEY = GROQ_API_KEYS[0] if GROQ_API_KEYS else ""

def save_status(new_url: str = None, new_text: str = None):
    global YOUTUBE_STATUS_URL, STATUS_TEXT
    if new_url:
        YOUTUBE_STATUS_URL = new_url.strip()
    if new_text:
        STATUS_TEXT = new_text.strip()
        
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        has_url = False
        has_text = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("YOUTUBE_STATUS_URL="):
                new_lines.append(f"YOUTUBE_STATUS_URL={YOUTUBE_STATUS_URL}\n")
                has_url = True
            elif line.strip().startswith("STATUS_TEXT="):
                new_lines.append(f"STATUS_TEXT={STATUS_TEXT}\n")
                has_text = True
            else:
                new_lines.append(line)
        if not has_url:
            new_lines.append(f"YOUTUBE_STATUS_URL={YOUTUBE_STATUS_URL}\n")
        if not has_text:
            new_lines.append(f"STATUS_TEXT={STATUS_TEXT}\n")
        with open(env_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
            
    return YOUTUBE_STATUS_URL, STATUS_TEXT

def save_youtube_status_url(new_url: str):
    url, _ = save_status(new_url=new_url)
    return url

BOT_NAME = os.getenv("BOT_NAME", "MoggerAI")
BOT_VERSION = "2.0.0 Peak Live Edition"

# Color Palette (HEX to Int)
EMBED_COLOR_MAIN = 0x00F3FF   # Cyber Neon Cyan
EMBED_COLOR_PLAY = 0x00FF87   # Neon Emerald Green
EMBED_COLOR_PAUSE = 0xFFB800  # Cyber Amber
EMBED_COLOR_ERROR = 0xFF0055  # Neon Crimson
EMBED_COLOR_DJ = 0x8A2BE2     # Electric Purple
EMBED_COLOR_EQ = 0xFF007F     # Cyber Pink

# FFmpeg DSP Filter Chains & HTTP Stream Options
FFMPEG_BEFORE_OPTIONS = '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'


AUDIO_FILTERS = {
    "normal": "",
    "bassboost_low": "equalizer=f=60:width_type=h:width=50:g=6",
    "bassboost_med": "equalizer=f=60:width_type=h:width=50:g=12",
    "bassboost_high": "equalizer=f=60:width_type=h:width=50:g=18",
    "bassboost_extreme": "equalizer=f=50:width_type=h:width=40:g=24,bass=g=15",
    "8d": "apulsator=hz=0.125:amount=1.0",
    "nightcore": "asetrate=44100*1.25,aresample=44100,atempo=1.05",
    "vaporwave": "asetrate=44100*0.8,aresample=44100,atempo=1.0",
    "reverb_room": "aecho=0.8:0.88:60:0.4",
    "reverb_hall": "aecho=0.8:0.9:1000|1800:0.3|0.25",
    "reverb_arena": "aecho=0.8:0.9:500|1000|2000:0.5|0.3|0.15",
    "karaoke": "pan=stereo|c0=c0-c1|c1=c1-c0",
    "vibrato": "vibrato=f=7.0:d=0.5",
    "tremolo": "tremolo=f=5.0:d=0.5",
    "speed_fast": "atempo=1.5",
    "speed_slow": "atempo=0.75",
    "flanger": "flanger=delay=10:depth=5:regen=70:width=71:speed=0.5",
    "phaser": "aphaser=in_gain=0.4:out_gain=0.74:delay=3.0:decay=0.4:speed=0.5",
    "lowpass": "lowpass=f=800",
    "highpass": "highpass=f=3000",
}
