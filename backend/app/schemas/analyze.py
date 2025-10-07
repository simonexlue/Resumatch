from __future__ import annotations
from typing import List, Literal
from pydantic import BaseModel

from .jd import ParsedJD
from .resume import ResumeOut

class MatchLocation(BaseModel):
    bullets: List[str] = []
    skills_section: bool = False

class MatchResult(BaseModel):
    term: str
    priority: Literal["must", "nice"]
    found: bool
    locations: MatchLocation

class AnalyzeRequest(BaseModel):
    jd: ParsedJD
    resume: ResumeOut
    count_skills_section: bool = True

class AnalyzeOut(BaseModel):
    results: List[MatchResult]
    coverage_pct: float
    must_found: int
    must_total: int
    nice_found: int
    nice_total: int