"""SQLite-backed provenance registry for auditable SkillScope data.

The registry stores source records, canonical entities, provenance links, and career facts.
Official imports and explicitly labelled curated extracts use the same lineage contract while
retaining distinct source types, source versions, and limitations.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.schemas.provenance import (
    CanonicalEntity,
    CareerFact,
    MappingType,
    ProvenanceLink,
    QualityStatus,
    SourceRecord,
    SourceType,
)

from app.config import resolve_database_path
from app.services.database import connect_sqlite

DEFAULT_DB_PATH = resolve_database_path()


class ProvenanceRepository:
    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        # Shared connection policy enforces FK checks, busy timeout, and row mapping.
        return connect_sqlite(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                PRAGMA foreign_keys = ON;

                CREATE TABLE IF NOT EXISTS source_records (
                    source_id TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    publisher TEXT NOT NULL,
                    title TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    geography TEXT,
                    source_uri TEXT,
                    record_uri TEXT,
                    source_version TEXT,
                    release_date TEXT,
                    accessed_at TEXT NOT NULL,
                    ingested_at TEXT,
                    license_reference TEXT,
                    license_text TEXT,
                    checksum_sha256 TEXT,
                    quality_status TEXT NOT NULL,
                    last_verified_at TEXT,
                    limitations_json TEXT NOT NULL,
                    PRIMARY KEY (source_id, source_record_id)
                );

                CREATE TABLE IF NOT EXISTS canonical_entities (
                    internal_id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    source_uri TEXT,
                    source_title TEXT NOT NULL,
                    source_code TEXT,
                    publisher TEXT NOT NULL,
                    geography TEXT,
                    source_version TEXT,
                    release_date TEXT,
                    accessed_at TEXT NOT NULL,
                    ingested_at TEXT NOT NULL,
                    license_reference TEXT,
                    source_type TEXT NOT NULL,
                    source_values_json TEXT NOT NULL,
                    normalized_values_json TEXT NOT NULL,
                    transformation_notes_json TEXT NOT NULL,
                    quality_status TEXT NOT NULL,
                    last_verified_at TEXT,
                    confidence REAL,
                    limitations_json TEXT NOT NULL,
                    FOREIGN KEY (source_id, source_record_id)
                        REFERENCES source_records(source_id, source_record_id)
                );

                CREATE TABLE IF NOT EXISTS provenance_links (
                    entity_internal_id TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_record_id TEXT NOT NULL,
                    source_uri TEXT,
                    source_version TEXT,
                    mapping_type TEXT NOT NULL,
                    mapping_notes_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (entity_internal_id, source_id, source_record_id),
                    FOREIGN KEY (entity_internal_id) REFERENCES canonical_entities(internal_id),
                    FOREIGN KEY (source_id, source_record_id)
                        REFERENCES source_records(source_id, source_record_id)
                );

                CREATE TABLE IF NOT EXISTS career_facts (
                    fact_id TEXT PRIMARY KEY,
                    entity_internal_id TEXT NOT NULL,
                    fact_type TEXT NOT NULL,
                    statement TEXT NOT NULL,
                    value_json TEXT NOT NULL,
                    display_status TEXT NOT NULL DEFAULT 'sourced',
                    FOREIGN KEY (entity_internal_id) REFERENCES canonical_entities(internal_id)
                );
                """
            )

    @staticmethod
    def _iso(value: datetime | None) -> str | None:
        if value is None:
            return None
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Provenance timestamps must include a timezone.")
        return value.astimezone(UTC).isoformat()

    def upsert_source(self, source: SourceRecord, source_record_id: str) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO source_records (
                    source_id, source_record_id, publisher, title, source_type, geography,
                    source_uri, record_uri, source_version, release_date, accessed_at,
                    ingested_at, license_reference, license_text, checksum_sha256,
                    quality_status, last_verified_at, limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id, source_record_id) DO UPDATE SET
                    publisher=excluded.publisher, title=excluded.title,
                    source_type=excluded.source_type, geography=excluded.geography,
                    source_uri=excluded.source_uri, record_uri=excluded.record_uri,
                    source_version=excluded.source_version, release_date=excluded.release_date,
                    accessed_at=source_records.accessed_at, ingested_at=source_records.ingested_at,
                    license_reference=excluded.license_reference, license_text=excluded.license_text,
                    checksum_sha256=excluded.checksum_sha256,
                    quality_status=excluded.quality_status,
                    last_verified_at=excluded.last_verified_at,
                    limitations_json=excluded.limitations_json
                """,
                (
                    source.source_id, source_record_id, source.publisher, source.title,
                    source.source_type.value, source.geography, str(source.source_uri) if source.source_uri else None,
                    str(source.record_uri) if source.record_uri else None, source.source_version,
                    source.release_date, self._iso(source.accessed_at), self._iso(source.ingested_at),
                    str(source.license_reference) if source.license_reference else None, source.license_text,
                    source.checksum_sha256, source.quality_status.value, self._iso(source.last_verified_at),
                    json.dumps(source.limitations),
                ),
            )

    def upsert_entity(self, entity: CanonicalEntity) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO canonical_entities (
                    internal_id, entity_type, source_id, source_record_id, source_uri,
                    source_title, source_code, publisher, geography, source_version,
                    release_date, accessed_at, ingested_at, license_reference, source_type,
                    source_values_json, normalized_values_json, transformation_notes_json,
                    quality_status, last_verified_at, confidence, limitations_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(internal_id) DO UPDATE SET
                    entity_type=excluded.entity_type, source_id=excluded.source_id,
                    source_record_id=excluded.source_record_id, source_uri=excluded.source_uri,
                    source_title=excluded.source_title, source_code=excluded.source_code,
                    publisher=excluded.publisher, geography=excluded.geography,
                    source_version=excluded.source_version, release_date=excluded.release_date,
                    accessed_at=canonical_entities.accessed_at, ingested_at=canonical_entities.ingested_at,
                    license_reference=excluded.license_reference, source_type=excluded.source_type,
                    source_values_json=excluded.source_values_json,
                    normalized_values_json=excluded.normalized_values_json,
                    transformation_notes_json=excluded.transformation_notes_json,
                    quality_status=excluded.quality_status,
                    last_verified_at=excluded.last_verified_at, confidence=excluded.confidence,
                    limitations_json=excluded.limitations_json
                """,
                (
                    entity.internal_id, entity.entity_type.value, entity.source_id, entity.source_record_id,
                    str(entity.source_uri) if entity.source_uri else None, entity.source_title, entity.source_code,
                    entity.publisher, entity.geography, entity.source_version, entity.release_date,
                    self._iso(entity.accessed_at), self._iso(entity.ingested_at),
                    str(entity.license_reference) if entity.license_reference else None,
                    entity.source_type.value, json.dumps(entity.source_values, sort_keys=True),
                    json.dumps(entity.normalized_values, sort_keys=True), json.dumps(entity.transformation_notes),
                    entity.quality_status.value, self._iso(entity.last_verified_at), entity.confidence,
                    json.dumps(entity.limitations),
                ),
            )

    def add_provenance_link(self, link: ProvenanceLink) -> None:
        with self._connect() as db:
            db.execute(
                """
                INSERT INTO provenance_links (
                    entity_internal_id, source_id, source_record_id, source_uri,
                    source_version, mapping_type, mapping_notes_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(entity_internal_id, source_id, source_record_id) DO UPDATE SET
                    source_uri=excluded.source_uri, source_version=excluded.source_version,
                    mapping_type=excluded.mapping_type, mapping_notes_json=excluded.mapping_notes_json,
                    created_at=provenance_links.created_at
                """,
                (
                    link.entity_internal_id, link.source_id, link.source_record_id,
                    str(link.source_uri) if link.source_uri else None, link.source_version,
                    link.mapping_type.value, json.dumps(link.mapping_notes), self._iso(link.created_at),
                ),
            )

    def add_career_fact(self, fact_id: str, entity_internal_id: str, fact_type: str, statement: str, value: Any) -> None:
        with self._connect() as db:
            entity = db.execute(
                "SELECT source_id, source_record_id FROM canonical_entities WHERE internal_id = ?",
                (entity_internal_id,),
            ).fetchone()
            if entity is not None:
                link = db.execute(
                    """
                    SELECT 1 FROM provenance_links
                    WHERE entity_internal_id = ? AND source_id = ? AND source_record_id = ?
                    """,
                    (entity_internal_id, entity["source_id"], entity["source_record_id"]),
                ).fetchone()
                if link is None:
                    raise sqlite3.IntegrityError(
                        "Career facts require a provenance link to their canonical entity's source record."
                    )
            # If the entity does not exist, the normal foreign-key check below raises an
            # IntegrityError, preserving SQLite's useful missing-entity diagnostic.
            db.execute(
                """
                INSERT INTO career_facts (fact_id, entity_internal_id, fact_type, statement, value_json)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(fact_id) DO UPDATE SET
                    entity_internal_id=excluded.entity_internal_id,
                    fact_type=excluded.fact_type, statement=excluded.statement,
                    value_json=excluded.value_json
                """,
                (fact_id, entity_internal_id, fact_type, statement, json.dumps(value, sort_keys=True)),
            )

    def get_career_fact(self, fact_id: str) -> CareerFact | None:
        with self._connect() as db:
            row = db.execute(
                """
                SELECT f.*, e.*, s.*,
                       p.source_id AS p_source_id, p.source_record_id AS p_source_record_id,
                       p.source_uri AS p_source_uri, p.source_version AS p_source_version,
                       p.mapping_type, p.mapping_notes_json, p.created_at AS p_created_at
                FROM career_facts f
                JOIN canonical_entities e ON e.internal_id = f.entity_internal_id
                JOIN source_records s ON s.source_id = e.source_id AND s.source_record_id = e.source_record_id
                JOIN provenance_links p ON p.entity_internal_id = e.internal_id
                    AND p.source_id = s.source_id AND p.source_record_id = s.source_record_id
                WHERE f.fact_id = ?
                """,
                (fact_id,),
            ).fetchone()
        if row is None:
            return None

        source = SourceRecord(
            source_id=row["source_id"], publisher=row["publisher"], title=row["title"],
            source_type=SourceType(row["source_type"]), geography=row["geography"],
            source_uri=row["source_uri"], record_uri=row["record_uri"], source_version=row["source_version"],
            release_date=row["release_date"], accessed_at=row["accessed_at"], ingested_at=row["ingested_at"],
            license_reference=row["license_reference"], license_text=row["license_text"],
            checksum_sha256=row["checksum_sha256"], quality_status=QualityStatus(row["quality_status"]),
            last_verified_at=row["last_verified_at"], limitations=json.loads(row["limitations_json"]),
        )
        entity = CanonicalEntity(
            internal_id=row["internal_id"], entity_type=row["entity_type"], source_id=row["source_id"],
            source_record_id=row["source_record_id"], source_uri=row["source_uri"], source_title=row["source_title"],
            source_code=row["source_code"], publisher=row["publisher"], geography=row["geography"],
            source_version=row["source_version"], release_date=row["release_date"], accessed_at=row["accessed_at"],
            ingested_at=row["ingested_at"], license_reference=row["license_reference"],
            source_type=SourceType(row["source_type"]), source_values=json.loads(row["source_values_json"]),
            normalized_values=json.loads(row["normalized_values_json"]),
            transformation_notes=json.loads(row["transformation_notes_json"]),
            quality_status=QualityStatus(row["quality_status"]), last_verified_at=row["last_verified_at"],
            confidence=row["confidence"], limitations=json.loads(row["limitations_json"]),
        )
        link = ProvenanceLink(
            entity_internal_id=row["internal_id"], source_id=row["p_source_id"],
            source_record_id=row["p_source_record_id"], source_uri=row["p_source_uri"],
            source_version=row["p_source_version"], mapping_type=MappingType(row["mapping_type"]),
            mapping_notes=json.loads(row["mapping_notes_json"]), created_at=row["p_created_at"],
        )
        return CareerFact(
            fact_id=row["fact_id"], entity_internal_id=row["entity_internal_id"], fact_type=row["fact_type"],
            statement=row["statement"], value=json.loads(row["value_json"]), source=source,
            entity=entity, provenance=link, display_status=row["display_status"],
        )

    def upsert_bundles(self, bundles: list[tuple[SourceRecord, str, CanonicalEntity, ProvenanceLink, list[tuple[str, str, str, Any]]]]) -> None:
        """Upsert a chunk of provenance bundles in one SQLite transaction.

        Each bundle contains (source, source_record_id, entity, provenance_link,
        [(fact_id, fact_type, statement, value), ...]). If any bundle fails, this
        chunk is rolled back as a whole. Importers use bounded chunks so a process
        can safely resume from the start; all keys are stable and operations are
        idempotent.
        """
        if not bundles:
            return
        with self._connect() as db:
            db.execute("PRAGMA foreign_keys = ON")
            for source, source_record_id, entity, link, facts in bundles:
                db.execute(
                    """
                    INSERT INTO source_records (
                        source_id, source_record_id, publisher, title, source_type, geography,
                        source_uri, record_uri, source_version, release_date, accessed_at,
                        ingested_at, license_reference, license_text, checksum_sha256,
                        quality_status, last_verified_at, limitations_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_id, source_record_id) DO UPDATE SET
                        publisher=excluded.publisher, title=excluded.title,
                        source_type=excluded.source_type, geography=excluded.geography,
                        source_uri=excluded.source_uri, record_uri=excluded.record_uri,
                        source_version=excluded.source_version, release_date=excluded.release_date,
                        accessed_at=source_records.accessed_at, ingested_at=source_records.ingested_at,
                        license_reference=excluded.license_reference, license_text=excluded.license_text,
                        checksum_sha256=excluded.checksum_sha256,
                        quality_status=excluded.quality_status,
                        last_verified_at=excluded.last_verified_at,
                        limitations_json=excluded.limitations_json
                    """,
                    (
                        source.source_id, source_record_id, source.publisher, source.title,
                        source.source_type.value, source.geography,
                        str(source.source_uri) if source.source_uri else None,
                        str(source.record_uri) if source.record_uri else None, source.source_version,
                        source.release_date, self._iso(source.accessed_at), self._iso(source.ingested_at),
                        str(source.license_reference) if source.license_reference else None, source.license_text,
                        source.checksum_sha256, source.quality_status.value, self._iso(source.last_verified_at),
                        json.dumps(source.limitations),
                    ),
                )
                db.execute(
                    """
                    INSERT INTO canonical_entities (
                        internal_id, entity_type, source_id, source_record_id, source_uri,
                        source_title, source_code, publisher, geography, source_version,
                        release_date, accessed_at, ingested_at, license_reference, source_type,
                        source_values_json, normalized_values_json, transformation_notes_json,
                        quality_status, last_verified_at, confidence, limitations_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(internal_id) DO UPDATE SET
                        entity_type=excluded.entity_type, source_id=excluded.source_id,
                        source_record_id=excluded.source_record_id, source_uri=excluded.source_uri,
                        source_title=excluded.source_title, source_code=excluded.source_code,
                        publisher=excluded.publisher, geography=excluded.geography,
                        source_version=excluded.source_version, release_date=excluded.release_date,
                        accessed_at=canonical_entities.accessed_at, ingested_at=canonical_entities.ingested_at,
                        license_reference=excluded.license_reference, source_type=excluded.source_type,
                        source_values_json=excluded.source_values_json,
                        normalized_values_json=excluded.normalized_values_json,
                        transformation_notes_json=excluded.transformation_notes_json,
                        quality_status=excluded.quality_status, last_verified_at=excluded.last_verified_at,
                        confidence=excluded.confidence, limitations_json=excluded.limitations_json
                    """,
                    (
                        entity.internal_id, entity.entity_type.value, entity.source_id, entity.source_record_id,
                        str(entity.source_uri) if entity.source_uri else None, entity.source_title, entity.source_code,
                        entity.publisher, entity.geography, entity.source_version, entity.release_date,
                        self._iso(entity.accessed_at), self._iso(entity.ingested_at),
                        str(entity.license_reference) if entity.license_reference else None,
                        entity.source_type.value, json.dumps(entity.source_values, sort_keys=True),
                        json.dumps(entity.normalized_values, sort_keys=True), json.dumps(entity.transformation_notes),
                        entity.quality_status.value, self._iso(entity.last_verified_at), entity.confidence,
                        json.dumps(entity.limitations),
                    ),
                )
                db.execute(
                    """
                    INSERT INTO provenance_links (
                        entity_internal_id, source_id, source_record_id, source_uri,
                        source_version, mapping_type, mapping_notes_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(entity_internal_id, source_id, source_record_id) DO UPDATE SET
                        source_uri=excluded.source_uri, source_version=excluded.source_version,
                        mapping_type=excluded.mapping_type, mapping_notes_json=excluded.mapping_notes_json,
                        created_at=provenance_links.created_at
                    """,
                    (
                        link.entity_internal_id, link.source_id, link.source_record_id,
                        str(link.source_uri) if link.source_uri else None, link.source_version,
                        link.mapping_type.value, json.dumps(link.mapping_notes), self._iso(link.created_at),
                    ),
                )
                for fact_id, fact_type, statement, value in facts:
                    db.execute(
                        """
                        INSERT INTO career_facts (fact_id, entity_internal_id, fact_type, statement, value_json)
                        VALUES (?, ?, ?, ?, ?)
                        ON CONFLICT(fact_id) DO UPDATE SET
                            entity_internal_id=excluded.entity_internal_id,
                            fact_type=excluded.fact_type, statement=excluded.statement,
                            value_json=excluded.value_json
                        """,
                        (fact_id, entity.internal_id, fact_type, statement, json.dumps(value, sort_keys=True)),
                    )

    def count(self) -> dict[str, int]:
        with self._connect() as db:
            return {
                "sources": db.execute("SELECT COUNT(*) FROM source_records").fetchone()[0],
                "entities": db.execute("SELECT COUNT(*) FROM canonical_entities").fetchone()[0],
                "provenance_links": db.execute("SELECT COUNT(*) FROM provenance_links").fetchone()[0],
                "career_facts": db.execute("SELECT COUNT(*) FROM career_facts").fetchone()[0],
            }


    def source_type_counts(self) -> dict[str, int]:
        """Count stored source records by their declared evidence class."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT source_type, COUNT(*) AS total FROM source_records GROUP BY source_type"
            ).fetchall()
        return {str(row["source_type"]): int(row["total"]) for row in rows}
