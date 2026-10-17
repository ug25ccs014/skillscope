import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "data" / "user_journey_contract.json"


def load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def test_required_journey_surfaces_have_unique_ids_and_real_owners():
    contract = load_contract()
    surfaces = contract["required_surfaces"]
    ids = [surface["id"] for surface in surfaces]
    assert len(ids) == len(set(ids))
    assert {"top", "evidence-ledger", "baseline-assessment", "discovery-loop", "career-recommendations", "pathway-planner", "career-knowledge", "profile-settings"}.issubset(ids)
    for surface in surfaces:
        assert (ROOT / surface["owner"]).is_file(), surface["owner"]


def test_all_primary_transitions_reference_known_surface_ids():
    contract = load_contract()
    ids = {surface["id"] for surface in contract["required_surfaces"]}
    transitions = contract["primary_transitions"]
    assert transitions
    for transition in transitions:
        assert transition["from"] in ids
        assert transition["to"] in ids
        assert transition["trigger"].strip()


def test_primary_journey_connects_start_to_sources_without_orphan_steps():
    contract = load_contract()
    edges = {(item["from"], item["to"]) for item in contract["primary_transitions"]}
    path = ["top", "evidence-ledger", "baseline-assessment", "discovery-loop", "career-recommendations", "pathway-planner", "career-knowledge"]
    for first, second in zip(path, path[1:]):
        assert (first, second) in edges, f"Missing journey transition: {first} -> {second}"
    assert ("evidence-ledger", "profile-settings") in edges


def test_first_visit_loading_offline_error_and_conflict_states_are_defined():
    states = set(load_contract()["states"])
    expected = {
        "first_visit_no_profile", "consent_not_confirmed", "calibration_loading", "api_unavailable",
        "baseline_not_started", "baseline_in_progress", "baseline_submitted", "profile_loading",
        "profile_load_error", "evidence_empty_or_unknown", "challenge_ready", "challenge_submitting",
        "challenge_saved", "recommendations_loading", "source_graph_not_built", "source_graph_stale",
        "source_graph_offline", "conflicting_or_mixed_evidence", "pathway_plan_missing",
        "pathway_plan_saved", "profile_data_settings",
    }
    assert expected.issubset(states)


def test_navigation_and_component_anchors_cover_the_journey():
    nav = (ROOT / "frontend" / "src" / "components" / "JourneyNavigation.tsx").read_text(encoding="utf-8")
    app = (ROOT / "frontend" / "src" / "App.tsx").read_text(encoding="utf-8")
    evidence = (ROOT / "frontend" / "src" / "components" / "EvidenceLedger.tsx").read_text(encoding="utf-8")
    for anchor in ("top", "evidence-ledger", "baseline-assessment", "discovery-loop", "career-recommendations", "pathway-planner", "career-knowledge", "profile-settings"):
        assert f"id: '{anchor}'" in nav or f'id="{anchor}"' in app or f'id="{anchor}"' in evidence, anchor
    assert "BaselineAssessment" in app
    assert 'aria-label="Primary journey navigation"' in nav


def test_privacy_and_evidence_invariants_are_part_of_the_contract():
    invariants = load_contract()["invariants"]
    joined = " ".join(invariants).casefold()
    assert "guardian consent" in joined
    assert "unknown, not zero" in joined
    assert "conflicting" in joined
    assert "developer tools" in joined
