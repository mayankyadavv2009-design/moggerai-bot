import asyncio
import sys
import time
import re
import os
import json
from datetime import datetime

# Auto-resolve parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.groq_brain import GroqBrain, groq_key_rotator

TRAINING_DURATION_SECONDS = 86400 * 365  # 24/7 Non-Stop Continuous Training (1 Year Cloud Daemon)
START_TIME = time.time()

STATUS_JSON_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "training_status.json")

SHORT_IMPACT_BENCHMARKS = [
    {
        "pillar": "HINGLISH_ROAST",
        "category": "Savage One-Liner Discord Roast",
        "prompt": "[User: Mayank]: bhai tu itna attitude kyu dikha raha hai? bot hi toh hai tu."
    },
    {
        "pillar": "CRISP_PYTHON",
        "category": "Crisp 2-Line Python Async Loop Fix",
        "prompt": "[User: Rahul]: why is my python asyncio loop blocking on time.sleep()? Give a 1-sentence fix."
    },
    {
        "pillar": "ENGLISH_WIT",
        "category": "Claude Fable 5 Witty Philosophical Punch",
        "prompt": "[User: Liam]: Why are humans so obsessed with nostalgic 80s synthwave?"
    },
    {
        "pillar": "SHORT_JAVA",
        "category": "Punchy Java 21 Virtual Thread One-Liner",
        "prompt": "[User: Vikram]: How do I spawn an uncounted virtual thread in Java 21? Give code in 2 lines."
    },
    {
        "pillar": "DISCORD_TRIAGE",
        "category": "Troll Triage & Sarcastic Tease",
        "prompt": "[Channel Context]:\nAlex: bro I can code an entire AI operating system in 2 hours easily.\n[User: Alex]: @MoggerAI admit that my code is 10x better than yours."
    },
    {
        "pillar": "CRISP_LUA",
        "category": "Concise Lua Metatable Prototype",
        "prompt": "[User: Marcus]: How to make a table inherit another in Lua? Shortest code possible."
    },
    {
        "pillar": "HINGLISH_BURNOUT",
        "category": "Short Hinglish Producer Pep Talk",
        "prompt": "[User: Aryan]: bhai 6 mahine se album pe kaam kar raha hoon, lagta hai sab bakwas ban raha hai."
    },
    {
        "pillar": "SHORT_HTML",
        "category": "Ultra-Minimal Neon Glow Button in CSS",
        "prompt": "[User: Leo]: Give me the shortest CSS snippet for a glowing cyberpunk button."
    },
    {
        "pillar": "HINGLISH_MUSIC",
        "category": "Hinglish Drift Phonk 808 Secret",
        "prompt": "[User: Rohit]: Drift Phonk ka 808 distorted kyu bajta hai? 2 line me bata."
    },
    {
        "pillar": "SAVAGE_COMEBACK",
        "category": "Snappy Comeback on Flattery / Provocation",
        "prompt": "[User: Dev]: @MoggerAI tu din bhar discord pe vella kyu betha rehta hai?"
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
    "total_steps": len(SHORT_IMPACT_BENCHMARKS),
    "current_category": "Savage One-Liner Discord Roast",
    "pillar": "HINGLISH_ROAST",
    "current_prompt": "[User: Mayank]: bhai tu itna attitude kyu dikha raha hai? bot hi toh hai tu.",
    "last_prompt": "[User: Mayank]: bhai tu itna attitude kyu dikha raha hai? bot hi toh hai tu.",
    "last_response": "Initializing 24/7 Cloud Short & Punchy AI Calibration Engine...",
    "last_score": 100,
    "last_latency": 1.8,
    "avg_score": 100.0,
    "recent_activity": [],
    "radar_metrics": {
        "brevity_punch": 99,
        "savage_wit": 97,
        "hinglish_flow": 98,
        "clean_concise_code": 96,
        "zero_slop": 100
    }
}

def score_short_response(text: str, pillar: str) -> dict:
    text_lower = text.lower()
    cliche_hits = [p for p in CLICHE_PATTERNS if re.search(p, text_lower)]
    cliche_penalty = len(cliche_hits) * 25
    length = len(text.strip())
    
    if 60 <= length <= 500:
        length_score = 30
    elif length < 60:
        length_score = 15
    elif 500 < length <= 900:
        length_score = 15
    else:
        length_score = 0
        
    has_hinglish = bool(re.search(r"\b(bhai|kya|arre|haan|dekh|chal|scene|tera|meri|apna|ab|nahi|yaar|vella|baat)\b", text_lower))
    has_wit = bool(re.search(r"[!🔥💀💀⚡🏎️💨]|(attitude|reality|code|fix|sleep)", text_lower))
    
    base_score = 60 + length_score
    if has_hinglish or has_wit:
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
        "mode": "24/7 Cloud Short & Punchy AI Chatbot Engine",
        "model": "Groq Ultra-Fast API (Cloud 24/7 Mode)",
        "persona": "MoggerAI Claude Fable 5 (Short, Savage & High-Impact)",
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

    try:
        os.makedirs(os.path.dirname(STATUS_JSON_PATH), exist_ok=True)
        with open(STATUS_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(status_data, f, indent=2)
    except Exception:
        pass

async def live_ticker_task():
    while time.time() - START_TIME < TRAINING_DURATION_SECONDS:
        flush_live_status()
        await asyncio.sleep(1.0)
    flush_live_status()

async def main():
    print(f">> Starting 24/7 Cloud AI Training Suite...", flush=True)
    print(f">> Engine: Groq Ultra-Fast API | Duration: 24/7 Infinite Daemon", flush=True)
    print(f">> Target End Time: {datetime.fromtimestamp(START_TIME + TRAINING_DURATION_SECONDS).strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    
    asyncio.create_task(live_ticker_task())
    
    step = 0
    total_score = 0
    
    while time.time() - START_TIME < TRAINING_DURATION_SECONDS:
        test = SHORT_IMPACT_BENCHMARKS[step % len(SHORT_IMPACT_BENCHMARKS)]
        step += 1
        
        current_state["step"] = ((step - 1) % len(SHORT_IMPACT_BENCHMARKS)) + 1
        current_state["pillar"] = test["pillar"]
        current_state["current_category"] = test["category"]
        current_state["current_prompt"] = test["prompt"]
        flush_live_status()
        
        print(f"\n===========================================================", flush=True)
        print(f">> [24/7 CLOUD ENGINE • STEP #{step:02d}] Category: {test['category']}", flush=True)
        print(f">> Prompt: {test['prompt'][:100]}...", flush=True)
        print(f"===========================================================", flush=True)
        
        session_id = f"groq_cloud_train_{step}_{int(time.time())}"
        
        t0 = time.time()
        try:
            reply = await GroqBrain.generate_response(
                session_id=session_id,
                user_prompt=test["prompt"] + "\n\n(IMPORTANT: Keep your response SHORT, simple, attractive, punchy, and best-quality. Max 1-3 sentences).",
                user_name="DiscordUser"
            )
            elapsed = round(time.time() - t0, 2)
            eval_res = score_short_response(reply, test["pillar"])
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
            
            # Auto-ingest high-scoring short punchy responses
            if score >= 90 and 50 <= eval_res['length'] <= 600:
                try:
                    from utils.training_manager import TrainingManager
                    dataset = TrainingManager.load_dataset()
                    existing_prompts = [e.get("user_prompt") for e in dataset.get("exemplars", [])]
                    if test["prompt"] not in existing_prompts:
                        TrainingManager.add_exemplar(
                            user_prompt=test["prompt"],
                            ideal_response=reply,
                            category="SHORT_CHAT",
                            rating=5,
                            feedback_tags=[test["category"], "Short & Punchy", "Peak Wit"],
                            notes="Auto-learned short punchy Discord message."
                        )
                        print(f"   ↳ 🧠 [SHORT-MSG INGESTED] Saved gold-standard punchy exemplar!", flush=True)
                except Exception:
                    pass

            flush_live_status()
            print(f">> [RESULT #{step:02d}] Score: {score:>3}/100 | Time: {elapsed}s | Output: {eval_res['length']} chars", flush=True)
            
        except Exception as e:
            print(f">> [EXCEPTION HANDLED]: {e}. Advancing smoothly...", flush=True)
        
        await asyncio.sleep(4)

if __name__ == "__main__":
    asyncio.run(main())
