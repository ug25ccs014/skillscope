from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.discovery_loop import LoopPreference
from app.services.discovery_loop import DiscoveryLoopRepository


@pytest.fixture
def setup_loop(tmp_path, monkeypatch):
    repository = DiscoveryLoopRepository(tmp_path / "loop.db")
    monkeypatch.setattr("app.api.discovery_loop.repo", lambda: repository)
    monkeypatch.setattr("app.api.challenges.repo", lambda: repository.challenges)
    monkeypatch.setattr("app.api.student_evidence.get_repository", lambda: repository.evidence)
    return TestClient(app), repository


def make_profile(client, age_band="18_plus", consent_basis="student_confirmed", goal=None):
    response = client.post("/api/student-profiles", json={
        "age_band": age_band,
        "consent_basis": consent_basis,
        "consent_confirmed": True,
        "current_goal": goal,
    })
    assert response.status_code == 201, response.text
    return response.json()


def submit(client, profile_id, challenge_id, interpretation="not_interpreted", enjoyment=3,
           difficulty=3, confidence=3, willingness=3, score=2):
    challenge = client.get(f"/api/challenges/{challenge_id}").json()
    observations = []
    for criterion in challenge["rubric"][:2]:
        observations.append({
            "criterion_id": criterion["criterion_id"],
            "score": score,
            "observation": f"Observed {criterion['label'].lower()} in the submitted work.",
        })
    response = client.post(f"/api/challenges/{challenge_id}/submissions", json={
        "profile_id": profile_id,
        "output": "A short solution and a note about how I checked it.",
        "rubric_observations": observations,
        "enjoyment": enjoyment,
        "difficulty_reported": difficulty,
        "confidence": confidence,
        "willingness_to_continue": willingness,
        "reflection": "This activity helped me notice what I want to test next.",
        "hypothesis_interpretation": interpretation,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_new_profile_receives_age_scaled_exploratory_task_and_unknown_exposure(setup_loop):
    client, _ = setup_loop
    profile = make_profile(client, age_band="15_17", consent_basis="guardian_confirmed")
    first = client.get(f"/api/discovery-loop/{profile['profile_id']}")
    assert first.status_code == 200, first.text
    body = first.json()
    assert body["loop_policy_version"] == "discovery-loop-v1.0"
    assert body["mode"] == "explore_and_validate"
    assert body["total_submissions"] == 0
    assert body["evidence_count"] == 0
    assert body["next_challenge"]["title"] == "Pattern Detective: Evidence Check"
    assert body["next_challenge"]["reason_code"] == "explore_underexposed_domain"
    assert next(x for x in body["domain_exposure"] if x["domain"] == "science_research")["status"] == "unknown"
    assert "not a verdict" in body["notice"]


def test_completion_persists_evidence_and_changes_next_task(setup_loop):
    client, repository = setup_loop
    profile = make_profile(client)
    before = client.get(f"/api/discovery-loop/{profile['profile_id']}").json()
    assert before["next_challenge"]["challenge_id"] == "pattern-detective"

    scored = submit(client, profile["profile_id"], "pattern-detective", "supports_current_hypothesis", enjoyment=5, willingness=5)
    assert scored["evidence_created_id"]
    after = client.get(f"/api/discovery-loop/{profile['profile_id']}")
    assert after.status_code == 200, after.text
    body = after.json()
    assert body["total_submissions"] == 1
    assert body["evidence_count"] == 1
    assert body["last_completion"]["interpretation"] == "supports_current_hypothesis"
    assert body["last_completion"]["enjoyment"] == 5
    assert body["next_challenge"]["challenge_id"] == "data-story"
    assert body["next_challenge"]["reason_code"] == "develop_demonstrated_engagement"
    assert body["next_challenge"]["challenge_id"] != "pattern-detective"
    assert "different task" in body["what_changed"].lower()

    evidence = repository.evidence.list_evidence(profile["profile_id"])[0][0]
    assert evidence.domain == "logic_data"
    assert evidence.user_interpretation.value == "supports_current_hypothesis"
    assert evidence.reported_curiosity is None  # Confidence is not incorrectly stored as curiosity.
    assert evidence.context["self_reported_confidence"] == 3
    # Pure read calls over unchanged persisted inputs return identical recommendations.
    second = client.get(f"/api/discovery-loop/{profile['profile_id']}").json()
    assert second["next_challenge"]["challenge_id"] == body["next_challenge"]["challenge_id"]
    assert second["what_changed"] == body["what_changed"]


def test_explicit_conflict_tests_an_alternative_domain(setup_loop):
    client, _ = setup_loop
    profile = make_profile(client)
    submit(client, profile["profile_id"], "pattern-detective", "challenges_current_hypothesis")
    body = client.get(f"/api/discovery-loop/{profile['profile_id']}").json()
    assert body["next_challenge"]["reason_code"] == "test_alternative_pathway"
    assert body["next_challenge"]["domain"] != "logic_data"
    assert "You said the last activity challenged" in body["next_challenge"]["rationale"]


def test_mixed_reflection_validates_with_different_task_in_same_domain(setup_loop):
    client, _ = setup_loop
    profile = make_profile(client)
    submit(client, profile["profile_id"], "pattern-detective", "contextual_or_mixed")
    body = client.get(f"/api/discovery-loop/{profile['profile_id']}").json()
    assert body["next_challenge"]["reason_code"] == "validate_uncertain_hypothesis"
    assert body["next_challenge"]["domain"] == "logic_data"
    assert body["next_challenge"]["challenge_id"] == "data-story"


def test_requesting_development_without_engagement_falls_back_to_exploration(setup_loop):
    client, _ = setup_loop
    profile = make_profile(client)
    body = client.get(f"/api/discovery-loop/{profile['profile_id']}?preference=develop").json()
    assert body["preference"] == "develop"
    assert body["next_challenge"]["reason_code"] == "explore_before_developing"
    submit(client, profile["profile_id"], "pattern-detective", "not_interpreted", enjoyment=5, willingness=5)
    developed = client.get(f"/api/discovery-loop/{profile['profile_id']}?preference=develop").json()
    assert developed["next_challenge"]["reason_code"] == "develop_demonstrated_engagement"
    assert developed["next_challenge"]["domain"] == "logic_data"


def test_not_enough_evidence_is_explained_as_unknown_not_failure(setup_loop):
    client, _ = setup_loop
    profile = make_profile(client)
    scored = client.post("/api/challenges/pattern-detective/submissions", json={
        "profile_id": profile["profile_id"],
        "output": "I stopped before completing the task.",
        "rubric_observations": [{
            "criterion_id": "identify", "score": None, "observation": "No observable result yet."
        }],
        "hypothesis_interpretation": "not_interpreted",
    })
    assert scored.status_code == 200, scored.text
    state = client.get(f"/api/discovery-loop/{profile['profile_id']}").json()
    assert state["last_completion"]["evidence_status"] == "not_enough_evidence"
    assert state["last_completion"]["objective_score"] is None
    assert "not a negative score" in state["what_changed"]
    assert state["total_submissions"] == 1


def test_missing_profile_returns_404(setup_loop):
    client, _ = setup_loop
    import uuid
    response = client.get(f"/api/discovery-loop/{uuid.uuid4()}")
    assert response.status_code == 404


def test_explicit_alternative_preference_avoids_previous_domain(setup_loop):
    client, _ = setup_loop
    profile = make_profile(client)
    submit(client, profile["profile_id"], "pattern-detective")
    body = client.get(f"/api/discovery-loop/{profile['profile_id']}?preference=alternative").json()
    assert body["next_challenge"]["reason_code"] == "test_alternative_pathway"
    assert body["next_challenge"]["domain"] != "logic_data"


def test_stage10_database_schema_migrates_additively_for_interpretation(tmp_path):
    import sqlite3
    from app.services.challenges import ChallengeRepository
    from app.services.evidence_ledger import EvidenceLedgerRepository

    db_path = tmp_path / "stage10-old-schema.db"
    EvidenceLedgerRepository(db_path)
    with sqlite3.connect(db_path) as db:
        db.execute("""CREATE TABLE challenge_submissions (
            submission_id TEXT PRIMARY KEY, challenge_id TEXT NOT NULL, challenge_version TEXT NOT NULL,
            profile_id TEXT NOT NULL, age_band TEXT NOT NULL, output TEXT NOT NULL,
            rubric_results_json TEXT NOT NULL, objective_score INTEGER, objective_max_score INTEGER,
            evidence_status TEXT NOT NULL, reflections_json TEXT NOT NULL, evidence_id TEXT,
            created_at TEXT NOT NULL, FOREIGN KEY(profile_id) REFERENCES student_profiles(profile_id) ON DELETE CASCADE)""")
    migrated = ChallengeRepository(db_path)
    with migrated.evidence._connect() as db:
        columns = {row["name"]: row for row in db.execute("PRAGMA table_info(challenge_submissions)")}
    assert "user_interpretation" in columns
    assert columns["user_interpretation"]["notnull"] == 1
