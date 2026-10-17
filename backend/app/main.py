"""SkillScope API entrypoint for health and age-aware entry calibration."""

from __future__ import annotations

import os
import logging
import sqlite3
import uuid
from contextlib import asynccontextmanager
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
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
from app.api.preferences import router as preferences_router
from app.api.system import router as system_router
from app.api.source_registry import router as source_registry_router
from app.services.database import initialize_database

APP_VERSION = "0.1.0"
APP_ENV = os.getenv("SKILLSCOPE_ENV", "development")
logger = logging.getLogger("skillscope.api")

# The prototype deliberately fails closed for student-data routes in production. It has no
# authenticated identity or ownership model yet; a profile UUID alone is not authorization.
_PRIVATE_DATA_PREFIXES = (
    "/api/student-profiles",
    "/api/baseline-assessments",
    "/api/discovery-loop",
    "/api/recommendations",
    "/api/pathway-plans",
    "/api/calibration",
)


def _requires_student_data_gate(path: str) -> bool:
    if any(path == prefix or path.startswith(prefix + "/") for prefix in _PRIVATE_DATA_PREFIXES):
        return True
    return path.startswith("/api/challenges/") and path.endswith("/submissions")


def _safe_route_for_log(request: Request) -> str:
    """Return a route template where available; otherwise redact profile-like identifiers."""
    route = request.scope.get("route")
    template = getattr(route, "path", None)
    if isinstance(template, str):
        return template
    path = request.url.path
    parts = path.split("/")
    if len(parts) > 3 and parts[1:3] == ["api", "student-profiles"]:
        parts[3] = "{profile_id}"
        return "/".join(parts)
    if len(parts) > 3 and parts[1:3] in (["api", "recommendations"], ["api", "pathway-plans"], ["api", "discovery-loop"]):
        parts[3] = "{profile_id}"
        return "/".join(parts)
    return path


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Initialize persistent schema and optional synthetic fixtures before serving requests."""
    try:
        application.state.database_bootstrap = initialize_database()
    except Exception as exc:
        # Keep health diagnosable without writing exception contents or user data to app logs.
        logger.error("Database bootstrap failed; starting in degraded mode (exception_type=%s).", type(exc).__name__)
        application.state.database_bootstrap = {"status": "degraded"}
    yield


def _allowed_origins() -> list[str]:
    environment = os.getenv("SKILLSCOPE_ENV", "development").strip().casefold()
    configured = os.getenv("CORS_ORIGINS")
    if environment == "production":
        # Production must explicitly provide HTTPS origins. The wildcard and development
        # origins are never silently carried into a production deployment.
        if not configured:
            return []
        origins = [origin.strip() for origin in configured.split(",") if origin.strip()]
        if not origins:
            return []
        valid: list[str] = []
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme != "https" or not parsed.netloc or parsed.path not in {"", "/"} or parsed.query or parsed.fragment or parsed.username or parsed.password or origin == "*":
                return []
            valid.append(f"https://{parsed.netloc}")
        return list(dict.fromkeys(valid))
    raw_origins = configured or "http://localhost:5173,http://127.0.0.1:5173"
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]


app = FastAPI(
    title="SkillScope API",
    description="Backend API for age-aware calibration, provenance, source-traceable career discovery, consent-aware student evidence, and explainable recommendations, and age-aware pathway plans.",
    version=APP_VERSION,
    lifespan=lifespan,
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
app.include_router(preferences_router)
app.include_router(system_router)
app.include_router(source_registry_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


@app.middleware("http")
async def request_id_and_privacy_middleware(request: Request, call_next):
    """Add safe response headers and fail closed for private prototype routes in production."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    path = request.url.path
    environment = os.getenv("SKILLSCOPE_ENV", "development").strip().casefold()
    if environment == "production" and _requires_student_data_gate(path):
        response = JSONResponse(status_code=503, content={
            "detail": "Student-data features are disabled in this prototype's production mode until authenticated identity, per-profile authorization, and verified consent are implemented.",
            "request_id": request_id,
        })
    else:
        response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if path.startswith("/api/") or path in {"/health", "/api/health"}:
        response.headers.setdefault("Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'; base-uri 'none'")
    if _requires_student_data_gate(path):
        response.headers["Cache-Control"] = "no-store, max-age=0"
        response.headers["Pragma"] = "no-cache"
    return response




@app.exception_handler(RequestValidationError)
async def request_validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return useful field errors without echoing submitted values into response payloads."""
    request_id = getattr(request.state, "request_id", "unavailable")
    route = _safe_route_for_log(request)
    errors = [
        {
            "type": str(item.get("type", "value_error")),
            "loc": list(item.get("loc", ())),
            "msg": str(item.get("msg", "Input validation failed.")),
        }
        for item in exc.errors()
    ]
    logger.warning("Request validation failed request_id=%s route=%s error_count=%s", request_id, route, len(errors))
    return JSONResponse(status_code=422, content={"detail": errors, "request_id": request_id}, headers={"X-Request-ID": request_id})


@app.exception_handler(sqlite3.Error)
async def sqlite_error_handler(request: Request, exc: sqlite3.Error) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unavailable")
    logger.error("Persistence error request_id=%s route=%s exception_type=%s", request_id, _safe_route_for_log(request), type(exc).__name__)
    return JSONResponse(status_code=503, content={
        "detail": "Persistent storage is temporarily unavailable. Please retry.",
        "request_id": request_id,
    }, headers={"X-Request-ID": request_id})


@app.exception_handler(Exception)
async def unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", "unavailable")
    logger.error("Unhandled API error request_id=%s route=%s exception_type=%s", request_id, _safe_route_for_log(request), type(exc).__name__)
    return JSONResponse(status_code=500, content={
        "detail": "An unexpected server error occurred. Retry and provide the request reference to the administrator.",
        "request_id": request_id,
    }, headers={"X-Request-ID": request_id})


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
