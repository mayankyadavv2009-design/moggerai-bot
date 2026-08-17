import time
from typing import Optional

SPECTRUM_ANIMATIONS = [
    "ılıılılı",
    "lıılılıl",
    "ıılılılı",
    "lılılılı",
    "ılılılıl",
    "lıılılıı"
]

def format_duration(seconds: int) -> str:
    if not seconds or seconds <= 0:
        return "LIVE 🔴"
    mins, secs = divmod(int(seconds), 60)
    hours, mins = divmod(mins, 60)
    if hours > 0:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

def create_progress_bar(current: int, total: int, length: int = 15) -> str:
    """Builds a sleek, modern Spotify-style dot scrubber progress bar"""
    if total <= 0:
        return "`🔴 LIVE` ━━━━━━━━━━━━━● `STREAM`"
    
    current = max(0, int(current))
    total = max(1, int(total))
    progress = min(max(current / total, 0.0), 1.0)
    
    pos = int(round(length * progress))
    pos = min(max(pos, 0), length)
    
    # Clean Spotify Scrubber: ━━━━●───────────
    filled_bar = "━" * pos
    empty_bar = "─" * (length - pos)
    
    curr_str = format_duration(current)
    tot_str = format_duration(total)
    
    return f"`{curr_str}` {filled_bar}🟢{empty_bar} `{tot_str}`"

def get_animated_spectrum() -> str:
    """Returns a lightweight, non-wrapping dynamic visualizer wave"""
    frame_idx = int(time.time() * 2) % len(SPECTRUM_ANIMATIONS)
    return SPECTRUM_ANIMATIONS[frame_idx]
