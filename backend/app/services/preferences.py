"""Persist explicit, user-controlled discovery preferences."""
from __future__ import annotations
import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID
from app.schemas.preferences import StudentPreferences, StudentPreferencesUpdate
from app.schemas.discovery_loop import LoopPreference
from app.schemas.challenges import ChallengeDomain
from app.services.database import connect_sqlite
from app.services.evidence_ledger import DEFAULT_DB_PATH, EvidenceLedgerRepository


class StudentPreferencesRepository:
    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.evidence = EvidenceLedgerRepository(self.db_path)
        with connect_sqlite(self.db_path) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS student_preferences (
                profile_id TEXT PRIMARY KEY,
                journey_preference TEXT NOT NULL DEFAULT 'balanced'
                    CHECK(journey_preference IN ('balanced','explore','develop','validate','alternative')),
                preferred_domains_json TEXT NOT NULL DEFAULT '[]',
                accessibility_formats_json TEXT NOT NULL DEFAULT '[]',
                updated_at TEXT NOT NULL,
                FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE
            )""")

    def get(self, profile_id: str | UUID) -> StudentPreferences | None:
        profile = self.evidence.get_profile(profile_id)
        if profile is None:
            return None
        with connect_sqlite(self.db_path) as db:
            row = db.execute("SELECT * FROM student_preferences WHERE profile_id=?", (str(profile.profile_id),)).fetchone()
        if not row:
            return StudentPreferences(profile_id=profile.profile_id, persisted=False)
        return StudentPreferences(
            profile_id=profile.profile_id,
            journey_preference=LoopPreference(row["journey_preference"]),
            preferred_domains=[ChallengeDomain(item) for item in json.loads(row["preferred_domains_json"])],
            accessibility_formats=json.loads(row["accessibility_formats_json"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            persisted=True,
        )

    def save(self, profile_id: str | UUID, request: StudentPreferencesUpdate) -> StudentPreferences | None:
        profile = self.evidence.get_profile(profile_id)
        if profile is None:
            return None
        now = datetime.now(UTC).replace(microsecond=0).isoformat()
        payload = request.model_dump(mode="json")
        with connect_sqlite(self.db_path) as db:
            db.execute("""INSERT INTO student_preferences(
                profile_id,journey_preference,preferred_domains_json,accessibility_formats_json,updated_at
            ) VALUES(?,?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET
                journey_preference=excluded.journey_preference,
                preferred_domains_json=excluded.preferred_domains_json,
                accessibility_formats_json=excluded.accessibility_formats_json,
                updated_at=excluded.updated_at""",
                (str(profile.profile_id), payload["journey_preference"],
                 json.dumps(payload["preferred_domains"], sort_keys=True),
                 json.dumps(payload["accessibility_formats"], sort_keys=True), now))
        return self.get(profile_id)
