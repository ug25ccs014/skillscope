"""Shared ingestion utilities. Fail closed on malformed or untraceable data."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import zipfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

PROJECT_ROOT = Path(__file__).resolve().parents[4]
DATA_ROOT = PROJECT_ROOT / "data"
RAW_ROOT = DATA_ROOT / "raw"
RUNS_ROOT = DATA_ROOT / "ingestion_runs"
STATE_PATH = DATA_ROOT / "ingestion_state.json"
MANIFEST_PATH = DATA_ROOT / "sources_manifest.yaml"
CURATED_SNAPSHOT_PATH = DATA_ROOT / "curated" / "occupations_snapshot.json"


class IngestionError(RuntimeError):
    """Expected ingestion failure that can be reported without a traceback."""


class IngestionValidationError(IngestionError):
    """Input data failed schema, provenance, or consistency validation."""


@dataclass(frozen=True)
class CsvTable:
    rows: list[dict[str, str]]
    columns: list[str]
    file_name: str
    sha256: str
    byte_size: int
    selected_member: str | None = None


def utc_now() -> datetime:
    return datetime.now(UTC)


def iso_utc(value: datetime | None = None) -> str:
    return (value or utc_now()).astimezone(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def parse_datetime(value: str | datetime) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        normalized = value.strip().replace("Z", "+00:00")
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise IngestionValidationError(f"Invalid ISO-8601 timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        raise IngestionValidationError("Timestamps must include a timezone, for example 2026-10-17T12:00:00Z.")
    return parsed.astimezone(UTC)


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_header(value: str) -> str:
    """Normalize headers for matching only; raw column names remain preserved."""
    text = value.lstrip("\ufeff").strip().casefold()
    return re.sub(r"[^a-z0-9]+", "_", text).strip("_")


def normalize_slug(value: str) -> str:
    text = value.casefold().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "unnamed"


def _decode_bytes(payload: bytes, file_name: str) -> str:
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return payload.decode(encoding, errors="strict")
        except UnicodeDecodeError:
            continue
    raise IngestionValidationError(f"Could not decode {file_name} using supported CSV encodings.")


def _parse_delimited_text(text: str, file_name: str) -> tuple[list[str], list[dict[str, str]]]:
    if not text.strip():
        raise IngestionValidationError(f"The source file {file_name!r} is empty.")
    sample = text[:16_384]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text, newline=""), dialect=dialect)
    if not reader.fieldnames:
        raise IngestionValidationError(f"The source file {file_name!r} has no header row.")
    columns = [str(item).lstrip("\ufeff").strip() for item in reader.fieldnames]
    if len({normalize_header(item) for item in columns}) != len(columns):
        raise IngestionValidationError(f"The source file {file_name!r} has duplicate/ambiguous column names.")
    rows: list[dict[str, str]] = []
    for line_number, row in enumerate(reader, start=2):
        normalized_row = {
            str(key).lstrip("\ufeff").strip(): (value or "").strip()
            for key, value in row.items()
            if key is not None
        }
        if not any(value for value in normalized_row.values()):
            continue
        if None in row:
            raise IngestionValidationError(
                f"Malformed CSV at {file_name!r} line {line_number}: too many fields for the header."
            )
        if any(value is None for value in row.values()):
            raise IngestionValidationError(
                f"Malformed CSV at {file_name!r} line {line_number}: too few fields for the header."
            )
        rows.append(normalized_row)
    return columns, rows


def read_csv_table(
    path: str | Path,
    *,
    member_name: str | None = None,
    member_keyword: str | None = None,
    max_uncompressed_bytes: int = 250 * 1024 * 1024,
) -> CsvTable:
    """Read one CSV/TSV (or one explicit member from a ZIP) without extraction."""
    source_path = Path(path)
    if not source_path.is_file():
        raise IngestionError(f"Source file does not exist: {source_path}")
    if source_path.stat().st_size == 0:
        raise IngestionValidationError(f"Source file is empty: {source_path}")
    digest = sha256_file(source_path)
    selected_member = None
    payload: bytes
    if source_path.suffix.casefold() == ".zip":
        try:
            with zipfile.ZipFile(source_path) as archive:
                names = [item for item in archive.infolist() if not item.is_dir()]
                candidates = [item for item in names if item.filename.casefold().endswith((".csv", ".txt"))]
                if member_name:
                    matches = [item for item in candidates if item.filename == member_name]
                elif member_keyword:
                    matches = [item for item in candidates if member_keyword.casefold() in Path(item.filename).name.casefold()]
                else:
                    raise IngestionValidationError("A ZIP source requires an explicit member_name or member_keyword.")
                if len(matches) != 1:
                    found = ", ".join(item.filename for item in matches[:8]) or "none"
                    raise IngestionValidationError(
                        f"Could not uniquely select a CSV member from {source_path.name!r}; matches: {found}."
                    )
                chosen = matches[0]
                if chosen.file_size > max_uncompressed_bytes:
                    raise IngestionValidationError(
                        f"ZIP member {chosen.filename!r} exceeds the configured uncompressed-size limit."
                    )
                if chosen.file_size > 0 and chosen.compress_size == 0:
                    raise IngestionValidationError(f"ZIP member {chosen.filename!r} has an invalid zero compressed size.")
                if chosen.compress_size and chosen.file_size / chosen.compress_size > 1000:
                    raise IngestionValidationError(f"ZIP member {chosen.filename!r} has a suspicious compression ratio.")
                payload = archive.read(chosen)
                selected_member = chosen.filename
        except IngestionValidationError:
            raise
        except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, NotImplementedError, OSError) as exc:
            raise IngestionValidationError(f"Invalid or unreadable ZIP archive: {source_path}") from exc
    else:
        if source_path.stat().st_size > max_uncompressed_bytes:
            raise IngestionValidationError(f"Source file exceeds the configured size limit: {source_path}")
        payload = source_path.read_bytes()

    text = _decode_bytes(payload, selected_member or source_path.name)
    if text.lstrip().startswith(("<!doctype html", "<html", "{\"error\"")):
        raise IngestionValidationError(f"Expected a CSV data file but received a likely HTML/error document: {source_path}")
    columns, rows = _parse_delimited_text(text, selected_member or source_path.name)
    if not rows:
        raise IngestionValidationError(f"No data records were found in {selected_member or source_path.name!r}.")
    return CsvTable(
        rows=rows,
        columns=columns,
        file_name=source_path.name,
        sha256=digest,
        byte_size=source_path.stat().st_size,
        selected_member=selected_member,
    )


def require_columns(columns: Iterable[str], required_aliases: dict[str, tuple[str, ...]], label: str) -> dict[str, str]:
    normalized_to_original = {normalize_header(column): column for column in columns}
    resolved: dict[str, str] = {}
    missing: list[str] = []
    for canonical, aliases in required_aliases.items():
        match = next((normalized_to_original[normalize_header(alias)] for alias in aliases
                      if normalize_header(alias) in normalized_to_original), None)
        if match is None:
            missing.append(f"{canonical} (accepted: {', '.join(aliases)})")
        else:
            resolved[canonical] = match
    if missing:
        raise IngestionValidationError(f"{label} is missing required columns: {'; '.join(missing)}. Found: {list(columns)}")
    return resolved


def parse_optional_float(value: str | None, *, field_name: str, row_number: int) -> float | None:
    if value is None or not value.strip():
        return None
    try:
        result = float(value.strip())
    except (TypeError, ValueError) as exc:
        raise IngestionValidationError(f"Row {row_number}: {field_name} must be numeric or blank, got {value!r}.") from exc
    if not math.isfinite(result):
        raise IngestionValidationError(f"Row {row_number}: {field_name} must be a finite number.")
    return result


def deduplicate_rows(
    rows: Iterable[dict[str, str]],
    *,
    key_fn,
    label: str,
) -> tuple[list[dict[str, str]], int]:
    """Drop byte-for-byte-equivalent logical duplicates; fail on conflicting duplicate IDs."""
    unique: dict[str, dict[str, str]] = {}
    duplicate_count = 0
    for row_number, row in enumerate(rows, start=2):
        key = key_fn(row)
        if not key:
            raise IngestionValidationError(f"{label} row {row_number} has a blank stable ID.")
        prior = unique.get(key)
        if prior is None:
            unique[key] = row
            continue
        if prior == row:
            duplicate_count += 1
            continue
        raise IngestionValidationError(
            f"{label} has conflicting rows for stable ID {key!r}; import was stopped before writing data."
        )
    return list(unique.values()), duplicate_count


def load_json_object(path: str | Path) -> dict[str, Any]:
    source = Path(path)
    try:
        content = json.loads(source.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise IngestionError(f"JSON file does not exist: {source}") from exc
    except json.JSONDecodeError as exc:
        raise IngestionValidationError(f"Invalid JSON in {source}: {exc}") from exc
    if not isinstance(content, dict):
        raise IngestionValidationError(f"Expected a JSON object in {source}.")
    return content


def write_text_atomic(path: str | Path, content: str) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_text(content, encoding="utf-8", newline="")
    temporary.replace(destination)


def write_json_atomic(path: str | Path, content: dict[str, Any]) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    temporary.write_text(json.dumps(content, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(destination)


def record_run_event(event: dict[str, Any], *, state_path: str | Path = STATE_PATH) -> dict[str, Any]:
    """Persist latest per-source state without silently erasing a damaged audit ledger."""
    state_file = Path(state_path)
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text(encoding="utf-8"))
        except OSError as exc:
            raise IngestionError(f"Could not read ingestion state file {state_file}: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise IngestionValidationError(
                f"Ingestion state file {state_file} is invalid JSON; existing run history was not overwritten."
            ) from exc
        if not isinstance(state, dict):
            raise IngestionValidationError(
                f"Ingestion state file {state_file} must contain a JSON object; existing history was not overwritten."
            )
        if not isinstance(state.get("sources", {}), dict) or not isinstance(state.get("runs", []), list):
            raise IngestionValidationError(
                f"Ingestion state file {state_file} has invalid sources/runs fields; existing history was not overwritten."
            )
    else:
        state = {"schema_version": 1, "sources": {}, "runs": []}
    state.setdefault("schema_version", 1)
    state.setdefault("sources", {})
    state.setdefault("runs", [])
    source_id = event.get("source_id", "unknown")
    previous = state["sources"].get(source_id, {})
    updated = {**previous, "last_attempt": event}
    if event.get("status") in {"downloaded", "imported", "curated_extract_imported"}:
        updated["last_successful_operation"] = event
    state["sources"][source_id] = updated
    state["runs"].append(event)
    state["runs"] = state["runs"][-100:]
    state["last_updated_at"] = event.get("finished_at", iso_utc())
    write_json_atomic(state_file, state)
    return state


def safe_host(url: str) -> str:
    return (urlparse(url).hostname or "").casefold().rstrip(".")
