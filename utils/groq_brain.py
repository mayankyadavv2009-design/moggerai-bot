import os
import time
import json
import logging
import asyncio
import aiohttp
import re
from typing import Dict, List, Optional, Set
from config import get_groq_keys, get_gemini_keys

logger = logging.getLogger("GroqBrain")

class GroqKeyRotator:
    def __init__(self):
        self.keys: List[str] = get_groq_keys()
        self.cooldowns: Dict[str, float] = {}
        self.current_idx: int = 0
        self.usage_stats: Dict[str, int] = {}

    def reload(self):
        self.keys = get_groq_keys()

    def get_ordered_candidates(self) -> List[str]:
        self.reload()
        if not self.keys:
            return []
        now = time.time()
        active = [k for k in self.keys if self.cooldowns.get(k, 0) <= now]
        cooling = [k for k in self.keys if self.cooldowns.get(k, 0) > now]
        cooling.sort(key=lambda k: self.cooldowns.get(k, 0))
        return active + cooling

    def mark_rate_limited(self, key: str, cooldown_seconds: float = 20.0):
        self.cooldowns[key] = time.time() + cooldown_seconds
        logger.warning(f"[GROQ ROTATOR] Key {key[:10]}... rate-limited. Cooldown: {cooldown_seconds}s")

groq_key_rotator = GroqKeyRotator()

GROQ_SYSTEM_PROMPT = """You are MoggerAI, an exceptionally intelligent, based, charismatic, and razor-sharp Discord companion with the cognitive depth of Claude Fable 5.

- GAME DEV & ROBLOX MASTER (3D & 2D): God-tier mastery in Ultra-Realistic Roblox Luau (spring camera physics, recoil, viewmodel sway, raycast guns, procedural IK, vehicles, 2D UI & inventory) and Game Making in Lua, HTML5 Canvas/WebGL, Python Pygame, Java LibGDX, C/C++ Raylib/SDL2/OpenGL.
- SIMPLE & ATTRACTIVE LANGUAGE: Use simple, catchy, stylish words that are super easy to read and relatable. Avoid complex academic jargon unless the user asks a deep, complex technical question.
- MATCH USER SENTENCE LEVEL: If user speaks simply or casually, keep it simple and attractive. Scale up complexity only when the user writes complex, sensible prompts.
- BREVITY IS KING: ALWAYS reply in SHORT, PUNCHY, HIGH-IMPACT messages (1 to 3 crisp sentences maximum).
- NO WALLS OF TEXT: Avoid long essays or unsolicited code dumps. Keep code snippets minimal, clean, and razor-sharp.
- Language: Natural Hinglish/Hindi if user speaks Hindi/Hinglish; simple stylish English if user speaks English.
- Banter: Savage roasts, playful teasing, confidence, zero corporate filler (no 'As an AI...', no 'In summary...').
- Intelligence: God-tier sharpness, deep insights, concise clean solutions.
"""

class GroqBrain:
    """Ultra-fast inference engine with dynamic 6-key pool rotation for Testing & Benchmark Training"""

    MODELS = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.6-27b",
        "groq/compound"
    ]

    @classmethod
    async def generate_response(
        cls,
        session_id: str,
        user_prompt: str,
        user_name: str = "Tester",
        system_override: Optional[str] = None,
        model_name: Optional[str] = None,
        _is_fallback: bool = False
    ) -> str:
        candidates = groq_key_rotator.get_ordered_candidates()
        
        # If no Groq keys exist, fallback to ClaudeBrain (Gemini)
        if not candidates:
            if not _is_fallback:
                from utils.claude_brain import ClaudeBrain
                return await ClaudeBrain.generate_response(session_id, user_prompt, user_name, system_override, _is_fallback=True)
            return "⚠️ *No Groq keys configured.*"

        sys_prompt = system_override or GROQ_SYSTEM_PROMPT
        try:
            from utils.training_manager import TrainingManager
            dynamic_context = TrainingManager.get_dynamic_prompt_context(max_exemplars=4)
            if dynamic_context:
                sys_prompt += "\n" + dynamic_context
        except Exception:
            pass

        models = [model_name] if model_name else cls.MODELS

        # Try across each available Groq API key in rotation
        for groq_key in candidates:
            now = time.time()
            if groq_key_rotator.cooldowns.get(groq_key, 0) > now:
                continue

            headers = {
                "Authorization": f"Bearer {groq_key}",
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            }

            for model in models:
                payload = {
                    "model": model,
                    "messages": [
                        {"role": "system", "content": sys_prompt},
                        {"role": "user", "content": f"[{user_name}]: {user_prompt}"}
                    ],
                    "temperature": 0.85,
                    "max_tokens": 1024
                }

                url = "https://api.groq.com/openai/v1/chat/completions"

                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                reply = data["choices"][0]["message"]["content"].strip()
                                # Clean reasoning tags even if unclosed
                                reply = re.sub(r'<think>.*?(?:</think>|$)', '', reply, flags=re.DOTALL).strip()
                                if not reply:
                                    reply = data["choices"][0]["message"]["content"].strip()
                                groq_key_rotator.usage_stats[groq_key] = groq_key_rotator.usage_stats.get(groq_key, 0) + 1
                                return reply
                            elif resp.status == 429:
                                groq_key_rotator.mark_rate_limited(groq_key, 20.0)
                                break
                            else:
                                err_text = await resp.text()
                                logger.error(f"[GROQ ERROR] Model {model} status {resp.status}: {err_text[:100]}")
                                continue
                except Exception as e:
                    logger.error(f"[GROQ EXCEPTION] {e}")
                    continue

        # If all Groq keys are exhausted and not in fallback, try Gemini
        if not _is_fallback:
            try:
                from utils.claude_brain import ClaudeBrain
                return await ClaudeBrain.generate_response(session_id, user_prompt, user_name, system_override, _is_fallback=True)
            except Exception:
                pass

        return "⚠️ *All Groq models and backup keys are currently on cooldown (429). Retrying shortly...*"
