# SkillScope AI — Ingestion Pipeline (Stage 6)

## Status

The Stage 6 ingestion pipeline has passed a second, independent code/data-integrity audit. The current normalizer schema version is `2`; it was bumped after ESCO relation metadata began participating in relationship identity, so downstream snapshots are namespaced separately from version `1`. Its code and local fixtures are tested, but authentic full-source imports are not claimed as runtime-verified. This environment's direct O*NET downloads and ESCO API attempt failed during DNS resolution. The bundled data is therefore a **manually curated, source-backed extract** with nine O*NET OnLine occupation profiles and one ESCO occupation concept, not a live response, bulk dataset, or complete occupational knowledge base.

Current external source state:

- O*NET 31.0 bulk files: both direct download attempts failed DNS; not integrated.
- ESCO public API: one request failed DNS; not integrated.
- ESCO official CSV ZIP: import route implemented, but its portal selection/email download workflow was not completed from this environment; not integrated.
- NCS and NSDC: link-only references pending record-level reuse confirmation.
- PLFS: no table imported; aggregate context only.
- Curated occupation snapshot: includes nine O*NET OnLine profiles and one ESCO occupation concept with source links, version/context and adaptation notes. O*NET Essential Skills labels are retained as occupation-scoped references without stable skill IDs or ratings; editorial coverage tags are not official taxonomies. It is a small curated extract, never a live feed.

## Design rules

1. **Allow-list official download URLs.** Downloader calls accept an asset key, not an arbitrary user-supplied URL. Each request and redirect hop must remain HTTPS on an allow-listed host and port; HTTP status, response content, file size, expected CSV headers and retry rules are checked. A locally validated metadata sidecar/checksum is not a cryptographic signature of the remote publisher or proof of origin.
2. **Download to raw storage.** Files are written under `data/raw/` using a `.part` temporary file, then atomically renamed after validation. `data/raw/` is git-ignored and excluded from checkpoint ZIPs.
3. **Write an artifact sidecar.** Successful O*NET downloads create adjacent `.metadata.json` with exact URL, official release page, version, release date, licence, retrieval timestamp, byte size, header check and SHA-256.
4. **Validate before database writes.** CSV encodings/headers, stable identifiers, duplicate conflicts, O*NET row values/flags/scale bounds, ESCO language selection and relationship endpoints are checked before import writes begin. Exact duplicate rows are skipped; conflicting duplicate identifiers fail closed.
5. **Preserve source lineage.** Raw source fields and normalized values remain separate. Imported records retain source/source-record IDs, geography, version, retrieval/ingestion timestamps, licence, checksum, mapping notes and limitations.
6. **Versioned, idempotent imports.** Stable IDs and upserts let an identical source snapshot be rerun without duplicating its canonical record set. Snapshot IDs include a hash of the source artifact plus `NORMALIZER_SCHEMA_VERSION`; bump the normalizer version deliberately when normalization/fact semantics change. If source content or normalizer version changes, the new snapshot receives a different namespace and the old snapshot is retained instead of silently overwritten. The manifest's `last_import.snapshot_id` is the active full-source snapshot pointer; downstream readers must scope queries to that active ID rather than mixing all historical snapshots.
7. **Status reports are explicit.** A failure updates the central `data/ingestion_state.json` ledger. Downloader attempts also write one latest-attempt summary per asset into `data/ingestion_runs/`; import events are not separately written there. A source remains `not_integrated` until validated data has actually been imported. Curated extracts do not count as full official-source integration.
8. **No individual labour-market scoring.** PLFS or other aggregate demand statistics are a separate dated/geographic context layer, never a student aptitude/interest signal.

## Commands

Run commands from the repository root in a Python environment with `backend/requirements.txt` installed.

### Inspect source and ingestion status

```bash
PYTHONPATH=backend python -m app.services.ingestion.cli status
```

### Import the bundled curated extract into the local SQLite registry

```bash
PYTHONPATH=backend python -m app.services.ingestion.cli import-curated
```

Use `--database`, `--state-file`, `--manifest`, and `--snapshot` to isolate a test or change paths. This command imports only the explicitly labelled curated snapshot (currently 10 occupation records: nine O*NET OnLine profiles and one ESCO concept, with source-listed tasks and Essential Skills labels where curated). It does not call any external source.

### Download the pinned O*NET 31.0 files

Only in a network-enabled environment:

```bash
PYTHONPATH=backend python -m app.services.ingestion.cli download-onet onet_occupation_data
PYTHONPATH=backend python -m app.services.ingestion.cli download-onet onet_essential_skills
```

The command downloads only preconfigured allow-listed official files. If DNS/network access fails, it records a failed run and leaves the source not integrated. Do not hand-edit the download sidecar to disguise a failure.

### Import downloaded O*NET files

The default downloader paths are under `data/raw/onet_database/O*NET_Database_31.0/`. Confirm the actual paths and sidecar JSON before running:

```bash
PYTHONPATH=backend python -m app.services.ingestion.cli import-onet \
  --occupations 'data/raw/onet_database/O*NET_Database_31.0/occupation_data.csv' \
  --essential-skills 'data/raw/onet_database/O*NET_Database_31.0/essential_skills.csv'
```

The importer rejects mismatched versions, invalid checksums, missing source IDs, unknown scales, out-of-range values, bad flags and skill rows that refer to unknown occupations. Occupation ratings are source occupational descriptors, not student skill scores.

### Import an ESCO official CSV ZIP

The ESCO portal requires selecting a dataset version, classification content, language and CSV format and uses a request/email-download flow. Download the ZIP manually from the [official ESCO download page](https://esco.ec.europa.eu/en/use-esco/download), retain the package unchanged, and verify the selected version and language shown by the portal/package before importing.

```bash
PYTHONPATH=backend python -m app.services.ingestion.cli import-esco \
  --package /path/to/official-esco-classification-en.zip \
  --source-version 'ESCO v1.2.1' \
  --release-date 2025-12-10 \
  --retrieved-at 'YYYY-MM-DDTHH:MM:SSZ' \
  --language en
```

Replace the example timestamp with the actual retrieval timestamp and select `ESCO v1.2.1` only when that is the exact version selected in the official portal. The importer pins/checks the operator-declared version and release date, but the ZIP/CSV payload does not independently cryptographically attest its own version label; keep the unmodified original package and portal/download metadata so this assertion can be audited. The importer understands official-style concept headers such as `Concept URI`, `Concept type`, `ISCO code`, and `Concept PT`, along with short concept-type codes such as `OC`/`OG` and `SK`/`SG`. Relation files accept `relationType`/`relationshipType` aliases and preserve `relationRelevance` as raw source data plus a normalized string attribute; relevance participates in relationship identity so rows differing in relevance are not collapsed. It validates language suffixes and relationship endpoints. Relation imports require both occupation and skill concepts from that same export.

## Safe handling and reproducibility

- Do not commit full raw source downloads or secret files.
- Record the official URL, version, exact filename/member, access timestamp, file size, SHA-256, package selection, licence, import report and error/status.
- Keep test fixture data separate from curated source-backed data; fixtures are synthetic and must never appear as sourced facts.
- Keep the original source IDs and terms. Cross-source mappings need their own explicit mapping type and explanation.
- The central event history and per-source latest attempt/success are recorded in `data/ingestion_state.json`. The current files in `data/ingestion_runs/` are downloader latest-attempt summaries, not an independent per-import audit log. The shipped state records observed DNS errors, not fake successful responses.
- Network failures are not evidence that the source is unavailable globally. Re-test in the actual network-enabled developer environment.

## Verification

```bash
PYTHONPATH=backend pytest -q
python -m compileall -q backend/app backend/tests
PYTHONPATH=backend python -m app.services.ingestion.cli status
```

An `imported` result means a local static source snapshot was imported, not that the source is live. The source readiness endpoint is `GET /api/ingestion/status`. Its `active_snapshot` field identifies the active immutable snapshot used by downstream stages. `artifact_sha256` hashes the retrieved source artifact; for the curated fallback, that is the bundled snapshot JSON. Full O*NET/ESCO import remains unverified until a real source package is fetched, validated, and the manifest records its active snapshot.
