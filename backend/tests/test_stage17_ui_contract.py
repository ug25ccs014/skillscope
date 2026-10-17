"""Static contract checks for Stage 17 auditability surfaces."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_recommendations_expose_evidence_logic_and_source_facts_separately():
    ui = _read("frontend/src/components/CareerRecommendations.tsx")
    assert "Audit trail: student evidence → matching logic → source facts" in ui
    assert "Student evidence used" in ui
    assert "distinct relevant observation" in ui
    assert "Local matching logic — SkillScope inference" in ui
    assert "External occupational facts — source-derived" in ui
    assert "Next validating action" in ui
    assert "Missing data means not yet observed, not low potential" in ui


def test_source_registry_discloses_snapshot_freshness_and_limits():
    ui = _read("frontend/src/components/SourceRegistry.tsx")
    assert "Last successful sync" in ui
    assert "Publisher links, terms, and limitations" in ui
    assert "Source records marked conflicted" in ui
    assert "Non-exact occupational mappings" in ui
    assert "built_from_active_snapshots" in ui
    assert "is_stale" in ui
    assert "Stale: graph snapshot differs from currently active source snapshots." in ui
    assert ui.count("Graph build and snapshot audit") == 1


def test_source_audit_route_and_navigation_are_unique_and_reachable():
    main = _read("backend/app/main.py")
    page = _read("frontend/src/pages/SourcesPage.tsx")
    router = _read("frontend/src/router.ts")
    app = _read("frontend/src/App.tsx")
    assert main.count("app.include_router(source_registry_router)") == 1
    assert "<SourceRegistry apiBaseUrl={apiBaseUrl} />" in page
    assert "path: '/sources'" in router and "'/sources': SourcesPage" in app
