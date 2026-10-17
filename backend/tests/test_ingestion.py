from __future__ import annotations

import csv
import hashlib
import json
import zipfile
from pathlib import Path

import httpx
import pytest

from app.services.ingestion.common import IngestionError, IngestionValidationError, read_csv_table, sha256_file
from app.services.ingestion.downloads import ASSETS, download_asset
from app.services.ingestion.pipeline import (
    import_curated_snapshot,
    import_esco_package,
    import_onet_files,
)
from app.services.provenance import ProvenanceRepository

RETRIEVED = "2026-10-17T08:00:00Z"


def _write_csv(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="")


def _write_onet_pair(tmp_path: Path, *, invalid_scale_value: str | None = None, duplicate_skill: bool = False) -> tuple[Path, Path]:
    occupations = tmp_path / "occupation_data.csv"
    skills = tmp_path / "essential_skills.csv"
    _write_csv(
        occupations,
        "O*NET-SOC Code,Title,Description\n"
        "15-1252.00,Software Developers,Develop software systems.\n",
    )
    scale_value = invalid_scale_value if invalid_scale_value is not None else "4.25"
    rows = [
        "15-1252.00,Software Developers,2.A.1.a,Reading Comprehension,IM," + scale_value + ",N,N",
        "15-1252.00,Software Developers,2.A.1.a,Reading Comprehension,LV,5.25,N,N",
        "15-1252.00,Software Developers,2.A.1.b,Active Listening,IM,4.00,Y,N",
        "15-1252.00,Software Developers,2.A.1.c,Writing,LV,,N,Y",
    ]
    if duplicate_skill:
        rows.append(rows[0])
    _write_csv(
        skills,
        "O*NET-SOC Code,Title,Element ID,Element Name,Scale ID,Data Value,Recommend Suppress,Not Relevant\n"
        + "\n".join(rows) + "\n",
    )
    for path, asset_id in [(occupations, "onet_occupation_data"), (skills, "onet_essential_skills")]:
        asset = ASSETS[asset_id]
        metadata = {
            "metadata_schema_version": 1,
            "asset_id": asset.asset_id,
            "source_id": asset.source_id,
            "source_url": asset.url,
            "official_release_url": "https://www.onetcenter.org/db_releases.html",
            "filename": path.name,
            "retrieved_at": RETRIEVED,
            "source_version": asset.source_version,
            "release_date": asset.release_date,
            "license_reference": asset.license_url,
            "license_summary": asset.license_summary,
            "content_type": "text/csv",
            "byte_size": path.stat().st_size,
            "sha256": sha256_file(path),
            "header_validation": "test-fixture-header-valid",
            "source_data_is_live": False,
        }
        Path(str(path) + ".metadata.json").write_text(json.dumps(metadata), encoding="utf-8")
    return occupations, skills


def _write_esco_zip(path: Path, *, languages: tuple[str, ...] = ("en",), orphan_relation: bool = False) -> Path:
    occupation_uri = "http://data.europa.eu/esco/occupation/test-software-dev"
    skill_uri = "http://data.europa.eu/esco/skill/test-debugging"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for language in languages:
            archive.writestr(
                f"classification/occupations_{language}.csv",
                "conceptUri,preferredLabel,description,code,status,conceptType\n"
                f"{occupation_uri},Software developer,Build software from requirements,2512.4,released,occupation\n",
            )
            archive.writestr(
                f"classification/skills_{language}.csv",
                "conceptUri,preferredLabel,description,conceptType\n"
                f"{skill_uri},Debug software,Identify and correct software defects,skill/competence\n",
            )
            related_skill = "http://data.europa.eu/esco/skill/missing" if orphan_relation else skill_uri
            archive.writestr(
                f"classification/occupationSkillRelations_{language}.csv",
                "occupationUri,skillUri,relationType,skillType\n"
                f"{occupation_uri},{related_skill},essential,skill/competence\n",
            )
    return path


def test_curated_snapshot_imports_with_traceability_and_is_idempotent(tmp_path):
    db_path = tmp_path / "curated.db"
    repo = ProvenanceRepository(db_path)
    state_file = tmp_path / "state.json"
    report1 = import_curated_snapshot(repository=repo, state_path=state_file)
    counts1 = repo.count()
    report2 = import_curated_snapshot(repository=repo, state_path=state_file)
    counts2 = repo.count()

    assert report1.records_processed == 10
    assert report1.facts_upserted == 32
    assert report1.details["records_by_source"] == {
        "onet_online_curated_sample": 9,
        "esco_curated_sample": 1,
    }
    assert counts1 == counts2
    assert report2.status == "curated_extract_imported"
    snapshot_id = report1.details["snapshot_id"]
    fact = repo.get_career_fact(f"fact:occupation:onetonline:{snapshot_id}:15-1252-00:summary")
    assert fact is not None
    assert fact.source.source_type.value == "curated_extract"
    assert fact.source.source_version
    assert fact.source.checksum_sha256 == report1.file_sha256
    assert fact.entity.normalized_values["not_student_evidence"] is True
    assert fact.entity.normalized_values["curation_domain"] == "technology"
    assert fact.entity.normalized_values["curation_domain_is_editorial"] is True
    assert "curation_domain" not in fact.entity.source_values
    assert len(fact.entity.normalized_values["selected_essential_skills"]) == 5
    assert "not a complete" in " ".join(fact.source.limitations).lower()


def test_curated_snapshot_import_refuses_a_live_fetch_claim(tmp_path):
    snapshot = json.loads(Path("data/curated/occupations_snapshot.json").read_text(encoding="utf-8"))
    snapshot["runtime_fetch_performed"] = True
    snapshot_path = tmp_path / "false-live-claim.json"
    snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
    repo = ProvenanceRepository(tmp_path / "no-write.db")
    with pytest.raises(IngestionValidationError, match="must not claim"):
        import_curated_snapshot(snapshot_path, repository=repo, state_path=tmp_path / "state.json")
    assert repo.count() == {"sources": 0, "entities": 0, "provenance_links": 0, "career_facts": 0}


def test_onet_import_validates_provenance_suppression_and_idempotence(tmp_path):
    occupations, skills = _write_onet_pair(tmp_path)
    repo = ProvenanceRepository(tmp_path / "onet.db")
    state_file = tmp_path / "state.json"
    report = import_onet_files(occupations, skills, repository=repo, state_path=state_file)
    counts = repo.count()
    snapshot_id = report.details["snapshot_id"]
    source_record_id = f"{snapshot_id}:occupation:15-1252.00"
    entity_id = f"occupation:onet:{snapshot_id}:15-1252.00"
    import sqlite3
    with sqlite3.connect(repo.db_path) as db:
        before_source = db.execute(
            "SELECT accessed_at, ingested_at FROM source_records WHERE source_id=? AND source_record_id=?",
            ("onet_database", source_record_id),
        ).fetchone()
        before_entity = db.execute(
            "SELECT accessed_at, ingested_at FROM canonical_entities WHERE internal_id=?",
            (entity_id,),
        ).fetchone()
        before_link = db.execute(
            "SELECT created_at FROM provenance_links WHERE entity_internal_id=?",
            (entity_id,),
        ).fetchone()
    report_again = import_onet_files(occupations, skills, repository=repo, state_path=state_file)
    with sqlite3.connect(repo.db_path) as db:
        after_source = db.execute(
            "SELECT accessed_at, ingested_at FROM source_records WHERE source_id=? AND source_record_id=?",
            ("onet_database", source_record_id),
        ).fetchone()
        after_entity = db.execute(
            "SELECT accessed_at, ingested_at FROM canonical_entities WHERE internal_id=?",
            (entity_id,),
        ).fetchone()
        after_link = db.execute(
            "SELECT created_at FROM provenance_links WHERE entity_internal_id=?",
            (entity_id,),
        ).fetchone()

    assert report.source_id == "onet_database"
    assert report.status == "imported"
    assert report.records_processed == 5
    assert report.records_upserted == 5
    assert report.suppressed_ratings_not_displayed == 2
    assert report_again.records_upserted == report.records_upserted
    assert repo.count() == counts
    assert before_source == after_source
    assert before_entity == after_entity
    assert before_link == after_link
    assert report.details["normalizer_schema_version"] == report_again.details["normalizer_schema_version"]
    snapshot_id = report.details["snapshot_id"]
    assert repo.get_career_fact(f"fact:occupation:onet:{snapshot_id}:15-1252.00:title") is not None
    visible_skill_fact = f"fact:occupation_skill_observation:onet:{snapshot_id}:essential-skill-15-1252-00-2-a-1-a-im:rating"
    suppressed_skill_fact = f"fact:occupation_skill_observation:onet:{snapshot_id}:essential-skill-15-1252-00-2-a-1-b-im:rating"
    assert repo.get_career_fact(visible_skill_fact) is not None
    assert repo.get_career_fact(suppressed_skill_fact) is None
    observation = repo.get_career_fact(visible_skill_fact)
    assert observation is not None
    assert observation.value["value"] == 4.25
    assert observation.value["source_version"] == "O*NET Database 31.0"
    assert observation.entity.normalized_values["value_is_student_score"] is False


def test_onet_identical_duplicate_rows_are_skipped(tmp_path):
    occupations, skills = _write_onet_pair(tmp_path, duplicate_skill=True)
    repo = ProvenanceRepository(tmp_path / "duplicate.db")
    report = import_onet_files(occupations, skills, repository=repo, state_path=tmp_path / "state.json")
    assert report.duplicate_rows_skipped == 1
    assert report.records_processed == 5


def test_onet_out_of_range_scale_is_rejected_before_any_database_write(tmp_path):
    occupations, skills = _write_onet_pair(tmp_path, invalid_scale_value="5.5")
    repo = ProvenanceRepository(tmp_path / "invalid-scale.db")
    with pytest.raises(IngestionValidationError, match="expected range 1–5"):
        import_onet_files(occupations, skills, repository=repo, state_path=tmp_path / "state.json")
    assert repo.count() == {"sources": 0, "entities": 0, "provenance_links": 0, "career_facts": 0}


def test_onet_conflicting_duplicate_occupation_fails_before_write(tmp_path):
    occupations = tmp_path / "occupation_data.csv"
    skills = tmp_path / "essential_skills.csv"
    _write_csv(
        occupations,
        "O*NET-SOC Code,Title,Description\n"
        "15-1252.00,Software Developers,Description A\n"
        "15-1252.00,Software Developers,Description B\n",
    )
    _write_csv(
        skills,
        "O*NET-SOC Code,Title,Element ID,Element Name,Scale ID,Data Value,Recommend Suppress,Not Relevant\n"
        "15-1252.00,Software Developers,2.A.1.a,Reading Comprehension,IM,4.25,N,N\n",
    )
    # Metadata is deliberately valid so the conflicting key is the actual failure.
    for path, asset_id in [(occupations, "onet_occupation_data"), (skills, "onet_essential_skills")]:
        asset = ASSETS[asset_id]
        Path(str(path) + ".metadata.json").write_text(json.dumps({
            "asset_id": asset_id, "source_id": asset.source_id, "source_url": asset.url,
            "filename": path.name, "retrieved_at": RETRIEVED, "source_version": asset.source_version,
            "release_date": asset.release_date, "license_reference": asset.license_url,
            "license_summary": asset.license_summary, "sha256": sha256_file(path),
        }), encoding="utf-8")
    repo = ProvenanceRepository(tmp_path / "duplicate-conflict.db")
    with pytest.raises(IngestionValidationError, match="conflicting rows"):
        import_onet_files(occupations, skills, repository=repo, state_path=tmp_path / "state.json")
    assert repo.count() == {"sources": 0, "entities": 0, "provenance_links": 0, "career_facts": 0}


def test_onet_checksum_tampering_is_rejected(tmp_path):
    occupations, skills = _write_onet_pair(tmp_path)
    sidecar = Path(str(occupations) + ".metadata.json")
    metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    metadata["sha256"] = "0" * 64
    sidecar.write_text(json.dumps(metadata), encoding="utf-8")
    repo = ProvenanceRepository(tmp_path / "checksum.db")
    with pytest.raises(IngestionValidationError, match="Checksum mismatch"):
        import_onet_files(occupations, skills, repository=repo, state_path=tmp_path / "state.json")
    assert repo.count() == {"sources": 0, "entities": 0, "provenance_links": 0, "career_facts": 0}


def test_esco_package_imports_occupation_skill_relations_and_is_idempotent(tmp_path):
    package = _write_esco_zip(tmp_path / "esco.zip")
    repo = ProvenanceRepository(tmp_path / "esco.db")
    report = import_esco_package(
        package,
        source_version="ESCO v1.2.1",
        release_date="2025-12-10",
        retrieved_at=RETRIEVED,
        repository=repo,
        state_path=tmp_path / "state.json",
    )
    counts = repo.count()
    repeated = import_esco_package(
        package,
        source_version="ESCO v1.2.1",
        release_date="2025-12-10",
        retrieved_at=RETRIEVED,
        repository=repo,
        state_path=tmp_path / "state.json",
    )
    assert report.details["occupation_records"] == 1
    assert report.details["skill_records"] == 1
    assert report.details["occupation_skill_relations"] == 1
    assert report.records_upserted == 3
    assert report.facts_upserted == 5  # occupation label + description, skill label + description, relation
    assert repo.count() == counts
    assert repeated.records_upserted == 3
    snapshot_id = report.details["snapshot_id"]
    occupation_uri = "http://data.europa.eu/esco/occupation/test-software-dev"
    uri_digest = hashlib.sha256(occupation_uri.encode("utf-8")).hexdigest()[:24]
    assert repo.get_career_fact(f"fact:occupation:esco:{snapshot_id}:{uri_digest}:label") is not None
    relation_digest = hashlib.sha256(
        "http://data.europa.eu/esco/occupation/test-software-dev|http://data.europa.eu/esco/skill/test-debugging|essential|".encode("utf-8")
    ).hexdigest()[:32]
    relation_facts = [repo.get_career_fact(
        f"fact:occupation_skill_observation:esco:{snapshot_id}:{relation_digest}:relation"
    )]
    assert relation_facts[0] is not None
    assert relation_facts[0].value["taxonomy"] == "ESCO"
    assert relation_facts[0].source.release_date == "2025-12-10"


def test_esco_language_selection_is_explicit_and_deterministic(tmp_path):
    package = _write_esco_zip(tmp_path / "multi-language.zip", languages=("en", "fr"))
    report = import_esco_package(
        package,
        source_version="ESCO v1.2.1",
        release_date="2025-12-10",
        retrieved_at=RETRIEVED,
        language="en",
        repository=ProvenanceRepository(tmp_path / "esco-en.db"),
        state_path=tmp_path / "state.json",
    )
    assert report.details["selected_members"]["occupations"].endswith("occupations_en.csv")
    assert report.details["selected_members"]["skills"].endswith("skills_en.csv")


def test_esco_orphan_relation_fails_before_any_write(tmp_path):
    package = _write_esco_zip(tmp_path / "orphan.zip", orphan_relation=True)
    repo = ProvenanceRepository(tmp_path / "esco-orphan.db")
    with pytest.raises(IngestionValidationError, match="missing from supplied"):
        import_esco_package(
            package,
            source_version="ESCO v1.2.1",
            release_date="2025-12-10",
            retrieved_at=RETRIEVED,
            repository=repo,
            state_path=tmp_path / "state.json",
        )
    assert repo.count() == {"sources": 0, "entities": 0, "provenance_links": 0, "career_facts": 0}


def test_esco_refuses_relations_without_skills(tmp_path):
    package = _write_esco_zip(tmp_path / "esco.zip")
    with pytest.raises(IngestionValidationError, match="require the matching skill concepts"):
        import_esco_package(
            package,
            source_version="ESCO v1.2.1",
            retrieved_at=RETRIEVED,
            include_skills=False,
            include_relations=True,
            repository=ProvenanceRepository(tmp_path / "no-skills.db"),
            state_path=tmp_path / "state.json",
        )


def test_esco_requires_timezone_aware_retrieval_time(tmp_path):
    package = _write_esco_zip(tmp_path / "esco.zip")
    with pytest.raises(IngestionValidationError, match="must include a timezone"):
        import_esco_package(
            package,
            source_version="ESCO v1.2.1",
            retrieved_at="2026-10-17T08:00:00",
            repository=ProvenanceRepository(tmp_path / "naive-time.db"),
            state_path=tmp_path / "state.json",
        )


def test_download_onet_uses_allowlisted_host_and_writes_hash_sidecar(tmp_path):
    asset = ASSETS["onet_occupation_data"]
    payload = b"O*NET-SOC Code,Title,Description\n15-1252.00,Software Developers,Build software\n"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == asset.url
        return httpx.Response(200, headers={"content-type": "text/csv"}, content=payload, request=request)

    def factory(**kwargs):
        return httpx.Client(transport=httpx.MockTransport(handler), **kwargs)

    metadata = download_asset(
        "onet_occupation_data",
        raw_root=tmp_path / "raw",
        state_path=tmp_path / "state.json",
        runs_root=tmp_path / "runs",
        retries=0,
        client_factory=factory,
    )
    target = tmp_path / "raw" / "onet_database" / "O*NET_Database_31.0" / "occupation_data.csv"
    assert target.read_bytes() == payload
    assert metadata["sha256"] == hashlib.sha256(payload).hexdigest()
    assert json.loads(Path(str(target) + ".metadata.json").read_text(encoding="utf-8"))["header_validation"] == "passed"
    state = json.loads((tmp_path / "state.json").read_text(encoding="utf-8"))
    assert state["sources"]["onet_database"]["last_attempt"]["status"] == "downloaded"


def test_download_onet_refuses_unknown_asset_without_network(tmp_path):
    from app.services.ingestion.common import IngestionError
    with pytest.raises(IngestionError, match="Unknown downloadable asset"):
        download_asset("arbitrary_url", raw_root=tmp_path / "raw", state_path=tmp_path / "state.json")


def test_versioned_imports_keep_prior_snapshot_facts_when_source_file_changes(tmp_path):
    occupations, skills = _write_onet_pair(tmp_path)
    repo = ProvenanceRepository(tmp_path / "versions.db")
    state_file = tmp_path / "state.json"
    first = import_onet_files(occupations, skills, repository=repo, state_path=state_file)
    first_fact_id = f"fact:occupation:onet:{first.details['snapshot_id']}:15-1252.00:description"
    first_fact = repo.get_career_fact(first_fact_id)
    assert first_fact is not None
    before = repo.count()

    # Same declared release, different artifact checksum: create a new immutable snapshot.
    occupations.write_text(
        "O*NET-SOC Code,Title,Description\n"
        "15-1252.00,Software Developers,Updated source description.\n",
        encoding="utf-8",
        newline="",
    )
    occ_asset = ASSETS["onet_occupation_data"]
    occ_sidecar = Path(str(occupations) + ".metadata.json")
    occ_meta = json.loads(occ_sidecar.read_text(encoding="utf-8"))
    occ_meta["sha256"] = sha256_file(occupations)
    occ_meta["byte_size"] = occupations.stat().st_size
    occ_sidecar.write_text(json.dumps(occ_meta), encoding="utf-8")

    second = import_onet_files(occupations, skills, repository=repo, state_path=state_file)
    assert second.details["snapshot_id"] != first.details["snapshot_id"]
    second_fact_id = f"fact:occupation:onet:{second.details['snapshot_id']}:15-1252.00:description"
    second_fact = repo.get_career_fact(second_fact_id)
    assert second_fact is not None
    assert second_fact.value["description"] == "Updated source description."
    # A previous fact remains queryable and is not overwritten by a new source snapshot.
    assert repo.get_career_fact(first_fact_id) == first_fact
    after = repo.count()
    assert after["entities"] > before["entities"]
    assert after["career_facts"] > before["career_facts"]


def test_failed_import_is_written_to_state_without_marking_success(tmp_path):
    state_file = tmp_path / "state.json"
    repo = ProvenanceRepository(tmp_path / "failed.db")
    with pytest.raises(IngestionError):
        import_onet_files(
            tmp_path / "missing-occupations.csv",
            tmp_path / "missing-skills.csv",
            repository=repo,
            state_path=state_file,
        )
    state = json.loads(state_file.read_text(encoding="utf-8"))
    source_state = state["sources"]["onet_database"]
    assert source_state["last_attempt"]["status"] == "import_failed"
    assert "last_successful_operation" not in source_state
    assert repo.count() == {"sources": 0, "entities": 0, "provenance_links": 0, "career_facts": 0}


def test_short_csv_rows_are_rejected_instead_of_silently_filling_missing_cells(tmp_path):
    path = tmp_path / "short-row.csv"
    path.write_text("a,b,c\n1,2\n", encoding="utf-8")
    with pytest.raises(IngestionValidationError, match="too few fields"):
        read_csv_table(path)


def test_download_rejects_same_host_https_to_http_redirect_before_second_request(tmp_path):
    asset = ASSETS["onet_occupation_data"]
    requests = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(str(request.url))
        return httpx.Response(302, headers={"location": "http://www.onetcenter.org/unsafe.csv"}, request=request)

    def factory(**kwargs):
        return httpx.Client(transport=httpx.MockTransport(handler), **kwargs)

    with pytest.raises(IngestionError, match="HTTPS host/port allow-list"):
        download_asset(
            "onet_occupation_data",
            raw_root=tmp_path / "raw",
            state_path=tmp_path / "state.json",
            runs_root=tmp_path / "runs",
            retries=0,
            client_factory=factory,
        )
    assert requests == [asset.url]


@pytest.mark.parametrize("kwargs", [{"retries": -1}, {"retries": 11}, {"timeout_seconds": 0}, {"timeout_seconds": float("nan")}])
def test_download_rejects_invalid_retry_or_timeout_configuration(tmp_path, kwargs):
    with pytest.raises(IngestionValidationError, match="retries|timeout_seconds"):
        download_asset("onet_occupation_data", raw_root=tmp_path / "raw", **kwargs)


def test_successful_official_import_updates_manifest_only_after_success(tmp_path):
    import yaml

    occupations, skills = _write_onet_pair(tmp_path)
    manifest_path = tmp_path / "manifest.yaml"
    manifest = yaml.safe_load(Path("data/sources_manifest.yaml").read_text(encoding="utf-8"))
    manifest_path.write_text(yaml.safe_dump(manifest, sort_keys=False), encoding="utf-8")
    report = import_onet_files(
        occupations,
        skills,
        repository=ProvenanceRepository(tmp_path / "manifest.db"),
        state_path=tmp_path / "state.json",
        manifest_path=manifest_path,
    )
    updated = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    source = next(item for item in updated["sources"] if item["id"] == "onet_database")
    assert source["integration_status"] == "versioned_snapshot_imported"
    assert source["last_import"]["snapshot_id"] == report.details["snapshot_id"]
    assert source["last_import"]["checksum_sha256"] == report.file_sha256
    assert source["last_import"]["source_data_is_live"] is False
    assert source["last_import"]["normalizer_schema_version"] == "2"
    assert "origin_not_cryptographically_attested" in source["last_import"]["acquisition_method"]
    assert "not_cryptographically_attested" in source["runtime_access_status"]


def test_esco_import_accepts_official_documented_csv_headers_and_concept_type_codes(tmp_path):
    package = tmp_path / "esco-official-schema.zip"
    occupation_uri = "http://data.europa.eu/esco/occupation/official-occupation"
    skill_uri = "http://data.europa.eu/esco/skill/official-skill"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "classification/occupations_en.csv",
            "Concept URI,Concept type,ISCO code,Concept PT,Definition,Parent Concept URI,Parent ISCO code\n"
            f"{occupation_uri},OC,2512,Software developer,Develops software,,2512\n",
        )
        archive.writestr(
            "classification/skills_en.csv",
            "Concept URI,Concept type,Concept PT,Definition\n"
            f"{skill_uri},SK,Debugging,Identify and resolve software defects\n",
        )
        archive.writestr(
            "classification/occupationSkillRelations_en.csv",
            "occupationUri,occupationLabel,skillType,skillUri,skillLabel,relationshipType,relationRelevance\n"
            f"{occupation_uri},Software developer,SK,{skill_uri},Debugging,essential,1\n",
        )
    repo = ProvenanceRepository(tmp_path / "esco-official-schema.db")
    report = import_esco_package(
        package,
        source_version="ESCO v1.2.1",
        release_date="2025-12-10",
        retrieved_at=RETRIEVED,
        repository=repo,
        state_path=tmp_path / "state.json",
    )
    assert report.status == "imported"
    assert report.details["occupation_records"] == 1
    assert report.details["skill_records"] == 1
    assert report.details["occupation_skill_relations"] == 1
    snapshot_id = report.details["snapshot_id"]
    uri_digest = hashlib.sha256(occupation_uri.encode("utf-8")).hexdigest()[:24]
    occupation = repo.get_career_fact(f"fact:occupation:esco:{snapshot_id}:{uri_digest}:label")
    assert occupation is not None
    assert occupation.value["preferred_label"] == "Software developer"
    assert occupation.entity.normalized_values["concept_uri"] == occupation_uri
    assert occupation.entity.normalized_values["display_url"].startswith("https://esco.ec.europa.eu/")
    assert str(occupation.provenance.source_uri) == occupation_uri

    relation_digest = hashlib.sha256(
        f"{occupation_uri}|{skill_uri}|essential|1".encode("utf-8")
    ).hexdigest()[:32]
    relation = repo.get_career_fact(
        f"fact:occupation_skill_observation:esco:{snapshot_id}:{relation_digest}:relation"
    )
    assert relation is not None
    assert relation.value["relation_type"] == "essential"
    assert relation.value["relation_relevance"] == "1"
    assert relation.entity.source_values["relationRelevance"] == "1"


def test_esco_relation_relevance_is_part_of_relation_identity(tmp_path):
    package = tmp_path / "esco-distinct-relevance.zip"
    occupation_uri = "http://data.europa.eu/esco/occupation/relevance-test"
    skill_uri = "http://data.europa.eu/esco/skill/relevance-test"
    with zipfile.ZipFile(package, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "classification/occupations_en.csv",
            "Concept URI,Concept type,ISCO code,Concept PT\n"
            f"{occupation_uri},OC,2512,Software developer\n",
        )
        archive.writestr(
            "classification/skills_en.csv",
            "Concept URI,Concept type,Concept PT\n"
            f"{skill_uri},SK,Debugging\n",
        )
        archive.writestr(
            "classification/occupationSkillRelations_en.csv",
            "occupationUri,skillUri,relationshipType,relationRelevance\n"
            f"{occupation_uri},{skill_uri},essential,1\n"
            f"{occupation_uri},{skill_uri},essential,2\n",
        )
    repo = ProvenanceRepository(tmp_path / "esco-distinct-relevance.db")
    report = import_esco_package(
        package,
        source_version="ESCO v1.2.1",
        release_date="2025-12-10",
        retrieved_at=RETRIEVED,
        repository=repo,
        state_path=tmp_path / "state.json",
    )
    assert report.details["occupation_skill_relations"] == 2
    assert report.duplicate_rows_skipped == 0
    assert report.records_upserted == 4
    assert report.facts_upserted == 4
    relation_values = []
    for relevance in ("1", "2"):
        digest = hashlib.sha256(
            f"{occupation_uri}|{skill_uri}|essential|{relevance}".encode("utf-8")
        ).hexdigest()[:32]
        fact = repo.get_career_fact(
            f"fact:occupation_skill_observation:esco:{report.details['snapshot_id']}:{digest}:relation"
        )
        assert fact is not None
        relation_values.append(fact.value["relation_relevance"])
    assert relation_values == ["1", "2"]


def test_normalizer_version_is_part_of_immutable_snapshot_identity(tmp_path, monkeypatch):
    import app.services.ingestion.pipeline as pipeline

    occupations, skills = _write_onet_pair(tmp_path)
    repo = ProvenanceRepository(tmp_path / "normalizer-versions.db")
    first = import_onet_files(occupations, skills, repository=repo, state_path=tmp_path / "state.json")
    monkeypatch.setattr(pipeline, "NORMALIZER_SCHEMA_VERSION", "3")
    second = import_onet_files(occupations, skills, repository=repo, state_path=tmp_path / "state.json")
    assert first.file_sha256 == second.file_sha256
    assert first.details["snapshot_id"] != second.details["snapshot_id"]
    assert first.details["normalizer_schema_version"] == "2"
    assert second.details["normalizer_schema_version"] == "3"
    old_fact_id = f"fact:occupation:onet:{first.details['snapshot_id']}:15-1252.00:description"
    new_fact_id = f"fact:occupation:onet:{second.details['snapshot_id']}:15-1252.00:description"
    assert repo.get_career_fact(old_fact_id) is not None
    assert repo.get_career_fact(new_fact_id) is not None


def test_invalid_manifest_is_rejected_before_official_import_writes(tmp_path):
    import yaml

    occupations, skills = _write_onet_pair(tmp_path)
    manifest_path = tmp_path / "invalid-manifest.yaml"
    manifest_path.write_text(yaml.safe_dump({"sources": []}), encoding="utf-8")
    repo = ProvenanceRepository(tmp_path / "manifest-preflight.db")
    with pytest.raises(IngestionValidationError, match="exactly one record"):
        import_onet_files(
            occupations,
            skills,
            repository=repo,
            state_path=tmp_path / "state.json",
            manifest_path=manifest_path,
        )
    assert repo.count() == {"sources": 0, "entities": 0, "provenance_links": 0, "career_facts": 0}


def test_corrupt_ingestion_state_is_not_silently_overwritten(tmp_path):
    from app.services.ingestion.common import record_run_event

    state_path = tmp_path / "corrupt-state.json"
    original = "{not valid audit history"
    state_path.write_text(original, encoding="utf-8")
    with pytest.raises(IngestionValidationError, match="existing run history was not overwritten"):
        record_run_event({"source_id": "test", "status": "imported"}, state_path=state_path)
    assert state_path.read_text(encoding="utf-8") == original
