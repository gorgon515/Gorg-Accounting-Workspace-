"""Build the single-file standalone app (Pocket edition).

Exports the content database from the seed modules as compact JSON and
injects it into standalone/template.html, producing one self-contained
HTML file: dictionary, SRS flashcards, curated lessons, the full grammar
encyclopedia, library texts, scripted dialogues, and trainers — no
server, no network, progress in localStorage. This is the build that
ships as a claude.ai Cowork artifact.

Usage:
    python -m tools.build_standalone [output.html]
"""
import json
import sys
from pathlib import Path

from app.seed.alphabet import ALPHABET, PRONUNCIATION_RULES
from app.seed.courses import COURSES
from app.seed.grammar_advanced import C2_TOPICS, CONTENT as GRAMMAR_CONTENT
from app.seed.grammar_topics import TOPICS
from app.seed.library import TEXTS
from app.seed.scenarios import SCENARIOS
from app.seed.vocabulary_core import VOCABULARY
from app.seed.wordlist import W
from app.services.morphology import strip_stress
from app.services.vocab_factory import build_all

TEMPLATE = Path(__file__).resolve().parents[2] / "standalone" / "template.html"

COMPACT_FIELDS = [
    ("gender", "g"), ("aspect", "asp"), ("aspect_partner", "ap"),
    ("mnemonic", "mn"), ("usage_notes", "un"), ("cultural_notes", "cn"),
    ("etymology", "et"), ("literal_translation", "lit"), ("register", "reg"),
]


def export_content() -> dict:
    words, forms = [], {}
    for entry in [*[dict(v) for v in VOCABULARY], *build_all(W)]:
        word = {
            "l": entry["lemma"], "s": entry["stressed"], "t": entry["translation"],
            "tr": entry["transliteration"], "ipa": entry["ipa"],
            "pos": entry["part_of_speech"], "cefr": entry["cefr_level"],
            "topic": entry.get("topic") or "general",
        }
        for src, dst in COMPACT_FIELDS:
            value = entry.get(src)
            if value and value != "neutral":
                word[dst] = value
        if entry.get("common_mistakes"):
            word["cm"] = entry["common_mistakes"]
        if entry.get("inflections"):
            word["inf"] = entry["inflections"]
        if entry.get("examples"):
            word["ex"] = [[a, b] for a, b in entry["examples"]]
        words.append(word)

        seen = {entry["lemma"]}
        for table in (entry.get("inflections") or {}).values():
            if isinstance(table, dict):
                for form in table.values():
                    plain = strip_stress(str(form)).lower()
                    if plain and plain not in seen:
                        seen.add(plain)
                        forms.setdefault(plain, entry["lemma"])

    topics = []
    for topic in TOPICS:
        if topic["slug"] in GRAMMAR_CONTENT and not topic["content"]:
            topic = {**topic, **GRAMMAR_CONTENT[topic["slug"]]}
        topics.append(topic)
    topics += C2_TOPICS

    return {
        "alphabet": ALPHABET, "rules": PRONUNCIATION_RULES,
        "words": words, "forms": forms, "grammar": topics,
        "courses": COURSES, "texts": TEXTS, "scenarios": SCENARIOS,
    }


def main(argv: list[str]) -> int:
    out_path = Path(argv[0]) if argv else Path("russian-institute.html")
    template = TEMPLATE.read_text(encoding="utf-8")
    if "__CONTENT__" not in template:
        print("ERROR: template has no __CONTENT__ marker")
        return 1
    payload = json.dumps(export_content(), ensure_ascii=False,
                         separators=(",", ":")).replace("</", "<\\/")
    out_path.write_text(template.replace("__CONTENT__", payload), encoding="utf-8")
    print(f"built {out_path} ({out_path.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
