"""Language Academy facade — composes every subsystem behind one object.

``get_language_academy()`` returns a process-wide singleton that wires together
the curriculum, lesson engine, vocabulary system (SRS), grammar academy,
conversation simulator, listening + pronunciation labs, assessment system, and
the daily coach. The vocabulary bank is auto-expanded on first use.
"""
from __future__ import annotations

from typing import Optional

from . import content as C
from .curriculum import Curriculum
from .lessons import get_lesson_engine
from .vocabulary import get_vocabulary_system
from .grammar import get_grammar_academy
from .conversation import get_conversation_simulator
from .listening import get_listening_academy
from .pronunciation import get_pronunciation_lab
from .assessment import get_assessment_system
from .coach import get_daily_coach


class LanguageAcademy:
    def __init__(self):
        self.curriculum = Curriculum()
        self.lessons = get_lesson_engine()
        self.vocabulary = get_vocabulary_system()  # triggers vocab expansion
        self.grammar = get_grammar_academy()
        self.conversation = get_conversation_simulator()
        self.listening = get_listening_academy()
        self.pronunciation = get_pronunciation_lab()
        self.assessment = get_assessment_system()
        self.coach = get_daily_coach()

    # ── Reference ────────────────────────────────────────────────────────────
    def languages(self) -> list[dict]:
        return list(C.LANGUAGES)

    def levels(self) -> list[str]:
        return list(C.LEVELS)

    def topics(self) -> list[dict]:
        return list(C.TOPICS)

    # ── Curriculum ───────────────────────────────────────────────────────────
    def get_curriculum(self, language: str, level: Optional[str] = None):
        if level:
            return self.curriculum.level(language, level)
        return self.curriculum.for_language(language)

    # ── Lessons ──────────────────────────────────────────────────────────────
    def list_lessons(self, language=None, level=None, topic=None, limit=200):
        return self.lessons.list(language, level, topic, limit)

    def get_lesson(self, lesson_id: str):
        return self.lessons.get(lesson_id)

    def generate_lesson(self, language: str, level: str, topic: str):
        return self.lessons.generate(language, level, topic)

    # ── Vocabulary ───────────────────────────────────────────────────────────
    def list_vocabulary(self, language: str, topic=None, level=None, limit=100):
        return self.vocabulary.list(language, topic, level, limit)

    def vocabulary_topics(self, language: Optional[str] = None):
        return self.vocabulary.topics(language)

    def search_vocabulary(self, language: str, q: str):
        return self.vocabulary.search(language, q)

    def review_vocabulary(self, language: str, limit=20):
        return self.vocabulary.review(language, limit)

    def grade_vocabulary(self, card_id: str, grade: int):
        return self.vocabulary.grade(card_id, grade)

    # ── Grammar ──────────────────────────────────────────────────────────────
    def grammar_lessons(self, language: str, level=None):
        return self.grammar.lessons(language, level)

    def get_grammar_rule(self, rule_id: str):
        return self.grammar.get(rule_id)

    def check_grammar(self, language: str, text: str, rule_id=None):
        return self.grammar.check(language, text, rule_id)

    # ── Conversation ─────────────────────────────────────────────────────────
    def conversation_scenarios(self):
        return self.conversation.scenarios()

    def start_conversation(self, language: str, scenario: str, level: str = "A2"):
        return self.conversation.start(language, scenario, level)

    def respond_conversation(self, session_id: str, text: str):
        return self.conversation.respond(session_id, text)

    def conversation_history(self, session_id: str):
        return self.conversation.history(session_id)

    # ── Listening ────────────────────────────────────────────────────────────
    def list_listening(self, language=None, level=None):
        return self.listening.list(language, level)

    def get_listening(self, ex_id: str, language=None):
        return self.listening.get(ex_id, language)

    def grade_listening(self, ex_id: str, answers: list):
        return self.listening.grade(ex_id, answers)

    # ── Pronunciation ────────────────────────────────────────────────────────
    def score_pronunciation(self, language: str, target: str, attempt: str):
        return self.pronunciation.score(language, target, attempt)

    # ── Assessment ───────────────────────────────────────────────────────────
    def placement(self, language: str, answers: Optional[list] = None):
        if answers is not None:
            return self.assessment.placement_grade(language, answers)
        return self.assessment.placement(language)

    def list_tests(self, language=None, level=None, kind=None):
        return self.assessment.tests(language, level, kind)

    def get_test(self, test_id: str):
        return self.assessment.get_test(test_id)

    def submit_test(self, test_id: str, answers: list):
        return self.assessment.submit(test_id, answers)

    # ── Coach ────────────────────────────────────────────────────────────────
    def coach_today(self, language: str):
        return self.coach.today(language)

    # ── Stats ────────────────────────────────────────────────────────────────
    def stats(self) -> dict:
        return {
            "languages": len(C.LANGUAGES),
            "levels": len(C.LEVELS),
            "topics": len(C.TOPICS),
            "lessons": self.lessons.stats(),
            "vocabulary": self.vocabulary.stats(),
            "listening": self.listening.stats(),
            "conversation": self.conversation.stats(),
            "assessment": self.assessment.stats(),
            "coach": self.coach.stats(),
            "grammar_rules": len(C.GRAMMAR),
        }


_instance: Optional[LanguageAcademy] = None


def get_language_academy() -> LanguageAcademy:
    global _instance
    if _instance is None:
        _instance = LanguageAcademy()
    return _instance
