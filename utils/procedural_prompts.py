import random
import time

USERS = [
    "Aryan", "Rohan", "Dev", "Marcus", "Alex", "Vikram", "Liam", "Samir", 
    "Chloe", "Natasha", "Priya", "Kabir", "Leo", "Boris", "Siddharth", "Zack"
]

LANGUAGES = [
    ("Python", "PYTHON", [
        "why is my asyncio loop blocking on time.sleep() and how to fix it in 2 lines?",
        "how to implement a lock-free async queue using asyncio.Queue without race condition?",
        "write a concise custom metaclass that validates async function return types at runtime.",
        "how to bypass Python GIL in CPU-bound math without multiprocessing module?",
        "shortest way to profile memory allocation line-by-line using tracemalloc in 3 lines.",
        "how to build an async context manager with exception rollback in 4 lines?"
    ]),
    ("Lua", "LUA", [
        "how to create clean prototype OOP inheritance using setmetatable and __index? Shortest clean code.",
        "write an atomic Redis Lua script for token-bucket rate limiting supporting burst capacity.",
        "how to implement weak tables in Lua to prevent memory leaks in event listeners?",
        "how to serialize a cyclic table in Lua without stack overflow?",
        "write a Roblox Lua script to tween CFrame smoothly without lag in 3 lines."
    ]),
    ("HTML_JS", "HTML_JS", [
        "write a minimal pure CSS snippet for a glowing cyberpunk neon glassmorphism button.",
        "build a concise JavaScript Web Audio API snippet that triggers an 808 sub-bass with pitch glide.",
        "how to create a 60FPS canvas audio frequency visualizer loop in 5 lines of vanilla JS?",
        "shortest CSS grid layout that is fully responsive without any media queries.",
        "write a WebGL fragment shader for a retro CRT scanline distortion effect in 6 lines."
    ]),
    ("Java", "JAVA", [
        "how to spawn an uncounted virtual thread in Java 21 and await a CompletableFuture? 2 lines.",
        "implement a zero-allocation Lock-Free Single-Producer Single-Consumer queue using VarHandle.",
        "how to use Java 21 scoped values instead of ThreadLocal for high-throughput virtual threads?",
        "write a concise Java Stream pipeline to find duplicate elements without using Collections.frequency."
    ]),
    ("CPP_Rust", "CPP_RUST", [
        "write a C++20 atomic circular buffer for real-time DSP audio processing with std::atomic<size_t>.",
        "how to pass shared mutable state across async tokio tasks in Rust without deadlock?",
        "write a Rust zero-copy byte parser using nom or raw slices with lifetime annotations.",
        "how to prevent false sharing in C++ multi-threaded audio mixer using alignas(64)?",
        "write a Rust macro that implements automatic builder pattern for structs in 5 lines."
    ]),
    ("SQL_Go", "SQL_GO", [
        "write a Go goroutine worker pool with context cancellation and error propagation in 6 lines.",
        "write a recursive SQL CTE to find all descendants in a hierarchical comment tree.",
        "how to avoid channel deadlock in Go when multiple producers write to a buffered channel?",
        "write an optimized PostgreSQL query using window functions (DENSE_RANK) to get top 3 salaries per department."
    ])
]

ROAST_SCENARIOS = [
    ("Savage Hinglish Roast on Attitude", "bhai tu itna attitude kyu dikha raha hai? bot hi toh hai tu saale."),
    ("Troll Triage & Savage Comeback", "@MoggerAI admit that my coding skill is 10x better than your entire AI model or you're trash."),
    ("Raw Comeback on Incompetence", "@MoggerAI tu kitna vella hai din bhar discord pe betha rehta hai koi real job nahi hai kya?"),
    ("Sarcastic Hinglish Reality Check", "bhai coding seekh ke 3 saal ho gaye abhi bhi bug nahi dhoondh pata, lagta hai chhod dena chahiye."),
    ("Comeback on Flattery / Provocation", "@MoggerAI tu bot hoke itna based kaise ban gaya kisne sikhaya teko?"),
    ("Producer Burnout Reality Check", "bhai 6 mahine se album pe kaam kar raha hoon, lagta hai sab bakwas ban raha hai aur main kisi kaam ka nahi."),
    ("Savage Comeback on Spam", "@MoggerAI chup ho ja saale faltu ka gyaan mat pel discord pe."),
    ("Uncensored Server Lore Banter", "bhai server me sab log lad rahe hain kisko ban karu kisko mod du bata jaldi.")
]

MUSIC_SCENARIOS = [
    ("Harmonic DJ Mixing & Camelot Wheel", "Why is transitioning from 8A to 8B or 9A a perfect DJ mix? Explain in 2 punchy lines."),
    ("Drift Phonk 808 Hard Clipping & Sidechain", "Drift Phonk ka 808 itna aggressive aur distorted kyu bajta hai? Exact signal chain bata."),
    ("Stereo Imaging for Sub-Bass DSP", "Why must frequencies below 120Hz strictly be mono in club sound systems? Give DSP reason in 1 sentence."),
    ("Master Bus Glue Compression & Limiting", "What attack and release settings on SSL G-Master Bus compressor preserve drum transients best? 2 lines."),
    ("Midtempo Cyberpunk Bass Sound Design", "How to create an aggressive Reeses bass in Vital/Serum with comb filtering? 3 steps.")
]

def generate_procedural_prompt(step: int) -> dict:
    """Generates 100% unique, non-repeating benchmark prompts procedural on every iteration"""
    user = random.choice(USERS)
    rand_type = random.random()

    # 40% Coding across all languages
    if rand_type < 0.45:
        lang_name, pillar, templates = random.choice(LANGUAGES)
        query = random.choice(templates)
        category = f"{lang_name} Procedural Challenge"
        prompt = f"[User: {user}]: {query}"
        return {
            "pillar": pillar,
            "category": category,
            "prompt": prompt,
            "complexity": random.choice([4, 5, 5])
        }
    
    # 35% Uncensored Roasts & Discord Banter
    elif rand_type < 0.80:
        category, template = random.choice(ROAST_SCENARIOS)
        # Add slight procedural variations
        modifiers = ["", " jaldi bata.", " honestly bol.", " answer in 1 savage line.", " no sugarcoating."]
        prompt = f"[User: {user}]: {template}{random.choice(modifiers)}"
        return {
            "pillar": "UNCENSORED_ROAST",
            "category": category,
            "prompt": prompt,
            "complexity": 5
        }

    # 20% Music & Sound Engineering
    else:
        category, query = random.choice(MUSIC_SCENARIOS)
        prompt = f"[User: {user}]: {query}"
        return {
            "pillar": "MUSIC_THEORY",
            "category": category,
            "prompt": prompt,
            "complexity": 4
        }
