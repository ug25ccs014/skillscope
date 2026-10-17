from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.evidence_ledger import EvidenceLedgerRepository


@pytest.fixture
def evidence_client(tmp_path, monkeypatch):
    repo = EvidenceLedgerRepository(tmp_path / "evidence-test.db")
    monkeypatch.setattr("app.api.student_evidence.get_repository", lambda: repo)
    return TestClient(app), repo


def create_adult_profile(client: TestClient, **extra):
    body = {
        "age_band": "18_plus",
        "consent_basis": "student_confirmed",
        "consent_confirmed": True,
    }
    body.update(extra)
    response = client.post("/api/student-profiles", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def create_minor_profile(client: TestClient, **extra):
    body = {
        "age_band": "15_17",
        "consent_basis": "guardian_confirmed",
        "consent_confirmed": True,
    }
    body.update(extra)
    response = client.post("/api/student-profiles", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def add_interest(client: TestClient, profile_id: str, *, interpretation="not_interpreted", title="Interested in design"):
    return client.post(
        f"/api/student-profiles/{profile_id}/evidence",
        json={
            "evidence_type": "stated_interest_goal",
            "signal_dimension": "interest",
            "title": title,
            "observation": "Student says they want to try visual design tasks.",
            "source_kind": "self_report",
            "uncertainty": "medium",
            "user_interpretation": interpretation,
            "reported_curiosity": 4,
        },
    )


def test_profile_requires_age_appropriate_consent(evidence_client):
    client, _ = evidence_client
    adult_wrong_basis = client.post("/api/student-profiles", json={
        "age_band": "18_plus", "consent_basis": "guardian_confirmed", "consent_confirmed": True,
    })
    assert adult_wrong_basis.status_code == 422
    minor_without_confirmation = client.post("/api/student-profiles", json={
        "age_band": "10_14", "consent_basis": "guardian_confirmed", "consent_confirmed": False,
    })
    assert minor_without_confirmation.status_code == 422
    minor_with_student_consent = client.post("/api/student-profiles", json={
        "age_band": "15_17", "consent_basis": "student_confirmed", "consent_confirmed": True,
    })
    assert minor_with_student_consent.status_code == 422
    assert client.get("/api/student-profiles/00000000-0000-0000-0000-000000000001").status_code == 404


def test_new_profile_summary_treats_missing_evidence_as_unknown_not_zero(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    response = client.get(f"/api/student-profiles/{profile['profile_id']}/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["overall_status"] == "unknown"
    assert body["evidence_count"] == 0
    assert len(body["signals"]) == 7
    for signal in body["signals"]:
        assert signal["status"] == "unknown"
        assert "Unknown—not zero" in signal["explanation"]
        assert signal["evidence_count"] == 0
        assert "score" not in signal


def test_add_evidence_records_context_source_uncertainty_consent_and_timestamp(evidence_client):
    client, _ = evidence_client
    profile = create_minor_profile(client)
    response = add_interest(client, profile["profile_id"])
    assert response.status_code == 201, response.text
    item = response.json()
    assert item["profile_id"] == profile["profile_id"]
    assert item["consent_basis_at_capture"] == "guardian_confirmed"
    assert item["source_kind"] == "self_report"
    assert item["uncertainty"] == "medium"
    assert item["observed_at"].endswith("Z") or "+00:00" in item["observed_at"]
    assert item["recorded_at"]
    assert item["updated_at"]


def test_summary_lists_recent_evidence_and_keeps_other_signals_unknown(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    created = add_interest(client, profile["profile_id"])
    assert created.status_code == 201
    summary = client.get(f"/api/student-profiles/{profile['profile_id']}/summary").json()
    interest = next(s for s in summary["signals"] if s["signal_dimension"] == "interest")
    performance = next(s for s in summary["signals"] if s["signal_dimension"] == "demonstrated_performance")
    assert summary["overall_status"] == "evidence_available"
    assert interest["status"] == "evidence_available"
    assert interest["evidence_count"] == 1
    assert interest["recent_evidence"][0]["title"] == "Interested in design"
    assert interest["recent_evidence"][0]["recency"] == "recent"
    assert performance["status"] == "unknown"
    assert performance["evidence_count"] == 0


def test_user_labelled_supporting_and_challenging_evidence_stays_mixed(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    assert add_interest(client, profile["profile_id"], interpretation="supports_current_hypothesis").status_code == 201
    assert add_interest(client, profile["profile_id"], interpretation="challenges_current_hypothesis", title="Design may not be a fit").status_code == 201
    summary = client.get(f"/api/student-profiles/{profile['profile_id']}/summary").json()
    interest = next(s for s in summary["signals"] if s["signal_dimension"] == "interest")
    assert interest["status"] == "mixed"
    assert interest["interpretation_counts"]["supports_current_hypothesis"] == 1
    assert interest["interpretation_counts"]["challenges_current_hypothesis"] == 1
    assert "open question" in interest["explanation"]


def test_challenge_performance_requires_named_rubric_and_criterion_observation(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    invalid = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json={
        "evidence_type": "challenge_performance", "signal_dimension": "demonstrated_performance",
        "title": "Challenge result", "observation": "Finished a puzzle", "source_kind": "challenge_result",
    })
    assert invalid.status_code == 422
    valid = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json={
        "evidence_type": "challenge_performance", "signal_dimension": "demonstrated_performance",
        "title": "Data reasoning challenge", "observation": "Completed the activity and checked one assumption.",
        "source_kind": "challenge_result", "challenge_label": "Small data puzzle",
        "rubric_name": "Reasoning rubric", "rubric_version": "1.0",
        "rubric_observations": [{"criterion": "Explain the approach", "observation": "Gave a clear sequence of steps", "score": 3, "score_scale": "0-4"}],
        "reported_effort": 3, "reported_difficulty": 2, "reported_enjoyment": 4,
    })
    assert valid.status_code == 201, valid.text
    assert valid.json()["rubric_observations"][0]["score_scale"] == "0-4"
    assert valid.json()["reported_difficulty"] == 2


def test_numeric_rubric_score_without_scale_is_rejected(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    response = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json={
        "evidence_type": "challenge_performance", "signal_dimension": "demonstrated_performance",
        "title": "Challenge result", "observation": "Observed one result", "source_kind": "challenge_result",
        "challenge_label": "Reasoning task", "rubric_name": "Criteria v1",
        "rubric_observations": [{"criterion": "Reasoning", "observation": "Gave a reason", "score": 3}],
    })
    assert response.status_code == 422


def test_repeated_behavior_requires_in_product_source_and_context(evidence_client):
    client, _ = evidence_client
    profile = create_minor_profile(client)
    base = {
        "evidence_type": "repeated_in_product_behavior", "signal_dimension": "interest",
        "title": "Returned to science tasks", "observation": "Repeated voluntary returns during this session.",
        "source_kind": "in_product_behavior",
    }
    missing_context = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json=base)
    assert missing_context.status_code == 422
    complete_context = {**base, "context": {"activity_name": "science mini-task", "time_window": "this session"}}
    without_item_consent = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json=complete_context)
    assert without_item_consent.status_code == 422
    valid = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json={**complete_context, "behavior_consent_confirmed": True})
    assert valid.status_code == 201, valid.text
    assert valid.json()["context"]["activity_name"] == "science mini-task"
    assert valid.json()["context"]["time_window"] == "this session"
    assert valid.json()["behavior_consent_confirmed"] is True
    assert valid.json()["behavior_consent_confirmed_at"] is not None
    assert valid.json()["consent_confirmed_at_capture"] is not None
    assert valid.json()["consent_notice_version_at_capture"] == "student-evidence-v1.0"


def test_repeated_behavior_cannot_be_mislabelled_as_self_report(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    response = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json={
        "evidence_type": "repeated_in_product_behavior", "signal_dimension": "interest",
        "title": "Returned to tasks", "observation": "Contextual behavior", "source_kind": "self_report",
        "context": {"activity": "design task"},
    })
    assert response.status_code == 422


def test_profile_and_evidence_can_be_corrected_without_losing_original_recorded_time(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    created = add_interest(client, profile["profile_id"])
    item = created.json()
    changed_profile = client.patch(f"/api/student-profiles/{profile['profile_id']}", json={"current_goal": "Explore interaction design"})
    assert changed_profile.status_code == 200
    assert changed_profile.json()["current_goal"] == "Explore interaction design"
    corrected = client.patch(f"/api/student-profiles/{profile['profile_id']}/evidence/{item['evidence_id']}", json={
        "title": "Corrected interest statement", "observation": "Student prefers to test interaction design next.",
    })
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["title"] == "Corrected interest statement"
    assert corrected.json()["recorded_at"] == item["recorded_at"]
    assert corrected.json()["observation"] == "Student prefers to test interaction design next."


def test_evidence_patch_revalidates_cross_field_rules(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    item = add_interest(client, profile["profile_id"]).json()
    result = client.patch(f"/api/student-profiles/{profile['profile_id']}/evidence/{item['evidence_id']}", json={"evidence_type": "challenge_performance"})
    assert result.status_code == 422


def test_evidence_list_filters_and_paginates(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    assert add_interest(client, profile["profile_id"]).status_code == 201
    assert add_interest(client, profile["profile_id"], title="Another stated interest").status_code == 201
    page = client.get(f"/api/student-profiles/{profile['profile_id']}/evidence?signal_dimension=interest&limit=1&offset=1")
    assert page.status_code == 200
    assert page.json()["count"] == 2
    assert len(page.json()["items"]) == 1
    assert page.json()["offset"] == 1
    absent = client.get(f"/api/student-profiles/{profile['profile_id']}/evidence?signal_dimension=demonstrated_performance")
    assert absent.json()["count"] == 0


def test_profile_age_band_correction_requires_fresh_appropriate_consent(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    no_consent = client.patch(f"/api/student-profiles/{profile['profile_id']}", json={"age_band": "15_17"})
    assert no_consent.status_code == 422
    wrong_basis = client.patch(f"/api/student-profiles/{profile['profile_id']}", json={
        "age_band": "15_17", "consent_confirmed": True, "consent_basis": "student_confirmed",
    })
    assert wrong_basis.status_code == 422
    corrected = client.patch(f"/api/student-profiles/{profile['profile_id']}", json={
        "age_band": "15_17", "consent_confirmed": True, "consent_basis": "guardian_confirmed",
    })
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["age_band"] == "15_17"
    assert corrected.json()["consent_basis"] == "guardian_confirmed"


def test_crossing_minor_adult_boundary_with_history_requires_delete_and_recreate(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    assert add_interest(client, profile["profile_id"]).status_code == 201
    attempted = client.patch(f"/api/student-profiles/{profile['profile_id']}", json={
        "age_band": "15_17", "consent_confirmed": True, "consent_basis": "guardian_confirmed",
    })
    assert attempted.status_code == 422
    assert "delete this profile and recreate" in attempted.json()["detail"]
    persisted = client.get(f"/api/student-profiles/{profile['profile_id']}")
    assert persisted.json()["age_band"] == "18_plus"
    assert client.get(f"/api/student-profiles/{profile['profile_id']}/evidence").json()["count"] == 1


def test_clear_evidence_retains_profile_but_delete_profile_permanently_cascades(evidence_client):
    client, repo = evidence_client
    profile = create_adult_profile(client, current_goal="Explore design", self_reported_context="Tried a few web projects")
    item = add_interest(client, profile["profile_id"]).json()
    cleared = client.delete(f"/api/student-profiles/{profile['profile_id']}/evidence")
    assert cleared.status_code == 200
    assert cleared.json() == {"deleted_count": 2, "profile_retained": True, "deletion": "permanent"}
    assert client.get(f"/api/student-profiles/{profile['profile_id']}/summary").json()["overall_status"] == "unknown"
    empty_profile = client.get(f"/api/student-profiles/{profile['profile_id']}").json()
    assert empty_profile["current_goal"] is None
    assert empty_profile["self_reported_context"] is None
    # Recreate evidence to verify whole-profile deletion + database ON DELETE CASCADE.
    item2 = add_interest(client, profile["profile_id"]).json()
    deleted = client.delete(f"/api/student-profiles/{profile['profile_id']}")
    assert deleted.status_code == 200
    assert deleted.json()["evidence_deleted_by_cascade"] is True
    assert client.get(f"/api/student-profiles/{profile['profile_id']}").status_code == 404
    assert repo.get_evidence(profile["profile_id"], item2["evidence_id"]) is None
    assert repo.get_evidence(profile["profile_id"], item["evidence_id"]) is None


def test_evidence_cannot_be_read_or_deleted_through_another_profile(evidence_client):
    client, _ = evidence_client
    p1 = create_adult_profile(client)
    p2 = create_adult_profile(client, current_goal="Explore engineering")
    item = add_interest(client, p1["profile_id"]).json()
    other_read = client.patch(f"/api/student-profiles/{p2['profile_id']}/evidence/{item['evidence_id']}", json={"title": "Cross-profile edit"})
    assert other_read.status_code == 404
    other_delete = client.delete(f"/api/student-profiles/{p2['profile_id']}/evidence/{item['evidence_id']}")
    assert other_delete.status_code == 404
    assert client.get(f"/api/student-profiles/{p1['profile_id']}/evidence").json()["count"] == 1


def test_naive_and_future_observed_timestamps_are_rejected(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    base = {
        "evidence_type": "stated_interest_goal", "signal_dimension": "interest", "title": "Interest",
        "observation": "Trying a new domain", "source_kind": "self_report",
    }
    naive = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json={**base, "observed_at": "2026-10-17T12:00:00"})
    assert naive.status_code == 422
    future = (datetime.now(UTC) + timedelta(days=2)).isoformat()
    too_future = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json={**base, "observed_at": future})
    assert too_future.status_code == 422


def test_source_identity_and_user_interpretation_remain_explicit(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    response = add_interest(client, profile["profile_id"], interpretation="contextual_or_mixed")
    assert response.status_code == 201
    item = response.json()
    assert item["source_kind"] == "self_report"
    assert item["user_interpretation"] == "contextual_or_mixed"
    assert item["consent_basis_at_capture"] == "student_confirmed"
    assert item["context"] == {}


def test_project_and_academic_evidence_keep_separate_source_kinds(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client)
    project = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json={
        "evidence_type": "project_portfolio", "signal_dimension": "experience_exposure", "title": "Built a small website",
        "observation": "Added a voluntary project summary.", "source_kind": "user_added_project",
        "source_reference": "https://example.com/portfolio", "uncertainty": "medium",
    })
    academic = client.post(f"/api/student-profiles/{profile['profile_id']}/evidence", json={
        "evidence_type": "academic_experience", "signal_dimension": "learning_progress", "title": "Course reflection",
        "observation": "Student says recent lessons made loops clearer.", "source_kind": "academic_self_report",
    })
    assert project.status_code == 201, project.text
    assert academic.status_code == 201, academic.text
    assert project.json()["source_kind"] == "user_added_project"
    assert academic.json()["source_kind"] == "academic_self_report"


def test_rejected_unconsented_profile_does_not_create_database_row(evidence_client):
    client, repo = evidence_client
    response = client.post("/api/student-profiles", json={
        "age_band": "10_14", "consent_basis": "guardian_confirmed", "consent_confirmed": False,
    })
    assert response.status_code == 422
    with repo._connect() as db:
        assert db.execute("SELECT COUNT(*) AS n FROM student_profiles").fetchone()["n"] == 0


def test_sqlite_foreign_key_cascade_removes_evidence(evidence_client):
    client, repo = evidence_client
    profile = create_minor_profile(client)
    assert add_interest(client, profile["profile_id"]).status_code == 201
    assert repo.delete_profile(profile["profile_id"])
    with repo._connect() as db:
        assert db.execute("SELECT COUNT(*) AS n FROM student_evidence_items").fetchone()["n"] == 0


def test_profile_goal_is_timestamped_and_goal_changes_preserve_history(evidence_client):
    client, _ = evidence_client
    profile = create_adult_profile(client, current_goal="Try user-interface design")
    initial = client.get(f"/api/student-profiles/{profile['profile_id']}/evidence?signal_dimension=goal_preference")
    assert initial.status_code == 200
    assert initial.json()["count"] == 1
    assert initial.json()["items"][0]["title"] == "Initial stated goal"
    assert initial.json()["items"][0]["context"]["capture"] == "profile_creation"

    corrected = client.patch(f"/api/student-profiles/{profile['profile_id']}", json={"current_goal": "Compare design and research"})
    assert corrected.status_code == 200
    history = client.get(f"/api/student-profiles/{profile['profile_id']}/evidence?signal_dimension=goal_preference").json()
    assert history["count"] == 2
    observations = [entry["observation"] for entry in history["items"]]
    assert any("Try user-interface design" in observation for observation in observations)
    assert any("Compare design and research" in observation for observation in observations)
    assert all(entry["source_kind"] == "self_report" for entry in history["items"])


def test_cors_preflight_allows_frontend_correction_and_deletion(evidence_client):
    client, _ = evidence_client
    for method in ("PATCH", "DELETE"):
        response = client.options(
            "/api/student-profiles/00000000-0000-0000-0000-000000000001",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "content-type",
            },
        )
        assert response.status_code == 200
        allowed = response.headers.get("access-control-allow-methods", "")
        assert method in allowed
