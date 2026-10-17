from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "data" / "sources_manifest.yaml"


def load_manifest():
    return yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_has_required_official_source_families():
    manifest = load_manifest()
    ids = {source["id"] for source in manifest["sources"]}
    assert {
        "ncs_india",
        "nsdc_india",
        "onet_database",
        "esco_classification",
        "plfs_india_annual_report",
        "onet_interest_profiler_tools",
        "onet_online_curated_sample",
        "esco_curated_sample",
    } <= ids
    assert manifest["last_reviewed"] == "2026-10-17"


def test_every_source_has_traceable_review_and_access_metadata():
    manifest = load_manifest()
    required = {
        "id",
        "publisher",
        "name",
        "official_url",
        "geographic_scope",
        "source_role",
        "selection",
        "integration_status",
        "planned_access_method",
        "runtime_access_status",
        "version_or_release",
        "license_terms_status",
        "reviewed_on",
        "evidence_urls",
        "limits",
    }
    for source in manifest["sources"]:
        assert required <= source.keys(), source.get("id", "<missing id>")
        assert source["official_url"].startswith("https://")
        assert source["reviewed_on"] == manifest["last_reviewed"]
        assert source["evidence_urls"]
        assert source["limits"]


def test_bulk_sources_are_not_falsely_marked_integrated():
    manifest = load_manifest()
    assert manifest["manifest_status"].startswith("curated_extract_imported")
    assert "external_access_blocked" in manifest["manifest_status"]
    by_id = {source["id"]: source for source in manifest["sources"]}
    for source_id in ("ncs_india", "nsdc_india", "onet_database", "esco_classification", "plfs_india_annual_report"):
        assert by_id[source_id]["integration_status"] == "not_integrated"
    for source_id in ("onet_online_curated_sample", "esco_curated_sample"):
        assert by_id[source_id]["integration_status"] == "curated_extract_imported_not_full_source_integrated"
        assert "not live" in " ".join(by_id[source_id]["limits"]).lower() or "runtime" in " ".join(by_id[source_id]["limits"]).lower()


def test_plfs_is_explicitly_aggregate_context_only():
    source = next(s for s in load_manifest()["sources"] if s["id"] == "plfs_india_annual_report")
    assert source["selection"] == "selected_context_only_link_first"
    assert "individual" in " ".join(source["limits"]).lower()
    assert "individual" in source["license_terms_status"].lower() or "not" in source["license_terms_status"].lower()


def test_interest_profiler_is_not_selected_for_questionnaire_copy():
    source = next(s for s in load_manifest()["sources"] if s["id"] == "onet_interest_profiler_tools")
    assert source["selection"] == "excluded_from_mvp_instrument_copy"
    assert source["integration_status"] == "not_integrated"
    assert "validation" in source["license_terms_status"].lower()
