"""Build a truthful, auditable data-source catalogue for students and reviewers.

The service combines the reviewed YAML manifest with actual ingestion-state metadata. It
never infers that a public page or a curated extract is a live data integration.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml

from app.services.ingestion.common import MANIFEST_PATH, STATE_PATH
from app.services.provenance import DEFAULT_DB_PATH
from app.services.knowledge_graph import load_active_snapshots


class SourceRegistryError(RuntimeError):
    """Source audit metadata is invalid or unavailable."""


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "sources": {}, "runs": []}
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceRegistryError("Ingestion state is unavailable or invalid.") from exc
    if not isinstance(result, dict):
        raise SourceRegistryError("Ingestion state must be a JSON object.")
    if not isinstance(result.get("sources", {}), dict):
        raise SourceRegistryError("Ingestion state sources must be an object.")
    return result


def _read_manifest(path: Path) -> dict[str, Any]:
    try:
        result = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise SourceRegistryError("Source manifest is unavailable or invalid.") from exc
    if not isinstance(result, dict) or not isinstance(result.get("sources"), list):
        raise SourceRegistryError("Source manifest must contain a sources list.")
    seen: set[str] = set()
    for item in result["sources"]:
        if not isinstance(item, dict) or not isinstance(item.get("id"), str) or not item["id"].strip():
            raise SourceRegistryError("Every source manifest entry must have a source ID.")
        if item["id"] in seen:
            raise SourceRegistryError("Source manifest contains duplicate source IDs.")
        seen.add(item["id"])
        if not isinstance(item.get("official_url"), str) or not item["official_url"].startswith("https://"):
            raise SourceRegistryError(f"Source {item['id']} has no valid HTTPS official URL.")
        if not isinstance(item.get("limits"), list):
            raise SourceRegistryError(f"Source {item['id']} must include a limitations list.")
    return result


def _status(source: dict[str, Any], imported: dict[str, Any], state_success: dict[str, Any]) -> tuple[str, str, bool]:
    explicit_live = state_success.get("source_data_is_live") is True or imported.get("source_data_is_live") is True
    if explicit_live:
        return "live", "The last successful runtime operation explicitly declared live source data.", True
    integration = str(source.get("integration_status", "unknown"))
    if imported.get("status") == "imported" and imported.get("snapshot_id"):
        if "curated" in integration or imported.get("snapshot_kind") == "curated_extract":
            return "curated", "A static curated extract is imported; this is not a live feed or a full upstream dataset.", False
        return "cached", "A versioned local snapshot is imported; the source is not live.", False
    if state_success.get("status") == "curated_extract_imported" and state_success.get("snapshot_id"):
        return "curated", "An imported curated extract is available; it is not live or exhaustive.", False
    if "curated_extract_imported_not_full_source_integrated" in integration:
        return "curated", "Only a selected curated extract is integrated, not the full source taxonomy.", False
    selection = str(source.get("selection", "")).casefold()
    planned = str(source.get("planned_access_method", "")).casefold()
    if ("link_only" in selection or "link-only" in planned or "context_only_link_first" in selection
            or "excluded_from_mvp_instrument_copy" in selection):
        return "link_only", "The official source is linked for manual review; source content is not imported by this app.", False
    return "unavailable", "No successful local integration is recorded. The official link is provided for reference only.", False


def _as_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, (str, int, float))]


def _decode_metadata_value(value: Any) -> Any:
    """Decode the graph repository's JSON-encoded metadata, tolerating legacy fixtures."""
    if not isinstance(value, str):
        return value
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        # Older test databases and hand-created diagnostics may store a raw scalar.
        return value


def _db_audit(
    db_path: Path,
    *,
    active_snapshots: dict[str, str] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    mappings: list[dict[str, Any]] = []
    graph_summary: dict[str, Any] = {
        "status": "not_built", "node_count": 0, "edge_count": 0,
        "unresolved_crosswalk_count": 0, "unresolved_relationship_count": 0,
        "built_at": None, "is_stale": False,
        "active_snapshots": dict(sorted((active_snapshots or {}).items())),
        "built_from_active_snapshots": {}, "limitations": [],
    }
    if not db_path.exists():
        return conflicts, mappings, graph_summary
    try:
        with sqlite3.connect(str(db_path)) as db:
            db.row_factory = sqlite3.Row
            tables = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if "source_records" in tables:
                rows = db.execute("""SELECT source_id, source_record_id, publisher, title, record_uri,
                        source_version, geography, limitations_json FROM source_records
                        WHERE lower(quality_status)='conflicted'
                        ORDER BY source_id, source_record_id LIMIT 200""").fetchall()
                for row in rows:
                    try:
                        limits = json.loads(row["limitations_json"] or "[]")
                    except (json.JSONDecodeError, TypeError):
                        limits = []
                    conflicts.append({
                        "source_id": row["source_id"], "source_record_id": row["source_record_id"], "internal_id": None,
                        "publisher": row["publisher"], "title": row["title"], "record_uri": row["record_uri"],
                        "source_version": row["source_version"], "geography": row["geography"],
                        "limitations": _as_list(limits),
                        "explanation": "This source record is explicitly marked conflicted in the provenance registry; do not treat it as resolved.",
                    })
            if {"canonical_entities", "source_records"} <= tables:
                rows = db.execute("""SELECT e.internal_id, e.source_id, e.source_record_id, e.source_title,
                        e.publisher, e.source_uri, e.source_version, e.geography, e.limitations_json
                        FROM canonical_entities e WHERE lower(e.quality_status)='conflicted'
                        ORDER BY e.source_id, e.source_record_id, e.internal_id LIMIT 200""").fetchall()
                existing = {(item["source_id"], item["source_record_id"], item.get("internal_id")) for item in conflicts}
                for row in rows:
                    key = (row["source_id"], row["source_record_id"], row["internal_id"])
                    if key in existing:
                        continue
                    try:
                        limits = json.loads(row["limitations_json"] or "[]")
                    except (json.JSONDecodeError, TypeError):
                        limits = []
                    conflicts.append({
                        "source_id": row["source_id"], "source_record_id": row["source_record_id"],
                        "internal_id": row["internal_id"], "publisher": row["publisher"],
                        "title": row["source_title"], "record_uri": row["source_uri"],
                        "source_version": row["source_version"], "geography": row["geography"],
                        "limitations": _as_list(limits),
                        "explanation": "This canonical entity is explicitly marked conflicted in the provenance registry; its normalization/mapping must be reviewed before use.",
                    })
            graph_tables = {"knowledge_graph_nodes", "knowledge_graph_edges"} <= tables
            if graph_tables:
                rows = db.execute("""SELECT e.edge_id, e.from_node_id, f.label AS from_label,
                        e.to_node_id, t.label AS to_label, e.relation_type, e.mapping_type,
                        e.review_status, e.description, e.notes_json
                        FROM knowledge_graph_edges e
                        JOIN knowledge_graph_nodes f ON f.node_id=e.from_node_id
                        JOIN knowledge_graph_nodes t ON t.node_id=e.to_node_id
                        WHERE e.relation_type IN ('related_occupation','related_work_activity','crosswalk_candidate')
                          AND (e.mapping_type!='exact' OR e.review_status IN ('unresolved','proposed'))
                        ORDER BY e.review_status, e.mapping_type, f.label, t.label LIMIT 200""").fetchall()
                for row in rows:
                    try:
                        notes = _as_list(json.loads(row["notes_json"] or "[]"))
                    except (json.JSONDecodeError, TypeError):
                        notes = []
                    refs: list[dict[str, Any]] = []
                    if "knowledge_graph_edge_sources" in tables and "source_records" in tables:
                        try:
                            source_rows = db.execute("""SELECT s.source_id, s.source_record_id, s.title,
                                    s.publisher, s.record_uri, s.source_version, s.geography, s.quality_status
                                    FROM knowledge_graph_edge_sources es JOIN source_records s
                                    ON s.source_id=es.source_id AND s.source_record_id=es.source_record_id
                                    WHERE es.edge_id=? ORDER BY s.source_id, s.source_record_id""",
                                                     (row["edge_id"],)).fetchall()
                            refs = [{key: source_row[key] for key in source_row.keys()} for source_row in source_rows]
                        except sqlite3.Error:
                            refs = []
                    mappings.append({
                        "edge_id": row["edge_id"], "from_label": row["from_label"], "to_label": row["to_label"],
                        "relation_type": row["relation_type"], "mapping_type": row["mapping_type"],
                        "review_status": row["review_status"], "description": row["description"],
                        "notes": notes, "source_references": refs,
                        "explanation": "This is a non-exact cross-taxonomy mapping or unresolved review state, not proof that the source facts contradict each other.",
                    })
            def count(table: str) -> int:
                return int(db.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]) if table in tables else 0

            graph_summary.update({
                "node_count": count("knowledge_graph_nodes"),
                "edge_count": count("knowledge_graph_edges"),
                "unresolved_crosswalk_count": sum(1 for item in mappings if item["review_status"] == "unresolved"),
            })
            if "knowledge_graph_edges" in tables:
                graph_summary["unresolved_relationship_count"] = int(db.execute(
                    "SELECT COUNT(*) FROM knowledge_graph_edges WHERE review_status='unresolved'"
                ).fetchone()[0])
            if "knowledge_graph_metadata" in tables:
                metadata_rows = db.execute("SELECT metadata_key, metadata_value FROM knowledge_graph_metadata").fetchall()
                metadata = {row["metadata_key"]: _decode_metadata_value(row["metadata_value"]) for row in metadata_rows}
                built_snapshots = metadata.get("active_snapshots", {})
                if not isinstance(built_snapshots, dict) or any(not isinstance(k, str) or not isinstance(v, str)
                                                                for k, v in built_snapshots.items()):
                    built_snapshots = {}
                current_snapshots = dict(sorted((active_snapshots or {}).items()))
                graph_summary.update({
                    "status": "ready" if metadata else "not_built",
                    "built_at": metadata.get("built_at"),
                    "built_from_active_snapshots": dict(sorted(built_snapshots.items())),
                    "active_snapshots": current_snapshots,
                    "is_stale": bool(metadata) and dict(sorted(built_snapshots.items())) != current_snapshots,
                    "graph_schema_version": metadata.get("graph_schema_version"),
                    "builder_version": metadata.get("builder_version"),
                    "limitations": _as_list(metadata.get("limitations")),
                })
    except sqlite3.Error:
        graph_summary["status"] = "unavailable"
    return conflicts, mappings, graph_summary


def get_source_registry(
    *, manifest_path: str | Path = MANIFEST_PATH,
    state_path: str | Path = STATE_PATH,
    db_path: str | Path = DEFAULT_DB_PATH,
) -> dict[str, Any]:
    manifest = _read_manifest(Path(manifest_path))
    state = _read_state(Path(state_path))
    runtime_sources = state.get("sources", {})
    sources: list[dict[str, Any]] = []
    for source in manifest["sources"]:
        source_id = source["id"]
        runtime = runtime_sources.get(source_id, {}) if isinstance(runtime_sources, dict) else {}
        attempt = runtime.get("last_attempt", {}) if isinstance(runtime, dict) else {}
        state_success = runtime.get("last_successful_operation", {}) if isinstance(runtime, dict) else {}
        if not isinstance(attempt, dict):
            attempt = {}
        if not isinstance(state_success, dict):
            state_success = {}
        imported = source.get("last_import") if isinstance(source.get("last_import"), dict) else {}
        status, status_explanation, is_live = _status(source, imported, state_success)
        last_sync = state_success.get("finished_at") or imported.get("imported_at")
        snapshot_id = imported.get("snapshot_id") or state_success.get("snapshot_id")
        checksum = imported.get("checksum_sha256") or state_success.get("snapshot_sha256") or state_success.get("file_sha256")
        reference_urls = _as_list(source.get("evidence_urls"))
        extra_urls = [source.get(key) for key in ("listing_url", "download_url", "api_url", "release_archive_url")]
        reference_urls = list(dict.fromkeys(reference_urls + [url for url in extra_urls if isinstance(url, str) and url.startswith("https://")]))
        terms_url = source.get("terms_url") or source.get("license_url") or source.get("license_terms_url")
        sources.append({
            "source_id": source_id, "publisher": str(source.get("publisher") or "Publisher not recorded"),
            "name": str(source.get("name") or source_id), "official_url": source.get("official_url"),
            "reference_urls": reference_urls, "terms_url": terms_url if isinstance(terms_url, str) else None,
            "geography": source.get("geographic_scope"), "source_role": str(source.get("source_role") or "Role not recorded"),
            "source_version_or_release": imported.get("source_version") or source.get("version_or_release"),
            "reviewed_on": source.get("reviewed_on"), "integration_status": str(source.get("integration_status") or "unknown"),
            "runtime_access_status": str(source.get("runtime_access_status") or "unknown"),
            "status": status, "status_explanation": status_explanation,
            "last_successful_sync_at": str(last_sync) if last_sync else None,
            "last_attempt_at": str(attempt.get("finished_at")) if attempt.get("finished_at") else None,
            "last_attempt_status": str(attempt.get("status")) if attempt.get("status") else None,
            "active_snapshot_id": str(snapshot_id) if snapshot_id else None,
            "checksum_sha256": str(checksum) if checksum else None,
            "license_terms_status": str(source.get("license_terms_status") or "Reuse terms not recorded"),
            "limitations": _as_list(source.get("limits")), "source_data_is_live": is_live,
        })
    # Use the exact snapshot selection logic used by the graph builder so the audit
    # can identify a graph that was built from an older active source snapshot.
    active_snapshots = load_active_snapshots(Path(state_path))
    conflicts, mappings, graph_summary = _db_audit(Path(db_path), active_snapshots=active_snapshots)
    any_live = any(source["source_data_is_live"] for source in sources)
    notes = [
        "Manifest review date is not a sync date. A missing last-successful-sync timestamp means no successful app-side retrieval/import timestamp is recorded.",
        "Curated means a small selected local extract; cached means a versioned imported snapshot. Neither means live.",
        "No source records marked conflicted is not evidence that every external source agrees. Non-exact cross-taxonomy mappings are shown separately.",
        "The source registry is operational metadata, not a claim that unintegrated sources have been ingested.",
    ]
    return {
        "manifest_version": manifest.get("manifest_version"), "manifest_last_reviewed": manifest.get("last_reviewed"),
        "manifest_status": str(manifest.get("manifest_status") or "unknown"),
        "generated_at": datetime.now(UTC).isoformat(), "sources": sources,
        "conflicted_source_records": conflicts, "mapping_uncertainties": mappings,
        "graph_status": graph_summary, "source_data_is_live": any_live,
        "notes": notes,
    }
