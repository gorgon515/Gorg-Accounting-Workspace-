"""Writing coach: deterministic analysis + optional LLM enrichment.

The offline analyzer does real work against the dictionary and the
inflection index:

* unknown-word detection — a token matching no lemma and no inflected
  form is either a typo (fuzzy suggestion attached) or out-of-dictionary
* repetition — lemmas used 3+ times get flagged with alternatives from
  synonym relations where available
* register mixing — slang/informal tokens inside otherwise formal text
  (and vice versa) are pointed out
* structure stats — sentence count/length distribution for style feedback

Corrected/unknown words that DO exist in the dictionary are offered for
one-tap SRS enrollment — mistakes become flashcards.
"""
from __future__ import annotations

import difflib
import re
from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InflectionForm, Lexeme, LexemeRelation

STOP_TOKENS = {"и", "а", "но", "не", "в", "на", "с", "у", "я", "ты", "он",
               "она", "мы", "вы", "они", "это", "что", "как", "же", "бы",
               "то", "за", "к", "о", "по", "из", "или", "да", "нет"}


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[а-яёА-ЯЁ-]+", text.lower().replace("ё", "е"))


def _sentences(text: str) -> list[str]:
    parts = re.split(r"[.!?]+", text)
    return [p.strip() for p in parts if p.strip()]


def analyze_writing(db: Session, text: str) -> dict:
    tokens = _tokenize(text)
    sentences = _sentences(text)
    unique = sorted(set(tokens) - STOP_TOKENS)

    # Resolve tokens: lemma hit, inflected-form hit, or unknown.
    lemma_hits = {
        l.lemma: l
        for l in db.scalars(select(Lexeme).where(Lexeme.lemma.in_(unique)))
    }
    remaining = [t for t in unique if t not in lemma_hits]
    form_rows = db.execute(
        select(InflectionForm.form, Lexeme)
        .join(Lexeme, InflectionForm.lexeme_id == Lexeme.id)
        .where(InflectionForm.form.in_(remaining))
    ).all()
    form_hits = {form: lexeme for form, lexeme in form_rows}
    unknown = [t for t in remaining if t not in form_hits and len(t) > 2]

    # Fuzzy suggestions for unknown tokens (likely typos).
    all_lemmas = list(db.scalars(select(Lexeme.lemma)))
    unknown_words = []
    for token in unknown[:10]:
        close = difflib.get_close_matches(token, all_lemmas, n=1, cutoff=0.75)
        unknown_words.append({
            "word": token,
            "suggestion": close[0] if close else None,
        })

    # Repetition: content words used 3+ times, with synonym alternatives.
    # Inflected forms collapse to their lemma; words outside the dictionary
    # (proper nouns etc.) still count as themselves.
    resolved_lemmas = []
    for token in tokens:
        if token in STOP_TOKENS or len(token) <= 2:
            continue
        if token in lemma_hits:
            resolved_lemmas.append(token)
        elif token in form_hits:
            resolved_lemmas.append(form_hits[token].lemma)
        else:
            resolved_lemmas.append(token)
    counts = Counter(resolved_lemmas)
    repetition = []
    for lemma, count in counts.most_common():
        if count < 3:
            break
        lexeme = lemma_hits.get(lemma) or next(
            (l for l in form_hits.values() if l.lemma == lemma), None
        )
        synonyms = []
        if lexeme:
            synonyms = list(db.scalars(
                select(LexemeRelation.target_lemma).where(
                    LexemeRelation.lexeme_id == lexeme.id,
                    LexemeRelation.relation_type == "synonym",
                )
            ))
        repetition.append({"lemma": lemma, "count": count, "synonyms": synonyms})

    # Register mixing.
    used_lexemes = list(lemma_hits.values()) + list(form_hits.values())
    informal = [l.lemma for l in used_lexemes if l.register in ("informal", "slang")]
    formal = [l.lemma for l in used_lexemes if l.register in ("formal", "academic")]
    register_notes = []
    if informal and formal:
        register_notes.append(
            f"Register mix: informal ({', '.join(sorted(set(informal))[:3])}) "
            f"alongside formal ({', '.join(sorted(set(formal))[:3])}) — pick one tone."
        )

    lengths = [len(_tokenize(s)) for s in sentences]
    avg_length = round(sum(lengths) / len(lengths), 1) if lengths else 0.0
    structure_notes = []
    if lengths and avg_length < 4:
        structure_notes.append("Very short sentences — try combining some with "
                               "потому́ что, кото́рый, or и.")
    if any(length > 20 for length in lengths):
        structure_notes.append("A sentence exceeds 20 words — consider splitting it.")

    # SRS candidates: dictionary words the writer clearly reached for.
    srs_candidates = [
        {"lexeme_id": lexeme.id, "lemma": lexeme.lemma,
         "translation": lexeme.translation}
        for lexeme in {l.id: l for l in used_lexemes}.values()
    ][:10]

    known_ratio = (
        round(1 - len(unknown) / len(unique), 3) if unique else 1.0
    )
    return {
        "word_count": len(tokens),
        "sentence_count": len(sentences),
        "avg_sentence_length": avg_length,
        "unique_words": len(unique),
        "dictionary_coverage": known_ratio,
        "unknown_words": unknown_words,
        "repetition": repetition,
        "register_notes": register_notes,
        "structure_notes": structure_notes,
        "srs_candidates": srs_candidates,
    }
