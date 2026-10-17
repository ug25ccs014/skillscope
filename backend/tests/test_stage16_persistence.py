from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.config import ConfigurationError, PROJECT_ROOT, resolve_database_path, seed_demo_enabled
from app.schemas.preferences import StudentPreferencesUpdate
from app.schemas.discovery_loop import LoopPreference
from app.schemas.challenges import ChallengeDomain
from app.schemas.student_evidence import AgeBand, ConsentBasis, StudentProfileCreate
from app.services.database import database_status, initialize_database
from app.services.evidence_ledger import EvidenceLedgerRepository
from app.services.preferences import StudentPreferencesRepository


def test_database_url_is_file_backed_and_relative_paths_are_project_anchored() -> None:
    assert resolve_database_path("sqlite:///./data/test-stage16.db") == (PROJECT_ROOT / "data/test-stage16.db").resolve()
    with pytest.raises(ConfigurationError, match="file-backed"):
        resolve_database_path("sqlite:///:memory:")
    with pytest.raises(ConfigurationError, match="Only file-backed SQLite"):
        resolve_database_path("postgresql://localhost/skillscope")


def test_demo_database_bootstrap_is_repeatable_and_persists_state(tmp_path: Path) -> None:
    db_path = tmp_path / "durable-demo.db"
    first = initialize_database(db_path, seed_demo=True)
    second = initialize_database(db_path, seed_demo=True)

    assert first["schema_version"] == 2
    assert second["applied_migrations"] == [1, 2]
    assert first["demo_fixture"]["synthetic"] is True
    assert second["demo_fixture"]["profile_id"] == first["demo_fixture"]["profile_id"]
    assert second["demo_fixture"]["evidence_count"] == first["demo_fixture"]["evidence_count"]
    assert second["demo_fixture"]["challenge_submission_count"] == first["demo_fixture"]["challenge_submission_count"] == 1

    profile_id = first["demo_fixture"]["profile_id"]
    # Reopen through fresh repository instances: data must outlive the startup/bootstrap call.
    profile = EvidenceLedgerRepository(db_path).get_profile(profile_id)
    assert profile is not None
    with sqlite3.connect(db_path) as db:
        classification = db.execute(
            "SELECT data_classification FROM demo_fixture_registry WHERE profile_id=?", (profile_id,)
        ).fetchone()[0]
        evidence_count = db.execute(
            "SELECT COUNT(*) FROM student_evidence_items WHERE profile_id=?", (profile_id,)
        ).fetchone()[0]
        challenge_count = db.execute(
            "SELECT COUNT(*) FROM challenge_submissions WHERE profile_id=?", (profile_id,)
        ).fetchone()[0]
    assert classification == "synthetic_demo"
    assert evidence_count == first["demo_fixture"]["evidence_count"]
    assert challenge_count == 1

    status = database_status(db_path)
    serialized = json.dumps(status)
    assert status["persistent_store"] is True
    assert status["demo_fixture"]["data_classification"] == "synthetic_demo"
    assert str(db_path) not in serialized  # Never disclose absolute storage paths.


def test_production_demo_seed_default_is_off_and_can_be_explicitly_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKILLSCOPE_ENV", "production")
    monkeypatch.delenv("SKILLSCOPE_SEED_DEMO", raising=False)
    assert seed_demo_enabled() is False
    monkeypatch.setenv("SKILLSCOPE_SEED_DEMO", "true")
    assert seed_demo_enabled() is True
    monkeypatch.setenv("SKILLSCOPE_SEED_DEMO", "false")
    assert seed_demo_enabled() is False


def test_preferences_survive_repository_recreation_and_unknown_profile_is_absent(tmp_path: Path) -> None:
    db_path = tmp_path / "preferences.db"
    profiles = EvidenceLedgerRepository(db_path)
    profile = profiles.create_profile(StudentProfileCreate(
        age_band=AgeBand.AGE_18_PLUS,
        consent_basis=ConsentBasis.STUDENT_CONFIRMED,
        consent_confirmed=True,
        current_goal="Explore accessible technology projects",
    ))
    first_repo = StudentPreferencesRepository(db_path)
    saved = first_repo.save(profile.profile_id, StudentPreferencesUpdate(
        journey_preference=LoopPreference.ALTERNATIVE,
        preferred_domains=[ChallengeDomain.TECHNOLOGY, ChallengeDomain.DESIGN_CREATIVE],
        accessibility_formats=["text", "low_materials"],
    ))
    assert saved is not None and saved.persisted is True

    restarted = StudentPreferencesRepository(db_path).get(profile.profile_id)
    assert restarted is not None
    assert restarted.persisted is True
    assert restarted.journey_preference == LoopPreference.ALTERNATIVE
    assert set(restarted.preferred_domains) == {ChallengeDomain.TECHNOLOGY, ChallengeDomain.DESIGN_CREATIVE}
    assert restarted.accessibility_formats == ["text", "low_materials"]
    assert StudentPreferencesRepository(db_path).get("00000000-0000-4000-8000-000000000099") is None


def test_preferences_reject_unknown_accessibility_format() -> None:
    with pytest.raises(ValueError, match="Accessibility formats"):
        StudentPreferencesUpdate(accessibility_formats=["background-monitoring"])
