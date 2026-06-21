"""CEFR Curriculum — builds the six-level learning path for any language.

Pure logic over ``content.py``: maps each CEFR level to its goals, can-do
statements, target vocabulary size, grammar focus, and the topics introduced
at that level. No database is required.
"""
from __future__ import annotations

from . import content as C


# Topics introduced at each CEFR level (cumulative learning path).
_LEVEL_TOPICS = {
    "A1": ["greetings", "numbers", "family"],
    "A2": ["daily_life", "food", "travel"],
    "B1": ["business", "technology", "healthcare"],
    "B2": ["finance", "accounting"],
    "C1": ["investing"],
    "C2": [],  # mastery/consolidation — revisits all topics with nuance
}

_LEVEL_LABELS = {
    "A1": "Breakthrough (Beginner)",
    "A2": "Waystage (Elementary)",
    "B1": "Threshold (Intermediate)",
    "B2": "Vantage (Upper Intermediate)",
    "C1": "Effective Operational Proficiency (Advanced)",
    "C2": "Mastery (Proficient)",
}

_LEVEL_GOALS = {
    "A1": ["Master greetings and introductions", "Count and use basic numbers",
           "Talk about family and self", "Build a 500-word core vocabulary"],
    "A2": ["Handle daily routines and shopping", "Order food and travel simply",
           "Describe immediate surroundings", "Reach a 1,000-word vocabulary"],
    "B1": ["Discuss work and technology", "Manage health and travel situations",
           "Tell connected stories in the past", "Reach a 2,000-word vocabulary"],
    "B2": ["Handle personal finance and budgeting", "Read basic accounting documents",
           "Argue a viewpoint with fluency", "Reach a 4,000-word vocabulary"],
    "C1": ["Discuss investing and markets", "Understand implicit meaning and nuance",
           "Use language for professional purposes", "Reach an 8,000-word vocabulary"],
    "C2": ["Operate at near-native precision", "Synthesize complex sources",
           "Differentiate fine shades of meaning", "Reach a 16,000-word vocabulary"],
}


class Curriculum:
    """Generates CEFR curricula. Stateless — safe to instantiate freely."""

    def _grammar_focus(self, language: str, level: str) -> list[dict]:
        """Grammar rules relevant to a language at a CEFR tier."""
        out = []
        for rule in C.GRAMMAR:
            if rule["level"] != level:
                continue
            if rule["language"] in (language, "generic"):
                out.append({"id": rule["id"], "title": rule["title"],
                            "language": rule["language"]})
        return out

    def level(self, language: str, level: str) -> dict:
        if language not in C.LANGUAGE_CODES:
            raise ValueError(f"unknown language: {language}")
        if level not in C.LEVELS:
            raise ValueError(f"unknown level: {level}")
        topics = list(_LEVEL_TOPICS.get(level, []))
        # C2 consolidates everything.
        all_topics = topics if level != "C2" else list(C.TOPIC_IDS)
        return {
            "language": language,
            "level": level,
            "label": _LEVEL_LABELS[level],
            "goals": list(_LEVEL_GOALS[level]),
            "can_do_statements": list(C.CAN_DO[level]),
            "target_word_count": C.TARGET_WORD_COUNT[level],
            "grammar_focus": self._grammar_focus(language, level),
            "topics": [{"id": t, "name": (C.topic_meta(t) or {}).get("name", t)} for t in all_topics],
        }

    def for_language(self, language: str) -> dict:
        if language not in C.LANGUAGE_CODES:
            raise ValueError(f"unknown language: {language}")
        levels = [self.level(language, lvl) for lvl in C.LEVELS]
        return {
            "language": language,
            "name": next((l["name"] for l in C.LANGUAGES if l["code"] == language), language),
            "levels": levels,
            "total_target_words": C.TARGET_WORD_COUNT["C2"],
        }
