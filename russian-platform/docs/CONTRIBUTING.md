# Contributing

## Ground rules
1. **Offline-first**: every AI/network feature ships with a deterministic
   fallback (`provider.is_generative` pattern). CI has no network.
2. **Content is data**: new words/texts/grammar/scenarios go through seed
   modules or content packs — never hard-code content into logic.
   Language-specific *code* is allowed only in `services/morphology.py`.
3. **Answer keys stay server-side.** Grade via
   `text_utils.answer_matches`; strip keys before serializing.
4. **Every interaction appends a `LearningEvent`** — analytics and quests
   derive from the stream; do not add parallel counters.
5. **Tests in the same commit**; backend coverage floor is 95%
   (`pytest --cov=app`), lint clean (`ruff check app tools tests --select F`).

## Workflow
```bash
cd backend && pip install -e ".[dev]" && pytest
cd frontend && npm install && npm test && npm run build
```
Branch from the default branch; keep commits scoped; describe *why* in
the commit body. Run the benchmark (`python -m tools.benchmark`) if you
touched a hot path and paste the table into the PR.

## Where things live
See docs/FINAL_ARCHITECTURE.md for the map, DEVELOPER_GUIDE.md for
conventions, CONTENT_PIPELINE.md to add content, CONTENT_PACK_SPEC.md to
ship it, TESTING.md for the test rules.

## Adding a language
Build a content pack (language_meta + vocabulary + texts + grammar +
scenarios) per CONTENT_PACK_SPEC.md. If the language needs generated
inflections, contribute a sibling morphology module and wire it in the
vocab factory — that is the single sanctioned code change.
