"""Read the current persisted-state-driven discovery recommendation."""
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from app.schemas.discovery_loop import DiscoveryLoopState, LoopPreference
from app.services.discovery_loop import DiscoveryLoopRepository
from app.services.preferences import StudentPreferencesRepository

router = APIRouter(prefix="/api/discovery-loop", tags=["Longitudinal discovery loop"])


def repo() -> DiscoveryLoopRepository:
    return DiscoveryLoopRepository()


@router.get("/{profile_id}", response_model=DiscoveryLoopState)
def read_discovery_loop(
    profile_id: UUID,
    preference: LoopPreference | None = Query(default=None),
) -> DiscoveryLoopState:
    """Return a deterministic next task; saved preferences apply unless explicitly overridden."""
    selected_preference = preference
    if selected_preference is None:
        selected = StudentPreferencesRepository().get(profile_id)
        selected_preference = selected.journey_preference if selected is not None else LoopPreference.BALANCED
    state = repo().get_state(profile_id, selected_preference)
    if state is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return state
