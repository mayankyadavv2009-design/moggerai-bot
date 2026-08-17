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

GAMEDEV_LANGUAGES = [
    ("Lua (Roblox & Love2D)", "GAMEDEV_LUA", [
        "how to implement a hitscan raycast gun in Roblox Luau with bullet spread and damage dropoff in 5 lines?",
        "write a Love2D 60FPS player movement script with smooth camera lerp following in love.update(dt).",
        "how to build a finite state machine (Idle, Run, Jump, Attack) for a 2D game character in Lua?",
        "write a Roblox Luau client-server RemoteEvent weapon replication script with debounce anticheat.",
        "shortest way to implement 2D AABB tilemap collision detection and response in Love2D Lua.",
        "how to generate a procedural 2D tile dungeon using cellular automata in Lua in 6 lines?"
    ]),
    ("HTML5 & WebGL (Canvas 2D / Three.js)", "GAMEDEV_HTML", [
        "write a complete HTML5 Canvas 2D platformer player jump physics loop with gravity and ground check in 6 lines.",
        "build a Web Audio API 8-bit retro sound effect generator (laser shot, jump, coin, explosion) in vanilla JS.",
        "how to implement a 60FPS particle emitter with velocity, lifespan, and alpha fade on HTML5 canvas?",
        "write a Three.js / WebGL third-person smooth camera follow controller with spherical coordinates.",
        "how to do circular spatial hashing for 500 colliding bullets in vanilla JavaScript canvas game?",
        "write a minimal WebGL fragment shader for a dynamic 2D pixel-art water reflection effect in 6 lines."
    ]),
    ("Python (Pygame & Ursina)", "GAMEDEV_PYTHON", [
        "write a clean Pygame delta-time fixed-step game loop with smooth sub-pixel vector movement in 5 lines.",
        "how to implement an A* pathfinding algorithm on a 2D tile grid for enemy AI in Pygame?",
        "write an Ursina 3D first-person voxel block placement and destruction raycast script.",
        "how to implement a memory-efficient bullet pooling system using Pygame sprite groups?",
        "write a Pygame camera scrolling system that offsets world coordinates smoothly around the player.",
        "how to build a 2D particle explosion system in Pygame using pygame.math.Vector2 in 5 lines?"
    ]),
    ("Java (LibGDX & Minecraft Plugin)", "GAMEDEV_JAVA", [
        "write a LibGDX OrthographicCamera lerp follow script with viewport boundary clamping.",
        "implement a zero-allocation 2D Spatial Quadtree in Java for 10,000 entity collision queries.",
        "how to code a Minecraft Spigot/Paper plugin fireball spell with particle trail and raycast hit detection?",
        "write a minimal Java 2D game loop with fixed delta-time accumulator and interpolation.",
        "how to build a lightweight Entity Component System (ECS) with BitSet component masks in Java?",
        "write a LibGDX Box2D character kinematic body jump controller with ground raycast."
    ]),
    ("C & C++ (Raylib, SDL2 & OpenGL)", "GAMEDEV_CPP", [
        "write a complete 2D top-down shooter player rotation and bullet fire loop in Raylib C in 6 lines.",
        "implement an SDL2 hardware-accelerated sprite animation renderer with source rect clipping in C++.",
        "write a C++20 EnTT-style cache-friendly Entity Component System component storage pool.",
        "how to implement 2D swept AABB continuous collision detection with time-of-impact in C++?",
        "write an OpenGL 3.3 GLSL vertex and fragment shader with Phong specular lighting for 3D game models.",
        "write a Raylib 3D first-person camera controller with mouse look and collision check in C."
    ])
]

AAA_GAMEDEV_LANGUAGES = [
    ("AAA Roblox Luau Studio Architecture", "AAA_ROBLOX", [
        "how to implement a server-side lag compensation rewind buffer that restores character hitboxes to past client timestamps in Luau?",
        "write an AAA-grade Roblox Luau procedural foot Inverse Kinematics (IK) solver with terrain normal raycasting and hip adjustments.",
        "how to code an AAA client-side prediction and server reconciliation character movement system in Roblox Luau?",
        "write a Roblox Luau modular weapon framework with data-driven weapon stats, ammo pools, and state machine transitions.",
        "how to implement dynamic PBR volumetric atmosphere and day-night lighting transitions in Roblox Lighting service?"
    ]),
    ("AAA WebGPU & WebGL (Deferred PBR & Shaders)", "AAA_WEBGPU", [
        "write a modern WebGPU deferred rendering compute shader pipeline calculating Cook-Torrance GGX PBR specular and diffuse lighting in 8 lines.",
        "how to implement Cascaded Shadow Maps (CSM) with depth texture comparison in WebGL / Three.js?",
        "write a WebGL GPU instanced particle simulator handling 100,000 particles at 60FPS using transform feedback.",
        "how to build a WebAudio 3D binaural spatial HRTF sound engine with wall distance lowpass attenuation in vanilla JS?"
    ]),
    ("AAA Python (Engine Tools, BVH & Async Streaming)", "AAA_PYTHON", [
        "how to implement a multi-threaded asynchronous asset streaming and decompression pipeline with Cython memoryviews in Python?",
        "write a Dynamic AABB Tree / BVH bounding volume hierarchy for fast broadphase collision queries in Python in 6 lines.",
        "how to build an automated AAA game level build pipeline that bakes lightmaps and compresses textures using multiprocessing?",
        "write an AAA state-based behavior tree for NPC combat AI (Selector, Sequence, Leaf, Decorator) in Python."
    ]),
    ("AAA Java (Voxel Compute, Archetype ECS & Netty)", "AAA_JAVA", [
        "how to implement an archetype-based cache-friendly ECS in Java that stores components in contiguous primitive arrays?",
        "write a zero-allocation Netty bytebuf network packet serializer with delta snapshot compression for multiplayer games.",
        "implement a compute-driven voxel greedy meshing algorithm in Java that merges coplanar quad faces to minimize vertex counts.",
        "how to write a 3D PBR shader pipeline in LibGDX with environment cubemap irradiance and split-sum specular approximation?"
    ]),
    ("AAA C++ & Unreal Engine (Fibers, GAS, Vulkan)", "AAA_CPP", [
        "write a lock-free work-stealing fiber/job system task scheduler in C++20 for multi-threaded game engine subsystems in 8 lines.",
        "how to implement a custom memory arena / linear allocator for per-frame temporary game allocations in C++ without malloc overhead?",
        "write an Unreal Engine C++ Gameplay Ability System (GAS) custom GameplayAttribute set with damage calculation and replication.",
        "how to implement GPU Frustum and Occlusion Culling using compute shaders and indirect draw calls in modern C++ Vulkan/DX12?"
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

    # 25% AAA Game Engine Architecture (Roblox, WebGPU, Python, Java, C++/Unreal)
    if rand_type < 0.25:
        engine_name, pillar, templates = random.choice(AAA_GAMEDEV_LANGUAGES)
        query = random.choice(templates)
        category = f"AAA Game Studio: {engine_name}"
        prompt = f"[User: {user}]: {query}"
        return {
            "pillar": pillar,
            "category": category,
            "prompt": prompt,
            "complexity": 5
        }

    # 20% Standard Game Development (2D/3D mechanics)
    elif rand_type < 0.45:
        engine_name, pillar, templates = random.choice(GAMEDEV_LANGUAGES)
        query = random.choice(templates)
        category = f"Game Making: {engine_name}"
        prompt = f"[User: {user}]: {query}"
        return {
            "pillar": pillar,
            "category": category,
            "prompt": prompt,
            "complexity": random.choice([4, 5, 5])
        }

    # 20% General Systems & Algorithm Coding
    elif rand_type < 0.65:
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
    
    # 20% Uncensored Roasts & Discord Banter
    elif rand_type < 0.85:
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

    # 15% Music & Sound Engineering
    else:
        category, query = random.choice(MUSIC_SCENARIOS)
        prompt = f"[User: {user}]: {query}"
        return {
            "pillar": "MUSIC_THEORY",
            "category": category,
            "prompt": prompt,
            "complexity": 4
        }
