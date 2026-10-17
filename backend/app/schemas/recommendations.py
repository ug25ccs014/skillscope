"""Public contract for the explainable, versioned career hypothesis engine."""
from __future__ import annotations

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.schemas.student_evidence import AgeBand


class RecommendationCategory(str, Enum):
    EXPLORE = "explore"
    DEVELOP = "develop"
    CHALLENGE = "challenge"
    ALTERNATIVE_TO_CONSIDER = "alternative_to_consider"
    RECONSIDER_REFRESH = "reconsider_refresh"


class EvidenceConfidenceLevel(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


class QualitativeStatus(str, Enum):
    NOT_AVAILABLE = "not_available"
    LIMITED = "limited"
    RECENT = "recent"
    OLDER = "older"
    MIXED = "mixed"
    CONSISTENT_SO_FAR = "consistent_so_far"
    REVIEWED = "reviewed"
    PARTIAL = "partial"
    BROAD = "broad"
    NARROW = "narrow"


class RecommendationEvidenceReference(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: UUID
    title: str
    evidence_type: str
    signal_dimension: str
    source_kind: str
    observed_at: str
    domain: str | None = None
    uncertainty: str
    user_interpretation: str
    why_used: str


class RecommendationSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_record_id: str
    title: str
    publisher: str
    record_uri: HttpUrl | None = None
    source_version: str | None = None
    source_type: str
    geography: str | None = None
    quality_status: str
    fact_id: str | None = None
    fact_type: str | None = None
    fact_statement: str | None = None
    evidence_role: str
    notes: list[str] = Field(default_factory=list)


class SourcedPathwayFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    fact_kind: str
    statement: str
    source: RecommendationSource


class RecommendationMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    match_type: str
    label: str
    explanation: str
    evidence_ids: list[UUID] = Field(default_factory=list)
    source_references: list[RecommendationSource] = Field(default_factory=list)


class RecommendationGap(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gap_type: str
    label: str
    explanation: str


class ConfidenceBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_volume: QualitativeStatus
    recency: QualitativeStatus
    consistency: QualitativeStatus
    source_quality: QualitativeStatus
    coverage: QualitativeStatus
    explanation: str


class ValidatingAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    challenge_id: str | None = None
    title: str
    domain: str | None = None
    expected_minutes: int | None = None
    action: str
    why_this_tests_the_hypothesis: str


class CareerHypothesisRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hypothesis_id: str
    hypothesis_label: str
    recommendation_type: str
    occupation_node_id: str | None = None
    occupation: str | None = None
    taxonomy: str | None = None
    geography: str | None = None
    category: RecommendationCategory
    support_level: str
    evidence_confidence: EvidenceConfidenceLevel
    confidence_breakdown: ConfidenceBreakdown
    rationale: list[str]
    matches: list[RecommendationMatch] = Field(default_factory=list)
    evidence_used: list[RecommendationEvidenceReference] = Field(default_factory=list)
    evidence_gaps: list[RecommendationGap] = Field(default_factory=list)
    source_backed_pathway_facts: list[SourcedPathwayFact] = Field(default_factory=list)
    next_validating_action: ValidatingAction
    source_record_count: int = Field(ge=0)
    source_quality_note: str
    important_limitations: list[str] = Field(default_factory=list)


class RecommendationSet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile_id: UUID
    age_band: AgeBand
    current_goal: str | None = None
    algorithm_version: str
    weights_status: str
    weights: RecommendationWeights
    domain_hypothesis_policy_version: str
    recommendations: list[CareerHypothesisRecommendation]
    evidence_count: int = Field(ge=0)
    evidence_count_is_truncated_for_detail: bool = False
    career_catalog_count: int = Field(ge=0)
    catalog_status: str
    catalog_limitations: list[str] = Field(default_factory=list)
    ordering_explanation: str
    global_notices: list[str] = Field(default_factory=list)


class RecommendationWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal_language_overlap: float = Field(ge=0, le=1)
    exact_skill_label_overlap: float = Field(ge=0, le=1)
    challenge_domain_alignment: float = Field(ge=0, le=1)
    repeated_activity_families: float = Field(ge=0, le=1)
    portfolio_context_overlap: float = Field(ge=0, le=1)


class RecommendationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    algorithm_version: str
    status: str
    description: str
    weights: RecommendationWeights
    active_component_normalization: str
    confidence_policy: dict[str, Any]
