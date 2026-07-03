"""Rule-based Russian morphology engine.

Generates transliteration, approximate IPA, noun/adjective declension and
verb conjugation tables from a stressed lemma. This is what lets the
vocabulary database scale: curated wordlists carry one compact line per
word, and the factory (services/vocab_factory.py) expands each into a full
dictionary entry at seed time. Irregular words pass explicit overrides.

Scope notes (deliberate, documented):
- IPA is a close phonetic approximation (palatalization, vowel reduction,
  final devoicing) — not a full phonological analysis (no gemination,
  no assimilation clusters like сч→щ).
- Declension covers the regular paradigms + the 7-letter spelling rule;
  mobile stress and fleeting vowels are supplied via overrides.
"""
from __future__ import annotations

STRESS = "́"
VOWELS = "аеёиоуыэюя"
SOFTENING_VOWELS = "еёиюя"
HUSHERS = "жчшщ"
VELARS = "гкх"

TRANSLIT = {
    "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo",
    "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
    "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
    "ф": "f", "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch",
    "ъ": '"', "ы": "y", "ь": "'", "э": "e", "ю": "yu", "я": "ya",
}

IPA_CONSONANTS = {
    "б": "b", "в": "v", "г": "ɡ", "д": "d", "ж": "ʐ", "з": "z", "й": "j",
    "к": "k", "л": "ɫ", "м": "m", "н": "n", "п": "p", "р": "r", "с": "s",
    "т": "t", "ф": "f", "х": "x", "ц": "ts", "ч": "tɕ", "ш": "ʂ", "щ": "ɕː",
}
# Always-hard and always-soft consonants ignore the following vowel.
ALWAYS_HARD = "жшц"
ALWAYS_SOFT = "чщй"
FINAL_DEVOICE = {"б": "p", "в": "f", "г": "k", "д": "t", "ж": "ʂ", "з": "s"}
SOFT_L = "lʲ"  # soft л is a plain l, not dark ɫ


def strip_stress(text: str) -> str:
    return text.replace(STRESS, "")


def stress_index(stressed: str) -> int:
    """Index (in the stress-stripped string) of the stressed vowel.
    Falls back to ё (always stressed), then to the only/first vowel."""
    accent_at = stressed.find(STRESS)
    if accent_at > 0:
        return accent_at - 1  # single accent: plain index equals stressed-1
    lower = strip_stress(stressed).lower()
    if "ё" in lower:
        return lower.index("ё")
    vowel_positions = [i for i, c in enumerate(lower) if c in VOWELS]
    return vowel_positions[0] if vowel_positions else -1


def transliterate(text: str) -> str:
    out = []
    for ch in strip_stress(text.lower()):
        out.append(TRANSLIT.get(ch, ch))
    return "".join(out)


def to_ipa(stressed: str) -> str:
    """Approximate IPA with stress marking, palatalization, vowel
    reduction, and final devoicing. E.g. молоко́ → [məɫɐˈko]."""
    word = strip_stress(stressed.lower())
    if not word:
        return "[]"
    stressed_at = stress_index(stressed.lower())
    vowel_positions = [i for i, c in enumerate(word) if c in VOWELS]

    def vowel_ipa(ch: str, pos: int, palatal: bool) -> str:
        is_stressed = pos == stressed_at
        if is_stressed:
            base = {"а": "a", "о": "o", "е": "e", "ё": "o", "и": "i",
                    "ы": "ɨ", "у": "u", "э": "ɛ", "ю": "u", "я": "a"}[ch]
            return base
        # Reduction: о/а → ɐ right before the stress, ə elsewhere;
        # е/я/э → ɪ; и/ы/у/ю keep quality.
        try:
            v_idx = vowel_positions.index(pos)
            stressed_v_idx = vowel_positions.index(stressed_at)
            pretonic = v_idx == stressed_v_idx - 1
        except ValueError:
            pretonic = False
        if ch in "оа":
            return "ɐ" if pretonic else "ə"
        if ch in "еяэ":
            return "ɪ"
        return {"и": "ɪ", "ы": "ɨ", "у": "ʊ", "ю": "ʊ", "ё": "o"}[ch]

    out: list[str] = []
    for i, ch in enumerate(word):
        nxt = word[i + 1] if i + 1 < len(word) else ""
        if ch in IPA_CONSONANTS:
            if i == len(word) - 1 and ch in FINAL_DEVOICE:
                consonant = FINAL_DEVOICE[ch]
            else:
                consonant = IPA_CONSONANTS[ch]
            soft = ch not in ALWAYS_HARD and (
                ch in ALWAYS_SOFT
                or (nxt != "" and nxt in SOFTENING_VOWELS)
                or nxt == "ь"
            )
            if soft and ch not in ALWAYS_SOFT:
                consonant = SOFT_L if ch == "л" else consonant + "ʲ"
            out.append(consonant)
        elif ch in VOWELS:
            glide = ch in "еёюя" and (
                i == 0 or word[i - 1] in VOWELS or word[i - 1] in "ъь"
            )
            piece = ("j" if glide else "") + vowel_ipa(ch, i, False)
            if i == stressed_at and len(vowel_positions) > 1:
                # ˈ goes before the syllable onset: the single consonant
                # (if any) directly preceding the stressed vowel.
                if i > 0 and word[i - 1] not in VOWELS and out:
                    out.insert(len(out) - 1, "ˈ")
                else:
                    piece = "ˈ" + piece
            out.append(piece)
        # ь/ъ: softness/separation already handled via the consonant/glide
    return "[" + "".join(out) + "]"


def infer_gender(lemma: str) -> str | None:
    plain = strip_stress(lemma)
    if plain.endswith(("а", "я")):
        return "f"
    if plain.endswith(("о", "е", "ё")):
        return "n"
    if plain.endswith("ь"):
        return None  # ambiguous — wordlist must specify
    return "m"


def _i_or_y(stem: str) -> str:
    """7-letter spelling rule: и (never ы) after velars and hushers."""
    return "и" if stem and stem[-1] in VELARS + HUSHERS else "ы"


def decline_noun(
    stressed: str,
    gender: str,
    animacy: str = "inanimate",
    overrides: dict[str, str] | None = None,
) -> dict[str, str]:
    """Regular declension (singular cases + nom/gen plural).

    Stress is kept in the lemma position; mobile-stress words pass the
    correct forms via `overrides`.
    """
    lemma = stressed
    plain = strip_stress(lemma)
    forms: dict[str, str] = {}

    def keep_stress(stem_plain: str, ending: str) -> str:
        """Reattach the lemma's stress: on the stem if it was there, else on
        the ending (end-stressed nouns like окно́ → окна́)."""
        idx = stress_index(lemma)
        if 0 <= idx < len(stem_plain):
            return stem_plain[: idx + 1] + STRESS + stem_plain[idx + 1:] + ending
        return _stress_last_vowel(stem_plain + ending)

    if gender == "f" and plain.endswith(("а", "я")):
        soft = plain.endswith("я")
        stem = plain[:-1]
        i_end = "и" if soft else _i_or_y(stem)
        forms = {
            "nom_sg": lemma,
            "gen_sg": keep_stress(stem, i_end),
            "dat_sg": keep_stress(stem, "и" if plain.endswith("ия") else "е"),
            "acc_sg": keep_stress(stem, "ю" if soft else "у"),
            "ins_sg": keep_stress(stem, "ей" if soft else "ой"),
            "pre_sg": keep_stress(stem, "и" if plain.endswith("ия") else "е"),
            "nom_pl": keep_stress(stem, i_end),
            "gen_pl": keep_stress(stem, "й" if plain.endswith("ия") else ""),
        }
    elif gender == "m" and (plain[-1] not in VOWELS and not plain.endswith("ь")):
        stem = plain if not plain.endswith("й") else plain[:-1]
        soft = plain.endswith("й")
        gen = keep_stress(stem, "я" if soft else "а")
        forms = {
            "nom_sg": lemma,
            "gen_sg": gen,
            "dat_sg": keep_stress(stem, "ю" if soft else "у"),
            "acc_sg": gen if animacy == "animate" else lemma,
            "ins_sg": keep_stress(stem, "ем" if soft else "ом"),
            "pre_sg": keep_stress(stem, "е"),
            "nom_pl": keep_stress(stem, "и" if soft else _i_or_y(stem)),
            "gen_pl": keep_stress(
                stem, "ев" if soft else ("ей" if stem[-1] in HUSHERS else "ов")
            ),
        }
    elif gender == "m" and plain.endswith("ь"):
        stem = plain[:-1]
        gen = keep_stress(stem, "я")
        forms = {
            "nom_sg": lemma,
            "gen_sg": gen,
            "dat_sg": keep_stress(stem, "ю"),
            "acc_sg": gen if animacy == "animate" else lemma,
            "ins_sg": keep_stress(stem, "ем"),
            "pre_sg": keep_stress(stem, "е"),
            "nom_pl": keep_stress(stem, "и"),
            "gen_pl": keep_stress(stem, "ей"),
        }
    elif gender == "f" and plain.endswith("ь"):
        stem = plain[:-1]
        i_form = keep_stress(stem, "и")
        forms = {
            "nom_sg": lemma,
            "gen_sg": i_form,
            "dat_sg": i_form,
            "acc_sg": lemma,
            "ins_sg": keep_stress(stem, "ью"),
            "pre_sg": i_form,
            "nom_pl": i_form,
            "gen_pl": keep_stress(stem, "ей"),
        }
    elif gender == "n" and plain.endswith(("о", "е")):
        soft = plain.endswith("е")
        stem = plain[:-1]
        forms = {
            "nom_sg": lemma,
            "gen_sg": keep_stress(stem, "я" if soft else "а"),
            "dat_sg": keep_stress(stem, "ю" if soft else "у"),
            "acc_sg": lemma,
            "ins_sg": keep_stress(stem, "ем" if soft else "ом"),
            "pre_sg": keep_stress(stem, "и" if plain.endswith("ие") else "е"),
            "nom_pl": keep_stress(stem, "я" if soft else "а"),
            "gen_pl": keep_stress(stem, "й" if plain.endswith("ие") else ""),
        }
    else:
        forms = {"nom_sg": lemma}

    if overrides:
        forms.update(overrides)
    return forms


def decline_adjective(stressed: str) -> dict[str, str]:
    """Nominative agreement forms for -ый/-ий/-ой adjectives."""
    plain = strip_stress(stressed)
    if plain.endswith("ой"):
        stem = plain[:-2]
        # -ой adjectives are end-stressed: больш-о́й, больш-а́я
        return {
            "m": stressed,
            "f": stem + "а" + STRESS + "я",
            "n": stem + "о" + STRESS + "е",
            "pl": stem + "и" + STRESS + "е",
        }
    stem_plain = plain[:-2]
    soft = plain.endswith("ий") and not (stem_plain and stem_plain[-1] in VELARS + HUSHERS)

    def with_stress(ending: str) -> str:
        idx = stress_index(stressed)
        if 0 <= idx < len(stem_plain):
            return stem_plain[: idx + 1] + STRESS + stem_plain[idx + 1:] + ending
        return stem_plain + ending

    if soft:
        return {"m": stressed, "f": with_stress("яя"), "n": with_stress("ее"),
                "pl": with_stress("ие")}
    plural = "ие" if stem_plain and stem_plain[-1] in VELARS + HUSHERS else "ые"
    feminine = "ая"
    neuter = "ее" if stem_plain and stem_plain[-1] in HUSHERS else "ое"
    return {"m": stressed, "f": with_stress(feminine), "n": with_stress(neuter),
            "pl": with_stress(plural)}


def conjugate_verb(
    stressed: str, overrides: dict[str, str] | None = None
) -> dict[str, dict[str, str]]:
    """Present-tense table + past tense for regular verbs.

    Handles -ать/-ять (1st conj.), -ить (2nd conj., with the husher
    spelling rule), -овать/-евать (→ -ую), -еть (2nd conj. by default for
    the common ones we seed). Irregulars pass full `overrides` shaped
    {"present": {...}, "past": {...}}.
    """
    plain = strip_stress(stressed)
    reflexive = plain.endswith("ся")
    if reflexive:
        # Conjugate the base verb, then re-attach -ся/-сь below.
        base = stressed[:-2] if stressed.endswith("ся") else stressed
        tables = conjugate_verb(base, None)
        for table, forms in tables.items():
            tables[table] = {
                k: v + ("ся" if strip_stress(v)[-1] not in VOWELS else "сь")
                for k, v in forms.items()
            }
        if overrides:
            for table, forms in overrides.items():
                tables.setdefault(table, {}).update(forms)
        return tables

    present: dict[str, str] = {}
    # 2nd-conjugation end stress (говори́ть → говорю́, говори́шь): the
    # infinitive is stressed on the и/е of its -ить/-еть ending.
    end_stressed = plain.endswith(("ить", "еть")) and stress_index(stressed) >= len(
        plain
    ) - 3

    def mark(form_plain: str, on_ending: bool) -> str:
        """Keep the infinitive's stem stress, or stress the ending's first
        vowel for end-stressed verbs (говор+ю́, говор+и́шь, говор+и́те)."""
        if on_ending:
            stem_len = len(plain) - 3  # consonant stem of -ить/-еть verbs
            for i in range(stem_len, len(form_plain)):
                if form_plain[i] in VOWELS:
                    return form_plain[: i + 1] + STRESS + form_plain[i + 1:]
            return _stress_last_vowel(form_plain)
        idx = stress_index(stressed)
        if 0 <= idx < len(form_plain) and form_plain[idx] in VOWELS:
            return form_plain[: idx + 1] + STRESS + form_plain[idx + 1:]
        return _stress_last_vowel(form_plain)

    if plain.endswith(("овать", "евать")):
        # -овать/-евать → -у́ю: рисова́ть → рису́ю. After hushers/ц the
        # spelling rule forces у: танцева́ть → танцу́ю.
        raw_stem = plain[:-5]
        suffix_vowel = (
            "у"
            if plain.endswith("овать") or (raw_stem and raw_stem[-1] in HUSHERS + "ц")
            else "ю"
        )
        stem = _stress_last_vowel(raw_stem + suffix_vowel)
        present = {
            "я": stem + "ю", "ты": stem + "ешь", "он": stem + "ет",
            "мы": stem + "ем", "вы": stem + "ете", "они": stem + "ют",
        }
    elif plain.endswith(("ать", "ять")):
        # 1st conjugation keeps the infinitive's stress: чита́ть → чита́ю.
        stem = plain[:-2]  # keeps the а/я: чита- → чита + ю
        present = {
            "я": mark(stem + "ю", False),
            "ты": mark(stem + "ешь", False),
            "он": mark(stem + "ет", False),
            "мы": mark(stem + "ем", False),
            "вы": mark(stem + "ете", False),
            "они": mark(stem + "ют", False),
        }
    elif plain.endswith(("ить", "еть")):
        stem = plain[:-3]
        husher = stem and stem[-1] in HUSHERS
        present = {
            "я": mark(stem + ("у" if husher else "ю"), end_stressed),
            "ты": mark(stem + "ишь", end_stressed),
            "он": mark(stem + "ит", end_stressed),
            "мы": mark(stem + "им", end_stressed),
            "вы": mark(stem + "ите", end_stressed),
            "они": mark(stem + ("ат" if husher else "ят"), end_stressed),
        }
    past_stem = plain[:-2] if plain.endswith("ть") else plain
    past = {
        "m": mark(past_stem + "л", False),
        "f": mark(past_stem + "ла", False),
        "n": mark(past_stem + "ло", False),
        "pl": mark(past_stem + "ли", False),
    }
    tables = {"present": present, "past": past}
    if overrides:
        # Merge per-form so irregulars only list the forms that deviate
        # (e.g. {"present": {"я": "прошу́"}} for the с→ш mutation).
        for table, forms in overrides.items():
            tables.setdefault(table, {}).update(forms)
    return tables


def _stress_last_vowel(text: str) -> str:
    for i in range(len(text) - 1, -1, -1):
        if text[i] in VOWELS:
            return text[: i + 1] + STRESS + text[i + 1:]
    return text
