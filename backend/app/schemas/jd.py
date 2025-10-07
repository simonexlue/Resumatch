from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel

class ParseJdRequest(BaseModel):
    raw_text: str

class Requirement(BaseModel):
    skill: str
    priority: Literal["must", "nice"]

class ParsedJD(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    seniority: Optional[str] = None
    requirements: List[Requirement] = []
    responsibilities: List[str] = []