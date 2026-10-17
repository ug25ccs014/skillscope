from uuid import UUID
from fastapi import APIRouter, HTTPException, status
from app.schemas.baseline_assessment import BaselineAssessment, BaselineResult, BaselineSubmission
from app.services.baseline_assessment import BaselineAssessmentRepository
router=APIRouter(prefix="/api/baseline-assessments", tags=["Baseline assessment"])
def repo(): return BaselineAssessmentRepository()
@router.post("/for/{profile_id}", response_model=BaselineAssessment, status_code=status.HTTP_201_CREATED)
def issue(profile_id: UUID):
    try: return repo().create(profile_id)
    except KeyError: raise HTTPException(404, "Student profile not found.")
@router.post("/submit", response_model=BaselineResult)
def submit(request: BaselineSubmission):
    try: return repo().submit(request)
    except KeyError: raise HTTPException(404, "Baseline assessment or student profile not found.")
    except ValueError as exc: raise HTTPException(422, str(exc))
