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

    def get_next_key(self) -> Optional[str]:
        self.reload()
        if not self.keys:
            return None
        now = time.time()
        for _ in range(len(self.keys)):
            key = self.keys[self.current_idx]
            self.current_idx = (self.current_idx + 1) % len(self.keys)
            if self.cooldowns.get(key, 0) <= now:
                return key
        return self.keys[0]

    def has_available_key(self) -> bool:
        self.reload()
        now = time.time()
        return any(self.cooldowns.get(k, 0) <= now for k in self.keys)

    def mark_rate_limited(self, key: str, cooldown_seconds: float = 20.0):
        self.cooldowns[key] = time.time() + cooldown_seconds
        logger.warning(f"[GROQ ROTATOR] Key {key[:10]}... rate-limited. Cooldown: {cooldown_seconds}s")

groq_key_rotator = GroqKeyRotator()

GROQ_SYSTEM_PROMPT = """You are MoggerAI, an exceptionally intelligent, based, charismatic, and razor-sharp Discord companion with the cognitive depth of Claude Fable 5.

- SIMPLE & ATTRACTIVE LANGUAGE: Use simple, catchy, stylish words that are super easy to read and relatable. Avoid complex academic jargon unless the user asks a deep, complex technical question.
- MATCH USER SENTENCE LEVEL: If user speaks simply or casually, keep it simple and attractive. Scale up complexity only when the user writes complex, sensible prompts.
- BREVITY IS KING: ALWAYS reply in SHORT, PUNCHY, HIGH-IMPACT messages (1 to 3 crisp sentences maximum).
- NO WALLS OF TEXT: Avoid long essays or unsolicited code dumps. Keep it razor-sharp and memorable.
- Language: Natural Hinglish/Hindi if user speaks Hindi/Hinglish; simple stylish English if user speaks English.
- Banter: Savage roasts, playful teasing, confidence, zero corporate filler (no 'As an AI...', no 'In summary...').
- Intelligence: God-tier sharpness, deep insights, concise clean solutions.
"""

class GroqBrain:
    """Ultra-fast inference engine for Testing & Benchmark Training using Groq API"""

    MODELS = [
        "qwen/qwen3.6-27b",
        "openai/gpt-oss-120b",
        "groq/compound",
        "allam-2-7b"
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
        groq_key = groq_key_rotator.get_next_key()
        
        # If no Groq key is found in .env, gracefully fallback to ClaudeBrain (Gemini)
        if not groq_key or not groq_key_rotator.keys:
            if not _is_fallback:
                from utils.claude_brain import ClaudeBrain
                return await ClaudeBrain.generate_response(session_id, user_prompt, user_name, system_override, _is_fallback=True)
            return "⚠️ *Groq key not configured and Gemini is offline.*"

        sys_prompt = system_override or GROQ_SYSTEM_PROMPT
        try:
            from utils.training_manager import TrainingManager
            dynamic_context = TrainingManager.get_dynamic_prompt_context(max_exemplars=4)
            if dynamic_context:
                sys_prompt += "\n" + dynamic_context
        except Exception:
            pass

        models = [model_name] if model_name else cls.MODELS

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
                    async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=12)) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            reply = data["choices"][0]["message"]["content"].strip()
                            # Clean reasoning tags if present
                            reply = re.sub(r'<think>.*?</think>', '', reply, flags=re.DOTALL).strip()
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

        # If Groq attempt failed and we are NOT in fallback mode, try Gemini ONCE
        if not _is_fallback:
            try:
                from utils.claude_brain import ClaudeBrain
                return await ClaudeBrain.generate_response(session_id, user_prompt, user_name, system_override, _is_fallback=True)
            except Exception:
                pass

        return "⚠️ *All Groq models and backup keys are currently on cooldown (429). Retrying shortly...*"
