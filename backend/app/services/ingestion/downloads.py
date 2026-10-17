"""Allow-listed official-source downloader with retries, hashes, and run state."""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from app.services.ingestion.common import (
    DATA_ROOT,
    IngestionError,
    IngestionValidationError,
    RAW_ROOT,
    RUNS_ROOT,
    STATE_PATH,
    iso_utc,
    normalize_header,
    record_run_event,
    sha256_file,
    safe_host,
    write_json_atomic,
)
from app.config import external_cache_ttl_seconds, resolve_database_path

ONET_LICENSE_URL = "https://www.onetcenter.org/license_db.html"
ONET_RELEASE_URL = "https://www.onetcenter.org/db_releases.html"


@dataclass(frozen=True)
class SourceAsset:
    asset_id: str
    source_id: str
    filename: str
    url: str
    allowed_hosts: tuple[str, ...]
    required_header_groups: tuple[tuple[str, ...], ...]
    source_version: str
    release_date: str
    license_url: str
    license_summary: str
    max_bytes: int = 100 * 1024 * 1024


ASSETS: dict[str, SourceAsset] = {
    "onet_occupation_data": SourceAsset(
        asset_id="onet_occupation_data",
        source_id="onet_database",
        filename="occupation_data.csv",
        url="https://www.onetcenter.org/dl_files/database/db_31_0_csv/occupation_data.csv",
        allowed_hosts=("www.onetcenter.org",),
        required_header_groups=(
            ("O*NET-SOC Code", "O*NET SOC Code"),
            ("Title",),
            ("Description",),
        ),
        source_version="O*NET Database 31.0",
        release_date="2026-08",
        license_url=ONET_LICENSE_URL,
        license_summary="CC BY 4.0 for downloadable O*NET 31.0 Database files, subject to the official licence exceptions; attribution, licence link, and modification notice required.",
        max_bytes=30 * 1024 * 1024,
    ),
    "onet_essential_skills": SourceAsset(
        asset_id="onet_essential_skills",
        source_id="onet_database",
        filename="essential_skills.csv",
        url="https://www.onetcenter.org/dl_files/database/db_31_0_csv/essential_skills.csv",
        allowed_hosts=("www.onetcenter.org",),
        required_header_groups=(
            ("O*NET-SOC Code", "O*NET SOC Code"),
            ("Element ID",),
            ("Element Name",),
            ("Scale ID",),
            ("Data Value",),
        ),
        source_version="O*NET Database 31.0",
        release_date="2026-08",
        license_url=ONET_LICENSE_URL,
        license_summary="CC BY 4.0 for downloadable O*NET 31.0 Database files, subject to the official licence exceptions; attribution, licence link, and modification notice required.",
        max_bytes=80 * 1024 * 1024,
    ),
}


def _validate_request_url(url: str, asset: SourceAsset) -> None:
    parsed = urlparse(url)
    if (
        parsed.scheme.casefold() != "https"
        or safe_host(url) not in asset.allowed_hosts
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise IngestionValidationError(
            f"Asset {asset.asset_id!r} encountered a redirect outside its HTTPS host/port allow-list."
        )


def _validate_allowed_url(asset: SourceAsset) -> None:
    _validate_request_url(asset.url, asset)


def _validate_csv_header(path: Path, asset: SourceAsset) -> list[str]:
    import csv

    # We intentionally inspect only the header here; full row validation belongs to the importer.
    raw = path.read_bytes()[:256 * 1024]
    if raw.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        raise IngestionValidationError(f"{asset.asset_id} returned HTML rather than a data file.")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    first_line = text.splitlines()[0] if text.splitlines() else ""
    try:
        dialect = csv.Sniffer().sniff(text[:8192], delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    header = next(csv.reader([first_line], dialect=dialect), [])
    normalized = {normalize_header(item) for item in header}
    for aliases in asset.required_header_groups:
        if not any(normalize_header(alias) in normalized for alias in aliases):
            raise IngestionValidationError(
                f"{asset.asset_id} is missing expected header group {aliases}; received {header!r}."
            )
    if len(header) < len(asset.required_header_groups):
        raise IngestionValidationError(f"{asset.asset_id} returned an implausibly short header.")
    return header


def _verified_cache_metadata(target_path: Path, asset: SourceAsset, ttl_seconds: int) -> tuple[dict[str, Any], float] | None:
    """Return a fresh cached asset only when its sidecar, timestamp and checksum all verify."""
    if ttl_seconds <= 0 or not target_path.is_file():
        return None
    sidecar = Path(str(target_path) + ".metadata.json")
    if not sidecar.is_file():
        return None
    try:
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            return None
        if metadata.get("asset_id") != asset.asset_id or metadata.get("source_url") != asset.url:
            return None
        if metadata.get("source_version") != asset.source_version:
            return None
        expected_checksum = metadata.get("sha256")
        if not isinstance(expected_checksum, str) or len(expected_checksum) != 64:
            return None
        actual_checksum = sha256_file(target_path)
        if actual_checksum != expected_checksum:
            return None
        retrieved = metadata.get("retrieved_at")
        if not isinstance(retrieved, str):
            return None
        retrieved_at = datetime.fromisoformat(retrieved.replace("Z", "+00:00"))
        if retrieved_at.tzinfo is None or retrieved_at.utcoffset() is None:
            return None
        age_seconds = (datetime.now(UTC) - retrieved_at.astimezone(UTC)).total_seconds()
        # A significantly future-dated sidecar is not trusted as a fresh cache entry.
        if age_seconds < -300 or age_seconds > ttl_seconds:
            return None
        header = _validate_csv_header(target_path, asset)
        if metadata.get("header_validation") != "passed":
            return None
        if metadata.get("header") and list(metadata["header"]) != header:
            return None
        return metadata, max(0.0, age_seconds)
    except (OSError, json.JSONDecodeError, TypeError, ValueError, IngestionError):
        return None


def _retry_after_seconds(headers: Any) -> float | None:
    """Parse numeric or HTTP-date Retry-After; callers cap waits to avoid hanging workers."""
    raw = headers.get("retry-after") if headers is not None else None
    if not raw:
        return None
    try:
        return max(0.0, float(raw.strip()))
    except (ValueError, AttributeError):
        try:
            target = parsedate_to_datetime(str(raw))
            if target.tzinfo is None:
                target = target.replace(tzinfo=UTC)
            return max(0.0, (target.astimezone(UTC) - datetime.now(UTC)).total_seconds())
        except (TypeError, ValueError, OverflowError):
            return None


def _record_cache_state(
    asset: SourceAsset,
    *,
    cache_status: str,
    source_uri: str,
    source_version: str | None = None,
    retrieved_at: str | None = None,
    expires_at: str | None = None,
    checksum_sha256: str | None = None,
    last_attempt_at: str | None = None,
    last_success_at: str | None = None,
    error_category: str | None = None,
    error_count_increment: bool = False,
    details: dict[str, Any] | None = None,
    enabled: bool = True,
) -> None:
    """Best-effort cache telemetry update; download outcomes remain recorded in the run ledger.

    The app's source_cache_state table is created by Stage 16 migrations. Stand-alone ingestion
    tests using custom state paths do not mutate the default application database.
    """
    if not enabled:
        return
    try:
        from app.services.database import connect_sqlite

        db_path = resolve_database_path()
        if not db_path.exists():
            return
        with connect_sqlite(db_path) as db:
            table_exists = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='source_cache_state'"
            ).fetchone()
            if not table_exists:
                return
            db.execute(
                """INSERT INTO source_cache_state(
                    source_id,source_uri,source_version,cache_status,retrieved_at,expires_at,
                    checksum_sha256,last_attempt_at,last_success_at,last_error_category,error_count,details_json
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
                ON CONFLICT(source_id) DO UPDATE SET
                    source_uri=excluded.source_uri,
                    source_version=COALESCE(excluded.source_version,source_cache_state.source_version),
                    cache_status=excluded.cache_status,
                    retrieved_at=COALESCE(excluded.retrieved_at,source_cache_state.retrieved_at),
                    expires_at=COALESCE(excluded.expires_at,source_cache_state.expires_at),
                    checksum_sha256=COALESCE(excluded.checksum_sha256,source_cache_state.checksum_sha256),
                    last_attempt_at=COALESCE(excluded.last_attempt_at,source_cache_state.last_attempt_at),
                    last_success_at=COALESCE(excluded.last_success_at,source_cache_state.last_success_at),
                    last_error_category=excluded.last_error_category,
                    error_count=source_cache_state.error_count + excluded.error_count,
                    details_json=excluded.details_json""",
                (asset.source_id, source_uri, source_version, cache_status, retrieved_at, expires_at,
                 checksum_sha256, last_attempt_at, last_success_at, error_category,
                 1 if error_count_increment else 0,
                 json.dumps(details or {}, ensure_ascii=False, sort_keys=True)),
            )
    except (OSError, sqlite3.Error, ValueError):
        # Cache telemetry must not prevent a valid source download or a core student flow.
        return


def download_asset(
    asset_id: str,
    *,
    raw_root: str | Path = RAW_ROOT,
    state_path: str | Path = STATE_PATH,
    runs_root: str | Path = RUNS_ROOT,
    timeout_seconds: float = 12.0,
    retries: int = 2,
    cache_ttl_seconds: int | None = None,
    force_refresh: bool = False,
    minimum_interval_seconds: float = 1.0,
    client_factory=httpx.Client,
) -> dict[str, Any]:
    """Download one fixed official asset; never accepts arbitrary URLs from callers."""
    if asset_id not in ASSETS:
        raise IngestionError(f"Unknown downloadable asset {asset_id!r}. Allowed assets: {', '.join(sorted(ASSETS))}.")
    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0 or retries > 10:
        raise IngestionValidationError("retries must be an integer between 0 and 10.")
    if not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0 or timeout_seconds > 300:
        raise IngestionValidationError("timeout_seconds must be a finite number greater than 0 and at most 300.")
    if cache_ttl_seconds is None:
        cache_ttl_seconds = external_cache_ttl_seconds()
    if not isinstance(cache_ttl_seconds, int) or isinstance(cache_ttl_seconds, bool) or not 0 <= cache_ttl_seconds <= 31_536_000:
        raise IngestionValidationError("cache_ttl_seconds must be an integer between 0 and 31536000.")
    if not isinstance(force_refresh, bool):
        raise IngestionValidationError("force_refresh must be a boolean.")
    if not isinstance(minimum_interval_seconds, (int, float)) or isinstance(minimum_interval_seconds, bool) or not math.isfinite(minimum_interval_seconds) or not 0 <= minimum_interval_seconds <= 60:
        raise IngestionValidationError("minimum_interval_seconds must be between 0 and 60 seconds.")
    asset = ASSETS[asset_id]
    _validate_allowed_url(asset)
    target_dir = Path(raw_root) / asset.source_id / asset.source_version.replace(" ", "_")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / asset.filename
    started_at = iso_utc()
    last_error: str | None = None

    cached = _verified_cache_metadata(target_path, asset, cache_ttl_seconds) if not force_refresh else None
    if cached is not None:
        metadata, age_seconds = cached
        completed_at = iso_utc()
        event = {
            "source_id": asset.source_id,
            "asset_id": asset.asset_id,
            "status": "cache_hit",
            "started_at": started_at,
            "finished_at": completed_at,
            "attempt_number": 0,
            "source_url": asset.url,
            "source_version": asset.source_version,
            "byte_size": target_path.stat().st_size,
            "sha256": metadata["sha256"],
            "cache_age_seconds": round(age_seconds, 3),
            "cache_ttl_seconds": cache_ttl_seconds,
        }
        record_run_event(event, state_path=state_path)
        Path(runs_root).mkdir(parents=True, exist_ok=True)
        write_json_atomic(Path(runs_root) / f"{asset.asset_id}_latest.json", event)
        _record_cache_state(
            asset, cache_status="fresh", source_uri=asset.url, source_version=asset.source_version,
            retrieved_at=metadata.get("retrieved_at"),
            expires_at=(datetime.fromisoformat(str(metadata["retrieved_at"]).replace("Z", "+00:00")) + timedelta(seconds=cache_ttl_seconds)).isoformat(),
            checksum_sha256=metadata["sha256"], last_attempt_at=completed_at,
            last_success_at=metadata.get("retrieved_at"), details={"asset_id": asset.asset_id, "cache_hit": True},
            enabled=Path(state_path).resolve() == Path(STATE_PATH).resolve(),
        )
        return {**metadata, "cache_status": "fresh_cache_hit", "cache_age_seconds": round(age_seconds, 3)}

    # Enforce a bounded inter-request delay per source using the existing durable run ledger.
    if minimum_interval_seconds > 0:
        try:
            state = json.loads(Path(state_path).read_text(encoding="utf-8")) if Path(state_path).exists() else {}
            last_attempt = state.get("sources", {}).get(asset.source_id, {}).get("last_attempt", {})
            finished_text = last_attempt.get("finished_at") if isinstance(last_attempt, dict) else None
            if finished_text:
                previous = datetime.fromisoformat(str(finished_text).replace("Z", "+00:00"))
                elapsed = (datetime.now(UTC) - previous.astimezone(UTC)).total_seconds()
                remaining = minimum_interval_seconds - elapsed
                if 0 < remaining <= 60:
                    time.sleep(remaining)
        except (OSError, ValueError, TypeError, AttributeError, json.JSONDecodeError):
            # Invalid prior timing data does not block a refresh; the main run ledger still records it.
            pass

    for attempt_number in range(1, retries + 2):
        temporary_path = target_path.with_suffix(target_path.suffix + ".part")
        try:
            total_bytes = 0
            digest = hashlib.sha256()
            with client_factory(
                timeout=httpx.Timeout(timeout_seconds, connect=min(5.0, timeout_seconds)),
                follow_redirects=False,
                headers={"User-Agent": "SkillScope-DataIngestion/0.1 (+https://www.onetcenter.org/license_db.html)"},
            ) as client:
                current_url = asset.url
                for redirect_count in range(6):
                    _validate_request_url(current_url, asset)
                    with client.stream("GET", current_url) as response:
                        if response.is_redirect:
                            if redirect_count >= 5:
                                raise IngestionValidationError(
                                    f"{asset.asset_id} exceeded the maximum of 5 redirects."
                                )
                            location = response.headers.get("location")
                            if not location:
                                raise IngestionValidationError(
                                    f"{asset.asset_id} returned a redirect without a Location header."
                                )
                            current_url = urljoin(str(response.url), location)
                            _validate_request_url(current_url, asset)
                            continue
                        if response.status_code == 429 or response.status_code >= 500:
                            raise httpx.HTTPStatusError(
                                f"Retryable HTTP status {response.status_code}", request=response.request, response=response
                            )
                        response.raise_for_status()
                        content_type = response.headers.get("content-type", "").casefold()
                        if "text/html" in content_type:
                            raise IngestionValidationError(f"{asset.asset_id} returned text/html instead of CSV data.")
                        content_length = response.headers.get("content-length")
                        if content_length and content_length.isdigit() and int(content_length) > asset.max_bytes:
                            raise IngestionValidationError(
                                f"{asset.asset_id} exceeds the maximum permitted download size of {asset.max_bytes} bytes."
                            )
                        with temporary_path.open("wb") as output:
                            for chunk in response.iter_bytes(chunk_size=64 * 1024):
                                if not chunk:
                                    continue
                                total_bytes += len(chunk)
                                if total_bytes > asset.max_bytes:
                                    raise IngestionValidationError(
                                        f"{asset.asset_id} exceeded the maximum permitted download size."
                                    )
                                output.write(chunk)
                                digest.update(chunk)
                        break
                else:  # pragma: no cover - range and redirect guard make this defensive only
                    raise IngestionValidationError(f"{asset.asset_id} exhausted redirect handling without a data response.")
            if total_bytes == 0:
                raise IngestionValidationError(f"{asset.asset_id} downloaded an empty file.")
            header = _validate_csv_header(temporary_path, asset)
            checksum = digest.hexdigest()
            temporary_path.replace(target_path)
            completed_at = iso_utc()
            metadata = {
                "metadata_schema_version": 1,
                "asset_id": asset.asset_id,
                "source_id": asset.source_id,
                "source_url": asset.url,
                "official_release_url": ONET_RELEASE_URL,
                "filename": asset.filename,
                "retrieved_at": completed_at,
                "source_version": asset.source_version,
                "release_date": asset.release_date,
                "license_reference": asset.license_url,
                "license_summary": asset.license_summary,
                "content_type": content_type,
                "byte_size": total_bytes,
                "sha256": checksum,
                "header": header,
                "header_validation": "passed",
                "source_data_is_live": False,
                "note": "Pinned source file downloaded as a static snapshot; not a live API feed.",
                "cache_ttl_seconds": cache_ttl_seconds,
            }
            write_json_atomic(str(target_path) + ".metadata.json", metadata)
            event = {
                "source_id": asset.source_id,
                "asset_id": asset.asset_id,
                "status": "downloaded",
                "started_at": started_at,
                "finished_at": completed_at,
                "attempt_number": attempt_number,
                "source_url": asset.url,
                "file_path": str(target_path.relative_to(Path(raw_root).parent)) if Path(raw_root).name == "raw" else str(target_path),
                "byte_size": total_bytes,
                "sha256": checksum,
                "source_version": asset.source_version,
            }
            record_run_event(event, state_path=state_path)
            Path(runs_root).mkdir(parents=True, exist_ok=True)
            write_json_atomic(Path(runs_root) / f"{asset.asset_id}_latest.json", event)
            expires_at = (datetime.fromisoformat(completed_at.replace("Z", "+00:00")) + timedelta(seconds=cache_ttl_seconds)).isoformat()
            _record_cache_state(
                asset, cache_status="fresh", source_uri=asset.url, source_version=asset.source_version,
                retrieved_at=completed_at, expires_at=expires_at, checksum_sha256=checksum,
                last_attempt_at=completed_at, last_success_at=completed_at,
                details={"asset_id": asset.asset_id, "byte_size": total_bytes, "header_validation": "passed"},
                enabled=Path(state_path).resolve() == Path(STATE_PATH).resolve(),
            )
            return metadata
        except (httpx.HTTPError, OSError, IngestionError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            temporary_path.unlink(missing_ok=True)
            if attempt_number <= retries and isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)):
                retry_after = _retry_after_seconds(exc.response.headers) if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None else None
                # Never spin against a source that asks for a long delay. Wait for at most three
                # seconds here; if the server asks for longer, fail safely and preserve old data.
                if retry_after is not None and retry_after > 3:
                    break
                time.sleep(retry_after if retry_after is not None else min(0.25 * attempt_number, 1.0))
                continue
            break

    finished_at = iso_utc()
    event = {
        "source_id": asset.source_id,
        "asset_id": asset.asset_id,
        "status": "download_failed",
        "started_at": started_at,
        "finished_at": finished_at,
        "attempt_number": attempt_number,
        "source_url": asset.url,
        "error": last_error or "Unknown download error.",
        "next_action": "Retry from a network-enabled development environment; keep the source not_integrated until import succeeds.",
    }
    record_run_event(event, state_path=state_path)
    Path(runs_root).mkdir(parents=True, exist_ok=True)
    write_json_atomic(Path(runs_root) / f"{asset.asset_id}_latest.json", event)
    old_metadata = None
    try:
        old_metadata = json.loads(Path(str(target_path) + ".metadata.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass
    _record_cache_state(
        asset, cache_status="refresh_failed" if target_path.exists() else "unknown",
        source_uri=asset.url, source_version=asset.source_version,
        retrieved_at=old_metadata.get("retrieved_at") if isinstance(old_metadata, dict) else None,
        expires_at=None, checksum_sha256=old_metadata.get("sha256") if isinstance(old_metadata, dict) else None,
        last_attempt_at=finished_at, error_category="download_failed", error_count_increment=True,
        details={"asset_id": asset.asset_id, "stale_file_retained": target_path.exists()},
        enabled=Path(state_path).resolve() == Path(STATE_PATH).resolve(),
    )
    raise IngestionError(
        f"Could not download {asset.asset_id} after {attempt_number} attempt(s): {event['error']}"
    )
