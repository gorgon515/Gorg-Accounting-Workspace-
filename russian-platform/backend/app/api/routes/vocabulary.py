import difflib

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models import Language, Lexeme, LexemeRelation, User

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])


def _lexeme_dict(lexeme: Lexeme, include_details: bool = False) -> dict:
    data = {
        "id": lexeme.id,
        "lemma": lexeme.lemma,
        "stressed": lexeme.stressed,
        "ipa": lexeme.ipa,
        "transliteration": lexeme.transliteration,
        "part_of_speech": lexeme.part_of_speech,
        "cefr_level": lexeme.cefr_level,
        "frequency_rank": lexeme.frequency_rank,
        "register": lexeme.register,
        "domain": lexeme.domain,
        "topic": lexeme.topic,
        "translation": lexeme.translation,
    }
    if include_details:
        data.update(
            difficulty=lexeme.difficulty,
            etymology=lexeme.etymology,
            literal_translation=lexeme.literal_translation,
            meanings=lexeme.meanings,
            root=lexeme.root,
            prefixes=lexeme.prefixes,
            suffixes=lexeme.suffixes,
            aspect=lexeme.aspect,
            aspect_partner=lexeme.aspect_partner,
            gender=lexeme.gender,
            animacy=lexeme.animacy,
            inflections=lexeme.inflections,
            government=lexeme.government,
            mnemonic=lexeme.mnemonic,
            usage_notes=lexeme.usage_notes,
            cultural_notes=lexeme.cultural_notes,
            common_mistakes=lexeme.common_mistakes,
            audio=lexeme.audio,
            examples=[
                {"text": e.text, "translation": e.translation, "audio_url": e.audio_url}
                for e in lexeme.examples
            ],
        )
    return data


@router.get("")
def list_vocabulary(
    q: str | None = None,
    cefr: str | None = None,
    pos: str | None = None,
    domain: str | None = None,
    topic: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    stmt = select(Lexeme)
    if q:
        pattern = f"%{q.lower()}%"
        stmt = stmt.where(
            or_(
                func.lower(Lexeme.lemma).like(pattern),
                func.lower(Lexeme.translation).like(pattern),
                func.lower(Lexeme.transliteration).like(pattern),
            )
        )
    if cefr:
        stmt = stmt.where(Lexeme.cefr_level == cefr)
    if pos:
        stmt = stmt.where(Lexeme.part_of_speech == pos)
    if domain:
        stmt = stmt.where(Lexeme.domain == domain)
    if topic:
        stmt = stmt.where(Lexeme.topic == topic)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(
        stmt.order_by(Lexeme.frequency_rank.asc().nulls_last())
        .limit(limit)
        .offset(offset)
    ).all()

    # Fuzzy fallback: exact search found nothing → suggest close matches
    # (typos, missing soft signs, wrong vowel): "кнега" → книга.
    fuzzy = []
    if q and total == 0 and not offset:
        needle = q.lower().replace("ё", "е")
        candidates = db.execute(select(Lexeme.id, Lexeme.lemma, Lexeme.translation)).all()
        scored: list[tuple[float, int]] = []
        for lex_id, lemma, translation in candidates:
            score = max(
                difflib.SequenceMatcher(a=needle, b=lemma.replace("ё", "е")).ratio(),
                difflib.SequenceMatcher(a=needle, b=translation.lower()).ratio(),
            )
            if score >= 0.72:
                scored.append((score, lex_id))
        scored.sort(reverse=True)
        if scored:
            ids = [lex_id for _, lex_id in scored[:5]]
            found = {l.id: l for l in db.scalars(select(Lexeme).where(Lexeme.id.in_(ids)))}
            fuzzy = [_lexeme_dict(found[i]) for i in ids if i in found]

    return {"total": total, "items": [_lexeme_dict(l) for l in rows], "fuzzy": fuzzy}


@router.get("/topics")
def list_topics(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Available thematic groups with counts, for dictionary filtering."""
    rows = db.execute(
        select(Lexeme.topic, func.count(Lexeme.id))
        .group_by(Lexeme.topic)
        .order_by(func.count(Lexeme.id).desc())
    ).all()
    return [{"topic": topic, "count": count} for topic, count in rows]


@router.get("/verb-pairs")
def verb_pairs(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """Aspect-pair browser: imperfective verbs with their perfective partners."""
    verbs = db.scalars(
        select(Lexeme)
        .where(Lexeme.part_of_speech == "verb", Lexeme.aspect_partner.is_not(None))
        .order_by(Lexeme.frequency_rank.asc().nulls_last())
    ).all()
    return [
        {
            "id": v.id,
            "imperfective": v.stressed if v.aspect == "imperfective" else v.aspect_partner,
            "perfective": v.aspect_partner if v.aspect == "imperfective" else v.stressed,
            "translation": v.translation,
            "cefr_level": v.cefr_level,
        }
        for v in verbs
    ]


@router.get("/language/{code}")
def language_info(
    code: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Language metadata incl. the full alphabet and pronunciation rules."""
    language = db.scalar(select(Language).where(Language.code == code))
    if language is None:
        raise HTTPException(404, "Language not found")
    return {
        "code": language.code,
        "name_english": language.name_english,
        "name_native": language.name_native,
        "script": language.script,
        **language.metadata_json,
    }


@router.get("/{lexeme_id}")
def get_lexeme(
    lexeme_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    lexeme = db.scalar(
        select(Lexeme)
        .options(selectinload(Lexeme.examples))
        .where(Lexeme.id == lexeme_id)
    )
    if lexeme is None:
        raise HTTPException(404, "Lexeme not found")
    data = _lexeme_dict(lexeme, include_details=True)
    data["relations"] = [
        {"type": r.relation_type, "target": r.target_lemma, "note": r.note}
        for r in db.scalars(
            select(LexemeRelation).where(LexemeRelation.lexeme_id == lexeme.id)
        )
    ]
    return data
