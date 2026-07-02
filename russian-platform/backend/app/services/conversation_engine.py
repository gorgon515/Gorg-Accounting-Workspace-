"""AI conversation partner.

With a generative LLM provider configured, the partner roleplays the
scenario persona with natural corrections and difficulty adaptation.
Without one (offline/CI), it walks the scenario's scripted dialogue tree —
real curated Russian dialogue, keyword-matched against learner replies —
so speaking practice works end-to-end with zero external dependencies.

Session memory (difficulty level, weaknesses, covered nodes) persists on
ConversationSession.memory so the partner remembers previous conversations.
"""
from __future__ import annotations

import re

from app.models import ConversationSession, Scenario
from app.services.llm import LLMProvider


def _normalize(text: str) -> str:
    return re.sub(r"[^\wё\s-]", "", text.lower().replace("ё", "е")).strip()


class ConversationEngine:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    def opening_line(self, scenario: Scenario) -> dict:
        if scenario.script:
            node = scenario.script[0]
            return {
                "text": node["partner"],
                "translation": node.get("translation"),
                "hints": node.get("hints", []),
            }
        return {"text": "Здра́вствуйте!", "translation": "Hello!", "hints": []}

    def reply(
        self,
        scenario: Scenario,
        session: ConversationSession,
        history: list[dict],
        user_text: str,
    ) -> dict:
        """Produce the partner's next turn plus gentle corrections."""
        if self.provider.is_generative:
            return self._llm_reply(scenario, session, history, user_text)
        return self._scripted_reply(scenario, session, user_text)

    # ------------------------------------------------------------- LLM path
    def _llm_reply(
        self,
        scenario: Scenario,
        session: ConversationSession,
        history: list[dict],
        user_text: str,
    ) -> dict:
        memory = session.memory or {}
        system = (
            f"{scenario.persona_prompt}\n\n"
            "Rules: reply in Russian appropriate to the learner's level "
            f"({memory.get('difficulty', scenario.cefr_level)}). Keep the "
            "conversation flowing; never lecture. If the learner makes a "
            "mistake, briefly model the correct form inside your natural "
            "reply, then continue. After your Russian reply, append a line "
            "'---' then an English translation, then a line '###' then a "
            "JSON array of corrections like "
            '[{"error": "...", "correction": "...", "explanation": "..."}] '
            "(empty array if none)."
        )
        messages = [
            {"role": ("user" if t["role"] == "user" else "assistant"), "content": t["text"]}
            for t in history
        ] + [{"role": "user", "content": user_text}]
        raw = self.provider.complete(system, messages)
        text, translation, corrections = raw, None, []
        if "---" in raw:
            text, _, rest = raw.partition("---")
            translation, _, corr_raw = rest.partition("###")
            translation = translation.strip()
            if corr_raw.strip():
                import json

                try:
                    corrections = json.loads(corr_raw.strip())
                except ValueError:
                    corrections = []
        return {
            "text": text.strip(),
            "translation": translation,
            "corrections": corrections,
            "hints": [],
        }

    # -------------------------------------------------------- scripted path
    def _scripted_reply(
        self, scenario: Scenario, session: ConversationSession, user_text: str
    ) -> dict:
        """Advance a dialogue tree. Each script node:
        {"partner": str, "translation": str, "hints": [str],
         "expects": [{"keywords": [..], "next": int, "feedback": str}]}
        Falls through to the node's first branch when nothing matches, with
        a hint, so learners are never stuck.
        """
        memory = dict(session.memory or {})
        idx = int(memory.get("node", 0))
        script = scenario.script or []
        if not script:
            return {
                "text": "Извини́те, я вас не по́нял.",
                "translation": "Sorry, I didn't understand you.",
                "corrections": [],
                "hints": [],
            }
        node = script[min(idx, len(script) - 1)]
        normalized = _normalize(user_text)

        chosen, matched = None, False
        for branch in node.get("expects", []):
            if any(_normalize(k) in normalized for k in branch.get("keywords", [])):
                chosen, matched = branch, True
                break
        if chosen is None and node.get("expects"):
            chosen = node["expects"][0]

        corrections = []
        if not matched and node.get("expects"):
            corrections.append(
                {
                    "error": user_text,
                    "correction": chosen.get("model_answer", ""),
                    "explanation": chosen.get(
                        "feedback", "Try using the suggested phrase."
                    ),
                }
            )

        next_idx = chosen["next"] if chosen else idx + 1
        if next_idx >= len(script) or next_idx < 0:
            memory["node"] = 0
            memory["completions"] = int(memory.get("completions", 0)) + 1
            session.memory = memory
            return {
                "text": "Отли́чно! Мы зако́нчили диало́г. Хоти́те повтори́ть?",
                "translation": "Excellent! We finished the dialogue. Want to repeat?",
                "corrections": corrections,
                "hints": [],
                "completed": True,
            }

        memory["node"] = next_idx
        session.memory = memory
        nxt = script[next_idx]
        return {
            "text": nxt["partner"],
            "translation": nxt.get("translation"),
            "corrections": corrections,
            "hints": nxt.get("hints", []),
        }
