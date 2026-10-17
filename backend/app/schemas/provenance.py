"""Canonical provenance contracts for SkillScope sourced facts and mappings."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class SourceType(str, Enum):
    OFFICIAL = "official"
    RESEARCH = "research"
    USER_PROVIDED = "user_provided"
    HEURISTIC = "heuristic"
    DEMO_FIXTURE = "demo_fixture"
    CURATED_EXTRACT = "curated_extract"


class QualityStatus(str, Enum):
    UNVERIFIED = "unverified"
    REVIEWED = "reviewed"
    VERIFIED = "verified"
    STALE = "stale"
    CONFLICTED = "conflicted"


class EntityType(str, Enum):
    OCCUPATION = "occupation"
    SKILL = "skill"
    QUALIFICATION = "qualification"
    WORK_ACTIVITY = "work_activity"
    CAREER_PATHWAY = "career_pathway"
    LABOUR_MARKET_FACT = "labour_market_fact"
    OCCUPATION_SKILL_OBSERVATION = "occupation_skill_observation"


class MappingType(str, Enum):
    EXACT = "exact"
    REVIEWED_RELATED = "reviewed_related"
    WEAK_LEXICAL = "weak_lexical"
    UNRESOLVED = "unresolved"


class SourceRecord(BaseModel):
    """One immutable description of an external or internal evidence source."""

    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=120)
    publisher: str = Field(min_length=1, max_length=240)
    title: str = Field(min_length=1, max_length=300)
    source_type: SourceType
    geography: str | None = Field(default=None, max_length=120)
    source_uri: HttpUrl | None = None
    record_uri: HttpUrl | None = None
    source_version: str | None = Field(default=None, max_length=120)
    release_date: str | None = Field(default=None, max_length=40)
    accessed_at: datetime
    ingested_at: datetime | None = None
    license_reference: HttpUrl | None = None
    license_text: str | None = Field(default=None, max_length=1000)
    checksum_sha256: str | None = Field(default=None, pattern=r"^[0-9a-fA-F]{64}$")
    quality_status: QualityStatus = QualityStatus.UNVERIFIED
    last_verified_at: datetime | None = None
    limitations: list[str] = Field(default_factory=list, max_length=20)


class CanonicalEntity(BaseModel):
    """Normalized entity while preserving its original source representation."""

    model_config = ConfigDict(extra="forbid")

    internal_id: str = Field(min_length=1, max_length=160)
    entity_type: EntityType
    source_id: str = Field(min_length=1, max_length=120)
    source_record_id: str = Field(min_length=1, max_length=160)
    source_uri: HttpUrl | None = None
    source_title: str = Field(min_length=1, max_length=300)
    source_code: str | None = Field(default=None, max_length=160)
    publisher: str = Field(min_length=1, max_length=240)
    geography: str | None = Field(default=None, max_length=120)
    source_version: str | None = Field(default=None, max_length=120)
    release_date: str | None = Field(default=None, max_length=40)
    accessed_at: datetime
    ingested_at: datetime
    license_reference: HttpUrl | None = None
    source_type: SourceType
    source_values: dict[str, Any] = Field(default_factory=dict)
    normalized_values: dict[str, Any] = Field(default_factory=dict)
    transformation_notes: list[str] = Field(default_factory=list)
    quality_status: QualityStatus = QualityStatus.UNVERIFIED
    last_verified_at: datetime | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)


class ProvenanceLink(BaseModel):
    """Trace from a canonical entity/fact to one source record."""

    model_config = ConfigDict(extra="forbid")

    entity_internal_id: str = Field(min_length=1, max_length=160)
    source_id: str = Field(min_length=1, max_length=120)
    source_record_id: str = Field(min_length=1, max_length=160)
    source_uri: HttpUrl | None = None
    source_version: str | None = Field(default=None, max_length=120)
    mapping_type: MappingType = MappingType.EXACT
    mapping_notes: list[str] = Field(default_factory=list)
    created_at: datetime


class CareerFact(BaseModel):
    """A displayable career fact whose evidence chain can be followed."""

    model_config = ConfigDict(extra="forbid")

    fact_id: str = Field(min_length=1, max_length=160)
    entity_internal_id: str = Field(min_length=1, max_length=160)
    fact_type: str = Field(min_length=1, max_length=120)
    statement: str = Field(min_length=1, max_length=1000)
    value: Any
    source: SourceRecord
    entity: CanonicalEntity
    provenance: ProvenanceLink
    display_status: str = "sourced"
