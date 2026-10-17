"""SQLite persistence and transparent summaries for student evidence.

This is a single-instance hackathon MVP store, not an authentication system. The opaque profile
UUID is a record locator; production use must add verified identity, authorization and retention
controls before storing real minors' data.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from app.schemas.student_evidence import (
    AgeBand,
    ConsentBasis,
    EvidenceCreate,
    EvidenceItem,
    EvidenceSourceKind,
    EvidenceType,
    EvidenceUpdate,
    SignalDimension,
    SignalEvidenceSummary,
    StudentProfile,
    StudentProfileCreate,
    StudentProfileSummary,
    StudentProfileUpdate,
    UncertaintyLevel,
    UserInterpretation,
)

from app.config import resolve_database_path
from app.services.database import connect_sqlite

DEFAULT_DB_PATH = resolve_database_path()
SUMMARY_POLICY_VERSION = "evidence-summary-v1.0"


def utc_now() -> datetime:
    return datetime.now(UTC).replace(microsecond=0)


def _iso(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamps must include a timezone.")
    return value.astimezone(UTC).isoformat()


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Stored timestamp is missing timezone information.")
    return parsed.astimezone(UTC)


class EvidenceLedgerRepository:
    """Persistence layer; each method creates a connection with FK enforcement enabled."""

    def __init__(self, db_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        return connect_sqlite(self.db_path)

    def _initialize(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS student_profiles (
                    profile_id TEXT PRIMARY KEY,
                    age_band TEXT NOT NULL CHECK(age_band IN ('10_14','15_17','18_plus')),
                    consent_basis TEXT NOT NULL CHECK(consent_basis IN ('student_confirmed','guardian_confirmed')),
                    consent_confirmed_at TEXT NOT NULL,
                    consent_notice_version TEXT NOT NULL,
                    current_goal TEXT,
                    self_reported_context TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS student_evidence_items (
                    evidence_id TEXT PRIMARY KEY,
                    profile_id TEXT NOT NULL,
                    evidence_type TEXT NOT NULL,
                    signal_dimension TEXT NOT NULL,
                    title TEXT NOT NULL,
                    observation TEXT NOT NULL,
                    domain TEXT,
                    source_kind TEXT NOT NULL,
                    source_reference TEXT,
                    observed_at TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    uncertainty TEXT NOT NULL,
                    user_interpretation TEXT NOT NULL,
                    consent_basis_at_capture TEXT NOT NULL,
                    consent_confirmed_at_capture TEXT NOT NULL,
                    consent_notice_version_at_capture TEXT NOT NULL,
                    behavior_consent_confirmed INTEGER NOT NULL DEFAULT 0 CHECK(behavior_consent_confirmed IN (0,1)),
                    behavior_consent_confirmed_at TEXT,
                    challenge_label TEXT,
                    rubric_name TEXT,
                    rubric_version TEXT,
                    rubric_observations_json TEXT NOT NULL,
                    reported_enjoyment INTEGER,
                    reported_curiosity INTEGER,
                    reported_effort INTEGER,
                    reported_difficulty INTEGER,
                    context_json TEXT NOT NULL,
                    FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE
                );
                CREATE INDEX IF NOT EXISTS idx_student_evidence_profile_observed
                    ON student_evidence_items(profile_id, observed_at DESC, evidence_id);
                CREATE INDEX IF NOT EXISTS idx_student_evidence_profile_signal
                    ON student_evidence_items(profile_id, signal_dimension, observed_at DESC);
                """
            )

    @staticmethod
    def _profile_from_row(row: sqlite3.Row) -> StudentProfile:
        return StudentProfile(
            profile_id=UUID(row["profile_id"]),
            age_band=AgeBand(row["age_band"]),
            consent_basis=ConsentBasis(row["consent_basis"]),
            consent_confirmed_at=_parse_time(row["consent_confirmed_at"]),
            current_goal=row["current_goal"],
            self_reported_context=row["self_reported_context"],
            created_at=_parse_time(row["created_at"]),
            updated_at=_parse_time(row["updated_at"]),
            consent_notice_version=row["consent_notice_version"],
        )

    @staticmethod
    def _evidence_from_row(row: sqlite3.Row) -> EvidenceItem:
        return EvidenceItem(
            evidence_id=UUID(row["evidence_id"]),
            profile_id=UUID(row["profile_id"]),
            evidence_type=row["evidence_type"],
            signal_dimension=row["signal_dimension"],
            title=row["title"],
            observation=row["observation"],
            domain=row["domain"],
            source_kind=row["source_kind"],
            source_reference=row["source_reference"],
            observed_at=_parse_time(row["observed_at"]),
            recorded_at=_parse_time(row["recorded_at"]),
            updated_at=_parse_time(row["updated_at"]),
            uncertainty=row["uncertainty"],
            user_interpretation=row["user_interpretation"],
            consent_basis_at_capture=row["consent_basis_at_capture"],
            consent_confirmed_at_capture=_parse_time(row["consent_confirmed_at_capture"]),
            consent_notice_version_at_capture=row["consent_notice_version_at_capture"],
            behavior_consent_confirmed=bool(row["behavior_consent_confirmed"]),
            behavior_consent_confirmed_at=_parse_time(row["behavior_consent_confirmed_at"]) if row["behavior_consent_confirmed_at"] else None,
            challenge_label=row["challenge_label"],
            rubric_name=row["rubric_name"],
            rubric_version=row["rubric_version"],
            rubric_observations=json.loads(row["rubric_observations_json"]),
            reported_enjoyment=row["reported_enjoyment"],
            reported_curiosity=row["reported_curiosity"],
            reported_effort=row["reported_effort"],
            reported_difficulty=row["reported_difficulty"],
            context=json.loads(row["context_json"]),
        )

    def _insert_evidence(self, db: sqlite3.Connection, profile: StudentProfile, request: EvidenceCreate) -> str:
        """Insert a validated item on a caller-owned connection for atomic profile/history updates."""
        evidence_id = str(uuid4())
        now = _iso(utc_now())
        payload = request.model_dump(mode="json")
        db.execute(
            """INSERT INTO student_evidence_items (
                evidence_id, profile_id, evidence_type, signal_dimension, title, observation, domain,
                source_kind, source_reference, observed_at, recorded_at, updated_at, uncertainty,
                user_interpretation, consent_basis_at_capture, consent_confirmed_at_capture,
                consent_notice_version_at_capture, behavior_consent_confirmed, behavior_consent_confirmed_at,
                challenge_label, rubric_name, rubric_version, rubric_observations_json, reported_enjoyment,
                reported_curiosity, reported_effort, reported_difficulty, context_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (evidence_id, str(profile.profile_id), payload["evidence_type"], payload["signal_dimension"],
             payload["title"], payload["observation"], payload.get("domain"), payload["source_kind"],
             payload.get("source_reference"), _iso(request.observed_at), now, now, payload["uncertainty"],
             payload["user_interpretation"], profile.consent_basis.value, _iso(profile.consent_confirmed_at),
             profile.consent_notice_version, int(bool(payload.get("behavior_consent_confirmed"))),
             now if payload.get("behavior_consent_confirmed") else None, payload.get("challenge_label"),
             payload.get("rubric_name"), payload.get("rubric_version"),
             json.dumps(payload.get("rubric_observations", []), sort_keys=True),
             payload.get("reported_enjoyment"), payload.get("reported_curiosity"),
             payload.get("reported_effort"), payload.get("reported_difficulty"),
             json.dumps(payload.get("context", {}), sort_keys=True)),
        )
        return evidence_id

    def create_profile(self, request: StudentProfileCreate) -> StudentProfile:
        now = _iso(utc_now())
        profile_id = str(uuid4())
        with self._connect() as db:
            db.execute(
                """INSERT INTO student_profiles (
                    profile_id, age_band, consent_basis, consent_confirmed_at, consent_notice_version,
                    current_goal, self_reported_context, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (profile_id, request.age_band.value, request.consent_basis.value, now,
                 "student-evidence-v1.0", request.current_goal, request.self_reported_context, now, now),
            )
            profile = self._profile_from_row(
                db.execute("SELECT * FROM student_profiles WHERE profile_id = ?", (profile_id,)).fetchone()
            )
            # A goal entered during profile creation is a dated self-report, not only a mutable
            # profile field. Write it in the same transaction as the profile.
            if request.current_goal and request.current_goal.strip():
                self._insert_evidence(
                    db,
                    profile,
                    EvidenceCreate(
                        evidence_type=EvidenceType.STATED_INTEREST_GOAL,
                        signal_dimension=SignalDimension.GOAL_PREFERENCE,
                        title="Initial stated goal",
                        observation=f"Student stated this goal at profile creation: {request.current_goal.strip()}",
                        source_kind=EvidenceSourceKind.SELF_REPORT,
                        uncertainty=UncertaintyLevel.NOT_ASSESSED,
                        user_interpretation=UserInterpretation.NOT_INTERPRETED,
                        context={"profile_field": "current_goal", "capture": "profile_creation"},
                    ),
                )
        return self.get_profile(profile_id) or profile

    def get_profile(self, profile_id: str | UUID) -> StudentProfile | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM student_profiles WHERE profile_id = ?", (str(profile_id),)).fetchone()
        return self._profile_from_row(row) if row else None

    def update_profile(self, profile_id: str | UUID, request: StudentProfileUpdate) -> StudentProfile | None:
        profile = self.get_profile(profile_id)
        if profile is None:
            return None
        changes = request.model_dump(exclude_unset=True, mode="json")
        if not changes:
            return profile
        effective_age = AgeBand(changes.get("age_band", profile.age_band.value))
        age_changed = "age_band" in changes and effective_age != profile.age_band
        provided_consent = "consent_basis" in changes or "consent_confirmed" in changes
        if age_changed and not provided_consent:
            raise ValueError("Changing the age band requires fresh age-appropriate consent confirmation.")
        if age_changed and ((profile.age_band == AgeBand.AGE_18_PLUS) != (effective_age == AgeBand.AGE_18_PLUS)):
            # Do not retrospectively relabel old evidence as if it had been captured under a
            # different consent regime. Correct across the minor/adult boundary by deleting the
            # profile/history and recreating it with the appropriate consent basis.
            with self._connect() as db:
                existing_count = db.execute(
                    "SELECT COUNT(*) AS n FROM student_evidence_items WHERE profile_id = ?",
                    (str(profile_id),),
                ).fetchone()["n"]
            if existing_count:
                raise ValueError("This age-band correction crosses the under-18/adult consent boundary while evidence exists. To preserve the historical consent record, permanently delete this profile and recreate it with the correct age band and consent.")
        if provided_consent and changes.get("consent_confirmed") is not True:
            raise ValueError("Consent cannot be withdrawn through profile editing. Delete the profile to permanently remove its evidence.")
        if age_changed or provided_consent:
            basis_raw = changes.get("consent_basis", profile.consent_basis.value)
            basis = ConsentBasis(basis_raw)
            required = ConsentBasis.GUARDIAN_CONFIRMED if effective_age in {AgeBand.AGE_10_14, AgeBand.AGE_15_17} else ConsentBasis.STUDENT_CONFIRMED
            if basis != required:
                raise ValueError("The consent basis does not match the profile age band.")
            changes["consent_basis"] = basis.value
            changes["consent_confirmed_at"] = _iso(utc_now())
        changes.pop("consent_confirmed", None)
        if "age_band" in changes and changes["age_band"] is not None:
            changes["age_band"] = AgeBand(changes["age_band"]).value
        allowed = {"age_band", "consent_basis", "consent_confirmed_at", "current_goal", "self_reported_context"}
        if not set(changes).issubset(allowed):
            raise ValueError("Unsupported profile update field.")
        goal_was_updated = "current_goal" in changes and changes["current_goal"] != profile.current_goal
        updated_goal = changes.get("current_goal")
        changes["updated_at"] = _iso(utc_now())
        assignments = ", ".join(f"{key} = ?" for key in changes)
        with self._connect() as db:
            db.execute(
                f"UPDATE student_profiles SET {assignments} WHERE profile_id = ?",
                (*changes.values(), str(profile_id)),
            )
            updated_profile = self._profile_from_row(
                db.execute("SELECT * FROM student_profiles WHERE profile_id = ?", (str(profile_id),)).fetchone()
            )
            if goal_was_updated:
                goal_statement = (
                    f"Student updated their stated goal: {updated_goal.strip()}"
                    if isinstance(updated_goal, str) and updated_goal.strip()
                    else "Student cleared their previously stated goal; no replacement goal was provided."
                )
                # The profile update and goal-history event commit or roll back together.
                self._insert_evidence(
                    db,
                    updated_profile,
                    EvidenceCreate(
                        evidence_type=EvidenceType.STATED_INTEREST_GOAL,
                        signal_dimension=SignalDimension.GOAL_PREFERENCE,
                        title="Updated stated goal" if updated_goal else "Stated goal cleared",
                        observation=goal_statement,
                        source_kind=EvidenceSourceKind.SELF_REPORT,
                        uncertainty=UncertaintyLevel.NOT_ASSESSED,
                        user_interpretation=UserInterpretation.NOT_INTERPRETED,
                        context={"profile_field": "current_goal", "capture": "profile_update"},
                    ),
                )
        return self.get_profile(profile_id) or updated_profile

    def add_evidence(self, profile_id: str | UUID, request: EvidenceCreate) -> EvidenceItem:
        profile = self.get_profile(profile_id)
        if profile is None:
            raise KeyError("profile_not_found")
        with self._connect() as db:
            evidence_id = self._insert_evidence(db, profile, request)
        item = self.get_evidence(profile_id, evidence_id)
        assert item is not None
        return item

    def get_evidence(self, profile_id: str | UUID, evidence_id: str | UUID) -> EvidenceItem | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT * FROM student_evidence_items WHERE profile_id = ? AND evidence_id = ?",
                (str(profile_id), str(evidence_id)),
            ).fetchone()
        return self._evidence_from_row(row) if row else None

    def list_evidence(
        self, profile_id: str | UUID, *, signal_dimension: SignalDimension | None = None,
        evidence_type: EvidenceType | None = None, limit: int = 50, offset: int = 0,
    ) -> tuple[list[EvidenceItem], int]:
        clauses = ["profile_id = ?"]
        values: list[Any] = [str(profile_id)]
        if signal_dimension:
            clauses.append("signal_dimension = ?")
            values.append(signal_dimension.value)
        if evidence_type:
            clauses.append("evidence_type = ?")
            values.append(evidence_type.value)
        where = " AND ".join(clauses)
        with self._connect() as db:
            count = db.execute(f"SELECT COUNT(*) AS n FROM student_evidence_items WHERE {where}", values).fetchone()["n"]
            rows = db.execute(
                f"SELECT * FROM student_evidence_items WHERE {where} ORDER BY observed_at DESC, evidence_id LIMIT ? OFFSET ?",
                (*values, limit, offset),
            ).fetchall()
        return [self._evidence_from_row(row) for row in rows], int(count)

    def update_evidence(self, profile_id: str | UUID, evidence_id: str | UUID, request: EvidenceUpdate) -> EvidenceItem | None:
        current = self.get_evidence(profile_id, evidence_id)
        if current is None:
            return None
        updates = request.model_dump(exclude_unset=True, mode="json")
        if not updates:
            return current
        current_payload = current.model_dump(mode="json")
        mutable_fields = set(EvidenceCreate.model_fields.keys())
        merged = {key: current_payload.get(key) for key in mutable_fields}
        for key, value in updates.items():
            if key not in mutable_fields:
                raise ValueError(f"Field {key} cannot be edited.")
            # Null rubric list means clear all criterion rows, not a null list in storage.
            if key == "rubric_observations" and value is None:
                value = []
            merged[key] = value
        # Re-run all cross-field constraints after the patch so an edit cannot leave stale invalid data.
        validated = EvidenceCreate.model_validate(merged)
        payload = validated.model_dump(mode="json")
        columns = {
            "evidence_type": payload["evidence_type"], "signal_dimension": payload["signal_dimension"],
            "title": payload["title"], "observation": payload["observation"], "domain": payload.get("domain"),
            "source_kind": payload["source_kind"], "source_reference": payload.get("source_reference"),
            "observed_at": _iso(validated.observed_at), "updated_at": _iso(utc_now()),
            "uncertainty": payload["uncertainty"], "user_interpretation": payload["user_interpretation"],
            "challenge_label": payload.get("challenge_label"), "rubric_name": payload.get("rubric_name"),
            "rubric_version": payload.get("rubric_version"),
            "rubric_observations_json": json.dumps(payload.get("rubric_observations", []), sort_keys=True),
            "reported_enjoyment": payload.get("reported_enjoyment"), "reported_curiosity": payload.get("reported_curiosity"),
            "reported_effort": payload.get("reported_effort"), "reported_difficulty": payload.get("reported_difficulty"),
            "context_json": json.dumps(payload.get("context", {}), sort_keys=True),
        }
        assignments = ", ".join(f"{key} = ?" for key in columns)
        with self._connect() as db:
            db.execute(
                f"UPDATE student_evidence_items SET {assignments} WHERE profile_id = ? AND evidence_id = ?",
                (*columns.values(), str(profile_id), str(evidence_id)),
            )
        return self.get_evidence(profile_id, evidence_id)

    def delete_evidence(self, profile_id: str | UUID, evidence_id: str | UUID) -> bool:
        with self._connect() as db:
            result = db.execute(
                "DELETE FROM student_evidence_items WHERE profile_id = ? AND evidence_id = ?",
                (str(profile_id), str(evidence_id)),
            )
            return result.rowcount > 0

    def clear_evidence(self, profile_id: str | UUID) -> int | None:
        if self.get_profile(profile_id) is None:
            return None
        with self._connect() as db:
            result = db.execute("DELETE FROM student_evidence_items WHERE profile_id = ?", (str(profile_id),))
            # A clear-history action must not leave the same stated goal/context behind in the
            # editable profile snapshot while reporting an empty profile shell.
            db.execute(
                "UPDATE student_profiles SET current_goal = NULL, self_reported_context = NULL, updated_at = ? WHERE profile_id = ?",
                (_iso(utc_now()), str(profile_id)),
            )
            return result.rowcount

    def delete_profile(self, profile_id: str | UUID) -> bool:
        with self._connect() as db:
            result = db.execute("DELETE FROM student_profiles WHERE profile_id = ?", (str(profile_id),))
            return result.rowcount > 0

    def profile_summary(self, profile_id: str | UUID) -> StudentProfileSummary | None:
        profile = self.get_profile(profile_id)
        if profile is None:
            return None
        now = utc_now()
        with self._connect() as db:
            counts = {
                row["signal_dimension"]: int(row["n"])
                for row in db.execute(
                    "SELECT signal_dimension, COUNT(*) AS n FROM student_evidence_items WHERE profile_id = ? GROUP BY signal_dimension",
                    (str(profile_id),),
                ).fetchall()
            }
            interpretations: dict[str, dict[str, int]] = {}
            for row in db.execute(
                "SELECT signal_dimension, user_interpretation, COUNT(*) AS n FROM student_evidence_items WHERE profile_id = ? GROUP BY signal_dimension, user_interpretation",
                (str(profile_id),),
            ).fetchall():
                interpretations.setdefault(row["signal_dimension"], {})[row["user_interpretation"]] = int(row["n"])
            recent_rows: dict[str, list[sqlite3.Row]] = {}
            # Window function bounds each signal to five records even for long-running profiles.
            rows = db.execute(
                """SELECT * FROM (
                    SELECT e.*, ROW_NUMBER() OVER (PARTITION BY signal_dimension ORDER BY observed_at DESC, evidence_id) AS rn
                    FROM student_evidence_items e WHERE profile_id = ?
                ) WHERE rn <= 5 ORDER BY signal_dimension, observed_at DESC""",
                (str(profile_id),),
            ).fetchall()
            for row in rows:
                recent_rows.setdefault(row["signal_dimension"], []).append(row)
        signal_summaries: list[SignalEvidenceSummary] = []
        for dimension in SignalDimension:
            count = counts.get(dimension.value, 0)
            ints = interpretations.get(dimension.value, {})
            support = ints.get(UserInterpretation.SUPPORTS_CURRENT_HYPOTHESIS.value, 0)
            challenge = ints.get(UserInterpretation.CHALLENGES_CURRENT_HYPOTHESIS.value, 0)
            if count == 0:
                status = "unknown"
                explanation = "No evidence is recorded for this signal. Unknown—not zero ability, low interest, or lack of potential."
            elif support > 0 and challenge > 0:
                status = "mixed"
                explanation = "User-labelled evidence points in more than one direction. Keep this as an open question; do not force a verdict."
            else:
                status = "evidence_available"
                explanation = "Records are available, but this is not a score or a definitive trait. Consider task context, exposure, recency and uncertainty."
            summaries: list[dict[str, Any]] = []
            for row in recent_rows.get(dimension.value, []):
                observed = _parse_time(row["observed_at"])
                days = max(0, (now - observed).days)
                recency = "recent" if days <= 30 else "developing" if days <= 90 else "older"
                summaries.append({
                    "evidence_id": row["evidence_id"], "title": row["title"], "evidence_type": row["evidence_type"],
                    "observation": row["observation"], "source_kind": row["source_kind"],
                    "observed_at": observed.isoformat(), "age_in_days": days, "recency": recency,
                    "uncertainty": row["uncertainty"], "user_interpretation": row["user_interpretation"],
                    "context": json.loads(row["context_json"]),
                })
            signal_summaries.append(SignalEvidenceSummary(
                signal_dimension=dimension, status=status, evidence_count=count,
                interpretation_counts={entry.value: ints.get(entry.value, 0) for entry in UserInterpretation},
                explanation=explanation, recent_evidence=summaries,
            ))
        total = sum(counts.values())
        return StudentProfileSummary(
            profile_id=profile.profile_id, generated_at=now, overall_status="evidence_available" if total else "unknown",
            overall_explanation=("The ledger contains observations. They are contextual evidence, not a complete profile or a career verdict."
                                 if total else "No evidence has been recorded yet. The profile is unknown, not a zero or a negative assessment."),
            signals=signal_summaries, evidence_count=total,
            limitations=[
                "This summary uses transparent counts and user-labelled interpretations; it does not calculate aptitude, personality, ability, or career-fit scores.",
                "Task performance is interpretable only with its own challenge, rubric, score scale, context, exposure and uncertainty.",
                "Recency labels describe the age of a record, not how trustworthy or important it is.",
                "The MVP stores a consent confirmation but does not verify the identity or authority of the person confirming it.",
            ],
        )
