from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.services.ingestion.cli import main

client = TestClient(app)


def test_ingestion_status_api_reports_static_snapshot_semantics_without_paths():
    response = client.get("/api/ingestion/status")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["manifest_version"] == 3
    assert body["source_data_is_live"] is False
    assert "sources" in body
    ids = {item["id"] for item in body["sources"]}
    assert {"onet_database", "esco_classification", "ncs_india", "nsdc_india"}.issubset(ids)
    assert "database_path" not in body
    assert all("file_path" not in item for item in body["sources"])
    assert body["sources"]
    by_id = {item["id"]: item for item in body["sources"]}
    for curated_id in ("onet_online_curated_sample", "esco_curated_sample"):
        active = by_id[curated_id]["active_snapshot"]
        assert active is not None
        assert active["snapshot_id"]
        assert active["snapshot_kind"] == "curated_extract"
        assert active["source_data_is_live"] is False
        assert active["normalizer_schema_version"] == "2"
        assert active["artifact_sha256"]


def test_ingestion_status_api_redacts_raw_paths_from_error_details(tmp_path, monkeypatch):
    import app.api.ingestion as ingestion_api

    private_path = str(tmp_path / "private" / "input.csv")
    state_path = tmp_path / "state-with-private-error.json"
    state_path.write_text(json.dumps({
        "schema_version": 1,
        "sources": {
            "onet_database": {
                "last_attempt": {
                    "source_id": "onet_database",
                    "status": "import_failed",
                    "error": f"Could not read {private_path}",
                }
            }
        },
        "runs": [{
            "source_id": "onet_database",
            "status": "import_failed",
            "started_at": "2026-10-17T12:00:00Z",
            "finished_at": "2026-10-17T12:00:01Z",
            "error": f"Could not read {private_path}",
        }],
    }), encoding="utf-8")
    monkeypatch.setattr(ingestion_api, "STATE_PATH", state_path)

    body = client.get("/api/ingestion/status").json()
    onet = next(item for item in body["sources"] if item["id"] == "onet_database")
    assert onet["last_error"] is not None
    assert private_path not in json.dumps(body)
    assert "detailed diagnostic" in onet["last_error"]


def test_cli_import_curated_snapshot_uses_temp_database_and_reports_static_extract(tmp_path, capsys):
    snapshot = Path("data/curated/occupations_snapshot.json")
    manifest = Path("data/sources_manifest.yaml")
    database = tmp_path / "skillscope-test.db"
    state = tmp_path / "state.json"

    code = main([
        "import-curated",
        "--snapshot", str(snapshot),
        "--manifest", str(manifest),
        "--database", str(database),
        "--state-file", str(state),
    ])

    assert code == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "curated_extract_imported"
    assert result["records_processed"] == 10
    assert result["facts_upserted"] == 32
    assert result["details"]["runtime_fetch_performed"] is False
    assert database.exists()
    persisted = json.loads(state.read_text(encoding="utf-8"))
    assert persisted["runs"]
    assert all(run["source_data_is_live"] is False for run in persisted["runs"])
