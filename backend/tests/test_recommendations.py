from datetime import UTC, datetime, timedelta
import json
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.provenance import QualityStatus, SourceRecord, SourceType
from app.schemas.student_evidence import (
    AgeBand, ConsentBasis, EvidenceCreate, EvidenceSourceKind, EvidenceType,
    SignalDimension, UncertaintyLevel, UserInterpretation,
)
from app.services.challenges import ChallengeRepository
from app.services.recommendations import (
    RecommendationCatalogError, RecommendationRepository,
    build_recommendation_set, load_domain_policy, load_recommendation_policy,
)


def source(source_id="test_onet", label="Software Developers"):
    return {
        "source_id": source_id,
        "source_record_id": f"snapshot:{label.lower().replace(' ', '-')}",
        "title": label,
        "publisher": "Test occupational source",
        "record_uri": "https://example.org/occupations/software",
        "source_version": "test-snapshot-v1",
        "source_type": "official",
        "geography": "United States",
        "quality_status": "reviewed",
        "license_reference": "https://example.org/license",
        "fact_id": "fact:test:one",
        "fact_type": "selected_occupational_tasks",
        "fact_statement": "Test-only task reference, not a real labour-market fact.",
        "evidence_role": "selected_task",
        "notes": ["Synthetic test fixture; not a production source."],
    }


def career(node_id, label, taxonomy, external_id, domain_source=None, skill="Critical Thinking", task=None):
    record = domain_source or source(label=label)
    return {
        "node_id": node_id,
        "node_type": "occupation",
        "label": label,
        "description": "Synthetic test-only source-linked occupation fixture.",
        "taxonomy": taxonomy,
        "external_id": external_id,
        "geography": "United States",
        "evidence_class": "official",
        "attributes": {"test_fixture": True},
        "source_references": [record],
        "tasks": [{"node_id": f"{node_id}:task", "label": task or "Develop, test or document software and related systems.", "source_references": [record]}],
        "skills": [{"node_id": f"{node_id}:skill", "label": skill, "source_references": [record]}] if skill else [],
        "occupational_terms": [],
        "relationships": [],
        "citations": [record],
    }


CAREERS = [
    career("occupation:software", "Software Developers", "O*NET OnLine", "15-1252.00", task="Debug or improve existing programs and interfaces."),
    career("occupation:graphic", "Graphic Designers", "O*NET OnLine", "27-1024.00", skill="Writing", task="Develop layouts and graphics for products, logos and websites."),
    career("occupation:esco-software", "software developer", "ESCO", "http://data.europa.eu/esco/occupation/f2b15a0e-e65a-438a-affb-29b9d50b77d1", task="Analyse software specifications."),
]


@pytest.fixture
def setup_test(tmp_path, monkeypatch):
    db_path = tmp_path / "recommendations.db"
    repository = RecommendationRepository(
        db_path,
        career_provider=lambda **kwargs: CAREERS,
        graph_status_provider=lambda **kwargs: {"status": "ready", "is_stale": False, "limitations": ["Synthetic test graph."], "source_data_is_live": False},
    )
    # Recommendations must cite a source record that actually exists in the internal registry.
    # These are explicitly synthetic test fixtures with example.org links, never production facts.
    unique_sources = {(item["source_id"], item["source_record_id"]): item
                      for career_item in CAREERS
                      for item in (career_item.get("source_references", []) +
                                   [ref for group in (career_item.get("tasks", []) + career_item.get("skills", []))
                                    for ref in group.get("source_references", [])])}
    for key, raw in unique_sources.items():
        repository.provenance.upsert_source(SourceRecord(
            source_id=raw["source_id"], publisher=raw["publisher"], title=raw["title"],
            source_type=SourceType.DEMO_FIXTURE, geography=raw.get("geography"),
            source_uri="https://example.org/occupations", record_uri=raw.get("record_uri"),
            source_version=raw.get("source_version"), accessed_at=datetime.now(UTC),
            quality_status=QualityStatus.UNVERIFIED,
            limitations=["Synthetic test fixture; not a production source."],
        ), key[1])
    challenges = ChallengeRepository(db_path)
    monkeypatch.setattr("app.api.recommendations.repo", lambda: repository)
    monkeypatch.setattr("app.api.student_evidence.get_repository", lambda: repository.evidence)
    monkeypatch.setattr("app.api.challenges.repo", lambda: challenges)
    return TestClient(app), repository, challenges


def profile(client, age="18_plus", goal=None):
    consent = "student_confirmed" if age == "18_plus" else "guardian_confirmed"
    response = client.post("/api/student-profiles", json={
        "age_band": age, "consent_basis": consent, "consent_confirmed": True, "current_goal": goal,
    })
    assert response.status_code == 201, response.text
    return response.json()


def submit(client, profile_id, challenge_id="debug-the-process", interpretation="not_interpreted", note="Observed the task criterion.", willingness=3):
    challenge = client.get(f"/api/challenges/{challenge_id}").json()
    criterion = challenge["rubric"][0]
    response = client.post(f"/api/challenges/{challenge_id}/submissions", json={
        "profile_id": profile_id,
        "output": "A short test output.",
        "rubric_observations": [{"criterion_id": criterion["criterion_id"], "score": 1, "observation": note}],
        "enjoyment": 4, "difficulty_reported": 3, "confidence": 3,
        "willingness_to_continue": willingness, "reflection": "A test reflection.",
        "hypothesis_interpretation": interpretation,
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_policy_is_configurable_versioned_and_weights_sum_to_one():
    policy = load_recommendation_policy()
    assert policy["algorithm_version"] == "transparent-career-match-v1.0"
    assert policy["status"] == "initial_heuristic_parameters_not_scientifically_optimized"
    assert sum(policy["weights"].values()) == pytest.approx(1.0)
    domain_policy = load_domain_policy()
    assert domain_policy["classification"] == "skillscope_authored_hypotheses_not_official_taxonomy"
    assert len(domain_policy["mappings"]) == 10


def test_goal_overlap_returns_explainable_challenge_not_percentage(setup_test):
    client, _, _ = setup_test
    student = profile(client, goal="I want to become a software developer")
    response = client.get(f"/api/recommendations/{student['profile_id']}")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["algorithm_version"] == "transparent-career-match-v1.0"
    assert result["recommendations"][0]["occupation"] == "Software Developers"
    rec = result["recommendations"][0]
    assert rec["category"] == "challenge"
    assert rec["evidence_confidence"] == "low"
    assert rec["next_validating_action"]["challenge_id"]
    assert rec["source_backed_pathway_facts"]
    assert rec["source_backed_pathway_facts"][0]["source"]["record_uri"].startswith("https://")
    assert result["weights_status"] == "initial_heuristic_parameters_not_scientifically_optimized"
    assert all("probability" not in item["hypothesis_label"].casefold() for item in result["recommendations"])


def test_recommendation_snapshots_are_durable_and_expose_algorithm_version(setup_test):
    client, repository, _ = setup_test
    student = profile(client, goal="I want to explore software and creative technology")
    first = client.get(f"/api/recommendations/{student['profile_id']}")
    assert first.status_code == 200, first.text
    second = client.get(f"/api/recommendations/{student['profile_id']}")
    assert second.status_code == 200, second.text

    history = client.get(f"/api/recommendations/{student['profile_id']}/history?limit=10")
    assert history.status_code == 200, history.text
    body = history.json()
    assert len(body) == 2
    assert all(row["algorithm_version"] == "transparent-career-match-v1.0" for row in body)
    assert all(row["source_keys"] for row in body)

    # A new repository instance sees the saved snapshots; they are not just in-process state.
    restarted = RecommendationRepository(
        repository.db_path,
        career_provider=lambda **kwargs: CAREERS,
        graph_status_provider=lambda **kwargs: {"status": "ready", "is_stale": False, "limitations": [], "source_data_is_live": False},
    )
    persisted_history = restarted.get_history(student["profile_id"], limit=10)
    assert persisted_history is not None and len(persisted_history) == 2


def test_missing_profile_returns_404(setup_test):
    client, _, _ = setup_test
    response = client.get(f"/api/recommendations/{uuid.uuid4()}")
    assert response.status_code == 404


def test_empty_evidence_is_unknown_and_confidence_stays_low(setup_test):
    client, _, _ = setup_test
    student = profile(client, goal=None)
    result = client.get(f"/api/recommendations/{student['profile_id']}").json()
    assert all(rec["evidence_confidence"] == "low" for rec in result["recommendations"])
    assert any(gap["gap_type"] == "unexplored_or_unrecorded_domain" for rec in result["recommendations"] for gap in rec["evidence_gaps"])
    assert "unknown" in result["ordering_explanation"].casefold()


def test_explicit_contradiction_moves_goal_aligned_path_to_refresh_not_goal_autoswitch(setup_test):
    client, _, _ = setup_test
    student = profile(client, goal="Software Developers")
    submit(client, student["profile_id"], interpretation="challenges_current_hypothesis")
    result = client.get(f"/api/recommendations/{student['profile_id']}").json()
    software = next(rec for rec in result["recommendations"] if rec["occupation"] == "Software Developers")
    assert software["category"] == "reconsider_refresh"
    assert any("does not automatically change your goal" in item for item in software["rationale"])
    assert any(e["user_interpretation"] == "challenges_current_hypothesis" for e in software["evidence_used"])
    assert software["evidence_confidence"] == "low"


def test_supportive_alternative_is_labelled_as_hypothesis_not_goal_change(setup_test):
    client, _, _ = setup_test
    student = profile(client, goal="I am exploring history")
    submit(client, student["profile_id"], interpretation="supports_current_hypothesis", willingness=5)
    result = client.get(f"/api/recommendations/{student['profile_id']}").json()
    software = next(rec for rec in result["recommendations"] if rec["occupation"] == "Software Developers")
    assert software["category"] == "alternative_to_consider"
    assert "alternative" in software["rationale"][0].casefold() or "alternative" in software["category"]
    assert any("not as a hidden goal change" in reason for reason in software["rationale"])


def test_exact_skill_label_overlap_is_explained_without_claiming_proficiency(setup_test):
    client, _, _ = setup_test
    student = profile(client, goal="software")
    submit(client, student["profile_id"], note="Critical Thinking helped me isolate the issue.")
    result = client.get(f"/api/recommendations/{student['profile_id']}").json()
    software = next(rec for rec in result["recommendations"] if rec["occupation"] == "Software Developers")
    overlap = next(match for match in software["matches"] if match["match_type"] == "exact_skill_label_overlap")
    assert overlap["label"] == "Critical Thinking"
    assert "not proof of proficiency" in overlap["explanation"]
    assert overlap["source_references"][0]["source_id"] == "test_onet"


def test_under_15_recommendations_are_broad_domains_and_do_not_require_graph(setup_test, monkeypatch):
    client, repository, _ = setup_test
    repository.graph_status_provider = lambda **kwargs: {"status": "not_built", "is_stale": False, "limitations": ["Graph intentionally not built."]}
    student = profile(client, age="10_14", goal="I want to be a software developer")
    result = client.get(f"/api/recommendations/{student['profile_id']}")
    assert result.status_code == 200, result.text
    body = result.json()
    assert body["catalog_status"] == "not_required_for_10_14_exploration"
    assert body["recommendations"]
    assert all(item["recommendation_type"] == "broad_domain_hypothesis" for item in body["recommendations"])
    assert all(item["occupation"] is None and item["occupation_node_id"] is None for item in body["recommendations"])
    assert all("career names are intentionally withheld" in " ".join(item["important_limitations"]).casefold() for item in body["recommendations"])


def test_stale_graph_is_rejected_for_occupation_hypotheses(setup_test):
    client, repository, _ = setup_test
    repository.graph_status_provider = lambda **kwargs: {"status": "ready", "is_stale": True, "limitations": []}
    student = profile(client, goal="software")
    response = client.get(f"/api/recommendations/{student['profile_id']}")
    assert response.status_code == 409
    assert "stale" in response.json()["detail"].casefold()


def test_repeat_reads_are_deterministic_with_same_persisted_inputs(setup_test):
    client, _, _ = setup_test
    student = profile(client, goal="Software Developers")
    one = client.get(f"/api/recommendations/{student['profile_id']}").json()
    two = client.get(f"/api/recommendations/{student['profile_id']}").json()
    assert one == two


def test_domain_associations_preserve_ontology_and_are_called_authored_hypotheses(setup_test):
    client, _, _ = setup_test
    student = profile(client, goal="software developer")
    submit(client, student["profile_id"], interpretation="supports_current_hypothesis")
    result = client.get(f"/api/recommendations/{student['profile_id']}").json()
    onet = next(rec for rec in result["recommendations"] if rec["occupation_node_id"] == "occupation:software")
    esco = next(rec for rec in result["recommendations"] if rec["occupation_node_id"] == "occupation:esco-software")
    assert onet["taxonomy"] == "O*NET OnLine"
    assert esco["taxonomy"] == "ESCO"
    assert onet["occupation_node_id"] != esco["occupation_node_id"]
    assert any(match["match_type"] == "authored_domain_hypothesis" for match in onet["matches"])
    assert "not official occupation classifications" in " ".join(result["global_notices"])


def test_catalog_unavailable_is_not_replaced_with_fabricated_pathways(setup_test):
    client, repository, _ = setup_test
    repository.graph_status_provider = lambda **kwargs: {"status": "not_built", "is_stale": False, "limitations": []}
    student = profile(client, goal="software developer")
    response = client.get(f"/api/recommendations/{student['profile_id']}")
    assert response.status_code == 503
    assert "graph is not built" in response.json()["detail"].casefold()


def test_portfolio_record_is_context_not_automatic_skill_proof(setup_test):
    client, repository, _ = setup_test
    student = profile(client, goal="software")
    repository.evidence.add_evidence(student["profile_id"], EvidenceCreate(
        evidence_type=EvidenceType.PROJECT_PORTFOLIO,
        signal_dimension=SignalDimension.EXPERIENCE_EXPOSURE,
        title="Software prototype project",
        observation="I created a software prototype and documented a test workflow.",
        domain="technology",
        source_kind=EvidenceSourceKind.USER_ADDED_PROJECT,
        uncertainty=UncertaintyLevel.MEDIUM,
        user_interpretation=UserInterpretation.NOT_INTERPRETED,
        context={"portfolio_kind": "personal_project"},
    ))
    result = client.get(f"/api/recommendations/{student['profile_id']}").json()
    software = next(rec for rec in result["recommendations"] if rec["occupation"] == "Software Developers")
    assert any(match["match_type"] == "portfolio_text_overlap" for match in software["matches"])
    assert not any("proven proficiency" in match["explanation"].casefold() for match in software["matches"])


def test_weights_and_raw_numerical_fit_are_not_returned_to_clients(setup_test):
    client, _, _ = setup_test
    student = profile(client, goal="software")
    body = client.get(f"/api/recommendations/{student['profile_id']}").json()
    forbidden = {"score", "match_score", "fit_score", "probability", "percentage", "rank_score"}
    keys = set()
    def collect(value):
        if isinstance(value, dict):
            keys.update(key.casefold() for key in value)
            for child in value.values(): collect(child)
        elif isinstance(value, list):
            for child in value: collect(child)
    collect(body)
    assert keys.isdisjoint(forbidden)


def test_skill_label_match_requires_contiguous_phrase_not_scattered_tokens(setup_test):
    client, _, _ = setup_test
    student = profile(client, goal="software")
    submit(client, student["profile_id"], note="I used thinking while investigating a critical issue.")
    result = client.get(f"/api/recommendations/{student['profile_id']}").json()
    software = next(rec for rec in result["recommendations"] if rec["occupation"] == "Software Developers")
    assert not any(match["match_type"] == "exact_skill_label_overlap" for match in software["matches"])
    assert any(gap["gap_type"] == "unobserved_exact_skill_label" for gap in software["evidence_gaps"])


def test_recommendation_exposes_full_distinct_observation_count_and_recency(setup_test):
    client, _, _ = setup_test
    student = profile(client, age="18_plus", goal="software engineering")
    profile_id = student["profile_id"]
    submit(client, profile_id, challenge_id="debug-the-process", note="I traced the logic and documented the error.")
    response = client.get(f"/api/recommendations/{profile_id}")
    assert response.status_code == 200, response.text
    body = response.json()
    supported = [item for item in body["recommendations"] if item["distinct_observation_count"] > 0]
    assert supported
    item = supported[0]
    assert item["most_recent_observation_at"]
    assert item["evidence_detail_limit"] >= len(item["evidence_used"])
    assert "probability" not in str(item["distinct_observation_count"]).lower()


# Stage 19 validation scenarios: these are behavioural checks, not psychometric validation.
def test_stage19_teen_software_goal_low_evidence_keeps_both_coding_and_non_coding_options(setup_test, monkeypatch):
    from app.services.baseline_assessment import BaselineAssessmentRepository

    client, repository, _ = setup_test
    monkeypatch.setattr("app.api.baseline_assessment.repo", lambda: BaselineAssessmentRepository(repository.db_path))
    student = profile(client, age="15_17", goal="I want to explore software engineering")
    baseline = client.post(f"/api/baseline-assessments/for/{student['profile_id']}")
    assert baseline.status_code == 201, baseline.text
    assert baseline.json()["mode"] == "explore_and_validate"

    result = client.get(f"/api/recommendations/{student['profile_id']}")
    assert result.status_code == 200, result.text
    body = result.json()
    labels = {item["occupation"] for item in body["recommendations"]}
    assert "Software Developers" in labels
    assert "Graphic Designers" in labels
    software = next(item for item in body["recommendations"] if item["occupation"] == "Software Developers")
    design = next(item for item in body["recommendations"] if item["occupation"] == "Graphic Designers")
    assert software["evidence_confidence"] == "low"
    assert software["next_validating_action"]["domain"] in {"technology", "logic_data"}
    assert design["next_validating_action"]["domain"] == "design_creative"
    assert any("validation" in reason.casefold() or "wording" in reason.casefold() for reason in software["rationale"])


def test_stage19_teen_design_and_communication_evidence_retains_software_and_surfaces_alternative(setup_test):
    client, repository, _ = setup_test
    student = profile(client, age="15_17", goal="I want to explore software engineering")
    for title, domain, note, enjoyment in (
        ("Design activity reflection", "design_creative", "I enjoyed creating a visual layout and revising it after feedback.", 5),
        ("Communication activity reflection", "communication", "I enjoyed explaining an idea to a different audience and improving the message.", 4),
    ):
        repository.evidence.add_evidence(student["profile_id"], EvidenceCreate(
            evidence_type=EvidenceType.ACTIVITY_REFLECTION,
            signal_dimension=SignalDimension.INTEREST,
            title=title, observation=note, domain=domain,
            source_kind=EvidenceSourceKind.SELF_REPORT,
            uncertainty=UncertaintyLevel.MEDIUM,
            user_interpretation=UserInterpretation.SUPPORTS_CURRENT_HYPOTHESIS,
            reported_enjoyment=enjoyment,
        ))
    body = client.get(f"/api/recommendations/{student['profile_id']}").json()
    software = next(item for item in body["recommendations"] if item["occupation"] == "Software Developers")
    design = next(item for item in body["recommendations"] if item["occupation"] == "Graphic Designers")
    assert software["category"] in {"challenge", "develop", "reconsider_refresh"}
    assert design["category"] == "alternative_to_consider"
    assert any(ref["domain"] in {"design_creative", "communication"} for ref in design["evidence_used"])
    current_profile = client.get(f"/api/student-profiles/{student['profile_id']}").json()
    assert current_profile["current_goal"] == "I want to explore software engineering"


def test_stage19_evidence_deletion_recalculates_recommendation_history(setup_test):
    client, _, _ = setup_test
    student = profile(client, age="18_plus", goal="Software Developers")
    submitted = submit(client, student["profile_id"], challenge_id="debug-the-process", note="I traced the software workflow and documented the process.")
    before = client.get(f"/api/recommendations/{student['profile_id']}").json()
    evidence_id = submitted["evidence_created_id"]
    deleted = client.delete(f"/api/student-profiles/{student['profile_id']}/evidence/{evidence_id}")
    assert deleted.status_code == 204
    after = client.get(f"/api/recommendations/{student['profile_id']}").json()
    assert before["evidence_count"] == after["evidence_count"] + 1
    history = client.get(f"/api/recommendations/{student['profile_id']}/history?limit=10").json()
    assert len(history) == 2
    assert {row["evidence_count"] for row in history} == {before["evidence_count"], after["evidence_count"]}
    remaining = client.get(f"/api/student-profiles/{student['profile_id']}/evidence").json()
    assert evidence_id not in {item["evidence_id"] for item in remaining["items"]}


def test_stage19_local_loop_does_not_require_external_api_keys_or_network(setup_test, monkeypatch):
    from app.services.discovery_loop import DiscoveryLoopRepository
    client, repository, _ = setup_test
    monkeypatch.setattr("app.api.discovery_loop.repo", lambda: DiscoveryLoopRepository(repository.db_path))
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "SKILLSCOPE_LLM_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    student = profile(client, age="15_17", goal="Explore a software project")
    loop = client.get(f"/api/discovery-loop/{student['profile_id']}")
    assert loop.status_code == 200, loop.text
    challenge = loop.json()["next_challenge"]
    assert challenge["challenge_id"] in {item.challenge_id for item in __import__("app.services.challenges", fromlist=["CHALLENGES"]).CHALLENGES}
    # The mocked source graph is static, explicitly non-live, and the local loop works without keys/network.
    result = client.get(f"/api/recommendations/{student['profile_id']}")
    assert result.status_code == 200, result.text
    assert result.json()["catalog_status"] == "ready"
    assert repository.graph_status_provider()["source_data_is_live"] is False


def test_stage19_evidence_correction_is_reflected_in_future_snapshot_without_erasing_history(setup_test):
    client, _, _ = setup_test
    student = profile(client, age="18_plus", goal="Software Developers")
    submitted = submit(client, student["profile_id"], note="I traced the workflow and documented the logic.")
    first = client.get(f"/api/recommendations/{student['profile_id']}")
    assert first.status_code == 200, first.text
    history_before = client.get(f"/api/recommendations/{student['profile_id']}/history?limit=10").json()

    corrected = client.patch(
        f"/api/student-profiles/{student['profile_id']}/evidence/{submitted['evidence_created_id']}",
        json={
            "observation": "Correction: I enjoyed explaining the interface to another person; task performance is not a general skill rating.",
            "domain": "communication",
            "reported_enjoyment": 5,
            "user_interpretation": "contextual_or_mixed",
        },
    )
    assert corrected.status_code == 200, corrected.text
    assert corrected.json()["observation"].startswith("Correction:")
    assert corrected.json()["reported_enjoyment"] == 5
    second = client.get(f"/api/recommendations/{student['profile_id']}")
    assert second.status_code == 200, second.text
    history_after = client.get(f"/api/recommendations/{student['profile_id']}/history?limit=10").json()
    assert len(history_after) == len(history_before) + 1
    # Earlier generated snapshots remain traceable as historical records; the corrected ledger item is current.
    current_items = client.get(f"/api/student-profiles/{student['profile_id']}/evidence").json()["items"]
    assert any(item["evidence_id"] == submitted["evidence_created_id"] and item["observation"].startswith("Correction:") for item in current_items)


def test_stage19_adult_with_no_goal_and_conflicting_interpretation_enters_rediscovery_without_forced_choice(setup_test, monkeypatch):
    from app.services.discovery_loop import DiscoveryLoopRepository

    client, repository, _ = setup_test
    monkeypatch.setattr("app.api.discovery_loop.repo", lambda: DiscoveryLoopRepository(repository.db_path))
    student = profile(client, age="18_plus", goal=None)
    submit(client, student["profile_id"], interpretation="challenges_current_hypothesis", note="This task did not feel like a direction I want to pursue.", willingness=3)

    loop = client.get(f"/api/discovery-loop/{student['profile_id']}?preference=balanced")
    assert loop.status_code == 200, loop.text
    assert loop.json()["next_challenge"]["reason_code"] == "test_alternative_pathway"
    recommendations = client.get(f"/api/recommendations/{student['profile_id']}")
    assert recommendations.status_code == 200, recommendations.text
    body = recommendations.json()
    assert body["current_goal"] is None
    assert body["recommendations"]
    assert not any(item["category"] == "develop" for item in body["recommendations"])
    assert all(item["evidence_confidence"] != "high" for item in body["recommendations"])


def test_stage19_age_10_with_no_prior_evidence_gets_broad_exploration_not_an_occupation(setup_test):
    client, _, _ = setup_test
    student = profile(client, age="10_14", goal=None)
    evidence = client.get(f"/api/student-profiles/{student['profile_id']}/evidence")
    assert evidence.status_code == 200 and evidence.json()["count"] == 0

    response = client.get(f"/api/recommendations/{student['profile_id']}")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["catalog_status"] == "not_required_for_10_14_exploration"
    assert body["evidence_count"] == 0
    assert body["recommendations"]
    assert all(item["recommendation_type"] == "broad_domain_hypothesis" for item in body["recommendations"])
    assert all(item["occupation"] is None for item in body["recommendations"])


def test_stage19_career_goal_change_updates_new_recommendation_and_preserves_prior_goal_history(setup_test):
    client, _, _ = setup_test
    student = profile(client, age="18_plus", goal="Explore software engineering")
    first = client.get(f"/api/recommendations/{student['profile_id']}")
    assert first.status_code == 200 and first.json()["current_goal"] == "Explore software engineering"

    patched = client.patch(f"/api/student-profiles/{student['profile_id']}", json={
        "current_goal": "Explore graphic design and communication",
    })
    assert patched.status_code == 200, patched.text
    second = client.get(f"/api/recommendations/{student['profile_id']}")
    assert second.status_code == 200, second.text
    assert second.json()["current_goal"] == "Explore graphic design and communication"

    goals = client.get(f"/api/student-profiles/{student['profile_id']}/evidence?signal_dimension=goal_preference")
    assert goals.status_code == 200
    observations = [item["observation"] for item in goals.json()["items"]]
    assert any("Explore software engineering" in item for item in observations)
    assert any("Explore graphic design and communication" in item for item in observations)

    history = client.get(f"/api/recommendations/{student['profile_id']}/history?limit=10")
    assert history.status_code == 200
    assert len(history.json()) >= 2
