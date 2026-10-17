"""Allow-listed official-source downloader with retries, hashes, and run state."""

from __future__ import annotations

import hashlib
import json
import math
import os
import time
from dataclasses import dataclass
from datetime import UTC, datetime
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


def download_asset(
    asset_id: str,
    *,
    raw_root: str | Path = RAW_ROOT,
    state_path: str | Path = STATE_PATH,
    runs_root: str | Path = RUNS_ROOT,
    timeout_seconds: float = 12.0,
    retries: int = 2,
    client_factory=httpx.Client,
) -> dict[str, Any]:
    """Download one fixed official asset; never accepts arbitrary URLs from callers."""
    if asset_id not in ASSETS:
        raise IngestionError(f"Unknown downloadable asset {asset_id!r}. Allowed assets: {', '.join(sorted(ASSETS))}.")
    if not isinstance(retries, int) or isinstance(retries, bool) or retries < 0 or retries > 10:
        raise IngestionValidationError("retries must be an integer between 0 and 10.")
    if not isinstance(timeout_seconds, (int, float)) or not math.isfinite(timeout_seconds) or timeout_seconds <= 0 or timeout_seconds > 300:
        raise IngestionValidationError("timeout_seconds must be a finite number greater than 0 and at most 300.")
    asset = ASSETS[asset_id]
    _validate_allowed_url(asset)
    target_dir = Path(raw_root) / asset.source_id / asset.source_version.replace(" ", "_")
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / asset.filename
    started_at = iso_utc()
    last_error: str | None = None

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
            return metadata
        except (httpx.HTTPError, OSError, IngestionError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            temporary_path.unlink(missing_ok=True)
            if attempt_number <= retries and isinstance(exc, (httpx.TimeoutException, httpx.NetworkError, httpx.HTTPStatusError)):
                time.sleep(min(0.25 * attempt_number, 1.0))
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
    raise IngestionError(
        f"Could not download {asset.asset_id} after {attempt_number} attempt(s): {event['error']}"
    )
