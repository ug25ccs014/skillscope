"""Exploratory, age-aware baseline assessment contracts.

This is an original SkillScope baseline, not a validated psychometric instrument.
"""
from __future__ import annotations
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.student_evidence import AgeBand
from app.schemas.privacy_validation import validate_user_text

class BaselineMode(str, Enum):
    DISCOVER_AND_SHAPE = "discover_and_shape"
    EXPLORE_AND_VALIDATE = "explore_and_validate"
    DEVELOP_AND_OPTIMIZE = "develop_and_optimize"

class BaselineItemType(str, Enum):
    SELF_REPORT = "self_report"
    MINI_ACTIVITY = "mini_activity"
    REFLECTION = "reflection"

class BaselineDomain(str, Enum):
    LOGIC_DATA = "logic_data"
    SCIENCE_RESEARCH = "science_research"
    TECHNOLOGY = "technology"
    DESIGN_CREATIVE = "design_creative"
    COMMUNICATION = "communication"
    HELPING_SOCIAL = "helping_social"
    BUSINESS = "business"
    HANDS_ON_SPATIAL = "hands_on_spatial"
    ENVIRONMENT = "environment"

class BaselineItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    item_id: str
    item_type: BaselineItemType
    domain: BaselineDomain
    prompt: str
    instructions: str | None = None
    options: list[str] = Field(default_factory=list, max_length=8)
    allow_skip: bool = True
    expected_minutes: int = Field(ge=1, le=10)
    age_bands: list[AgeBand] = Field(min_length=1)
    rubric: list[str] = Field(default_factory=list, max_length=5)

class BaselineAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment_id: UUID
    profile_id: UUID
    age_band: AgeBand
    mode: BaselineMode
    version: str
    notice: str
    items: list[BaselineItem]
    expected_minutes: int

class BaselineResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("answer", mode="before")
    @classmethod
    def prevent_contact_details(cls, value: object) -> object:
        return validate_user_text(value)

    item_id: str
    skipped: bool = False
    answer: str | None = Field(default=None, max_length=2000)
    confidence: int | None = Field(default=None, ge=1, le=5)

class BaselineSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment_id: UUID
    responses: list[BaselineResponse] = Field(min_length=1, max_length=20)

class BaselineDomainResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: BaselineDomain
    evidence_status: str
    response_count: int
    skipped_count: int
    confidence_observed: bool
    interpretation: str

class BaselineResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assessment_id: UUID
    profile_id: UUID
    age_band: AgeBand
    mode: BaselineMode
    version: str
    statement: str
    domain_results: list[BaselineDomainResult]
    evidence_created_count: int
    next_step: str
