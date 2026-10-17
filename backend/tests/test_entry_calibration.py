"""Contract and branch tests for Stage 3 entry calibration."""

from fastapi.testclient import TestClient
import pytest

from app.main import app
from app.schemas.calibration import (
    AgeMode,
    CalibrationRequest,
    EvidenceStrength,
    StartingPath,
)
from app.services.entry_calibration import calibrate_entry

client = TestClient(app)


def test_child_uses_discover_and_shape_without_career_labelling() -> None:
    result = calibrate_entry(CalibrationRequest(age=12))

    assert result.age_band.value == "10-14"
    assert result.age_mode is AgeMode.DISCOVER_AND_SHAPE
    assert result.starting_path is StartingPath.GUIDED_EXPLORATION
    assert result.evidence_strength is EvidenceStrength.NONE
    assert any("not that the user has low ability" in reason for reason in result.rationale)
    assert "never determines" not in result.next_step.lower()


def test_teen_late_entrant_with_low_data_starts_with_baseline_discovery() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=16,
            career_clarity="low",
            prior_evidence_count=0,
            exploration_need="high",
        )
    )

    assert result.age_mode is AgeMode.EXPLORE_AND_VALIDATE
    assert result.starting_path is StartingPath.BASELINE_DISCOVERY
    assert result.evidence_strength is EvidenceStrength.NONE


def test_teen_with_clear_goal_but_no_evidence_gets_goal_validation_not_gap_analysis() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=16,
            career_clarity="high",
            current_goal="software engineering",
            prior_evidence_count=0,
        )
    )

    assert result.starting_path is StartingPath.VALIDATE_DECLARED_INTEREST
    assert result.evidence_strength is EvidenceStrength.NONE
    assert "practical project" in result.next_step.lower()


def test_teen_with_conflicting_signals_broadens_exploration() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=17,
            career_clarity="high",
            current_goal="medicine",
            contradictory_evidence=True,
        )
    )

    assert result.starting_path is StartingPath.BROADEN_EXPLORATION
    assert any("conflicting signals" in reason for reason in result.rationale)


def test_teen_goal_change_resets_to_baseline_discovery() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=15,
            career_clarity="high",
            current_goal="environmental science",
            career_goal_changed=True,
            prior_evidence_count=10,
            prior_evidence_quality="high",
            prior_projects_experience="substantial",
        )
    )

    assert result.starting_path is StartingPath.BASELINE_DISCOVERY
    assert any("goal changed" in reason for reason in result.rationale)


def test_adult_unclear_goal_starts_career_discovery() -> None:
    result = calibrate_entry(CalibrationRequest(age=22, career_clarity="low"))

    assert result.age_band.value == "18+"
    assert result.age_mode is AgeMode.DEVELOP_AND_OPTIMIZE
    assert result.starting_path is StartingPath.CAREER_DISCOVERY


def test_adult_with_clear_goal_and_substantial_relevant_evidence_can_start_gap_analysis() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=22,
            career_clarity="high",
            current_goal="data scientist",
            prior_evidence_count=8,
            prior_evidence_quality="high",
            prior_projects_experience="substantial",
            skills_summary="Python, SQL, statistical modeling, data visualization",
            education_summary="B.Tech in Computer Science",
            exploration_need="low",
        )
    )

    assert result.starting_path is StartingPath.CAREER_GAP_ANALYSIS
    assert result.evidence_strength is EvidenceStrength.SUBSTANTIAL
    assert any("gap review" in reason for reason in result.rationale)


def test_adult_with_clear_goal_but_limited_evidence_validates_goal_first() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=25,
            career_clarity="high",
            current_goal="UX designer",
            prior_evidence_count=2,
            prior_evidence_quality="high",
            prior_projects_experience="some",
        )
    )

    assert result.starting_path is StartingPath.CAREER_GOAL_VALIDATION
    assert result.evidence_strength is EvidenceStrength.LIMITED


def test_adult_conflicting_evidence_avoids_automatic_gap_analysis() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=30,
            career_clarity="high",
            current_goal="product manager",
            prior_evidence_count=12,
            prior_evidence_quality="high",
            prior_projects_experience="substantial",
            contradictory_evidence=True,
        )
    )

    assert result.starting_path is StartingPath.CAREER_DISCOVERY


def test_adult_can_reenter_discovery_even_with_strong_prior_evidence() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=28,
            career_clarity="high",
            current_goal="data scientist",
            prior_evidence_count=12,
            prior_evidence_quality="high",
            prior_projects_experience="substantial",
            reenter_discovery=True,
        )
    )

    assert result.starting_path is StartingPath.REENTER_DISCOVERY
    assert any("fresh discovery cycle" in reason for reason in result.rationale)


def test_changed_adult_goal_is_validated_before_optimisation() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=24,
            career_clarity="high",
            current_goal="public policy analyst",
            prior_evidence_count=12,
            prior_evidence_quality="high",
            prior_projects_experience="substantial",
            career_goal_changed=True,
        )
    )

    assert result.starting_path is StartingPath.CAREER_GOAL_VALIDATION


def test_explicit_journey_preference_is_respected_with_age_appropriate_mapping() -> None:
    adult = calibrate_entry(
        CalibrationRequest(age=26, career_clarity="high", current_goal="designer", journey_preference="explore")
    )
    child = calibrate_entry(
        CalibrationRequest(age=12, career_clarity="high", current_goal="designer", journey_preference="optimize")
    )

    assert adult.starting_path is StartingPath.CAREER_DISCOVERY
    assert child.age_mode is AgeMode.DISCOVER_AND_SHAPE
    assert child.starting_path is StartingPath.GUIDED_EXPLORATION
    assert any("translated into safe" in reason for reason in child.rationale)


def test_evidence_thresholds_measure_coverage_not_ability() -> None:
    limited = calibrate_entry(
        CalibrationRequest(age=20, prior_evidence_count=2, prior_evidence_quality="high")
    )
    emerging = calibrate_entry(
        CalibrationRequest(age=20, prior_evidence_count=4, prior_evidence_quality="medium")
    )
    substantial = calibrate_entry(
        CalibrationRequest(age=20, prior_evidence_count=6, prior_evidence_quality="high")
    )

    assert limited.evidence_strength is EvidenceStrength.LIMITED
    assert emerging.evidence_strength is EvidenceStrength.EMERGING
    assert substantial.evidence_strength is EvidenceStrength.SUBSTANTIAL
    assert "estimate of ability" in substantial.limitations[0].lower()


def test_current_goal_is_normalized_and_blank_goal_becomes_none() -> None:
    normalized = CalibrationRequest(age=20, current_goal="  data   science  ")
    blank = CalibrationRequest(age=20, current_goal="   ")

    assert normalized.current_goal == "data science"
    assert blank.current_goal is None


def test_calibration_http_endpoint_returns_explainable_contract() -> None:
    response = client.post(
        "/api/calibration",
        json={"age": 16, "career_clarity": "low", "prior_evidence_count": 0},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["age_band"] == "15-17"
    assert body["age_mode"] == "explore_and_validate"
    assert body["starting_path"] == "baseline_discovery"
    assert body["evidence_strength"] == "none"
    assert body["rationale"]
    assert body["next_step"]
    assert "prior_evidence_quality" in body["considered_inputs"]
    assert body["calibration_version"] == "1.0.0"


def test_calibration_rejects_ages_below_supported_range() -> None:
    for age in (0, 9):
        response = client.post("/api/calibration", json={"age": age})
        assert response.status_code == 422


def test_calibration_rejects_ages_above_supported_range() -> None:
    response = client.post("/api/calibration", json={"age": 101})
    assert response.status_code == 422


def test_calibration_rejects_unknown_fields_instead_of_silently_ignoring_them() -> None:
    response = client.post("/api/calibration", json={"age": 19, "aptitude_score": 99})
    assert response.status_code == 422


def test_calibration_rejects_negative_evidence_count() -> None:
    response = client.post("/api/calibration", json={"age": 19, "prior_evidence_count": -1})
    assert response.status_code == 422


def test_cors_allows_post_from_vite_development_origin() -> None:
    response = client.options(
        "/api/calibration",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


@pytest.mark.parametrize(
    ("age", "expected_band", "expected_mode"),
    [
        (10, "10-14", "discover_and_shape"),
        (14, "10-14", "discover_and_shape"),
        (15, "15-17", "explore_and_validate"),
        (17, "15-17", "explore_and_validate"),
        (18, "18+", "develop_and_optimize"),
        (100, "18+", "develop_and_optimize"),
    ],
)
def test_age_boundaries_are_disjoint_and_complete(
    age: int,
    expected_band: str,
    expected_mode: str,
) -> None:
    result = calibrate_entry(CalibrationRequest(age=age))

    assert result.age_band.value == expected_band
    assert result.age_mode.value == expected_mode


def test_teen_with_high_exploration_need_but_low_clarity_starts_with_baseline() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=16,
            career_clarity="low",
            current_goal="software engineering",
            exploration_need="high",
        )
    )

    assert result.starting_path is StartingPath.BASELINE_DISCOVERY
    assert any("baseline across multiple domains" in reason for reason in result.rationale)


def test_teen_with_clear_goal_and_high_exploration_need_broadens_comparison() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=16,
            career_clarity="high",
            current_goal="software engineering",
            exploration_need="high",
        )
    )

    assert result.starting_path is StartingPath.BROADEN_EXPLORATION
    assert any("high need for exploration" in reason for reason in result.rationale)


def test_adult_with_goal_change_and_conflicting_signals_reopens_discovery() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=29,
            career_clarity="high",
            current_goal="product design",
            prior_evidence_count=8,
            prior_evidence_quality="high",
            prior_projects_experience="substantial",
            career_goal_changed=True,
            contradictory_evidence=True,
        )
    )

    assert result.starting_path is StartingPath.CAREER_DISCOVERY
    assert any("goal changed and signals conflict" in reason for reason in result.rationale)


def test_age_mode_stays_age_appropriate_when_user_selects_optimisation() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=13,
            career_clarity="high",
            current_goal="robotics",
            journey_preference="optimize",
        )
    )

    assert result.age_mode is AgeMode.DISCOVER_AND_SHAPE
    assert result.starting_path is StartingPath.GUIDED_EXPLORATION
    assert any("translated into safe" in reason for reason in result.rationale)



def test_adult_high_evidence_without_current_skill_context_stays_in_goal_validation() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=25,
            career_clarity="high",
            current_goal="data analyst",
            prior_evidence_count=8,
            prior_evidence_quality="high",
            prior_projects_experience="substantial",
            exploration_need="low",
        )
    )

    assert result.starting_path is StartingPath.CAREER_GOAL_VALIDATION
    assert any("do not justify skipping directly to gap analysis" in reason for reason in result.rationale)


def test_unexplored_domains_are_used_to_broaden_teen_exploration() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=16,
            career_clarity="high",
            current_goal="software engineering",
            unexplored_domains=["business_entrepreneurship", "creative_design"],
        )
    )

    assert result.starting_path is StartingPath.BROADEN_EXPLORATION
    assert "business and entrepreneurship" in result.next_step
    assert "creative design" in result.next_step
    assert any("not areas of weakness" in reason for reason in result.rationale)
    assert any("identified areas you have not yet tried" in reason for reason in result.rationale)


def test_unexplored_domains_are_deduplicated_and_blank_adult_context_normalized() -> None:
    request = CalibrationRequest(
        age=22,
        unexplored_domains=["creative_design", "creative_design", "health_wellbeing"],
        education_summary="  B.Tech    Computer Science ",
        skills_summary="   ",
        experience_summary="  Capstone   project  ",
        planning_constraints="  5 hours per week ",
        desired_timeline="3_to_6_months",
    )
    result = calibrate_entry(request)

    assert [domain.value for domain in request.unexplored_domains] == ["creative_design", "health_wellbeing"]
    assert request.education_summary == "B.Tech Computer Science"
    assert request.skills_summary is None
    assert request.experience_summary == "Capstone project"
    assert request.planning_constraints == "5 hours per week"
    assert result.starting_path is StartingPath.CAREER_DISCOVERY
    assert any("education/training" in reason for reason in result.rationale)
    assert any("3–6 months" in reason for reason in result.rationale)


def test_unexplored_domains_with_no_goal_are_opportunities_not_negative_signals() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=12,
            unexplored_domains=["science_experimentation"],
        )
    )

    assert result.starting_path is StartingPath.GUIDED_EXPLORATION
    assert "science and experimentation" in result.next_step
    assert any("not areas of weakness" in reason for reason in result.rationale)


def test_adult_optional_context_is_not_echoed_back_verbatim() -> None:
    secretish_but_non_sensitive_context = "I can study for six hours a week"
    result = calibrate_entry(
        CalibrationRequest(
            age=28,
            career_clarity="medium",
            current_goal="product analyst",
            planning_constraints=secretish_but_non_sensitive_context,
        )
    )

    assert secretish_but_non_sensitive_context not in " ".join(result.rationale)
    assert any("planning constraints were supplied" in reason for reason in result.rationale)


def test_unquantified_activity_summary_counts_as_limited_context_not_zero_knowledge() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=16,
            prior_evidence_count=0,
            prior_activity_summary="Built a paper bridge and made a simple webpage",
        )
    )

    assert result.evidence_strength is EvidenceStrength.LIMITED
    assert any("without a numeric count" in reason for reason in result.rationale)
    assert any("not independently verified" in reason for reason in result.rationale)


def test_prior_activity_summary_is_not_echoed_back_verbatim() -> None:
    activity_summary = "Volunteered for a community clean-up and made a small game"
    result = calibrate_entry(
        CalibrationRequest(age=17, prior_activity_summary=activity_summary)
    )

    combined_rationale = " ".join(result.rationale)
    assert activity_summary not in combined_rationale
    assert any("summary of activities already tried was supplied" in reason for reason in result.rationale)


def test_too_many_unexplored_domains_are_rejected() -> None:
    domains = [
        "creative_design",
        "analytical_logic",
        "hands_on_making",
        "social_collaboration",
        "communication_storytelling",
        "science_experimentation",
        "technology_computing",
        "environment_sustainability",
        "business_entrepreneurship",
        "health_wellbeing",
        "creative_design",
    ]
    response = client.post(
        "/api/calibration",
        json={"age": 18, "unexplored_domains": domains},
    )
    assert response.status_code == 422



def test_education_alone_does_not_unlock_adult_gap_analysis() -> None:
    result = calibrate_entry(
        CalibrationRequest(
            age=26,
            career_clarity="high",
            current_goal="data scientist",
            prior_evidence_count=10,
            prior_evidence_quality="high",
            prior_projects_experience="substantial",
            education_summary="B.Tech Computer Science",
            exploration_need="low",
        )
    )

    assert result.starting_path is StartingPath.CAREER_GOAL_VALIDATION
