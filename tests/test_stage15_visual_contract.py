from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend" / "src"
COMPONENTS = FRONTEND / "components"


def text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def all_tsx() -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in FRONTEND.rglob("*.tsx"))


def test_visual_tokens_and_accessibility_rules_are_present():
    css = text(FRONTEND / "index.css")
    for token in (
        "--ss-ink", "--ss-canvas", "--ss-surface", "--ss-line",
        "--ss-teal", "--ss-focus", ".ss-panel", ".ss-section-kicker",
    ):
        assert token in css
    assert ":focus-visible" in css
    assert "prefers-reduced-motion: reduce" in css
    assert "@media (max-width: 640px)" in css
    assert 'font-size: 16px' in css
    assert "text-wrap: balance" in css
    assert "overflow-wrap: anywhere" in css
    assert ".text-slate-400 { color: #5c6b7d; }" in css


def test_every_route_and_journey_step_has_a_page():
    """The themed UI is multi-page (hash routes), so navigation targets are routes, not in-page anchors."""
    router = text(FRONTEND / "router.ts")
    app = text(FRONTEND / "App.tsx")
    strip = text(FRONTEND / "layout" / "JourneyStrip.tsx")
    route_paths = re.findall(r"\{ path: '(/[^']*)', label", router)
    assert route_paths, "Expected inspectable routes"
    for path in route_paths:
        assert f"'{path}':" in app, f"Route {path} has no page in App.tsx"
    for path in re.findall(r"\{ path: '(/[^']*)', label", strip):
        assert path in route_paths, f"Journey step {path} is not a real route"
    for required in ("/baseline", "/demo", "/sources"):
        assert required in route_paths

    sources = all_tsx()
    static_ids = [i for i in re.findall(r'\bid="([^"{]+)"', sources) if not i.startswith("auth-")]
    duplicates = sorted({value for value in static_ids if static_ids.count(value) > 1})
    assert not duplicates, f"Duplicate static DOM IDs: {duplicates}"


def test_required_stage15_surfaces_are_implemented_in_real_components():
    start = text(FRONTEND / "pages" / "StartPage.tsx")
    sources = text(FRONTEND / "pages" / "SourcesPage.tsx")
    baseline = text(COMPONENTS / "BaselineAssessment.tsx")
    evidence = text(COMPONENTS / "EvidenceLedger.tsx")
    challenge = text(COMPONENTS / "DiscoveryLoop.tsx")
    careers = text(COMPONENTS / "CareerRecommendations.tsx")
    pathway = text(COMPONENTS / "PathwayPlanner.tsx")

    assert "Recommended starting path" in start and "evidence_strength_label" in start
    assert "initial snapshot" in baseline.lower()
    assert "signals" in evidence and "recent_evidence" in evidence and "evidence_count" in evidence
    assert "expected_output" in challenge and "reflection_prompts" in challenge
    assert "source_backed_pathway_facts" in careers and "evidence_gaps" in careers
    assert "Turn ideas into next steps" in pathway
    assert "Static snapshot · Not live job-market data" in sources
    assert "Prototype privacy boundary" in evidence
    assert "Delete profile + history" in evidence


def test_responsive_sections_share_the_outer_page_width():
    css = text(FRONTEND / "index.css")
    assert ".ss-app-shell" in css and ".ss-section" in css
    assert "min-width: 0" in css
    assert "ss-app-shell" in text(FRONTEND / "layout" / "SiteLayout.tsx")
    assert 'className="w-full min-w-0"' in text(COMPONENTS / "BaselineAssessment.tsx")
    strip = text(FRONTEND / "layout" / "JourneyStrip.tsx")
    assert "overflow-x-auto" in strip, "Mobile journey strip should scroll instead of compressing"
    assert "aria-current" in strip


def test_no_inert_controls_or_fake_live_charts_are_introduced():
    sources = all_tsx()
    non_motion = "\n".join(p.read_text(encoding="utf-8") for p in FRONTEND.rglob("*.tsx") if "motion" not in p.parts)
    assert 'onClick={() => {}}' not in sources
    assert 'href="#"' not in sources
    assert "<Chart" not in sources
    assert "<canvas" not in non_motion.lower(), "Canvas is only allowed for the decorative scene in motion/"


def test_visual_audit_discloses_unverified_browser_build_checks():
    audit = text(ROOT / "docs" / "STAGE15_VISUAL_AUDIT.md")
    assert "Full browser rendering audit is not claimed" in audit
    assert "not verified" in audit.lower()
    assert "reduced-motion" in audit.lower()
    assert "profile deletion" in audit.lower()


def _rgb_luminance(hex_color: str) -> float:
    channels = [int(hex_color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted((_rgb_luminance(foreground), _rgb_luminance(background)), reverse=True)
    return (lighter + 0.05) / (darker + 0.05)


def test_primary_text_and_focus_colors_meet_wcag_aa_contrast():
    css = text(FRONTEND / "index.css")
    tokens = dict(re.findall(r"(--ss-[\w-]+):\s*(#[0-9a-fA-F]{6})", css))
    assert {"--ss-ink", "--ss-canvas", "--ss-teal", "--ss-indigo", "--ss-focus"} <= tokens.keys()
    muted = re.search(r"\.text-slate-400\s*\{\s*color:\s*(#[0-9a-fA-F]{6})", css)
    assert muted, "Muted small metadata text must have an explicit accessible color override"
    white = "#ffffff"
    assert _contrast_ratio(tokens["--ss-ink"], tokens["--ss-canvas"]) >= 4.5
    assert _contrast_ratio(tokens["--ss-teal"], white) >= 4.5
    assert _contrast_ratio(tokens["--ss-indigo"], white) >= 4.5
    assert _contrast_ratio(tokens["--ss-focus"], white) >= 4.5
    assert _contrast_ratio(muted.group(1), white) >= 4.5
