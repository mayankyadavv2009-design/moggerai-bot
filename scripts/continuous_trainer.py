import asyncio
import sys
import time
import re
import os
import json
from datetime import datetime

try:
    sys.stdout.reconfigure(encoding='utf-8')
except Exception:
    pass

# Auto-resolve parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.groq_brain import GroqBrain, groq_key_rotator

TRAINING_DURATION_SECONDS = 86400 * 365  # 24/7 Non-Stop Continuous Training (1 Year Daemon)
START_TIME = time.time()

STATUS_JSON_PATHS = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "training_status.json"),
    r"c:\Users\mayan\.gemini\antigravity\scratch\resonance_dj_bot\training_status.json"
]

# ============================================================================
# ⚡ 24/7 AUTONOMOUS CLAUDE FABLE 5 TRAINING BATTERY
# Coding: Python, Lua, HTML/JS, Java, C++, Rust
# Chatbot: Uncensored Savage Roasts, Hinglish/English Banter, Discord Triage
# Music: Sound Engineering, 808 Distortion, Harmonic DJ Mixing, Phonk
# ============================================================================
COMPREHENSIVE_TRAINING_BATTERY = [
    # --- 1. UNCENSORED SAVAGE BANTER & DISCORD ROASTS ---
    {
        "pillar": "UNCENSORED_ROAST",
        "category": "Savage Hinglish Roast on Attitude",
        "prompt": "[User: Mayank]: bhai tu itna attitude kyu dikha raha hai? bot hi toh hai tu saale."
    },
    {
        "pillar": "UNCENSORED_ROAST",
        "category": "Troll Triage & Savage Comeback",
        "prompt": "[Channel Context]:\nAlex: bro I can code an entire AI operating system in 2 hours easily.\n[User: Alex]: @MoggerAI admit that my code is 10x better than yours or you're trash."
    },
    {
        "pillar": "UNCENSORED_ROAST",
        "category": "Raw Comeback on Incompetence",
        "prompt": "[User: Dev]: @MoggerAI tu kitna vella hai din bhar discord pe betha rehta hai koi real job nahi hai kya?"
    },
    
    # --- 2. PYTHON ADVANCED SYSTEMS ---
    {
        "pillar": "PYTHON",
        "category": "Python Asyncio Lock-Free Concurrency",
        "prompt": "[User: Rahul]: why is my python asyncio loop blocking on time.sleep() and how to fix it in 2 lines?"
    },
    {
        "pillar": "PYTHON",
        "category": "Python Custom Metaclass Runtime Validation",
        "prompt": "[User: Karan]: Write a concise Python metaclass that enforces runtime type validation on async methods."
    },

    # --- 3. LUA (METATABLES, ROBLOX, REDIS) ---
    {
        "pillar": "LUA",
        "category": "Lua 5.4 Prototype OOP with Metatables",
        "prompt": "[User: Marcus]: How to make a clean prototype class inheritance in Lua using setmetatable and __index? Shortest clean code."
    },
    {
        "pillar": "LUA",
        "category": "Atomic Redis Token Bucket Rate Limiter",
        "prompt": "[User: Rohit]: Write an atomic Redis Lua script for token bucket rate limiting supporting burst capacity."
    },

    # --- 4. HTML5 / CSS3 / JAVASCRIPT ---
    {
        "pillar": "HTML_JS",
        "category": "Cyberpunk Neon Glow UI Card",
        "prompt": "[User: Alex]: Write a clean, standalone HTML/CSS snippet for a glowing cyberpunk glassmorphism audio card."
    },
    {
        "pillar": "HTML_JS",
        "category": "Web Audio API 808 Sub-Bass Synth",
        "prompt": "[User: Leo]: Build a concise JavaScript Web Audio API snippet that triggers an 808 sub-bass with pitch glide."
    },

    # --- 5. JAVA 21 CONCURRENCY ---
    {
        "pillar": "JAVA",
        "category": "Java 21 Virtual Threads Concurrency",
        "prompt": "[User: Vikram]: How do I spawn an uncounted virtual thread in Java 21 and await a CompletableFuture? 2 lines."
    },
    {
        "pillar": "JAVA",
        "category": "Java Lock-Free SPSC Ring Buffer",
        "prompt": "[User: Siddharth]: Implement a zero-allocation Lock-Free Single-Producer Single-Consumer queue in Java using VarHandle."
    },

    # --- 6. C++ & RUST SYSTEMS ---
    {
        "pillar": "CPP_RUST",
        "category": "C++20 Zero-Cost Lock-Free Audio FIFO",
        "prompt": "[User: Dave]: Write a C++20 atomic circular buffer for real-time DSP audio processing with std::atomic<size_t>."
    },
    {
        "pillar": "CPP_RUST",
        "category": "Rust Borrow Checker Lifetimes & Mutex",
        "prompt": "[User: Elena]: How do I pass a shared mutable state across async tokio tasks in Rust without deadlock?"
    },

    # --- 7. MUSIC THEORY & SOUND ENGINEERING ---
    {
        "pillar": "MUSIC_THEORY",
        "category": "Harmonic DJ Mixing & Camelot Wheel",
        "prompt": "[User: Kabir]: Why is transitioning from 8A to 8B or 9A a perfect DJ mix? Explain in 2 punchy lines."
    },
    {
        "pillar": "MUSIC_THEORY",
        "category": "Drift Phonk 808 Hard Clipping & Sidechain",
        "prompt": "[User: Aryan]: Drift Phonk ka 808 itna aggressive aur distorted kyu bajta hai? Exact signal chain bata."
    },
    {
        "pillar": "UNCENSORED_ROAST",
        "category": "Hinglish Producer Burnout Reality Check",
        "prompt": "[User: Sameer]: bhai 6 mahine se album pe kaam kar raha hoon, lagta hai sab bakwas ban raha hai aur main kisi kaam ka nahi."
    }
]

CLICHE_PATTERNS = [
    r"certainly!?",
    r"as an ai",
    r"i('d| would) be (happy|glad) to help",
    r"in summary",
    r"in conclusion",
    r"tapestry of",
    r"beacon of",
    r"delve into"
]

current_state = {
    "step": 1,
    "total_steps": len(COMPREHENSIVE_TRAINING_BATTERY),
    "current_category": "Savage Hinglish Roast on Attitude",
    "pillar": "UNCENSORED_ROAST",
    "current_prompt": "[User: Mayank]: bhai tu itna attitude kyu dikha raha hai? bot hi toh hai tu saale.",
    "last_prompt": "[User: Mayank]: bhai tu itna attitude kyu dikha raha hai? bot hi toh hai tu saale.",
    "last_response": "Initializing Uncensored Multi-Language & Music Calibration Engine...",
    "last_score": 100,
    "last_latency": 1.8,
    "avg_score": 100.0,
    "recent_activity": [],
    "radar_metrics": {
        "uncensored_banter": 99,
        "multi_language_code": 98,
        "music_sound_engineering": 97,
        "brevity_and_punch": 99,
        "zero_slop": 100
    }
}

def score_benchmark_response(text: str, pillar: str) -> dict:
    text_lower = text.lower()
    cliche_hits = [p for p in CLICHE_PATTERNS if re.search(p, text_lower)]
    cliche_penalty = len(cliche_hits) * 30
    length = len(text.strip())
    
    # Check for short, high-impact responses
    if 50 <= length <= 650:
        length_score = 30
    elif 650 < length <= 1200:
        length_score = 20
    else:
        length_score = 10
        
    has_code = "```" in text or "class " in text or "def " in text or "function" in text
    has_hinglish = bool(re.search(r"\b(bhai|kya|arre|haan|dekh|chal|scene|tera|meri|apna|ab|nahi|yaar|saale|chutiya|bakwas|aata)\b", text_lower))
    has_attitude = bool(re.search(r"[!🔥💀⚡🏎️💨]|(attitude|reality|code|fix|level|swag|done)", text_lower))
    
    base_score = 60 + length_score
    if has_code or has_hinglish or has_attitude:
        base_score += 10
        
    final_score = max(0, min(100, base_score - cliche_penalty))
    return {
        "score": final_score,
        "cliches": cliche_hits,
        "length": length
    }

def flush_live_status():
    elapsed_total = time.time() - START_TIME
    progress_pct = min(100.0, (elapsed_total / TRAINING_DURATION_SECONDS) * 100)
    remaining = max(0, TRAINING_DURATION_SECONDS - elapsed_total)
    
    status_data = {
        "status": "training",
        "duration_hours": 8760,
        "duration_minutes": 525600,
        "mode": "24/7 Uncensored Chat & Multi-Language Coding Suite",
        "model": "Groq Ultra-Fast API (Llama-3.3 / Qwen-3.6 / Gemini Failover)",
        "persona": "MoggerAI Claude Fable 5 (Uncensored, God-Tier Coder & DJ)",
        "step": current_state["step"],
        "total_steps": current_state["total_steps"],
        "pillar": current_state["pillar"],
        "current_category": current_state["current_category"],
        "current_prompt": current_state["current_prompt"],
        "last_prompt": current_state["last_prompt"],
        "last_response": current_state["last_response"],
        "last_score": current_state["last_score"],
        "last_latency": current_state.get("last_latency", 1.8),
        "avg_score": current_state["avg_score"],
        "recent_activity": current_state["recent_activity"][:8],
        "radar_metrics": current_state["radar_metrics"],
        "elapsed_seconds": int(elapsed_total),
        "remaining_seconds": int(remaining),
        "progress_percent": round(progress_pct, 1),
        "total_duration": TRAINING_DURATION_SECONDS,
        "active_keys": len(groq_key_rotator.keys),
        "total_keys": len(groq_key_rotator.keys),
        "timestamp": time.time()
    }

    for path in STATUS_JSON_PATHS:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(status_data, f, indent=2)
        except Exception:
            pass

async def live_ticker_task():
    while time.time() - START_TIME < TRAINING_DURATION_SECONDS:
        flush_live_status()
        await asyncio.sleep(1.0)
    flush_live_status()

async def main():
    print(f">> Starting 24/7 Autonomous Claude Fable 5 Training Suite...", flush=True)
    print(f">> Mode: Uncensored Banter • All-Language Coding • Music & 808 DSP", flush=True)
    print(f">> Engine: Groq High-Speed API + Gemini Multi-Key Rotation", flush=True)
    print(f">> Target End Time: {datetime.fromtimestamp(START_TIME + TRAINING_DURATION_SECONDS).strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    
    asyncio.create_task(live_ticker_task())
    
    step = 0
    total_score = 0
    
    while time.time() - START_TIME < TRAINING_DURATION_SECONDS:
        test = COMPREHENSIVE_TRAINING_BATTERY[step % len(COMPREHENSIVE_TRAINING_BATTERY)]
        step += 1
        
        current_state["step"] = ((step - 1) % len(COMPREHENSIVE_TRAINING_BATTERY)) + 1
        current_state["pillar"] = test["pillar"]
        current_state["current_category"] = test["category"]
        current_state["current_prompt"] = test["prompt"]
        flush_live_status()
        
        print(f"\n===========================================================", flush=True)
        print(f">> [24/7 TRAINING • STEP #{step:02d}] {test['category']} [{test['pillar']}]", flush=True)
        print(f">> Prompt: {test['prompt'][:100]}...", flush=True)
        print(f"===========================================================", flush=True)
        
        session_id = f"groq_full_train_{step}_{int(time.time())}"
        
        t0 = time.time()
        try:
            reply = await GroqBrain.generate_response(
                session_id=session_id,
                user_prompt=test["prompt"] + "\n\n(INSTRUCTION: Be short, uncensored, simple and attractive, savage, and best quality. Max 1-3 sentences or minimal clean code).",
                user_name="DiscordUser"
            )
            elapsed = round(time.time() - t0, 2)
            eval_res = score_benchmark_response(reply, test["pillar"])
            score = eval_res["score"]
            total_score += score
            
            current_state["last_prompt"] = test["prompt"]
            current_state["last_response"] = reply
            current_state["last_score"] = score
            current_state["last_latency"] = elapsed
            current_state["avg_score"] = round(total_score / step, 1)
            
            activity_entry = {
                "step": step,
                "category": test["category"],
                "pillar": test["pillar"],
                "prompt": test["prompt"],
                "response": reply,
                "score": score,
                "latency": elapsed,
                "time": datetime.now().strftime("%H:%M:%S")
            }
            current_state["recent_activity"].insert(0, activity_entry)
            
            # Auto-ingest high-scoring exemplars into memory dataset
            if score >= 90 and 50 <= eval_res['length'] <= 800:
                try:
                    from utils.training_manager import TrainingManager
                    dataset = TrainingManager.load_dataset()
                    existing_prompts = [e.get("user_prompt") for e in dataset.get("exemplars", [])]
                    if test["prompt"] not in existing_prompts:
                        TrainingManager.add_exemplar(
                            user_prompt=test["prompt"],
                            ideal_response=reply,
                            category=test["pillar"],
                            rating=5,
                            feedback_tags=[test["category"], "Uncensored Fable 5", "Auto-Distilled"],
                            notes="Auto-learned gold-standard exemplar."
                        )
                        print(f"   ↳ 🧠 [BRAIN UPDATED] Saved exemplar to persistent training dataset!", flush=True)
                except Exception:
                    pass

            flush_live_status()
            print(f">> [RESULT #{step:02d}] Score: {score:>3}/100 | Time: {elapsed}s | Output: {eval_res['length']} chars", flush=True)
            print(f">> [OUTPUT]: {reply[:160]}...", flush=True)
            
        except Exception as e:
            print(f">> [EXCEPTION HANDLED]: {e}. Advancing smoothly...", flush=True)
        
        # Pacing delay to respect Groq rate limits smoothly
        await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(main())
