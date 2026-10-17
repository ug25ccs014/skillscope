from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.requests import Request

from app.main import (
    _allowed_origins,
    _requires_student_data_gate,
    _safe_route_for_log,
    app,
    unexpected_error_handler,
)
from app.schemas.student_evidence import AgeBand, ConsentBasis, StudentProfileCreate
from app.services.database import connect_sqlite, initialize_database
from app.services.evidence_ledger import EvidenceLedgerRepository


def _valid_profile_payload(**overrides):
    payload = {
        "age_band": "18_plus",
        "consent_basis": "student_confirmed",
        "consent_confirmed": True,
    }
    payload.update(overrides)
    return payload


@pytest.fixture
def privacy_client(tmp_path, monkeypatch):
    repo = EvidenceLedgerRepository(tmp_path / "stage18-evidence.db")
    monkeypatch.setattr("app.api.student_evidence.get_repository", lambda: repo)
    return TestClient(app), repo


def test_profile_creation_consent_gate_rejects_missing_or_wrong_basis(privacy_client):
    client, repo = privacy_client
    no_consent = client.post("/api/student-profiles", json=_valid_profile_payload(consent_confirmed=False))
    assert no_consent.status_code == 422
    wrong_minor_basis = client.post("/api/student-profiles", json={
        "age_band": "10_14", "consent_basis": "student_confirmed", "consent_confirmed": True,
    })
    assert wrong_minor_basis.status_code == 422
    valid_minor = client.post("/api/student-profiles", json={
        "age_band": "10_14", "consent_basis": "guardian_confirmed", "consent_confirmed": True,
    })
    assert valid_minor.status_code == 201, valid_minor.text
    assert valid_minor.json()["consent_notice_version"] == "student-evidence-v1.0"
    with repo._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM student_profiles").fetchone()[0] == 1


def test_email_is_rejected_from_profile_text_without_storage_or_error_echo(privacy_client):
    client, repo = privacy_client
    email = "private.student@example.org"
    response = client.post("/api/student-profiles", json=_valid_profile_payload(current_goal=f"Please contact me at {email}"))
    assert response.status_code == 422
    assert email not in response.text
    assert "input" not in response.text.lower()
    with repo._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM student_profiles").fetchone()[0] == 0


def test_phone_or_long_numeric_identifier_is_rejected_from_evidence_and_not_saved(privacy_client):
    client, repo = privacy_client
    profile = client.post("/api/student-profiles", json=_valid_profile_payload()).json()
    profile_id = profile["profile_id"]
    response = client.post(f"/api/student-profiles/{profile_id}/evidence", json={
        "evidence_type": "stated_interest_goal", "signal_dimension": "interest",
        "title": "Design curiosity", "observation": "Call me at +91 98765 43210",
        "source_kind": "self_report",
    })
    assert response.status_code == 422
    assert "+91 98765 43210" not in response.text
    with repo._connect() as db:
        assert db.execute("SELECT COUNT(*) FROM student_evidence_items").fetchone()[0] == 0


def test_nested_context_and_calibration_text_use_direct_identifier_guard():
    from pydantic import ValidationError
    from app.schemas.calibration import CalibrationRequest
    from app.schemas.student_evidence import EvidenceCreate

    with pytest.raises(ValidationError):
        CalibrationRequest(age=16, current_goal="My email is person@example.org")
    with pytest.raises(ValidationError):
        EvidenceCreate(
            evidence_type="stated_interest_goal", signal_dimension="interest", title="Interest",
            observation="I tried a project", source_kind="self_report", context={"note": "Call 9876543210"},
        )


def test_extra_fields_and_out_of_range_inputs_are_rejected():
    from pydantic import ValidationError
    from app.schemas.challenges import ChallengeSubmission
    from app.schemas.student_evidence import EvidenceCreate

    with pytest.raises(ValidationError):
        EvidenceCreate(
            evidence_type="stated_interest_goal", signal_dimension="interest", title="Interest",
            observation="I want to try this", source_kind="self_report", inferred_caste="unknown",
        )
    with pytest.raises(ValidationError):
        ChallengeSubmission(
            profile_id="00000000-0000-4000-8000-000000000001", output="Example output",
            rubric_observations=[{"criterion_id": "explain", "observation": "Explained"}], enjoyment=9,
        )


def test_profile_delete_cascades_all_profile_scoped_tables(tmp_path):
    db_path = tmp_path / "stage18-cascade.db"
    initialize_database(db_path, seed_demo=False)
    repo = EvidenceLedgerRepository(db_path)
    profile = repo.create_profile(StudentProfileCreate(
        age_band=AgeBand.AGE_18_PLUS, consent_basis=ConsentBasis.STUDENT_CONFIRMED,
        consent_confirmed=True, current_goal="Explore product design",
    ))
    pid = str(profile.profile_id)
    now = "2026-10-17T12:00:00+00:00"
    with connect_sqlite(db_path) as db:
        db.execute("INSERT INTO student_preferences VALUES(?,?,?,?,?)", (pid, "explore", "[]", "[\"text\"]", now))
        db.execute("INSERT INTO recommendation_snapshots VALUES(?,?,?,?,?,?,?,?)", (
            "stage18-snapshot", pid, "test-v1", now, 1, "ready", "[]", "{}",
        ))
        db.execute("INSERT INTO baseline_assessments(assessment_id,profile_id,age_band,mode,version,created_at,status,submitted_at) VALUES(?,?,?,?,?,?,?,?)", (
            "stage18-assessment", pid, "18_plus", "develop_and_optimize", "baseline-test", now, "submitted", now,
        ))
        db.execute("INSERT INTO baseline_responses VALUES(?,?,?,?,?,?)", (
            "stage18-assessment", "q01", 0, "synthetic answer", 3, now,
        ))
        db.execute("INSERT INTO challenge_submissions(submission_id,challenge_id,challenge_version,profile_id,age_band,output,rubric_results_json,objective_score,objective_max_score,evidence_status,reflections_json,evidence_id,created_at,user_interpretation) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (
            "stage18-submission", "pattern-detective", "v1", pid, "18_plus", "synthetic output", "[]", 1, 2,
            "partial_evidence", "{}", None, now, "not_interpreted",
        ))
        db.execute("INSERT INTO pathway_plans VALUES(?,?,?,?,?,?,?,?,?)", (
            "stage18-plan", pid, "pathway-test-v1", "Explore product design", "18_plus", 0, now, "{}", "{}",
        ))
        for table in ("student_profiles", "student_evidence_items", "student_preferences", "recommendation_snapshots", "baseline_assessments", "challenge_submissions", "pathway_plans"):
            assert db.execute(f"SELECT COUNT(*) FROM {table} WHERE profile_id=?", (pid,)).fetchone()[0] >= 1, table
        assert db.execute("SELECT COUNT(*) FROM baseline_responses WHERE assessment_id='stage18-assessment'").fetchone()[0] == 1
    assert repo.delete_profile(pid)
    with connect_sqlite(db_path) as db:
        for table in ("student_profiles", "student_evidence_items", "student_preferences", "recommendation_snapshots", "baseline_assessments", "challenge_submissions", "pathway_plans"):
            assert db.execute(f"SELECT COUNT(*) FROM {table} WHERE profile_id=?", (pid,)).fetchone()[0] == 0, table
        assert db.execute("SELECT COUNT(*) FROM baseline_responses WHERE assessment_id='stage18-assessment'").fetchone()[0] == 0


def test_production_mode_fails_closed_for_student_data_but_keeps_public_library(monkeypatch):
    monkeypatch.setenv("SKILLSCOPE_ENV", "production")
    with TestClient(app) as client:
        gated = client.get("/api/student-profiles/00000000-0000-4000-8000-000000000123")
        assert gated.status_code == 503
        assert "authenticated identity" in gated.json()["detail"].lower()
        assert gated.headers["Cache-Control"].startswith("no-store")
        assert gated.headers["X-Content-Type-Options"] == "nosniff"
        assert client.get("/api/challenges").status_code == 200
        assert client.get("/api/health").status_code == 200


def test_production_cors_requires_explicit_https_origins(monkeypatch):
    monkeypatch.setenv("SKILLSCOPE_ENV", "production")
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    assert _allowed_origins() == []
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173,*")
    assert _allowed_origins() == []
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.org,https://admin.example.org/")
    assert _allowed_origins() == ["https://app.example.org", "https://admin.example.org"]


def test_protected_route_classification_includes_personal_write_and_read_paths():
    for path in (
        "/api/student-profiles", "/api/student-profiles/id/evidence", "/api/baseline-assessments/for/id",
        "/api/discovery-loop/id", "/api/recommendations/id/history", "/api/pathway-plans/id/generate",
        "/api/calibration", "/api/challenges/pattern-detective/submissions",
    ):
        assert _requires_student_data_gate(path), path
    assert not _requires_student_data_gate("/api/challenges")
    assert not _requires_student_data_gate("/api/source-registry")


def test_error_logs_redact_route_identifier_and_never_log_exception_contents(caplog):
    profile_id = "private-profile-uuid-12345"
    request = Request({
        "type": "http", "http_version": "1.1", "method": "GET", "scheme": "http",
        "path": f"/api/student-profiles/{profile_id}/evidence", "raw_path": f"/api/student-profiles/{profile_id}/evidence".encode(),
        "query_string": b"", "headers": [], "server": ("testserver", 80), "client": ("testclient", 123), "root_path": "",
    })
    request.state.request_id = "stage18-log-test"
    caplog.set_level(logging.ERROR, logger="skillscope.api")
    asyncio.run(unexpected_error_handler(request, RuntimeError("email private.student@example.org token=very-secret")))
    logged = caplog.text
    assert profile_id not in logged
    assert "private.student@example.org" not in logged
    assert "very-secret" not in logged
    assert "{profile_id}" in logged
    assert "RuntimeError" in logged


def test_public_health_has_security_headers():
    with TestClient(app) as client:
        response = client.get("/api/health")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "camera=()" in response.headers["Permissions-Policy"]
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]
