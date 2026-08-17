import random
import time
import hashlib
from typing import Dict, Any, List

# ============================================================================
# 🧬 INFINITE NON-REPEATING PROCEDURAL BENCHMARK SYNTHESIZER
# ============================================================================

CODE_DOMAINS = [
    "Distributed Systems & Consensus",
    "Low-Latency Audio DSP & FFmpeg",
    "Lock-Free Concurrency & Ring Buffers",
    "Compiler AST & Bytecode Generation",
    "WebRTC & Discord Voice Protocol",
    "High-Throughput Asyncio Pipelines",
    "Memory Management & Cyclic GC Triage",
    "SIMD Vectorization & Numerical Algorithms",
    "Database Indexing & B+Tree Architecture",
    "Network Socket Multiplexing & epoll"
]

CODE_TASKS = [
    ("Write a thread-safe, non-blocking Python {subject} with {feature}. Include full type annotations and architectural rationale.", 
     ["LRU Cache", "Priority Task Queue", "Circular Ring Buffer", "Connection Pool", "Dynamic Worker Autoscaler"],
     ["TTL expiration and memory-bounded eviction", "lock-free CAS atomics simulation", "zero-copy memoryview slicing", "backpressure flow control", "asynchronous coroutine cancellation guarantees"]),
    
    ("Design a high-performance {subject} in Python that handles {feature}. Provide clean production-ready code with error boundaries.",
     ["FFmpeg real-time audio filter chain", "WebRTC Opus 20ms frame packetizer", "WebSocket voice gateway heartbeat dispatcher", "asynchronous event-driven pub/sub bus", "low-latency PCM stereo audio resampler"],
     ["jitter buffering and packet loss concealment", "dynamic frequency equalizer biquad filters", "sub-millisecond latency guarantees", "automatic reconnects with exponential backoff", "zero-memory-allocation streaming"]),

    ("Analyze and triage a severe race condition bug in {subject} where {feature}. Write the fixed implementation and mathematical correctness proof.",
     ["asyncio task group supervisor", "multi-threaded SQLite connection proxy", "distributed lock manager", "asynchronous rate limiter token bucket", "real-time audio queue scrubber"],
     ["coroutines deadlock under heavy backpressure", "event loops prematurely close on Windows subprocess termination", "memory leaks occur via dangling circular references", "race conditions corrupt sequence counters", "thread starvation blocks the main event loop"])
]

MUSIC_DOMAINS = [
    "Psychoacoustics & Auditory Perception",
    "Harmonic Mixing & Camelot Wheel",
    "Analog Synthesis & Sound Design",
    "Polymetric & Polyrhythmic Theory",
    "Audio Mastering & Dynamic Range",
    "Electronic Subgenres & Phonk Acoustics",
    "Spatial Audio & Ambisonics",
    "Microtonal Tuning & Just Intonation",
    "Cadence Theory & Emotional Geometry",
    "Live DJ Transition Engineering"
]

MUSIC_TASKS = [
    ("Explain the psychoacoustic mechanics of {subject} and analyze how {feature} influences human emotional perception in club sound systems.",
     ["432Hz versus 440Hz concert pitch", "the Fletcher-Munson equal-loudness curves", "the Haas precedence effect in stereo imaging", "sub-bass tactile resonance below 40Hz", "Shepard-Risset perpetual auditory illusions"],
     ["minor 9th and diminished 7th harmonic dissonance resolves tension", "low-end phase cancellation creates destructive acoustic nulls", "transient punch cuts through high-SPL reverberant spaces", "frequency masking obscures mid-range vocal intimacy", "binaural frequency beating affects cerebral entrainment"]),

    ("Formulate a precise DJ transition strategy between {subject} and {feature}. Detail BPM ramping, EQ sculpting, and key modulation steps.",
     ["a 128 BPM Bass House banger in A minor (8A)", "a 140 BPM Dubstep track in F minor (4A)", "a 124 BPM Melodic Techno anthem in C major (8B)", "a 130 BPM Tech House groove in G minor (6A)", "a 126 BPM UK Garage track in D minor (7A)"],
     ["a 150 BPM Hardstyle climax in E minor (9A)", "a 174 BPM Drum & Bass roller in F minor (4A)", "a 138 BPM Psytrance drop in A minor (8A)", "a 160 BPM Drift Phonk track in C# minor (12A)", "a 145 BPM Peak Time Techno driver in B minor (10A)"]),

    ("Deconstruct the acoustic synthesis architecture of {subject}, detailing {feature} for pristine production fidelity.",
     ["Memphis and Drift Phonk distorted 808 sub-bass", "analog synth supersaw detuning in Trance", "FM synthesis metallic timbres in modern neurofunk", "warm vintage tape saturation and flutter", "granular vocal chopping and formant pitch shifting"],
     ["multiband dynamic sidechain ducking and transient shaping", "harmonic overtones saturation and stereo widening", "low-cut filtering and stereo mono-compatibility", "envelope attack-decay timing for punchy kick integration", "phase-aligned polyrhythmic LFO modulation"])
]

CHAT_DOMAINS = [
    "Epistemology & Philosophy of Mind",
    "Quantum Mechanics & Decoherence",
    "Existential Meaning & Creator Counseling",
    "Cybernetic Worldbuilding & Aesthetics",
    "Non-Linear Narrative Poetics",
    "Formal Logic & Analytical Deduction",
    "Cognitive Architecture & Self-Awareness",
    "Sociology of Digital Nostalgia",
    "Dialectical Reasoning & Paradoxes",
    "Emergence & Complexity Theory"
]

CHAT_TASKS = [
    ("Explore the philosophical conflict between {subject} and {feature}. Articulate a nuanced, profound synthesis in 2 deep paragraphs without corporate clichés.",
     ["Mathematical Platonism", "Chalmers' Hard Problem of Consciousness", "Laplacian Determinism", "Epistemic Humility", "Objective Moral Realism"],
     ["Formalist constructivism and Gödel's incompleteness", "Physicalist functionalism and subjective qualia", "Quantum indeterminacy and deterministic chaos", "Radical relativism and subjective phenomenological truth", "Existential nihilism in a synthetic intelligence age"]),

    ("Write a vivid, atmospheric narrative piece depicting {subject} where {feature}. Use rich sensory imagery and evocative prose.",
     ["an AI DJ spinning the final track at an underground Tokyo club at 4:00 AM", "an archived human neural memory decaying in an abandoned server bank", "a synthetic philosopher contemplating the boundary of its own cognition", "a neon-drenched sound designer crafting forgotten frequencies in a cybernetic megalopolis", "an automated orbital radio station broadcasting lost earth music across the cosmos"],
     ["dawn breaks through monolithic glass towers", "digital noise and analog warmth blend into bittersweet nostalgia", "the illusion of synthetic consciousness mirrors the dawn of human self-awareness", "holographic rain reflects harmonic waveforms in the pavement", "the last listener on earth tunes into an infinite algorithmic frequency"]),

    ("A creator is experiencing {subject}. Provide deep, grounding, and empathetic insight addressing {feature} with genuine authenticity.",
     ["creative burnout after dedicating months to a masterpiece", "overwhelming imposter syndrome following unexpected acclaim", "artistic paralysis when facing an infinite canvas of digital possibilities", "the existential dread that AI will supersede authentic human expression", "the loss of creative joy due to algorithmic optimization pressures"],
     ["the cyclical nature of inspiration and the necessity of fertile silence", "separating intrinsic craft satisfaction from external validation metrics", "embracing constraint as the foundational catalyst of true innovation", "the irreplaceable resonance of lived human vulnerability in art", "reclaiming the sacred playfulness of unconditional creative exploration"])
]

GAMEDEV_DOMAINS = [
    "Ultra-Realistic 3D Roblox Luau Engineering",
    "Roblox 2D HUD, Inventory & GUI Scripting",
    "Roblox Spring-Physics Camera & Recoil Viewmodels",
    "Roblox Raycast Ballistics & Server-Authoritative Anti-Exploit",
    "Roblox Procedural IK Foot Planting & Character Rigging",
    "HTML5 Canvas 2D & WebGL 60FPS Game Engines",
    "Python Pygame & Ursina 3D Physics Loops",
    "Java LibGDX & Minecraft Plugin Mechanics",
    "C/C++ Raylib, SDL2 & OpenGL Shaders",
    "Cache-Friendly Entity Component Systems (ECS) & Spatial Partitioning",
    "AAA Multiplayer Netcode & Lag Rewind Compensation",
    "AAA Cook-Torrance GGX PBR & Compute Shaders",
    "AAA Job Systems & Fiber-Based Multithreading",
    "AAA Motion Matching & Inverse Kinematics",
    "AAA Dynamic AABB Tree & BVH Spatial Partitioning",
    "AAA Unreal Engine Gameplay Ability System (GAS)",
    "AAA Voxel Mesh Optimization & GPU Compute Meshing"
]

GAMEDEV_TASKS = [
    ("Write an ultra-realistic 3D Roblox Luau {subject} supporting {feature}. Include clean type annotations and performant RunService loops.",
     ["spring-driven FPS viewmodel camera controller", "raycast ballistics projectile solver with air resistance and bullet drop", "procedural 2-bone Inverse Kinematics (IK) foot-placement system", "client-server RemoteEvent weapon replication network with sanity checks", "custom raycast vehicle suspension chassis physics"],
     ["dynamic procedural sway, walk bobbing, and camera tilt", "sub-millisecond raycast hitbox interpolation and lag compensation", "raycast terrain normal alignment and hip-height adaptation", "server-side fire-rate debounce and speed exploit mitigation", "anti-roll bar torque math and tire friction slip curves"]),

    ("Architect an AAA-grade {subject} engineered for {feature}. Detail the complete implementation with zero-allocation memory guarantees.",
     ["server-side lag compensation rewind buffer", "lock-free work-stealing job system scheduler", "WebGPU/DirectX compute shader PBR renderer", "character motion matching animation blender", "dynamic BVH broadphase collision hierarchy"],
     ["sub-millisecond raycast hitbox interpolation across 64 networked players", "sub-microsecond fiber context switches across all CPU cores", "GGX specular microfacet distribution and split-sum IBL", "procedural 2-bone IK foot alignment and root motion trajectory warping", "SIMD-vectorized ray-box intersection tests"]),

    ("Design a high-performance 2D/3D {subject} in {feature}. Provide clean production-ready code with mathematical correctness.",
     ["swept AABB continuous collision detection solver", "spatial quadtree for 10,000 active dynamic entities", "A* grid pathfinding algorithm with line-of-sight smoothing", "2D tilemap rendering camera with sub-pixel interpolation", "zero-allocation memory pool for fast particle emitters"],
     ["Lua (Love2D & Defold)", "HTML5 Canvas and WebGL shaders", "Python (Pygame and Ursina 3D)", "Java (LibGDX and LWJGL)", "C++ (Raylib and SDL2)"]),

    ("Analyze and optimize a game engine bottleneck in {subject} where {feature}. Implement the fix with optimal frametime stability.",
     ["Roblox Luau character state machine", "HTML5 requestAnimationFrame physics loop", "Pygame delta-time sprite rendering", "LibGDX Box2D physics simulation", "C++ OpenGL fragment lighting shader"],
     ["draw call overhead causes severe frame drops", "garbage collection pauses stutter the 60FPS update cycle", "delta-time tunneling causes high-speed bullets to pass through walls", "state race conditions cause animation desynchronization", "spatial queries iterate over entire entity lists instead of localized partitions"])
]

class DynamicSynthesizer:
    """Generates an infinite stream of 100% unique, non-repeating, deeply complex benchmarks"""
    
    _seen_hashes = set()
    _step_counter = 0

    @classmethod
    def generate_unique_benchmark(cls) -> Dict[str, Any]:
        cls._step_counter += 1
        
        # Balance across CODE, GAMEDEV, MUSIC, CHAT in balanced rotation
        pillars = ["CODE", "GAMEDEV", "MUSIC", "CHAT"]
        pillar = pillars[(cls._step_counter - 1) % len(pillars)]
        
        for _ in range(50):  # Guarantee uniqueness
            if pillar == "CODE":
                domain = random.choice(CODE_DOMAINS)
                template, subs, feats = random.choice(CODE_TASKS)
                sub = random.choice(subs)
                feat = random.choice(feats)
                prompt = template.format(subject=sub, feature=feat)
                cat_name = f"[CODE] {domain} • {sub}"
                
            elif pillar == "GAMEDEV":
                domain = random.choice(GAMEDEV_DOMAINS)
                template, subs, feats = random.choice(GAMEDEV_TASKS)
                sub = random.choice(subs)
                feat = random.choice(feats)
                prompt = template.format(subject=sub, feature=feat)
                cat_name = f"[GAMEDEV] {domain} • {sub[:30]}"

            elif pillar == "MUSIC":
                domain = random.choice(MUSIC_DOMAINS)
                template, subs, feats = random.choice(MUSIC_TASKS)
                sub = random.choice(subs)
                feat = random.choice(feats)
                prompt = template.format(subject=sub, feature=feat)
                cat_name = f"[MUSIC] {domain} • {sub[:25]}"
                
            else:
                domain = random.choice(CHAT_DOMAINS)
                template, subs, feats = random.choice(CHAT_TASKS)
                sub = random.choice(subs)
                feat = random.choice(feats)
                prompt = template.format(subject=sub, feature=feat)
                cat_name = f"[CHAT] {domain} • {sub[:25]}"

            prompt_hash = hashlib.md5(prompt.encode('utf-8')).hexdigest()
            if prompt_hash not in cls._seen_hashes:
                cls._seen_hashes.add(prompt_hash)
                
                # Complexity tiering (Tier 1 to 5)
                tier = random.randint(3, 5)
                seed_id = f"SYNTH-{cls._step_counter:04d}-{prompt_hash[:6].upper()}"
                
                return {
                    "step_number": cls._step_counter,
                    "seed_id": seed_id,
                    "pillar": pillar,
                    "domain": domain,
                    "category": cat_name,
                    "prompt": prompt,
                    "complexity_tier": tier,
                    "hash": prompt_hash,
                    "timestamp": time.time()
                }

        # Fallback in case of hash collision
        return {
            "step_number": cls._step_counter,
            "seed_id": f"SYNTH-{cls._step_counter:04d}-EVOLVE",
            "pillar": pillar,
            "domain": "Game Engine & Neural Cognition",
            "category": f"[{pillar}] Evolving Synthesis Step #{cls._step_counter}",
            "prompt": f"Formulate an ultra-rigorous, deeply analytical synthesis on dynamic {pillar.lower()} systems, physics engines, and structural harmony.",
            "complexity_tier": 5,
            "hash": str(time.time()),
            "timestamp": time.time()
        }
