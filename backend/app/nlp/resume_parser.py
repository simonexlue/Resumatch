# backend/app/nlp/resume_parser.py
from __future__ import annotations
import io, re, uuid, unicodedata
from typing import Dict, List, Optional, Tuple
from pdfminer.high_level import extract_text as pdf_extract_text
from docx import Document
import spacy
from spacy.matcher import PhraseMatcher

# One shared spaCy nlp
_nlp = spacy.load("en_core_web_sm")

# ------------------------- Regexes & helpers -------------------------

# Headings
HEADING_EXPERIENCE = re.compile(r'^(work\s+experience|professional\s+experience|experience|employment\s+history)\s*:?\s*$', re.I)
HEADING_PROJECTS   = re.compile(r'^(projects?|personal\s+projects?)\s*:?\s*$', re.I)
HEADING_SKILLS     = re.compile(r'^(relevant\s+(coursework\s*&\s*)?skills|skills?|technical\s+skills|tech(nical)?\s+(stack|skills)|skills\s*&\s*(tools|technologies)|tools|tooling|languages\s*&\s*frameworks?)\s*:?\s*$', re.I)
HEADING_EDUCATION  = re.compile(r'^(education|education\s*&\s*certifications|education\s+and\s+certifications|certifications)\s*:?\s*$', re.I)

BULLET_LINE = re.compile(r'^\s*([\-–—•●▪‣*]|[0-9]+\.)\s+')

EMAIL_RE    = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}')
URL_RE      = re.compile(r'https?://[^\s)]+', re.I)
LINKEDIN_RE = re.compile(r'linkedin\s*:?\s*(?P<path>(?:https?://)?(?:www\.)?linkedin\.com[^\s]*|/in/[A-Za-z0-9\-_/]+)', re.I)

# Name in Title Case or ALL CAPS, 2–4 tokens
NAME_CANDIDATE = re.compile(r'^([A-Z][a-z]+(?:[-\s][A-Z][a-z]+){1,3}|[A-Z]+(?:[-\s][A-Z]+){1,3})$')
SEP_SPLIT   = re.compile(r'[|•●▪‣·]+')
SKILL_SPLIT = re.compile(r'[;,/|•●·]+')

# Header split must have spaces around separators; never split "simone-lue" or "cross-device"
HEADER_SPLITS = [re.compile(r'\s\|\s'), re.compile(r'\s-\s'), re.compile(r'\s–\s'), re.compile(r'\s—\s')]

# Month names + date range
MONTH = (
    r'(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|'
    r'Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
)
# pure date line, anchored; supports hyphen or "to"
DATE_RANGE_ONLY = re.compile(
    rf'^\s*(?P<start_m>{MONTH})\s+(?P<start_y>\d{{4}})\s*(?:[-–—]|to|TO)\s*'
    rf'(?P<end_m>{MONTH}|Present|PRESENT|Current|Now)\s*(?P<end_y>\d{{4}})?\s*$',
    re.I
)
# embedded range (for lines like "Company | Title | Aug 2025 - Oct 2025")
DATE_RANGE_ANY = re.compile(
    rf'(?P<start_m>{MONTH})\s+(?P<start_y>\d{{4}})\s*(?:[-–—]|to|TO)\s*'
    rf'(?P<end_m>{MONTH}|Present|PRESENT|Current|Now)\s*(?P<end_y>\d{{4}})?',
    re.I
)

TITLE_HINT = re.compile(r'(developer|engineer|manager|lead|intern|analyst|designer|freelance)', re.I)
BIZ_HINT   = re.compile(r'(inc|ltd|llc|corp|co|company|bar|cafe|shop|studio|solutions|systems|labs)', re.I)

MONTH_TO_NUM = {
    'jan':'01','january':'01','feb':'02','february':'02','mar':'03','march':'03','apr':'04','april':'04',
    'may':'05','jun':'06','june':'06','jul':'07','july':'07','aug':'08','august':'08','sep':'09','sept':'09','september':'09',
    'oct':'10','october':'10','nov':'11','november':'11','dec':'12','december':'12'
}

def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"

def _normalize(text: str) -> str:
    return unicodedata.normalize("NFKC", text)

def _normalize_lines(text: str) -> List[str]:
    text = _normalize(text)
    raw = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    return [ln.strip() for ln in raw]

def _detect_headings(line: str) -> Optional[str]:
    if not line: return None
    if HEADING_EXPERIENCE.match(line): return "experience"
    if HEADING_PROJECTS.match(line):   return "projects"
    if HEADING_SKILLS.match(line):     return "skills"
    if HEADING_EDUCATION.match(line):  return "education"
    return None

def _is_contact_line(ln: str) -> bool:
    low = ln.lower()
    return ('linkedin' in low) or ('portfolio' in low) or EMAIL_RE.search(ln) or URL_RE.search(ln)

def _extract_name(lines: List[str]) -> Optional[str]:
    checked = 0
    for ln in lines:
        if not ln: continue
        checked += 1
        if checked > 12: break
        parts: List[str] = []
        for piece in SEP_SPLIT.split(ln):
            parts += [p for p in re.split(r'\s{2,}', piece) if p.strip()]
        for part in parts or [ln]:
            cand = part.strip()
            if not cand: continue
            low = cand.lower()
            if any(x in low for x in ["http","linkedin","github","@"]): continue
            if "," in cand: continue
            w = cand.split()
            if not (2 <= len(w) <= 4): continue
            if NAME_CANDIDATE.match(cand): return cand
    return None

def _extract_links(text: str) -> List[str]:
    urls: List[str] = []
    seen = set()
    for u in URL_RE.findall(text):
        if u not in seen:
            urls.append(u); seen.add(u)
    for m in LINKEDIN_RE.finditer(text):
        path = m.group("path").strip()
        if path.startswith("/"):
            full = "https://www.linkedin.com" + path
        elif path.startswith("linkedin.com"):
            full = path if path.startswith("http") else "https://" + path
        else:
            full = path if path.startswith("http") else "https://" + path
        if full not in seen:
            urls.append(full); seen.add(full)
    return urls

def _to_yyyy_mm(m: str, y: Optional[str]) -> Optional[str]:
    k = (m or "").lower()
    if k in ('present','current','now'): return 'PRESENT'
    mm = MONTH_TO_NUM.get(k)
    return f"{y}-{mm}" if (mm and y) else None

def _parse_date_any(line: str) -> Tuple[Optional[str], Optional[str]]:
    m = DATE_RANGE_ANY.search(line)
    if not m: return None, None
    return _to_yyyy_mm(m.group('start_m'), m.group('start_y')), _to_yyyy_mm(m.group('end_m'), m.group('end_y'))

def _is_pure_date_line(line: str) -> Tuple[bool, Optional[str], Optional[str]]:
    m = DATE_RANGE_ONLY.match(line)
    if not m: return False, None, None
    return True, _to_yyyy_mm(m.group('start_m'), m.group('start_y')), _to_yyyy_mm(m.group('end_m'), m.group('end_y'))

def _split_header(line: str) -> List[str]:
    # Try " | " first
    if ' | ' in line:
        return [p.strip() for p in line.split(' | ') if p.strip()]
    # Then spaced dashes
    for pat in HEADER_SPLITS[1:]:
        if pat.search(line):
            return [p.strip() for p in pat.split(line) if p.strip()]
    return [line.strip()]

def _looks_like_job_header(parts: List[str]) -> bool:
    if len(parts) < 2 or len(parts) > 3:
        return False
    joined = " ".join(parts).lower()
    if 'http' in joined or 'linkedin' in joined or '@' in joined:
        return False
    for p in parts:
        if len(p.split()) > 10 or p.endswith('.'):
            return False
    hint = any(TITLE_HINT.search(p) for p in parts) or any(BIZ_HINT.search(p) for p in parts)
    return bool(hint)

def _guess_company_title(a: str, b: str) -> Tuple[str, str]:
    a_is_title = bool(TITLE_HINT.search(a))
    b_is_title = bool(TITLE_HINT.search(b))
    if a_is_title and not b_is_title: return b.strip(), a.strip()
    if b_is_title and not a_is_title: return a.strip(), b.strip()
    a_is_biz = bool(BIZ_HINT.search(a))
    b_is_biz = bool(BIZ_HINT.search(b))
    if a_is_biz and not b_is_biz: return a.strip(), b.strip()
    if b_is_biz and not a_is_biz: return b.strip(), a.strip()
    return a.strip(), b.strip()

def _split_skills_line(ln: str) -> List[str]:
    core = ln.split(':', 1)[-1].strip() if ':' in ln else ln
    return [p.strip() for p in SKILL_SPLIT.split(core) if p.strip()]

def _tag_skills(text: str, matcher: PhraseMatcher, alias_to_canonical: Dict[str,str]) -> List[str]:
    doc = _nlp(text)
    hits = matcher(doc)
    out, seen = [], set()
    for _, s, e in hits:
        alias = doc[s:e].text.lower()
        c = alias_to_canonical.get(alias)
        if c and c not in seen:
            out.append(c); seen.add(c)
    return out

def _line_to_canon_skills(ln: str, alias_to_canonical: Dict[str,str]) -> List[str]:
    parts = _split_skills_line(ln)
    hits: List[str] = []
    for p in parts:
        c = alias_to_canonical.get((p or "").lower())
        if c and c not in hits:
            hits.append(c)
    return hits

def _looks_like_project_header(line: str) -> bool:
    """Heuristics for lines like:
       'Quantra – Inventory Management App (for ...)'
       'WayPoint: Personalized Travel Planner App'
       'The Body Shop clone'
    """
    if not line or BULLET_LINE.match(line): return False
    if EMAIL_RE.search(line) or URL_RE.search(line): return False
    if line.endswith('.'): return False
    words = line.split()
    if len(words) > 14: return False
    # signals: contains ' – ' / ' — ' / ':' or words like App/Project/clone
    if (' – ' in line) or (' — ' in line) or (':' in line):
        return True
    if re.search(r'\b(App|Project|clone)\b', line, re.I):
        return True
    # Title-case ratio
    caps = sum(1 for w in words if w[:1].isupper())
    return (caps / max(len(words), 1)) >= 0.5

# ------------------------- File extraction -------------------------

def extract_text_from_pdf(file_bytes: bytes) -> str:
    return pdf_extract_text(io.BytesIO(file_bytes)) or ""

def extract_text_from_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)

# ------------------------------ Main --------------------------------

def parse_resume_bytes(file_bytes: bytes, filename: str,
                       matcher: PhraseMatcher, alias_to_canonical: Dict[str,str]):
    # 1) text
    ext = (filename or "").lower()
    if ext.endswith(".pdf"):
        text = extract_text_from_pdf(file_bytes)
    elif ext.endswith(".docx"):
        text = extract_text_from_docx(file_bytes)
    else:
        try:
            text = extract_text_from_pdf(file_bytes)
        except Exception:
            text = extract_text_from_docx(file_bytes)

    lines = _normalize_lines(text)

    # 2) basics
    name  = _extract_name(lines)
    email = EMAIL_RE.search(text).group(0) if EMAIL_RE.search(text) else None
    links = _extract_links(text)

    # 3) state
    current: Optional[str] = None
    skills_pool: List[str] = []
    education: List[str] = []

    experience_entries: List[dict] = []
    current_entry: Optional[dict] = None

    project_entries: List[dict] = []
    current_project: Optional[dict] = None  # {"name", "stack", "bullets"}

    # 4) walk
    for ln in lines:
        if not ln:
            # blank line: just continue; do not auto-close projects/experience
            continue

        # Skip obvious contact lines anywhere
        if _is_contact_line(ln):
            continue

        sec = _detect_headings(ln)
        if sec:
            # close open experience entry if leaving experience
            if current_entry and sec != "experience":
                experience_entries.append(current_entry); current_entry = None
            # close open project when leaving projects
            if current_project and sec != "projects":
                project_entries.append(current_project); current_project = None
            current = sec
            continue

        # If no section yet, try to detect first job header and switch to experience; else ignore
        if current is None:
            parts = _split_header(ln)
            if _looks_like_job_header(parts):
                current = "experience"
            else:
                continue

        # ---------------- EXPERIENCE ----------------
        if current == "experience":
            # pure date line
            pure, s, e = _is_pure_date_line(ln)
            if pure and current_entry:
                if s: current_entry["start"] = current_entry.get("start") or s
                if e: current_entry["end"]   = current_entry.get("end")   or e
                continue

            # header with separators
            parts = _split_header(ln)
            if _looks_like_job_header(parts):
                if current_entry:
                    experience_entries.append(current_entry)
                company, title = _guess_company_title(parts[0], parts[1])
                start, end = (None, None)
                if len(parts) >= 3:
                    s2, e2 = _parse_date_any(parts[2])
                    start, end = s2 or start, e2 or end
                current_entry = {
                    "company": company or None,
                    "title": title or None,
                    "start": start,
                    "end": end,
                    "stack": [],
                    "bullets": []
                }
                continue

            # stack / tech line for experience
            if current_entry:
                hits = _line_to_canon_skills(ln, alias_to_canonical)
                if len(hits) >= 2:
                    for c in hits:
                        if c not in current_entry["stack"]:
                            current_entry["stack"].append(c)
                    skills_pool.extend(hits)
                    continue

            # bullets (or VERB-leading)
            is_bullet = bool(BULLET_LINE.match(ln))
            if is_bullet or (_nlp(ln) and len(_nlp(ln)) > 0 and _nlp(ln)[0].pos_ == "VERB"):
                txt = BULLET_LINE.sub("", ln).strip() if is_bullet else ln.strip()
                if not current_entry:
                    current_entry = {"company": None, "title": None, "start": None, "end": None, "stack": [], "bullets": []}
                tags = _tag_skills(txt, matcher, alias_to_canonical)  # no stack inheritance
                current_entry["bullets"].append({"id": _gen_id("b"), "text": txt, "skills": tags})
                continue

        # ---------------- PROJECTS -----------------
        elif current == "projects":
            # 1) bullets under a project
            if BULLET_LINE.match(ln):
                txt = BULLET_LINE.sub("", ln).strip()
                if not current_project:
                    # open a generic project if bullets appear first
                    current_project = {"name": None, "stack": [], "bullets": []}
                tags = _tag_skills(txt, matcher, alias_to_canonical)  # only literal skills in bullet
                current_project["bullets"].append({"id": _gen_id("b"), "text": txt, "skills": tags})
                continue

            # 2) strong skills/stack line (>=2 known skills) → attach to current project
            hits = _line_to_canon_skills(ln, alias_to_canonical)
            if len(hits) >= 2:
                if not current_project:
                    # if stack appears before name, open unnamed project
                    current_project = {"name": None, "stack": [], "bullets": []}
                for c in hits:
                    if c not in current_project["stack"]:
                        current_project["stack"].append(c)
                skills_pool.extend(hits)
                continue

            # 3) project header line (name/title)
            if _looks_like_project_header(ln):
                if current_project:
                    project_entries.append(current_project)
                current_project = {"name": ln.strip(), "stack": [], "bullets": []}
                continue

            # 4) verb-leading line → treat as a bullet under current project (helps when bullets miss a bullet symbol)
            doc = _nlp(ln)
            if doc and len(doc) > 0 and doc[0].pos_ == "VERB":
                if not current_project:
                    current_project = {"name": None, "stack": [], "bullets": []}
                tags = _tag_skills(ln, matcher, alias_to_canonical)
                current_project["bullets"].append({"id": _gen_id("b"), "text": ln.strip(), "skills": tags})
                continue

        # ---------------- SKILLS -------------------
        elif current == "skills":
            skills_pool.extend(_split_skills_line(ln))

        # ---------------- EDUCATION ----------------
        elif current == "education":
            txt = ln.strip()
            # Strip any bullet-like prefix (• ● ◦ ▪ ‣ · * - – — or numbered lists)
            txt = BULLET_LINE.sub("", txt).strip()
            txt = re.sub(r'^[•●◦▪‣·*\-–—]+\s*', "", txt)
            if txt:
                education.append(txt)


    # close open entries
    if current_entry:
        experience_entries.append(current_entry)
    if current_project:
        project_entries.append(current_project)

    # skills de-dupe (preserve order)
    skill_set: List[str] = []
    seen = set()
    for s in skills_pool:
        alias = (s or "").lower()
        val = alias_to_canonical.get(alias) or s
        if val and val not in seen:
            skill_set.append(val); seen.add(val)

    resume_json = {
        "basics": {"name": name, "email": email, "links": links},
        "experience": experience_entries,
        "projects": project_entries,  # now a list of entries with name/stack/bullets
        "skills": skill_set,
        "education": education[:10],
    }
    return resume_json
