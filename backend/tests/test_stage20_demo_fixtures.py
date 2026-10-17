"""Stage 20: reproducible age-mode demo fixtures and one live local evidence-loop scenario."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app
from app.services.database import database_status, initialize_database
from app.services.challenges import ChallengeRepository
from app.services.discovery_loop import DiscoveryLoopRepository
from app.services.evidence_ledger import EvidenceLedgerRepository


def test_stage20_demo_fixture_seeding_is_idempotent_and_covers_all_age_modes(tmp_path):
    path = tmp_path / "stage20-demo.db"
    first = initialize_database(path, seed_demo=True)
    first_status = database_status(path)
    second = initialize_database(path, seed_demo=True)
    second_status = database_status(path)

    assert first["demo_fixture"]["fixture_count"] == 3
    assert second["demo_fixture"]["fixture_count"] == 3
    assert first_status["status"] == second_status["status"] == "ready"
    assert len(first_status["demo_fixtures"]) == 3
    assert {row["age_band"] for row in first_status["demo_fixtures"]} == {"10_14", "15_17", "18_plus"}
    assert all(row["synthetic"] is True and row["data_classification"] == "synthetic_demo" for row in first_status["demo_fixtures"])
    before = {row["fixture_id"]: (row["profile_id"], row["evidence_count"], row["challenge_submission_count"]) for row in first_status["demo_fixtures"]}
    after = {row["fixture_id"]: (row["profile_id"], row["evidence_count"], row["challenge_submission_count"]) for row in second_status["demo_fixtures"]}
    assert before == after
    assert next(row for row in first_status["demo_fixtures"] if row["age_band"] == "15_17")["challenge_submission_count"] == 0


def test_stage20_live_demo_path_completes_challenge_updates_ledger_and_changes_next_step(tmp_path, monkeypatch):
    path = tmp_path / "stage20-live-demo.db"
    initialize_database(path, seed_demo=True)
    status = database_status(path)
    teen = next(row for row in status["demo_fixtures"] if row["age_band"] == "15_17")
    challenge_repo = ChallengeRepository(path)
    discovery_repo = DiscoveryLoopRepository(path)
    evidence_repo = EvidenceLedgerRepository(path)
    monkeypatch.setattr("app.api.challenges.repo", lambda: challenge_repo)
    monkeypatch.setattr("app.api.discovery_loop.repo", lambda: discovery_repo)
    monkeypatch.setattr("app.api.student_evidence.get_repository", lambda: evidence_repo)
    client = TestClient(app)

    before = client.get(f"/api/discovery-loop/{teen['profile_id']}?preference=balanced")
    assert before.status_code == 200, before.text
    before_body = before.json()
    challenge_id = before_body["next_challenge"]["challenge_id"]
    challenge_response = client.get(f"/api/challenges/{challenge_id}")
    assert challenge_response.status_code == 200, challenge_response.text
    challenge = challenge_response.json()
    observations = [
        {"criterion_id": item["criterion_id"], "score": min(1, item["max_score"]),
         "observation": f"SYNTHETIC TEST ONLY: observed example for {item['label']}."}
        for item in challenge["rubric"]
    ]
    submitted = client.post(f"/api/challenges/{challenge_id}/submissions", json={
        "profile_id": teen["profile_id"],
        "output": "SYNTHETIC TEST ONLY: example challenge output.",
        "rubric_observations": observations,
        "enjoyment": 4, "difficulty_reported": 3, "confidence": 3, "willingness_to_continue": 4,
        "reflection": "SYNTHETIC TEST ONLY: liked the activity and would like a different follow-on task.",
        "hypothesis_interpretation": "contextual_or_mixed",
    })
    assert submitted.status_code == 200, submitted.text
    after = client.get(f"/api/discovery-loop/{teen['profile_id']}?preference=balanced")
    assert after.status_code == 200, after.text
    after_body = after.json()
    summary = client.get(f"/api/student-profiles/{teen['profile_id']}/summary")
    assert summary.status_code == 200, summary.text
    assert submitted.json()["evidence_created_id"]
    assert after_body["evidence_count"] == before_body["evidence_count"] + 1
    assert after_body["total_submissions"] == before_body["total_submissions"] + 1
    assert after_body["next_challenge"]["challenge_id"] != challenge_id
    assert after_body["what_changed"]
    assert after_body["next_challenge"]["why_this_now"]
