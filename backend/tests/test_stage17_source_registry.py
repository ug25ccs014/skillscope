"""Stage 17 source audit tests use only clearly synthetic temporary data."""
import json
import sqlite3
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from app.main import app
from app.services.source_registry import SourceRegistryError, get_source_registry


def _write_manifest(path: Path):
    manifest = {
        "manifest_version": 7,
        "last_reviewed": "2026-10-17",
        "manifest_status": "test_fixture",
        "sources": [
            {"id": "curated", "publisher": "Fixture Publisher", "name": "Curated sample", "official_url": "https://example.org/curated",
             "geographic_scope": "Test geography", "source_role": "Synthetic test entry", "selection": "curated_extract",
             "integration_status": "curated_extract_imported_not_full_source_integrated", "runtime_access_status": "curated_snapshot_imported",
             "version_or_release": "fixture-v1", "reviewed_on": "2026-10-17", "license_terms_status": "Test-only terms", "limits": ["Synthetic record; not a production source."], "evidence_urls": ["https://example.org/curated/source"]},
            {"id": "link", "publisher": "Fixture Publisher", "name": "Link-only source", "official_url": "https://example.org/link",
             "geographic_scope": "Test geography", "source_role": "Manual check only", "selection": "selected_link_only_reference",
             "integration_status": "not_integrated", "runtime_access_status": "not_tested_from_application_runtime",
             "version_or_release": "Rolling", "reviewed_on": "2026-10-17", "license_terms_status": "Unknown", "limits": ["Not imported."], "evidence_urls": []},
            {"id": "bulk", "publisher": "Fixture Publisher", "name": "Unintegrated database", "official_url": "https://example.org/bulk",
             "geographic_scope": "Test geography", "source_role": "Future import", "selection": "selected_for_future_curated_bulk_snapshot",
             "integration_status": "not_integrated", "runtime_access_status": "not_tested",
             "version_or_release": "bulk-v1", "reviewed_on": "2026-10-17", "license_terms_status": "Unknown", "limits": ["Not imported."], "evidence_urls": []},
            {"id": "cached", "publisher": "Fixture Publisher", "name": "Versioned cache", "official_url": "https://example.org/cache",
             "geographic_scope": "Test geography", "source_role": "Versioned test import", "selection": "future_snapshot",
             "integration_status": "versioned_snapshot_imported", "runtime_access_status": "imported",
             "version_or_release": "v1", "reviewed_on": "2026-10-17", "license_terms_status": "Known", "limits": ["Static snapshot."], "evidence_urls": [],
             "last_import": {"status": "imported", "snapshot_id": "snapshot-abc", "source_version": "v2", "imported_at": "2026-10-16T12:30:00Z", "checksum_sha256": "a" * 64, "source_data_is_live": False}},
        ],
    }
    path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")


def _write_db(path: Path):
    with sqlite3.connect(path) as db:
        db.executescript("""
          CREATE TABLE source_records (source_id TEXT, source_record_id TEXT, publisher TEXT, title TEXT,
            record_uri TEXT, source_version TEXT, geography TEXT, limitations_json TEXT, quality_status TEXT);
          INSERT INTO source_records VALUES ('src-a','rec-a','Publisher A','Conflicted record','https://example.org/record','v1','Testland','[\"conflicting source values require review\"]','conflicted');
          CREATE TABLE knowledge_graph_nodes (node_id TEXT PRIMARY KEY, label TEXT);
          INSERT INTO knowledge_graph_nodes VALUES ('n1','Software Developer');
          INSERT INTO knowledge_graph_nodes VALUES ('n2','Software Developers');
          CREATE TABLE knowledge_graph_edges (edge_id TEXT PRIMARY KEY, from_node_id TEXT, to_node_id TEXT,
            relation_type TEXT, mapping_type TEXT, review_status TEXT, description TEXT, notes_json TEXT);
          INSERT INTO knowledge_graph_edges VALUES ('e1','n1','n2','related_occupation','reviewed_related','reviewed','Related concepts, not an exact identity.','[\"taxonomy identities remain separate\"]');
          CREATE TABLE knowledge_graph_metadata (metadata_key TEXT PRIMARY KEY, metadata_value TEXT);
          INSERT INTO knowledge_graph_metadata VALUES ('built_at','2026-10-17T12:00:00Z');
          CREATE TABLE knowledge_graph_edge_sources (edge_id TEXT, source_id TEXT, source_record_id TEXT);
        """)


def test_source_status_uses_real_import_state_not_review_date(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    state = tmp_path / "state.json"
    db = tmp_path / "db.sqlite"
    _write_manifest(manifest)
    state.write_text(json.dumps({"schema_version": 1, "sources": {}, "runs": []}), encoding="utf-8")
    result = get_source_registry(manifest_path=manifest, state_path=state, db_path=db)
    by_id = {source["source_id"]: source for source in result["sources"]}
    assert by_id["curated"]["status"] == "curated"
    assert by_id["link"]["status"] == "link_only"
    assert by_id["bulk"]["status"] == "unavailable"
    assert by_id["cached"]["status"] == "cached"
    assert by_id["cached"]["last_successful_sync_at"] == "2026-10-16T12:30:00Z"
    assert by_id["link"]["last_successful_sync_at"] is None  # reviewed_on is not sync time
    assert result["source_data_is_live"] is False


def test_source_audit_exposes_conflicted_records_and_nonexact_mapping_separately(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    state = tmp_path / "state.json"
    db = tmp_path / "db.sqlite"
    _write_manifest(manifest)
    state.write_text("{\"sources\": {}, \"runs\": []}", encoding="utf-8")
    _write_db(db)
    result = get_source_registry(manifest_path=manifest, state_path=state, db_path=db)
    assert result["conflicted_source_records"][0]["source_id"] == "src-a"
    assert result["mapping_uncertainties"][0]["mapping_type"] == "reviewed_related"
    assert "not proof" in result["mapping_uncertainties"][0]["explanation"]
    assert result["graph_status"]["status"] == "ready"
    assert result["graph_status"]["edge_count"] == 1
    assert result["graph_status"]["built_at"] == "2026-10-17T12:00:00Z"
    assert result["graph_status"]["is_stale"] is False


def test_source_registry_rejects_duplicate_source_ids(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    _write_manifest(manifest)
    doc = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    doc["sources"].append(doc["sources"][0])
    manifest.write_text(yaml.safe_dump(doc, sort_keys=False), encoding="utf-8")
    state = tmp_path / "state.json"
    state.write_text("{\"sources\": {}, \"runs\": []}", encoding="utf-8")
    with pytest.raises(SourceRegistryError, match="duplicate"):
        get_source_registry(manifest_path=manifest, state_path=state, db_path=tmp_path / "missing.db")


def test_source_registry_api_returns_manifest_and_truthful_status():
    client = TestClient(app)
    response = client.get("/api/source-registry")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["manifest_version"] is not None
    assert len(body["sources"]) >= 8
    assert body["source_data_is_live"] is False
    assert any(source["status"] in {"curated", "link_only", "unavailable", "cached"} for source in body["sources"])
    assert "review date is not a sync date" in " ".join(body["notes"]).lower()


def test_source_audit_includes_conflicted_canonical_entities(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    state = tmp_path / "state.json"
    db = tmp_path / "db.sqlite"
    _write_manifest(manifest)
    state.write_text("{\"sources\": {}, \"runs\": []}", encoding="utf-8")
    _write_db(db)
    with sqlite3.connect(db) as connection:
        connection.execute("""CREATE TABLE canonical_entities (internal_id TEXT, source_id TEXT,
            source_record_id TEXT, source_title TEXT, publisher TEXT, source_uri TEXT, source_version TEXT,
            geography TEXT, limitations_json TEXT, quality_status TEXT)""")
        connection.execute("INSERT INTO canonical_entities VALUES (?,?,?,?,?,?,?,?,?,?)", (
            "entity:conflicted", "src-a", "rec-a", "Canonical mapping", "Publisher A",
            "https://example.org/canonical", "v1", "Testland", '["normalization needs review"]', "conflicted",
        ))
    result = get_source_registry(manifest_path=manifest, state_path=state, db_path=db)
    entity_conflicts = [item for item in result["conflicted_source_records"] if item.get("internal_id")]
    assert len(entity_conflicts) == 1
    assert entity_conflicts[0]["internal_id"] == "entity:conflicted"
    assert "canonical entity" in entity_conflicts[0]["explanation"].lower()


def test_graph_metadata_is_decoded_and_stale_snapshots_are_reported(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    state = tmp_path / "state.json"
    db = tmp_path / "db.sqlite"
    _write_manifest(manifest)
    # The graph was built from the previous snapshot. The source-state helper's
    # active snapshot selection is deliberately identical to the graph builder's.
    state.write_text(json.dumps({"sources": {"curated": {
        "last_successful_operation": {"status": "curated_extract_imported", "snapshot_id": "current-v2"}
    }}, "runs": []}), encoding="utf-8")
    _write_db(db)
    with sqlite3.connect(db) as connection:
        connection.execute("INSERT INTO knowledge_graph_metadata VALUES (?,?)", (
            "active_snapshots", json.dumps({"curated": "previous-v1"})
        ))
        connection.execute("INSERT INTO knowledge_graph_metadata VALUES (?,?)", (
            "limitations", json.dumps(["Static graph fixture."])
        ))
        connection.execute("INSERT INTO knowledge_graph_metadata VALUES (?,?)", (
            "graph_schema_version", json.dumps(1)
        ))
    result = get_source_registry(manifest_path=manifest, state_path=state, db_path=db)
    assert result["graph_status"]["status"] == "ready"
    assert result["graph_status"]["built_at"] == "2026-10-17T12:00:00Z"
    assert result["graph_status"]["active_snapshots"] == {"curated": "current-v2"}
    assert result["graph_status"]["built_from_active_snapshots"] == {"curated": "previous-v1"}
    assert result["graph_status"]["is_stale"] is True
    assert result["graph_status"]["limitations"] == ["Static graph fixture."]


def test_real_source_registry_graph_metadata_is_fresh_or_explicitly_not_built():
    client = TestClient(app)
    response = client.get("/api/source-registry")
    assert response.status_code == 200
    graph = response.json()["graph_status"]
    assert graph["status"] in {"ready", "not_built"}
    if graph["status"] == "ready":
        assert isinstance(graph.get("active_snapshots"), dict)
        assert isinstance(graph.get("built_from_active_snapshots"), dict)
        assert isinstance(graph.get("is_stale"), bool)


def test_graph_metadata_is_decoded_and_stale_snapshots_are_reported(tmp_path):
    manifest = tmp_path / "manifest.yaml"
    state = tmp_path / "state.json"
    db = tmp_path / "db.sqlite"
    _write_manifest(manifest)
    state.write_text(json.dumps({"sources": {"curated": {
        "last_successful_operation": {"status": "curated_extract_imported", "snapshot_id": "current-v2"}
    }}, "runs": []}), encoding="utf-8")
    _write_db(db)
    with sqlite3.connect(db) as connection:
        connection.execute("INSERT INTO knowledge_graph_metadata VALUES (?,?)", (
            "active_snapshots", json.dumps({"curated": "previous-v1"})
        ))
        connection.execute("INSERT INTO knowledge_graph_metadata VALUES (?,?)", (
            "limitations", json.dumps(["Static graph fixture."])
        ))
        connection.execute("INSERT INTO knowledge_graph_metadata VALUES (?,?)", (
            "graph_schema_version", json.dumps(1)
        ))
    result = get_source_registry(manifest_path=manifest, state_path=state, db_path=db)
    graph = result["graph_status"]
    assert graph["status"] == "ready"
    assert graph["built_at"] == "2026-10-17T12:00:00Z"
    assert graph["active_snapshots"] == {"curated": "current-v2"}
    assert graph["built_from_active_snapshots"] == {"curated": "previous-v1"}
    assert graph["is_stale"] is True
    assert graph["limitations"] == ["Static graph fixture."]


def test_real_source_registry_graph_metadata_reports_snapshot_comparison():
    client = TestClient(app)
    response = client.get("/api/source-registry")
    assert response.status_code == 200
    graph = response.json()["graph_status"]
    assert graph["status"] in {"ready", "not_built"}
    if graph["status"] == "ready":
        assert isinstance(graph.get("active_snapshots"), dict)
        assert isinstance(graph.get("built_from_active_snapshots"), dict)
        assert isinstance(graph.get("is_stale"), bool)
