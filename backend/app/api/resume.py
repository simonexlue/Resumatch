from __future__ import annotations

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends

from ..core.resources import NLPResources, get_resources
from ..schemas.resume import ResumeOut
from ..nlp.resume_parser import parse_resume_bytes

router = APIRouter()

@router.post("/resume/ingest", response_model=ResumeOut)
async def resume_ingest(
    file: UploadFile = File(...),
    res: NLPResources = Depends(get_resources),
):
    try:
        data = await file.read()
        result = parse_resume_bytes(
            file_bytes=data,
            filename=file.filename or "",
            matcher=res.matcher,
            alias_to_canonical=res.alias_to_canonical,
        )
        return ResumeOut(**result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse resume: {e}")
