"""Job discovery connectors.

Direct connectors hit employers' own public ATS job-board APIs (original postings, no scraping, no login).
Board results (Indeed, ZipRecruiter, ...) arrive through the orchestrating agent's connectors and are loaded with
`ingest()`. Sites whose terms forbid automated access (LinkedIn, Glassdoor) are deliberately not scraped.
"""
import html
import json
import re
import urllib.error
import urllib.request

from . import crm, db

UA = "career-agent/0.1"


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


def _text(s):
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(s or ""))).strip()


def _arrangement(*parts):
    t = " ".join(p or "" for p in parts).lower()
    return "remote" if "remote" in t else "hybrid" if "hybrid" in t else "onsite" if ("on-site" in t or "onsite" in t) else None


def greenhouse(token, employer):
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
    for j in data.get("jobs", []):
        loc = (j.get("location") or {}).get("name")
        yield {"source": "greenhouse", "source_id": str(j["id"]), "employer": employer, "title": j["title"],
               "location": loc, "arrangement": _arrangement(loc, j["title"]), "url": j["absolute_url"],
               "description": _text(j.get("content")), "verified": True}


def lever(token, employer):
    for j in _get(f"https://api.lever.co/v0/postings/{token}?mode=json"):
        cat = j.get("categories") or {}
        sal = j.get("salaryRange") or {}
        yield {"source": "lever", "source_id": j["id"], "employer": employer, "title": j["text"],
               "location": cat.get("location"),
               "arrangement": (j.get("workplaceType") or "").replace("on-site", "onsite") or _arrangement(cat.get("location")),
               "url": j["hostedUrl"], "description": _text(j.get("descriptionPlain") or j.get("description")),
               "comp_min": sal.get("min"), "comp_max": sal.get("max"), "comp_currency": sal.get("currency"),
               "verified": True}


def ashby(token, employer):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true")
    for j in data.get("jobs", []):
        yield {"source": "ashby", "source_id": j["id"], "employer": employer, "title": j["title"],
               "location": j.get("location"),
               "arrangement": "remote" if j.get("isRemote") else _arrangement(j.get("workplaceType"), j.get("location")),
               "url": j["jobUrl"], "description": _text(j.get("descriptionPlain") or j.get("descriptionHtml")),
               "verified": True}


CONNECTORS = {"greenhouse": greenhouse, "lever": lever, "ashby": ashby}


def ingest(conn, jobs, source_label=None):
    """Load normalised postings (from a connector or an agent-run board search). Dedupes by fingerprint."""
    stats = {"new": 0, "updated": 0, "unchanged": 0, "rejected": 0, "ids": []}
    for j in jobs:
        if source_label and not j.get("source"):
            j["source"] = source_label
        jid, res = crm.upsert_job(conn, j)
        stats[res.split(":")[0]] += 1
        if jid:
            stats["ids"].append(jid)
    return stats


def run_watchlist(conn, watchlist, title_filter=None):
    """watchlist: [{'ats': 'greenhouse', 'token': 'acme', 'employer': 'Acme'}]. Never raises: failures are reported."""
    report = []
    pat = re.compile(title_filter, re.I) if title_filter else None
    for w in watchlist:
        entry = {"employer": w["employer"], "ats": w["ats"]}
        try:
            jobs = [j for j in CONNECTORS[w["ats"]](w["token"], w["employer"]) if not pat or pat.search(j["title"])]
            stats = ingest(conn, jobs)
            closed = crm.close_missing(conn, w["ats"], w["employer"], set(stats["ids"])) if not pat else []
            entry.update(ok=True, **{k: v for k, v in stats.items() if k != "ids"}, closed=len(closed))
        except KeyError:
            entry.update(ok=False, error=f"unsupported ATS {w['ats']!r}")
        except (urllib.error.URLError, OSError, ValueError) as e:
            entry.update(ok=False, error=f"{type(e).__name__}: {e}")
        report.append(entry)
    db.audit(conn, "discovery.run", detail=report)
    return report
