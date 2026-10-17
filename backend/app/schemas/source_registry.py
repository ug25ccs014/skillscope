"""Public read-only contract for the source audit interface."""
from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field

SourceStatus = Literal["live", "cached", "curated", "link_only", "unavailable"]


class SourceRegistryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    publisher: str
    name: str
    official_url: str
    reference_urls: list[str] = Field(default_factory=list)
    terms_url: str | None = None
    geography: str | None = None
    source_role: str
    source_version_or_release: str | None = None
    reviewed_on: str | None = None
    integration_status: str
    runtime_access_status: str
    status: SourceStatus
    status_explanation: str
    last_successful_sync_at: str | None = None
    last_attempt_at: str | None = None
    last_attempt_status: str | None = None
    active_snapshot_id: str | None = None
    checksum_sha256: str | None = None
    license_terms_status: str
    limitations: list[str] = Field(default_factory=list)
    source_data_is_live: bool = False


class SourceConflictRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_record_id: str
    internal_id: str | None = None
    publisher: str
    title: str
    record_uri: str | None = None
    source_version: str | None = None
    geography: str | None = None
    limitations: list[str] = Field(default_factory=list)
    explanation: str


class MappingUncertainty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    edge_id: str
    from_label: str
    to_label: str
    relation_type: str
    mapping_type: str
    review_status: str
    description: str | None = None
    notes: list[str] = Field(default_factory=list)
    source_references: list[dict[str, Any]] = Field(default_factory=list)
    explanation: str


class SourceRegistryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    manifest_version: int | str | None = None
    manifest_last_reviewed: str | None = None
    manifest_status: str
    generated_at: str
    sources: list[SourceRegistryEntry] = Field(default_factory=list)
    conflicted_source_records: list[SourceConflictRecord] = Field(default_factory=list)
    mapping_uncertainties: list[MappingUncertainty] = Field(default_factory=list)
    graph_status: dict[str, Any] = Field(default_factory=dict)
    source_data_is_live: bool = False
    notes: list[str] = Field(default_factory=list)
