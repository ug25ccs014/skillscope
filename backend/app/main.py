"""SkillScope API entrypoint for health and age-aware entry calibration."""

from __future__ import annotations

import os
from typing import Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.api.calibration import router as calibration_router
from app.api.ingestion import router as ingestion_router
from app.api.knowledge_graph import router as knowledge_graph_router
from app.api.provenance import router as provenance_router
from app.api.student_evidence import router as student_evidence_router
from app.api.baseline_assessment import router as baseline_assessment_router
from app.api.challenges import router as challenges_router
from app.api.discovery_loop import router as discovery_loop_router
from app.api.recommendations import router as recommendations_router
from app.api.pathway_plans import router as pathway_plans_router

APP_VERSION = "0.1.0"
APP_ENV = os.getenv("SKILLSCOPE_ENV", "development")


def _allowed_origins() -> list[str]:
    raw_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app = FastAPI(
    title="SkillScope API",
    description="Backend API for age-aware calibration, provenance, source-traceable career discovery, consent-aware student evidence, and explainable recommendations, and age-aware pathway plans.",
    version=APP_VERSION,
    docs_url="/docs" if APP_ENV != "production" else None,
    redoc_url="/redoc" if APP_ENV != "production" else None,
)

app.include_router(calibration_router)
app.include_router(provenance_router)
app.include_router(ingestion_router)
app.include_router(knowledge_graph_router)
app.include_router(student_evidence_router)
app.include_router(baseline_assessment_router)
app.include_router(challenges_router)
app.include_router(discovery_loop_router)
app.include_router(recommendations_router)
app.include_router(pathway_plans_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: str
    version: str
    environment: str


@app.get("/health", tags=["Operations"])
def health() -> dict[str, str]:
    """Simple infrastructure health check; does not imply data-source readiness."""
    return {"status": "ok", "service": "skillscope-api", "version": APP_VERSION}


@app.get("/api/health", response_model=HealthResponse, tags=["Operations"])
def api_health() -> HealthResponse:
    """API contract used by the frontend shell to check connectivity."""
    return HealthResponse(
        status="ok",
        service="skillscope-api",
        version=APP_VERSION,
        environment=APP_ENV,
    )
