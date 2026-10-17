"""Contracts for consent-aware, longitudinal student evidence.

Evidence is append-oriented and contextual. It is never collapsed into a single ability,
aptitude, personality or career-fit score.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator


class AgeBand(str, Enum):
    AGE_10_14 = "10_14"
    AGE_15_17 = "15_17"
    AGE_18_PLUS = "18_plus"


class ConsentBasis(str, Enum):
    STUDENT_CONFIRMED = "student_confirmed"
    GUARDIAN_CONFIRMED = "guardian_confirmed"


class EvidenceType(str, Enum):
    STATED_INTEREST_GOAL = "stated_interest_goal"
    ACTIVITY_REFLECTION = "activity_reflection"
    CHALLENGE_PERFORMANCE = "challenge_performance"
    EFFORT_DIFFICULTY = "effort_difficulty"
    PROJECT_PORTFOLIO = "project_portfolio"
    ACADEMIC_EXPERIENCE = "academic_experience"
    REPEATED_IN_PRODUCT_BEHAVIOR = "repeated_in_product_behavior"


class SignalDimension(str, Enum):
    INTEREST = "interest"
    DEMONSTRATED_PERFORMANCE = "demonstrated_performance"
    EXPERIENCE_EXPOSURE = "experience_exposure"
    LEARNING_PROGRESS = "learning_progress"
    GOAL_PREFERENCE = "goal_preference"
    PRACTICAL_READINESS = "practical_readiness"
    EFFORT_DIFFICULTY = "effort_difficulty"


class EvidenceSourceKind(str, Enum):
    SELF_REPORT = "self_report"
    CHALLENGE_RESULT = "challenge_result"
    USER_ADDED_PROJECT = "user_added_project"
    ACADEMIC_SELF_REPORT = "academic_self_report"
    IN_PRODUCT_BEHAVIOR = "in_product_behavior"


class UncertaintyLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    NOT_ASSESSED = "not_assessed"


class UserInterpretation(str, Enum):
    SUPPORTS_CURRENT_HYPOTHESIS = "supports_current_hypothesis"
    CHALLENGES_CURRENT_HYPOTHESIS = "challenges_current_hypothesis"
    CONTEXTUAL_OR_MIXED = "contextual_or_mixed"
    NOT_INTERPRETED = "not_interpreted"


class RubricObservation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    criterion: str = Field(min_length=1, max_length=120)
    observation: str = Field(min_length=1, max_length=500)
    score: float | None = Field(default=None, ge=-1_000_000, le=1_000_000)
    score_scale: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def score_requires_scale(self) -> "RubricObservation":
        if self.score is not None and not self.score_scale:
            raise ValueError("A rubric score must identify its original score_scale; scores from different rubrics are not comparable by default.")
        if self.score is None and self.score_scale is not None:
            raise ValueError("score_scale is only valid when a numeric score is supplied.")
        return self


class StudentProfileCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_band: AgeBand
    consent_basis: ConsentBasis
    consent_confirmed: bool
    current_goal: str | None = Field(default=None, max_length=500)
    self_reported_context: str | None = Field(default=None, max_length=1500)

    @model_validator(mode="after")
    def require_age_appropriate_consent(self) -> "StudentProfileCreate":
        if not self.consent_confirmed:
            raise ValueError("Evidence storage requires explicit consent confirmation.")
        if self.age_band in {AgeBand.AGE_10_14, AgeBand.AGE_15_17} and self.consent_basis != ConsentBasis.GUARDIAN_CONFIRMED:
            raise ValueError("For student profiles under 18, the MVP requires confirmation that appropriate guardian consent has been obtained.")
        if self.age_band == AgeBand.AGE_18_PLUS and self.consent_basis != ConsentBasis.STUDENT_CONFIRMED:
            raise ValueError("For adult profiles, consent must be confirmed by the student.")
        return self


class StudentProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age_band: AgeBand | None = None
    consent_basis: ConsentBasis | None = None
    consent_confirmed: bool | None = None
    current_goal: str | None = Field(default=None, max_length=500)
    self_reported_context: str | None = Field(default=None, max_length=1500)


class StudentProfile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: UUID
    age_band: AgeBand
    consent_basis: ConsentBasis
    consent_confirmed_at: datetime
    current_goal: str | None
    self_reported_context: str | None
    created_at: datetime
    updated_at: datetime
    consent_notice_version: str = "student-evidence-v1.0"


class EvidenceCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_type: EvidenceType
    signal_dimension: SignalDimension
    title: str = Field(min_length=1, max_length=160)
    observation: str = Field(min_length=1, max_length=2400)
    domain: str | None = Field(default=None, max_length=100, description="Student-entered domain/context label, not an official taxonomy.")
    source_kind: EvidenceSourceKind
    source_reference: HttpUrl | None = None
    behavior_consent_confirmed: bool = False
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC).replace(microsecond=0))
    uncertainty: UncertaintyLevel = UncertaintyLevel.NOT_ASSESSED
    user_interpretation: UserInterpretation = UserInterpretation.NOT_INTERPRETED
    challenge_label: str | None = Field(default=None, max_length=160)
    rubric_name: str | None = Field(default=None, max_length=160)
    rubric_version: str | None = Field(default=None, max_length=80)
    rubric_observations: list[RubricObservation] = Field(default_factory=list, max_length=20)
    reported_enjoyment: int | None = Field(default=None, ge=1, le=5)
    reported_curiosity: int | None = Field(default=None, ge=1, le=5)
    reported_effort: int | None = Field(default=None, ge=1, le=5)
    reported_difficulty: int | None = Field(default=None, ge=1, le=5)
    context: dict[str, str | int | float | bool | None] = Field(default_factory=dict)

    @field_validator("observed_at")
    @classmethod
    def timestamp_must_have_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone.")
        if value.astimezone(UTC) > datetime.now(UTC) + timedelta(seconds=5):
            raise ValueError("observed_at cannot be in the future.")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_evidence_context(self) -> "EvidenceCreate":
        valid_dimensions: dict[EvidenceType, set[SignalDimension]] = {
            EvidenceType.STATED_INTEREST_GOAL: {SignalDimension.INTEREST, SignalDimension.GOAL_PREFERENCE},
            EvidenceType.ACTIVITY_REFLECTION: {SignalDimension.INTEREST, SignalDimension.LEARNING_PROGRESS, SignalDimension.EFFORT_DIFFICULTY},
            EvidenceType.CHALLENGE_PERFORMANCE: {SignalDimension.DEMONSTRATED_PERFORMANCE, SignalDimension.LEARNING_PROGRESS, SignalDimension.PRACTICAL_READINESS},
            EvidenceType.EFFORT_DIFFICULTY: {SignalDimension.EFFORT_DIFFICULTY, SignalDimension.LEARNING_PROGRESS, SignalDimension.INTEREST},
            EvidenceType.PROJECT_PORTFOLIO: {SignalDimension.EXPERIENCE_EXPOSURE, SignalDimension.DEMONSTRATED_PERFORMANCE, SignalDimension.PRACTICAL_READINESS, SignalDimension.LEARNING_PROGRESS},
            EvidenceType.ACADEMIC_EXPERIENCE: {SignalDimension.EXPERIENCE_EXPOSURE, SignalDimension.DEMONSTRATED_PERFORMANCE, SignalDimension.LEARNING_PROGRESS, SignalDimension.PRACTICAL_READINESS},
            EvidenceType.REPEATED_IN_PRODUCT_BEHAVIOR: {SignalDimension.INTEREST, SignalDimension.LEARNING_PROGRESS, SignalDimension.EXPERIENCE_EXPOSURE},
        }
        if self.signal_dimension not in valid_dimensions[self.evidence_type]:
            raise ValueError("This evidence type cannot be assigned to that signal dimension; preserve the distinction between what was observed and what it may mean.")
        if self.evidence_type == EvidenceType.CHALLENGE_PERFORMANCE:
            if not self.challenge_label or not self.rubric_name or not self.rubric_observations:
                raise ValueError("Challenge performance must include the challenge label, rubric name, and at least one criterion-level observation.")
            if self.source_kind != EvidenceSourceKind.CHALLENGE_RESULT:
                raise ValueError("Challenge performance must use source_kind='challenge_result'.")
        if self.evidence_type == EvidenceType.PROJECT_PORTFOLIO and self.source_kind != EvidenceSourceKind.USER_ADDED_PROJECT:
            raise ValueError("Project/portfolio evidence must use source_kind='user_added_project'.")
        if self.evidence_type == EvidenceType.ACADEMIC_EXPERIENCE and self.source_kind != EvidenceSourceKind.ACADEMIC_SELF_REPORT:
            raise ValueError("Academic experience must use source_kind='academic_self_report'.")
        if self.evidence_type == EvidenceType.REPEATED_IN_PRODUCT_BEHAVIOR:
            if not self.behavior_consent_confirmed:
                raise ValueError("Recording an in-product behavior item requires explicit consent for this specific interaction.")
            if self.source_kind != EvidenceSourceKind.IN_PRODUCT_BEHAVIOR:
                raise ValueError("Repeated in-product behavior must use source_kind='in_product_behavior'.")
            if not self.context:
                raise ValueError("Repeated behavior must retain its context (for example activity and time window); no background monitoring is implemented.")
            activity = self.context.get("activity_name")
            time_window = self.context.get("time_window")
            if not isinstance(activity, str) or not activity.strip() or not isinstance(time_window, str) or not time_window.strip():
                raise ValueError("Repeated behavior requires non-empty activity_name and time_window context fields.")
        # Keep context compact: no file/blob payloads or arbitrary large user data in this ledger.
        import json
        if len(json.dumps(self.context, ensure_ascii=False)) > 4096:
            raise ValueError("Evidence context must be 4 KB or smaller.")
        return self


class EvidenceUpdate(BaseModel):
    """Patch model for user correction; identity and original recording time are immutable."""
    model_config = ConfigDict(extra="forbid")

    evidence_type: EvidenceType | None = None
    signal_dimension: SignalDimension | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)
    observation: str | None = Field(default=None, min_length=1, max_length=2400)
    domain: str | None = Field(default=None, max_length=100)
    source_kind: EvidenceSourceKind | None = None
    source_reference: HttpUrl | None = None
    observed_at: datetime | None = None
    uncertainty: UncertaintyLevel | None = None
    user_interpretation: UserInterpretation | None = None
    challenge_label: str | None = Field(default=None, max_length=160)
    rubric_name: str | None = Field(default=None, max_length=160)
    rubric_version: str | None = Field(default=None, max_length=80)
    rubric_observations: list[RubricObservation] | None = Field(default=None, max_length=20)
    reported_enjoyment: int | None = Field(default=None, ge=1, le=5)
    reported_curiosity: int | None = Field(default=None, ge=1, le=5)
    reported_effort: int | None = Field(default=None, ge=1, le=5)
    reported_difficulty: int | None = Field(default=None, ge=1, le=5)
    context: dict[str, str | int | float | bool | None] | None = None

    @field_validator("observed_at")
    @classmethod
    def timestamp_must_have_timezone(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("observed_at must include a timezone.")
        if value.astimezone(UTC) > datetime.now(UTC) + timedelta(seconds=5):
            raise ValueError("observed_at cannot be in the future.")
        return value.astimezone(UTC)


class EvidenceItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID
    profile_id: UUID
    evidence_type: EvidenceType
    signal_dimension: SignalDimension
    title: str
    observation: str
    domain: str | None
    source_kind: EvidenceSourceKind
    source_reference: HttpUrl | None
    observed_at: datetime
    recorded_at: datetime
    updated_at: datetime
    uncertainty: UncertaintyLevel
    user_interpretation: UserInterpretation
    consent_basis_at_capture: ConsentBasis
    consent_confirmed_at_capture: datetime
    consent_notice_version_at_capture: str
    behavior_consent_confirmed: bool
    behavior_consent_confirmed_at: datetime | None
    challenge_label: str | None
    rubric_name: str | None
    rubric_version: str | None
    rubric_observations: list[RubricObservation]
    reported_enjoyment: int | None
    reported_curiosity: int | None
    reported_effort: int | None
    reported_difficulty: int | None
    context: dict[str, str | int | float | bool | None]


class SignalEvidenceSummary(BaseModel):
    signal_dimension: SignalDimension
    status: str
    evidence_count: int
    interpretation_counts: dict[str, int]
    explanation: str
    recent_evidence: list[dict[str, Any]]


class StudentProfileSummary(BaseModel):
    profile_id: UUID
    generated_at: datetime
    summary_policy_version: str = "evidence-summary-v1.0"
    overall_status: str
    overall_explanation: str
    signals: list[SignalEvidenceSummary]
    evidence_count: int
    limitations: list[str]
