"""Expands compact curated wordlist entries into full dictionary entries.

A wordlist line is a tuple:

    (stressed_lemma, pos, translation, topic, cefr, extras?)

pos: n | v | adj | adv | num | pron | prep | conj | particle | phrase
extras (all optional): gender, animacy ("animate"), aspect ("perfective"),
aspect_partner, register, domain, root, usage_notes, cultural_notes,
etymology, mnemonic, rank, inflections (full override), decl_overrides,
conj_overrides, examples [(ru, en), ...], relations [(type, target, note)].

The factory fills in transliteration, IPA, morphology tables, and a
difficulty score, producing the same dict shape the seed runner already
consumes for the hand-curated core set.
"""
from __future__ import annotations

from app.services import morphology

POS_MAP = {
    "n": "noun", "v": "verb", "adj": "adjective", "adv": "adverb",
    "num": "numeral", "pron": "pronoun", "prep": "preposition",
    "conj": "conjunction", "particle": "particle", "phrase": "phrase",
}

CEFR_DIFFICULTY = {"A1": 1.0, "A2": 2.0, "B1": 3.0, "B2": 4.0, "C1": 5.0, "C2": 6.0}


def build_entry(compact: tuple) -> dict:
    stressed, pos, translation, topic, cefr = compact[:5]
    extras: dict = compact[5] if len(compact) > 5 else {}

    lemma = morphology.strip_stress(stressed)
    part_of_speech = POS_MAP[pos]

    gender = extras.get("gender")
    animacy = extras.get("animacy", "inanimate")
    if pos == "n" and gender is None:
        gender = morphology.infer_gender(lemma)
        if gender is None:
            raise ValueError(f"{lemma}: gender is ambiguous (-ь), specify in extras")

    inflections: dict = extras.get("inflections", {})
    if not inflections:
        if pos == "n" and gender:
            inflections = {
                "declension": morphology.decline_noun(
                    stressed, gender, animacy, extras.get("decl_overrides")
                )
            }
        elif pos == "v":
            inflections = morphology.conjugate_verb(
                stressed, extras.get("conj_overrides")
            )
        elif pos == "adj":
            inflections = {"forms": morphology.decline_adjective(stressed)}

    aspect = extras.get("aspect")
    if pos == "v" and aspect is None:
        aspect = "imperfective"

    return {
        "lemma": lemma,
        "stressed": stressed,
        "ipa": extras.get("ipa", morphology.to_ipa(stressed)),
        "transliteration": morphology.transliterate(stressed),
        "part_of_speech": part_of_speech,
        "cefr_level": cefr,
        "frequency_rank": extras.get("rank"),
        "register": extras.get("register", "neutral"),
        "domain": extras.get("domain", "general"),
        "topic": topic,
        "difficulty": extras.get("difficulty", CEFR_DIFFICULTY.get(cefr, 3.0)),
        "translation": translation,
        "literal_translation": extras.get("literal_translation"),
        "meanings": extras.get("meanings", []),
        "root": extras.get("root"),
        "prefixes": extras.get("prefixes", []),
        "suffixes": extras.get("suffixes", []),
        "aspect": aspect,
        "aspect_partner": extras.get("aspect_partner"),
        "gender": gender,
        "animacy": animacy if pos == "n" else None,
        "inflections": inflections,
        "government": extras.get("government", []),
        "mnemonic": extras.get("mnemonic"),
        "usage_notes": extras.get("usage_notes"),
        "cultural_notes": extras.get("cultural_notes"),
        "etymology": extras.get("etymology"),
        "common_mistakes": extras.get("common_mistakes", []),
        "audio": {},  # populated by the Phase 3 audio pipeline
        "examples": extras.get("examples", []),
        "relations": extras.get("relations", []),
    }


def build_all(wordlist: list[tuple]) -> list[dict]:
    entries = []
    seen: set[str] = set()
    for compact in wordlist:
        entry = build_entry(compact)
        if entry["lemma"] in seen:
            raise ValueError(f"duplicate wordlist lemma: {entry['lemma']}")
        seen.add(entry["lemma"])
        entries.append(entry)
    return entries
