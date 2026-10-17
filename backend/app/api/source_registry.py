"""Read-only, student-facing source catalogue and discrepancy audit."""
from fastapi import APIRouter, HTTPException

from app.schemas.source_registry import SourceRegistryResponse
from app.services.source_registry import SourceRegistryError, get_source_registry

router = APIRouter(prefix="/api/source-registry", tags=["Source audit"])


@router.get("", response_model=SourceRegistryResponse)
def read_source_registry() -> SourceRegistryResponse:
    """Return publisher, version, sync status, limitations, conflicts and mapping uncertainty."""
    try:
        return SourceRegistryResponse.model_validate(get_source_registry())
    except SourceRegistryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail="Source audit metadata could not be validated.") from exc
