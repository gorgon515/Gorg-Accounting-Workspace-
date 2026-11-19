"""Weighted 0-100 job scoring.

Deterministic categories are computed here. Judgement categories (advancement,
benefits, reputation, and optionally career_alignment) are supplied by the AI
evaluator as `rated`. A category nobody has rated is left out and the remaining
weights are renormalised; the result is then flagged provisional rather than
padded with a made-up neutral number.
"""
import re

CLASSES = [(90, "Exceptional match"), (80, "Strong match"), (70, "Worth pursuing"), (60, "Secondary opportunity"),
           (0, "Below threshold")]


def classify(score):
    return next(label for floor, label in CLASSES if score >= floor)


def _norm(s):
    return re.sub(r"[^a-z0-9+#. ]", " ", (s or "").lower())


def _has(text, term):
    return re.search(r"(?<![a-z0-9])" + re.escape(_norm(term).strip()) + r"(?![a-z0-9])", text) is not None


def qualifications(job, profile):
    """Mandatory misses hurt a lot, preferred misses a little; never auto-reject on a preferred gap."""
    q = profile.get("qualifications", {})
    have = _norm(" ; ".join(str(x) for k in ("skills", "certifications", "certifications_in_progress", "software",
                                              "education", "languages", "experience_keywords")
                            for x in q.get(k, [])))
    mand, pref = job.get("mandatory") or [], job.get("preferred") or []
    if not mand and not pref:
        return None, {}
    m_hit = [t for t in mand if _has(have, t)]
    p_hit = [t for t in pref if _has(have, t)]
    m = len(m_hit) / len(mand) if mand else 1.0
    p = len(p_hit) / len(pref) if pref else 1.0
    score = 100 * (0.8 * m + 0.2 * p) if mand else 100 * (0.6 + 0.4 * p)
    yrs, need = q.get("years_experience"), job.get("years_required")
    if yrs is not None and need:
        if yrs < need:
            score -= min(30, 10 * (need - yrs))
    return max(0.0, score), {"mandatory_missing": [t for t in mand if t not in m_hit],
                             "preferred_missing": [t for t in pref if t not in p_hit],
                             "overqualified": bool(yrs is not None and need and yrs >= need + 3)}


def compensation(job, profile):
    c = profile.get("compensation", {})
    lo, hi = job.get("comp_min"), job.get("comp_max")
    floor, ideal = c.get("min_base"), c.get("ideal_base")
    if not floor or (lo is None and hi is None):
        return None, {}
    mid = (lo + hi) / 2 if lo is not None and hi is not None else (hi if hi is not None else lo)
    top = hi if hi is not None else mid
    if top < floor:
        return 0.0, {"below_minimum": True}
    ideal = ideal or floor * 1.2
    if mid >= ideal:
        return 100.0, {}
    return max(40.0, 60 + 40 * (mid - floor) / max(1, ideal - floor)), {}


def location(job, profile):
    p = profile.get("employment_preferences", {})
    locs = [_norm(x) for x in p.get("locations", [])]
    jl, arr = _norm(job.get("location")), (job.get("arrangement") or "").lower()
    if not locs and not p.get("arrangements"):
        return None, {}
    if arr == "remote" and "remote" in [a.lower() for a in p.get("arrangements", [])]:
        return 100.0, {}
    if any(l and l in jl for l in locs):
        return 100.0, {}
    if p.get("open_to_relocation"):
        return 60.0, {"requires_relocation": True}
    return 10.0, {"outside_preferred_locations": True}


def working_conditions(job, profile):
    p = profile.get("employment_preferences", {})
    want = [a.lower() for a in p.get("arrangements", [])]
    arr = (job.get("arrangement") or "").lower()
    if not want or not arr:
        return None, {}
    return (100.0 if arr in want else 30.0), {}


def career_alignment(job, profile):
    ci = profile.get("career_interests", {})
    title, ind = _norm(job.get("title")), _norm(job.get("industry"))
    avoid = [_norm(x) for x in ci.get("avoid_industries", [])]
    if ind and any(a and a in ind for a in avoid):
        return 0.0, {"avoided_industry": True}
    titles = [_norm(t) for t in ci.get("target_titles", [])]
    if not titles:
        return None, {}
    best = 0.0
    for t in titles:
        words = [w for w in t.split() if len(w) > 2]
        if t and t in title:
            best = 100.0
        elif words:
            best = max(best, 90 * sum(w in title.split() for w in words) / len(words))
    inds = [_norm(x) for x in ci.get("industries", [])]
    if ind and inds:
        best = 0.8 * best + (20 if any(i in ind for i in inds) else 0)
    return min(100.0, best), {}


COMPUTED = {"career_alignment": career_alignment, "qualifications": qualifications, "compensation": compensation,
            "location": location, "working_conditions": working_conditions}


def score_job(job, profile, weights, rated=None):
    """Return {score, classification, categories, flags, provisional, unrated}."""
    rated = rated or {}
    cats, flags, unrated = {}, {}, []
    for name in weights:
        if name in rated:
            cats[name] = float(rated[name])
            continue
        val, fl = COMPUTED[name](job, profile) if name in COMPUTED else (None, {})
        flags.update(fl)
        if val is None:
            unrated.append(name)
        else:
            cats[name] = round(val, 1)
    total_w = sum(weights[c] for c in cats)
    score = round(sum(cats[c] * weights[c] for c in cats) / total_w, 1) if total_w else 0.0
    return {"score": score, "classification": classify(score), "categories": cats, "flags": flags,
            "unrated": unrated, "provisional": bool(unrated)}
