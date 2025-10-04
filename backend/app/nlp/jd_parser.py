from __future__ import annotations
import csv
import re
from typing import Dict, List, Tuple, Optional
import spacy
from spacy.matcher import PhraseMatcher

# Load spaCy Model
_nlp = spacy.load("en_core_web_sm")

MUST_HINTS = re.compile(r"\b(must[-\s]?have|required|required skills|you must|we need)\b", re.I)
NICE_HINTS = re.compile(r"\b(nice[-\s]?to[-\s]?have|preferred|bonus|a plus)\b", re.I)

# Seniority keywords by priority
SENIORITY_ORDER = ["junior", "mid", "intermediate", "senior", "lead", "staff", "principal"]
SENIORITY_REGEX = re.compile(r"\b(junior|mid|intermediate|senior|lead|staff|principal)\b", re.I)

TITLE_FROM_LINE = re.compile(r"^(?:title|role)\s*:\s*(.+)$", re.I)
COMPANY_FROM_LINE = re.compile(r"^(?:company)\s*:\s*(.+)$", re.I)
COMPANY_AT = re.compile(r"\bat\s+([A-Z][A-Za-z0-9&.\- ]{1,})")

BULLET = re.compile(r"^\s*[-•*]\s+")

def load_skills_dict(csv_path: str) -> Tuple[Dict[str, Dict], Dict[str, str], PhraseMatcher]:
    """
    Returns:
      skills_map: {canonical_skill: {"type":"hard|soft","aliases":[...]}}
      alias_to_canonical: {"react.js":"React", "reactjs":"React", ...}
      matcher: spaCy PhraseMatcher ready to find aliases as exact phrases
    """
    skills_map: Dict[str, Dict] = {}
    alias_to_canonical: Dict[str, str] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canonical = row["skill"].strip()
            s_type = (row.get("type") or "hard").strip().lower()
            aliases = [canonical]  # include canonical itself
            if row.get("aliases"):
                aliases += [a.strip() for a in row["aliases"].split(",") if a.strip()]
            skills_map[canonical] = {"type": s_type, "aliases": aliases}
            for a in aliases:
                alias_to_canonical[a.lower()] = canonical

    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    patterns = [ _nlp.make_doc(a) for a in alias_to_canonical.keys() ]
    matcher.add("SKILLS", patterns)
    return skills_map, alias_to_canonical, matcher

def _extract_title_company(lines: List[str]) -> Tuple[Optional[str], Optional[str]]:
    title = None
    company = None
    for line in lines[:10]:  # look near the top
        m = TITLE_FROM_LINE.search(line)
        if m:
            title = m.group(1).strip()
        m2 = COMPANY_FROM_LINE.search(line)
        if m2:
            company = m2.group(1).strip()
        if not company:
            mat = COMPANY_AT.search(line)
            if mat:
                company = mat.group(1).strip()
    # Fallback: first short line could be title
    if not title:
        if lines:
            first = lines[0].strip()
            if 3 <= len(first.split()) <= 8:
                title = first
    return title, company

def _extract_seniority(text: str) -> Optional[str]:
    m = SENIORITY_REGEX.search(text)
    if not m:
        return None
    found = m.group(1).lower()
    # normalize to canonical label in SENIORITY_ORDER
    for s in SENIORITY_ORDER:
        if s in found:
            return s
    return found

def _extract_responsibilities(lines: List[str]) -> List[str]:
    out: List[str] = []
    for ln in lines:
        if BULLET.match(ln.strip()):
            out.append(BULLET.sub("", ln).strip())
        else:
            # Include lines starting with a verb
            doc = _nlp(ln)
            if doc and len(doc) > 0 and doc[0].pos_ == "VERB":
                out.append(ln.strip())
    # Deduplicate keep order
    seen = set()
    uniq = []
    for r in out:
        if r not in seen:
            uniq.append(r)
            seen.add(r)
    return uniq[:20]  # cap to keep payload tidy

def parse_job_description(raw_text: str, skills_map: Dict, alias_to_canonical: Dict, matcher: PhraseMatcher):
    """
    Returns structured dict:
      { title, company, seniority, requirements: [{skill, priority}], responsibilities: [...] }
    """
    # Normalize & split into non-empty lines
    lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    text = "\n".join(lines)

    title, company = _extract_title_company(lines)
    seniority = _extract_seniority(text)

    # Per-line pass: find skills and classify must/nice by hints in same line
    must_set, nice_set = set(), set()
    for ln in lines:
        doc = _nlp(ln)
        spans = matcher(doc)
        if not spans:
            continue
        is_must = bool(MUST_HINTS.search(ln))
        is_nice = bool(NICE_HINTS.search(ln))
        for _, start, end in spans:
            alias = doc[start:end].text.lower()
            canonical = alias_to_canonical.get(alias)
            if not canonical:
                continue
            if is_must:
                must_set.add(canonical)
            elif is_nice:
                nice_set.add(canonical)
            else:
                # Default: put in 'must' if line contains 'requirement' word, else 'nice'
                if re.search(r"\brequire(d|ments?)\b", ln, re.I):
                    must_set.add(canonical)
                else:
                    nice_set.add(canonical)

    # Build requirements list with unique canonical skills
    reqs = []
    seen = set()
    for s in list(must_set) + [x for x in nice_set if x not in must_set]:
        if s in seen:
            continue
        seen.add(s)
        priority = "must" if s in must_set else "nice"
        reqs.append({"skill": s, "priority": priority})

    responsibilities = _extract_responsibilities(lines)

    return {
        "title": title,
        "company": company,
        "seniority": seniority,
        "requirements": reqs,
        "responsibilities": responsibilities
    }