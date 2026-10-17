"""Operational persistence diagnostics with no filesystem path or sensitive profile data."""
from fastapi import APIRouter
from app.services.database import database_status

router = APIRouter(prefix="/api/system", tags=["System diagnostics"])

@router.get("/persistence")
def persistence_status() -> dict[str, object]:
    """Expose schema and synthetic-fixture status without revealing the resolved local path."""
    return database_status()
