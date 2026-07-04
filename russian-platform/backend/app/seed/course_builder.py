"""Curriculum engine: generates the course catalog from the content DB.

Nine lesson families, all derived from real data (wordlist morphology
tables, curated examples, grammar drills, library texts, the alphabet) —
every exercise is machine-gradeable and every answer traces back to a
verified source. As content grows, the curriculum grows; no hand-editing.

Families:
  vocab        recognition lessons per topic (RU→EN + EN→RU mix)
  recall       production twins (EN→RU only, active recall)
  cases        noun declension drills from generated/curated tables
  verbs        conjugation drills (present + past)
  adjectives   agreement drills (m/f/n/pl forms)
  aspects      aspect-pair drills
  grammar      one lesson per grammar encyclopedia topic
  sentences    word-order rebuilding from curated example sentences
  listening    dictation lessons from library texts
  phonetics    transliteration drills from the alphabet
Plus review checkpoints inserted every 5 lessons inside vocab courses.
"""
from __future__ import annotations

import random
import re

from app.seed.alphabet import ALPHABET
from app.seed.grammar_advanced import C2_TOPICS, CONTENT as GRAMMAR_CONTENT
from app.seed.grammar_topics import TOPICS as GRAMMAR_TOPICS
from app.seed.library import TEXTS
from app.seed.vocabulary_core import VOCABULARY
from app.seed.wordlist import W
from app.services.morphology import strip_stress
from app.services.vocab_factory import build_all

WORDS_PER_LESSON = 9

A2_COURSE_TOPICS = [
    ("food", "Food & Drink"), ("family", "Family & People"),
    ("home", "Home & Apartment"), ("city", "City & Transport"),
    ("time", "Time & Calendar"), ("daily", "Daily Verbs"),
    ("adjectives", "Describing Things"), ("nature", "Nature & Weather"),
    ("clothing", "Clothing"), ("adverbs", "Adverbs & Connectors"),
]
B1_COURSE_TOPICS = [
    ("travel", "Travel & the World"), ("work", "Work & Study"),
    ("body", "Body & Health"), ("emotions", "Emotions & Character"),
    ("tech", "Technology & Media"), ("leisure", "Leisure & Sport"),
    ("education", "Education & Knowledge"), ("art", "Art & Music"),
    ("society", "Society & Environment"), ("communication", "Ideas & Society"),
]
A2_GRAMMAR_SEQUENCE = [
    "verb-aspect-intro", "past-tense", "dative-case", "instrumental-case",
    "adjective-declension", "future-tense", "motion-verbs-1",
    "reflexive-verbs", "imperative", "plural-declension",
]
B1_GRAMMAR_SEQUENCE = [
    "short-adjectives", "motion-verbs-2", "aspect-mastery", "comparatives",
    "numerals-declension", "time-expressions", "conditional",
    "relative-clauses", "impersonal",
]

CASE_NAMES = {
    "gen_sg": "genitive singular", "dat_sg": "dative singular",
    "acc_sg": "accusative singular", "ins_sg": "instrumental singular",
    "pre_sg": "prepositional singular", "nom_pl": "nominative plural",
}


def _entries() -> list[dict]:
    """Full lexeme dicts: expanded wordlist + curated core."""
    return build_all(W) + [dict(v) for v in VOCABULARY]


def _primary_translation(translation: str) -> str:
    first = re.split(r"[;,]", translation)[0]
    return re.sub(r"\s*\(.*?\)", "", first).strip()


def _translation_accepts(translation: str) -> list[str]:
    parts = re.split(r"[;,]", translation)
    cleaned = [re.sub(r"\s*\(.*?\)", "", p).strip() for p in parts]
    return [c for c in cleaned if c]


def _lesson(slug, title, order, objectives, blocks, new_lemmas=None,
            grammar_slugs=None, threshold=0.8) -> dict:
    return {
        "slug": slug, "title": title, "order_index": order,
        "objectives": objectives, "blocks": blocks,
        "new_lemmas": new_lemmas or [], "grammar_slugs": grammar_slugs or [],
        "mastery_threshold": threshold,
    }


def _course(slug, title, cefr, order, description, track, prereq,
            lessons, min_completion=0.6) -> dict:
    for i, lesson in enumerate(lessons, start=1):
        lesson["order_index"] = i
    return {
        "slug": slug, "title": title, "cefr_level": cefr,
        "order_index": order, "description": description, "track": track,
        "prerequisite_slug": prereq, "min_completion": min_completion,
        "lessons": lessons,
    }


# ------------------------------------------------------------ vocab family
def _vocab_lessons(course_slug: str, topics, levels, grammar_sequence) -> list[dict]:
    words_by_topic: dict[str, list[tuple]] = {}
    for w in W:
        if w[3] in {t[0] for t in topics} and w[4] in levels:
            words_by_topic.setdefault(w[3], []).append(w)

    lessons: list[dict] = []
    cursor = 0
    for topic_key, topic_title in topics:
        words = words_by_topic.get(topic_key, [])
        chunks = [words[i : i + WORDS_PER_LESSON]
                  for i in range(0, len(words), WORDS_PER_LESSON)]
        if len(chunks) > 1 and len(chunks[-1]) < 4:
            chunks[-2].extend(chunks.pop())
        for n, chunk in enumerate(chunks, start=1):
            lemmas = [strip_stress(w[0]) for w in chunk]
            grammar_slug = grammar_sequence[cursor % len(grammar_sequence)]
            cursor += 1
            blocks = [
                {"type": "vocabulary", "lemmas": lemmas, "note": ""},
                {"type": "grammar_ref", "slug": grammar_slug},
                {"type": "exercise", "questions": [
                    {"id": f"e{i}", "prompt": f"Translate to English: «{w[0]}»",
                     "answer": _primary_translation(w[2]),
                     "accept": _translation_accepts(w[2])}
                    for i, w in enumerate(chunk[:4])
                ]},
                {"type": "mastery_test", "questions": [
                    {"id": f"m{i}",
                     "prompt": f"Translate to Russian: “{_primary_translation(w[2])}” ({w[1]})",
                     "answer": strip_stress(w[0]), "accept": []}
                    for i, w in enumerate(chunk[4:9] if len(chunk) > 4 else chunk)
                ]},
            ]
            lessons.append(_lesson(
                f"{course_slug}-{topic_key}-{n:02d}",
                f"{topic_title} {n}" if n > 1 else topic_title, 0,
                [f"Learn {len(lemmas)} words: {topic_title.lower()}"],
                blocks, new_lemmas=lemmas, grammar_slugs=[grammar_slug],
            ))
    return _with_checkpoints(course_slug, lessons)


def _with_checkpoints(course_slug: str, lessons: list[dict]) -> list[dict]:
    """Insert a review checkpoint after every 5 lessons, resampling two
    mastery questions from each of the covered lessons."""
    rng = random.Random(course_slug)
    result: list[dict] = []
    window: list[dict] = []
    checkpoint = 0
    for lesson in lessons:
        result.append(lesson)
        window.append(lesson)
        if len(window) == 5:
            checkpoint += 1
            questions = []
            for covered in window:
                pool = [q for b in covered["blocks"]
                        if b["type"] == "mastery_test" for q in b["questions"]]
                for q in rng.sample(pool, min(2, len(pool))):
                    questions.append({**q, "id": f"r{len(questions)}"})
            result.append(_lesson(
                f"{course_slug}-review-{checkpoint:02d}",
                f"Checkpoint {checkpoint}: review", 0,
                ["Prove retention of the last five lessons"],
                [{"type": "mastery_test", "questions": questions}],
                threshold=0.75,
            ))
            window = []
    return result


# ----------------------------------------------------------- recall family
def _recall_lessons(course_slug: str, topics, levels) -> list[dict]:
    """Production twins: every word EN→RU from memory. Recognition and
    production are distinct skills; the SRS mirrors the same split."""
    words = [w for w in W if w[3] in {t[0] for t in topics} and w[4] in levels]
    chunks = [words[i : i + WORDS_PER_LESSON]
              for i in range(0, len(words), WORDS_PER_LESSON)]
    if len(chunks) > 1 and len(chunks[-1]) < 4:
        chunks[-2].extend(chunks.pop())
    lessons = []
    for n, chunk in enumerate(chunks, start=1):
        lessons.append(_lesson(
            f"{course_slug}-{n:02d}", f"Active recall {n}", 0,
            [f"Produce {len(chunk)} words from English cues"],
            [{"type": "mastery_test", "questions": [
                {"id": f"m{i}",
                 "prompt": f"Say it in Russian: “{_primary_translation(w[2])}” ({w[1]})",
                 "answer": strip_stress(w[0]), "accept": []}
                for i, w in enumerate(chunk)
            ]}],
            threshold=0.75,
        ))
    return lessons


# ------------------------------------------------------------ cases family
def _case_lessons() -> list[dict]:
    nouns = [e for e in _entries()
             if e["part_of_speech"] == "noun"
             and len(e.get("inflections", {}).get("declension", {})) >= 5]
    lessons = []
    rng = random.Random("cases")
    chunk_size = 8
    for n, start in enumerate(range(0, len(nouns), chunk_size), start=1):
        chunk = nouns[start : start + chunk_size]
        if len(chunk) < 4:
            break
        questions = []
        for i, entry in enumerate(chunk):
            declension = entry["inflections"]["declension"]
            forms = [(k, v) for k, v in declension.items() if k in CASE_NAMES]
            case_key, form = forms[rng.randrange(len(forms))]
            questions.append({
                "id": f"c{i}",
                "prompt": f"Put «{entry['stressed']}» into the {CASE_NAMES[case_key]}:",
                "answer": strip_stress(form), "accept": [],
            })
        lessons.append(_lesson(
            f"cases-{n:02d}", f"Case drill {n}", 0,
            ["Decline nouns across the six cases from memory"],
            [{"type": "grammar_ref", "slug": "cases-overview"},
             {"type": "mastery_test", "questions": questions}],
            grammar_slugs=["cases-overview"], threshold=0.75,
        ))
    return lessons


# ------------------------------------------------------------ verbs family
def _verb_lessons() -> list[dict]:
    verbs = [e for e in _entries()
             if e["part_of_speech"] == "verb"
             and e.get("inflections", {}).get("present")]
    persons = ["я", "ты", "он", "мы", "вы", "они"]
    lessons = []
    for n, start in enumerate(range(0, len(verbs), 6), start=1):
        chunk = verbs[start : start + 6]
        if len(chunk) < 3:
            break
        questions = []
        for i, entry in enumerate(chunk):
            present = entry["inflections"]["present"]
            person = persons[i % len(persons)]
            if person not in present:
                person = next(iter(present))
            questions.append({
                "id": f"v{i}",
                "prompt": f"{person} ({entry['stressed']}) → {person} …",
                "answer": strip_stress(present[person]), "accept": [],
            })
            past = entry.get("inflections", {}).get("past", {})
            if "f" in past and i < 2:
                questions.append({
                    "id": f"p{i}",
                    "prompt": f"Она вчера … ({entry['stressed']}, past f)",
                    "answer": strip_stress(past["f"]), "accept": [],
                })
        lessons.append(_lesson(
            f"verbs-{n:02d}", f"Conjugation drill {n}", 0,
            ["Conjugate verbs in present and past"],
            [{"type": "grammar_ref", "slug": "present-tense"},
             {"type": "mastery_test", "questions": questions}],
            grammar_slugs=["present-tense"], threshold=0.75,
        ))
    return lessons


# -------------------------------------------------------- adjectives family
def _adjective_lessons() -> list[dict]:
    adjectives = [e for e in _entries()
                  if e["part_of_speech"] == "adjective"
                  and e.get("inflections", {}).get("forms")]
    labels = {"f": "feminine", "n": "neuter", "pl": "plural"}
    lessons = []
    rng = random.Random("adjectives")
    for n, start in enumerate(range(0, len(adjectives), 8), start=1):
        chunk = adjectives[start : start + 8]
        if len(chunk) < 4:
            break
        questions = []
        for i, entry in enumerate(chunk):
            forms = entry["inflections"]["forms"]
            options = [k for k in ("f", "n", "pl") if k in forms]
            key = options[rng.randrange(len(options))]
            questions.append({
                "id": f"a{i}",
                "prompt": f"{labels[key].capitalize()} form of «{entry['stressed']}»:",
                "answer": strip_stress(forms[key]), "accept": [],
            })
        lessons.append(_lesson(
            f"adjectives-{n:02d}", f"Agreement drill {n}", 0,
            ["Agree adjectives with gender and number"],
            [{"type": "grammar_ref", "slug": "adjective-declension"},
             {"type": "mastery_test", "questions": questions}],
            grammar_slugs=["adjective-declension"], threshold=0.75,
        ))
    return lessons


# ----------------------------------------------------------- aspects family
def _aspect_lessons() -> list[dict]:
    pairs = [e for e in _entries()
             if e["part_of_speech"] == "verb" and e.get("aspect_partner")
             and e.get("aspect") == "imperfective"]
    lessons = []
    for n, start in enumerate(range(0, len(pairs), 8), start=1):
        chunk = pairs[start : start + 8]
        if len(chunk) < 4:
            break
        questions = [{
            "id": f"asp{i}",
            "prompt": f"Perfective partner of «{entry['stressed']}» ({_primary_translation(entry['translation'])}):",
            "answer": strip_stress(entry["aspect_partner"]), "accept": [],
        } for i, entry in enumerate(chunk)]
        lessons.append(_lesson(
            f"aspects-{n:02d}", f"Aspect pairs {n}", 0,
            ["Match imperfective verbs to their perfective partners"],
            [{"type": "grammar_ref", "slug": "verb-aspect-intro"},
             {"type": "mastery_test", "questions": questions}],
            grammar_slugs=["verb-aspect-intro"], threshold=0.75,
        ))
    return lessons


# ----------------------------------------------------------- grammar family
def _grammar_lessons() -> list[dict]:
    merged = []
    for t in GRAMMAR_TOPICS:
        if t["slug"] in GRAMMAR_CONTENT and not t["content"]:
            t = {**t, **GRAMMAR_CONTENT[t["slug"]]}
        merged.append(t)
    merged += C2_TOPICS

    lessons = []
    for topic in merged:
        if not topic["drills"]:
            continue
        questions = [{"id": d["id"], "prompt": d["prompt"],
                      "answer": d["answer"], "accept": d.get("accept", [])}
                     for d in topic["drills"]]
        lessons.append(_lesson(
            f"grammar-{topic['slug']}", topic["title"], 0,
            [f"Master: {topic['summary']}"],
            [{"type": "grammar_ref", "slug": topic["slug"]},
             {"type": "mastery_test", "questions": questions}],
            grammar_slugs=[topic["slug"]], threshold=0.75,
        ))
    return lessons


# --------------------------------------------------------- sentences family
def _sentence_lessons() -> list[dict]:
    """Word-order rebuilding from curated example sentences and library
    texts. The learner sees shuffled words + the translation and must
    reconstruct the sentence."""
    rng = random.Random("sentences")
    pool: list[tuple[str, str]] = []
    for v in VOCABULARY:
        for ru, en in v.get("examples", []):
            words = strip_stress(ru).replace("—", "").split()
            if 3 <= len(words) <= 9:
                pool.append((ru, en))
    for text in TEXTS:
        for sent in text["sentences"]:
            words = strip_stress(sent["ru"]).replace("—", "").split()
            if 3 <= len(words) <= 9:
                pool.append((sent["ru"], sent["en"]))

    seen: set[str] = set()
    unique = []
    for ru, en in pool:
        key = strip_stress(ru).lower()
        if key not in seen:
            seen.add(key)
            unique.append((ru, en))

    lessons = []
    for n, start in enumerate(range(0, len(unique), 6), start=1):
        chunk = unique[start : start + 6]
        if len(chunk) < 3:
            break
        questions = []
        for i, (ru, en) in enumerate(chunk):
            plain = strip_stress(ru).strip()
            answer = re.sub(r"[«»\"]", "", plain).rstrip(".!?").strip()
            words = answer.replace(",", "").split()
            shuffled = words[:]
            rng.shuffle(shuffled)
            if shuffled == words and len(words) > 1:
                shuffled[0], shuffled[-1] = shuffled[-1], shuffled[0]
            questions.append({
                "id": f"s{i}",
                "prompt": f"Rebuild the sentence: [{' / '.join(shuffled)}] — “{en}”",
                "answer": answer.replace(",", ""),
                "accept": [answer],
            })
        lessons.append(_lesson(
            f"sentences-{n:02d}", f"Sentence workshop {n}", 0,
            ["Reconstruct natural Russian word order"],
            [{"type": "grammar_ref", "slug": "word-order"},
             {"type": "mastery_test", "questions": questions}],
            grammar_slugs=["word-order"], threshold=0.7,
        ))
    return lessons


# ------------------------------------------------------- translation family
def _translation_lessons() -> list[dict]:
    """Full-sentence production: EN → RU from the same curated pool the
    sentence workshop uses. Rebuilding order and producing from scratch
    are different skills."""
    pool: list[tuple[str, str]] = []
    for v in VOCABULARY:
        for ru, en in v.get("examples", []):
            words = strip_stress(ru).split()
            if 3 <= len(words) <= 8:
                pool.append((ru, en))
    for text in TEXTS:
        for sent in text["sentences"]:
            words = strip_stress(sent["ru"]).split()
            if 3 <= len(words) <= 8:
                pool.append((sent["ru"], sent["en"]))
    seen: set[str] = set()
    unique = []
    for ru, en in pool:
        key = strip_stress(ru).lower()
        if key not in seen:
            seen.add(key)
            unique.append((ru, en))

    lessons = []
    for n, start in enumerate(range(0, len(unique), 5), start=1):
        chunk = unique[start : start + 5]
        if len(chunk) < 3:
            break
        questions = []
        for i, (ru, en) in enumerate(chunk):
            answer = re.sub(r"[«»\"—]", "", strip_stress(ru)).rstrip(".!?").strip()
            questions.append({
                "id": f"t{i}",
                "prompt": f"Translate to Russian: “{en.strip('— ')}”",
                "answer": answer,
                "accept": [answer.replace(",", "")],
            })
        lessons.append(_lesson(
            f"translation-{n:02d}", f"Translation workshop {n}", 0,
            ["Produce full Russian sentences from English"],
            [{"type": "mastery_test", "questions": questions}],
            threshold=0.6,
        ))
    return lessons


# ----------------------------------------------------------- stress family
def _stress_lessons() -> list[dict]:
    """Stress placement drills: the single hardest mechanical skill in
    Russian. Answers come from the stress marks in the dictionary."""
    from app.services.morphology import STRESS, stress_index, VOWELS

    candidates = []
    for e in _entries():
        plain = strip_stress(e["stressed"])
        syllables = sum(1 for ch in plain.lower() if ch in VOWELS)
        if syllables >= 2 and STRESS in e["stressed"]:
            vowel_positions = [i for i, ch in enumerate(plain.lower())
                               if ch in VOWELS]
            stressed_syllable = vowel_positions.index(stress_index(e["stressed"])) + 1
            candidates.append((plain, e["translation"], stressed_syllable, syllables))

    lessons = []
    for n, start in enumerate(range(0, len(candidates), 10), start=1):
        chunk = candidates[start : start + 10]
        if len(chunk) < 5 or n > 20:  # cap the course at 20 lessons
            break
        questions = [{
            "id": f"st{i}",
            "prompt": f"Which syllable is stressed in «{plain}» "
                      f"({_primary_translation(translation)})? (1–{total})",
            "answer": str(syllable),
            "accept": [],
        } for i, (plain, translation, syllable, total) in enumerate(chunk)]
        lessons.append(_lesson(
            f"stress-{n:02d}", f"Stress drill {n}", 0,
            ["Place the stress correctly from memory"],
            [{"type": "grammar_ref", "slug": "stress-and-reduction"},
             {"type": "mastery_test", "questions": questions}],
            grammar_slugs=["stress-and-reduction"], threshold=0.7,
        ))
    return lessons


# --------------------------------------------------------- listening family
def _listening_lessons() -> list[dict]:
    lessons = []
    for n, text in enumerate(TEXTS, start=1):
        sentences = [s for s in text["sentences"]
                     if len(strip_stress(s["ru"]).split()) <= 12][:6]
        if len(sentences) < 3:
            continue
        questions = [{
            "id": f"d{i}",
            "prompt": f"Listen and type what you hear ({i + 1}/{len(sentences)}):",
            "speak": strip_stress(s["ru"]),
            "answer": re.sub(r"[«»\"—]", "", strip_stress(s["ru"])).rstrip(".!?").strip(),
            "accept": [],
        } for i, s in enumerate(sentences)]
        lessons.append(_lesson(
            f"listening-{text['slug']}", f"Dictation: {text['title']}", 0,
            [f"Transcribe {len(sentences)} sentences by ear"],
            [{"type": "mastery_test", "questions": questions}],
            threshold=0.7,
        ))
    return lessons


# --------------------------------------------------------- phonetics family
def _phonetics_lessons() -> list[dict]:
    from app.services.morphology import transliterate

    lessons = []
    letters = [l for l in ALPHABET if l["type"] != "sign"]
    for n, start in enumerate(range(0, len(letters), 6), start=1):
        chunk = letters[start : start + 6]
        if len(chunk) < 3:
            break
        questions = [{
            "id": f"ph{i}",
            "prompt": f"Transliterate the word «{letter['example']['word']}» "
                      f"({letter['example']['translation']}):",
            "answer": transliterate(letter["example"]["word"]).replace("'", ""),
            "accept": [transliterate(letter["example"]["word"])],
        } for i, letter in enumerate(chunk)]
        lessons.append(_lesson(
            f"phonetics-{n:02d}", f"Reading Cyrillic {n}", 0,
            ["Sound out Cyrillic words letter by letter"],
            [{"type": "grammar_ref", "slug": "cyrillic-alphabet"},
             {"type": "mastery_test", "questions": questions}],
            grammar_slugs=["cyrillic-alphabet"], threshold=0.7,
        ))
    return lessons


def build_generated_courses() -> list[dict]:
    return [
        _course("a2-everyday", "Everyday Life", "A2", 3,
                "Themed vocabulary sprints through daily life with review "
                "checkpoints.", "core", "a1-survival",
                _vocab_lessons("a2-everyday", A2_COURSE_TOPICS, {"A1", "A2"},
                               A2_GRAMMAR_SEQUENCE)),
        _course("b1-wider-world", "The Wider World", "B1", 4,
                "Travel, work, ideas, art, and society — the vocabulary of "
                "real conversations.", "core", "a2-everyday",
                _vocab_lessons("b1-wider-world", B1_COURSE_TOPICS,
                               {"B1", "B2"}, B1_GRAMMAR_SEQUENCE)),
        _course("a2-recall", "Active Recall: Everyday", "A2", 5,
                "Produce every A2 word from English cues — recognition is "
                "not production.", "core", "a2-everyday",
                _recall_lessons("a2-recall", A2_COURSE_TOPICS, {"A1", "A2"})),
        _course("b1-recall", "Active Recall: Wider World", "B1", 6,
                "Production practice for the B1 vocabulary.", "core",
                "b1-wider-world",
                _recall_lessons("b1-recall", B1_COURSE_TOPICS, {"B1", "B2"})),
        _course("phonetics-path", "Cyrillic Bootcamp", "A0", 7,
                "Sound out real words letter by letter until reading is "
                "automatic.", "phonetics", None, _phonetics_lessons()),
        _course("grammar-path", "Grammar Mastery Path", "A1", 8,
                "Every grammar topic as a gradeable lesson, in curriculum "
                "order.", "grammar", "a0-foundations", _grammar_lessons()),
        _course("case-workshop", "Case Workshop", "A2", 9,
                "Decline every noun you know, case by case.", "skills",
                "a1-survival", _case_lessons()),
        _course("verb-workshop", "Verb Workshop", "A2", 10,
                "Conjugation drills across every verb in the dictionary.",
                "skills", "a1-survival", _verb_lessons()),
        _course("adjective-workshop", "Agreement Workshop", "A2", 11,
                "Adjective agreement drills.", "skills", "a1-survival",
                _adjective_lessons()),
        _course("aspect-workshop", "Aspect Pair Gym", "B1", 12,
                "Imperfective ↔ perfective, from memory.", "skills",
                "a2-everyday", _aspect_lessons()),
        _course("sentence-workshop", "Sentence Workshop", "A2", 13,
                "Rebuild scrambled sentences into natural word order.",
                "sentences", "a1-survival", _sentence_lessons()),
        _course("translation-workshop", "Translation Workshop", "B1", 14,
                "Produce full Russian sentences from English cues.",
                "sentences", "sentence-workshop", _translation_lessons()),
        _course("stress-workshop", "Stress Gym", "A2", 15,
                "Train the hardest mechanical skill in Russian: stress "
                "placement.", "phonetics", "a0-foundations", _stress_lessons()),
        _course("listening-path", "Dictation Studio", "A2", 16,
                "Transcribe the library by ear, sentence by sentence.",
                "listening", "a1-survival", _listening_lessons()),
    ]
