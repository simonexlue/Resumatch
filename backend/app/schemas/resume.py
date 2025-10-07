from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field

class Bullet(BaseModel):
    id: str
    text: str
    skills: List[str] = Field(default_factory=list)

class Basics(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    links: List[str] = Field(default_factory=list)

class ExperienceEntry(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None   # "YYYY-MM"
    end: Optional[str] = None     # "YYYY-MM" or "PRESENT"
    stack: List[str] = Field(default_factory=list)
    bullets: List[Bullet] = Field(default_factory=list)

class ProjectEntry(BaseModel):
    name: Optional[str] = None
    stack: List[str] = Field(default_factory=list)
    bullets: List[Bullet] = Field(default_factory=list)

class ResumeOut(BaseModel):
    basics: Basics
    experience: List[ExperienceEntry] = Field(default_factory=list)
    projects: List[ProjectEntry] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    education: List[str] = Field(default_factory=list)
