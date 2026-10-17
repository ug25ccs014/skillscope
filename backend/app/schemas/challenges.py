"""Age-scaled challenge library and transparent scoring contracts."""
from __future__ import annotations
from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.privacy_validation import validate_user_text
from app.schemas.student_evidence import AgeBand, UserInterpretation

VERSION = "challenge-library-v1.0"

class ChallengeDomain(str, Enum):
    LOGIC_DATA = "logic_data"
    SCIENCE_RESEARCH = "science_research"
    TECHNOLOGY = "technology"
    DESIGN_CREATIVE = "design_creative"
    COMMUNICATION = "communication"
    HELPING_SOCIAL = "helping_social"
    BUSINESS = "business"
    HANDS_ON_SPATIAL = "hands_on_spatial"
    ENVIRONMENT = "environment"

class Difficulty(str, Enum):
    GENTLE = "gentle"
    STANDARD = "standard"
    STRETCH = "stretch"

class SafetyRating(str, Enum):
    LOW = "low"
    MEDIUM = "medium"

class EvidenceStatus(str, Enum):
    NOT_ENOUGH_EVIDENCE = "not_enough_evidence"
    PARTIAL = "partial_evidence"
    EVIDENCE_AVAILABLE = "evidence_available"

class RubricCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_id: str = Field(min_length=1, max_length=60)
    label: str = Field(min_length=1, max_length=160)
    observable_description: str = Field(min_length=1, max_length=500)
    score_scale: str = "0-2"
    max_score: int = Field(default=2, ge=1, le=5)

class AgeVariant(BaseModel):
    model_config = ConfigDict(extra="forbid")
    age_band: AgeBand
    title: str = Field(min_length=1, max_length=180)
    instructions: str = Field(min_length=1, max_length=3000)
    expected_output: str = Field(min_length=1, max_length=500)
    expected_minutes: int = Field(ge=3, le=45)
    materials: list[str] = Field(default_factory=list, max_length=12)
    accessibility_notes: list[str] = Field(default_factory=list, max_length=12)
    reflection_prompts: list[str] = Field(min_length=2, max_length=5)
    minimum_observed_criteria: int = Field(default=2, ge=1, le=10)

class Challenge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: str = Field(min_length=1, max_length=80)
    version: str = VERSION
    domain: ChallengeDomain
    skill_tags: list[str] = Field(min_length=1, max_length=8)
    difficulty: Difficulty
    safety_rating: SafetyRating
    content_origin: str = "skillscope_authored"
    source_reference: str | None = None
    rubric: list[RubricCriterion] = Field(min_length=1, max_length=8)
    age_variants: list[AgeVariant] = Field(min_length=3, max_length=3)

    @model_validator(mode="after")
    def validate_age_coverage(self) -> "Challenge":
        bands = {v.age_band for v in self.age_variants}
        required = set(AgeBand)
        if bands != required:
            raise ValueError("Every challenge must provide exactly one age-scaled variant for each age band.")
        ids = [c.criterion_id for c in self.rubric]
        if len(ids) != len(set(ids)):
            raise ValueError("Rubric criterion IDs must be unique within a challenge.")
        for variant in self.age_variants:
            if variant.minimum_observed_criteria > len(self.rubric):
                raise ValueError("minimum_observed_criteria cannot exceed rubric length.")
        return self

class RubricObservationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("observation", mode="before")
    @classmethod
    def prevent_contact_details(cls, value: object) -> object:
        return validate_user_text(value)

    criterion_id: str
    score: int | None = Field(default=None, ge=0, le=5)
    observation: str = Field(min_length=1, max_length=500)

class ChallengeSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    @field_validator("output", "reflection", mode="before")
    @classmethod
    def prevent_contact_details(cls, value: object) -> object:
        return validate_user_text(value)

    profile_id: UUID
    output: str = Field(min_length=1, max_length=5000)
    rubric_observations: list[RubricObservationInput] = Field(min_length=1, max_length=8)
    enjoyment: int | None = Field(default=None, ge=1, le=5)
    difficulty_reported: int | None = Field(default=None, ge=1, le=5)
    confidence: int | None = Field(default=None, ge=1, le=5)
    willingness_to_continue: int | None = Field(default=None, ge=1, le=5)
    reflection: str | None = Field(default=None, max_length=1500)
    hypothesis_interpretation: UserInterpretation = UserInterpretation.NOT_INTERPRETED

class CriterionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    criterion_id: str
    label: str
    score: int | None
    observation: str
    max_score: int

class ChallengeScoreResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    submission_id: UUID
    challenge_id: str
    challenge_version: str
    profile_id: UUID
    age_band: AgeBand
    evidence_status: EvidenceStatus
    observed_criteria: int
    required_observed_criteria: int
    objective_score: int | None
    objective_max_score: int | None
    criteria: list[CriterionResult]
    reflections_recorded: bool
    evidence_created_id: UUID | None
    explanation: str
    hypothesis_interpretation: UserInterpretation = UserInterpretation.NOT_INTERPRETED

class ChallengeListItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: str
    version: str
    domain: ChallengeDomain
    skill_tags: list[str]
    difficulty: Difficulty
    safety_rating: SafetyRating
    content_origin: str
    title: str
    expected_minutes: int
    age_band: AgeBand
