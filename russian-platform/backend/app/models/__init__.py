"""ORM models.

Every content table is keyed by language_id so additional languages can be
added by seeding new rows, not by changing the schema. Russian is simply
the first language (id/code "ru").
"""
from app.models.analytics import LearningEvent, PronunciationAttempt, WritingSubmission
from app.models.content_pack import InstalledPack
from app.models.conversation import ConversationSession, ConversationTurn, Scenario
from app.models.exam import ExamResult
from app.models.gamification import Achievement, UserAchievement
from app.models.grammar import GrammarMastery, GrammarTopic
from app.models.language import Language
from app.models.lesson import Course, Lesson, LessonCompletion
from app.models.library import Bookmark, Text
from app.models.srs import Card, ReviewLog
from app.models.user import User
from app.models.vocabulary import (
    ExampleSentence,
    InflectionForm,
    Lexeme,
    LexemeRelation,
)

__all__ = [
    "Achievement",
    "Bookmark",
    "Card",
    "ConversationSession",
    "ConversationTurn",
    "Course",
    "ExamResult",
    "ExampleSentence",
    "GrammarMastery",
    "GrammarTopic",
    "InflectionForm",
    "InstalledPack",
    "Language",
    "LearningEvent",
    "Lesson",
    "LessonCompletion",
    "Lexeme",
    "LexemeRelation",
    "PronunciationAttempt",
    "ReviewLog",
    "Scenario",
    "Text",
    "User",
    "UserAchievement",
    "WritingSubmission",
]
