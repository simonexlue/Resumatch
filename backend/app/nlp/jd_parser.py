# app/nlp/jd_parser.py
from __future__ import annotations
import csv, re, unicodedata
from typing import Dict, List, Tuple, Optional
import spacy
from spacy.matcher import PhraseMatcher

# ---------------- NLP core ----------------
_nlp = spacy.load("en_core_web_sm")

def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s or "")

# ---------------- CSV loader (skill,aliases,type) ----------------
def load_skills_dict(csv_path: str) -> Tuple[Dict[str, Dict], Dict[str, str], PhraseMatcher]:
    skills_map: Dict[str, Dict] = {}
    alias_to_canonical: Dict[str, str] = {}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            canonical = _norm((row.get("skill") or "").strip())
            if not canonical:
                continue
            aliases = [canonical]
            if row.get("aliases"):
                aliases += [ _norm(a).strip() for a in row["aliases"].split(",") if _norm(a).strip() ]
            s_type = (row.get("type") or "hard").strip().lower()

            skills_map[canonical] = {"type": s_type, "aliases": aliases}
            for a in aliases:
                alias_to_canonical[a.lower()] = canonical

    matcher = PhraseMatcher(_nlp.vocab, attr="LOWER")
    all_aliases = sorted(alias_to_canonical.keys(), key=lambda s: (-len(s), s))
    matcher.add("SKILLS", [_nlp.make_doc(a) for a in all_aliases])
    return skills_map, alias_to_canonical, matcher

# ---------------- Patterns ----------------
# Company / title / headings
COMPANY_AT = re.compile(r'^\s*At\s+([A-Z][\w&.\-]*(?:\s+[A-Z][\w&.\-]*)*)', re.I)
COMPANY_WHY = re.compile(r'^\s*Why\s+([A-Z][A-Za-z0-9&.\- ]{1,})\?', re.I)
COMPANY_LINE = re.compile(r'^(?:Company)\s*:\s*(.+)$', re.I)

TITLE_FROM_LINE = re.compile(r'^(?:Title|Role)\s*:\s*(.+)$', re.I)
TITLE_CUES = [
    re.compile(r'\b(?:looking\s+for|hiring|seeking)\s+(?:an?\s+)?(?P<title>[A-Z][A-Za-z0-9+/ .\-]{2,}?(?:Developer|Engineer|Manager|Scientist|Designer))\b', re.I),
    re.compile(r'\bjoin\s+(?:our|the)\s+team\s+(?:as|as\s+an|as\s+a)?\s+(?P<title>[A-Z][A-Za-z0-9+/ .\-]{2,}?(?:Developer|Engineer|Manager|Scientist|Designer))\b', re.I),
]
TITLE_FALLBACK = re.compile(r'\b(front[\s-]?end\s+engineer|front[\s-]?end\s+developer|full\s+stack\s+developer)\b', re.I)

SENIORITY_REGEX = re.compile(r'\b(junior|jr\.?|entry[-\s]?level|mid|intermediate|senior|sr\.?|lead|staff|principal)\b', re.I)

# Section headers
RESP_HEADERS = [
    r"Responsibilities",
    r"You will",
    r"You’ll",
    r"What you’ll do",
    r"What you'll do",
    r"What you will do",
]
REQ_MUST_HEADERS = [
    r"Basic Qualifications",
    r"Minimum Qualifications",
    r"Qualifications",
    r"Requirements",
]
REQ_NICE_HEADERS = [
    r"Preferred Qualifications",
    r"Other Qualifications",
    r"Nice to have",
]

HEADER_RE = re.compile(rf"^({'|'.join([
    *RESP_HEADERS, *REQ_MUST_HEADERS, *REQ_NICE_HEADERS,
    'About The Role','About the Role','About The Team','About the Team','Benefits','About','Overview','Role'
])})\s*:?\s*$", re.I)

BULLET = re.compile(r"^\s*([\-–—•●▪‣*]|[0-9]+\.)\s+")

# Skill list helpers
PAREN_LIST_NEAR_LANG = re.compile(r'programming\s+languages?\s*\((?P<inside>[^)]+)\)', re.I)
EITHER_ANDOR = re.compile(r'\beither\s+(?P<a>[A-Za-z0-9#+.]+)\s+(?:and\/?or|or)\s+(?P<b>[A-Za-z0-9#+.]+)', re.I)

TRICKY_SKILLS = [
    ("C++", re.compile(r'\bC\+\+\b', re.I)),
    ("C#",  re.compile(r'\bC#\b', re.I)),
    (".NET", re.compile(r'\b\.NET\b', re.I)),
    ("Node.js", re.compile(r'\bNode\.js\b', re.I)),
]

MUST_HINTS = re.compile(r"\b(must[-\s]?have|required|required\s+skills|you\s+must|we\s+need|proficien\w+|proficient)\b", re.I)
NICE_HINTS = re.compile(r"\b(nice[-\s]?to[-\s]?have|preferred|bonus|a\s+plus)\b", re.I)

# ---------------- Small helpers ----------------
def _titlecase_words(s: str) -> str:
    return " ".join(w if re.search(r'[+#.]', w) else w.capitalize() for w in s.split())

def _canon(token: str, alias_to_canonical: Dict[str, str]) -> Optional[str]:
    return alias_to_canonical.get((token or "").lower())

def _split_list(text: str) -> List[str]:
    parts = re.split(r'[,\uFF0C/]|(?:\s+and\s+)', text)
    return [p.strip() for p in parts if p.strip()]

def _collect_skills_by_phrase(text: str, alias_to_canonical: Dict[str, str]) -> List[str]:
    found: List[str] = []
    for m in PAREN_LIST_NEAR_LANG.finditer(text):
        for token in _split_list(m.group("inside")):
            c = _canon(token, alias_to_canonical)
            if c and c not in found:
                found.append(c)
    for m in EITHER_ANDOR.finditer(text):
        for token in (m.group("a"), m.group("b")):
            c = _canon(token, alias_to_canonical)
            if c and c not in found:
                found.append(c)
    for label, rx in TRICKY_SKILLS:
        if rx.search(text):
            c = _canon(label, alias_to_canonical) or label
            if c not in found:
                found.append(c)
    return found

# ---------------- Title / Company / Seniority ----------------
def _extract_company(lines: List[str]) -> Optional[str]:
    for ln in lines[:15]:
        m = COMPANY_LINE.search(ln)
        if m:
            return m.group(1).strip().rstrip(".")
        m2 = COMPANY_AT.search(ln)
        if m2:
            return m2.group(1).strip().rstrip(".")
        m3 = COMPANY_WHY.search(ln)
        if m3:
            return m3.group(1).strip().rstrip(".")
    # fallbacks: look for single proper noun in very first line
    first = lines[0] if lines else ""
    if first and first.istitle() and len(first.split()) <= 4:
        return first.strip().rstrip(".")
    return None

def _extract_title(text: str, lines: List[str]) -> Optional[str]:
    for ln in lines[:10]:
        m = TITLE_FROM_LINE.search(ln)
        if m:
            return _titlecase_words(m.group(1).strip())
    for rx in TITLE_CUES:
        m = rx.search(text)
        if m:
            return _titlecase_words(m.group("title").strip())
    m2 = TITLE_FALLBACK.search(text)
    if m2:
        return _titlecase_words(m2.group(0))
    return None

def _extract_seniority(text: str) -> Optional[str]:
    m = SENIORITY_REGEX.search(text)
    if not m:
        return None
    val = m.group(1).lower()
    if val.startswith(("junior","jr")): return "junior"
    if val.startswith(("mid","intermediate")): return "mid"
    if val.startswith(("senior","sr")): return "senior"
    if val in ("lead","staff","principal"): return val
    return None

# ---------------- Section slicing ----------------
def _slice_sections(lines: List[str]) -> Dict[str, List[str]]:
    """
    Returns a dict of sections with raw lines.
    Keys we care about:
      - responsibilities
      - req_must
      - req_nice
    """
    out = {"responsibilities": [], "req_must": [], "req_nice": []}
    current = None

    def _choose_bucket(h: str) -> Optional[str]:
        if re.fullmatch(rf"({'|'.join(RESP_HEADERS)})", h, re.I):
            return "responsibilities"
        if re.fullmatch(rf"({'|'.join(REQ_MUST_HEADERS)})", h, re.I):
            return "req_must"
        if re.fullmatch(rf"({'|'.join(REQ_NICE_HEADERS)})", h, re.I):
            return "req_nice"
        return None

    for ln in lines:
        if HEADER_RE.match(ln):
            head = HEADER_RE.match(ln).group(1)
            current = _choose_bucket(head)  # may be None for unrelated headings
            continue
        if current:
            out[current].append(ln)

    return out

def _lines_to_items(raw: List[str]) -> List[str]:
    """
    Convert bullet/verb-leading lines under a section into clean items.
    """
    items: List[str] = []
    for ln in raw:
        if not ln.strip():
            continue
        if BULLET.match(ln):
            items.append(BULLET.sub("", ln).strip())
        else:
            doc = _nlp(ln)
            if doc and len(doc) > 0 and doc[0].pos_ == "VERB":
                items.append(ln.strip())
    # dedupe preserve order
    seen, out = set(), []
    for it in items:
        if it not in seen:
            out.append(it); seen.add(it)
    return out

# ---------------- Main ----------------
def parse_job_description(raw_text: str,
                          skills_map: Dict[str, Dict],
                          alias_to_canonical: Dict[str, str],
                          matcher: PhraseMatcher) -> dict:
    lines = [ln.strip() for ln in _norm(raw_text).splitlines() if ln.strip()]
    text  = "\n".join(lines)
    doc   = _nlp(text)

    title = _extract_title(text, lines)
    company = _extract_company(lines)
    seniority = _extract_seniority(text)

    # Slice sections
    blocks = _slice_sections(lines)
    responsibilities = _lines_to_items(blocks["responsibilities"])

    # Requirements from blocks + sentence scanning
    req_map: Dict[str, str] = {}

    def add_skills_from_text(s: str, default_prio: str):
        # PhraseMatcher
        sdoc = _nlp(s)
        spans = matcher(sdoc)
        for _, st, en in spans:
            alias = sdoc[st:en].text.lower()
            c = alias_to_canonical.get(alias)
            if not c:
                continue
            # escalate to 'must' if MUST hints appear in same line
            prio = "must" if MUST_HINTS.search(s) else default_prio
            if c not in req_map or req_map[c] == "nice":
                req_map[c] = prio
        # Regex collectors (parenthesis lists, either/and-or, tricky tokens)
        for c in _collect_skills_by_phrase(s, alias_to_canonical):
            prio = "must" if default_prio == "must" or MUST_HINTS.search(s) else default_prio
            if c not in req_map or req_map[c] == "nice":
                req_map[c] = prio

    # From labeled sections
    for line in _lines_to_items(blocks["req_must"]):
        add_skills_from_text(line, default_prio="must")
    for line in _lines_to_items(blocks["req_nice"]):
        add_skills_from_text(line, default_prio="nice")

    # If nothing found yet, scan all sentences (helps “paragraph-y” JDs)
    if not req_map:
        for sent in doc.sents:
            s = sent.text.strip()
            if not s:
                continue
            default = "must" if MUST_HINTS.search(s) else ("nice" if NICE_HINTS.search(s) else "nice")
            add_skills_from_text(s, default_prio=default)

    # Keep only hard skills (exact-match project rule)
    requirements = [{"skill": k, "priority": req_map[k]}
                    for k in sorted(req_map.keys())
                    if skills_map.get(k, {}).get("type", "hard") == "hard"]

    return {
        "title": title,
        "company": company,
        "seniority": seniority,
        "requirements": requirements,
        "responsibilities": responsibilities
    }
