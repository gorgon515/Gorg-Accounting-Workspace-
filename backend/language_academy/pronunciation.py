"""Pronunciation Lab — text-based pronunciation scoring (no audio).

Scores how closely an ``attempt`` matches a ``target`` phrase using four real
metrics derived from a hand-rolled Levenshtein distance plus token/character
overlap heuristics:

  * accuracy   — normalized Levenshtein similarity (char level)
  * fluency    — token-count ratio + word-ordering similarity
  * clarity    — character-set overlap
  * intonation — punctuation + length-match heuristic

All four are 0..100, plus an overall, the differing words, practice drills, and
human-readable feedback.
"""
from __future__ import annotations

from typing import Optional


def _levenshtein(a: str, b: str) -> int:
    """Classic dynamic-programming edit distance (no external deps)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        cur = [i]
        for j, cb in enumerate(b, start=1):
            ins = cur[j - 1] + 1
            dele = prev[j] + 1
            sub = prev[j - 1] + (0 if ca == cb else 1)
            cur.append(min(ins, dele, sub))
        prev = cur
    return prev[-1]


def _similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    dist = _levenshtein(a, b)
    longest = max(len(a), len(b)) or 1
    return 1.0 - dist / longest


def _norm(s: str) -> str:
    return s.strip().lower()


class PronunciationLab:
    def score(self, language: str, target: str, attempt: str) -> dict:
        t_raw, a_raw = target, attempt
        t, a = _norm(target), _norm(attempt)

        # accuracy — char-level normalized Levenshtein similarity.
        accuracy = _similarity(t, a) * 100

        # fluency — token count ratio blended with ordered token similarity.
        t_tokens = t.split()
        a_tokens = a.split()
        if not t_tokens and not a_tokens:
            count_ratio = 1.0
        else:
            count_ratio = min(len(a_tokens), len(t_tokens)) / (max(len(a_tokens), len(t_tokens)) or 1)
        matched_order = sum(1 for i, tok in enumerate(t_tokens) if i < len(a_tokens) and a_tokens[i] == tok)
        order_sim = matched_order / (len(t_tokens) or 1)
        fluency = (0.5 * count_ratio + 0.5 * order_sim) * 100

        # clarity — character-set overlap (Jaccard on chars).
        ts, as_ = set(t.replace(" ", "")), set(a.replace(" ", ""))
        if not ts and not as_:
            clarity = 100.0
        else:
            inter = len(ts & as_)
            union = len(ts | as_) or 1
            clarity = inter / union * 100

        # intonation — length match + matching terminal punctuation.
        len_ratio = min(len(t), len(a)) / (max(len(t), len(a)) or 1)
        t_punct = t_raw.strip()[-1:] if t_raw.strip() else ""
        a_punct = a_raw.strip()[-1:] if a_raw.strip() else ""
        punct_match = 1.0 if (t_punct in ".!?" and a_punct in ".!?" and t_punct == a_punct) else \
            (0.6 if (t_punct in ".!?") == (a_punct in ".!?") else 0.3)
        intonation = (0.7 * len_ratio + 0.3 * punct_match) * 100

        overall = round(0.4 * accuracy + 0.3 * fluency + 0.2 * clarity + 0.1 * intonation, 1)

        # corrections — which target words differ from the attempt.
        corrections = []
        for i, tok in enumerate(t_tokens):
            given = a_tokens[i] if i < len(a_tokens) else None
            if given != tok:
                corrections.append({"position": i, "expected": tok, "got": given,
                                    "similarity": round(_similarity(tok, given or "") * 100, 1)})

        drills = self._drills(corrections, overall)
        feedback = self._feedback(overall, corrections)

        return {
            "language": language,
            "target": t_raw,
            "attempt": a_raw,
            "accuracy": round(accuracy, 1),
            "fluency": round(fluency, 1),
            "clarity": round(clarity, 1),
            "intonation": round(intonation, 1),
            "overall": overall,
            "corrections": corrections,
            "drills": drills,
            "feedback": feedback,
        }

    def _drills(self, corrections: list[dict], overall: float) -> list[str]:
        drills = []
        for c in corrections[:3]:
            drills.append(f"Repeat the word '{c['expected']}' slowly three times, then in context.")
        if overall < 60:
            drills.append("Listen to the model phrase and shadow it sentence by sentence.")
        if not drills:
            drills.append("Great match — practice the phrase at natural speed for fluency.")
        return drills

    def _feedback(self, overall: float, corrections: list[dict]) -> str:
        if overall >= 95:
            return "Excellent — nearly perfect pronunciation."
        if overall >= 80:
            return "Very good. Minor differences in a few words."
        if overall >= 60:
            return "Good attempt. Focus on the highlighted words."
        return "Keep practicing — several words need work. Slow down and articulate."


_instance: Optional[PronunciationLab] = None


def get_pronunciation_lab() -> PronunciationLab:
    global _instance
    if _instance is None:
        _instance = PronunciationLab()
    return _instance
