"""API for explicit, persistent discovery and accessibility preferences."""
from uuid import UUID
from fastapi import APIRouter, HTTPException
from app.schemas.preferences import StudentPreferences, StudentPreferencesUpdate
from app.services.preferences import StudentPreferencesRepository

router = APIRouter(prefix="/api/student-profiles", tags=["Student preferences"])

@router.get("/{profile_id}/preferences", response_model=StudentPreferences)
def read_preferences(profile_id: UUID) -> StudentPreferences:
    preferences = StudentPreferencesRepository().get(profile_id)
    if preferences is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return preferences

@router.put("/{profile_id}/preferences", response_model=StudentPreferences)
def update_preferences(profile_id: UUID, request: StudentPreferencesUpdate) -> StudentPreferences:
    try:
        preferences = StudentPreferencesRepository().save(profile_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if preferences is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return preferences
