"""Request and response contracts for age-aware entry calibration.

The calibration chooses an appropriate starting experience. It does not score
aptitude, predict a career outcome, or diagnose a student.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AgeBand(str, Enum):
    AGES_10_14 = "10-14"
    AGES_15_17 = "15-17"
    AGES_18_PLUS = "18+"


class AgeMode(str, Enum):
    DISCOVER_AND_SHAPE = "discover_and_shape"
    EXPLORE_AND_VALIDATE = "explore_and_validate"
    DEVELOP_AND_OPTIMIZE = "develop_and_optimize"


class StartingPath(str, Enum):
    GUIDED_EXPLORATION = "guided_exploration"
    BASELINE_DISCOVERY = "baseline_discovery"
    BROADEN_EXPLORATION = "broaden_exploration"
    VALIDATE_DECLARED_INTEREST = "validate_declared_interest"
    CAREER_DISCOVERY = "career_discovery"
    CAREER_GOAL_VALIDATION = "career_goal_validation"
    CAREER_GAP_ANALYSIS = "career_gap_analysis"
    REENTER_DISCOVERY = "reenter_discovery"


class EvidenceStrength(str, Enum):
    NONE = "none"
    LIMITED = "limited"
    EMERGING = "emerging"
    SUBSTANTIAL = "substantial"


class Rating(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceQuality(str, Enum):
    UNKNOWN = "unknown"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ExperienceLevel(str, Enum):
    NONE = "none"
    SOME = "some"
    SUBSTANTIAL = "substantial"


class JourneyPreference(str, Enum):
    AUTOMATIC = "automatic"
    EXPLORE = "explore"
    VALIDATE = "validate"
    OPTIMIZE = "optimize"


class ExplorationDomain(str, Enum):
    CREATIVE_DESIGN = "creative_design"
    ANALYTICAL_LOGIC = "analytical_logic"
    HANDS_ON_MAKING = "hands_on_making"
    SOCIAL_COLLABORATION = "social_collaboration"
    COMMUNICATION_STORYTELLING = "communication_storytelling"
    SCIENCE_EXPERIMENTATION = "science_experimentation"
    TECHNOLOGY_COMPUTING = "technology_computing"
    ENVIRONMENT_SUSTAINABILITY = "environment_sustainability"
    BUSINESS_ENTREPRENEURSHIP = "business_entrepreneurship"
    HEALTH_WELLBEING = "health_wellbeing"


class DesiredTimeline(str, Enum):
    UNSPECIFIED = "unspecified"
    UNDER_3_MONTHS = "under_3_months"
    MONTHS_3_TO_6 = "3_to_6_months"
    MONTHS_6_TO_12 = "6_to_12_months"
    OVER_12_MONTHS = "over_12_months"


class CalibrationRequest(BaseModel):
    """Minimal, user-supplied inputs needed to choose a starting journey.

    Age is collected as an integer (not a date of birth). Evidence counts and
    qualitative assessments are self-reported at this stage; they are not
    independently verified or persisted by this endpoint.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    age: int = Field(
        ge=10,
        le=100,
        description="Age in completed years; no full date of birth is required.",
    )
    career_clarity: Rating = Field(
        default=Rating.LOW,
        description="How clear the user currently feels about a direction.",
    )
    prior_evidence_count: int = Field(
        default=0,
        ge=0,
        le=10000,
        description="Self-reported number of relevant activities, projects, or records.",
    )
    prior_activity_summary: str | None = Field(
        default=None,
        max_length=240,
        description="Optional summary of activities/projects already tried, with no sensitive personal details.",
    )
    prior_evidence_quality: EvidenceQuality = Field(
        default=EvidenceQuality.UNKNOWN,
        description="Self-reported quality/variety of prior evidence.",
    )
    prior_projects_experience: ExperienceLevel = Field(
        default=ExperienceLevel.NONE,
        description="Self-reported project or practical experience level.",
    )
    exploration_need: Rating = Field(
        default=Rating.MEDIUM,
        description="How much breadth-first exploration the user wants or needs.",
    )
    current_goal: str | None = Field(
        default=None,
        max_length=180,
        description="Optional career/domain direction stated by the user.",
    )
    unexplored_domains: list[ExplorationDomain] = Field(
        default_factory=list,
        max_length=10,
        description="Domains the user says they have had little opportunity to try; not interpreted as weaknesses.",
    )
    education_summary: str | None = Field(
        default=None,
        max_length=200,
        description="Optional context for adult career planning; do not enter sensitive personal details.",
    )
    skills_summary: str | None = Field(
        default=None,
        max_length=300,
        description="Optional self-described skills for adult career planning.",
    )
    experience_summary: str | None = Field(
        default=None,
        max_length=300,
        description="Optional project, work, volunteering, or portfolio context for adult career planning.",
    )
    planning_constraints: str | None = Field(
        default=None,
        max_length=240,
        description="Optional user-chosen planning constraints such as time or training access; avoid sensitive details.",
    )
    desired_timeline: DesiredTimeline = Field(
        default=DesiredTimeline.UNSPECIFIED,
        description="Optional time horizon for adult planning.",
    )
    contradictory_evidence: bool = Field(
        default=False,
        description="Whether the user has noticed conflicting signals about their direction.",
    )
    career_goal_changed: bool = Field(
        default=False,
        description="Whether the user says their direction changed recently.",
    )
    reenter_discovery: bool = Field(
        default=False,
        description="Explicit request to restart with an exploration-first cycle.",
    )
    journey_preference: JourneyPreference = Field(
        default=JourneyPreference.AUTOMATIC,
        description="Optional starting-journey preference; age-appropriate guardrails still apply.",
    )

    @field_validator(
        "current_goal",
        "prior_activity_summary",
        "education_summary",
        "skills_summary",
        "experience_summary",
        "planning_constraints",
    )
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = " ".join(value.split())
        return cleaned or None

    @field_validator("unexplored_domains")
    @classmethod
    def deduplicate_unexplored_domains(
        cls,
        value: list[ExplorationDomain],
    ) -> list[ExplorationDomain]:
        return list(dict.fromkeys(value))


class CalibrationResponse(BaseModel):
    """Explainable entry recommendation; contains no aptitude score or probability."""

    age_band: AgeBand
    age_mode: AgeMode
    age_mode_label: str
    starting_path: StartingPath
    starting_path_label: str
    evidence_strength: EvidenceStrength
    evidence_strength_label: str
    rationale: list[str]
    next_step: str
    considered_inputs: list[str]
    limitations: list[str]
    calibration_version: Literal["1.0.0"] = "1.0.0"
