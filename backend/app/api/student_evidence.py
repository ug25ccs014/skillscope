"""Consent-aware student profile and evidence-ledger API.

The current MVP is unauthenticated. Do not deploy these routes for real student records until
identity/authorization, deployment security and operational retention controls are added.
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Response, status
from pydantic import ValidationError

from app.schemas.student_evidence import (
    EvidenceCreate,
    EvidenceItem,
    EvidenceType,
    EvidenceUpdate,
    SignalDimension,
    StudentProfile,
    StudentProfileCreate,
    StudentProfileSummary,
    StudentProfileUpdate,
)
from app.services.evidence_ledger import EvidenceLedgerRepository

router = APIRouter(prefix="/api/student-profiles", tags=["Student evidence ledger"])


def get_repository() -> EvidenceLedgerRepository:
    """Factory kept replaceable in tests; the database path matches the rest of the MVP."""
    return EvidenceLedgerRepository()


def _profile_or_404(repo: EvidenceLedgerRepository, profile_id: UUID) -> StudentProfile:
    profile = repo.get_profile(profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return profile


@router.post("", response_model=StudentProfile, status_code=status.HTTP_201_CREATED)
def create_student_profile(request: StudentProfileCreate) -> StudentProfile:
    """Create a profile only after age-appropriate consent has been confirmed."""
    try:
        return get_repository().create_profile(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{profile_id}", response_model=StudentProfile)
def read_student_profile(profile_id: UUID) -> StudentProfile:
    return _profile_or_404(get_repository(), profile_id)


@router.patch("/{profile_id}", response_model=StudentProfile)
def correct_student_profile(profile_id: UUID, request: StudentProfileUpdate) -> StudentProfile:
    """Correct stated goal/context. Age-band corrections require renewed, appropriate consent."""
    repo = get_repository()
    try:
        profile = repo.update_profile(profile_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if profile is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return profile


@router.get("/{profile_id}/evidence", response_model=dict[str, object])
def list_student_evidence(
    profile_id: UUID,
    signal_dimension: SignalDimension | None = None,
    evidence_type: EvidenceType | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0, le=100_000),
) -> dict[str, object]:
    repo = get_repository()
    _profile_or_404(repo, profile_id)
    items, count = repo.list_evidence(
        profile_id, signal_dimension=signal_dimension, evidence_type=evidence_type, limit=limit, offset=offset
    )
    return {"items": [item.model_dump(mode="json") for item in items], "count": count, "limit": limit, "offset": offset}


@router.post("/{profile_id}/evidence", response_model=EvidenceItem, status_code=status.HTTP_201_CREATED)
def add_student_evidence(profile_id: UUID, request: EvidenceCreate) -> EvidenceItem:
    repo = get_repository()
    _profile_or_404(repo, profile_id)
    try:
        return repo.add_evidence(profile_id, request)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Student profile not found.") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.patch("/{profile_id}/evidence/{evidence_id}", response_model=EvidenceItem)
def correct_student_evidence(profile_id: UUID, evidence_id: UUID, request: EvidenceUpdate) -> EvidenceItem:
    """Correct a record in place while retaining its original recorded_at timestamp."""
    repo = get_repository()
    try:
        item = repo.update_evidence(profile_id, evidence_id, request)
    except (ValueError, ValidationError) as exc:
        message = str(exc)
        raise HTTPException(status_code=422, detail=message[:1000]) from exc
    if item is None:
        raise HTTPException(status_code=404, detail="Evidence item not found in this student profile.")
    return item


@router.delete("/{profile_id}/evidence/{evidence_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_student_evidence(profile_id: UUID, evidence_id: UUID) -> Response:
    repo = get_repository()
    _profile_or_404(repo, profile_id)
    if not repo.delete_evidence(profile_id, evidence_id):
        raise HTTPException(status_code=404, detail="Evidence item not found in this student profile.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{profile_id}/summary", response_model=StudentProfileSummary)
def summarize_student_profile(profile_id: UUID) -> StudentProfileSummary:
    summary = get_repository().profile_summary(profile_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return summary


@router.delete("/{profile_id}/evidence")
def clear_student_evidence(profile_id: UUID) -> dict[str, object]:
    """Permanently delete all ledger items while retaining the consented empty profile."""
    deleted = get_repository().clear_evidence(profile_id)
    if deleted is None:
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return {"deleted_count": deleted, "profile_retained": True, "deletion": "permanent"}


@router.delete("/{profile_id}")
def delete_student_profile(profile_id: UUID) -> dict[str, object]:
    """Permanently delete a profile and all evidence through the database cascade."""
    repo = get_repository()
    if not repo.delete_profile(profile_id):
        raise HTTPException(status_code=404, detail="Student profile not found.")
    return {"deleted": True, "profile_id": str(profile_id), "evidence_deleted_by_cascade": True, "deletion": "permanent"}
