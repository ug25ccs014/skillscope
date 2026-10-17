"""Idempotent, provenance-preserving ingestion pipelines for official career sources."""

from __future__ import annotations

import hashlib
import json
import re
from functools import wraps
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Literal
from urllib.parse import quote, urlparse

import yaml
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, ValidationError

from app.schemas.provenance import (
    CanonicalEntity,
    EntityType,
    MappingType,
    ProvenanceLink,
    QualityStatus,
    SourceRecord,
    SourceType,
)
from app.services.ingestion.common import (
    CURATED_SNAPSHOT_PATH,
    DATA_ROOT,
    IngestionError,
    IngestionValidationError,
    STATE_PATH,
    deduplicate_rows,
    iso_utc,
    normalize_header,
    normalize_slug,
    parse_datetime,
    parse_optional_float,
    read_csv_table,
    record_run_event,
    require_columns,
    sha256_file,
    write_text_atomic,
)
from app.services.ingestion.downloads import ASSETS
from app.services.provenance import ProvenanceRepository

ONET_LICENSE_URL = "https://www.onetcenter.org/license_db.html"
ESCO_LICENSE_URL = "https://esco.ec.europa.eu/en/about-esco/faq?page=1"
ESCO_DOWNLOAD_URL = "https://esco.ec.europa.eu/en/use-esco/download"
ESCO_VERSION_PAGE = "https://esco.ec.europa.eu/en/structure-esco-downloadable-datasets"
ONET_PUBLISHER = "U.S. Department of Labor, Employment and Training Administration (USDOL/ETA); National Center for O*NET Development"
ESCO_PUBLISHER = "European Commission, Directorate-General for Employment, Social Affairs and Inclusion"
MAX_ESCO_PACKAGE_BYTES = 1024 * 1024 * 1024
MAX_ESCO_ARCHIVE_MEMBERS = 10_000

# Bump this when canonical transformations/fact semantics change. It deliberately participates
# in snapshot IDs so re-normalization never silently mutates an earlier derived snapshot.
NORMALIZER_SCHEMA_VERSION = "2"


class CuratedRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str = Field(min_length=1, max_length=120)
    source_record_id: str = Field(min_length=1, max_length=160)
    publisher: str = Field(min_length=1, max_length=240)
    source_base_uri: HttpUrl
    record_uri: HttpUrl
    source_title: str = Field(min_length=1, max_length=300)
    source_code: str = Field(min_length=1, max_length=160)
    source_version: str = Field(min_length=1, max_length=120)
    release_date: str | None = Field(default=None, max_length=40)
    geography: str = Field(min_length=1, max_length=120)
    source_accessed_at: datetime
    license_reference: HttpUrl
    license_summary: str = Field(min_length=1, max_length=1000)
    source_values: dict[str, Any]
    # Editorial coverage metadata, deliberately separate from original source values.
    curation_domain: Literal[
        "technology", "data_analytics", "creative_design", "business_marketing",
        "social_support", "hands_on_environmental_technology", "environmental_science",
        "business_coordination", "hands_on_engineering"
    ] | None = None
    summary: str = Field(min_length=1, max_length=1200)
    selected_tasks: list[str] = Field(default_factory=list, max_length=30)
    selected_terms: list[str] = Field(default_factory=list, max_length=80)
    selected_essential_skills: list[str] = Field(default_factory=list, max_length=30)
    transformation_notes: list[str] = Field(min_length=1, max_length=20)
    limitations: list[str] = Field(min_length=1, max_length=20)


class CuratedSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = Field(ge=1)
    snapshot_id: str = Field(min_length=1, max_length=160)
    snapshot_type: str
    curated_at: datetime
    curated_by: str
    runtime_fetch_performed: bool
    runtime_fetch_note: str
    records: list[CuratedRecord] = Field(min_length=1, max_length=1000)


@dataclass
class IngestionReport:
    source_id: str
    status: str
    source_version: str | None
    records_processed: int = 0
    records_upserted: int = 0
    facts_upserted: int = 0
    duplicate_rows_skipped: int = 0
    suppressed_ratings_not_displayed: int = 0
    file_sha256: str | None = None
    warnings: list[str] | None = None
    details: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["warnings"] = result.get("warnings") or []
        result["details"] = result.get("details") or {}
        return result


def _track_import_failures(source_id: str):
    """Ensure expected and unexpected importer failures remain visible in the run ledger."""
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            try:
                return function(*args, **kwargs)
            except Exception as exc:
                state_path = kwargs.get("state_path", STATE_PATH)
                now = iso_utc()
                event = {
                    "source_id": source_id,
                    "status": "import_failed",
                    "started_at": now,
                    "finished_at": iso_utc(),
                    "source_version": kwargs.get("source_version"),
                    "failure_type": type(exc).__name__,
                    "error": str(exc)[:2000],
                    "source_data_is_live": False,
                    "next_action": "Inspect the validation/runtime error; correct the input or environment and retry. The source must not be reported as newly integrated.",
                }
                try:
                    record_run_event(event, state_path=state_path)
                except Exception:
                    # Never hide the original import error because its diagnostic write also failed.
                    pass
                raise
        return wrapped
    return decorate


def _snapshot_namespace(prefix: str, source_version: str, digest: str) -> str:
    version_slug = normalize_slug(source_version)[:28].strip("-") or "version-unknown"
    normalized_digest = hashlib.sha256(
        f"normalizer:{NORMALIZER_SCHEMA_VERSION}\0{digest}".encode("utf-8")
    ).hexdigest()
    return f"{prefix}-{version_slug}-n{NORMALIZER_SCHEMA_VERSION}-{normalized_digest[:16]}"


def update_source_manifest_import(
    manifest_path: str | Path,
    *,
    source_id: str,
    source_version: str,
    snapshot_id: str,
    checksum_sha256: str,
    imported_at: str,
    report: IngestionReport,
    acquisition_method: str,
) -> None:
    """Atomically mark an official source imported only after its validated DB import succeeds."""
    path = Path(manifest_path)
    try:
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise IngestionError(f"Could not read source manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list):
        raise IngestionValidationError("Source manifest must be an object containing a sources list.")
    matches = [item for item in manifest["sources"] if isinstance(item, dict) and item.get("id") == source_id]
    if len(matches) != 1:
        raise IngestionValidationError(
            f"Source manifest must contain exactly one record for {source_id!r}; found {len(matches)}."
        )
    source = matches[0]
    source["integration_status"] = "versioned_snapshot_imported"
    if source_id == "onet_database":
        source["runtime_access_status"] = (
            "pinned_asset_metadata_and_file_checksum_validated_locally;_download_origin_not_cryptographically_attested"
            if acquisition_method == "sidecar_metadata_validated_source_origin_not_cryptographically_attested"
            else "operator_supplied_pinned_local_files_and_retrieval_metadata_validated;_origin_not_independently_verified"
        )
    else:
        source["runtime_access_status"] = (
            "operator_supplied_version_pinned_package_imported_locally;_portal_origin_not_independently_verified"
        )
    source["last_import"] = {
        "status": "imported",
        "source_version": source_version,
        "normalizer_schema_version": report.details.get("normalizer_schema_version") if report.details else NORMALIZER_SCHEMA_VERSION,
        "snapshot_id": snapshot_id,
        "checksum_sha256": checksum_sha256,
        "imported_at": imported_at,
        "acquisition_method": acquisition_method,
        "source_data_is_live": False,
        "counts": {
            "records_processed": report.records_processed,
            "records_upserted": report.records_upserted,
            "facts_upserted": report.facts_upserted,
        },
    }
    official_sources = [
        item for item in manifest["sources"]
        if isinstance(item, dict) and item.get("id") in {"onet_database", "esco_classification"}
    ]
    if any(item.get("integration_status") == "versioned_snapshot_imported" for item in official_sources):
        manifest["manifest_status"] = "mixed_integration_official_snapshots_imported_other_sources_unintegrated"
    header = "# Stage 4 source register; runtime import status is updated only after a validated local import succeeds.\n"
    content = header + yaml.safe_dump(manifest, sort_keys=False, allow_unicode=True, width=100)
    write_text_atomic(path, content)


def _validate_manifest_target(manifest_path: str | Path | None, source_id: str) -> None:
    """Validate the manifest write target before an importer starts database writes."""
    if manifest_path is None:
        return
    path = Path(manifest_path)
    try:
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise IngestionError(f"Could not read source manifest {path}: {exc}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list):
        raise IngestionValidationError("Source manifest must be an object containing a sources list.")
    matches = [item for item in manifest["sources"] if isinstance(item, dict) and item.get("id") == source_id]
    if len(matches) != 1:
        raise IngestionValidationError(
            f"Source manifest must contain exactly one record for {source_id!r}; found {len(matches)}."
        )


def _manifest_source_ids(manifest_path: str | Path) -> set[str]:
    try:
        manifest = yaml.safe_load(Path(manifest_path).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise IngestionError(f"Could not read source manifest {manifest_path}: {exc}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list):
        raise IngestionValidationError("Source manifest must be an object containing a sources list.")
    ids = {item.get("id") for item in manifest["sources"] if isinstance(item, dict)}
    if None in ids:
        ids.remove(None)
    return {str(item) for item in ids}


def _artifact_metadata(
    path: str | Path,
    *,
    asset_id: str,
    source_version: str | None = None,
    release_date: str | None = None,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    source_path = Path(path)
    if not source_path.is_file():
        raise IngestionError(f"Source artifact does not exist or is not a regular file: {source_path}")
    checksum = sha256_file(source_path)
    sidecar = Path(str(source_path) + ".metadata.json")
    if asset_id not in ASSETS:
        raise IngestionValidationError(f"No allow-listed source asset definition exists for {asset_id!r}.")
    asset = ASSETS[asset_id]
    if sidecar.is_file():
        try:
            metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise IngestionValidationError(f"Invalid metadata sidecar {sidecar}: {exc}") from exc
        if not isinstance(metadata, dict):
            raise IngestionValidationError(f"Metadata sidecar must be a JSON object: {sidecar}")
        if metadata.get("sha256") != checksum:
            raise IngestionValidationError(
                f"Checksum mismatch for {source_path.name}; the metadata sidecar does not describe this file."
            )
        if metadata.get("asset_id") != asset_id:
            raise IngestionValidationError(f"Metadata sidecar belongs to {metadata.get('asset_id')!r}, not {asset_id!r}.")
        if metadata.get("source_id") != asset.source_id:
            raise IngestionValidationError(f"Metadata sidecar has an unexpected source_id for {asset_id!r}.")
        if metadata.get("source_url") != asset.url:
            raise IngestionValidationError(f"Metadata sidecar URL does not match the allow-listed official URL for {asset_id!r}.")
        if metadata.get("source_version") != asset.source_version:
            raise IngestionValidationError(
                f"Metadata sidecar source version must be the pinned {asset.source_version!r}; add an explicit downloader asset for another release."
            )
        if metadata.get("release_date") != asset.release_date:
            raise IngestionValidationError(f"Metadata sidecar release date does not match the pinned release for {asset_id!r}.")
        if metadata.get("license_reference") != asset.license_url:
            raise IngestionValidationError(f"Metadata sidecar has an unexpected licence reference for {asset_id!r}.")
        if metadata.get("filename") != source_path.name:
            raise IngestionValidationError(f"Metadata sidecar filename does not match {source_path.name!r}.")
        if not metadata.get("retrieved_at"):
            raise IngestionValidationError(f"Metadata sidecar is missing a retrieval timestamp for {asset_id!r}.")
        parse_datetime(str(metadata["retrieved_at"]))
        return metadata
    if not source_version or not retrieved_at:
        raise IngestionValidationError(
            f"{source_path.name} has no downloader metadata sidecar. For manually downloaded files, provide both "
            "an explicit --source-version and timezone-aware --retrieved-at timestamp."
        )
    if source_version != asset.source_version:
        raise IngestionValidationError(
            f"Manual {asset_id} file must be labelled with the pinned version {asset.source_version!r}."
        )
    if release_date and release_date != asset.release_date:
        raise IngestionValidationError(
            f"Manual {asset_id} file release date must match the pinned release {asset.release_date!r}."
        )
    return {
        "asset_id": asset_id,
        "source_id": asset.source_id,
        "source_url": asset.url,
        "filename": source_path.name,
        "retrieved_at": iso_utc(parse_datetime(retrieved_at)),
        "source_version": source_version,
        "release_date": release_date or asset.release_date,
        "license_reference": asset.license_url,
        "license_summary": asset.license_summary,
        "byte_size": source_path.stat().st_size,
        "sha256": checksum,
        "manual_file": True,
    }


def _validate_sha_metadata(metadata: dict[str, Any], actual_sha: str, label: str) -> None:
    expected = metadata.get("sha256")
    if expected and expected != actual_sha:
        raise IngestionValidationError(f"Checksum mismatch for {label}: metadata says {expected}, file is {actual_sha}.")


def _make_source_record(
    *,
    source_id: str,
    source_record_id: str,
    publisher: str,
    title: str,
    geography: str,
    source_url: str,
    record_url: str | None,
    source_version: str,
    release_date: str | None,
    retrieved_at: datetime,
    ingested_at: datetime,
    license_url: str,
    license_summary: str,
    checksum: str,
    quality_status: QualityStatus,
    limitations: list[str],
    source_type: SourceType = SourceType.OFFICIAL,
) -> SourceRecord:
    return SourceRecord(
        source_id=source_id,
        publisher=publisher,
        title=title,
        source_type=source_type,
        geography=geography,
        source_uri=source_url,
        record_uri=record_url,
        source_version=source_version,
        release_date=release_date,
        accessed_at=retrieved_at,
        ingested_at=ingested_at,
        license_reference=license_url,
        license_text=license_summary,
        checksum_sha256=checksum,
        quality_status=quality_status,
        last_verified_at=ingested_at if quality_status is QualityStatus.REVIEWED else None,
        limitations=limitations,
    )


def _make_link(entity_id: str, source: SourceRecord, source_record_id: str, notes: list[str]) -> ProvenanceLink:
    return ProvenanceLink(
        entity_internal_id=entity_id,
        source_id=source.source_id,
        source_record_id=source_record_id,
        source_uri=source.record_uri or source.source_uri,
        source_version=source.source_version,
        mapping_type=MappingType.EXACT,
        mapping_notes=notes,
        created_at=source.ingested_at or source.accessed_at,
    )


def _chunks(items: list[Any], size: int) -> Iterator[list[Any]]:
    if size < 1:
        raise ValueError("batch_size must be at least 1")
    for start in range(0, len(items), size):
        yield items[start:start + size]


@_track_import_failures("curated_snapshot")
def import_curated_snapshot(
    snapshot_path: str | Path = CURATED_SNAPSHOT_PATH,
    *,
    repository: ProvenanceRepository | None = None,
    state_path: str | Path = STATE_PATH,
    manifest_path: str | Path | None = None,
    batch_size: int = 250,
) -> IngestionReport:
    """Import a small manually curated snapshot; it is never presented as a live feed."""
    path = Path(snapshot_path)
    try:
        snapshot_obj = json.loads(path.read_text(encoding="utf-8"))
        snapshot = CuratedSnapshot.model_validate(snapshot_obj)
    except FileNotFoundError as exc:
        raise IngestionError(f"Curated snapshot not found: {path}") from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise IngestionValidationError(f"Curated snapshot validation failed: {exc}") from exc
    if snapshot.snapshot_type != "curated_extract":
        raise IngestionValidationError("Curated snapshot must be explicitly labelled snapshot_type='curated_extract'.")
    if snapshot.runtime_fetch_performed:
        raise IngestionValidationError(
            "This bundled curated snapshot must not claim the app runtime fetched the source pages."
        )
    manifest_file = Path(manifest_path) if manifest_path else (DATA_ROOT / "sources_manifest.yaml")
    known_sources = _manifest_source_ids(manifest_file)
    unknown = sorted({record.source_id for record in snapshot.records} - known_sources)
    if unknown:
        raise IngestionValidationError(f"Snapshot refers to source IDs absent from the manifest: {unknown}")
    identities = [(record.source_id, record.source_record_id) for record in snapshot.records]
    if len(set(identities)) != len(identities):
        raise IngestionValidationError("Curated snapshot contains duplicate (source_id, source_record_id) pairs.")

    checksum = sha256_file(path)
    snapshot_storage_id = _snapshot_namespace("curated", snapshot.snapshot_id, checksum)
    now = datetime.now(UTC)
    repository = repository or ProvenanceRepository()
    bundles: list[tuple[SourceRecord, str, CanonicalEntity, ProvenanceLink, list[tuple[str, str, str, Any]]]] = []
    source_counts: dict[str, int] = {}
    for record in snapshot.records:
        source_counts[record.source_id] = source_counts.get(record.source_id, 0) + 1
        source_record_id = f"{snapshot_storage_id}:{record.source_record_id}"
        source = _make_source_record(
            source_id=record.source_id,
            source_record_id=source_record_id,
            publisher=record.publisher,
            title=record.source_title,
            geography=record.geography,
            source_url=str(record.source_base_uri),
            record_url=str(record.record_uri),
            source_version=record.source_version,
            release_date=record.release_date,
            retrieved_at=record.source_accessed_at.astimezone(UTC),
            ingested_at=now,
            license_url=str(record.license_reference),
            license_summary=record.license_summary,
            checksum=checksum,
            quality_status=QualityStatus.REVIEWED,
            limitations=record.limitations + [
                "This record comes from a bundled, manually curated extract; it is not a live API response or a complete dataset."
            ],
            source_type=SourceType.CURATED_EXTRACT,
        )
        code_slug = normalize_slug(record.source_code)
        # Keep stable IDs for the two currently bundled source IDs. Any future curated source
        # receives its own deterministic namespace rather than silently inheriting the ESCO label.
        known_namespaces = {
            "onet_online_curated_sample": "onetonline",
            "esco_curated_sample": "esco",
        }
        source_namespace = known_namespaces.get(record.source_id, normalize_slug(record.source_id))
        internal_id = f"occupation:{source_namespace}:{snapshot_storage_id}:{code_slug}"
        entity = CanonicalEntity(
            internal_id=internal_id,
            entity_type=EntityType.OCCUPATION,
            source_id=record.source_id,
            source_record_id=source_record_id,
            source_uri=str(record.record_uri),
            source_title=record.source_title,
            source_code=record.source_code,
            publisher=record.publisher,
            geography=record.geography,
            source_version=record.source_version,
            release_date=record.release_date,
            accessed_at=record.source_accessed_at.astimezone(UTC),
            ingested_at=now,
            license_reference=str(record.license_reference),
            source_type=SourceType.CURATED_EXTRACT,
            source_values=record.source_values,
            normalized_values={
                "title": record.source_title.strip(),
                "code": record.source_code.strip(),
                "summary": record.summary.strip(),
                "selected_tasks": [item.strip() for item in record.selected_tasks],
                "selected_terms": [item.strip() for item in record.selected_terms],
                "selected_essential_skills": [item.strip() for item in record.selected_essential_skills],
                "record_kind": "curated_extract",
                "curation_domain": record.curation_domain,
                "curation_domain_is_editorial": record.curation_domain is not None,
                "not_student_evidence": True,
            },
            transformation_notes=record.transformation_notes,
            quality_status=QualityStatus.REVIEWED,
            last_verified_at=now,
            confidence=None,
            limitations=record.limitations + [
                "Occupation reference information must not be interpreted as an assessment of the individual student."
            ],
        )
        link = _make_link(
            internal_id,
            source,
            source_record_id,
            ["This link resolves to the exact cited source-page record; no cross-taxonomy equivalence is claimed."],
        )
        facts: list[tuple[str, str, str, Any]] = [
            (
                f"fact:{internal_id}:summary",
                "occupation_profile_summary",
                f"Summary of the {record.source_title} occupational profile, adapted from the cited official source.",
                {"summary": record.summary, "geography": record.geography, "source_kind": "curated_extract"},
            ),
        ]
        if record.selected_tasks:
            facts.append((
                f"fact:{internal_id}:tasks",
                "selected_occupational_tasks",
                f"Selected task summaries for {record.source_title}; concise paraphrases, not a complete task list.",
                {"tasks": record.selected_tasks, "source_kind": "curated_extract"},
            ))
        if record.selected_terms:
            facts.append((
                f"fact:{internal_id}:terms",
                "selected_occupational_terms",
                f"Selected source terms related to {record.source_title}; not student-skill scores.",
                {"terms": record.selected_terms, "source_kind": "curated_extract"},
            ))
        if record.selected_essential_skills:
            facts.append((
                f"fact:{internal_id}:essential-skills",
                "selected_essential_skills",
                f"Selected labels listed in the O*NET OnLine Essential Skills section for {record.source_title}; no individual score or rating is included.",
                {
                    "skills": record.selected_essential_skills,
                    "source_section": "Essential Skills",
                    "source_category_captured": True,
                    "source_skill_element_ids_captured": False,
                    "occupation_specific_ratings_included": False,
                    "source_kind": "curated_extract",
                },
            ))
        bundles.append((source, source_record_id, entity, link, facts))

    for chunk in _chunks(bundles, batch_size):
        repository.upsert_bundles(chunk)

    source_totals: dict[str, int] = {}
    for source_id, count in source_counts.items():
        event = {
            "source_id": source_id,
            "status": "curated_extract_imported",
            "started_at": iso_utc(now),
            "finished_at": iso_utc(),
            "snapshot_id": snapshot_storage_id,
            "normalizer_schema_version": NORMALIZER_SCHEMA_VERSION,
            "source_version": snapshot.snapshot_id,
            "snapshot_label": snapshot.snapshot_id,
            "snapshot_path": str(path.relative_to(DATA_ROOT)) if path.is_relative_to(DATA_ROOT) else path.name,
            "snapshot_sha256": checksum,
            "source_record_count": count,
            "runtime_fetch_performed": False,
            "source_data_is_live": False,
            "note": "Bundled curated source-backed extract imported idempotently; source runtime API/download remains separate.",
        }
        record_run_event(event, state_path=state_path)
        source_totals[source_id] = count
    return IngestionReport(
        source_id="curated_snapshot",
        status="curated_extract_imported",
        source_version=snapshot.snapshot_id,
        records_processed=len(bundles),
        records_upserted=len(bundles),
        facts_upserted=sum(len(bundle[4]) for bundle in bundles),
        file_sha256=checksum,
        warnings=[snapshot.runtime_fetch_note],
        details={
            "records_by_source": source_totals,
            "snapshot_type": snapshot.snapshot_type,
            "runtime_fetch_performed": False,
            "snapshot_id": snapshot_storage_id,
            "snapshot_label": snapshot.snapshot_id,
            "snapshot_sha256": checksum,
            "normalizer_schema_version": NORMALIZER_SCHEMA_VERSION,
            "snapshot_policy": "immutable_source_checksum_and_normalizer_version_namespace",
        },
    )


def _onet_column_map(columns: list[str], *, skills: bool) -> dict[str, str]:
    required = {
        "occupation_code": ("O*NET-SOC Code", "O*NET SOC Code"),
        "element_id": ("Element ID",),
        "element_name": ("Element Name",),
        "scale_id": ("Scale ID",),
        "data_value": ("Data Value",),
    } if skills else {
        "occupation_code": ("O*NET-SOC Code", "O*NET SOC Code"),
        "title": ("Title",),
        "description": ("Description",),
    }
    resolved = require_columns(columns, required, "O*NET essential skills" if skills else "O*NET occupation data")
    available = {normalize_header(item): item for item in columns}
    optional_aliases = {
        "title": ("Title",),
        "sample_n": ("N",),
        "standard_error": ("Standard Error",),
        "lower_ci_bound": ("Lower CI Bound",),
        "upper_ci_bound": ("Upper CI Bound",),
        "recommend_suppress": ("Recommend Suppress",),
        "not_relevant": ("Not Relevant",),
        "date": ("Date",),
    }
    for canonical, aliases in optional_aliases.items():
        match = next((available[normalize_header(alias)] for alias in aliases if normalize_header(alias) in available), None)
        if match:
            resolved[canonical] = match
    return resolved


def _onet_source_bundle(
    *,
    source_record_id: str,
    entity_id: str,
    record_title: str,
    source_uri: str,
    source_version: str,
    release_date: str,
    retrieved_at: datetime,
    ingested_at: datetime,
    checksum: str,
    source_values: dict[str, Any],
    normalized_values: dict[str, Any],
    entity_type: EntityType,
    fact_specs: list[tuple[str, str, str, Any]],
    quality: QualityStatus = QualityStatus.REVIEWED,
) -> tuple[SourceRecord, str, CanonicalEntity, ProvenanceLink, list[tuple[str, str, str, Any]]]:
    limitations = [
        "O*NET-SOC occupation reference is based on the United States economy; it is not an India-specific hiring or qualification rule.",
        "Occupational ratings describe source occupational context and must not be treated as an individual student's ability or interest score.",
    ]
    source = _make_source_record(
        source_id="onet_database",
        source_record_id=source_record_id,
        publisher=ONET_PUBLISHER,
        title=f"O*NET Database 31.0 — {record_title}",
        geography="United States",
        source_url=source_uri,
        record_url=None,
        source_version=source_version,
        release_date=release_date,
        retrieved_at=retrieved_at,
        ingested_at=ingested_at,
        license_url=ONET_LICENSE_URL,
        license_summary=(
            "Downloadable O*NET 31.0 Database content is available under CC BY 4.0 subject to official exceptions. "
            "Attribution names the O*NET 31.0 Database and USDOL/ETA, links the licence, and discloses changes."
        ),
        checksum=checksum,
        quality_status=quality,
        limitations=limitations,
        source_type=SourceType.OFFICIAL,
    )
    entity = CanonicalEntity(
        internal_id=entity_id,
        entity_type=entity_type,
        source_id="onet_database",
        source_record_id=source_record_id,
        source_uri=source_uri,
        source_title=record_title,
        source_code=source_values.get("O*NET-SOC Code") or source_values.get("Element ID"),
        publisher=ONET_PUBLISHER,
        geography="United States",
        source_version=source_version,
        release_date=release_date,
        accessed_at=retrieved_at,
        ingested_at=ingested_at,
        license_reference=ONET_LICENSE_URL,
        source_type=SourceType.OFFICIAL,
        source_values=source_values,
        normalized_values=normalized_values,
        transformation_notes=[
            "Original CSV field values are preserved in source_values.",
            "Normalized fields are stored separately; O*NET source scale IDs are not converted into SkillScope student scores.",
        ],
        quality_status=quality,
        last_verified_at=ingested_at if quality is QualityStatus.REVIEWED else None,
        limitations=limitations,
    )
    link = _make_link(
        entity_id,
        source,
        source_record_id,
        ["Exact source row identity; no cross-taxonomy or student-fit inference is made."],
    )
    return source, source_record_id, entity, link, fact_specs


@_track_import_failures("onet_database")
def import_onet_files(
    occupation_file: str | Path,
    essential_skills_file: str | Path,
    *,
    repository: ProvenanceRepository | None = None,
    state_path: str | Path = STATE_PATH,
    source_version: str | None = None,
    retrieved_at: str | None = None,
    release_date: str | None = None,
    batch_size: int = 500,
    manifest_path: str | Path | None = None,
) -> IngestionReport:
    """Validate and ingest the O*NET occupation table and its essential-skill observations."""
    _validate_manifest_target(manifest_path, "onet_database")
    occupation_path = Path(occupation_file)
    skills_path = Path(essential_skills_file)
    occupation_meta = _artifact_metadata(
        occupation_path, asset_id="onet_occupation_data", source_version=source_version,
        retrieved_at=retrieved_at, release_date=release_date,
    )
    skills_meta = _artifact_metadata(
        skills_path, asset_id="onet_essential_skills", source_version=source_version,
        retrieved_at=retrieved_at, release_date=release_date,
    )
    occupation_table = read_csv_table(occupation_path)
    skills_table = read_csv_table(skills_path)
    _validate_sha_metadata(occupation_meta, occupation_table.sha256, occupation_path.name)
    _validate_sha_metadata(skills_meta, skills_table.sha256, skills_path.name)
    occupation_cols = _onet_column_map(occupation_table.columns, skills=False)
    skills_cols = _onet_column_map(skills_table.columns, skills=True)

    occupation_deduped, occupation_duplicates = deduplicate_rows(
        occupation_table.rows,
        key_fn=lambda row: (row.get(occupation_cols["occupation_code"]) or "").strip(),
        label="O*NET occupation data",
    )
    skills_deduped, skills_duplicates = deduplicate_rows(
        skills_table.rows,
        key_fn=lambda row: ":".join([
            (row.get(skills_cols["occupation_code"]) or "").strip(),
            (row.get(skills_cols["element_id"]) or "").strip(),
            (row.get(skills_cols["scale_id"]) or "").strip(),
        ]),
        label="O*NET essential skills",
    )

    occupation_codes: set[str] = set()
    for row_number, row in enumerate(occupation_deduped, start=2):
        code = row.get(occupation_cols["occupation_code"], "").strip()
        title = row.get(occupation_cols["title"], "").strip()
        if not re.fullmatch(r"\d{2}-\d{4}\.\d{2}", code):
            raise IngestionValidationError(f"O*NET occupation row {row_number} has invalid O*NET-SOC code {code!r}.")
        if not title:
            raise IngestionValidationError(f"O*NET occupation row {row_number} has a blank title for {code}.")
        occupation_codes.add(code)
    unknown_skill_codes = sorted({
        row.get(skills_cols["occupation_code"], "").strip() for row in skills_deduped
        if row.get(skills_cols["occupation_code"], "").strip() not in occupation_codes
    })
    if unknown_skill_codes:
        raise IngestionValidationError(
            "O*NET essential-skill rows refer to occupation codes missing from Occupation Data: "
            + ", ".join(unknown_skill_codes[:12])
            + (" …" if len(unknown_skill_codes) > 12 else "")
        )
    # Validate every skill row before any database write. This prevents malformed
    # flags, unsupported scales or out-of-range ratings from leaving a partial import.
    scale_bounds = {"IM": (1.0, 5.0), "LV": (0.0, 7.0)}
    skill_validation: dict[tuple[str, str, str], tuple[float | None, bool, bool]] = {}
    for row_number, row in enumerate(skills_deduped, start=2):
        code = row.get(skills_cols["occupation_code"], "").strip()
        element_id = row.get(skills_cols["element_id"], "").strip()
        element_name = row.get(skills_cols["element_name"], "").strip()
        scale_id = row.get(skills_cols["scale_id"], "").strip().upper()
        if not code or not element_id or not element_name or not scale_id:
            raise IngestionValidationError(
                f"O*NET essential-skill row {row_number} is missing occupation code, Element ID, Element Name, or Scale ID."
            )
        if scale_id not in scale_bounds:
            raise IngestionValidationError(
                f"O*NET essential-skill row {row_number} uses unexpected scale {scale_id!r}; "
                "verify the pinned O*NET release and Scales Reference before extending this importer."
            )
        raw_value = row.get(skills_cols["data_value"], "")
        data_value = parse_optional_float(raw_value, field_name="Data Value", row_number=row_number)
        if data_value is not None:
            lower, upper = scale_bounds[scale_id]
            if not lower <= data_value <= upper:
                raise IngestionValidationError(
                    f"O*NET essential-skill row {row_number} Data Value {data_value} is outside scale "
                    f"{scale_id}'s expected range {lower:g}–{upper:g}."
                )
        raw_suppress = row.get(skills_cols.get("recommend_suppress", ""), "").strip().casefold()
        raw_not_relevant = row.get(skills_cols.get("not_relevant", ""), "").strip().casefold()
        valid_flags = {"", "y", "n", "yes", "no", "true", "false", "1", "0"}
        if raw_suppress not in valid_flags or raw_not_relevant not in valid_flags:
            raise IngestionValidationError(
                f"O*NET essential-skill row {row_number} contains an unknown suppression/relevance flag."
            )
        should_suppress = raw_suppress in {"y", "yes", "true", "1"}
        not_relevant = raw_not_relevant in {"y", "yes", "true", "1"}
        skill_validation[(code, element_id, scale_id)] = (data_value, should_suppress, not_relevant)

    occupation_version = str(occupation_meta.get("source_version") or source_version or "").strip()
    skills_version = str(skills_meta.get("source_version") or source_version or "").strip()
    if not occupation_version or not skills_version:
        raise IngestionValidationError("O*NET import is missing a source version.")
    if occupation_version != skills_version:
        raise IngestionValidationError(
            f"O*NET files have mismatched versions ({occupation_version!r} vs {skills_version!r}); import stopped."
        )
    occ_retrieved = parse_datetime(str(occupation_meta.get("retrieved_at")))
    skills_retrieved = parse_datetime(str(skills_meta.get("retrieved_at")))
    occ_release = str(occupation_meta.get("release_date") or release_date or "")
    skills_release = str(skills_meta.get("release_date") or release_date or "")
    if occ_release != skills_release:
        raise IngestionValidationError("O*NET files have mismatched release dates; import stopped.")

    combined_checksum = hashlib.sha256(
        f"{occupation_version}\0{occupation_table.sha256}\0{skills_table.sha256}".encode("utf-8")
    ).hexdigest()
    snapshot_id = _snapshot_namespace("onet", occupation_version, combined_checksum)
    now = datetime.now(UTC)
    repo = repository or ProvenanceRepository()
    processed_bundles = 0
    fact_count = 0
    for row_chunk in _chunks(occupation_deduped, batch_size):
        bundles = []
        for row in row_chunk:
            code = row[occupation_cols["occupation_code"]].strip()
            title = row[occupation_cols["title"]].strip()
            description = row[occupation_cols["description"]].strip()
            record_id = f"{snapshot_id}:occupation:{code}"
            internal_id = f"occupation:onet:{snapshot_id}:{code}"
            source_values = dict(row)
            normalized_values = {
                "code": code,
                "title": title,
                "description": description,
                "taxonomy": "O*NET-SOC",
                "source_geography": "United States",
                "rating_semantics": "not_student_evidence",
            }
            fact_specs = [
                (f"fact:{internal_id}:title", "occupation_title", f"O*NET lists the occupation as {title}.", {"title": title, "code": code}),
            ]
            if description:
                fact_specs.append((
                    f"fact:{internal_id}:description",
                    "occupation_description",
                    f"O*NET occupation description for {title}.",
                    {"description": description, "geography": "United States", "not_student_evidence": True},
                ))
            bundles.append(_onet_source_bundle(
                source_record_id=record_id,
                entity_id=internal_id,
                record_title=title,
                source_uri=str(occupation_meta["source_url"]),
                source_version=occupation_version,
                release_date=occ_release,
                retrieved_at=occ_retrieved,
                ingested_at=now,
                checksum=occupation_table.sha256,
                source_values=source_values,
                normalized_values=normalized_values,
                entity_type=EntityType.OCCUPATION,
                fact_specs=fact_specs,
            ))
            fact_count += len(fact_specs)
        repo.upsert_bundles(bundles)
        processed_bundles += len(bundles)

    skill_observations = 0
    suppressed = 0
    for row_chunk in _chunks(skills_deduped, batch_size):
        bundles = []
        for row_number, row in enumerate(row_chunk, start=2):
            code = row[skills_cols["occupation_code"]].strip()
            element_id = row[skills_cols["element_id"]].strip()
            element_name = row[skills_cols["element_name"]].strip()
            scale_id = row[skills_cols["scale_id"]].strip()
            if not element_id or not element_name or not scale_id:
                raise IngestionValidationError(
                    f"O*NET essential skill row {row_number} is missing Element ID, Element Name, or Scale ID."
                )
            raw_value = row.get(skills_cols["data_value"], "")
            data_value, should_suppress, not_relevant = skill_validation[(code, element_id, scale_id)]
            should_hide_fact = should_suppress or not_relevant or data_value is None
            suppressed += int(should_hide_fact)
            composite = f"essential-skill:{code}:{element_id}:{scale_id}"
            record_id = f"{snapshot_id}:{composite}"
            internal_id = f"occupation_skill_observation:onet:{snapshot_id}:{normalize_slug(composite)}"
            source_values = dict(row)
            normalized_values = {
                "occupation_code": code,
                "element_id": element_id,
                "element_name": element_name,
                "scale_id": scale_id,
                "source_scale_value": data_value,
                "source_scale_value_raw": raw_value,
                "recommend_suppress": should_suppress,
                "not_relevant": not_relevant,
                "value_is_student_score": False,
            }
            quality = QualityStatus.UNVERIFIED if should_hide_fact else QualityStatus.REVIEWED
            facts = []
            if not should_hide_fact:
                facts.append((
                    f"fact:{internal_id}:rating",
                    "occupation_skill_rating",
                    f"O*NET reports {element_name!r} for occupation {code} on source scale {scale_id}; this is an occupational reference value, not a student score.",
                    {
                        "occupation_code": code,
                        "skill": element_name,
                        "element_id": element_id,
                        "scale_id": scale_id,
                        "value": data_value,
                        "source_version": skills_version,
                    },
                ))
                fact_count += 1
            bundles.append(_onet_source_bundle(
                source_record_id=record_id,
                entity_id=internal_id,
                record_title=f"{element_name} — {code} — {scale_id}",
                source_uri=str(skills_meta["source_url"]),
                source_version=skills_version,
                release_date=skills_release,
                retrieved_at=skills_retrieved,
                ingested_at=now,
                checksum=skills_table.sha256,
                source_values=source_values,
                normalized_values=normalized_values,
                entity_type=EntityType.OCCUPATION_SKILL_OBSERVATION,
                fact_specs=facts,
                quality=quality,
            ))
        repo.upsert_bundles(bundles)
        processed_bundles += len(bundles)
        skill_observations += len(bundles)

    summary = IngestionReport(
        source_id="onet_database",
        status="imported",
        source_version=occupation_version,
        records_processed=len(occupation_deduped) + len(skills_deduped),
        records_upserted=processed_bundles,
        facts_upserted=fact_count,
        duplicate_rows_skipped=occupation_duplicates + skills_duplicates,
        suppressed_ratings_not_displayed=suppressed,
        file_sha256=combined_checksum,
        warnings=[
            "O*NET is a United States occupational reference; never interpret its occupational ratings as a student's scores.",
            "Import occurred from local files; no live API or continuous freshness is implied.",
        ],
        details={
            "occupation_records": len(occupation_deduped),
            "occupation_skill_observations": skill_observations,
            "occupation_duplicates_skipped": occupation_duplicates,
            "skill_observation_duplicates_skipped": skills_duplicates,
            "occupation_file_sha256": occupation_table.sha256,
            "essential_skills_file_sha256": skills_table.sha256,
            "occupation_file_size_bytes": occupation_table.byte_size,
            "essential_skills_file_size_bytes": skills_table.byte_size,
            "source_urls": [occupation_meta["source_url"], skills_meta["source_url"]],
            "snapshot_id": snapshot_id,
            "normalizer_schema_version": NORMALIZER_SCHEMA_VERSION,
            "snapshot_policy": "immutable_source_version_artifact_checksum_and_normalizer_version_namespace",
        },
    )
    imported_at = iso_utc()
    if manifest_path is not None:
        update_source_manifest_import(
            manifest_path,
            source_id="onet_database",
            source_version=occupation_version,
            snapshot_id=snapshot_id,
            checksum_sha256=combined_checksum,
            imported_at=imported_at,
            report=summary,
            acquisition_method=(
                "operator_supplied_pinned_local_files_with_operator_declared_retrieval_metadata"
                if occupation_meta.get("manual_file") or skills_meta.get("manual_file")
                else "sidecar_metadata_validated_source_origin_not_cryptographically_attested"
            ),
        )
    event = {
        "source_id": "onet_database",
        "status": "imported",
        "started_at": iso_utc(now),
        "finished_at": iso_utc(),
        "source_version": occupation_version,
        "snapshot_id": snapshot_id,
        "normalizer_schema_version": NORMALIZER_SCHEMA_VERSION,
        "sha256": combined_checksum,
        "report": summary.to_dict(),
        "source_data_is_live": False,
    }
    record_run_event(event, state_path=state_path)
    return summary


def _esco_members(path: Path, *, language: str = "en") -> dict[str, str]:
    """Select a consistent language's ESCO CSV members without extracting the archive.

    An export can contain multiple language variants. If the requested language cannot
    be resolved uniquely, stop rather than silently importing the first file found.
    """
    import zipfile

    if path.suffix.casefold() != ".zip":
        return {"occupations": "", "skills": "", "relations": ""}
    language = language.strip().casefold()
    if not re.fullmatch(r"[a-z]{2,3}(?:-[a-z0-9]{2,8})?", language):
        raise IngestionValidationError(f"Invalid ESCO language code {language!r}.")
    try:
        with zipfile.ZipFile(path) as archive:
            archive_items = archive.infolist()
            if len(archive_items) > MAX_ESCO_ARCHIVE_MEMBERS:
                raise IngestionValidationError(
                    f"ESCO ZIP contains {len(archive_items)} entries, above the safety limit of {MAX_ESCO_ARCHIVE_MEMBERS}."
                )
            csv_names = [item.filename for item in archive_items if not item.is_dir() and item.filename.casefold().endswith(".csv")]
    except (zipfile.BadZipFile, OSError, zipfile.LargeZipFile) as exc:
        raise IngestionValidationError(f"Invalid or unreadable ESCO package ZIP: {path}") from exc

    candidates: dict[str, list[str]] = {"occupations": [], "skills": [], "relations": []}
    for name in csv_names:
        base = Path(name).name.casefold()
        if "occupationskillrelations" in base or "occupation_skill_relations" in base:
            candidates["relations"].append(name)
        elif base.startswith("occupations") and "relation" not in base:
            candidates["occupations"].append(name)
        elif base.startswith("skills") and not any(token in base for token in ("relation", "hierarchy", "group")):
            candidates["skills"].append(name)

    def has_language(filename: str, code: str) -> bool:
        stem = Path(filename).stem.casefold()
        # Official exports commonly use *_en.csv; allow '-' or '.' separators too.
        return bool(re.search(rf"(?:^|[_\-.]){re.escape(code)}$", stem))

    resolved: dict[str, str] = {}
    for kind, files in candidates.items():
        if not files:
            continue
        lang_matches = [name for name in files if has_language(name, language)]
        if len(lang_matches) == 1:
            resolved[kind] = lang_matches[0]
        elif len(lang_matches) > 1:
            raise IngestionValidationError(
                f"ESCO ZIP has multiple {kind} CSVs for language {language!r}: {lang_matches}."
            )
        elif len(files) == 1 and not re.search(r"(?:^|[_\-.])[a-z]{2,3}(?:-[a-z0-9]{2,8})?\.csv$", files[0].casefold()):
            # Language-neutral / unsuffixed package with exactly one member of this kind.
            resolved[kind] = files[0]
        elif len(files) == 1 and has_language(files[0], language):
            resolved[kind] = files[0]
        else:
            raise IngestionValidationError(
                f"Could not uniquely select the requested {language!r} language for ESCO {kind}. "
                f"Available candidate files: {files}. Supply an export with an unambiguous language suffix."
            )
    return resolved


def _esco_column_map(columns: list[str], *, is_relation: bool = False) -> dict[str, str]:
    if is_relation:
        required = {
            "occupation_uri": ("occupationUri", "occupation_uri", "occupationURI"),
            "skill_uri": ("skillUri", "skill_uri", "skillURI"),
        }
    else:
        required = {
            "concept_uri": ("conceptUri", "concept_uri", "conceptURI", "uri"),
            "preferred_label": ("preferredLabel", "preferred_label", "conceptPT", "concept_pt", "conceptPreferredTerm", "label", "title"),
        }
    resolved = require_columns(columns, required, "ESCO occupation-skill relations" if is_relation else "ESCO concepts")
    available = {normalize_header(item): item for item in columns}
    optional_aliases = {
        "definition": ("definition",),
        "description": ("description",),
        "scope_note": ("scopeNote", "scope_note"),
        "code": ("code", "escoCode", "esco_code", "iscoCode", "isco_code", "ISCO code"),
        "isco_group": ("iscoGroup", "isco_group"),
        "status": ("status", "conceptStatus", "concept_status"),
        "modified_date": ("modifiedDate", "modified_date"),
        "alt_labels": ("altLabels", "alt_labels"),
        "concept_type": ("conceptType", "concept_type"),
        "relation_type": ("relationType", "relationshipType", "relation_type", "relationship_type"),
        "relation_relevance": ("relationRelevance", "relation_relevance"),
        "skill_type": ("skillType", "skill_type"),
    }
    for canonical, aliases in optional_aliases.items():
        match = next((available[normalize_header(alias)] for alias in aliases if normalize_header(alias) in available), None)
        if match:
            resolved[canonical] = match
    return resolved


def _canonical_url_for_esco(uri: str) -> str:
    return "https://esco.ec.europa.eu/en/classification/occupation?uri=" + quote(uri, safe="")


@_track_import_failures("esco_classification")
def import_esco_package(
    package_file: str | Path,
    *,
    source_version: str,
    retrieved_at: str,
    release_date: str | None = None,
    language: str = "en",
    repository: ProvenanceRepository | None = None,
    state_path: str | Path = STATE_PATH,
    batch_size: int = 500,
    include_skills: bool = True,
    include_relations: bool = True,
    manifest_path: str | Path | None = None,
) -> IngestionReport:
    """Ingest selected ESCO CSV members from a package downloaded via the official portal.

    The ESCO package download currently uses a portal selection/request workflow. This
    importer works from a locally obtained ZIP and never pretends to download it itself.
    """
    pinned_version = "ESCO v1.2.1"
    pinned_release_date = "2025-12-10"
    if source_version.strip() != pinned_version:
        raise IngestionValidationError(
            f"ESCO importer is pinned to {pinned_version!r}; supplied version was {source_version!r}. "
            "Review the official download page and update the source manifest/code deliberately before changing the pin."
        )
    if release_date and release_date != pinned_release_date:
        raise IngestionValidationError(
            f"ESCO {pinned_version} is pinned to release/update date {pinned_release_date}; got {release_date!r}."
        )
    release_date = pinned_release_date
    if include_relations and not include_skills:
        raise IngestionValidationError("ESCO occupation-skill relations require the matching skill concepts to be imported too.")
    _validate_manifest_target(manifest_path, "esco_classification")
    retrieved = parse_datetime(retrieved_at)
    path = Path(package_file)
    if not path.is_file():
        raise IngestionError(f"ESCO package does not exist or is not a regular file: {path}")
    if path.suffix.casefold() != ".zip":
        raise IngestionValidationError("ESCO package ingestion expects the official CSV ZIP package.")
    if path.stat().st_size > MAX_ESCO_PACKAGE_BYTES:
        raise IngestionValidationError(
            f"ESCO package exceeds the safety limit of {MAX_ESCO_PACKAGE_BYTES} bytes."
        )
    file_hash = sha256_file(path)
    snapshot_id = _snapshot_namespace("esco", source_version, file_hash)
    members = _esco_members(path, language=language)
    if not members.get("occupations"):
        raise IngestionValidationError(
            "Could not identify the ESCO occupations CSV. Confirm this is an English (or explicitly selected language) classification ZIP."
        )
    occupation_table = read_csv_table(path, member_name=members["occupations"])
    occupation_cols = _esco_column_map(occupation_table.columns)
    occupation_rows, occupation_duplicates = deduplicate_rows(
        occupation_table.rows,
        key_fn=lambda row: (row.get(occupation_cols["concept_uri"]) or "").strip(),
        label="ESCO occupations",
    )
    skills_table = None
    skills_cols = None
    skills_rows: list[dict[str, str]] = []
    skills_duplicates = 0
    if include_skills:
        if not members.get("skills"):
            raise IngestionValidationError("ESCO ZIP does not contain a uniquely discoverable skills CSV.")
        skills_table = read_csv_table(path, member_name=members["skills"])
        skills_cols = _esco_column_map(skills_table.columns)
        skills_rows, skills_duplicates = deduplicate_rows(
            skills_table.rows,
            key_fn=lambda row: (row.get(skills_cols["concept_uri"]) or "").strip(),
            label="ESCO skills",
        )
    relations_table = None
    relations_cols = None
    relations_rows: list[dict[str, str]] = []
    relation_duplicates = 0
    if include_relations:
        if not members.get("relations"):
            raise IngestionValidationError("ESCO ZIP does not contain an occupationSkillRelations CSV.")
        relations_table = read_csv_table(path, member_name=members["relations"])
        relations_cols = _esco_column_map(relations_table.columns, is_relation=True)
        relations_rows, relation_duplicates = deduplicate_rows(
            relations_table.rows,
            key_fn=lambda row: "|".join([
                (row.get(relations_cols["occupation_uri"]) or "").strip(),
                (row.get(relations_cols["skill_uri"]) or "").strip(),
                (row.get(relations_cols.get("relation_type", "")) or "").strip() or "occupation-skill",
                (row.get(relations_cols.get("relation_relevance", "")) or "").strip(),
            ]),
            label="ESCO occupation-skill relations",
        )

    occupation_uris: set[str] = set()
    for row_num, row in enumerate(occupation_rows, start=2):
        uri = row.get(occupation_cols["concept_uri"], "").strip()
        label = row.get(occupation_cols["preferred_label"], "").strip()
        if not uri.startswith("http://data.europa.eu/esco/occupation/"):
            raise IngestionValidationError(f"ESCO occupation row {row_num} has a non-occupation or invalid concept URI: {uri!r}.")
        if not label:
            raise IngestionValidationError(f"ESCO occupation row {row_num} has an empty preferred label for {uri}.")
        if occupation_cols.get("concept_type") and row.get(occupation_cols["concept_type"], "").strip():
            concept_type = row.get(occupation_cols["concept_type"], "").strip().casefold()
            # ESCO's documented CSV values include OC (occupation) and OG (occupation group),
            # not only the human-readable word "occupation" often used in simplified fixtures.
            if concept_type not in {"oc", "og", "occupation", "occupation_group", "occupation group"} and "occupation" not in concept_type:
                raise IngestionValidationError(f"ESCO occupation file contains unexpected concept type {concept_type!r} at row {row_num}.")
        occupation_uris.add(uri)
    skill_uris: set[str] = set()
    if skills_table and skills_cols:
        for row_num, row in enumerate(skills_rows, start=2):
            uri = row.get(skills_cols["concept_uri"], "").strip()
            label = row.get(skills_cols["preferred_label"], "").strip()
            if not uri.startswith("http://data.europa.eu/esco/skill/"):
                raise IngestionValidationError(f"ESCO skill row {row_num} has an invalid skill concept URI: {uri!r}.")
            if not label:
                raise IngestionValidationError(f"ESCO skill row {row_num} has an empty preferred label for {uri}.")
            if skills_cols.get("concept_type") and row.get(skills_cols["concept_type"], "").strip():
                concept_type = row.get(skills_cols["concept_type"], "").strip().casefold()
                if concept_type not in {"sk", "sg", "skill", "skill/competence", "skill_competence", "competence"} and not any(word in concept_type for word in ("skill", "competence")):
                    raise IngestionValidationError(f"ESCO skills file contains unexpected concept type {concept_type!r} at row {row_num}.")
            skill_uris.add(uri)
    if relations_cols:
        relation_orphans = [
            row for row in relations_rows
            if (row.get(relations_cols["occupation_uri"], "").strip() not in occupation_uris)
            or (include_skills and skills_table and row.get(relations_cols["skill_uri"], "").strip() not in skill_uris)
        ]
        # The official file may cover only a subset if user deliberately supplied partial files;
        # fail closed because such a package should be complete before relationship ingestion.
        if relation_orphans:
            raise IngestionValidationError(
                f"ESCO relations contain {len(relation_orphans)} endpoint(s) missing from supplied occupations/skills files; import stopped."
            )

    repo = repository or ProvenanceRepository()
    now = datetime.now(UTC)
    bundles: list[tuple[SourceRecord, str, CanonicalEntity, ProvenanceLink, list[tuple[str, str, str, Any]]]] = []

    def concept_bundle(row: dict[str, str], cols: dict[str, str], entity_type: EntityType):
        uri = row[cols["concept_uri"]].strip()
        label = row[cols["preferred_label"]].strip()
        code_field = cols.get("code") or cols.get("isco_group")
        code = row.get(code_field, "").strip() if code_field else ""
        source_record_id = f"{snapshot_id}:{uri}"
        uri_digest = hashlib.sha256(uri.encode("utf-8")).hexdigest()[:24]
        internal_id = f"{entity_type.value}:esco:{snapshot_id}:{uri_digest}"
        label_kind = "occupation" if entity_type is EntityType.OCCUPATION else "skill"
        record_url = uri  # ESCO's concept URI is the stable source identifier and provenance target.
        display_url = _canonical_url_for_esco(uri) if label_kind == "occupation" else None
        source_values = dict(row)
        text_description = row.get(cols.get("description", ""), "").strip() if cols.get("description") else ""
        text_definition = row.get(cols.get("definition", ""), "").strip() if cols.get("definition") else ""
        text_scope_note = row.get(cols.get("scope_note", ""), "").strip() if cols.get("scope_note") else ""
        normalized_values = {
            "title": label,
            "concept_uri": uri,
            "display_url": display_url,
            "code": code or None,
            "description": text_description or None,
            "definition": text_definition or None,
            "scope_note": text_scope_note or None,
            "taxonomy": "ESCO",
            "geography_context": "European classification context",
            "not_student_evidence": True,
        }
        source = _make_source_record(
            source_id="esco_classification",
            source_record_id=source_record_id,
            publisher=ESCO_PUBLISHER,
            title=f"ESCO {label_kind.title()} — {label}",
            geography="European classification context",
            source_url=ESCO_DOWNLOAD_URL,
            record_url=record_url,
            source_version=source_version,
            release_date=release_date,
            retrieved_at=retrieved,
            ingested_at=now,
            license_url=ESCO_LICENSE_URL,
            license_summary=(
                "ESCO classification reuse is permitted under the European Commission document reuse framework; "
                "applications must acknowledge the European Commission classification and clearly identify adaptations."
            ),
            checksum=file_hash,
            quality_status=QualityStatus.REVIEWED,
            limitations=[
                "European occupational/skills taxonomy; not evidence of Indian labour demand, wages, or regulated qualifications.",
                "Original concept URI is preserved; no O*NET/NCS/NSDC equivalence is inferred by this import.",
            ],
            source_type=SourceType.OFFICIAL,
        )
        entity = CanonicalEntity(
            internal_id=internal_id,
            entity_type=entity_type,
            source_id="esco_classification",
            source_record_id=source_record_id,
            source_uri=record_url,
            source_title=label,
            source_code=code or None,
            publisher=ESCO_PUBLISHER,
            geography="European classification context",
            source_version=source_version,
            release_date=source.release_date,
            accessed_at=retrieved,
            ingested_at=now,
            license_reference=ESCO_LICENSE_URL,
            source_type=SourceType.OFFICIAL,
            source_values=source_values,
            normalized_values=normalized_values,
            transformation_notes=[
                "Raw ESCO export row is retained in source_values.",
                "URI is the stable ESCO concept identity; normalized labels do not replace the original URI.",
            ],
            quality_status=QualityStatus.REVIEWED,
            last_verified_at=now,
            limitations=source.limitations,
        )
        link = _make_link(internal_id, source, source_record_id, ["Exact ESCO concept URI identity; no cross-taxonomy match asserted."])
        facts = [(
            f"fact:{internal_id}:label",
            f"esco_{label_kind}_label",
            f"ESCO preferred label for this {label_kind} concept.",
            {"preferred_label": label, "concept_uri": uri, "taxonomy": "ESCO"},
        )]
        if text_description:
            facts.append((f"fact:{internal_id}:description", f"esco_{label_kind}_description", f"ESCO description for {label}.", {"description": text_description, "concept_uri": uri}))
        if text_definition:
            facts.append((f"fact:{internal_id}:definition", f"esco_{label_kind}_definition", f"ESCO definition for {label}.", {"definition": text_definition, "concept_uri": uri}))
        return source, source_record_id, entity, link, facts

    facts_upserted = 0
    for row_chunk in _chunks(occupation_rows, batch_size):
        bundles = [concept_bundle(row, occupation_cols, EntityType.OCCUPATION) for row in row_chunk]
        repo.upsert_bundles(bundles)
        facts_upserted += sum(len(bundle[4]) for bundle in bundles)
    processed_concepts = len(occupation_rows)
    if skills_table and skills_cols:
        for row_chunk in _chunks(skills_rows, batch_size):
            bundles = [concept_bundle(row, skills_cols, EntityType.SKILL) for row in row_chunk]
            repo.upsert_bundles(bundles)
            facts_upserted += sum(len(bundle[4]) for bundle in bundles)
        processed_concepts += len(skills_rows)

    relation_count = 0
    if relations_table and relations_cols:
        for row_chunk in _chunks(relations_rows, batch_size):
            relation_bundles = []
            for row in row_chunk:
                occupation_uri = row[relations_cols["occupation_uri"]].strip()
                skill_uri = row[relations_cols["skill_uri"]].strip()
                relation_type = row.get(relations_cols.get("relation_type", ""), "").strip() or "occupation-skill"
                relation_relevance = row.get(relations_cols.get("relation_relevance", ""), "").strip() or None
                relation_digest = hashlib.sha256(
                    f"{occupation_uri}|{skill_uri}|{relation_type}|{relation_relevance or ''}".encode("utf-8")
                ).hexdigest()[:32]
                source_record_id = f"{snapshot_id}:occupation-skill-relation:{relation_digest}"
                internal_id = f"occupation_skill_observation:esco:{snapshot_id}:{relation_digest}"
                source_values = dict(row)
                normalized_values = {
                    "occupation_uri": occupation_uri,
                    "skill_uri": skill_uri,
                    "relation_type": relation_type,
                    "relation_relevance": relation_relevance,
                    "taxonomy": "ESCO",
                    "geography_context": "European classification context",
                    "not_student_evidence": True,
                }
                source = _make_source_record(
                    source_id="esco_classification",
                    source_record_id=source_record_id,
                    publisher=ESCO_PUBLISHER,
                    title="ESCO occupation-skill relationship",
                    geography="European classification context",
                    source_url=ESCO_DOWNLOAD_URL,
                    record_url=str(ESCO_VERSION_PAGE),
                    source_version=source_version,
                    release_date=release_date,
                    retrieved_at=retrieved,
                    ingested_at=now,
                    license_url=ESCO_LICENSE_URL,
                    license_summary="ESCO classification reuse is permitted under the European Commission document reuse framework; acknowledge ESCO and identify adaptations.",
                    checksum=file_hash,
                    quality_status=QualityStatus.REVIEWED,
                    limitations=["Relationship endpoints must resolve to concepts in the same package/version.", "EU classification relationship, not an individual student score."],
                    source_type=SourceType.OFFICIAL,
                )
                entity = CanonicalEntity(
                    internal_id=internal_id,
                    entity_type=EntityType.OCCUPATION_SKILL_OBSERVATION,
                    source_id="esco_classification",
                    source_record_id=source_record_id,
                    source_uri=str(ESCO_VERSION_PAGE),
                    source_title="ESCO occupation-skill relationship",
                    source_code=source_record_id,
                    publisher=ESCO_PUBLISHER,
                    geography="European classification context",
                    source_version=source_version,
                    release_date=source.release_date,
                    accessed_at=retrieved,
                    ingested_at=now,
                    license_reference=ESCO_LICENSE_URL,
                    source_type=SourceType.OFFICIAL,
                    source_values=source_values,
                    normalized_values=normalized_values,
                    transformation_notes=["Original occupation/skill URIs preserved; relation type normalized only when blank."],
                    quality_status=QualityStatus.REVIEWED,
                    last_verified_at=now,
                    limitations=source.limitations,
                )
                link = _make_link(internal_id, source, source_record_id, ["Relationship record imported from the same pinned ESCO package."])
                facts = [(
                    f"fact:{internal_id}:relation",
                    "occupation_skill_relation",
                    "ESCO links the specified occupation concept and skill concept in this relationship record.",
                    normalized_values,
                )]
                relation_bundles.append((source, source_record_id, entity, link, facts))
            repo.upsert_bundles(relation_bundles)
            relation_count += len(relation_bundles)
        processed_concepts += relation_count
        facts_upserted += relation_count

    summary = IngestionReport(
        source_id="esco_classification",
        status="imported",
        source_version=source_version,
        records_processed=processed_concepts,
        records_upserted=processed_concepts,
        facts_upserted=facts_upserted,
        duplicate_rows_skipped=occupation_duplicates + skills_duplicates + relation_duplicates,
        file_sha256=file_hash,
        warnings=[
            "ESCO is a European occupational taxonomy; it is not an Indian demand or qualification dataset.",
            "The package was supplied locally; no live ESCO API/download is implied by this import.",
        ],
        details={
            "occupation_records": len(occupation_rows),
            "skill_records": len(skills_rows),
            "occupation_skill_relations": relation_count,
            "duplicates_skipped": occupation_duplicates + skills_duplicates + relation_duplicates,
            "package_file": path.name,
            "package_sha256": file_hash,
            "selected_members": members,
            "snapshot_id": snapshot_id,
            "normalizer_schema_version": NORMALIZER_SCHEMA_VERSION,
            "snapshot_policy": "immutable_source_version_package_checksum_and_normalizer_version_namespace",
        },
    )
    imported_at = iso_utc()
    if manifest_path is not None:
        update_source_manifest_import(
            manifest_path,
            source_id="esco_classification",
            source_version=source_version,
            snapshot_id=snapshot_id,
            checksum_sha256=file_hash,
            imported_at=imported_at,
            report=summary,
            acquisition_method="operator_supplied_zip_version_and_retrieval_timestamp_declared;_portal_origin_not_independently_verified",
        )
    event = {
        "source_id": "esco_classification",
        "status": "imported",
        "started_at": iso_utc(now),
        "finished_at": iso_utc(),
        "source_version": source_version,
        "snapshot_id": snapshot_id,
        "normalizer_schema_version": NORMALIZER_SCHEMA_VERSION,
        "sha256": file_hash,
        "report": summary.to_dict(),
        "source_data_is_live": False,
    }
    record_run_event(event, state_path=state_path)
    return summary
