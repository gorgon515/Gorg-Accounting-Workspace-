# API Reference

Interactive documentation: run the server and open **`/docs`** (Swagger)
or **`/redoc`** — every route, schema, and example is generated from the
code and always current. This file is the orientation map.

All routes are under `/api/v1` and require `Authorization: Bearer <jwt>`
except register/login. Answer keys never appear in responses.

| Module | Routes | Purpose |
|---|---|---|
| auth | POST /auth/register · /auth/login · GET/PATCH /auth/me | accounts, profile, preferences |
| vocabulary | GET /vocabulary (q, wildcards, cefr/pos/domain/topic filters, form_matches, fuzzy) · /vocabulary/topics · /vocabulary/verb-pairs · /vocabulary/{id} · /vocabulary/{id}/family · /vocabulary/language/{code} | Dictionary 2.0 |
| grammar | GET /grammar/topics (mastery, readiness) · /grammar/topics/{slug} · POST …/drills | encyclopedia + drills |
| lessons | GET /lessons/courses (tracks, gating) · /lessons/{slug} · POST /lessons/{slug}/complete | curriculum |
| reviews | GET /reviews/queue · /reviews/forecast · POST /reviews/{card_id} | SRS |
| conversation | GET /conversation/scenarios · POST /conversation/sessions/{slug} · POST …/messages · GET …/report · GET /conversation/tutor/plan · POST /conversation/tutor | scenarios + tutor |
| practice | GET /practice/quiz · /practice/cloze · /practice/story · /practice/pronunciation/queue · POST /practice/pronunciation · /practice/writing | adaptive practice |
| writing | GET /writing/prompts · /writing/history · POST /writing/analyze | writing coach |
| library | GET /library/texts · /library/texts/{slug} · PUT …/bookmark · POST …/dictation · POST /library/add-word | reading/listening |
| exams | GET /exams/levels · /exams/level/{level} · POST …/submit · GET/POST /exams/placement(+/submit) · GET /exams/results · /exams/certificates/{id} | exams & certificates |
| analytics | GET /analytics/dashboard · /analytics/trends · /analytics/report?period= | dashboards & error intelligence |
| gamification | GET /gamification/quests · POST …/{slug}/claim · GET /gamification/achievements | quests & badges |
| account | POST /account/export · /account/import · GET /account/search | backup/restore, global search |

Conventions: JSON everywhere; errors are `{"detail": string}` with
meaningful status codes (401 auth, 403 locked, 404 missing, 409 state
conflicts, 422 validation); `Server-Timing` header on every response.
