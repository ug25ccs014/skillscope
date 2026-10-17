"""Acceptance and regression tests for Stage 13 career pathway plans."""
from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.pathway_plans import DesiredTimeline, PlanInput
from app.schemas.recommendations import RecommendationSource, SourcedPathwayFact
from app.schemas.student_evidence import AgeBand, ConsentBasis, StudentProfileCreate
from app.services.evidence_ledger import EvidenceLedgerRepository
from app.services.pathway_plans import PathwayPlanRepository, build_pathway_plan


def source(label: str = "Software Developers") -> RecommendationSource:
    return RecommendationSource(
        source_id="test_onet", source_record_id=f"snapshot:{label.casefold().replace(' ', '-')}",
        title=label, publisher="Synthetic test source", record_uri="https://example.org/record",
        source_version="test-v1", source_type="official", geography="United States",
        quality_status="reviewed", fact_id="test-fact", fact_type="selected_occupational_tasks",
        fact_statement="Synthetic fixture work activity; not a real credential or employment fact.",
        evidence_role="selected_task", notes=["Test-only fixture."],
    )


def recommendation(label: str = "Software Developers", *, category: str = "challenge", domain: str = "technology"):
    src = source(label)
    fact = SourcedPathwayFact(
        fact_kind="source_listed_work_activity",
        statement="Debug or improve a small example program.", source=src,
    )
    return SimpleNamespace(
        hypothesis_id=f"hypothesis:{label.casefold().replace(' ', '-')}",
        hypothesis_label=label, recommendation_type="occupation_hypothesis",
        occupation_node_id=f"occupation:{label.casefold().replace(' ', '-')}",
        occupation=label, taxonomy="O*NET OnLine", geography="United States",
        category=SimpleNamespace(value=category), evidence_confidence=SimpleNamespace(value="low"),
        rationale=["The stated goal and current evidence make this a possibility to test.", "The catalog contains a source-listed work context."],
        matches=[SimpleNamespace(label="Problem solving", match_type="authored_domain_hypothesis")],
        evidence_used=[], evidence_gaps=[SimpleNamespace(label="Different activity contexts", explanation="This hypothesis has not been tested across several activity types.")],
        source_backed_pathway_facts=[fact],
        next_validating_action=SimpleNamespace(
            challenge_id="debug-the-process", title="Debug a Small Process", domain=domain,
            expected_minutes=12, action="Complete the activity and record observable notes.",
            why_this_tests_the_hypothesis="It samples a bounded task associated with this domain.",
        ),
    )


def recommendation_set(profile_id, age: AgeBand, goal: str | None, recs=None):
    recs = recs or [
        recommendation("Software Developers", category="challenge"),
        recommendation("Graphic Designers", category="explore", domain="design_creative"),
        recommendation("Data Analysts", category="alternative_to_consider", domain="logic_data"),
    ]
    return SimpleNamespace(
        profile_id=profile_id, age_band=age, current_goal=goal,
        algorithm_version="transparent-career-match-v1.0", recommendations=recs,
        evidence_count=0, catalog_status="test_fixture",
    )


class FakeRecommendationProvider:
    def __init__(self, repo: EvidenceLedgerRepository):
        self.repo = repo
        self.result_override = None

    def get_recommendations(self, profile_id, *, limit=5):
        profile = self.repo.get_profile(profile_id)
        if self.result_override is not None:
            return self.result_override
        assert profile is not None
        return recommendation_set(profile.profile_id, profile.age_band, profile.current_goal)


def make_profile(repo: EvidenceLedgerRepository, age: AgeBand, goal: str | None = None):
    consent = ConsentBasis.STUDENT_CONFIRMED if age == AgeBand.AGE_18_PLUS else ConsentBasis.GUARDIAN_CONFIRMED
    return repo.create_profile(StudentProfileCreate(
        age_band=age, consent_basis=consent, consent_confirmed=True, current_goal=goal,
    ))


def repo_for(tmp_path, age=AgeBand.AGE_18_PLUS, goal="Explore software development"):
    db_path = tmp_path / "pathways.db"
    evidence = EvidenceLedgerRepository(db_path)
    profile = make_profile(evidence, age, goal)
    provider = FakeRecommendationProvider(evidence)
    cards = [
        {"node_id": "occupation:software-developers", "relationships": [], "skills": [
            {"label": "Critical Thinking", "source_references": [source().model_dump(mode="json")]},
            {"label": "Systems Analysis", "source_references": [source().model_dump(mode="json")]},
        ]},
        {"node_id": "occupation:graphic-designers", "relationships": [], "skills": [
            {"label": "Design", "source_references": [source("Graphic Designers").model_dump(mode="json")]},
        ]},
    ]
    return PathwayPlanRepository(db_path, recommendation_provider=provider, career_provider=lambda **kwargs: cards), evidence, profile, provider


def test_younger_student_gets_one_small_activity_and_no_occupation_labels(tmp_path):
    plans, _, profile, _ = repo_for(tmp_path, AgeBand.AGE_10_14, "I like computers")
    plan = plans.generate(profile.profile_id, PlanInput())
    assert plan is not None
    assert plan.mode == "discover_and_shape"
    assert plan.pathway_options == []
    assert len(plan.actions) == 1
    assert plan.actions[0].action_type == "explore"
    assert not any("software developer" in action.title.casefold() for action in plan.actions)
    assert plan.timebox.status == "not_applicable_age_mode"
    assert "career occupation labels" in " ".join(plan.limitations).casefold()


def test_teen_plan_includes_small_pathway_group_unknowns_and_validation_projects(tmp_path):
    plans, _, profile, _ = repo_for(tmp_path, AgeBand.AGE_15_17, "Explore technology")
    plan = plans.generate(profile.profile_id, PlanInput())
    assert plan is not None
    assert len(plan.pathway_options) == 3
    assert any(option.recommendation_category == "alternative_to_consider" for option in plan.pathway_options)
    assert all(option.what_remains_unknown for option in plan.pathway_options)
    assert all(option.validation_actions for option in plan.pathway_options)
    assert any(step.source_references for option in plan.pathway_options for step in option.validation_actions)
    assert plan.timebox.status == "not_applicable_age_mode"
    assert "salary" in " ".join(plan.limitations).casefold()


def test_adult_timebox_requires_goal_current_state_capacity_and_timeline(tmp_path):
    plans, _, profile, _ = repo_for(tmp_path)
    incomplete = plans.generate(profile.profile_id, PlanInput())
    assert incomplete is not None
    assert incomplete.timebox.status == "missing_inputs"
    assert len(incomplete.timebox.missing_inputs) == 3
    assert all(action.time_horizon_days is None for action in incomplete.actions)

    complete = plans.generate(profile.profile_id, PlanInput(
        current_skills_summary="Python and basic programming", education_summary="Computer science student",
        available_hours_per_week=5, desired_timeline=DesiredTimeline.DAYS_90,
    ))
    assert complete is not None
    assert complete.timebox.status == "time_bounded"
    assert any(action.time_horizon_days == 30 for action in complete.actions)
    assert any(action.time_horizon_days == 60 for action in complete.actions)
    assert any(action.time_horizon_days == 90 for action in complete.actions)
    assert complete.skills_to_check_or_develop
    assert all(gap.status in {"self_reported_in_current_state", "mentioned_in_evidence", "not_yet_documented"} for gap in complete.skills_to_check_or_develop)


def test_skill_gap_absence_is_not_called_a_deficit(tmp_path):
    plans, _, profile, _ = repo_for(tmp_path)
    plan = plans.generate(profile.profile_id, PlanInput(current_skills_summary="Python", education_summary="CS student"))
    assert plan is not None
    gap = next(item for item in plan.skills_to_check_or_develop if item.skill_label == "Critical Thinking")
    assert gap.status == "not_yet_documented"
    assert "not" in gap.explanation.casefold() and "deficit" in gap.explanation.casefold()


def test_goal_edit_recalculates_plan_and_preserves_historical_goal_evidence(tmp_path):
    plans, evidence, profile, provider = repo_for(tmp_path, AgeBand.AGE_18_PLUS, "Software developer")
    initial_evidence, _ = evidence.list_evidence(profile.profile_id)
    initial_goal_records = [item for item in initial_evidence if item.context.get("profile_field") == "current_goal"]
    assert len(initial_goal_records) == 1

    revised = plans.generate(profile.profile_id, PlanInput(current_goal="Explore data analysis"))
    assert revised is not None and revised.goal_change_detected
    assert revised.previous_goal == "Software developer"
    assert revised.current_goal == "Explore data analysis"
    assert "retained" in revised.goal_change_handling.casefold()

    goal_evidence, total = evidence.list_evidence(profile.profile_id, evidence_type=None, limit=200)
    history_items = [item for item in goal_evidence if item.context.get("profile_field") in {"current_goal", None} and item.evidence_type.value == "stated_interest_goal"]
    assert total >= 2
    assert len([item for item in goal_evidence if item.evidence_type.value == "stated_interest_goal"]) >= 2
    history = plans.history(profile.profile_id)
    assert history and history[0].plan_id == revised.plan_id and history[0].goal_change_detected


def test_pathway_plan_history_persists_and_is_deleted_with_profile(tmp_path):
    plans, evidence, profile, _ = repo_for(tmp_path, AgeBand.AGE_15_17, "Explore design")
    first = plans.generate(profile.profile_id, PlanInput())
    second = plans.generate(profile.profile_id, PlanInput(current_goal="Explore engineering"))
    assert first and second
    latest = plans.get_latest(profile.profile_id)
    assert latest and latest.plan_id == second.plan_id
    assert [item.plan_id for item in plans.history(profile.profile_id)] == [second.plan_id, first.plan_id]
    assert evidence.delete_profile(profile.profile_id)
    assert plans.get_latest(profile.profile_id) is None
    assert plans.history(profile.profile_id) is None


def test_minor_profiles_cannot_submit_adult_planning_context(tmp_path):
    plans, _, profile, _ = repo_for(tmp_path, AgeBand.AGE_15_17, "Explore science")
    with pytest.raises(ValueError, match=r"only collected in the 18\+"):
        plans.generate(profile.profile_id, PlanInput(available_hours_per_week=5, desired_timeline="90_days"))


def test_api_creates_plan_and_returns_history(tmp_path, monkeypatch):
    plans, evidence, profile, provider = repo_for(tmp_path, AgeBand.AGE_15_17, "Explore technology")
    monkeypatch.setattr("app.api.pathway_plans.repo", lambda: plans)
    client = TestClient(app)
    response = client.post(f"/api/pathway-plans/{profile.profile_id}/generate", json={})
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["algorithm_version"] == "career-pathway-action-plan-v1.0"
    assert body["actions"]
    latest = client.get(f"/api/pathway-plans/{profile.profile_id}")
    assert latest.status_code == 200, latest.text
    history = client.get(f"/api/pathway-plans/{profile.profile_id}/history")
    assert history.status_code == 200 and len(history.json()) == 1
