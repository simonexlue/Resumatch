from fastapi import APIRouter, Body, Depends
from ..core.resources import get_resources, NLPResources
from ..schemas.jd import ParseJdRequest, ParsedJD
from ..nlp.jd_parser import parse_job_description

router = APIRouter()

@router.post("/parse-jd", response_model=ParsedJD)
def parse_jd(payload: ParseJdRequest, res: NLPResources = Depends(get_resources)):
    result = parse_job_description(payload.raw_text, res.skills_map, res.alias_to_canonical, res.matcher)
    return ParsedJD(**result)

@router.post("/parse-jd-text", response_model=ParsedJD)
def parse_jd_text(raw_text: str = Body(..., media_type="text/plain"),
                  res: NLPResources = Depends(get_resources)):
    result = parse_job_description(raw_text, res.skills_map, res.alias_to_canonical, res.matcher)
    return ParsedJD(**result)
