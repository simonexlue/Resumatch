from __future__ import annotations
import os
import spacy
from spacy.matcher import PhraseMatcher
from fastapi import Request
from typing import Dict, Tuple

from ..nlp.jd_parser import load_skills_dict

class NLPResources:
    def __init__(self, skills_csv_path: str):
        self.nlp = spacy.load("en_core_web_sm")
        # reuse CSV loader
        skills_map, alias_to_canonical, matcher = load_skills_dict(skills_csv_path)
        self.skills_map: Dict = skills_map
        self.alias_to_canonical: Dict[str, str] = alias_to_canonical
        self.matcher: PhraseMatcher = matcher

def init_resources() -> NLPResources:
    here = os.path.dirname(os.path.dirname(__file__))  # backend/app
    skills_csv = os.path.join(here, "nlp", "skills_dict.csv")
    return NLPResources(skills_csv_path=skills_csv)

def get_resources(request: Request) -> NLPResources:
    # access from app.state (set in main.py startup)
    return request.app.state.nlp_resources
