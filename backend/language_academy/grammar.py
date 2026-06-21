"""Grammar Academy — CEFR-tiered rules + real mistake detection.

``check`` scans submitted text for the ``common_mistakes`` patterns defined in
``content.GRAMMAR`` (case-insensitive substring match) and returns the located
errors with their correction, an explanatory note, and a character position,
plus a 0..100 score and study suggestions.
"""
from __future__ import annotations

from typing import Optional

from . import content as C


class GrammarAcademy:
    """Stateless grammar tutor — safe to instantiate freely."""

    def _rules_for(self, language: str, level: Optional[str] = None) -> list[dict]:
        out = []
        for rule in C.GRAMMAR:
            if rule["language"] not in (language, "generic"):
                continue
            if level and rule["level"] != level:
                continue
            out.append(rule)
        return out

    def lessons(self, language: str, level: Optional[str] = None) -> list[dict]:
        """Return grammar rules filtered by language and (optionally) tier/level.

        ``level`` may be a CEFR level (A1..C2) or a tier name (beginner/
        intermediate/advanced).
        """
        if language not in C.LANGUAGE_CODES:
            raise ValueError(f"unknown language: {language}")
        levels: Optional[list[str]] = None
        if level:
            if level in C.TIERS:
                levels = C.TIERS[level]
            elif level in C.LEVELS:
                levels = [level]
            else:
                raise ValueError(f"unknown level/tier: {level}")
        out = []
        for rule in C.GRAMMAR:
            if rule["language"] not in (language, "generic"):
                continue
            if levels and rule["level"] not in levels:
                continue
            out.append({**rule, "tier": C.tier_for_level(rule["level"])})
        return out

    def get(self, rule_id: str) -> Optional[dict]:
        for rule in C.GRAMMAR:
            if rule["id"] == rule_id:
                return {**rule, "tier": C.tier_for_level(rule["level"])}
        return None

    def check(self, language: str, text: str, rule_id: Optional[str] = None) -> dict:
        """Detect known wrong forms in ``text``. Returns found errors + score."""
        if language not in C.LANGUAGE_CODES:
            raise ValueError(f"unknown language: {language}")
        lowered = text.lower()
        if rule_id:
            rule = self.get(rule_id)
            rules = [rule] if rule else []
        else:
            rules = self._rules_for(language)

        found = []
        suggestions = []
        for rule in rules:
            if not rule:
                continue
            for mistake in rule.get("common_mistakes", []):
                wrong = mistake["wrong"].lower()
                pos = lowered.find(wrong)
                if pos != -1:
                    found.append({
                        "rule_id": rule["id"],
                        "rule_title": rule["title"],
                        "wrong": mistake["wrong"],
                        "right": mistake["right"],
                        "note": mistake["note"],
                        "position": pos,
                    })
                    suggestions.append(
                        f"In '{rule['title']}': use '{mistake['right']}' instead of '{mistake['wrong']}' — {mistake['note']}")

        # Score: start at 100, deduct per detected mistake (floor 0).
        score = max(0, 100 - 20 * len(found))
        return {
            "language": language,
            "text": text,
            "found": found,
            "suggestions": suggestions,
            "score": score,
            "clean": len(found) == 0,
            "rules_checked": len([r for r in rules if r]),
        }


_instance: Optional[GrammarAcademy] = None


def get_grammar_academy() -> GrammarAcademy:
    global _instance
    if _instance is None:
        _instance = GrammarAcademy()
    return _instance
