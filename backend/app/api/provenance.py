"""Provenance API: expose traceability without exposing raw source dumps."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.services.provenance import ProvenanceRepository

router = APIRouter(prefix="/api/provenance", tags=["Provenance"])


@router.get("/status")
def provenance_status() -> dict[str, object]:
    """Return registry counts and make clear whether external data is present."""
    repository = ProvenanceRepository()
    counts = repository.count()
    by_type = repository.source_type_counts()
    external_official_records = by_type.get("official", 0)
    curated_extract_records = by_type.get("curated_extract", 0)
    return {
        "status": "ready",
        "external_data_integrated": external_official_records > 0,
        "curated_extract_records_present": curated_extract_records > 0,
        "source_records_by_type": by_type,
        "counts": counts,
        "note": (
            "Curated extracts are versioned demonstration records, not a live feed or complete dataset. "
            "Official records appear only after a source file is imported successfully."
        ),
    }


@router.get("/career-facts/{fact_id}")
def career_fact(fact_id: str):
    fact = ProvenanceRepository().get_career_fact(fact_id)
    if fact is None:
        raise HTTPException(status_code=404, detail="Career fact not found.")
    return fact
