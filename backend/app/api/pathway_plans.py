"""Generate, retrieve, and revise persistent stage-aware pathway plans."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.pathway_plans import PathwayPlan, PathwayPlanHistoryItem, PlanInput
from app.services.pathway_plans import PathwayPlanRepository
from app.services.recommendations import RecommendationCatalogError

router = APIRouter(prefix="/api/pathway-plans", tags=["Career pathway and action plans"])


def repo() -> PathwayPlanRepository:
    return PathwayPlanRepository()


@router.post("/{profile_id}/generate", response_model=PathwayPlan, status_code=status.HTTP_201_CREATED)
def generate_pathway_plan(profile_id: UUID, request: PlanInput) -> PathwayPlan:
    """Create a new plan snapshot. Supplying current_goal edits the saved goal and preserves goal history."""
    try:
        plan = repo().generate(profile_id, request)
    except RecommendationCatalogError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)[:1000]) from exc
    except OSError as exc:
        raise HTTPException(status_code=503, detail="Pathway planning storage or source data is unavailable.") from exc
    if plan is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return plan


@router.get("/{profile_id}", response_model=PathwayPlan)
def latest_pathway_plan(profile_id: UUID) -> PathwayPlan:
    repository = repo()
    plan = repository.get_latest(profile_id)
    if plan is None:
        # Use the same database configured for this repository (important for tests and local
        # deployments with a non-default DB path).
        if repository.evidence.get_profile(profile_id) is None:
            raise HTTPException(status_code=404, detail="Student profile not found.")
        raise HTTPException(status_code=404, detail="No pathway plan has been generated for this profile yet.")
    return plan


@router.get("/{profile_id}/history", response_model=list[PathwayPlanHistoryItem])
def pathway_plan_history(
    profile_id: UUID,
    limit: int = Query(default=20, ge=1, le=100),
) -> list[PathwayPlanHistoryItem]:
    history = repo().history(profile_id, limit=limit)
    if history is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return history
