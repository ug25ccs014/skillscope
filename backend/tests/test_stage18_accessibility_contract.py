from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "src"


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_visible_demo_only_privacy_notice_and_minor_consent_boundary():
    ui = read("frontend/src/components/EvidenceLedger.tsx")
    assert "Prototype privacy and safety notice — demo data only" in ui
    assert "Do not enter real student or child data" in ui
    assert "guardian identity and legal consent are not independently verified" in ui.lower()
    assert 'aria-describedby="privacy-safety-notice-copy"' in ui
    assert 'role="note" aria-labelledby="privacy-safety-notice-heading"' in ui
    assert "Delete profile + history" in ui


def test_major_journeys_have_named_sections_and_announced_errors_or_status():
    expected = {
        "frontend/src/components/EvidenceLedger.tsx": ("aria-labelledby=\"evidence-ledger-heading\"", "role=\"alert\"", "role=\"status\""),
        "frontend/src/components/DiscoveryLoop.tsx": ("aria-labelledby=\"discovery-loop-heading\"", "role=\"alert\"", "role=\"status\""),
        "frontend/src/components/CareerRecommendations.tsx": ("aria-labelledby=\"career-recommendations-heading\"", "role=\"alert\""),
        "frontend/src/components/PathwayPlanner.tsx": ("aria-labelledby=\"pathway-planner-heading\"", "role=\"alert\""),
        "frontend/src/components/SourceRegistry.tsx": ("aria-labelledby=\"source-registry-heading\"", "role=\"alert\""),
    }
    for filename, required_snippets in expected.items():
        content = read(filename)
        for snippet in required_snippets:
            assert snippet in content, f"Missing accessibility/status pattern {snippet} in {filename}"


def test_global_accessibility_tokens_and_checklist_exist():
    css = read("frontend/src/index.css")
    doc = read("docs/PRIVACY_AND_SAFETY.md")
    assert ":focus-visible" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "@media (max-width: 640px)" in css
    assert "Mandatory production release gates" in doc
    assert "No legal compliance review has been performed" in doc
    assert "not a comprehensive sensitive-data detector" in doc
