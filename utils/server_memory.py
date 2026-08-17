import sqlite3
import os
import time
import re
import json
import logging
from typing import List, Dict, Optional, Any

logger = logging.getLogger("ServerMemory")

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database", "resonance.db")

def init_memory_tables():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 1. Full Discord Messages Log (Reads and stores all channel chats)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS discord_chat_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        channel_id INTEGER,
        channel_name TEXT,
        user_id INTEGER,
        user_name TEXT,
        message_text TEXT,
        timestamp REAL DEFAULT (strftime('%s', 'now'))
    )
    """)

    # 2. Learned User Facts & Long-Term Memory
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_learned_facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        user_id INTEGER,
        user_name TEXT,
        fact_category TEXT,
        fact_summary TEXT,
        raw_context TEXT,
        updated_at REAL DEFAULT (strftime('%s', 'now')),
        UNIQUE(guild_id, user_id, fact_summary)
    )
    """)

    # 3. Server-Wide Lore & Inside Jokes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS server_lore_memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        guild_id INTEGER,
        topic TEXT,
        lore_content TEXT,
        updated_at REAL DEFAULT (strftime('%s', 'now')),
        UNIQUE(guild_id, topic)
    )
    """)

    conn.commit()
    conn.close()

init_memory_tables()


class ServerMemoryManager:
    """Manages continuous Discord message listening, memory extraction, and dynamic recall"""

    # Common memory extraction patterns
    FACT_PATTERNS = [
        (r"\b(?:i am|i'm|my name is|call me)\s+([a-zA-Z0-9_ -]{2,20})\b", "identity", "Name/Alias is {}"),
        (r"\b(?:i like|i love|i listen to|my favorite music is|my fav genre is)\s+([a-zA-Z0-9_ -]{3,35})\b", "music_taste", "Likes music/genre: {}"),
        (r"\b(?:i code in|i program in|my main language is|i use)\s+(python|javascript|typescript|java|c\+\+|rust|lua|golang|html|react|node)\b", "coding_skill", "Codes in {}"),
        (r"\b(?:i am working on|i'm building|my project is|i am producing)\s+([a-zA-Z0-9_ -]{3,45})\b", "current_project", "Working on {}"),
        (r"\b(?:i hate|i dislike|i can't stand)\s+([a-zA-Z0-9_ -]{3,35})\b", "dislikes", "Dislikes: {}")
    ]

    @classmethod
    def record_message(cls, guild_id: int, channel_id: int, channel_name: str, user_id: int, user_name: str, message_text: str):
        """Saves every incoming Discord message into persistent memory and extracts facts"""
        if not message_text or len(message_text.strip()) == 0:
            return

        clean_text = message_text.strip()

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Save raw message
            cursor.execute("""
            INSERT INTO discord_chat_memory (guild_id, channel_id, channel_name, user_id, user_name, message_text, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (guild_id, channel_id, channel_name, user_id, user_name, clean_text, time.time()))

            # Automatic Fact Extraction (Learning from User Messages)
            text_lower = clean_text.lower()
            for pattern, category, template in cls.FACT_PATTERNS:
                match = re.search(pattern, text_lower)
                if match:
                    extracted_val = match.group(1).strip()
                    fact_str = template.format(extracted_val)
                    cursor.execute("""
                    INSERT OR REPLACE INTO user_learned_facts (guild_id, user_id, user_name, fact_category, fact_summary, raw_context, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (guild_id, user_id, user_name, category, fact_str, clean_text[:120], time.time()))

            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"[MEMORY RECORD ERROR] {e}")

    @classmethod
    def get_recent_channel_context(cls, guild_id: int, channel_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieves the recent chat stream from the channel so the bot knows everything happening in the room"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
            SELECT user_name, message_text, timestamp FROM discord_chat_memory
            WHERE guild_id = ? AND channel_id = ?
            ORDER BY id DESC LIMIT ?
            """, (guild_id, channel_id, limit))
            rows = cursor.fetchall()
            conn.close()
            
            results = []
            for r in reversed(rows):
                results.append({
                    "user_name": r[0],
                    "message_text": r[1],
                    "timestamp": r[2]
                })
            return results
        except Exception as e:
            logger.error(f"[MEMORY FETCH ERROR] {e}")
            return []

    @classmethod
    def get_user_learned_facts(cls, guild_id: int, user_id: int) -> List[str]:
        """Retrieves all persistent memories/facts known about this specific user"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("""
            SELECT fact_summary FROM user_learned_facts
            WHERE guild_id = ? AND user_id = ?
            ORDER BY updated_at DESC LIMIT 8
            """, (guild_id, user_id))
            rows = cursor.fetchall()
            conn.close()
            return [r[0] for r in rows]
        except Exception as e:
            logger.error(f"[USER FACTS ERROR] {e}")
            return []

    @classmethod
    def build_neural_memory_prompt(cls, guild_id: int, channel_id: int, user_id: int, user_name: str) -> str:
        """Constructs a comprehensive memory context block for injection into Claude/Groq brain"""
        facts = cls.get_user_learned_facts(guild_id, user_id)
        recent_chats = cls.get_recent_channel_context(guild_id, channel_id, limit=8)

        memory_blocks = []

        if facts:
            facts_str = "\n".join([f"- {f}" for f in facts])
            memory_blocks.append(f"### 🧠 Persistent Long-Term Memories About {user_name}:\n{facts_str}")

        if recent_chats:
            chat_stream = "\n".join([f"{c['user_name']}: {c['message_text']}" for c in recent_chats])
            memory_blocks.append(f"### 📜 Recent Channel Stream (Room Banter & Context):\n{chat_stream}")

        if memory_blocks:
            return "\n\n".join(memory_blocks) + "\n\n(Use these memories naturally without explicitly saying 'according to my database')."
        return ""

    @classmethod
    def get_global_memory_stats(cls) -> Dict[str, Any]:
        """Returns stats on total messages learned and user facts stored for web dashboard"""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM discord_chat_memory")
            total_msgs = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM user_learned_facts")
            total_facts = cursor.fetchone()[0]
            
            cursor.execute("SELECT user_name, fact_category, fact_summary FROM user_learned_facts ORDER BY updated_at DESC LIMIT 10")
            recent_facts = [{"user": r[0], "category": r[1], "summary": r[2]} for r in cursor.fetchall()]
            conn.close()

            return {
                "total_messages_recorded": total_msgs,
                "total_facts_learned": total_facts,
                "recent_learned_facts": recent_facts
            }
        except Exception as e:
            return {"total_messages_recorded": 0, "total_facts_learned": 0, "recent_learned_facts": []}
