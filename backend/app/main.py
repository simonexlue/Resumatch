from typing import Literal, List, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .nlp.jd_parser import load_skills_dict, parse_job_description
import os
from fastapi import Body

app = FastAPI(title="Resumatch API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load skills dict and matcher once on startup
SKILLS_CSV = os.path.join(os.path.dirname(__file__), "nlp", "skills_dict.csv")
SKILLS_MAP, ALIAS_TO_CANONICAL, MATCHER = load_skills_dict(SKILLS_CSV)

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

@app.get("/health")
def heath():
    return {"ok": True}

@app.post("/parse-jd", response_model=ParsedJD)
def parse_jd(payload: ParseJdRequest):
    result = parse_job_description(payload.raw_text, SKILLS_MAP, ALIAS_TO_CANONICAL, MATCHER)
    return ParsedJD(**result)

@app.post("/parse-jd-text", response_model=ParsedJD)
def parse_jd_text(raw_text: str = Body(..., media_type="text/plain")):
    result = parse_job_description(raw_text, SKILLS_MAP, ALIAS_TO_CANONICAL, MATCHER)
    return ParsedJD(**result)