"""Stage 19 data-integrity checks for the small, deliberately curated career snapshot."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import yaml

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = ROOT / "data/curated/occupations_snapshot.json"
MANIFEST_PATH = ROOT / "data/sources_manifest.yaml"
DOMAIN_POLICY_PATH = ROOT / "data/career_domain_hypotheses.json"
REQUIRED_DOMAINS = {
    "logic_data", "science_research", "technology", "design_creative", "communication",
    "helping_social", "business", "hands_on_spatial", "environment",
}
REQUIRED_RECORD_FIELDS = {
    "source_id", "source_record_id", "publisher", "source_base_uri", "record_uri", "source_title",
    "source_version", "release_date", "geography", "source_accessed_at", "license_reference",
    "license_summary", "summary", "selected_tasks", "transformation_notes", "limitations",
}


def _https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc) and not parsed.username and not parsed.password


def test_stage19_curated_snapshot_has_required_provenance_unique_ids_and_stable_links():
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    assert snapshot["snapshot_type"] == "curated_extract"
    assert snapshot["runtime_fetch_performed"] is False
    assert snapshot["snapshot_id"] and snapshot["curated_at"] and snapshot["curated_by"]
    records = snapshot["records"]
    assert len(records) == 10
    identities: list[tuple[str, str]] = []
    urls: list[str] = []
    for row in records:
        assert REQUIRED_RECORD_FIELDS <= row.keys(), f"Missing metadata for {row.get('source_record_id')}"
        assert row["source_id"] and row["source_record_id"] and row["source_version"]
        assert row["publisher"] and row["license_summary"] and row["geography"] and row["release_date"]
        assert row["selected_tasks"] and row["transformation_notes"] and row["limitations"]
        assert _https_url(row["source_base_uri"])
        assert _https_url(row["record_uri"])
        assert _https_url(row["license_reference"])
        stamp = datetime.fromisoformat(row["source_accessed_at"].replace("Z", "+00:00"))
        assert stamp.tzinfo is not None and stamp.utcoffset() is not None
        identities.append((row["source_id"], row["source_record_id"]))
        urls.append(row["record_uri"])
        # The curated payload intentionally carries no wage/employment/outlook statistic fields.
        forbidden_keys = {"salary", "wage", "annual_wage", "employment_count", "job_openings", "growth_rate"}
        assert not forbidden_keys.intersection({str(k).casefold() for k in row})
    assert len(identities) == len(set(identities)), "Duplicate source identity in curated snapshot"
    assert len(urls) == len(set(urls)), "Duplicate record URLs obscure stable source identity"


def test_stage19_manifest_truthfully_separates_link_only_sources_and_curated_extracts():
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    sources = manifest["sources"]
    by_id = {item["id"]: item for item in sources}
    assert len(by_id) == len(sources) >= 8
    for item in sources:
        assert _https_url(item["official_url"]), item["id"]
        assert item.get("license_terms_status"), item["id"]
        assert item.get("geographic_scope"), item["id"]
        assert item.get("limits"), item["id"]
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    snapshot_source_ids = {row["source_id"] for row in snapshot["records"]}
    assert snapshot_source_ids == {"onet_online_curated_sample", "esco_curated_sample"}
    for source_id in snapshot_source_ids:
        assert by_id[source_id]["integration_status"] == "curated_extract_imported_not_full_source_integrated"
    for source_id in {"ncs_india", "nsdc_india", "onet_database", "esco_classification", "plfs_india_annual_report", "onet_interest_profiler_tools"}:
        assert by_id[source_id]["integration_status"] == "not_integrated"
    assert manifest["manifest_status"] == "curated_extract_imported_external_access_blocked"


def test_stage19_all_curated_occupations_have_one_authored_domain_hypothesis_mapping():
    snapshot = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    policy = json.loads(DOMAIN_POLICY_PATH.read_text(encoding="utf-8"))
    mappings = policy["mappings"]
    keys = [(item["taxonomy"], item["external_id"]) for item in mappings]
    assert len(keys) == len(set(keys)) == len(snapshot["records"]) == 10
    assert policy["classification"] == "skillscope_authored_hypotheses_not_official_taxonomy"
    mapped_domains = set()
    for mapping in mappings:
        assert mapping["basis"].strip()
        assert mapping["domains"]
        mapped_domains.update(mapping["domains"])
    assert mapped_domains == REQUIRED_DOMAINS
    snapshot_keys = set()
    for record in snapshot["records"]:
        if record["source_id"] == "esco_curated_sample":
            snapshot_keys.add(("ESCO", record["source_record_id"]))
        else:
            snapshot_keys.add(("O*NET OnLine", record["source_code"]))
    assert set(keys) == snapshot_keys


def test_stage19_cross_taxonomy_mapping_does_not_claim_exact_equivalence_by_default():
    graph_contract = json.loads((ROOT / "data/canonical_data_contract.json").read_text(encoding="utf-8"))
    mapping_values = set(graph_contract["entities"]["provenance_link"]["mapping_types"])
    # The active contract must explicitly support uncertain mapping classes; mapping names alone are not equivalence.
    assert {"exact", "reviewed_related", "weak_lexical", "unresolved"} <= mapping_values
    policy_text = json.dumps(json.loads(DOMAIN_POLICY_PATH.read_text(encoding="utf-8"))).casefold()
    assert "not_official_taxonomy" in policy_text or "hypotheses" in policy_text
