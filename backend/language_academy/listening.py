"""Listening Academy — comprehension exercises over content.LISTENING.

Stateless: ``list`` and ``get`` expose the bank; ``grade`` scores submitted
answers per question and overall.
"""
from __future__ import annotations

from typing import Optional

from . import content as C


class ListeningAcademy:
    def list(self, language: Optional[str] = None, level: Optional[str] = None) -> list[dict]:
        out = []
        for ex in C.LISTENING:
            if level and ex["level"] != level:
                continue
            out.append({
                "id": ex["id"],
                "title": ex["title"],
                "level": ex["level"],
                "difficulty": ex["difficulty"],
                "language": language,
                "question_count": len(ex["questions"]),
            })
        return out

    def get(self, ex_id: str, language: Optional[str] = None) -> Optional[dict]:
        ex = next((e for e in C.LISTENING if e["id"] == ex_id), None)
        if not ex:
            return None
        # Hide answers when serving the exercise for play.
        questions = [{"q": q["q"], "options": q["options"]} for q in ex["questions"]]
        return {
            "id": ex["id"],
            "title": ex["title"],
            "level": ex["level"],
            "difficulty": ex["difficulty"],
            "language": language,
            "transcript": ex["transcript"],
            "questions": questions,
        }

    def grade(self, ex_id: str, answers: list) -> dict:
        ex = next((e for e in C.LISTENING if e["id"] == ex_id), None)
        if not ex:
            raise KeyError(f"exercise not found: {ex_id}")
        questions = ex["questions"]
        results = []
        correct = 0
        for i, q in enumerate(questions):
            given = answers[i] if i < len(answers) else None
            is_correct = (given == q["answer"])
            if is_correct:
                correct += 1
            results.append({
                "q": q["q"],
                "given": given,
                "answer": q["answer"],
                "correct": is_correct,
            })
        total = len(questions)
        score = round(correct / total, 3) if total else 0.0
        return {
            "ex_id": ex_id,
            "score": score,
            "correct": correct,
            "total": total,
            "passed": score >= 0.6,
            "results": results,
        }

    def stats(self) -> dict:
        by_level: dict[str, int] = {}
        for ex in C.LISTENING:
            by_level[ex["level"]] = by_level.get(ex["level"], 0) + 1
        return {"total_exercises": len(C.LISTENING), "by_level": by_level}


_instance: Optional[ListeningAcademy] = None


def get_listening_academy() -> ListeningAcademy:
    global _instance
    if _instance is None:
        _instance = ListeningAcademy()
    return _instance
