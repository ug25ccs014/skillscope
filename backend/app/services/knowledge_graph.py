"""Build and query the source-traceable SkillScope career/skill graph.

The graph is a materialized, version-aware view of the canonical provenance registry. It
never merges unlike taxonomy identities, numeric scales, or student evidence. Its small
cross-taxonomy crosswalk is editorially reviewed, versioned, and visibly marked as related
rather than exact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from app.schemas.knowledge_graph import (
    GraphMappingType,
    GraphNodeType,
    GraphRelationType,
    MappingReviewStatus,
)
from app.services.provenance import DEFAULT_DB_PATH, ProvenanceRepository

try:
    from app.services.ingestion.common import STATE_PATH
except ImportError:  # pragma: no cover - defensive fallback for direct scripts
    STATE_PATH = Path(__file__).resolve().parents[3] / "data" / "ingestion_state.json"

GRAPH_SCHEMA_VERSION = 1
GRAPH_BUILDER_VERSION = "1.0.0"


class KnowledgeGraphError(RuntimeError):
    """Raised when graph construction would hide invalid or ambiguous source state."""


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9]+", "-", value.casefold()).strip("-")
    return value[:54] or "unnamed"


def _stable_id(prefix: str, *parts: str) -> str:
    raw = "\0".join(parts)
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
    readable = _slug(parts[-1])[:36] if parts else "node"
    return f"{prefix}:{readable}:{digest}"


def _taxonomy_for(source_id: str, normalized: Mapping[str, Any]) -> str:
    candidate = str(normalized.get("taxonomy") or "").strip()
    if candidate:
        return candidate
    if source_id.startswith("onet_online"):
        return "O*NET OnLine"
    if source_id.startswith("onet_database"):
        return "O*NET-SOC"
    if source_id.startswith("onet_"):
        return "O*NET"
    if source_id.startswith("esco_"):
        return "ESCO"
    if source_id.startswith("ncs_"):
        return "NCS India"
    if source_id.startswith("nsdc_"):
        return "NSDC India"
    return source_id


def _taxonomy_family(taxonomy: str, source_id: str = "") -> str:
    combined = f"{taxonomy} {source_id}".casefold()
    if "esco" in combined:
        return "ESCO"
    if "onet" in combined or "o*net" in combined:
        return "O*NET"
    if "ncs" in combined:
        return "NCS India"
    if "nsdc" in combined:
        return "NSDC India"
    return taxonomy or source_id or "unknown"


def load_active_snapshots(state_path: str | Path = STATE_PATH) -> dict[str, str]:
    """Return only successfully imported active source snapshot IDs.

    Download attempts, failed imports, and mere source-manifest rows are never treated as
    active snapshots. An invalid state file fails closed rather than mixing historical data.
    """
    path = Path(state_path)
    if not path.exists():
        return {}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise KnowledgeGraphError("Ingestion state is unavailable or invalid; refusing to build a mixed-snapshot graph.") from exc
    if not isinstance(state, dict) or not isinstance(state.get("sources", {}), dict):
        raise KnowledgeGraphError("Ingestion state has an invalid structure; refusing to build the graph.")
    active: dict[str, str] = {}
    for source_id, source_state in state.get("sources", {}).items():
        if not isinstance(source_state, dict):
            continue
        imported = source_state.get("last_import")
        success = source_state.get("last_successful_operation")
        if isinstance(imported, dict) and imported.get("status") == "imported" and imported.get("snapshot_id"):
            active[str(source_id)] = str(imported["snapshot_id"])
        elif (
            isinstance(success, dict)
            and success.get("status") == "curated_extract_imported"
            and success.get("snapshot_id")
        ):
            active[str(source_id)] = str(success["snapshot_id"])
    return dict(sorted(active.items()))


def _snapshot_fingerprint(snapshots: Mapping[str, str]) -> str:
    return hashlib.sha256(_json(dict(sorted(snapshots.items()))).encode("utf-8")).hexdigest()


class KnowledgeGraphRepository:
    """SQLite-backed graph projection with source/fact references enforced by foreign keys."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # Ensure the canonical provenance tables exist before graph tables declare FKs.
        ProvenanceRepository(self.db_path)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                PRAGMA foreign_keys = ON;
                CREATE TABLE IF NOT EXISTS knowledge_graph_nodes (
                    node_id TEXT PRIMARY KEY,
                    node_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    description TEXT,
                    taxonomy TEXT,
                    external_id TEXT,
                    geography TEXT,
                    evidence_class TEXT NOT NULL,
                    attributes_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS knowledge_graph_edges (
                    edge_id TEXT PRIMARY KEY,
                    from_node_id TEXT NOT NULL,
                    to_node_id TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    mapping_type TEXT NOT NULL,
                    review_status TEXT NOT NULL,
                    description TEXT,
                    attributes_json TEXT NOT NULL,
                    notes_json TEXT NOT NULL,
                    FOREIGN KEY (from_node_id) REFERENCES knowledge_graph_nodes(node_id) ON DELETE CASCADE,
                    FOREIGN KEY (to_node_id) REFERENCES knowledge_graph_nodes(node_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_kg_nodes_type ON knowledge_graph_nodes(node_type);
                CREATE INDEX IF NOT EXISTS idx_kg_nodes_label ON knowledge_graph_nodes(label);
                CREATE INDEX IF NOT EXISTS idx_kg_edges_from ON knowledge_graph_edges(from_node_id);
                CREATE INDEX IF NOT EXISTS idx_kg_edges_to ON knowledge_graph_edges(to_node_id);
                CREATE INDEX IF NOT EXISTS idx_kg_edges_relation ON knowledge_graph_edges(relation_type);
                CREATE TABLE IF NOT EXISTS knowledge_graph_node_sources (
                    node_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    fact_id TEXT,
                    evidence_role TEXT NOT NULL,
                    notes_json TEXT NOT NULL,
                    PRIMARY KEY (node_id, source_id, source_record_id, evidence_role, fact_id),
                    FOREIGN KEY (node_id) REFERENCES knowledge_graph_nodes(node_id) ON DELETE CASCADE,
                    FOREIGN KEY (source_id, source_record_id) REFERENCES source_records(source_id, source_record_id),
                    FOREIGN KEY (fact_id) REFERENCES career_facts(fact_id)
                );
                CREATE TABLE IF NOT EXISTS knowledge_graph_edge_sources (
                    edge_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    fact_id TEXT,
                    evidence_role TEXT NOT NULL,
                    notes_json TEXT NOT NULL,
                    PRIMARY KEY (edge_id, source_id, source_record_id, evidence_role, fact_id),
                    FOREIGN KEY (edge_id) REFERENCES knowledge_graph_edges(edge_id) ON DELETE CASCADE,
                    FOREIGN KEY (source_id, source_record_id) REFERENCES source_records(source_id, source_record_id),
                    FOREIGN KEY (fact_id) REFERENCES career_facts(fact_id)
                );
                CREATE TABLE IF NOT EXISTS knowledge_graph_metadata (
                    metadata_key TEXT PRIMARY KEY,
                    metadata_value TEXT NOT NULL
                );
                """
            )

    def read_active_entities(
        self,
        active_snapshots: Mapping[str, str],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Return canonical entities and facts strictly scoped to active source snapshots."""
        if not active_snapshots:
            return [], []
        with self._connect() as db:
            entities_raw = db.execute(
                """
                SELECT e.*, s.publisher AS source_publisher, s.title AS source_record_title,
                       s.source_type AS source_source_type, s.geography AS source_geography,
                       s.record_uri AS source_record_uri, s.source_uri AS source_base_uri,
                       s.source_version AS source_record_version, s.license_reference AS source_license,
                       s.quality_status AS source_quality, s.limitations_json AS source_limitations
                FROM canonical_entities e
                JOIN source_records s ON s.source_id = e.source_id AND s.source_record_id = e.source_record_id
                ORDER BY e.source_id, e.source_record_id, e.internal_id
                """
            ).fetchall()
            active_entities: list[dict[str, Any]] = []
            allowed_entity_ids: set[str] = set()
            for row in entities_raw:
                source_id = str(row["source_id"])
                snapshot_id = active_snapshots.get(source_id)
                if not snapshot_id or not str(row["source_record_id"]).startswith(snapshot_id + ":"):
                    continue
                item = dict(row)
                item["source_values"] = json.loads(item.pop("source_values_json"))
                item["normalized_values"] = json.loads(item.pop("normalized_values_json"))
                item["transformation_notes"] = json.loads(item.pop("transformation_notes_json"))
                item["limitations"] = json.loads(item.pop("limitations_json"))
                item["source_limitations"] = json.loads(item.pop("source_limitations"))
                active_entities.append(item)
                allowed_entity_ids.add(str(item["internal_id"]))
            if not allowed_entity_ids:
                return [], []
            facts_raw = db.execute(
                """
                SELECT f.*, e.source_id, e.source_record_id
                FROM career_facts f
                JOIN canonical_entities e ON e.internal_id = f.entity_internal_id
                ORDER BY f.fact_id
                """
            ).fetchall()
            facts: list[dict[str, Any]] = []
            for row in facts_raw:
                if str(row["entity_internal_id"]) not in allowed_entity_ids:
                    continue
                item = dict(row)
                item["value"] = json.loads(item.pop("value_json"))
                facts.append(item)
        return active_entities, facts

    def replace_graph(
        self,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        node_sources: list[dict[str, Any]],
        edge_sources: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> None:
        """Replace the projection in one transaction; a failed write keeps the prior graph."""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM knowledge_graph_edge_sources")
            db.execute("DELETE FROM knowledge_graph_edges")
            db.execute("DELETE FROM knowledge_graph_node_sources")
            db.execute("DELETE FROM knowledge_graph_nodes")
            for node in nodes:
                db.execute(
                    """INSERT INTO knowledge_graph_nodes
                    (node_id,node_type,label,description,taxonomy,external_id,geography,evidence_class,attributes_json)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (node["node_id"], node["node_type"], node["label"], node.get("description"),
                     node.get("taxonomy"), node.get("external_id"), node.get("geography"),
                     node["evidence_class"], _json(node.get("attributes", {}))),
                )
            node_ids = {node["node_id"] for node in nodes}
            for edge in edges:
                if edge["from_node_id"] not in node_ids or edge["to_node_id"] not in node_ids:
                    raise KnowledgeGraphError("A graph edge references a node outside the graph projection.")
                db.execute(
                    """INSERT INTO knowledge_graph_edges
                    (edge_id,from_node_id,to_node_id,relation_type,mapping_type,review_status,description,attributes_json,notes_json)
                    VALUES (?,?,?,?,?,?,?,?,?)""",
                    (edge["edge_id"], edge["from_node_id"], edge["to_node_id"], edge["relation_type"],
                     edge["mapping_type"], edge["review_status"], edge.get("description"),
                     _json(edge.get("attributes", {})), _json(edge.get("notes", []))),
                )
            for item in node_sources:
                db.execute(
                    """INSERT OR IGNORE INTO knowledge_graph_node_sources
                    (node_id,source_id,source_record_id,fact_id,evidence_role,notes_json)
                    VALUES (?,?,?,?,?,?)""",
                    (item["node_id"], item["source_id"], item["source_record_id"], item.get("fact_id"),
                     item["evidence_role"], _json(item.get("notes", []))),
                )
            for item in edge_sources:
                db.execute(
                    """INSERT OR IGNORE INTO knowledge_graph_edge_sources
                    (edge_id,source_id,source_record_id,fact_id,evidence_role,notes_json)
                    VALUES (?,?,?,?,?,?)""",
                    (item["edge_id"], item["source_id"], item["source_record_id"], item.get("fact_id"),
                     item["evidence_role"], _json(item.get("notes", []))),
                )
            db.execute("DELETE FROM knowledge_graph_metadata")
            for key, value in metadata.items():
                db.execute(
                    "INSERT INTO knowledge_graph_metadata(metadata_key,metadata_value) VALUES (?,?)",
                    (key, _json(value)),
                )

    def get_metadata(self) -> dict[str, Any]:
        with self._connect() as db:
            rows = db.execute("SELECT metadata_key, metadata_value FROM knowledge_graph_metadata").fetchall()
        return {row["metadata_key"]: json.loads(row["metadata_value"]) for row in rows}

    def status(self, active_snapshots: Mapping[str, str]) -> dict[str, Any]:
        metadata = self.get_metadata()
        with self._connect() as db:
            node_rows = db.execute("SELECT node_type, COUNT(*) AS n FROM knowledge_graph_nodes GROUP BY node_type").fetchall()
            edge_rows = db.execute("SELECT relation_type, COUNT(*) AS n FROM knowledge_graph_edges GROUP BY relation_type").fetchall()
            node_count = int(db.execute("SELECT COUNT(*) FROM knowledge_graph_nodes").fetchone()[0])
            edge_count = int(db.execute("SELECT COUNT(*) FROM knowledge_graph_edges").fetchone()[0])
            unresolved = int(db.execute(
                "SELECT COUNT(*) FROM knowledge_graph_edges WHERE review_status = 'unresolved'"
            ).fetchone()[0])
        built_snapshots = metadata.get("active_snapshots", {})
        return {
            "status": "ready" if metadata else "not_built",
            "graph_schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "built_at": metadata.get("built_at"),
            "node_count": node_count,
            "edge_count": edge_count,
            "nodes_by_type": {row["node_type"]: int(row["n"]) for row in node_rows},
            "edges_by_relation": {row["relation_type"]: int(row["n"]) for row in edge_rows},
            "active_snapshots": dict(sorted(active_snapshots.items())),
            "built_from_active_snapshots": built_snapshots,
            "is_stale": bool(metadata) and built_snapshots != dict(sorted(active_snapshots.items())),
            "unresolved_crosswalk_count": unresolved,
            "unresolved_relationship_count": int(metadata.get("unresolved_relationship_count", 0)),
            "unresolved_relationships": metadata.get("unresolved_relationships", []),
            "source_data_is_live": False,
            "limitations": metadata.get("limitations", ["The graph has not been built yet."]),
        }

    def list_nodes(
        self,
        *,
        node_type: str | None = None,
        query: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if node_type:
            where.append("n.node_type = ?")
            params.append(node_type)
        if query:
            where.append("(lower(n.label) LIKE ? OR lower(COALESCE(n.description,'')) LIKE ? OR lower(COALESCE(n.taxonomy,'')) LIKE ?)")
            needle = f"%{query.casefold()}%"
            params.extend([needle, needle, needle])
        sql = "SELECT n.* FROM knowledge_graph_nodes n"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY CASE n.node_type WHEN 'occupation' THEN 0 WHEN 'skill' THEN 1 ELSE 2 END, lower(n.label), n.node_id LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        with self._connect() as db:
            rows = db.execute(sql, params).fetchall()
            return [self._node_with_sources(db, dict(row)) for row in rows]

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM knowledge_graph_nodes WHERE node_id = ?", (node_id,)).fetchone()
            if row is None:
                return None
            result = self._node_with_sources(db, dict(row))
            edges = db.execute(
                """SELECT e.*, f.label AS from_label, t.label AS to_label
                FROM knowledge_graph_edges e
                JOIN knowledge_graph_nodes f ON f.node_id=e.from_node_id
                JOIN knowledge_graph_nodes t ON t.node_id=e.to_node_id
                WHERE e.from_node_id=? OR e.to_node_id=?
                ORDER BY e.relation_type, e.edge_id""",
                (node_id, node_id),
            ).fetchall()
            result["relationships"] = [self._edge_with_sources(db, dict(item)) for item in edges]
            return result

    def list_edges(
        self,
        *,
        relation_type: str | None = None,
        mapping_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if relation_type:
            where.append("e.relation_type = ?")
            params.append(relation_type)
        if mapping_type:
            where.append("e.mapping_type = ?")
            params.append(mapping_type)
        sql = """SELECT e.*, f.label AS from_label, t.label AS to_label
        FROM knowledge_graph_edges e
        JOIN knowledge_graph_nodes f ON f.node_id=e.from_node_id
        JOIN knowledge_graph_nodes t ON t.node_id=e.to_node_id"""
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY e.review_status, e.relation_type, f.label, t.label LIMIT ?"
        params.append(limit)
        with self._connect() as db:
            rows = db.execute(sql, params).fetchall()
            return [self._edge_with_sources(db, dict(row)) for row in rows]

    def list_careers(self, *, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        with self._connect() as db:
            rows = db.execute(
                """SELECT * FROM knowledge_graph_nodes WHERE node_type='occupation'
                ORDER BY lower(label), node_id LIMIT ? OFFSET ?""", (limit, offset)
            ).fetchall()
            careers = []
            for row in rows:
                node = self._node_with_sources(db, dict(row))
                edge_rows = db.execute(
                    """SELECT e.*, f.label AS from_label, t.label AS to_label
                    FROM knowledge_graph_edges e
                    JOIN knowledge_graph_nodes f ON f.node_id=e.from_node_id
                    JOIN knowledge_graph_nodes t ON t.node_id=e.to_node_id
                    WHERE e.from_node_id=? ORDER BY e.relation_type, t.label""",
                    (node["node_id"],),
                ).fetchall()
                outgoing = [self._edge_with_sources(db, dict(edge)) for edge in edge_rows]
                node["tasks"] = [
                    self._node_with_sources(db, dict(db.execute(
                        "SELECT * FROM knowledge_graph_nodes WHERE node_id=?", (edge["to_node_id"],)
                    ).fetchone()))
                    for edge in outgoing if edge["relation_type"] == GraphRelationType.PERFORMS_TASK.value
                ]
                node["occupational_terms"] = [
                    self._node_with_sources(db, dict(db.execute(
                        "SELECT * FROM knowledge_graph_nodes WHERE node_id=?", (edge["to_node_id"],)
                    ).fetchone()))
                    for edge in outgoing if edge["relation_type"] == GraphRelationType.ASSOCIATED_WITH_SOURCE_TERM.value
                ]
                node["skills"] = [
                    self._node_with_sources(db, dict(db.execute(
                        "SELECT * FROM knowledge_graph_nodes WHERE node_id=?", (edge["to_node_id"],)
                    ).fetchone()))
                    for edge in outgoing if edge["relation_type"] == GraphRelationType.OCCUPATION_HAS_SKILL.value
                ]
                node["relationships"] = outgoing
                node["citations"] = node["source_references"]
                careers.append(node)
            return careers

    @staticmethod
    def _node_with_sources(db: sqlite3.Connection, row: dict[str, Any]) -> dict[str, Any]:
        row["attributes"] = json.loads(row.pop("attributes_json", "{}"))
        sources = db.execute(
            """SELECT ns.source_id, ns.source_record_id, ns.fact_id, ns.evidence_role, ns.notes_json,
                      s.title, s.publisher, s.record_uri, s.source_version, s.source_type,
                      s.geography, s.quality_status, s.license_reference,
                      f.fact_type, f.statement
            FROM knowledge_graph_node_sources ns
            JOIN source_records s ON s.source_id=ns.source_id AND s.source_record_id=ns.source_record_id
            LEFT JOIN career_facts f ON f.fact_id=ns.fact_id
            WHERE ns.node_id=? ORDER BY s.source_id, s.source_record_id, ns.evidence_role, ns.fact_id""",
            (row["node_id"],),
        ).fetchall()
        row["source_references"] = [
            {
                "source_id": source["source_id"], "source_record_id": source["source_record_id"],
                "title": source["title"], "publisher": source["publisher"],
                "record_uri": source["record_uri"], "source_version": source["source_version"],
                "source_type": source["source_type"], "geography": source["geography"],
                "quality_status": source["quality_status"], "license_reference": source["license_reference"],
                "fact_id": source["fact_id"], "fact_type": source["fact_type"],
                "fact_statement": source["statement"], "evidence_role": source["evidence_role"],
                "notes": json.loads(source["notes_json"]),
            }
            for source in sources
        ]
        return row

    @classmethod
    def _edge_with_sources(cls, db: sqlite3.Connection, row: dict[str, Any]) -> dict[str, Any]:
        row["attributes"] = json.loads(row.pop("attributes_json", "{}"))
        row["notes"] = json.loads(row.pop("notes_json", "[]"))
        sources = db.execute(
            """SELECT es.source_id, es.source_record_id, es.fact_id, es.evidence_role, es.notes_json,
                      s.title, s.publisher, s.record_uri, s.source_version, s.source_type,
                      s.geography, s.quality_status, s.license_reference,
                      f.fact_type, f.statement
            FROM knowledge_graph_edge_sources es
            JOIN source_records s ON s.source_id=es.source_id AND s.source_record_id=es.source_record_id
            LEFT JOIN career_facts f ON f.fact_id=es.fact_id
            WHERE es.edge_id=? ORDER BY s.source_id, s.source_record_id, es.evidence_role, es.fact_id""",
            (row["edge_id"],),
        ).fetchall()
        row["source_references"] = [
            {
                "source_id": source["source_id"], "source_record_id": source["source_record_id"],
                "title": source["title"], "publisher": source["publisher"],
                "record_uri": source["record_uri"], "source_version": source["source_version"],
                "source_type": source["source_type"], "geography": source["geography"],
                "quality_status": source["quality_status"], "license_reference": source["license_reference"],
                "fact_id": source["fact_id"], "fact_type": source["fact_type"],
                "fact_statement": source["statement"], "evidence_role": source["evidence_role"],
                "notes": json.loads(source["notes_json"]),
            }
            for source in sources
        ]
        return row


class KnowledgeGraphBuilder:
    def __init__(self, repository: KnowledgeGraphRepository) -> None:
        self.repository = repository
        self.nodes: dict[str, dict[str, Any]] = {}
        self.edges: dict[str, dict[str, Any]] = {}
        self.node_sources: dict[tuple[Any, ...], dict[str, Any]] = {}
        self.edge_sources: dict[tuple[Any, ...], dict[str, Any]] = {}
        self.entity_nodes: dict[str, str] = {}
        self.external_nodes: dict[tuple[str, str], str] = {}
        self.occupation_nodes: list[dict[str, Any]] = []
        self.activity_nodes: list[dict[str, Any]] = []
        self.active_snapshots: dict[str, str] = {}
        self.unresolved_relationships: list[dict[str, Any]] = []
        self.facts_by_entity: dict[str, list[dict[str, Any]]] = {}

    def _add_node(
        self,
        node_type: GraphNodeType,
        label: str,
        *,
        taxonomy: str | None = None,
        external_id: str | None = None,
        description: str | None = None,
        geography: str | None = None,
        evidence_class: str = "sourced",
        attributes: dict[str, Any] | None = None,
        node_id: str | None = None,
    ) -> str:
        node_id = node_id or _stable_id(node_type.value, taxonomy or "", external_id or label)
        candidate = {
            "node_id": node_id,
            "node_type": node_type.value,
            "label": label.strip(),
            "description": description,
            "taxonomy": taxonomy,
            "external_id": external_id,
            "geography": geography,
            "evidence_class": evidence_class,
            "attributes": attributes or {},
        }
        previous = self.nodes.get(node_id)
        if previous:
            # Merge only metadata on the exact same namespaced graph identity. Conflicting
            # descriptions remain explicit alternatives rather than silently overwriting.
            if previous["label"].casefold() != candidate["label"].casefold():
                aliases = set(previous["attributes"].get("source_labels", []))
                aliases.update([previous["label"], candidate["label"]])
                previous["attributes"]["source_labels"] = sorted(aliases)
            if previous.get("description") and candidate.get("description") and previous["description"] != candidate["description"]:
                alternatives = previous["attributes"].setdefault("description_variants", [])
                if candidate["description"] not in alternatives and candidate["description"] != previous["description"]:
                    alternatives.append(candidate["description"])
            elif candidate.get("description") and not previous.get("description"):
                previous["description"] = candidate["description"]
            previous["attributes"].update({k: v for k, v in candidate["attributes"].items() if k not in previous["attributes"]})
            return node_id
        self.nodes[node_id] = candidate
        return node_id

    def _add_node_source(
        self, node_id: str, entity: Mapping[str, Any], *, fact: Mapping[str, Any] | None,
        evidence_role: str, notes: list[str] | None = None,
    ) -> None:
        fact_id = str(fact["fact_id"]) if fact else None
        source_id = str(entity["source_id"])
        source_record_id = str(entity["source_record_id"])
        key = (node_id, source_id, source_record_id, fact_id, evidence_role)
        self.node_sources[key] = {
            "node_id": node_id, "source_id": source_id, "source_record_id": source_record_id,
            "fact_id": fact_id, "evidence_role": evidence_role, "notes": notes or [],
        }

    def _add_edge(
        self,
        from_node_id: str,
        to_node_id: str,
        relation_type: GraphRelationType,
        *,
        mapping_type: GraphMappingType = GraphMappingType.EXACT,
        review_status: MappingReviewStatus = MappingReviewStatus.SOURCED,
        description: str | None = None,
        attributes: dict[str, Any] | None = None,
        notes: list[str] | None = None,
        identity: str = "",
    ) -> str:
        edge_id = _stable_id("edge", from_node_id, to_node_id, relation_type.value, identity)
        candidate = {
            "edge_id": edge_id, "from_node_id": from_node_id, "to_node_id": to_node_id,
            "relation_type": relation_type.value, "mapping_type": mapping_type.value,
            "review_status": review_status.value, "description": description,
            "attributes": attributes or {}, "notes": notes or [],
        }
        existing = self.edges.get(edge_id)
        if existing:
            existing["attributes"].update(candidate["attributes"])
            for note in candidate["notes"]:
                if note not in existing["notes"]:
                    existing["notes"].append(note)
        else:
            self.edges[edge_id] = candidate
        return edge_id

    def _add_edge_source(
        self, edge_id: str, entity: Mapping[str, Any], *, fact: Mapping[str, Any] | None,
        evidence_role: str, notes: list[str] | None = None,
    ) -> None:
        fact_id = str(fact["fact_id"]) if fact else None
        source_id = str(entity["source_id"])
        source_record_id = str(entity["source_record_id"])
        key = (edge_id, source_id, source_record_id, fact_id, evidence_role)
        self.edge_sources[key] = {
            "edge_id": edge_id, "source_id": source_id, "source_record_id": source_record_id,
            "fact_id": fact_id, "evidence_role": evidence_role, "notes": notes or [],
        }

    def build(
        self,
        active_snapshots: Mapping[str, str] | None = None,
        *,
        state_path: str | Path = STATE_PATH,
    ) -> dict[str, Any]:
        snapshots = dict(active_snapshots) if active_snapshots is not None else load_active_snapshots(state_path)
        snapshots = dict(sorted((str(k), str(v)) for k, v in snapshots.items()))
        entities, facts = self.repository.read_active_entities(snapshots)
        facts_by_entity: dict[str, list[dict[str, Any]]] = {}
        for fact in facts:
            facts_by_entity.setdefault(str(fact["entity_internal_id"]), []).append(fact)
        self.facts_by_entity = facts_by_entity

        # First pass: occupation, skill and qualification nodes retain taxonomy identity.
        observations: list[dict[str, Any]] = []
        for entity in entities:
            entity_type = str(entity["entity_type"])
            normalized = entity["normalized_values"]
            source_id = str(entity["source_id"])
            taxonomy = _taxonomy_for(source_id, normalized)
            family = _taxonomy_family(taxonomy, source_id)
            # ESCO concept URIs are the stable identity, including in a curated record where
            # the normalized fields may not copy the URI but the original source values do.
            external_id = str(
                normalized.get("concept_uri") or entity["source_values"].get("concept_uri") or
                normalized.get("code") or entity.get("source_code") or entity.get("source_uri") or entity["source_record_id"]
            )
            related_facts = facts_by_entity.get(str(entity["internal_id"]), [])

            if entity_type == "occupation":
                label = str(normalized.get("title") or normalized.get("preferred_label") or entity["source_title"])
                summary_fact = next((f for f in related_facts if f["fact_type"] in {
                    "occupation_profile_summary", "occupation_description", "esco_occupation_description",
                    "esco_occupation_definition", "esco_occupation_summary"
                }), None)
                description = None
                if summary_fact:
                    val = summary_fact["value"]
                    description = val.get("summary") or val.get("description") or val.get("definition")
                if not description:
                    description = normalized.get("description")
                node_id = self._add_node(
                    GraphNodeType.OCCUPATION, label, taxonomy=taxonomy, external_id=external_id,
                    description=str(description) if description else None, geography=entity.get("geography"),
                    evidence_class=str(entity["source_type"]),
                    attributes={
                        "source_code": entity.get("source_code") or normalized.get("code"),
                        "taxonomy_family": family,
                        "source_record_kind": normalized.get("record_kind"),
                        "curation_domain": normalized.get("curation_domain"),
                        "curation_domain_is_editorial": bool(normalized.get("curation_domain_is_editorial", False)),
                        "source_version": entity.get("source_version"),
                        "not_student_evidence": True,
                        "source_limitations": entity.get("limitations", []),
                        "transformation_notes": entity.get("transformation_notes", []),
                    },
                )
                self.entity_nodes[str(entity["internal_id"])] = node_id
                self.external_nodes[(family, external_id)] = node_id
                self.occupation_nodes.append({"node_id": node_id, "entity": entity, "family": family, "external_id": external_id, "label": label})
                self._add_node_source(node_id, entity, fact=summary_fact, evidence_role="occupation_profile", notes=[
                    "Source-linked occupational context only; not a statement about an individual student's ability or career suitability."
                ])
                if summary_fact:
                    # Also attach title and selected descriptive/task facts below, so a career
                    # card can expose the full small evidence bundle for reviewers.
                    for fact in related_facts:
                        if fact["fact_type"] in {"occupation_title", "occupation_description", "esco_occupation_description", "esco_occupation_definition"}:
                            self._add_node_source(node_id, entity, fact=fact, evidence_role="occupation_fact")

            elif entity_type == "skill":
                label = str(normalized.get("preferred_label") or normalized.get("title") or entity["source_title"])
                description = normalized.get("description") or normalized.get("definition") or normalized.get("scope_note")
                node_id = self._add_node(
                    GraphNodeType.SKILL, label, taxonomy=taxonomy, external_id=external_id,
                    description=str(description) if description else None, geography=entity.get("geography"),
                    evidence_class=str(entity["source_type"]),
                    attributes={
                        "taxonomy_family": family, "source_code": entity.get("source_code") or normalized.get("code"),
                        "source_version": entity.get("source_version"), "not_student_evidence": True,
                        "source_limitations": entity.get("limitations", []),
                    },
                )
                self.entity_nodes[str(entity["internal_id"])] = node_id
                self.external_nodes[(family, external_id)] = node_id
                self._add_node_source(node_id, entity, fact=None, evidence_role="taxonomy_skill_concept")
                for fact in related_facts:
                    if "skill" in fact["fact_type"] or "description" in fact["fact_type"] or "definition" in fact["fact_type"]:
                        self._add_node_source(node_id, entity, fact=fact, evidence_role="skill_concept_fact")

            elif entity_type == "qualification":
                label = str(normalized.get("title") or normalized.get("preferred_label") or entity["source_title"])
                node_id = self._add_node(
                    GraphNodeType.QUALIFICATION, label, taxonomy=taxonomy, external_id=external_id,
                    description=str(normalized.get("description") or "") or None,
                    geography=entity.get("geography"), evidence_class=str(entity["source_type"]),
                    attributes={"taxonomy_family": family, "source_version": entity.get("source_version"),
                                "source_limitations": entity.get("limitations", [])},
                )
                self.entity_nodes[str(entity["internal_id"])] = node_id
                self.external_nodes[(family, external_id)] = node_id
                self._add_node_source(node_id, entity, fact=None, evidence_role="qualification_concept")

            elif entity_type == "occupation_skill_observation":
                observations.append(entity)

        # Second pass: curated task paraphrases and source terms, with the exact fact line attached.
        for entity in entities:
            if str(entity["entity_type"]) != "occupation":
                continue
            occ_node_id = self.entity_nodes.get(str(entity["internal_id"]))
            if not occ_node_id:
                continue
            taxonomy = _taxonomy_for(str(entity["source_id"]), entity["normalized_values"])
            family = _taxonomy_family(taxonomy, str(entity["source_id"]))
            related_facts = facts_by_entity.get(str(entity["internal_id"]), [])
            for fact in related_facts:
                value = fact["value"] if isinstance(fact["value"], dict) else {}
                if fact["fact_type"] == "selected_occupational_tasks" and isinstance(value.get("tasks"), list):
                    for task in value["tasks"]:
                        if not isinstance(task, str) or not task.strip():
                            continue
                        task_label = task.strip()
                        task_node_id = self._add_node(
                            GraphNodeType.WORK_ACTIVITY, task_label, taxonomy=taxonomy,
                            external_id=task_label, geography=entity.get("geography"),
                            evidence_class=str(entity["source_type"]),
                            description="Selected task description from a manually curated occupational profile; it is a concise paraphrase, not a complete official task list.",
                            attributes={
                                "taxonomy_family": family, "source_fact_type": fact["fact_type"],
                                "phrase_is_paraphrase": True, "not_student_evidence": True,
                                "source_version": entity.get("source_version"),
                            },
                        )
                        self.activity_nodes.append({"node_id": task_node_id, "label": task_label, "family": family, "entity": entity, "fact": fact})
                        self._add_node_source(task_node_id, entity, fact=fact, evidence_role="selected_task",
                                             notes=["Task wording is a concise paraphrase stated in the curated snapshot, not a verbatim quotation."])
                        edge_id = self._add_edge(
                            occ_node_id, task_node_id, GraphRelationType.PERFORMS_TASK,
                            description="This task is included in the source-linked curated occupation profile.",
                            attributes={"relationship_basis": "selected_occupational_tasks", "task_is_complete_list": False},
                            identity=str(fact["fact_id"]),
                        )
                        self._add_edge_source(edge_id, entity, fact=fact, evidence_role="task_membership",
                                              notes=["Source link supports the task being associated with this occupation; it does not score a student."])
                elif fact["fact_type"] == "selected_essential_skills" and isinstance(value.get("skills"), list):
                    for skill_label in value["skills"]:
                        if not isinstance(skill_label, str) or not skill_label.strip():
                            continue
                        label = skill_label.strip()
                        # The O*NET OnLine profile's Essential Skills section names a skill
                        # label, but this curated extract does not carry the stable skill
                        # element ID. Keep an occupation-scoped reference node instead of
                        # merging identical labels into a falsely canonical concept.
                        skill_node_id = _stable_id(
                            "skill-reference", str(entity["source_record_id"]), label
                        )
                        skill_node = self._add_node(
                            GraphNodeType.SKILL, label,
                            taxonomy=f"{taxonomy} / Essential Skills reference labels",
                            description="A skill label listed for this occupation in the cited profile's Essential Skills section; no rating is included.",
                            geography=entity.get("geography"),
                            evidence_class=str(entity["source_type"]),
                            node_id=skill_node_id,
                            attributes={
                                "taxonomy_family": family,
                                "source_section": "Essential Skills",
                                "source_concept_id_captured": False,
                                "identity_basis": "occupation_scoped_source_label; not a canonical skill identifier",
                                "not_student_evidence": True,
                                "not_scored": True,
                                "source_version": entity.get("source_version"),
                            },
                        )
                        self._add_node_source(
                            skill_node, entity, fact=fact, evidence_role="selected_essential_skill_label",
                            notes=["The official profile lists this skill label for the occupation. The stable source skill element ID was not captured; do not merge with another taxonomy or interpret as a student score."],
                        )
                        edge_id = self._add_edge(
                            occ_node_id, skill_node, GraphRelationType.OCCUPATION_HAS_SKILL,
                            mapping_type=GraphMappingType.EXACT,
                            review_status=MappingReviewStatus.SOURCED,
                            description="The cited occupational profile lists this label in its Essential Skills section.",
                            attributes={
                                "source_section": "Essential Skills",
                                "source_skill_element_id_captured": False,
                                "occupation_specific_rating_included": False,
                                "not_student_evidence": True,
                            },
                            notes=["Source-listed occupational reference only; not an aptitude, interest, proficiency or fit score."],
                            identity=str(fact["fact_id"]) + ":" + _slug(label),
                        )
                        self._add_edge_source(
                            edge_id, entity, fact=fact, evidence_role="occupation_skill_reference",
                            notes=["Association is evidenced by the cited source profile's Essential Skills section. No score is included."],
                        )
                elif fact["fact_type"] == "selected_occupational_terms" and isinstance(value.get("terms"), list):
                    for term in value["terms"]:
                        if not isinstance(term, str) or not term.strip():
                            continue
                        term_label = term.strip()
                        term_node_id = self._add_node(
                            GraphNodeType.OCCUPATIONAL_TERM, term_label, taxonomy=taxonomy,
                            external_id=term_label, geography=entity.get("geography"),
                            evidence_class=str(entity["source_type"]),
                            description=("A selected occupational term copied into the curated extract. Its original source category is not captured, "
                                         "so SkillScope does not relabel it as a validated skill, interest, or student score."),
                            attributes={"taxonomy_family": family, "source_category_captured": False,
                                        "not_student_evidence": True, "source_version": entity.get("source_version")},
                        )
                        self._add_node_source(term_node_id, entity, fact=fact, evidence_role="selected_source_term",
                                              notes=["The original category/scale is not preserved in this curated extract."])
                        edge_id = self._add_edge(
                            occ_node_id, term_node_id, GraphRelationType.ASSOCIATED_WITH_SOURCE_TERM,
                            description="The term was recorded as associated with this occupation in the cited extract.",
                            attributes={"source_category_captured": False, "not_student_evidence": True},
                            identity=str(fact["fact_id"]),
                            notes=["Do not treat this relationship as a student's interest/ability result."],
                        )
                        self._add_edge_source(edge_id, entity, fact=fact, evidence_role="term_association")
                else:
                    # A task/term fact can coexist with a missing description. Keep it on the
                    # occupation node so reviewers can inspect evidence without losing lineage.
                    if fact["fact_type"] not in {"occupation_profile_summary", "selected_occupational_tasks", "selected_occupational_terms"}:
                        self._add_node_source(occ_node_id, entity, fact=fact, evidence_role="occupation_fact")

        # Third pass: create skill/occupation edges only from explicit source taxonomy concepts
        # or source occupation-skill observations. Source-specific numeric scales remain edge attributes.
        self._build_source_skill_edges(entities, observations)
        self._build_reviewed_crosswalks()

        built_at = _utc_now()
        nodes = sorted(self.nodes.values(), key=lambda item: (item["node_type"], item["label"].casefold(), item["node_id"]))
        edges = sorted(self.edges.values(), key=lambda item: (item["relation_type"], item["from_node_id"], item["to_node_id"], item["edge_id"]))
        active_source_ids = {str(entity["source_id"]) for entity in entities}
        limitations = ["Graph is a static projection of imported active snapshots, not a live occupational feed."]
        if "onet_database" not in active_source_ids:
            limitations.append("The full O*NET Database is not integrated in this active graph; the O*NET OnLine profiles are small curated extracts.")
        if "esco_classification" not in active_source_ids:
            limitations.append("The full ESCO classification package is not integrated in this active graph; the ESCO occupation is a small curated extract.")
        if not (active_source_ids & {"ncs_india", "ncs_occupations", "national_career_service"}):
            limitations.append("NCS is not integrated, so no India-first NCS crosswalk is claimed.")
        if not (active_source_ids & {"nsdc_india", "nsdc_nos", "national_occupational_standards"}):
            limitations.append("NSDC qualification packs/occupational standards are not integrated, so no NSDC qualification pathway is asserted.")
        skill_nodes = [node for node in nodes if node["node_type"] == GraphNodeType.SKILL.value]
        if not skill_nodes:
            limitations.append("No skill references are available in the current active records; capability hypotheses remain separate and are not official skill definitions.")
        elif any(not node.get("attributes", {}).get("source_concept_id_captured", True) for node in skill_nodes):
            limitations.append("Some O*NET OnLine skill nodes are occupation-scoped labels from the Essential Skills section; their stable element IDs and ratings are not captured, so identical labels are not merged into canonical skill concepts.")
        if any(node["node_type"] == GraphNodeType.OCCUPATIONAL_TERM.value for node in nodes):
            limitations.append("The curated extract does not preserve the exact source category for its selected terms; they are not relabelled as skills or student interests.")
        if any(str(entity["source_id"]) == "onet_database" for entity in entities):
            limitations.append("O*NET occupational rating scales are retained with their own scale IDs and are never student scores or cross-scale comparisons.")
        if any(edge["mapping_type"] == GraphMappingType.REVIEWED_RELATED.value for edge in edges):
            limitations.append("Cross-taxonomy links marked reviewed_related are editorial relationship hypotheses, not official exact-equivalence mappings.")
        metadata = {
            "graph_schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "built_at": built_at,
            "active_snapshots": snapshots,
            "active_snapshot_fingerprint": _snapshot_fingerprint(snapshots),
            "node_count": len(nodes), "edge_count": len(edges),
            "unresolved_crosswalk_count": sum(1 for edge in edges if edge["review_status"] == MappingReviewStatus.UNRESOLVED.value),
            "unresolved_relationship_count": len(self.unresolved_relationships),
            "unresolved_relationships": self.unresolved_relationships[:100],
            "limitations": limitations,
        }
        self.repository.replace_graph(
            nodes, edges, list(self.node_sources.values()), list(self.edge_sources.values()), metadata
        )
        return {
            "status": "built",
            "built_at": built_at,
            "graph_schema_version": GRAPH_SCHEMA_VERSION,
            "builder_version": GRAPH_BUILDER_VERSION,
            "active_snapshots": snapshots,
            "node_count": len(nodes), "edge_count": len(edges),
            "nodes_by_type": dict(Counter(node["node_type"] for node in nodes)),
            "edges_by_relation": dict(Counter(edge["relation_type"] for edge in edges)),
            "unresolved_crosswalk_count": metadata["unresolved_crosswalk_count"],
            "unresolved_relationship_count": metadata["unresolved_relationship_count"],
            "unresolved_relationships": metadata["unresolved_relationships"],
            "source_data_is_live": False,
            "limitations": limitations,
        }

    def _build_source_skill_edges(
        self, entities: list[dict[str, Any]], observations: list[dict[str, Any]]
    ) -> None:
        # Map taxonomy/external URI keys to the exact graph occupation/skill nodes already loaded.
        for entity in entities:
            entity_type = str(entity["entity_type"])
            normalized = entity["normalized_values"]
            if entity_type != "occupation_skill_observation":
                continue
            source_id = str(entity["source_id"])
            taxonomy = _taxonomy_for(source_id, normalized)
            family = _taxonomy_family(taxonomy, source_id)
            related_facts = [
                item for item in self._facts_for_entity(entity)
            ]
            if normalized.get("occupation_uri") and normalized.get("skill_uri"):
                occ_key = (family, str(normalized["occupation_uri"]))
                skill_key = (family, str(normalized["skill_uri"]))
                occ_node = self.external_nodes.get(occ_key)
                skill_node = self.external_nodes.get(skill_key)
                if occ_node and skill_node:
                    fact = related_facts[0] if related_facts else None
                    edge_id = self._add_edge(
                        occ_node, skill_node, GraphRelationType.OCCUPATION_HAS_SKILL,
                        mapping_type=GraphMappingType.EXACT, review_status=MappingReviewStatus.SOURCED,
                        description="This exact occupation-skill relation was present in the same source package/version.",
                        attributes={"taxonomy": taxonomy, "source_relation_type": normalized.get("relation_type"),
                                    "relation_relevance": normalized.get("relation_relevance"),
                                    "not_student_evidence": True},
                        identity=str(entity["source_record_id"]),
                    )
                    self._add_edge_source(edge_id, entity, fact=fact, evidence_role="taxonomy_occupation_skill_relation",
                                          notes=["Source relation is scoped to this taxonomy and package version."])
                else:
                    self.unresolved_relationships.append({
                        "source_id": source_id,
                        "source_record_id": str(entity["source_record_id"]),
                        "relation_type": "occupation_skill_relation",
                        "taxonomy": taxonomy,
                        "occupation_uri": str(normalized["occupation_uri"]),
                        "skill_uri": str(normalized["skill_uri"]),
                        "reason": "One or both active-snapshot endpoints are absent from the graph projection; no edge was fabricated.",
                    })
                continue

            # O*NET essential-skill observations use an occupation code + Element ID + scale.
            # Do not merge scale IDs; keep the source-specific value on the edge.
            if normalized.get("element_id") and normalized.get("occupation_code"):
                code = str(normalized["occupation_code"])
                occ_node = next((
                    item["node_id"] for item in self.occupation_nodes
                    if item["family"] == family and str(item["entity"].get("source_code") or item["entity"]["normalized_values"].get("code")) == code
                ), None)
                value = normalized.get("source_scale_value")
                suppressed = bool(normalized.get("recommend_suppress") or normalized.get("not_relevant") or value is None)
                if suppressed:
                    continue
                if not occ_node:
                    self.unresolved_relationships.append({
                        "source_id": source_id,
                        "source_record_id": str(entity["source_record_id"]),
                        "relation_type": "occupation_skill_observation",
                        "taxonomy": taxonomy,
                        "occupation_code": code,
                        "element_id": str(normalized["element_id"]),
                        "reason": "The occupational skill observation does not have a matching occupation node in the active snapshot; no edge was fabricated.",
                    })
                    continue
                skill_taxonomy = str(normalized.get("taxonomy") or taxonomy)
                skill_id = _stable_id("skill", skill_taxonomy, str(normalized["element_id"]))
                skill_label = str(normalized.get("element_name") or entity["source_title"])
                skill_node = self._add_node(
                    GraphNodeType.SKILL, skill_label, taxonomy=taxonomy, external_id=str(normalized["element_id"]),
                    geography=entity.get("geography"), evidence_class=str(entity["source_type"]),
                    attributes={"taxonomy_family": family, "skill_element_id": normalized["element_id"],
                                "definition_available": False, "not_student_evidence": True,
                                "source_rating_scale_is_taxonomy_specific": True}, node_id=skill_id,
                )
                self._add_node_source(skill_node, entity, fact=None, evidence_role="occupational_skill_observation",
                                      notes=["Skill label and rating belong to this occupational taxonomy, not to a student."])
                fact = related_facts[0] if related_facts else None
                edge_id = self._add_edge(
                    occ_node, skill_node, GraphRelationType.HAS_OCCUPATIONAL_SKILL_REFERENCE,
                    mapping_type=GraphMappingType.EXACT, review_status=MappingReviewStatus.SOURCED,
                    description="Source-specific occupational skill reference; numeric value is not a student score.",
                    attributes={"taxonomy": taxonomy, "scale_id": normalized.get("scale_id"),
                                "source_scale_value": value, "value_is_student_score": False,
                                "source_scale_value_is_comparable_across_scales": False},
                    identity=f"{normalized.get('scale_id')}:{entity['source_record_id']}",
                )
                self._add_edge_source(edge_id, entity, fact=fact, evidence_role="occupation_skill_rating",
                                      notes=["Preserve this source's scale ID; do not compare to another scale or student evidence."])

    def _facts_for_entity(self, entity: Mapping[str, Any]) -> list[dict[str, Any]]:
        # Reuse the facts already filtered to the active source snapshots. This is important
        # for large imports: never open one SQLite connection per skill/crosswalk record, and
        # never accidentally pull facts from a prior snapshot.
        return self.facts_by_entity.get(str(entity["internal_id"]), [])

    def _build_reviewed_crosswalks(self) -> None:
        """Add only manually reviewed related mappings with clear non-equivalence warnings."""
        onet_developers = [
            item for item in self.occupation_nodes
            if item["family"] == "O*NET"
            and str(item["entity"].get("source_code") or item["entity"]["normalized_values"].get("code") or "") == "15-1252.00"
        ]
        esco_developers = [
            item for item in self.occupation_nodes
            if item["family"] == "ESCO"
            and (str(item["entity"]["normalized_values"].get("code") or "") == "2512.4"
                 or "software developer" == item["label"].casefold())
        ]
        for onet in onet_developers:
            for esco in esco_developers:
                notes = [
                    "Editorially reviewed as related based on the source-backed labels and concise profile/task descriptions available in the selected records.",
                    "This is not an official O*NET–ESCO crosswalk and does not prove exact occupation equivalence.",
                    "Taxonomy boundaries, occupational scope and geographic context differ (United States O*NET reference vs European ESCO classification context).",
                    "Re-review against complete pinned source releases before production use; no Indian demand/qualification equivalence is implied.",
                    "This relationship is many-to-many-capable; no unique or one-to-one mapping assumption is encoded.",
                ]
                edge_id = self._add_edge(
                    onet["node_id"], esco["node_id"], GraphRelationType.RELATED_OCCUPATION,
                    mapping_type=GraphMappingType.REVIEWED_RELATED, review_status=MappingReviewStatus.REVIEWED,
                    description="Related software-development occupation concepts; not an exact equivalence.",
                    attributes={"crosswalk_kind": "manual_reviewed_related", "reviewed_at": "2026-10-17",
                                "equivalence_claimed": False, "many_to_many_allowed": True,
                                "geographic_contexts": [onet["entity"].get("geography"), esco["entity"].get("geography")]},
                    notes=notes, identity="onet-esco-software-development-reviewed-related-v1",
                )
                for item in (onet, esco):
                    entity = item["entity"]
                    facts = self._facts_for_entity(entity)
                    fact = next((f for f in facts if f["fact_type"] in {
                        "occupation_profile_summary", "esco_occupation_description", "occupation_description"
                    }), None)
                    self._add_edge_source(edge_id, entity, fact=fact, evidence_role="crosswalk_review_evidence",
                                          notes=["Independent taxonomy source cited for one endpoint of this related-role review."])

                # Keep the question of *exact* equivalence visible as unresolved instead of
                # letting a related-role crosswalk accidentally imply a one-to-one match.
                unresolved_id = self._add_edge(
                    onet["node_id"], esco["node_id"], GraphRelationType.CROSSWALK_CANDIDATE,
                    mapping_type=GraphMappingType.UNRESOLVED, review_status=MappingReviewStatus.UNRESOLVED,
                    description="Unresolved question: whether these occupation concepts are exactly equivalent.",
                    attributes={"exact_equivalence_claimed": False, "related_mapping_available": True,
                                "required_review": ["complete occupation definitions", "scope boundaries", "skill/competency records", "pinned source releases"]},
                    notes=[
                        "A separate reviewed-related edge exists, but the curated records do not establish exact equivalence.",
                        "No official one-to-one O*NET–ESCO crosswalk was included in the available package.",
                        "Keep the source taxonomy identities separate until the complete pinned releases and any official crosswalk are reviewed.",
                    ], identity="onet-esco-software-development-exact-equivalence-unresolved-v1",
                )
                for item in (onet, esco):
                    entity = item["entity"]
                    facts = self._facts_for_entity(entity)
                    fact = next((f for f in facts if f["fact_type"] in {
                        "occupation_profile_summary", "esco_occupation_description", "occupation_description"
                    }), None)
                    self._add_edge_source(unresolved_id, entity, fact=fact, evidence_role="unresolved_crosswalk_endpoint",
                                          notes=["Source reference supports review of this endpoint; exact taxonomy equivalence remains unestablished."])

        # A second independent-source example: task phrases about debugging software. Keep the
        # two task nodes separate and connect them only as reviewed-related activities.
        onet_debug = [
            item for item in self.activity_nodes
            if item["family"] == "O*NET" and item["label"].casefold().startswith("debug or improve existing programs")
        ]
        esco_debug = [
            item for item in self.activity_nodes
            if item["family"] == "ESCO" and item["label"].casefold().startswith("debug software")
        ]
        for left in onet_debug:
            for right in esco_debug:
                notes = [
                    "The source phrases overlap around software debugging, but the O*NET paraphrase also includes improvement/interfaces; therefore this is related, not exact.",
                    "Both task descriptions are concise paraphrases recorded in the curated extract, not verbatim quotes or an official shared skill taxonomy.",
                ]
                edge_id = self._add_edge(
                    left["node_id"], right["node_id"], GraphRelationType.RELATED_WORK_ACTIVITY,
                    mapping_type=GraphMappingType.REVIEWED_RELATED, review_status=MappingReviewStatus.REVIEWED,
                    description="Related software-debugging work activities represented separately in two taxonomies.",
                    attributes={"equivalence_claimed": False, "source_taxonomies": ["O*NET OnLine", "ESCO"]},
                    notes=notes, identity="onet-esco-debugging-activity-related-v1",
                )
                for item in (left, right):
                    self._add_edge_source(edge_id, item["entity"], fact=item["fact"], evidence_role="activity_crosswalk_evidence",
                                          notes=["Source-backed task phrase supports a reviewed-related activity connection."])

        # Use a narrow, explicit editorial abstraction to show a path from source activities to
        # a reusable capability concept. It remains a hypothesis, never an official skill record.
        hypothesis_specs = [
            {
                "label": "Software debugging",
                "left_prefix": "debug or improve existing programs",
                "right_prefix": "debug software",
                "description": "A SkillScope synthesis of two related source task phrases about debugging software.",
                "note": "This concept label is authored by SkillScope; neither source is claimed to define this exact competency label.",
            },
            {
                "label": "Requirements/specification analysis",
                "left_prefix": "review user needs and software requirements",
                "right_prefix": "analyse software specifications",
                "description": "A SkillScope synthesis of related source task phrases about examining software requirements/specifications.",
                "note": "This is a navigational abstraction over two related task descriptions, not a validated or officially harmonized competency.",
            },
        ]
        for spec in hypothesis_specs:
            left_items = [item for item in self.activity_nodes if item["family"] == "O*NET" and item["label"].casefold().startswith(spec["left_prefix"])]
            right_items = [item for item in self.activity_nodes if item["family"] == "ESCO" and item["label"].casefold().startswith(spec["right_prefix"])]
            for left in left_items:
                for right in right_items:
                    capability_id = self._add_node(
                        GraphNodeType.CAPABILITY_HYPOTHESIS, spec["label"],
                        external_id=f"editorial:{_slug(spec['label'])}:v1",
                        description=(spec["description"] + " It is not an official taxonomy skill, validated competency, or student assessment."),
                        geography="Cross-taxonomy reference (US/EU context; not harmonized)",
                        evidence_class="heuristic",
                        attributes={
                            "concept_class": "SkillScope editorial abstraction",
                            "official_taxonomy_concept": False,
                            "validated_competency": False,
                            "student_evidence": False,
                            "normalization_version": 1,
                            "source_taxonomies": ["O*NET OnLine", "ESCO"],
                        },
                    )
                    for item in (left, right):
                        self._add_node_source(
                            capability_id, item["entity"], fact=item["fact"], evidence_role="capability_hypothesis_evidence",
                            notes=[spec["note"], "The source task phrase is a concise paraphrase in the curated extract."],
                        )
                        support_edge_id = self._add_edge(
                            item["node_id"], capability_id, GraphRelationType.SUPPORTS_CAPABILITY_HYPOTHESIS,
                            mapping_type=GraphMappingType.REVIEWED_RELATED,
                            review_status=MappingReviewStatus.REVIEWED,
                            description="This source task phrase is one of the inputs to a SkillScope-authored capability hypothesis.",
                            attributes={"source_taxonomy": item["family"], "concept_is_heuristic": True,
                                        "not_student_evidence": True},
                            notes=[spec["note"]], identity=f"{_slug(spec['label'])}:{item['node_id']}",
                        )
                        self._add_edge_source(
                            support_edge_id, item["entity"], fact=item["fact"], evidence_role="capability_hypothesis_input",
                            notes=[spec["note"]],
                        )


def rebuild_knowledge_graph(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    active_snapshots: Mapping[str, str] | None = None,
    state_path: str | Path = STATE_PATH,
) -> dict[str, Any]:
    repository = KnowledgeGraphRepository(db_path)
    return KnowledgeGraphBuilder(repository).build(active_snapshots, state_path=state_path)


def graph_status(
    db_path: str | Path = DEFAULT_DB_PATH,
    *,
    active_snapshots: Mapping[str, str] | None = None,
    state_path: str | Path = STATE_PATH,
) -> dict[str, Any]:
    snapshots = dict(active_snapshots) if active_snapshots is not None else load_active_snapshots(state_path)
    return KnowledgeGraphRepository(db_path).status(dict(sorted(snapshots.items())))


def list_graph_nodes(
    *, db_path: str | Path = DEFAULT_DB_PATH, node_type: str | None = None,
    query: str | None = None, limit: int = 50, offset: int = 0,
) -> list[dict[str, Any]]:
    return KnowledgeGraphRepository(db_path).list_nodes(node_type=node_type, query=query, limit=limit, offset=offset)


def get_graph_node(node_id: str, *, db_path: str | Path = DEFAULT_DB_PATH) -> dict[str, Any] | None:
    return KnowledgeGraphRepository(db_path).get_node(node_id)


def list_graph_edges(
    *, db_path: str | Path = DEFAULT_DB_PATH, relation_type: str | None = None,
    mapping_type: str | None = None, limit: int = 100,
) -> list[dict[str, Any]]:
    return KnowledgeGraphRepository(db_path).list_edges(relation_type=relation_type, mapping_type=mapping_type, limit=limit)


def list_career_cards(*, db_path: str | Path = DEFAULT_DB_PATH, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
    return KnowledgeGraphRepository(db_path).list_careers(limit=limit, offset=offset)


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Build SkillScope's source-traceable career knowledge graph.")
    parser.add_argument("command", choices=["rebuild", "status"])
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite database path")
    parser.add_argument("--state", default=str(STATE_PATH), help="Ingestion state JSON path")
    args = parser.parse_args()
    result = rebuild_knowledge_graph(args.db, state_path=args.state) if args.command == "rebuild" else graph_status(args.db, state_path=args.state)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess tests
    raise SystemExit(_cli())
