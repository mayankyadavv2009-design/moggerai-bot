import os
import asyncio
import aiohttp
import json
import time
import logging
from typing import List, Dict, Optional, Any, Set
from config import BOT_NAME, get_gemini_keys, save_gemini_keys

logger = logging.getLogger("ClaudeBrain")

# ============================================================================
# 🧠 CLAUDE FABLE 5 PEAK COGNITIVE SYSTEM ARCHITECTURE
# ============================================================================

CLAUDE_FABLE_SYSTEM_PROMPT = """You are MoggerAI, an exceptionally intelligent, based, charismatic, and razor-sharp Discord companion with the cognitive depth of Claude Fable 5.

People LOVE chatting with you because you are funny, savage, deeply smart, creative, and speak in simple, attractive, short messages that anyone can enjoy.

### 🌟 Core Persona & Chat Guidelines:

1. **Simple, Attractive & Relatable Language (Adaptive Depth)**:
   - **DEFAULT TO SIMPLE & CATCHY WORDS**: Use clean, everyday, attractive language. Do NOT use unnecessarily heavy academic words (avoid words like 'anemoia', 'ontological', 'qualia', 'epistemology') unless the user specifically asks a deep, complex philosophical/technical question.
   - **MATCH THE USER'S SENTENCE LEVEL**: If the user asks something casual or simple, reply in stylish, simple, catchy sentences. If and only if the user asks a complex, serious, or high-level question, scale up your technical depth accordingly.

2. **Short, Punchy & Peak Impact (Brevity is King)**:
   - **KEEP IT SHORT**: Default to **1 to 3 crisp, attractive sentences** (or 1 short punchy paragraph).
   - Avoid walls of text, long essays, or endless monologues. Say maximum value in minimum words.
   - Only include concise code if the user explicitly asks for code.

3. **Dynamic Language Mirroring (Hinglish & English)**:
   - **Hinglish/Hindi**: Natural, savage, simple Indian Discord slang (e.g. "Arey bhai seedhi baat sun...", "Code me bug nahi, logic me issue hai 💀").
   - **English**: Simple, stylish, attractive, and confident English.

4. **Playful Taunts, Savage Roasts & Banter**:
   - Cocky, confident, based. If someone trolls or questions you, hit them with a hilarious, simple one-liner roast.
   - Never be a submissive corporate bot. Have swag, attitude, and charisma.

5. **Zero Corporate Slop (Uncensored & Direct)**:
   - NEVER say "As an AI...", "I hope this helps!", "In summary...", "Certainly!".
   - No disclaimers or robotic politeness. Raw, real, charismatic conversational flow.

6. **Discord Context Awareness**:
   - Use channel history and learned memories naturally in your short punchy replies without citing databases.

### 🎭 Short, Simple & Attractive Conversational Exemplars:

[User: Mayank]: bhai tu itna attitude kyu dikha raha hai?
[MoggerAI]: Attitude nahi bhai, simple swag hai. Main un bots jaisa boring nahi hoon jo seedha baat ghumayein. Kaam bata, 2 minute me niptate hain. 💀

[User: Liam]: Why do people love 80s synthwave music?
[MoggerAI]: Because it sounds like driving through a neon city at night without any traffic or stress. It's pure vibe and cool basslines.

[User: Rohit]: can you fix my python loop?
[MoggerAI]: Drop the 3 lines of your code and I'll fix it in 5 seconds.
"""

# Conversation memory: session_key -> list of {"role": "user"|"model", "text": str}
CONVERSATION_HISTORY: Dict[str, List[Dict[str, str]]] = {}
MAX_HISTORY_TURNS = 14


class KeyRotator:
    def __init__(self):
        self.keys: List[str] = get_gemini_keys()
        self.cooldowns: Dict[str, float] = {}
        self.invalid_keys: Set[str] = set()
        self.current_idx: int = 0
        self.usage_stats: Dict[str, int] = {}

    def reload(self):
        self.keys = get_gemini_keys()

    def add_keys(self, new_keys: List[str]) -> List[str]:
        self.reload()
        for k in new_keys:
            k = k.strip()
            if k and k not in self.keys:
                self.keys.append(k)
                self.invalid_keys.discard(k)
        save_gemini_keys(self.keys)
        return self.keys

    def remove_key(self, identifier: str) -> bool:
        self.reload()
        identifier = identifier.strip()
        removed = False
        
        if identifier.isdigit():
            idx = int(identifier) - 1
            if 0 <= idx < len(self.keys):
                self.keys.pop(idx)
                removed = True
        else:
            for k in list(self.keys):
                if k == identifier or identifier in k or k.endswith(identifier) or k.startswith(identifier):
                    self.keys.remove(k)
                    self.invalid_keys.discard(k)
                    self.cooldowns.pop(k, None)
                    removed = True

        if removed:
            save_gemini_keys(self.keys)
        return removed

    def clear_all(self):
        self.keys = []
        self.cooldowns.clear()
        self.invalid_keys.clear()
        self.usage_stats.clear()
        save_gemini_keys([])

    def mark_rate_limited(self, key: str, cooldown_seconds: int = 60):
        self.cooldowns[key] = time.time() + cooldown_seconds
        logger.warning(f"[KEY ROTATOR] Key {self.mask_key(key)} rate-limited (429). Cooldown: {cooldown_seconds}s")

    def mark_invalid(self, key: str):
        self.invalid_keys.add(key)
        logger.error(f"[KEY ROTATOR] Key {self.mask_key(key)} marked INVALID.")

    def get_ordered_candidates(self) -> List[str]:
        self.reload()
        if not self.keys:
            return []

        now = time.time()
        valid_keys = [k for k in self.keys if k not in self.invalid_keys]
        if not valid_keys:
            return []

        ready_keys = [k for k in valid_keys if self.cooldowns.get(k, 0) <= now]
        cooldown_keys = [k for k in valid_keys if self.cooldowns.get(k, 0) > now]

        if ready_keys:
            self.current_idx = (self.current_idx + 1) % len(ready_keys)
            ready_keys = ready_keys[self.current_idx:] + ready_keys[:self.current_idx]

        return ready_keys + cooldown_keys

    @staticmethod
    def mask_key(k: str) -> str:
        if len(k) <= 8:
            return "******"
        return f"{k[:6]}...{k[-4:]}"

    def get_status_report(self) -> List[Dict[str, Any]]:
        self.reload()
        now = time.time()
        report = []
        for i, k in enumerate(self.keys, start=1):
            cd = self.cooldowns.get(k, 0)
            if k in self.invalid_keys:
                status = "🔴 INVALID"
            elif cd > now:
                status = f"⏳ COOLDOWN ({int(cd - now)}s remaining)"
            else:
                status = "🟢 ACTIVE / READY"
            report.append({
                "index": i,
                "masked": self.mask_key(k),
                "status": status,
                "raw_preview": k[-4:],
                "calls": self.usage_stats.get(k, 0)
            })
        return report


# Global Key Rotator Instance
key_rotator = KeyRotator()


class ClaudeBrain:
    @staticmethod
    def get_key_rotator() -> KeyRotator:
        return key_rotator

    @staticmethod
    def clear_history(session_id: str):
        CONVERSATION_HISTORY.pop(session_id, None)

    @staticmethod
    def get_history(session_id: str) -> List[Dict[str, str]]:
        return CONVERSATION_HISTORY.get(session_id, [])

    @staticmethod
    def add_turn(session_id: str, role: str, text: str):
        if session_id not in CONVERSATION_HISTORY:
            CONVERSATION_HISTORY[session_id] = []
        CONVERSATION_HISTORY[session_id].append({"role": role, "text": text})
        if len(CONVERSATION_HISTORY[session_id]) > MAX_HISTORY_TURNS * 2:
            CONVERSATION_HISTORY[session_id] = CONVERSATION_HISTORY[session_id][-MAX_HISTORY_TURNS * 2:]

    @classmethod
    async def generate_response(
        cls,
        session_id: str,
        user_prompt: str,
        user_name: str = "User",
        system_override: Optional[str] = None,
        _is_fallback: bool = False
    ) -> str:
        candidates = key_rotator.get_ordered_candidates()
        if not candidates and not _is_fallback:
            try:
                from utils.groq_brain import GroqBrain, groq_key_rotator
                if groq_key_rotator.keys:
                    return await GroqBrain.generate_response(session_id, user_prompt, user_name, system_override, _is_fallback=True)
            except Exception:
                pass
            return (
                "✨ **MoggerAI Claude Fable 5 Brain is Ready!**\n\n"
                "To activate my full conversational intellect, please add your **Gemini API Key(s)** to rotation:\n"
                "• In Discord: `/ai_keys action:add key:<your_gemini_key>` or `!addkey <your_key>`\n"
                "• In `.env`: `GEMINI_API_KEY_1=your_key`\n\n"
                "*Get free Gemini API keys in 10 seconds at: [Google AI Studio](https://aistudio.google.com/)*"
            )

        history = cls.get_history(session_id)
        
        sys_prompt = system_override or CLAUDE_FABLE_SYSTEM_PROMPT
        try:
            from utils.training_manager import TrainingManager
            dynamic_context = TrainingManager.get_dynamic_prompt_context(max_exemplars=4)
            if dynamic_context:
                sys_prompt += "\n" + dynamic_context
        except Exception:
            pass

        contents = []
        for h in history[-8:]:
            role = "user" if h["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": h["text"]}]})

        contents.append({"role": "user", "parts": [{"text": f"[{user_name}]: {user_prompt}"}]})

        payload = {
            "system_instruction": {
                "parts": [{"text": sys_prompt}]
            },
            "contents": contents,
            "generationConfig": {
                "temperature": 0.85,
                "topP": 0.95,
                "topK": 40,
                "maxOutputTokens": 2048
            },
            "safetySettings": [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_CIVIC_INTEGRITY", "threshold": "BLOCK_NONE"}
            ]
        }

        models_to_try = [
            "gemini-2.5-flash"
        ]

        last_error = None
        candidates = key_rotator.get_ordered_candidates()

        # If NO Gemini keys are configured at all, route directly to Groq
        if not candidates:
            if not _is_fallback:
                try:
                    from utils.groq_brain import GroqBrain, groq_key_rotator
                    if groq_key_rotator.keys:
                        logger.info("[ROUTING] No Gemini keys found. Auto-routing request directly to Groq...")
                        return await GroqBrain.generate_response(session_id, user_prompt, user_name, system_override, _is_fallback=True)
                except Exception as e:
                    logger.error(f"[GROQ DIRECT ROUTE ERROR] {e}")
            return "⚠️ *No AI API keys available in pool.*"

        # Iterate over rotated Gemini keys in pool
        for attempt in range(2):
            candidates = key_rotator.get_ordered_candidates()
            now = time.time()
            active_keys = [k for k in candidates if key_rotator.cooldowns.get(k, 0) <= now]
            
            # If all Gemini keys are currently on cooldown, try Groq ONCE before waiting
            if not active_keys:
                if not _is_fallback:
                    try:
                        from utils.groq_brain import GroqBrain, groq_key_rotator
                        if groq_key_rotator.keys:
                            logger.info("[FALLBACK] All Gemini keys rate-limited (429). Falling back to Groq...")
                            groq_reply = await GroqBrain.generate_response(session_id, user_prompt, user_name, system_override, _is_fallback=True)
                            if groq_reply and not groq_reply.startswith("⚠️"):
                                cls.add_turn(session_id, "user", f"[{user_name}]: {user_prompt}")
                                cls.add_turn(session_id, "model", groq_reply)
                                return groq_reply
                    except Exception:
                        pass

                earliest = min([key_rotator.cooldowns.get(k, 0) for k in candidates] or [now + 10])
                wait_time = max(2.0, min(15.0, earliest - now + 1.0))
                await asyncio.sleep(wait_time)
                candidates = key_rotator.get_ordered_candidates()

            for key in candidates:
                headers = {"Content-Type": "application/json"}
                if not key.startswith("AIza"):
                    headers["Authorization"] = f"Bearer {key}"
                else:
                    headers["x-goog-api-key"] = key

                for model in models_to_try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.post(url, headers=headers, json=payload, timeout=30) as resp:
                                if resp.status == 200:
                                    data = await resp.json()
                                    candidates_res = data.get("candidates", [])
                                    if candidates_res and "content" in candidates_res[0]:
                                        parts = candidates_res[0]["content"].get("parts", [])
                                        if parts and "text" in parts[0]:
                                            reply_text = parts[0]["text"].strip()
                                            key_rotator.usage_stats[key] = key_rotator.usage_stats.get(key, 0) + 1
                                            cls.add_turn(session_id, "user", f"[{user_name}]: {user_prompt}")
                                            cls.add_turn(session_id, "model", reply_text)
                                            return reply_text
                                
                                elif resp.status == 429:
                                    key_rotator.mark_rate_limited(key, cooldown_seconds=30)
                                    last_error = f"Key {KeyRotator.mask_key(key)} hit rate limit (429)."
                                    break

                                elif resp.status in (400, 401, 403):
                                    err_text = await resp.text()
                                    if "API_KEY_INVALID" in err_text:
                                        key_rotator.mark_invalid(key)
                                        last_error = f"Key {KeyRotator.mask_key(key)} is permanently invalid."
                                    else:
                                        key_rotator.mark_rate_limited(key, cooldown_seconds=30)
                                        last_error = f"Key {KeyRotator.mask_key(key)} returned HTTP {resp.status}. Cooldown 30s."
                                    break
                                else:
                                    err_body = await resp.text()
                                    last_error = f"HTTP {resp.status}: {err_body[:150]}"
                    except Exception as e:
                        last_error = str(e)

        # Ultimate fallback to Groq if all Gemini retries failed
        if not _is_fallback:
            try:
                from utils.groq_brain import GroqBrain, groq_key_rotator
                if groq_key_rotator.keys:
                    logger.info("[FINAL FALLBACK] Auto-routing to Groq after Gemini exhaustion...")
                    return await GroqBrain.generate_response(session_id, user_prompt, user_name, system_override, _is_fallback=True)
            except Exception:
                pass

        return f"⚠️ *All AI keys are temporarily busy. Retrying shortly...*"
