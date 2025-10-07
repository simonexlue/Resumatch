import re, unicodedata
from fastapi import APIRouter
from ..schemas.analyze import AnalyzeRequest, AnalyzeOut, MatchLocation, MatchResult

router = APIRouter()

def _normalize_text(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")

def _build_exact_pattern(term: str) -> re.Pattern:
    esc = re.escape(term)
    return re.compile(rf"(?<![A-Za-z0-9]){esc}(?![A-Za-z0-9])", re.IGNORECASE)

def _flatten_bullets(resume):
    out = []
    for sec in (resume.experience or []):
        out.extend(sec.bullets or [])
    for sec in (resume.projects or []):
        out.extend(sec.bullets or [])
    return out

@router.post("/analyze", response_model=AnalyzeOut)
def analyze(req: AnalyzeRequest):
    jd = req.jd
    resume = req.resume
    bullets = _flatten_bullets(resume)
    norm = [{"id": b.id, "text": _normalize_text(b.text)} for b in bullets]
    skills_lower = set((s or "").lower() for s in (resume.skills or []))

    results = []
    must_found = nice_found = 0
    must_total = sum(1 for r in jd.requirements if r.priority == "must")
    nice_total = sum(1 for r in jd.requirements if r.priority == "nice")

    for r in jd.requirements:
        pat = _build_exact_pattern(r.skill)
        hit_ids = [b["id"] for b in norm if pat.search(b["text"])]
        skills_hit = req.count_skills_section and (r.skill.lower() in skills_lower)
        found = bool(hit_ids) or skills_hit
        if found:
            if r.priority == "must": must_found += 1
            else: nice_found += 1
        results.append(MatchResult(
            term=r.skill, priority=r.priority, found=found,
            locations=MatchLocation(bullets=hit_ids, skills_section=skills_hit)
        ))

    max_score = must_total * 2 + nice_total
    got_score = must_found * 2 + nice_found
    coverage_pct = 0.0 if max_score == 0 else round(100.0 * got_score / max_score, 1)

    return AnalyzeOut(
        results=results,
        coverage_pct=coverage_pct,
        must_found=must_found, must_total=must_total,
        nice_found=nice_found, nice_total=nice_total
    )
