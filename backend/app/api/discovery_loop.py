"""Read the current persisted-state-driven discovery recommendation."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.discovery_loop import DiscoveryLoopState, LoopPreference
from app.services.discovery_loop import DiscoveryLoopRepository

router = APIRouter(prefix="/api/discovery-loop", tags=["Longitudinal discovery loop"])


def repo() -> DiscoveryLoopRepository:
    return DiscoveryLoopRepository()


@router.get("/{profile_id}", response_model=DiscoveryLoopState)
def read_discovery_loop(
    profile_id: UUID,
    preference: LoopPreference = Query(default=LoopPreference.BALANCED),
) -> DiscoveryLoopState:
    """Return a deterministic next task derived from this profile's saved activity/evidence."""
    state = repo().get_state(profile_id, preference)
    if state is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return state
