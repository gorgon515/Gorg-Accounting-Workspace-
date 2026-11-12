# Career Desk — career acquisition agent

A local system that holds your career profile, discovers and scores jobs, builds fact-checked application
packages, tracks every application through a 17-stage pipeline, and gates what may be done without you.

## Run

```bash
cd career
python3 -m career_agent.cli init
python3 -m career_agent.cli serve        # dashboard on http://127.0.0.1:8765
python3 -m unittest discover -s tests
```

Requires Python 3.10+ and `cryptography`. No other dependencies.

## Modules

| Module | Role |
|---|---|
| `db.py` | SQLite schema, Fernet field encryption, hash-chained audit log |
| `profile.py` | Career Profile sections, settings, explicit approvals (any edit revokes approval) |
| `discovery.py` | Employer ATS connectors (Greenhouse, Lever, Ashby public APIs) + `ingest()` for board results |
| `scoring.py` | Weighted 0–100 score; mandatory vs preferred; unrated categories make a score provisional |
| `documents.py` | Versioned encrypted documents, achievements/skills databases, fact-check for tailored documents |
| `crm.py` | Jobs, applications, statuses, communications, interviews, approval queue |
| `rules.py` | Submission gate: `auto` / `approval` / `manual` / `blocked` |
| `followup.py` | Due follow-up actions from timelines and correspondence |
| `analytics.py` | Dashboard metrics, all derived from recorded rows |
| `server.py`, `web/` | Localhost-only dashboard and JSON API |

The AI layer (interviewing, resume reconstruction, tailoring, judgement scores, email triage, browser form
filling) is performed by Claude sessions that call these modules; the modules enforce the rules.

## Hard guarantees enforced in code

- An application becomes **Application submitted** only through `crm.mark_submitted()`, which requires the
  portal's confirmation and where it was observed. Later stages are unreachable without it.
- Nothing is submitted until the profile, master documents and submission rules are each approved.
- Tailored documents must cite verified achievements; any figure or skill not in a verified source fails the
  fact-check and blocks submission.
- Legal declarations, background-check consent, work-eligibility, pay commitments, sensitive personal data,
  restrictive covenants and any answer not sourced from the verified profile always go to the approval queue.
- CAPTCHA or identity verification means `manual`: the package is saved and the link handed over.

## Automation boundary

| Fully automated | Needs your approval | Manual |
|---|---|---|
| Discovery, dedupe, closure detection | Profile, master documents, submission rules | CAPTCHA / identity verification |
| Scoring and classification | Any sensitive or unverified form answer | Portals that block automation |
| Tailoring + fact-check | Submission while auto-submit is off | Signing offers |
| Status tracking, follow-up reminders | Negotiation, accepting/declining, commitments | |

## Data

`career/data/` (database) is git-ignored and never committed. Personal fields and all documents are encrypted
with a key stored outside the data directory (`~/.config/career-agent/key`, or `CAREER_KEY`).

## Not built yet

Browser form-filling driver (Playwright), Gmail/Calendar sync loop, interview-prep generator, market-intelligence
reports, scheduled runs.
