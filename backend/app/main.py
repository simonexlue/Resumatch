from __future__ import annotations
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import settings
from .core.resources import init_resources

from .api.health import router as health_router
from .api.jd import router as jd_router
from .api.resume import router as resume_router
from .api.analyze import router as analyze_router

app = FastAPI(title="Resumatch API")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Startup: load NLP resources once
@app.on_event("startup")
def _startup():
    app.state.nlp_resources = init_resources()

# Routers
app.include_router(health_router)
app.include_router(jd_router)
app.include_router(resume_router)
app.include_router(analyze_router)
