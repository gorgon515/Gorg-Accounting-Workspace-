"""AI tutor: a learner-profile-aware teaching layer above the LLM provider.

The tutor differs from scenario roleplay in three ways: it knows the
learner (vocabulary size, weak grammar, frequent mistakes), it teaches in
a chosen mode (Socratic, storytelling, debate, ...), and it is explicitly
instructed to GUIDE rather than hand over answers.

Offline (no generative provider) the tutor still earns its keep: it
composes personalized practice prompts from the learner's actual weak
points — deterministic, honest, useful.
"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Card, GrammarMastery, GrammarTopic, Lexeme, ReviewLog
from app.services.cefr import estimate_cefr
from app.services.llm import LLMProvider

MODES = {
    "free": "Have a natural, friendly conversation on any topic the learner raises.",
    "socratic": "Teach by asking questions. Never state a rule outright — lead "
                "the learner to discover it through examples and counterexamples.",
    "storytelling": "Tell a short story in Russian at the learner's level, one "
                    "paragraph per turn, and ask them to predict or retell.",
    "debate": "Take a (light-hearted) opposing position on a topic and defend "
              "it in simple Russian; push the learner to argue back.",
    "grammar-help": "Answer grammar questions with minimal examples first; only "
                    "give the rule after the learner has tried to formulate it.",
    "news": "Discuss a current-events style topic in graded Russian, "
            "summarizing simply and asking the learner's opinion.",
}

PERSONALITIES = {
    "warm": "Encouraging and patient; celebrate small wins.",
    "strict": "Professional and exacting; correct every error precisely.",
    "playful": "Funny and informal; use light humor, stay ты-form.",
}


def learner_profile(db: Session, user_id: int) -> dict:
    cefr = estimate_cefr(db, user_id)
    weak_grammar = db.execute(
        select(GrammarTopic.slug, GrammarTopic.title, GrammarMastery.mastery)
        .join(GrammarMastery, GrammarMastery.topic_id == GrammarTopic.id)
        .where(GrammarMastery.user_id == user_id, GrammarMastery.mastery < 0.7)
        .order_by(GrammarMastery.mastery)
        .limit(5)
    ).all()
    weak_words = db.execute(
        select(Lexeme.lemma, Lexeme.translation)
        .join(Card, Card.lexeme_id == Lexeme.id)
        .where(Card.user_id == user_id, Card.state != "new")
        .order_by(Card.stability.asc())
        .limit(10)
    ).all()
    lapses = (
        db.scalar(
            select(func.count(ReviewLog.id)).where(
                ReviewLog.user_id == user_id, ReviewLog.rating == 1
            )
        )
        or 0
    )
    return {
        "cefr": cefr["level"],
        "known_words": cefr["known_words"],
        "weak_grammar": [
            {"slug": slug, "title": title, "mastery": round(m, 2)}
            for slug, title, m in weak_grammar
        ],
        "weak_words": [
            {"lemma": lemma, "translation": translation}
            for lemma, translation in weak_words
        ],
        "total_lapses": lapses,
    }


def tutor_system_prompt(profile: dict, mode: str, personality: str) -> str:
    weak_grammar = ", ".join(g["title"] for g in profile["weak_grammar"]) or "none known yet"
    weak_words = ", ".join(w["lemma"] for w in profile["weak_words"]) or "none known yet"
    return (
        "You are a professional Russian tutor inside a language-learning app.\n"
        f"Learner profile: CEFR {profile['cefr']}, ~{profile['known_words']} known "
        f"words. Weak grammar: {weak_grammar}. Shaky vocabulary: {weak_words}.\n"
        f"Mode: {MODES.get(mode, MODES['free'])}\n"
        f"Personality: {PERSONALITIES.get(personality, PERSONALITIES['warm'])}\n"
        "Rules:\n"
        "- Speak Russian at (or slightly above) the learner's level; add stress "
        "marks to every multisyllabic Russian word.\n"
        "- NEVER give the answer immediately. Hint, ask a guiding question, and "
        "only reveal the answer after two genuine attempts.\n"
        "- Weave the learner's weak words and weak grammar into your Russian "
        "naturally, so practice targets what needs it.\n"
        "- Correct errors by modeling the right form inside your reply, then "
        "move on — never lecture mid-conversation.\n"
        "- After your Russian reply append '---' then an English translation, "
        "then '###' then a JSON array of corrections "
        '[{"error", "correction", "explanation"}] (empty if none).'
    )


def offline_practice_plan(db: Session, user_id: int) -> dict:
    """Deterministic tutoring without an LLM: a personalized practice plan
    built from the learner's actual weaknesses."""
    profile = learner_profile(db, user_id)
    speaking_prompts = [
        f"Say a sentence using «{w['lemma']}» ({w['translation']})."
        for w in profile["weak_words"][:5]
    ]
    grammar_targets = [
        {
            "slug": g["slug"],
            "title": g["title"],
            "suggestion": f"Redo the drills for “{g['title']}” — mastery is "
                          f"{int(g['mastery'] * 100)}%.",
        }
        for g in profile["weak_grammar"]
    ]
    writing_prompt = (
        "Напиши́те 5 предложе́ний о ва́шем дне."
        if profile["cefr"] in ("A0", "A1")
        else "Напиши́те коро́ткий текст (8–10 предложе́ний) о ва́шем люби́мом ме́сте."
    )
    return {
        "profile": profile,
        "speaking_prompts": speaking_prompts,
        "grammar_targets": grammar_targets,
        "writing_prompt": writing_prompt,
    }


class TutorEngine:
    def __init__(self, provider: LLMProvider):
        self.provider = provider

    @property
    def is_generative(self) -> bool:
        return self.provider.is_generative

    def reply(
        self,
        db: Session,
        user_id: int,
        mode: str,
        personality: str,
        history: list[dict],
        user_text: str,
    ) -> dict:
        profile = learner_profile(db, user_id)
        system = tutor_system_prompt(profile, mode, personality)
        messages = [
            {"role": ("user" if t["role"] == "user" else "assistant"),
             "content": t["text"]}
            for t in history
        ] + [{"role": "user", "content": user_text}]
        raw = self.provider.complete(system, messages, max_tokens=1024)

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
        }
