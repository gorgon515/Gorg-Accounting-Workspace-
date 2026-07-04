# User Manual · Русский Институт

## Getting started
1. Create an account (email + password). Your data stays on the machine
   running the server.
2. Take the **placement test** (Exams → it sets your CEFR level), or start
   from zero with *Foundations: Read & Greet*.
3. Set your daily goal and immersion level in **Settings**.

## Daily loop (60–90 minutes)
1. **Review** (🔁) — clear your due cards first. Keyboard: Space reveals,
   1–4 rates (Again/Hard/Good/Easy). Honest ratings make the scheduler
   smarter; it adapts your intervals to your accuracy.
2. **Lessons** (🎓) — one or two lessons from your current course. Passing
   the mastery test unlocks the next lesson and enrolls new words into
   your reviews automatically.
3. **One skill block** — rotate: Library (read/shadow/dictate a text),
   Conversation (finish a scenario, read the report), Writing (any prompt,
   fix what the coach flags), or a Workshop (cases, verbs, stress).

## The tracks (Lessons page)
- **Core Path** — vocabulary courses A0→B1 with checkpoints.
- **Grammar Mastery** — every grammar topic as a gradeable lesson.
- **Skill Workshops** — declension, conjugation, agreement, aspect pairs.
- **Sentence Lab** — word order and full-sentence translation.
- **Phonetics / Listening** — Cyrillic bootcamp, stress gym, dictation.
Courses unlock when their prerequisite course is 60% passed.

## Features worth knowing
- **Press `/` anywhere** → global search. It finds declined forms
  («книгу» → книга) and forgives typos («кнега» → книга).
- **Click any word** in a library text for its dictionary card; add it to
  your reviews with one tap.
- **Reader modes**: 🔊 karaoke playback highlights each word; 🐢 slow;
  🔁 loop; A·B repeats a sentence range; speed presets are remembered.
- **Certificates**: pass a level exam (70%+) and print it from the result
  screen.
- **Progress** (📈) shows your weekly report, forgotten words, weakest
  skill, and what to do about each.

## Offline use
After your first online session the app keeps working without internet:
cached lessons, texts, dictionary, and reviews (ratings sync when you
reconnect). For fully offline setups run the server locally — see
docs/DEPLOYMENT_GUIDE — and optionally point the AI tutor at a local
model (docs/AI_PROVIDER_GUIDE).

## Backup
Settings are per-account; your learning data can be exported from the API
(`POST /api/v1/account/export`, optionally password-encrypted) and
restored on any other installation — restoring never erases progress.

## Accessibility
Settings → font size, high contrast, dyslexia-friendly font, reduced
motion. Full keyboard navigation: Tab everywhere, skip-link at the top,
Space/1–4 in reviews, `/` for search.
