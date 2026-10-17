"""Reproducible SQLite bootstrap, additive migrations, demo fixtures and diagnostics.

Existing repository classes continue to own their domain tables; this module provides a single
startup path that initializes them, tracks schema migrations, and adds Stage 16 cross-cutting
persistence metadata. The demo profile is synthetic and must never be mistaken for a real user.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.config import resolve_database_path, seed_demo_enabled

DEMO_FIXTURE_ID = "skillscope-synthetic-demo-v1"  # Legacy adult fixture ID retained for compatibility.
DEMO_PROFILE_ID = UUID("00000000-0000-4000-8000-000000000016")
DEMO_MODE_FIXTURES = (
    {
        "fixture_id": "skillscope-synthetic-demo-age-10-14-v1",
        "profile_id": UUID("00000000-0000-4000-8000-000000000010"),
        "age_band": "10_14",
        "consent_basis": "guardian_confirmed",
        "goal": "SYNTHETIC DEMO: explore puzzles, making, and useful ideas through small activities",
        "description": "Synthetic ages 10–14 discover-and-shape profile; no real child data.",
    },
    {
        "fixture_id": "skillscope-synthetic-demo-age-15-17-v1",
        "profile_id": UUID("00000000-0000-4000-8000-000000000015"),
        "age_band": "15_17",
        "consent_basis": "guardian_confirmed",
        "goal": "SYNTHETIC DEMO: explore software engineering while testing design and communication through small projects",
        "description": "Synthetic ages 15–17 explore-and-validate profile with varied prior exposure; no real teen data.",
    },
)
DATABASE_SCHEMA_VERSION = 2


MIGRATIONS: tuple[tuple[int, str, str], ...] = (
    (1, "profile_preferences_and_source_cache", """
        CREATE TABLE IF NOT EXISTS student_preferences (
            profile_id TEXT PRIMARY KEY,
            journey_preference TEXT NOT NULL DEFAULT 'balanced'
                CHECK(journey_preference IN ('balanced','explore','develop','validate','alternative')),
            preferred_domains_json TEXT NOT NULL DEFAULT '[]',
            accessibility_formats_json TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL,
            FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS source_cache_state (
            source_id TEXT PRIMARY KEY,
            source_uri TEXT NOT NULL,
            source_version TEXT,
            cache_status TEXT NOT NULL CHECK(cache_status IN ('fresh','stale','refresh_failed','link_only','unknown')),
            retrieved_at TEXT,
            expires_at TEXT,
            checksum_sha256 TEXT,
            last_attempt_at TEXT,
            last_success_at TEXT,
            last_error_category TEXT,
            error_count INTEGER NOT NULL DEFAULT 0 CHECK(error_count >= 0),
            details_json TEXT NOT NULL DEFAULT '{}'
        );
    """),
    (2, "recommendation_snapshots_and_synthetic_fixtures", """
        CREATE TABLE IF NOT EXISTS recommendation_snapshots (
            snapshot_id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL,
            algorithm_version TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            evidence_count INTEGER NOT NULL CHECK(evidence_count >= 0),
            catalog_status TEXT NOT NULL,
            source_keys_json TEXT NOT NULL DEFAULT '[]',
            snapshot_json TEXT NOT NULL,
            FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_recommendation_snapshots_profile_generated
            ON recommendation_snapshots(profile_id, generated_at DESC, snapshot_id);
        CREATE TABLE IF NOT EXISTS demo_fixture_registry (
            fixture_id TEXT PRIMARY KEY,
            profile_id TEXT NOT NULL UNIQUE,
            fixture_version TEXT NOT NULL,
            fixture_kind TEXT NOT NULL,
            data_classification TEXT NOT NULL CHECK(data_classification = 'synthetic_demo'),
            description TEXT NOT NULL,
            seeded_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE
        );
    """),
)


def database_path(db_path: str | Path | None = None) -> Path:
    return Path(db_path).resolve() if db_path is not None else resolve_database_path()


def connect_sqlite(db_path: str | Path, *, timeout_seconds: float = 10.0) -> sqlite3.Connection:
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(str(path), timeout=timeout_seconds)
    db.execute(f"PRAGMA busy_timeout = {int(timeout_seconds * 1000)}")
    db.execute("PRAGMA foreign_keys = ON")
    db.row_factory = sqlite3.Row
    return db


def _migration_checksum(sql: str) -> str:
    return hashlib.sha256(" ".join(sql.split()).encode("utf-8")).hexdigest()


def migrate_database(db_path: str | Path | None = None) -> dict[str, Any]:
    """Apply additive migrations after idempotent domain-repository schema initialization."""
    path = database_path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect_sqlite(path) as db:
        # WAL is durable across restarts and improves concurrent read/write behavior for the MVP.
        db.execute("PRAGMA journal_mode = WAL")
        db.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            checksum_sha256 TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )""")

    # Each legacy repository has idempotent CREATE TABLE IF NOT EXISTS setup. Running these in one
    # place guarantees a fresh database and a Stage 1-15 database both converge on the same schema.
    from app.services.evidence_ledger import EvidenceLedgerRepository
    from app.services.provenance import ProvenanceRepository
    from app.services.challenges import ChallengeRepository
    from app.services.baseline_assessment import BaselineAssessmentRepository
    from app.services.knowledge_graph import KnowledgeGraphRepository
    from app.services.pathway_plans import PathwayPlanRepository
    from app.services.recommendations import RecommendationRepository

    EvidenceLedgerRepository(path)
    ProvenanceRepository(path)
    ChallengeRepository(path)
    BaselineAssessmentRepository(path)
    KnowledgeGraphRepository(path)
    PathwayPlanRepository(path)
    RecommendationRepository(path)

    with connect_sqlite(path) as db:
        applied_rows = db.execute("SELECT version, checksum_sha256 FROM schema_migrations").fetchall()
        applied = {int(row["version"]): str(row["checksum_sha256"]) for row in applied_rows}
        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        for version, name, sql in MIGRATIONS:
            checksum = _migration_checksum(sql)
            if version in applied:
                if applied[version] != checksum:
                    raise RuntimeError(f"Database migration {version} checksum differs from the recorded migration.")
                continue
            db.executescript(sql)
            db.execute(
                "INSERT INTO schema_migrations(version,name,checksum_sha256,applied_at) VALUES(?,?,?,?)",
                (version, name, checksum, now),
            )
        expected = {"student_profiles", "student_evidence_items", "source_records", "career_facts",
                    "challenge_submissions", "baseline_assessments", "baseline_responses", "pathway_plans",
                    "student_preferences", "recommendation_snapshots", "demo_fixture_registry"}
        actual = {str(row["name"]) for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = sorted(expected - actual)
        if missing:
            raise RuntimeError(f"Database bootstrap is incomplete; required tables are missing: {missing}.")
        versions = [int(row["version"]) for row in db.execute("SELECT version FROM schema_migrations ORDER BY version")]
    return {"database_configured": True, "schema_version": max(versions, default=0), "applied_migrations": versions}


def _seed_demo_profile(db_path: Path) -> str:
    from app.schemas.student_evidence import (
        AgeBand, ConsentBasis, EvidenceCreate, EvidenceSourceKind, EvidenceType,
        SignalDimension, StudentProfileCreate, UncertaintyLevel, UserInterpretation,
    )
    from app.services.evidence_ledger import EvidenceLedgerRepository

    evidence = EvidenceLedgerRepository(db_path)
    with connect_sqlite(db_path) as db:
        marker = db.execute("SELECT profile_id FROM demo_fixture_registry WHERE fixture_id=?", (DEMO_FIXTURE_ID,)).fetchone()
        if marker:
            return str(marker["profile_id"])
        existing = db.execute("SELECT profile_id FROM student_profiles WHERE profile_id=?", (str(DEMO_PROFILE_ID),)).fetchone()
        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        if not existing:
            profile_request = StudentProfileCreate(
                age_band=AgeBand.AGE_18_PLUS,
                consent_basis=ConsentBasis.STUDENT_CONFIRMED,
                consent_confirmed=True,
                current_goal="SYNTHETIC DEMO: explore how technology and data can solve practical problems",
                self_reported_context="Synthetic demonstration profile. Contains no real student's data.",
            )
            # Use a deterministic profile ID so interrupted or repeated seeding cannot multiply demo profiles.
            db.execute(
                """INSERT INTO student_profiles(profile_id,age_band,consent_basis,consent_confirmed_at,
                   consent_notice_version,current_goal,self_reported_context,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?)""",
                (str(DEMO_PROFILE_ID), profile_request.age_band.value, profile_request.consent_basis.value,
                 now, "student-evidence-v1.0", profile_request.current_goal, profile_request.self_reported_context, now, now),
            )
            profile_row = db.execute("SELECT * FROM student_profiles WHERE profile_id=?", (str(DEMO_PROFILE_ID),)).fetchone()
            profile = evidence._profile_from_row(profile_row)
            evidence._insert_evidence(db, profile, EvidenceCreate(
                evidence_type=EvidenceType.STATED_INTEREST_GOAL,
                signal_dimension=SignalDimension.GOAL_PREFERENCE,
                title="Synthetic demo goal",
                observation="Demo fixture only: explore how technology and data can solve practical problems.",
                source_kind=EvidenceSourceKind.SELF_REPORT,
                uncertainty=UncertaintyLevel.NOT_ASSESSED,
                user_interpretation=UserInterpretation.NOT_INTERPRETED,
                context={"synthetic_demo": True, "fixture_id": DEMO_FIXTURE_ID, "fixture_version": "1.0"},
            ))
        db.execute(
            """INSERT INTO demo_fixture_registry(fixture_id,profile_id,fixture_version,fixture_kind,
               data_classification,description,seeded_at,metadata_json) VALUES(?,?,?,?,?,?,?,?)""",
            (DEMO_FIXTURE_ID, str(DEMO_PROFILE_ID), "1.0", "student_profile_with_challenge_evidence",
             "synthetic_demo", "Synthetic showcase profile and challenge history; not real student data.", now,
             json.dumps({"synthetic": True, "not_for_real_student_decisions": True}, sort_keys=True)),
        )
    return str(DEMO_PROFILE_ID)


def _seed_age_mode_demo_profile(db_path: Path, fixture: dict[str, Any]) -> str:
    """Create one deterministic, clearly synthetic age-mode fixture without creating challenge history.

    Keeping the teen fixture free of prior challenge submissions makes it suitable for a live demo:
    complete the next recommended challenge and watch the evidence and next-step state change.
    """
    from app.schemas.student_evidence import (
        AgeBand, ConsentBasis, EvidenceCreate, EvidenceSourceKind, EvidenceType,
        SignalDimension, UncertaintyLevel, UserInterpretation,
    )
    from app.services.evidence_ledger import EvidenceLedgerRepository

    evidence = EvidenceLedgerRepository(db_path)
    fixture_id = str(fixture["fixture_id"])
    profile_id = str(fixture["profile_id"])
    with connect_sqlite(db_path) as db:
        registered = db.execute(
            "SELECT profile_id FROM demo_fixture_registry WHERE fixture_id=?", (fixture_id,)
        ).fetchone()
        if registered:
            if not db.execute("SELECT 1 FROM student_profiles WHERE profile_id=?", (str(registered["profile_id"]),)).fetchone():
                raise RuntimeError(f"Synthetic fixture {fixture_id} points to a missing profile.")
            return str(registered["profile_id"])
        existing = db.execute("SELECT 1 FROM student_profiles WHERE profile_id=?", (profile_id,)).fetchone()
        if existing:
            # The deterministic UUID is reserved for this fixture. Never overwrite a non-fixture profile.
            raise RuntimeError(f"Reserved demo profile ID {profile_id} exists without its fixture registry marker.")
        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        age_band = AgeBand(str(fixture["age_band"]))
        consent_basis = ConsentBasis(str(fixture["consent_basis"]))
        db.execute(
            """INSERT INTO student_profiles(profile_id,age_band,consent_basis,consent_confirmed_at,
               consent_notice_version,current_goal,self_reported_context,created_at,updated_at)
               VALUES(?,?,?,?,?,?,?,?,?)""",
            (profile_id, age_band.value, consent_basis.value, now, "student-evidence-v1.0",
             str(fixture["goal"]), "SYNTHETIC DEMO ONLY. No real student data. Example context for a hackathon walkthrough.", now, now),
        )
        row = db.execute("SELECT * FROM student_profiles WHERE profile_id=?", (profile_id,)).fetchone()
        profile = evidence._profile_from_row(row)
        evidence._insert_evidence(db, profile, EvidenceCreate(
            evidence_type=EvidenceType.STATED_INTEREST_GOAL,
            signal_dimension=SignalDimension.GOAL_PREFERENCE,
            title="Synthetic demo goal",
            observation=str(fixture["goal"]),
            source_kind=EvidenceSourceKind.SELF_REPORT,
            uncertainty=UncertaintyLevel.NOT_ASSESSED,
            user_interpretation=UserInterpretation.NOT_INTERPRETED,
            context={"synthetic_demo": True, "fixture_id": fixture_id, "fixture_version": "1.0"},
        ))
        if age_band == AgeBand.AGE_15_17:
            # Explicitly synthetic prior exposure illustrates the difference between a goal and
            # what the student has already tried. It is self-report, not an assessed competency.
            for title, domain, observation, enjoyment in (
                ("Synthetic design reflection", "design_creative", "Synthetic example: enjoyed trying two visual layouts and comparing how clearly they communicate an idea.", 5),
                ("Synthetic communication reflection", "communication", "Synthetic example: enjoyed explaining a project idea to a different audience and revising after feedback.", 4),
            ):
                evidence._insert_evidence(db, profile, EvidenceCreate(
                    evidence_type=EvidenceType.ACTIVITY_REFLECTION,
                    signal_dimension=SignalDimension.INTEREST,
                    title=title,
                    observation=observation,
                    domain=domain,
                    source_kind=EvidenceSourceKind.SELF_REPORT,
                    uncertainty=UncertaintyLevel.MEDIUM,
                    user_interpretation=UserInterpretation.CONTEXTUAL_OR_MIXED,
                    reported_enjoyment=enjoyment,
                    context={"synthetic_demo": True, "fixture_id": fixture_id, "fixture_version": "1.0", "not_skill_proof": True},
                ))
        db.execute(
            """INSERT INTO demo_fixture_registry(fixture_id,profile_id,fixture_version,fixture_kind,
               data_classification,description,seeded_at,metadata_json) VALUES(?,?,?,?,?,?,?,?)""",
            (fixture_id, profile_id, "1.0", "age_mode_profile_with_synthetic_prior_context",
             "synthetic_demo", str(fixture["description"]), now,
             json.dumps({"synthetic": True, "not_for_real_student_decisions": True,
                         "age_mode": str(fixture["age_band"]), "challenge_history_intentionally_empty": True}, sort_keys=True)),
        )
    return profile_id


def _demo_fixture_summaries(db_path: Path) -> list[dict[str, Any]]:
    with connect_sqlite(db_path) as db:
        rows = db.execute(
            """SELECT d.fixture_id,d.profile_id,d.fixture_version,d.fixture_kind,d.data_classification,
                      d.description,d.seeded_at,p.age_band,p.current_goal
               FROM demo_fixture_registry d JOIN student_profiles p ON p.profile_id=d.profile_id
               ORDER BY CASE p.age_band WHEN '10_14' THEN 0 WHEN '15_17' THEN 1 ELSE 2 END, d.fixture_id"""
        ).fetchall()
        results = []
        for row in rows:
            profile_id = str(row["profile_id"])
            evidence_count = int(db.execute("SELECT COUNT(*) FROM student_evidence_items WHERE profile_id=?", (profile_id,)).fetchone()[0])
            challenge_count = int(db.execute("SELECT COUNT(*) FROM challenge_submissions WHERE profile_id=?", (profile_id,)).fetchone()[0])
            results.append({**dict(row), "synthetic": True, "evidence_count": evidence_count,
                            "challenge_submission_count": challenge_count})
    return results


def seed_demo_fixtures(db_path: str | Path | None = None) -> dict[str, Any]:
    """Idempotently ensure synthetic demo profile, a real challenge submission, and evidence exist."""
    from app.schemas.challenges import ChallengeSubmission, RubricObservationInput
    from app.services.challenges import ChallengeRepository
    from app.services.evidence_ledger import EvidenceLedgerRepository

    path = database_path(db_path)
    profile_id = _seed_demo_profile(path)
    evidence_repo = EvidenceLedgerRepository(path)
    profile = evidence_repo.get_profile(profile_id)
    if profile is None:
        raise RuntimeError("Synthetic demo fixture marker points to a missing profile.")

    challenges = ChallengeRepository(path)
    with connect_sqlite(path) as db:
        challenge_count = int(db.execute("SELECT COUNT(*) FROM challenge_submissions WHERE profile_id=?", (profile_id,)).fetchone()[0])
    if challenge_count == 0:
        challenge = challenges.get("pattern-detective")
        if challenge is None:
            raise RuntimeError("Required synthetic demo challenge is unavailable.")
        observations = [
            RubricObservationInput(criterion_id=challenge.rubric[0].criterion_id, score=2,
                                  observation="Synthetic demo: identifies a pattern in the sample data."),
            RubricObservationInput(criterion_id=challenge.rubric[1].criterion_id, score=1,
                                  observation="Synthetic demo: provides a checkable explanation."),
        ]
        challenges.submit("pattern-detective", ChallengeSubmission(
            profile_id=UUID(profile_id),
            output="SYNTHETIC DEMO ONLY: This example identifies a repeating pattern, explains the rule, and notes that one more example should be checked.",
            rubric_observations=observations,
            enjoyment=4, difficulty_reported=2, confidence=3, willingness_to_continue=4,
            reflection="Synthetic example showing how an observed task and self-reflection remain separate.",
        ))
    for fixture in DEMO_MODE_FIXTURES:
        _seed_age_mode_demo_profile(path, fixture)
    summaries = _demo_fixture_summaries(path)
    adult = next((item for item in summaries if item["fixture_id"] == DEMO_FIXTURE_ID), None)
    if adult is None:
        raise RuntimeError("Synthetic adult demo fixture was not registered.")
    return {"enabled": True, "synthetic": True, "fixture_id": DEMO_FIXTURE_ID, "profile_id": profile_id,
            "evidence_count": adult["evidence_count"], "challenge_submission_count": adult["challenge_submission_count"],
            "fixture_count": len(summaries), "fixtures": summaries,
            "live_walkthrough_fixture_id": next((item["fixture_id"] for item in summaries if item["age_band"] == "15_17"), None)}


def database_status(db_path: str | Path | None = None) -> dict[str, Any]:
    path = database_path(db_path)
    if not path.exists():
        return {"status": "not_initialized", "schema_version": 0, "persistent_store": False, "demo_fixture": None, "demo_fixtures": []}
    try:
        with connect_sqlite(path) as db:
            versions = [int(row[0]) for row in db.execute("SELECT version FROM schema_migrations ORDER BY version")]
            tables = {str(row[0]) for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            fixture = db.execute(
                "SELECT fixture_id,profile_id,fixture_version,fixture_kind,data_classification,seeded_at FROM demo_fixture_registry WHERE fixture_id=?",
                (DEMO_FIXTURE_ID,),
            ).fetchone() if "demo_fixture_registry" in tables else None
            all_fixtures = _demo_fixture_summaries(path) if "demo_fixture_registry" in tables else []
            summary = next((item for item in all_fixtures if item["fixture_id"] == DEMO_FIXTURE_ID), None)
            if summary is None and fixture:
                summary = dict(fixture)
        return {"status": "ready", "schema_version": max(versions, default=0), "persistent_store": True,
                "path_configured": True, "demo_fixture": summary, "demo_fixtures": all_fixtures}
    except sqlite3.Error:
        return {"status": "degraded", "schema_version": 0, "persistent_store": False, "demo_fixture": None, "demo_fixtures": []}


def initialize_database(db_path: str | Path | None = None, *, seed_demo: bool | None = None) -> dict[str, Any]:
    info = migrate_database(db_path)
    should_seed = seed_demo if seed_demo is not None else seed_demo_enabled()
    fixture = seed_demo_fixtures(db_path) if should_seed else {"enabled": False, "synthetic": True}
    return {**info, "demo_fixture": fixture}


def _main() -> int:
    """Minimal reproducible local database administration entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Initialize or inspect the SkillScope SQLite store.")
    parser.add_argument("command", choices=("init", "status"), help="init applies migrations; status prints non-sensitive diagnostics")
    parser.add_argument("--db", type=Path, default=None, help="optional file-backed SQLite path for isolated development/test stores")
    parser.add_argument("--no-demo", action="store_true", help="do not create the synthetic demo fixture (init only)")
    args = parser.parse_args()
    if args.command == "status":
        result = database_status(args.db)
    else:
        result = initialize_database(args.db, seed_demo=False if args.no_demo else None)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.get("status", "ready") not in {"degraded", "not_initialized"} else 1


if __name__ == "__main__":  # pragma: no cover - exercised as a CLI smoke test
    raise SystemExit(_main())
