"""Contracts for age-aware, persistent career pathway plans.

A plan is an editable learning proposal, not a qualification checklist or career guarantee.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.schemas.privacy_validation import validate_user_text

from app.schemas.recommendations import RecommendationSource, SourcedPathwayFact
from app.schemas.student_evidence import AgeBand


class DesiredTimeline(str, Enum):
    UNSPECIFIED = "unspecified"
    DAYS_30 = "30_days"
    DAYS_60 = "60_days"
    DAYS_90 = "90_days"
    MONTHS_6 = "6_months"
    MONTHS_12 = "12_months"


class PlanInput(BaseModel):
    """Student-controlled planning context; adult planning fields are checked against age on save."""
    model_config = ConfigDict(extra="forbid")

    @field_validator("current_goal", "current_skills_summary", "education_summary", "experience_summary", "planning_constraints", mode="before")
    @classmethod
    def prevent_contact_details(cls, value: object) -> object:
        return validate_user_text(value)

    # Presence of current_goal in model_fields_set means the user deliberately edited it.
    current_goal: str | None = Field(default=None, max_length=500)
    current_skills_summary: str | None = Field(default=None, max_length=1800)
    education_summary: str | None = Field(default=None, max_length=1500)
    experience_summary: str | None = Field(default=None, max_length=1800)
    planning_constraints: str | None = Field(default=None, max_length=1200)
    available_hours_per_week: int | None = Field(default=None, ge=1, le=80)
    desired_timeline: DesiredTimeline = DesiredTimeline.UNSPECIFIED


class PlanAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str
    order: int = Field(ge=1)
    phase: str
    time_horizon_days: int | None = Field(default=None, ge=1, le=3650)
    time_horizon_label: str | None = None
    action_type: Literal["explore", "validate", "learn", "build", "document", "feedback", "review", "revise"]
    title: str
    why_this_step: str
    instructions: list[str] = Field(min_length=1)
    expected_outcome: str
    estimated_hours_min: float | None = Field(default=None, ge=0)
    estimated_hours_max: float | None = Field(default=None, ge=0)
    skill_labels: list[str] = Field(default_factory=list)
    evidence_ids: list[UUID] = Field(default_factory=list)
    source_references: list[RecommendationSource] = Field(default_factory=list)
    prerequisite_status: Literal["sourced", "none_identified", "not_assessed"] = "not_assessed"
    prerequisite_note: str
    action_origin: Literal["skillscope_authored", "source_informed", "student_goal"]


class PathwayOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pathway_id: str
    label: str
    occupation_node_id: str | None = None
    taxonomy: str | None = None
    geography: str | None = None
    recommendation_category: str
    evidence_confidence: str
    why_plausible: list[str] = Field(default_factory=list)
    skill_or_interest_matches: list[str] = Field(default_factory=list)
    what_remains_unknown: list[str] = Field(default_factory=list)
    pathway_facts: list[SourcedPathwayFact] = Field(default_factory=list)
    validation_actions: list[PlanAction] = Field(default_factory=list)
    comparison_note: str


class SkillEvidenceGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_label: str
    status: Literal["self_reported_in_current_state", "mentioned_in_evidence", "not_yet_documented"]
    explanation: str
    source_references: list[RecommendationSource] = Field(default_factory=list)


class PlanRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    status: Literal["source_backed_requirement", "source_backed_work_context", "not_available_in_catalog"]
    statement: str
    is_prerequisite: bool | None = None
    source_references: list[RecommendationSource] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


class TimeboxAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["time_bounded", "missing_inputs", "not_applicable_age_mode"]
    requested_timeline: DesiredTimeline
    explanation: str
    missing_inputs: list[str] = Field(default_factory=list)
    available_hours_per_week: int | None = None


class PathwayPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: UUID
    profile_id: UUID
    age_band: AgeBand
    mode: Literal["discover_and_shape", "explore_and_validate", "develop_and_optimize"]
    algorithm_version: str
    recommendation_algorithm_version: str
    current_goal: str | None = None
    previous_goal: str | None = None
    goal_change_detected: bool = False
    goal_change_handling: str
    created_at: datetime
    inputs_used: dict[str, str | int | None]
    pathway_options: list[PathwayOption] = Field(default_factory=list)
    skills_to_check_or_develop: list[SkillEvidenceGap] = Field(default_factory=list)
    requirements_and_sources: list[PlanRequirement] = Field(default_factory=list)
    actions: list[PlanAction] = Field(default_factory=list)
    timebox: TimeboxAssessment
    revision_instructions: list[str] = Field(min_length=1)
    limitations: list[str] = Field(default_factory=list)


class PathwayPlanHistoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_id: UUID
    profile_id: UUID
    created_at: datetime
    current_goal: str | None = None
    age_band: AgeBand
    goal_change_detected: bool
    action_count: int
    pathway_count: int
    algorithm_version: str
