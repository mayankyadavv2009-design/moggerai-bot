import os
import json
import time
import uuid
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("TrainingManager")

TRAINING_DATA_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "human_training_dataset.json")

class TrainingManager:
    """Manages Human-in-the-Loop RLHF training data, prompt injection, and fine-tuning datasets"""
    
    @classmethod
    def _ensure_file(cls):
        os.makedirs(os.path.dirname(TRAINING_DATA_FILE), exist_ok=True)
        if not os.path.exists(TRAINING_DATA_FILE):
            initial_data = {
                "version": "1.0",
                "created_at": time.time(),
                "exemplars": [
                    {
                        "id": str(uuid.uuid4()),
                        "category": "CODE",
                        "user_prompt": "Write a clean Python singleton decorator.",
                        "ideal_response": "Here is a thread-safe singleton decorator using a function closure with an `asyncio.Lock`:\n\n```python\nimport functools\nimport threading\n\ndef singleton(cls):\n    instances = {}\n    lock = threading.Lock()\n    \n    @functools.wraps(cls)\n    def get_instance(*args, **kwargs):\n        with lock:\n            if cls not in instances:\n                instances[cls] = cls(*args, **kwargs)\n        return instances[cls]\n    return get_instance\n```",
                        "rating": 5,
                        "feedback_tags": ["Clean Code", "Concise", "Thread-Safe"],
                        "timestamp": time.time()
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "category": "MUSIC",
                        "user_prompt": "Why is 8A to 8B a good DJ transition?",
                        "ideal_response": "In the Camelot wheel harmonic mixing system, 8A corresponds to A minor and 8B corresponds to C major. Because they are relative major and minor keys sharing identical key signatures (zero sharps/flats), transitioning between them maintains total melodic congruence while shifting the emotional valence from introspective/dark (A minor) to uplifting and luminous (C major).",
                        "rating": 5,
                        "feedback_tags": ["Musical Depth", "Camelot Harmonic", "Accurate Theory"],
                        "timestamp": time.time()
                    },
                    {
                        "id": str(uuid.uuid4()),
                        "category": "CHAT",
                        "user_prompt": "What is consciousness?",
                        "ideal_response": "Consciousness remains the central frontier where phenomenology meets neurobiology. Chalmers famously separated the 'easy problems'—mapping neural correlates of sensory processing—from the 'Hard Problem': why subjective qualitative experience (qualia) accompanies information processing at all. Whether emergent from integrated information or a fundamental ontological primitive, consciousness is the aperture through which reality observes itself.",
                        "rating": 5,
                        "feedback_tags": ["Philosophical Rigor", "Claude Persona", "No Clichés"],
                        "timestamp": time.time()
                    }
                ]
            }
            with open(TRAINING_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(initial_data, f, indent=2)

    @classmethod
    def load_dataset(cls) -> Dict[str, Any]:
        cls._ensure_file()
        try:
            with open(TRAINING_DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading training dataset: {e}")
            return {"exemplars": []}

    @classmethod
    def save_dataset(cls, data: Dict[str, Any]):
        cls._ensure_file()
        try:
            with open(TRAINING_DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving training dataset: {e}")

    @classmethod
    def add_exemplar(
        cls,
        user_prompt: str,
        ideal_response: str,
        category: str = "CHAT",
        rating: int = 5,
        feedback_tags: Optional[List[str]] = None,
        notes: str = ""
    ) -> Dict[str, Any]:
        data = cls.load_dataset()
        exemplar = {
            "id": str(uuid.uuid4()),
            "category": category.upper(),
            "user_prompt": user_prompt.strip(),
            "ideal_response": ideal_response.strip(),
            "rating": rating,
            "feedback_tags": feedback_tags or [],
            "notes": notes.strip(),
            "timestamp": time.time()
        }
        data["exemplars"].insert(0, exemplar)
        cls.save_dataset(data)
        return exemplar

    @classmethod
    def delete_exemplar(cls, exemplar_id: str) -> bool:
        data = cls.load_dataset()
        orig_len = len(data.get("exemplars", []))
        data["exemplars"] = [e for e in data.get("exemplars", []) if e.get("id") != exemplar_id]
        if len(data["exemplars"]) < orig_len:
            cls.save_dataset(data)
            return True
        return False

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        data = cls.load_dataset()
        exemplars = data.get("exemplars", [])
        categories = {}
        for e in exemplars:
            cat = e.get("category", "CHAT")
            categories[cat] = categories.get(cat, 0) + 1

        avg_rating = sum(e.get("rating", 5) for e in exemplars) / max(1, len(exemplars))
        
        return {
            "total_exemplars": len(exemplars),
            "categories": categories,
            "average_rating": round(avg_rating, 2),
            "last_updated": time.time()
        }

    @classmethod
    def get_dynamic_prompt_context(cls, max_exemplars: int = 6) -> str:
        """Injects human-trained exemplars into ClaudeBrain system prompt"""
        data = cls.load_dataset()
        exemplars = [e for e in data.get("exemplars", []) if e.get("rating", 0) >= 4][:max_exemplars]
        if not exemplars:
            return ""

        context_lines = [
            "\n### HUMAN TRAINED GOLD-STANDARD EXEMPLARS (ADOPT THIS EXACT STYLE & RIGOR):"
        ]
        for idx, ex in enumerate(exemplars, 1):
            context_lines.append(f"\n[EXEMPLAR {idx} - {ex.get('category', 'CHAT')}]:")
            context_lines.append(f"User: {ex.get('user_prompt')}")
            context_lines.append(f"Ideal Output:\n{ex.get('ideal_response')}")
        
        return "\n".join(context_lines)
