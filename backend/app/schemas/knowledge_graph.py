"""Public contracts for the source-traceable SkillScope career knowledge graph."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class GraphNodeType(str, Enum):
    OCCUPATION = "occupation"
    SKILL = "skill"
    CAPABILITY_HYPOTHESIS = "capability_hypothesis"
    WORK_ACTIVITY = "work_activity"
    OCCUPATIONAL_TERM = "occupational_term"
    QUALIFICATION = "qualification"
    EDUCATION_PATHWAY = "education_pathway"
    PROJECT = "project"
    CHALLENGE = "challenge"
    INTEREST_TERM = "interest_term"


class GraphRelationType(str, Enum):
    PERFORMS_TASK = "performs_task"
    ASSOCIATED_WITH_SOURCE_TERM = "associated_with_source_term"
    OCCUPATION_HAS_SKILL = "occupation_has_skill"
    HAS_OCCUPATIONAL_SKILL_REFERENCE = "has_occupational_skill_reference"
    RELATED_OCCUPATION = "related_occupation"
    RELATED_WORK_ACTIVITY = "related_work_activity"
    REQUIRES_QUALIFICATION = "requires_qualification"
    PATHWAY_TO = "pathway_to"
    DEMONSTRATES_SKILL = "demonstrates_skill"
    DEVELOPS_SKILL = "develops_skill"
    SUPPORTS_CAPABILITY_HYPOTHESIS = "supports_capability_hypothesis"
    CROSSWALK_CANDIDATE = "crosswalk_candidate"


class GraphMappingType(str, Enum):
    EXACT = "exact"
    REVIEWED_RELATED = "reviewed_related"
    WEAK_LEXICAL = "weak_lexical"
    UNRESOLVED = "unresolved"


class MappingReviewStatus(str, Enum):
    SOURCED = "sourced"
    REVIEWED = "reviewed"
    PROPOSED = "proposed"
    UNRESOLVED = "unresolved"
    REJECTED = "rejected"


class GraphSourceReference(BaseModel):
    """A source citation with its version and source class kept visible."""

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
    license_reference: HttpUrl | None = None
    fact_id: str | None = None
    fact_type: str | None = None
    fact_statement: str | None = None
    evidence_role: str
    notes: list[str] = Field(default_factory=list)


class KnowledgeGraphNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    node_type: GraphNodeType
    label: str
    description: str | None = None
    taxonomy: str | None = None
    external_id: str | None = None
    geography: str | None = None
    evidence_class: str
    attributes: dict[str, Any] = Field(default_factory=dict)
    source_references: list[GraphSourceReference] = Field(default_factory=list)


class KnowledgeGraphEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    from_node_id: str
    to_node_id: str
    relation_type: GraphRelationType
    mapping_type: GraphMappingType = GraphMappingType.EXACT
    review_status: MappingReviewStatus = MappingReviewStatus.SOURCED
    description: str | None = None
    attributes: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)
    source_references: list[GraphSourceReference] = Field(default_factory=list)


class KnowledgeGraphStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    graph_schema_version: int
    builder_version: str
    built_at: str | None = None
    node_count: int
    edge_count: int
    nodes_by_type: dict[str, int]
    edges_by_relation: dict[str, int]
    active_snapshots: dict[str, str]
    built_from_active_snapshots: dict[str, str]
    is_stale: bool
    unresolved_crosswalk_count: int
    unresolved_relationship_count: int = 0
    unresolved_relationships: list[dict[str, Any]] = Field(default_factory=list)
    source_data_is_live: bool = False
    limitations: list[str] = Field(default_factory=list)
