"""Explainable career-hypothesis and evidence-confidence API."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.recommendations import RecommendationSet
from app.services.recommendations import RecommendationCatalogError, RecommendationRepository

router = APIRouter(prefix="/api/recommendations", tags=["Transparent career recommendations"])


def repo() -> RecommendationRepository:
    return RecommendationRepository()


@router.get("/{profile_id}", response_model=RecommendationSet)
def read_recommendations(
    profile_id: UUID,
    limit: int = Query(default=5, ge=1, le=10),
) -> RecommendationSet:
    """Return traceable hypothesis categories, confidence rationale, source facts and a validation task."""
    repository = repo()
    try:
        result = repository.get_recommendations(profile_id, limit=limit)
    except RecommendationCatalogError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except (ValueError, OSError) as exc:
        # Policy corruption should fail visibly instead of emitting untraceable recommendations.
        raise HTTPException(status_code=503, detail=f"Recommendation policy or source graph is unavailable: {str(exc)[:500]}") from exc
    if result is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return result
