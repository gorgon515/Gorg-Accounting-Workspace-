# Content Pack Specification (format 1)

A pack is one JSON document with two top-level keys:

```json
{
  "manifest": {
    "name": "ru-core",            // unique pack identity
    "version": "1.2.0",           // must increase for upgrades
    "format": 1,                  // this spec version
    "language": "ru",             // ISO code; new codes create a Language
    "counts": {"vocabulary": 663, "texts": 8, "grammar_topics": 40, "scenarios": 12},
    "checksum": "<sha256 of canonical content JSON>",
    "signature": "<hmac-sha256(checksum, pack_key)>"   // optional
  },
  "content": {
    "language_meta": {"code": "ru", "name_english": "...", "name_native": "...",
                       "script": "...", "metadata_json": {"alphabet": [...]}},
    "vocabulary":     [ /* full lexeme entries incl. examples/relations */ ],
    "texts":          [ /* library texts, sentence-aligned */ ],
    "grammar_topics": [ /* encyclopedia topics with drills */ ],
    "scenarios":      [ /* conversation dialogue trees */ ]
  }
}
```

## Guarantees
- **Integrity**: `checksum` = SHA-256 over `json.dumps(content,
  ensure_ascii=False, sort_keys=True)`. Any modification fails validation.
- **Authenticity**: if `signature` is present it must verify against the
  configured `RLP_PACK_KEY` (HMAC-SHA256 of the checksum). A bad
  signature is a hard error; an absent one installs with a warning.
- **Versioning**: installing requires `version` strictly greater than the
  installed version of the same `name`.
- **Partial/incremental updates**: content already present (by
  lemma/slug) is skipped, new content is added, and the provenance record
  merges — a v2 pack can ship only its additions.
- **Rollback**: `python -m tools.pack rollback <name>` removes exactly the
  rows the pack created. It **refuses** if the learner has SRS cards on
  the pack's vocabulary unless `--force` — user progress is never
  silently destroyed.
- **New languages**: a pack with an unknown `language` code creates the
  Language row from `language_meta`. No code changes.

## Tooling
```
python -m tools.pack build out.json --name ru-core --version 1.0.0
python -m tools.pack validate out.json
python -m tools.pack install out.json
python -m tools.pack rollback ru-core [--force]
python -m tools.pack list
```
Validation reuses the same validators as the bulk importers
(`app/services/content_import.py`, `app/services/content_packs.py`), so a
pack that validates will install.
