"""Command-line entry points for SkillScope's reproducible ingestion pipeline.

Run from the project root with:
  PYTHONPATH=backend python -m app.services.ingestion.cli --help
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from app.services.ingestion.common import (
    CURATED_SNAPSHOT_PATH,
    DATA_ROOT,
    IngestionError,
    MANIFEST_PATH,
    RAW_ROOT,
    STATE_PATH,
    load_json_object,
)
from app.services.ingestion.downloads import ASSETS, download_asset
from app.services.ingestion.pipeline import (
    import_curated_snapshot,
    import_esco_package,
    import_onet_files,
)
from app.services.provenance import DEFAULT_DB_PATH, ProvenanceRepository


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="skillscope-ingest",
        description="Download/validate permitted career-data artifacts and import them with full provenance.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status", help="Show latest source operations and canonical registry counts.")

    download = sub.add_parser("download-onet", help="Download one allow-listed O*NET 31.0 CSV asset.")
    download.add_argument("asset_id", choices=sorted(ASSETS))
    download.add_argument("--timeout", type=float, default=12.0)
    download.add_argument("--retries", type=int, default=2)

    curated = sub.add_parser("import-curated", help="Import the bundled, source-backed curated occupation extract.")
    curated.add_argument("--snapshot", type=Path, default=CURATED_SNAPSHOT_PATH)
    curated.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    curated.add_argument("--state-file", type=Path, default=STATE_PATH)
    curated.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    curated.add_argument("--batch-size", type=int, default=250)

    onet = sub.add_parser("import-onet", help="Import matching local O*NET 31.0 Occupation Data + Essential Skills CSVs.")
    onet.add_argument("--occupations", required=True, type=Path, help="Official occupation_data.csv file.")
    onet.add_argument("--essential-skills", required=True, type=Path, help="Official essential_skills.csv file.")
    onet.add_argument("--source-version", help="Required for manually downloaded files without downloader sidecars.")
    onet.add_argument("--retrieved-at", help="Timezone-aware ISO-8601 time, e.g. 2026-10-17T12:00:00Z.")
    onet.add_argument("--release-date", help="Optional explicit source release date.")
    onet.add_argument("--state-file", type=Path, default=STATE_PATH)
    onet.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    onet.add_argument("--batch-size", type=int, default=500)
    onet.add_argument("--manifest", type=Path, default=MANIFEST_PATH)

    esco = sub.add_parser("import-esco", help="Import an official ESCO classification CSV ZIP already downloaded through the official portal.")
    esco.add_argument("--package", required=True, type=Path, help="Official ESCO CSV ZIP package.")
    esco.add_argument("--source-version", required=True, help="Exact selected export version, e.g. 'ESCO v1.2.1'.")
    esco.add_argument("--release-date", help="Release date from official package/page, if verified.")
    esco.add_argument("--retrieved-at", required=True, help="Timezone-aware ISO-8601 package retrieval time.")
    esco.add_argument("--language", default="en", help="Language selected for the package; default 'en'.")
    esco.add_argument("--without-skills", action="store_true", help="Import occupation concepts only; relations must also be disabled.")
    esco.add_argument("--without-relations", action="store_true", help="Import concepts without occupation-skill relationships.")
    esco.add_argument("--state-file", type=Path, default=STATE_PATH)
    esco.add_argument("--database", type=Path, default=DEFAULT_DB_PATH)
    esco.add_argument("--batch-size", type=int, default=500)
    esco.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    return parser


def _read_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schema_version": 1, "sources": {}, "runs": []}
    return load_json_object(path)


def _status(database: Path, state_file: Path, manifest_file: Path) -> dict[str, Any]:
    state = _read_state(state_file)
    try:
        manifest = yaml.safe_load(manifest_file.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise IngestionError(f"Could not read source manifest {manifest_file}: {exc}") from exc
    if not isinstance(manifest, dict) or not isinstance(manifest.get("sources"), list):
        raise IngestionError("Source manifest must contain a sources list.")
    repo = ProvenanceRepository(database)
    latest: dict[str, Any] = {}
    for source_id, value in state.get("sources", {}).items():
        if not isinstance(value, dict):
            continue
        attempt = value.get("last_attempt", {})
        success = value.get("last_successful_operation", {})
        latest[source_id] = {
            "last_attempt_status": attempt.get("status") if isinstance(attempt, dict) else None,
            "last_attempt_at": attempt.get("finished_at") if isinstance(attempt, dict) else None,
            "last_success_status": success.get("status") if isinstance(success, dict) else None,
            "last_success_at": success.get("finished_at") if isinstance(success, dict) else None,
            "last_attempt_error": attempt.get("error") if isinstance(attempt, dict) else None,
            "source_version": (attempt.get("source_version") or success.get("source_version")) if isinstance(attempt, dict) and isinstance(success, dict) else None,
        }
    return {
        "project": manifest.get("project", "SkillScope AI"),
        "manifest_status": manifest.get("manifest_status"),
        "database_counts": repo.count(),
        "sources": {
            item["id"]: {
                "integration_status": item.get("integration_status", "unknown"),
                "runtime_access_status": item.get("runtime_access_status", "unknown"),
                "latest_run": latest.get(item["id"], {}),
            }
            for item in manifest["sources"] if isinstance(item, dict) and item.get("id")
        },
        "recent_runs": state.get("runs", [])[-10:],
        "source_data_is_live": False,
        "note": "A successful import creates a static snapshot. It never implies a live feed; status is per source/version.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = _status(DEFAULT_DB_PATH, STATE_PATH, MANIFEST_PATH)
        elif args.command == "download-onet":
            result = download_asset(args.asset_id, timeout_seconds=args.timeout, retries=args.retries)
        elif args.command == "import-curated":
            result = import_curated_snapshot(
                args.snapshot,
                repository=ProvenanceRepository(args.database),
                state_path=args.state_file,
                manifest_path=args.manifest,
                batch_size=args.batch_size,
            ).to_dict()
        elif args.command == "import-onet":
            result = import_onet_files(
                args.occupations,
                args.essential_skills,
                repository=ProvenanceRepository(args.database),
                state_path=args.state_file,
                source_version=args.source_version,
                retrieved_at=args.retrieved_at,
                release_date=args.release_date,
                batch_size=args.batch_size,
                manifest_path=args.manifest,
            ).to_dict()
        elif args.command == "import-esco":
            result = import_esco_package(
                args.package,
                source_version=args.source_version,
                release_date=args.release_date,
                retrieved_at=args.retrieved_at,
                language=args.language,
                repository=ProvenanceRepository(args.database),
                state_path=args.state_file,
                batch_size=args.batch_size,
                include_skills=not args.without_skills,
                include_relations=not args.without_relations,
                manifest_path=args.manifest,
            ).to_dict()
        else:  # pragma: no cover - argparse prevents unknown commands
            parser.error(f"Unknown command: {args.command}")
            return 2
    except IngestionError as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(json.dumps({"status": "failed", "error": f"{type(exc).__name__}: {exc}"}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
