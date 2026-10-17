"""Contracts for SkillScope's deterministic longitudinal discovery loop."""
from __future__ import annotations

from enum import Enum
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.challenges import ChallengeDomain, Difficulty, RubricCriterion, SafetyRating
from app.schemas.student_evidence import AgeBand, UserInterpretation

LOOP_POLICY_VERSION = "discovery-loop-v1.0"


class LoopPreference(str, Enum):
    BALANCED = "balanced"
    EXPLORE = "explore"
    DEVELOP = "develop"
    VALIDATE = "validate"
    ALTERNATIVE = "alternative"


class DomainExposure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    domain: ChallengeDomain
    submission_count: int = Field(ge=0)
    distinct_challenges: int = Field(ge=0)
    latest_at: str | None = None
    status: str


class LastCompletion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    submission_id: UUID
    challenge_id: str
    title: str
    domain: ChallengeDomain
    evidence_status: str
    observed_criteria: int
    objective_score: int | None
    objective_max_score: int | None
    interpretation: UserInterpretation
    enjoyment: int | None
    reported_difficulty: int | None
    confidence: int | None
    willingness_to_continue: int | None
    reflection: str | None
    created_at: str


class NextChallenge(BaseModel):
    model_config = ConfigDict(extra="forbid")
    challenge_id: str
    challenge_version: str
    domain: ChallengeDomain
    skill_tags: list[str]
    difficulty: Difficulty
    safety_rating: SafetyRating
    title: str
    instructions: str
    expected_output: str
    expected_minutes: int
    materials: list[str]
    accessibility_notes: list[str]
    rubric: list[RubricCriterion]
    reflection_prompts: list[str]
    reason_code: str
    rationale: str
    why_this_now: str
    avoids_recent_repeat: bool


class DiscoveryLoopState(BaseModel):
    model_config = ConfigDict(extra="forbid")
    loop_policy_version: str = LOOP_POLICY_VERSION
    profile_id: UUID
    age_band: AgeBand
    mode: str
    preference: LoopPreference
    current_goal: str | None
    total_submissions: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    domain_exposure: list[DomainExposure]
    last_completion: LastCompletion | None
    next_challenge: NextChallenge
    what_changed: str
    next_step: str
    notice: str = "This is an evolving discovery snapshot, not a verdict about your ability or future. Each completed activity adds context; skipped or unobserved evidence is not treated as zero."
    limitations: list[str]
