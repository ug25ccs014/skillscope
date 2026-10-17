"""HTTP route for SkillScope entry calibration."""

from fastapi import APIRouter

from app.schemas.calibration import CalibrationRequest, CalibrationResponse
from app.services.entry_calibration import calibrate_entry

router = APIRouter(prefix="/api", tags=["Entry calibration"])


@router.post("/calibration", response_model=CalibrationResponse)
def create_entry_calibration(request: CalibrationRequest) -> CalibrationResponse:
    """Choose an appropriate starting journey from self-reported inputs.

    This endpoint is stateless: it returns a calibration for this request only
    and does not create or persist a student profile.
    """
    return calibrate_entry(request)
