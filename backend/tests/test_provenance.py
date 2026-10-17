from datetime import UTC, datetime
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.provenance import (
    CanonicalEntity,
    EntityType,
    MappingType,
    ProvenanceLink,
    QualityStatus,
    SourceRecord,
    SourceType,
)
from app.services.provenance import ProvenanceRepository


def make_source() -> SourceRecord:
    return SourceRecord(
        source_id="test_source",
        publisher="Test Publisher",
        title="Test occupational record",
        source_type=SourceType.OFFICIAL,
        geography="India",
        source_uri="https://example.com/source",
        record_uri="https://example.com/source/role-1",
        source_version="2026-test",
        release_date="2026-01-01",
        accessed_at=datetime.now(UTC),
        license_reference="https://example.com/license",
        quality_status=QualityStatus.REVIEWED,
        limitations=["Synthetic test source"],
    )


def make_entity(source: SourceRecord) -> CanonicalEntity:
    now = datetime.now(UTC)
    return CanonicalEntity(
        internal_id="occupation:test-role",
        entity_type=EntityType.OCCUPATION,
        source_id=source.source_id,
        source_record_id="role-1",
        source_uri=source.record_uri,
        source_title=source.title,
        source_code="TEST-1",
        publisher=source.publisher,
        geography=source.geography,
        source_version=source.source_version,
        release_date=source.release_date,
        accessed_at=source.accessed_at,
        ingested_at=now,
        license_reference=source.license_reference,
        source_type=source.source_type,
        source_values={"title": "Original Role", "skills": ["Original Skill"]},
        normalized_values={"title": "Original Role", "skills": ["original-skill"]},
        transformation_notes=["Normalized skill identifier without changing source value."],
        quality_status=QualityStatus.REVIEWED,
        confidence=0.9,
        limitations=["Synthetic test source"],
    )


def test_provenance_repository_round_trips_full_lineage(tmp_path):
    repo = ProvenanceRepository(tmp_path / "test.db")
    source = make_source()
    entity = make_entity(source)
    repo.upsert_source(source, "role-1")
    repo.upsert_entity(entity)
    with pytest.raises(sqlite3.IntegrityError, match="require a provenance link"):
        repo.add_career_fact(
            "fact:test-role-skill-without-lineage",
            entity.internal_id,
            "required_skill",
            "This must not become a displayable sourced fact without lineage.",
            {"skill": "untraceable"},
        )
    repo.add_provenance_link(
        ProvenanceLink(
            entity_internal_id=entity.internal_id,
            source_id=source.source_id,
            source_record_id="role-1",
            source_uri=source.record_uri,
            source_version=source.source_version,
            mapping_type=MappingType.EXACT,
            mapping_notes=["Direct source record."],
            created_at=datetime.now(UTC),
        )
    )
    repo.add_career_fact(
        "fact:test-role-skill",
        entity.internal_id,
        "required_skill",
        "This role uses the source-listed skill.",
        {"skill": "original-skill"},
    )

    fact = repo.get_career_fact("fact:test-role-skill")
    assert fact is not None
    assert fact.display_status == "sourced"
    assert fact.source.source_id == "test_source"
    assert fact.source.source_version == "2026-test"
    assert fact.entity.source_values["skills"] == ["Original Skill"]
    assert fact.entity.normalized_values["skills"] == ["original-skill"]
    assert fact.provenance.mapping_type is MappingType.EXACT


def test_repository_counts_are_explicit(tmp_path):
    repo = ProvenanceRepository(tmp_path / "empty.db")
    assert repo.count() == {"sources": 0, "entities": 0, "provenance_links": 0, "career_facts": 0}


def test_provenance_status_does_not_claim_external_data_without_records(tmp_path, monkeypatch):
    # The production endpoint uses the default DB, so this test checks the contract
    # directly rather than replacing global application state.
    repo = ProvenanceRepository(tmp_path / "status.db")
    counts = repo.count()
    assert counts["sources"] == 0
    assert counts["entities"] == 0


def test_api_returns_404_for_unknown_career_fact():
    client = TestClient(app)
    response = client.get("/api/provenance/career-facts/does-not-exist")
    assert response.status_code == 404


def test_api_exposes_provenance_status():
    client = TestClient(app)
    response = client.get("/api/provenance/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["external_data_integrated"] is False
    assert set(body["counts"]) == {"sources", "entities", "provenance_links", "career_facts"}


def test_repository_rejects_naive_provenance_timestamps():
    with pytest.raises(ValueError, match="must include a timezone"):
        ProvenanceRepository._iso(datetime(2026, 10, 17, 12, 0, 0))


def test_repository_enforces_foreign_keys_on_every_connection(tmp_path):
    repo = ProvenanceRepository(tmp_path / "fk.db")
    source = make_source()
    entity = make_entity(source)

    # Individual-write methods must not silently bypass SQLite lineage constraints.
    with pytest.raises(sqlite3.IntegrityError):
        repo.upsert_entity(entity)

    repo.upsert_source(source, "role-1")
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_provenance_link(
            ProvenanceLink(
                entity_internal_id="missing-entity",
                source_id=source.source_id,
                source_record_id="role-1",
                source_uri=source.record_uri,
                source_version=source.source_version,
                mapping_type=MappingType.EXACT,
                mapping_notes=["Invalid link should fail."],
                created_at=datetime.now(UTC),
            )
        )
    with pytest.raises(sqlite3.IntegrityError):
        repo.add_career_fact("fact:missing-entity", "missing-entity", "skill", "Must fail.", {})
    assert repo.count() == {"sources": 1, "entities": 0, "provenance_links": 0, "career_facts": 0}
