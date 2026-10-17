"""Read-only source/ingestion status API for diagnostics and a truthful UI status."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import APIRouter, HTTPException

from app.services.ingestion.common import MANIFEST_PATH, STATE_PATH
from app.services.provenance import ProvenanceRepository

router = APIRouter(prefix="/api/ingestion", tags=["Data ingestion"])


def _error_summary(event: dict[str, Any]) -> str | None:
    """Keep raw diagnostics in the local ledger; never echo arbitrary paths via the API."""
    if not event.get("error"):
        return None
    category = event.get("failure_type") or event.get("status") or "operation_failed"
    return f"{category}: detailed diagnostic is available in the local ingestion ledger."


def _active_snapshot(source: dict[str, Any], last_success: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve the active immutable snapshot without implying live-source access."""
    imported = source.get("last_import")
    if isinstance(imported, dict) and imported.get("status") == "imported" and imported.get("snapshot_id"):
        return {
            "snapshot_id": imported.get("snapshot_id"),
            "source_version": imported.get("source_version"),
            "normalizer_schema_version": imported.get("normalizer_schema_version"),
            "artifact_sha256": imported.get("checksum_sha256"),
            "imported_at": imported.get("imported_at"),
            "snapshot_kind": "versioned_source_snapshot",
            "source_data_is_live": False,
            "acquisition_method": imported.get("acquisition_method"),
        }

    if last_success.get("status") == "curated_extract_imported" and last_success.get("snapshot_id"):
        return {
            "snapshot_id": last_success.get("snapshot_id"),
            "source_version": last_success.get("source_version"),
            "normalizer_schema_version": last_success.get("normalizer_schema_version"),
            "artifact_sha256": last_success.get("snapshot_sha256"),
            "imported_at": last_success.get("finished_at"),
            "snapshot_kind": "curated_extract",
            "source_data_is_live": False,
        }
    return None


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "sources": {}, "runs": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Ingestion state file is unavailable or invalid.")
    if not isinstance(value, dict):
        raise HTTPException(status_code=503, detail="Ingestion state file must contain a JSON object.")
    return value


@router.get("/status")
def ingestion_status() -> dict[str, Any]:
    """Expose compact operation status without leaking raw filesystem paths or source files."""
    try:
        manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        raise HTTPException(status_code=503, detail="Source manifest is unavailable or invalid.")
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list):
        raise HTTPException(status_code=503, detail="Source manifest must contain a sources list.")

    state = _read_state(STATE_PATH)
    source_state = state.get("sources", {}) if isinstance(state.get("sources", {}), dict) else {}
    source_summaries: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        if not isinstance(source, dict) or not source.get("id"):
            continue
        source_id = str(source["id"])
        run = source_state.get(source_id, {})
        attempt = run.get("last_attempt", {}) if isinstance(run, dict) else {}
        success = run.get("last_successful_operation", {}) if isinstance(run, dict) else {}
        source_summaries.append({
            "id": source_id,
            "name": source.get("name"),
            "geographic_scope": source.get("geographic_scope"),
            "integration_status": source.get("integration_status", "unknown"),
            "runtime_access_status": source.get("runtime_access_status", "unknown"),
            "last_attempt_status": attempt.get("status") if isinstance(attempt, dict) else None,
            "last_attempt_at": attempt.get("finished_at") if isinstance(attempt, dict) else None,
            "last_success_status": success.get("status") if isinstance(success, dict) else None,
            "last_success_at": success.get("finished_at") if isinstance(success, dict) else None,
            "active_snapshot": _active_snapshot(source, success if isinstance(success, dict) else {}),
            "last_error": _error_summary(attempt) if isinstance(attempt, dict) else None,
        })
    repository = ProvenanceRepository()
    return {
        "status": "ready",
        "manifest_version": manifest.get("manifest_version"),
        "manifest_status": manifest.get("manifest_status"),
        "counts": repository.count(),
        "source_records_by_type": repository.source_type_counts(),
        "sources": source_summaries,
        "recent_runs": [
            {
                "source_id": item.get("source_id"),
                "status": item.get("status"),
                "started_at": item.get("started_at"),
                "finished_at": item.get("finished_at"),
                "source_version": item.get("source_version"),
                "file_sha256": item.get("sha256") or (item.get("report") or {}).get("file_sha256"),
                "error": _error_summary(item),
            }
            for item in state.get("runs", [])[-10:]
            if isinstance(item, dict)
        ],
        "source_data_is_live": False,
        "note": "Ingestion status reports the last known operation. A successful import is a static snapshot, not a live feed.",
    }
