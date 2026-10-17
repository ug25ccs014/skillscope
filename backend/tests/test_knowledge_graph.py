from __future__ import annotations

from datetime import UTC, datetime
import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.provenance import CanonicalEntity, EntityType, MappingType, ProvenanceLink, QualityStatus, SourceRecord, SourceType
from app.services.knowledge_graph import (
    KnowledgeGraphBuilder,
    KnowledgeGraphError,
    KnowledgeGraphRepository,
    graph_status,
    load_active_snapshots,
    rebuild_knowledge_graph,
)
from app.services.provenance import ProvenanceRepository
from app.services.ingestion.pipeline import import_curated_snapshot


def make_bundle(
    *, source_id: str, snapshot: str, source_record_suffix: str, entity_id: str,
    entity_type: EntityType, title: str, taxonomy: str, external_id: str,
    normalized: dict, geography: str, fact_specs: list[tuple[str, str, str, object]] | None = None,
):
    now = datetime.now(UTC)
    record_id = f"{snapshot}:{source_record_suffix}"
    record_uri = external_id if external_id.startswith("http") else f"https://example.org/{source_id}/{source_record_suffix}"
    source = SourceRecord(
        source_id=source_id,
        publisher="Fixture publisher; test data only",
        title=title,
        source_type=SourceType.CURATED_EXTRACT,
        geography=geography,
        source_uri="https://example.org/source",
        record_uri=record_uri,
        source_version=f"fixture-{snapshot}",
        release_date="2026-10-17",
        accessed_at=now,
        ingested_at=now,
        license_reference="https://example.org/license",
        quality_status=QualityStatus.REVIEWED,
        limitations=["Synthetic test fixture; never a production source claim."],
    )
    entity = CanonicalEntity(
        internal_id=entity_id,
        entity_type=entity_type,
        source_id=source_id,
        source_record_id=record_id,
        source_uri=record_uri,
        source_title=title,
        source_code=external_id if not external_id.startswith("http") else None,
        publisher=source.publisher,
        geography=geography,
        source_version=source.source_version,
        release_date=source.release_date,
        accessed_at=now,
        ingested_at=now,
        license_reference=source.license_reference,
        source_type=source.source_type,
        source_values={"original_title": title, "source_identifier": external_id},
        normalized_values={"taxonomy": taxonomy, **normalized},
        transformation_notes=["Test fixture normalization; source values remain separate."],
        quality_status=QualityStatus.REVIEWED,
        last_verified_at=now,
        limitations=source.limitations,
    )
    link = ProvenanceLink(
        entity_internal_id=entity_id,
        source_id=source_id,
        source_record_id=record_id,
        source_uri=record_uri,
        source_version=source.source_version,
        mapping_type=MappingType.EXACT,
        mapping_notes=["Test-only exact source link."],
        created_at=now,
    )
    facts = fact_specs or []
    return (source, record_id, entity, link, facts)


def seed_graph_fixture(db_path):
    repo = ProvenanceRepository(db_path)
    onet_occ = make_bundle(
        source_id="test_onet", snapshot="snap-onet", source_record_suffix="occupation:15-1252.00",
        entity_id="entity:on-occupation", entity_type=EntityType.OCCUPATION, title="Software Developers",
        taxonomy="O*NET OnLine", external_id="15-1252.00", geography="United States",
        normalized={"title": "Software Developers", "code": "15-1252.00", "summary": "Design, build, test and maintain software.", "not_student_evidence": True},
        fact_specs=[
            ("fact:on:summary", "occupation_profile_summary", "Test source summary.", {"summary": "Design, build, test and maintain software."}),
            ("fact:on:tasks", "selected_occupational_tasks", "Selected task summaries; fixture only.", {"tasks": ["Debug or improve existing programs and interfaces.", "Review user needs and software requirements before design."]}),
        ],
    )
    esco_occ_uri = "http://data.europa.eu/esco/occupation/test-software-developer"
    esco_occ = make_bundle(
        source_id="test_esco", snapshot="snap-esco", source_record_suffix="occupation:software-developer",
        entity_id="entity:esco-occupation", entity_type=EntityType.OCCUPATION, title="software developer",
        taxonomy="ESCO", external_id=esco_occ_uri, geography="European Union classification context",
        normalized={"title": "software developer", "concept_uri": esco_occ_uri, "code": "2512.4", "summary": "Build software from specifications."},
        fact_specs=[
            ("fact:esco:summary", "occupation_profile_summary", "ESCO-like fixture summary.", {"summary": "Build software from specifications."}),
            ("fact:esco:tasks", "selected_occupational_tasks", "Selected task summaries; fixture only.", {"tasks": ["Debug software.", "Analyse software specifications."]}),
        ],
    )
    esco_skill_uri = "http://data.europa.eu/esco/skill/test-debugging"
    esco_skill = make_bundle(
        source_id="test_esco", snapshot="snap-esco", source_record_suffix="skill:software-debugging",
        entity_id="entity:esco-skill", entity_type=EntityType.SKILL, title="software debugging",
        taxonomy="ESCO", external_id=esco_skill_uri, geography="European Union classification context",
        normalized={"preferred_label": "software debugging", "concept_uri": esco_skill_uri, "description": "Debugging software (test data)."},
        fact_specs=[("fact:esco:skill-title", "esco_skill_title", "ESCO-like skill fixture.", {"preferred_label": "software debugging"})],
    )
    esco_relation = make_bundle(
        source_id="test_esco", snapshot="snap-esco", source_record_suffix="relation:occ-skill",
        entity_id="entity:esco-relation", entity_type=EntityType.OCCUPATION_SKILL_OBSERVATION,
        title="occupation-skill relationship", taxonomy="ESCO", external_id="https://example.org/relationship/1",
        geography="European Union classification context",
        normalized={"occupation_uri": esco_occ_uri, "skill_uri": esco_skill_uri, "relation_type": "occupation-skill", "relation_relevance": "essential"},
        fact_specs=[("fact:esco:relation", "occupation_skill_relation", "Source links this occupation and skill (fixture).", {"occupation_uri": esco_occ_uri, "skill_uri": esco_skill_uri})],
    )
    # An old snapshot must never be mixed into the active graph.
    old_occ = make_bundle(
        source_id="test_onet", snapshot="old-snapshot", source_record_suffix="occupation:old",
        entity_id="entity:old-occupation", entity_type=EntityType.OCCUPATION, title="Old stale occupation",
        taxonomy="O*NET OnLine", external_id="99-0000.00", geography="United States",
        normalized={"title": "Old stale occupation", "code": "99-0000.00", "summary": "Stale fixture."},
        fact_specs=[("fact:old:summary", "occupation_profile_summary", "Old stale fixture.", {"summary": "Stale fixture."})],
    )
    repo.upsert_bundles([onet_occ, esco_occ, esco_skill, esco_relation, old_occ])
    return {"test_onet": "snap-onet", "test_esco": "snap-esco"}


def test_graph_build_preserves_taxonomy_identity_and_builds_related_crosswalk(tmp_path):
    db_path = tmp_path / "graph.db"
    snapshots = seed_graph_fixture(db_path)
    result = rebuild_knowledge_graph(db_path, active_snapshots=snapshots)

    assert result["status"] == "built"
    assert result["nodes_by_type"]["occupation"] == 2
    assert result["nodes_by_type"]["skill"] == 1
    assert result["edges_by_relation"]["occupation_has_skill"] == 1
    assert result["unresolved_crosswalk_count"] == 1
    assert result["unresolved_relationship_count"] == 0

    repo = KnowledgeGraphRepository(db_path)
    crosswalks = repo.list_edges(relation_type="related_occupation")
    assert len(crosswalks) == 1
    assert crosswalks[0]["mapping_type"] == "reviewed_related"
    assert crosswalks[0]["review_status"] == "reviewed"
    assert crosswalks[0]["attributes"]["equivalence_claimed"] is False
    assert len(crosswalks[0]["source_references"]) == 2
    assert {source["source_id"] for source in crosswalks[0]["source_references"]} == {"test_onet", "test_esco"}

    unresolved = repo.list_edges(relation_type="crosswalk_candidate")
    assert len(unresolved) == 1
    assert unresolved[0]["review_status"] == "unresolved"
    assert unresolved[0]["mapping_type"] == "unresolved"

    nodes = repo.list_nodes(query="old stale occupation")
    assert nodes == []  # old snapshot was filtered out before graph construction


def test_graph_rebuild_is_idempotent_and_source_citations_are_traceable(tmp_path):
    db_path = tmp_path / "graph.db"
    snapshots = seed_graph_fixture(db_path)
    first = rebuild_knowledge_graph(db_path, active_snapshots=snapshots)
    repo = KnowledgeGraphRepository(db_path)
    node_list_1 = repo.list_nodes(limit=200)
    edge_list_1 = repo.list_edges(limit=500)
    second = rebuild_knowledge_graph(db_path, active_snapshots=snapshots)
    node_list_2 = repo.list_nodes(limit=200)
    edge_list_2 = repo.list_edges(limit=500)

    assert first["node_count"] == second["node_count"]
    assert first["edge_count"] == second["edge_count"]
    assert {n["node_id"] for n in node_list_1} == {n["node_id"] for n in node_list_2}
    assert {e["edge_id"] for e in edge_list_1} == {e["edge_id"] for e in edge_list_2}

    software = next(n for n in node_list_2 if n["label"] == "Software Developers")
    assert software["source_references"]
    assert all(source["source_record_id"].startswith("snap-onet:") for source in software["source_references"])
    assert all(source["source_version"] == "fixture-snap-onet" for source in software["source_references"])
    assert "not a statement about an individual student's ability" in software["source_references"][0]["notes"][0]


def test_graph_status_marks_projection_stale_when_active_snapshot_changes(tmp_path):
    db_path = tmp_path / "graph.db"
    snapshots = seed_graph_fixture(db_path)
    rebuild_knowledge_graph(db_path, active_snapshots=snapshots)
    status = graph_status(db_path, active_snapshots={**snapshots, "test_onet": "snap-onet-v2"})
    assert status["is_stale"] is True
    assert status["built_from_active_snapshots"] == snapshots
    assert status["active_snapshots"]["test_onet"] == "snap-onet-v2"


def test_graph_builder_surfaces_dangling_taxonomy_relationship(tmp_path):
    db_path = tmp_path / "graph.db"
    repo = ProvenanceRepository(db_path)
    dangling_relation = make_bundle(
        source_id="test_esco", snapshot="snap-esco", source_record_suffix="relation:dangling",
        entity_id="entity:dangling-relation", entity_type=EntityType.OCCUPATION_SKILL_OBSERVATION,
        title="dangling occupation-skill relationship", taxonomy="ESCO", external_id="https://example.org/relationship/dangling",
        geography="European Union classification context",
        normalized={"occupation_uri": "http://data.europa.eu/esco/occupation/missing", "skill_uri": "http://data.europa.eu/esco/skill/missing", "taxonomy": "ESCO"},
        fact_specs=[("fact:dangling:relation", "occupation_skill_relation", "Dangling fixture relationship.", {})],
    )
    repo.upsert_bundles([dangling_relation])
    result = rebuild_knowledge_graph(db_path, active_snapshots={"test_esco": "snap-esco"})
    assert result["unresolved_relationship_count"] == 1
    assert result["unresolved_relationships"][0]["reason"].startswith("One or both active-snapshot endpoints")
    assert result["edges_by_relation"] == {}


def test_graph_failed_build_does_not_accept_invalid_state(tmp_path):
    state_path = tmp_path / "broken-state.json"
    state_path.write_text("{not valid", encoding="utf-8")
    with pytest.raises(KnowledgeGraphError, match="unavailable or invalid"):
        load_active_snapshots(state_path)


def test_graph_rejects_cross_snapshot_node_references_via_active_filter(tmp_path):
    db_path = tmp_path / "graph.db"
    snapshots = seed_graph_fixture(db_path)
    result = rebuild_knowledge_graph(db_path, active_snapshots=snapshots)
    assert "Old stale occupation" not in [node["label"] for node in KnowledgeGraphRepository(db_path).list_nodes(limit=200)]
    assert result["active_snapshots"] == snapshots


def test_knowledge_graph_status_api_reports_snapshot_scoping():
    response = TestClient(app).get("/api/knowledge-graph/status")
    assert response.status_code == 200
    body = response.json()
    assert body["source_data_is_live"] is False
    assert "active_snapshots" in body
    assert "is_stale" in body


def test_knowledge_graph_api_bounds_pagination():
    response = TestClient(app).get("/api/knowledge-graph/nodes?limit=201")
    assert response.status_code == 422


def test_bundled_curated_snapshot_builds_source_cited_skill_reference_nodes(tmp_path):
    db_path = tmp_path / "curated-knowledge-graph.db"
    state_path = tmp_path / "curated-state.json"
    repo = ProvenanceRepository(db_path)
    import_report = import_curated_snapshot(
        "data/curated/occupations_snapshot.json",
        repository=repo,
        state_path=state_path,
        manifest_path="data/sources_manifest.yaml",
    )
    assert import_report.records_processed == 10
    assert import_report.facts_upserted == 32

    status = rebuild_knowledge_graph(db_path, state_path=state_path)
    assert status["status"] == "built"
    assert status["nodes_by_type"]["occupation"] == 10
    assert status["nodes_by_type"]["skill"] == 45
    assert status["edges_by_relation"]["occupation_has_skill"] == 45
    assert status["source_data_is_live"] is False

    graph = KnowledgeGraphRepository(db_path)
    careers = graph.list_careers(limit=100)
    assert len(careers) == 10
    software = next(item for item in careers if item["label"] == "Software Developers" and item["taxonomy"] == "O*NET OnLine")
    assert software["attributes"]["curation_domain"] == "technology"
    assert software["attributes"]["curation_domain_is_editorial"] is True
    assert len(software["skills"]) == 5
    assert all(skill["node_type"] == "skill" for skill in software["skills"])
    assert all(skill["external_id"] is None for skill in software["skills"])
    assert all(skill["attributes"]["source_concept_id_captured"] is False for skill in software["skills"])
    assert all(skill["attributes"]["not_student_evidence"] is True for skill in software["skills"])
    assert all(skill["source_references"] for skill in software["skills"])
    assert all("Essential Skills" in skill["taxonomy"] for skill in software["skills"])

    skill_edges = graph.list_edges(relation_type="occupation_has_skill", limit=100)
    assert len(skill_edges) == 45
    assert all(edge["review_status"] == "sourced" for edge in skill_edges)
    assert all(edge["attributes"]["occupation_specific_rating_included"] is False for edge in skill_edges)
    assert all(edge["source_references"] for edge in skill_edges)
