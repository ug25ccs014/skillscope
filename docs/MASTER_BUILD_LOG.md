# SkillScope Master Build Log

## Stage 1 — Greenfield initialization and runnable foundation

**Status:** Completed with one environment blocker; approved by user and carried forward.

**Objective:** Establish a clean greenfield project, document architecture/product principles, and implement a minimal real frontend/backend connectivity shell.

**Files created/changed:**
- `.gitignore`, `.env.example`, `README.md`
- `frontend/package.json`, `frontend/.env.example`, TypeScript/Vite/Tailwind/PostCSS configuration, `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`
- `backend/requirements.txt`, `backend/app/__init__.py`, `backend/app/main.py`, `backend/tests/test_main.py`
- `data/sources_manifest.yaml`
- `docs/PRODUCT_CONTRACT.md`, `docs/DECISIONS.md`, `docs/PROJECT_STATUS.md`, `docs/MASTER_BUILD_LOG.md`

**Checks run:**
- Verified runtime versions: Python 3.13.5, Node.js v22.16.0, npm 10.9.2, Git 2.47.3.
- `cd backend && PYTHONPATH=. pytest -q` — **3 passed**.
- `python -m compileall -q app tests` from `backend/` — passed.
- Live `GET /api/health` — **HTTP 200**.
- npm registry lookup/install failed with `EAI_AGAIN`; frontend dependency install, typecheck, and build remain unverified.

**Outcome:** Backend health endpoint and tests verified. Frontend sources/configuration scaffolded but packages are not installed in this network-restricted environment.

**Unresolved risks:** Frontend dependencies and build not verified; career/skills sources are not yet audited or integrated.

## Stage 2 — Product contract and MVP boundary

**Status:** Completed, approved, and carried forward into Stage 3.

**Objective:** Lock the product promise, target personas, coherent end-to-end MVP journey, deliverable boundary, demo-versus-production distinction, success criteria, assumptions, and source/data integrity requirements before adding the age-calibration implementation in Stage 3.

**Files created/changed:**
- `docs/PRODUCT_CONTRACT.md` — replaced the Stage 1 initial draft with the Stage 2 product contract.
- `docs/MASTER_BUILD_LOG.md` — added this Stage 2 checkpoint.
- `docs/PROJECT_STATUS.md` — updated current stage and scope.
- `README.md` — updated the current development checkpoint and contract description.
- `docs/DECISIONS.md` — added MVP boundary and acceptance-contract decisions.

**Checks run:**
- Manually reviewed the product contract against the Stage 2 exit gate in `docs/20_STAGE_MASTER_PROMPT.md`.
- Verified it specifies primary personas, single vertical journey, required MVP features, non-functional requirements, explicit non-goals, demo scope, success criteria, and known assumptions.
- `cd backend && PYTHONPATH=. pytest -q` — **3 passed** (regression check).
- `python -m compileall -q app tests` from `backend/` — passed (regression check).
- Frontend build remains unverified because npm registry access previously failed; Stage 2 does not change frontend runtime code.

**Outcome:** Product/MVP contract is explicit and locked for the current scope. No student profile, calibration algorithm, career recommendation logic, external dataset, or SQLite persistence is claimed as implemented by this stage.

**Unresolved risks:** External data access/licensing audit remains Stage 4; the actual entry calibration remains Stage 3; frontend build remains blocked until dependency installation succeeds in a network-enabled environment.

**Next stage:** Stage 3 — Age modes and entry calibration, only after explicit user approval.


## Stage 3 — Age modes and entry calibration

**Status:** Implemented; backend checks passed; waiting for user approval before Stage 4.

**Objective:** Build an age-aware, reversible entry strategy that uses age to select activity style and uses existing context to choose a starting path without inferring aptitude or fabricating a student history.

**Files created/changed:**
- `backend/app/schemas/calibration.py` — request/response schemas and enum contracts, including prior-activity summaries, user-named unexplored domains, and optional adult context/timeline.
- `backend/app/services/entry_calibration.py` — versioned deterministic calibration and explanatory rationale.
- `backend/app/api/calibration.py` — `POST /api/calibration`.
- `backend/app/main.py` — route registration and POST CORS support.
- `backend/tests/test_entry_calibration.py` — age boundaries, late entry, missing evidence, clear/unclear goals, contradictory signals, changed goals, re-entry, journey preferences, request validation and API response tests.
- `frontend/src/App.tsx` — responsive calibration form, prior-activity summary, areas with limited exposure, optional adult education/skills/experience/constraints/timeline fields, API connection status, result rationale, evidence-coverage message, next step, and limitation disclosure.
- `frontend/src/vite-env.d.ts` — Vite client type declaration.
- `docs/ENTRY_CALIBRATION.md` — rules, thresholds, precedence, API example, limitation, and acceptance criteria.
- `README.md`, `docs/PROJECT_STATUS.md`, `docs/DECISIONS.md`, and this build log.

**Checks run:**
- `PYTHONPATH=backend pytest -q` — **42 passed**.
- `python -m compileall -q backend/app backend/tests` — passed.
- Live Uvicorn smoke test — `GET /api/health` returned HTTP 200; `POST /api/calibration` returned HTTP 200 with the expected teen mode, broadened-exploration path for a stated goal plus unfamiliar domains, limited evidence-coverage label, rationale, next step, and considered-input list.
- Global TypeScript `transpileModule` on `App.tsx`, `main.tsx`, and `vite.config.ts` — syntax transpilation passed. This does not verify types or bundle output.
- `npm install --no-audit --no-fund --fetch-timeout=8000 --fetch-retries=0` — failed with `EAI_AGAIN` resolving `registry.npmjs.org`. React/Vite packages cannot be installed here; full frontend typecheck and production build remain **unverified**.
- Backend tests exercise the live FastAPI app via `TestClient`, including `POST /api/calibration`, error validation, CORS preflight and all cohort boundaries.

**Calibration behavior:**
- Ages 10–14: `Discover & Shape` / `guided_exploration`.
- Ages 15–17: `Explore & Validate`, with baseline discovery, broadened exploration, stated-interest validation, or a fresh discovery cycle as appropriate.
- Ages 18+: `Develop & Optimize`, with career discovery, goal validation, gap analysis only when all explicit conditions are met, and optional re-entry into discovery. Adult inputs can include education/training, skills, projects/work experience, user-chosen constraints, and a desired timeline.
- Users can summarize activities already tried and name domains they have had little opportunity to try; an unquantified activity summary counts as limited context coverage when the numeric count is zero. For teens, an existing stated direction plus unfamiliar domains can prompt broader exploration. Such domains are treated as opportunities, not weaknesses.
- Reported evidence coverage is `none`, `limited`, `emerging`, or `substantial`; it is not an ability score. Current goal, goal changes, contradictions, journey preference and rationale are returned.
- Calibration is stateless and uses only request inputs. No student record is stored.

**Outcome:** Stage 3 has a testable backend implementation and an interactive frontend source component. The product clearly discloses heuristic limitations and the lack of profile persistence.

**Unresolved risks:** The frontend could not be fully installed, type-checked, or production-built because of external npm DNS/network failure. Data access/licensing and source selection remain Stage 4. The calibration thresholds are hand-authored MVP heuristics and are not scientifically validated.

**Next stage:** Stage 4 — Source research, access feasibility, and licence audit, only after explicit user approval.


## Stage 4 — Source research, access feasibility, and licence audit

**Status:** Research and source-selection decisions completed; local runtime data fetch remains explicitly unverified. No external dataset is integrated.

**Objective:** Review official NCS, NSDC, O*NET, ESCO, and PLFS sources; record access routes, release/version information, licences/terms, attribution needs, source limitations and integration decisions without falsely claiming live connectivity.

**Files created/changed:**
- `docs/DATA_SOURCE_REGISTER.md` — selected/excluded sources, access decisions, exact reviewed links, licence/terms findings, versions, limitations and attribution requirements.
- `docs/SOURCE_ACCESS_AUDIT.md` — distinguishes what official web research confirmed from what was not tested by the application runtime.
- `data/sources_manifest.yaml` — upgraded to manifest version 2 with source role, selection, access method, licence status, version, review date and limitations; every source remains `not_integrated`.
- `docs/PROJECT_STATUS.md`, `README.md`, `docs/DECISIONS.md` — updated current stage and source strategy.
- `backend/tests/test_source_manifest.py` — regression checks for manifest completeness and honest integration statuses.
- `backend/requirements.txt` — added PyYAML for parsing/validating the YAML manifest in tests and later source-contract work.

**Research findings (official pages reviewed 2026-10-17):**
- **NCS:** Official portal/Terms & Conditions reviewed. That page does not establish a blanket open-data licence, so use exact page links until per-page reuse permissions are confirmed. No public API/bulk data route was verified in reviewed pages.
- **NSDC QP/NOS:** Official pages describe occupational standards and show distinct lifecycle states, including NSQF-aligned/NSQC-cleared, under validation, draft/reviewed and retired records. Rights are not assumed identical across documents; exact records remain link-only until terms are confirmed.
- **O*NET:** Official page identifies O*NET Database 31.0 (August 2026) as the current production release during this review. Downloadable database files are CC BY 4.0 subject to the page's scope/exceptions and attribution/version/change-notice requirements. Web Services has separate account/registration, attribution and no-alteration rules and may expose third-party content.
- **ESCO:** Official pages document downloadable machine-readable data and free reuse subject to acknowledgement and marking adaptations. The download page describes v1.2.1 (updated 10 December 2025), while the Web API page lists default v1.0.9 and v1.2.0. Later ingestion must pin and inspect the actual exported package instead of relying on an unpinned API default.
- **PLFS:** Official MoSPI Annual Report 2025 press note/report covers January–December 2025 and is dated 27 March 2026. Its intended use is aggregate, dated context only; individual scoring is prohibited by product design. Exact redistribution terms for extracted tables were not confirmed.
- **O*NET Interest Profiler:** Tool-specific terms differ from database terms. Verbatim redistribution is under CC BY-ND 4.0; adaptation/extension requires the O*NET Tools Developer License and validation obligations. Tool content is excluded from the MVP questionnaire; SkillScope will author original challenges.

**Checks run:**
- Official source pages / terms were reviewed through the research browser.
- Source register and YAML manifest parsed/validated locally.
- Automated regression tests cover required source IDs, required provenance/terms fields, and the rule that no source can be labelled integrated without actual imported data/code use.
- `PYTHONPATH=backend pytest -q` — **47 passed** after adding source-manifest tests.
- No bulk data package was downloaded and no external API was called from the application runtime. A prior npm registry call failed DNS with `EAI_AGAIN`; source host runtime access remains unverified, not assumed available.

**Selected strategy:** NCS/NSDC link-only Indian references pending exact reuse clearance; future O*NET 31.0 and ESCO version-pinned narrow bulk extracts for supplementary taxonomy; PLFS link-first aggregate context only; exclude O*NET Interest Profiler instrument content from MVP.

**Outcome:** Stage 4's source-selection and licensing exit gate is met through a traceable source register. Runtime fetch feasibility is an explicit unresolved item for Stage 6; nothing is marked integrated and no data access is fabricated.

**Next stage:** Stage 5 — Provenance model and canonical data contract, only after explicit user approval.

## Stage 5 — Provenance model and canonical data contract

**Status:** Complete — 2026-10-17

Implemented the canonical provenance layer before any external career dataset import.

### Added

- `backend/app/schemas/provenance.py` — source, entity, provenance-link, and career-fact contracts.
- `backend/app/services/provenance.py` — SQLite-backed provenance repository with source/entity/link/fact tables and lineage-preserving upserts.
- `backend/app/api/provenance.py` — provenance status and career-fact trace endpoints.
- `data/canonical_data_contract.json` — machine-readable canonical contract.
- `docs/PROVENANCE_MODEL.md` — lineage, mapping, display, and labour-market rules.
- `backend/tests/test_provenance.py` — repository and API traceability tests.

### Provenance guarantees

- Original source values are stored separately from normalized values.
- Every canonical entity retains source ID, source record ID, version, publisher, geography, dates, licence reference, quality status and limitations where available.
- Cross-source mappings use explicit `exact`, `reviewed_related`, `weak_lexical`, or `unresolved` states.
- A sourced career fact resolves through a canonical entity to a source record and provenance link.
- Heuristics, user evidence and demo fixtures remain separate source types.
- PLFS/aggregate labour-market evidence is structurally treated as context, not individual scoring evidence.
- Stage 5 does not mark or import any external source; Stage 4's source manifest remains authoritative for integration status.

### Verification

- Backend tests: **52 passed**.
- Python compilation: passed.
- Canonical JSON contract parsing: passed.
- Unknown career-fact endpoint returns HTTP 404.
- Provenance status endpoint explicitly reports `external_data_integrated: false` while the registry is empty.

### Known limitations

- No external source package has been imported yet.
- The provenance database is an MVP SQLite implementation; production deployment should add migrations, transactional ingestion jobs, access controls and backup/retention policy.
- The frontend does not yet display career facts because the career/skill knowledge base is intentionally deferred to later stages.

## Stage 6 — Data ingestion and normalization

**Status:** Complete for the ingestion code and verified curated-snapshot fallback. Full external database/API integration remains blocked by DNS/portal access in this execution environment. No claim of live data is made.

### Implemented

- `backend/app/services/ingestion/common.py` — UTC/timestamp parsing, bounded CSV/ZIP reading, tolerant common encodings, header normalization, required-column matching, stable ID/duplicate handling, SHA-256 and atomic JSON state helpers.
- `backend/app/services/ingestion/downloads.py` — fixed allow-listed O*NET 31.0 CSV download targets, HTTPS/redirect-host checking, timeout/retry handling, size/content/header validation, SHA-256 sidecars and failure logs.
- `backend/app/services/ingestion/pipeline.py` — idempotent curated-snapshot import, pinned O*NET occupation/essential-skill CSV import, and local ESCO CSV ZIP import. Importers preserve raw fields, normalized values, provenance links, source version, release/retrieval/ingestion metadata, licence, checksums and limitations.
- `backend/app/services/ingestion/cli.py` — `status`, `download-onet`, `import-curated`, `import-onet`, and `import-esco` commands.
- `backend/app/api/ingestion.py` — read-only `GET /api/ingestion/status` with registry counts, per-source latest attempt/success and the explicit `source_data_is_live: false` marker.
- `data/curated/occupations_snapshot.json` — 4-record source-backed curated extract (3 O*NET OnLine profile summaries and 1 ESCO concept summary) with version/context, source URI, terms, transformations and limitations. It is not a full database export, and it is not a live response.
- `data/ingestion_state.json`, `data/ingestion_runs/` — observed download/API failure state and successful local curated import report.
- `docs/INGESTION_PIPELINE.md` — operational commands, raw-file management, validation gates and offline recovery instructions.
- `docs/ATTRIBUTIONS.md` — current attribution/adapter notices for the included curated data and future bulk imports.
- Updated source manifest/register/access audit/project status/README and source manifest regression tests.
- `backend/tests/test_ingestion.py`, `backend/tests/test_ingestion_api.py` — import validation, duplicate conflict, idempotency, provenance, O*NET scale/suppression rules, ESCO language/package/relationship integrity, downloader errors, API status and CLI checks.

### Source ingestion outcomes

**O*NET runtime attempts:** `occupation_data.csv` and `essential_skills.csv` were each requested from their fixed official HTTPS URL. Both failed with `ConnectError: [Errno -3] Temporary failure in name resolution`; no bytes were downloaded. Each failure, start/finish timestamp, URL and recovery instruction is recorded in the ingestion state/run ledger.

**ESCO runtime attempt:** A request to the official ESCO API route failed with the same DNS resolution error. No response body was received. The official ESCO CSV ZIP portal flow asks the user to select the version/content/language/file type and then provides a download link following its request/email workflow; it was not completed in this environment. The local ZIP importer is implemented and is tested against non-production fixture files.

**Verified local import:** The bundled curated snapshot imported into the default local SQLite registry:
- 4 source records / canonical entities;
- 4 provenance links;
- 11 career facts;
- 3 O*NET OnLine profile extracts and 1 ESCO concept extract;
- snapshot SHA-256: `88ec85950889f99f79cfaa71a044a74ec3047e73748c0e5f822714da9b85bc3b`.

The canonical records are `source_type=curated_extract`. `/api/provenance/status` therefore reports `external_data_integrated: false`, and `/api/ingestion/status` reports `source_data_is_live: false`. The manifest keeps O*NET Database 31.0 and the full ESCO classification `not_integrated`.

### Safety and data-quality controls

- No arbitrary download URL accepted; requests are restricted to allow-listed official O*NET assets.
- Redirect hosts, HTTP failures, content type, maximum size, CSV header and checksums validated.
- Downloads use a temporary `.part` path and do not leave an unvalidated data asset as a successful download.
- CSV parser checks blank files, ambiguous headers, malformed rows, and ZIP member size/ratio limits.
- O*NET rows require expected codes and occupation references; unknown scales, out-of-range ratings, unrecognized flags and conflicting duplicates fail before data writes. Suppressed/not-relevant or blank ratings do not create student-facing rating facts.
- ESCO import pins the operator-supplied package version, requires timezone-aware retrieval time, chooses the specified language without guessing, and validates occupation/skill endpoints before relationship import.
- Test fixtures are separate from curated source material and are never reported as imported source records.
- Raw data files are excluded from checkpoint ZIPs. The small seeded `data/skillscope.db` only contains curated extracts and can be regenerated with the documented idempotent CLI command.

### Checks run

- `PYTHONPATH=backend pytest -q` — **68 passed**.
- `python -m compileall -q backend/app backend/tests` — passed.
- Source manifest YAML, canonical JSON contract and curated snapshot JSON — passed local parsing/validation.
- CLI help — passed; curated snapshot CLI import — succeeded, 4 records and 11 facts.
- `GET /api/ingestion/status` — HTTP 200; accurately reports source statuses, counts and non-live semantics.
- `GET /api/provenance/status` — HTTP 200; reports four `curated_extract` records and `external_data_integrated: false`.
- `GET /api/provenance/career-facts/fact:occupation:onetonline:15-1252-00:summary` — HTTP 200 with a provenance chain back to the source page and curated-extract limitations.
- Direct O*NET and ESCO network calls — **failed with observed DNS errors**; source integration remains blocked and not falsely claimed.
- Frontend npm dependency install, typecheck and production build remain unverified because `registry.npmjs.org` could not be resolved earlier in this environment.

### Stage 6 exit assessment

The reusable ingestion and normalization pipeline, offline curated fallback, validation, provenance and failure-state reporting are implemented. Full external dataset imports are an explicit environment blocker, not passed acceptance checks. In a network-enabled developer environment, retry the official downloads/portal workflow, capture the exact package metadata/checksum, then run importer validation before marking those sources integrated.

**Next stage:** Stage 7 — Career and skill knowledge graph, only after explicit user approval.


### Stage 6 — Independent post-completion audit and corrective hardening (2026-10-17)

**Audit outcome:** The first Stage 6 checkpoint was not yet reliable enough to hand to Stage 7. A second review found several gaps that the initial green tests did not catch. These have now been corrected and covered by regression tests.

**Corrections made:**
- Fixed the single-entity provenance upsert to reference the `canonical_entities` table's timestamps rather than another table's columns.
- Enabled SQLite foreign-key enforcement on every repository connection, rejected naive (timezone-free) provenance timestamps, and required each inserted career fact to have a provenance link matching the entity's exact source record.
- Added the active immutable snapshot pointer to `GET /api/ingestion/status`, including source/package hash, source version, normalizer schema version and static-data semantics. Downstream readers must use that pointer; older versioned records are retained but not implicitly mixed.
- Added `NORMALIZER_SCHEMA_VERSION` to generated snapshot namespaces so normalization-rule changes cannot silently overwrite older derived snapshots.
- Fixed ESCO CSV normalization to understand the official field names (`Concept URI`, `Concept type`, `ISCO code`, `Concept PT`) and documented concept-type codes (`OC`/`OG`, `SK`/`SG`). Verified the expected field semantics against the [official ESCO CSV structure guide](https://esco.ec.europa.eu/en/about-esco/escopedia/escopedia/comma-separated-values-csv) and official O*NET 31.0 Essential Skills data dictionary (https://www.onetcenter.org/dictionary/31.0/csv/essential_skills.html).
- A final relation-data pass added aliases for relation-type headers, preserved `relationRelevance` as a normalized source attribute and in relation identity, added regression coverage for distinct relevance values, and bumped `NORMALIZER_SCHEMA_VERSION` to `2` so prior derived snapshots cannot collide with the updated semantics.
- Preserved exact ESCO concept URIs as the source/provenance target, while keeping a separate display URL where applicable.
- Made provenance acquisition metadata explicit that validated local hashes/sidecars are not cryptographic proof of source origin. Manifest statuses no longer claim a verified official download based only on sidecar presence.
- Hardened malformed CSV/ZIP/state handling, preserved the central run ledger on corrupt-state input, added manifest-target preflight before official import writes, and extended tests for HTTPS-to-HTTP redirect rejection, versioned snapshots, repeated-import timestamp stability and import-failure recording.
- Rebuilt the packaged SQLite demo registry from a clean database using only the curated snapshot. Its expected contents remain 4 curated source records, 4 canonical entities, 4 provenance links and 11 career facts.

**Verification after audit:**
- `PYTHONPATH=backend pytest -q` — **85 passed** after the ESCO relation-relevance regression and normalizer version bump.
- `python -m compileall -q backend/app backend/tests` — passed.
- Curated snapshot, canonical JSON contract and YAML manifest validation — passed.
- `import-curated` CLI — succeeded from a clean database; repeat import behavior is covered by tests.
- Ingestion/provenance API tests — pass, including active snapshot metadata and non-live semantics.
- External O*NET and ESCO requests still fail with observed DNS errors in this environment; neither full source is marked integrated.
- Frontend npm dependency installation/typecheck/production build remains unverified because npm-registry DNS access was previously unavailable.

**Final Stage 6 disposition:** Complete for the ingestion/normalization implementation and curated offline fallback. External source acquisition remains an explicit environment limitation; importer behavior against authentic complete official packages is not claimed as runtime-verified. Stage 7 is not started until the user approves.

## Stage 7 — Career & Skill Knowledge Graph

**Status:** Complete within the documented curated-data scope — 2026-10-17. Stages 8–20 remain untouched and require approval at each checkpoint.

### Goal and data boundary

Create a materialized, version-aware graph over the canonical provenance registry. Career profiles connect to selected work activities, source-listed skill references, occupational terms and explicit crosswalk records. The graph must preserve source IDs, source URIs, version/geography/licence context and uncertainties; it must not turn occupational descriptors into student evidence.

The Stage 7 snapshot is larger than the initial Stage 6 checkpoint: it contains ten curated profile records (nine O*NET OnLine profiles plus one ESCO software-developer concept). Profile pages were reviewed through official source pages and relevant task and “Essential Skills” labels paraphrased/selected. No full source package was downloaded by the project runtime. The data remains `curated_extract`, not full-source integration or live data.

### Implemented

- `backend/app/schemas/knowledge_graph.py` — typed node, edge, mapping and status contracts.
- `backend/app/services/knowledge_graph.py` — idempotent/version-aware SQLite graph projection, active-snapshot filtering, source-lineage joins, crosswalk creation, unresolved mapping visibility, graph freshness checks and CLI rebuild/status commands.
- `backend/app/api/knowledge_graph.py` — read-only status, node search/detail, edges, crosswalk and career-card endpoints; stale or not-built graph reads fail rather than return misleading data.
- `data/curated/occupations_snapshot.json` — expanded from four to ten profile records, with nine O*NET OnLine career examples across technical, analytical, creative, business, social, environmental and hands-on domains, plus one ESCO occupation concept. The SkillScope `curation_domain` field is explicitly editorial metadata.
- Stage 6 curated importer now preserves `curation_domain` as normalized editorial metadata (not in original source values) and carries the selected O*NET OnLine Essential Skills section labels as a source-category-aware fact without ratings.
- Graph creates occupation-scoped skill-reference nodes and `occupation_has_skill` edges only from these source-listed Essential Skills labels. As stable skill-element IDs and occupational ratings are not captured in the curated extract, identical labels are **not merged** into canonical source skill concepts.
- The O*NET–ESCO software-development link remains a reviewed `related_occupation` edge with separate source references; an unresolved exact-equivalence candidate stays visible. Debugging task phrases are likewise mapped as related, not exact.
- `frontend/src/App.tsx` — sourced career cards, selected activities, source-listed essential skill references with caveats, editorial coverage labels, source links/licence references and a cross-taxonomy audit view.
- `docs/KNOWLEDGE_GRAPH.md` — graph semantics, counts, APIs, reproducible build commands and limitations.
- `docs/ATTRIBUTIONS.md`, `data/sources_manifest.yaml`, `docs/INGESTION_PIPELINE.md`, `docs/PROJECT_STATUS.md`, `README.md` and `docs/DECISIONS.md` updated for this checkpoint.
- Added curated import regression coverage and graph tests for source-linked skill references, identity preservation, crosswalk status, idempotency, stale-snapshot refusal, invalid state, endpoints and API behavior.

### Current graph inventory

- **109 nodes:** 10 occupation profile nodes, 45 occupation-scoped skill references, 45 selected work activities, 7 occupational terms and 2 SkillScope-authored capability hypotheses.
- **109 edges:** 45 occupation-to-skill references, 45 performs-task edges, 12 source-term associations, 4 capability-hypothesis support edges, 1 reviewed related occupation, 1 reviewed related work activity and 1 unresolved crosswalk candidate.
- Zero unresolved relationship endpoints; graph `source_data_is_live` remains `false`.
- NCS and NSDC remain absent, so no India-first job/qualification pathways or local hiring-demand claims are made.

### Checks run

- `PYTHONPATH=backend pytest -q` — **94 passed**.
- `python -m compileall -q backend/app backend/tests` — passed.
- Curated snapshot JSON and source YAML manifest parse/validate; canonical JSON contract parse passed.
- Removed the previous generated local database, imported the updated snapshot cleanly (10 records, 32 facts), and rebuilt the graph against the active versioned snapshot (109 nodes, 109 edges).
- API smoke checks confirm status, `/careers`, `/crosswalks`, skill-node query, source references, and current snapshot consistency.
- Archive ZIP integrity checked. Raw source downloads, generated SQLite DB, caches and `.git` are excluded.
- Retried frontend dependency installation on 2026-10-17; npm registry DNS returned `EAI_AGAIN` and the install timed out. TypeScript TSX syntax transpilation passed, but `npm run build` and a full typecheck remain unverified; this limitation is carried forward instead of claiming success.

### Stage 7 exit assessment

The MVP graph and reviewer-facing source-trace inspection are in place for the available curated extract. Two independent source references can be inspected for the sampled software-development crosswalk where corroboration exists, and the unresolved exact-equivalence issue is explicitly retained. The graph architecture supports explicit skill concepts and occupation-skill relationships from future authentic imports, but the current occupation-scoped skill labels are not promoted into canonical concepts without stable source IDs.

**Known limitations:** Full O*NET Database, full ESCO, NCS, and NSDC imports are not present. No official qualification pathway or student-level recommendation is created in Stage 7. Frontend production compilation is not yet verified. These are visible in API/UI/documentation.

**Next stage:** Stage 8 — Student evidence model and evidence ledger, only after the user approves Stage 7.


## Stage 8 — Student Profile & Evidence Ledger

**Status:** Complete within documented prototype scope — 2026-10-17. Stage 9 is not started pending user approval.

### Implemented

- Created `backend/app/schemas/student_evidence.py`, with explicit typed contracts for age bands, consent basis, evidence types, signal dimensions, source kinds, uncertainty levels, user-labelled interpretations, rubric observations, profile records and no-score summaries.
- Created `backend/app/services/evidence_ledger.py`: SQLite-backed student profiles and timestamped evidence, foreign-key enforcement on each connection, indexes, filtering/pagination, correction paths, capture-time consent metadata, and permanent deletion/cascade support.
- Created `backend/app/api/student_evidence.py`: profile create/read/patch/delete, evidence list/add/patch/delete, summary, and clear-history routes.
- Added the React evidence ledger at `frontend/src/components/EvidenceLedger.tsx`; integrated it into the frontend. The UI lets students create/correct pseudonymous profiles, record typed evidence and rubric criteria, review per-dimension summaries, correct/delete entries, clear history, and delete a profile.
- Added `data/student_evidence_contract.json` and `docs/STUDENT_EVIDENCE_LEDGER.md` with schema, APIs, deterministic summary semantics, privacy boundary and production limitations.

### Key correctness rules

- Profiles for ages 10–17 require recorded guardian-consent confirmation; 18+ profiles require student consent. Evidence records snapshot consent basis, confirmation timestamp and notice version at capture.
- Repeated in-product behavior must have consent for that specific record and non-empty activity/time-window context. No background monitoring is implemented.
- Challenge results require a named activity, rubric and criterion-level observation; numeric scores require their own stated scale. Scores are not normalized across rubrics.
- A stated goal is a timestamped self-report. Later goal changes/removals append a new ledger record instead of silently rewriting the old record.
- Empty dimensions are `unknown`, not zero. `mixed` only follows explicit user-labelled supporting and challenging records. No signal number or career-fit/aptitude score is computed.
- A correction changes the editable fields and update timestamp while preserving original `recorded_at`. Clearing evidence also clears current goal/context; whole-profile deletion is permanent. Crossing the minor/adult consent boundary with history is blocked until the profile is deleted and recreated, so historic consent metadata is never relabelled.

### Verification

- `PYTHONPATH=backend pytest -q` — **117 passed**.
- `python -m compileall -q backend/app backend/tests` — passed.
- TypeScript syntax transpilation using the globally installed TypeScript compiler — passed for `App.tsx`, `EvidenceLedger.tsx` and `main.tsx`.
- `npm install --offline` could not complete because required packages (starting with `@types/react`) are not cached. No frontend production build or full typecheck is claimed.
- Tests validate age-aware consent, per-item behavior consent, context, record-type/dimension combinations, rubric-scale rules, recent evidence explanations, unknown and mixed states, pagination, corrections, timezone-aware observations, goal-history preservation, profile isolation at query level, deletion and foreign-key cascade.

### Limitations and next stage

The API is unauthenticated, and consent is a self-attestation—not verified guardian authority. Profile UUIDs are locators rather than authentication. Do not deploy with real student/minor data before implementing verified identity, server-side authorization, deployment security, applicable consent/assent flows and operational retention controls. Browser `localStorage` keeps the profile locator in the local prototype; evidence itself is persisted server-side in SQLite.

**Next stage:** Stage 9 — Baseline Assessment Engine, only after explicit user approval.


## Stage 9 checkpoint — 2026-10-17

Implemented `baseline-exploratory-v1.0`: age-aware nine-domain baseline, meaningfully different age framing, self-report plus mini-activity evidence, skip/confidence handling, persisted assessment/submission state, Stage 8 evidence integration, explicit non-psychometric notice, and deterministic tests (`122 passed`).

## Stage 10 checkpoint — 2026-10-17

**Objective:** Turn exploration into practical, inspectable evidence with a diverse, age-scaled challenge library and transparent reproducible scoring.

**Implemented:**
- Added `backend/app/schemas/challenges.py` with typed challenge, age-variant, rubric, submission and scoring contracts.
- Added `backend/app/services/challenges.py` with a 12-family authored challenge library and deterministic rubric scorer.
- Added `backend/app/api/challenges.py` with library/filter/detail/submission endpoints and registered the router in `backend/app/main.py`.
- Added `backend/tests/test_challenges.py` covering library diversity, age scaling, rubric transparency, reproducible scoring, reflection separation, partial/insufficient evidence, invalid criteria/scales and profile age selection.
- Added `docs/CHALLENGE_LIBRARY.md` documenting the library, provenance, scoring semantics, evidence integration, safety boundary and limitations.

**Library coverage:** 12 challenge families × 3 age bands = 36 age-scaled variants across all nine target domains. Challenge content is explicitly `skillscope_authored`; no third-party questionnaire or external task set was copied, and no external source is falsely claimed.

**Scoring rules:** Scores exist only for observed rubric criteria. Missing observations are not zero. `not_enough_evidence`, `partial_evidence`, and `evidence_available` are explicit states. Objective scores are challenge-local and are never presented as aptitude, personality, clinical, or career-fit scores. Enjoyment, reported difficulty, confidence, willingness to continue, and reflection are stored separately and do not alter objective rubric scores.

**Evidence integration:** Each valid submission creates a Stage 8 `challenge_performance` evidence item in the same SQLite transaction as the submission. Challenge ID/version, criterion-level observations, score status and reflection context are retained for later longitudinal stages.

**Checks run:**
- `PYTHONPATH=backend pytest -q` — **129 passed**.
- `python -m compileall -q backend/app backend/tests` — passed.
- Direct challenge-library contract validation — 12 families, 36 variants, all nine domains, authored-content provenance checks passed.
- API submission smoke path exercised through the automated TestClient suite.

**Unresolved risks/limitations:** API remains unauthenticated and is not safe for real student/minor deployment; challenge content and rubric scales are transparent heuristics, not psychometrically validated measures; frontend dependency-backed production build remains unverified because npm registry access is still unavailable in the environment.

**Next stage:** Stage 11 — Daily/regular discovery loop, pending explicit user approval.


## Stage 11 checkpoint — 2026-10-17

**Objective:** Make SkillScope meaningfully longitudinal: saved challenge work and student-led reflection should affect the next challenge, with a plain-language explanation.

**Implemented:**
- Added `backend/app/schemas/discovery_loop.py` with versioned policy response, preference contract, age-scaled next-challenge representation, domain exposure, prior completion summary and explicit limitation fields.
- Added `backend/app/services/discovery_loop.py`. It derives the next task deterministically from persisted activity history, challenge-family exposure, the latest student-authored interpretation, optional engagement ratings and the chosen preference. Lifetime coverage is aggregated in SQLite; a bounded recent window drives the narrative/engagement decision. It prefers never-tried challenge families, then avoids the three most recent tasks when the finite library has been exhausted. Stable challenge-library order resolves ties.
- Added `backend/app/api/discovery_loop.py` and registered `GET /api/discovery-loop/{profile_id}`. Preferences: `balanced`, `explore`, `develop`, `validate`, `alternative`. Missing activity remains unknown, and explicit student disagreement can trigger a different-domain test without silently changing the student's goal.
- Extended challenge submissions to retain `hypothesis_interpretation` separately from rubric scores. Added an additive `challenge_submissions.user_interpretation` migration for Stage 10 databases.
- Corrected evidence capture so confidence is stored as confidence context, not mislabelled as curiosity; the challenge domain and the student's interpretation are retained on the evidence record. Submission and evidence persistence remain in one transaction.
- Added `frontend/src/components/DiscoveryLoop.tsx`: consent-attested profile setup, age-specific activity, visible rubric, criterion scores/observations, separate self-reports and reflection, and visible re-selection explanation. It interoperates with the existing evidence-ledger profile locator through a same-tab event. No reminders or background monitoring are claimed.
- Added `docs/DISCOVERY_LOOP.md`, `data/discovery_loop_contract.json`, Stage 11 status/build-log updates, and API/readme documentation.

**Selection policy:**
1. Age band selects the exact age-appropriate challenge variant.
2. Prefer a never-tried challenge family; after all families are used, avoid the three most recent where possible.
3. A student-reported conflict prioritizes an alternative domain; mixed/context-dependent reports or a validation preference prioritize a different task in the same domain where available.
4. Explicit support or high voluntary enjoyment/willingness can offer a different activity in that domain, without calling this ability evidence.
5. A request to develop without relevant engagement evidence falls back to exploration instead of guessing.
6. Rubric totals are not compared across unrelated challenge families and free-text goals are not mapped into domains through keyword heuristics.

**Checks run:**
- `PYTHONPATH=backend pytest -q` — **138 passed**.
- `PYTHONPATH=backend python -m compileall -q backend/app backend/tests` — passed.
- Challenge/loop contract validation — passed: 12 challenge families, 36 age variants, nine domains and five preference modes.
- TypeScript `transpileModule` syntax diagnostics — passed for `App.tsx`, `EvidenceLedger.tsx`, `DiscoveryLoop.tsx` and `main.tsx`.
- Attempted dependency-backed `tsc --noEmit -p frontend/tsconfig.json`; it cannot pass in this environment because `react`, `react/jsx-runtime`, and their type declarations are not installed. The earlier npm registry DNS failure continues to block a dependency install. No Vite build or full frontend typecheck is claimed.
- Added an explicit Stage 10 schema migration test and deterministic same-input/state test.

**Limitations:** The loop is request-driven and does not schedule daily reminders/push notifications. The API remains unauthenticated; consent is a self-attestation, not verified guardian authority. The heuristic is not psychometrically validated. It is not safe for public deployment with real student/minor data without identity, authorization, verified consent and production security controls.

**Stage 11 exit assessment:** Completing an activity now changes persisted evidence/history and the visibly explained next recommendation under deterministic rules. Stage 11 is complete within the documented prototype scope. Stage 12 has not started and awaits user approval.


## Stage 12 checkpoint — 2026-10-17

**Objective:** Return transparent, repeatable career hypotheses with explicit evidence use, qualitative confidence, gaps, source-backed facts and next validation steps—without a numeric career-fit result.

**Implemented:**
- Added `backend/app/schemas/recommendations.py`, `backend/app/services/recommendations.py`, and `backend/app/api/recommendations.py`; registered `GET /api/recommendations/{profile_id}?limit=5`.
- Added `data/recommendation_weights.json` (`transparent-career-match-v1.0`) and `data/career_domain_hypotheses.json` (`career-domain-hypotheses-v1.0`). Weights are configurable initial heuristics explicitly not scientifically optimized. Unavailable components are omitted and the remaining weights are renormalized.
- Added the frontend `CareerRecommendations.tsx` panel and integrated it with profile/evidence update events. The UI surfaces hypothesis category, reasons, evidence records, source references, qualitative confidence breakdown, unknowns, and a validating challenge.
- Ages 10–14 receive broad activity-domain exploration only and no occupation labels. Ages 15+ receive occupation hypotheses only when the current source-linked graph exists and is not stale.
- Kept O*NET and ESCO identities separate; SkillScope-authored domain associations are clearly identified as hypotheses rather than official classifications. Sourced work activities retain provenance metadata. No unsupported salary, demand, local qualification or labour-market statements are manufactured.
- Tightened skill-label overlap to require the complete normalized phrase in the recorded text, preserving word order; isolated shared tokens no longer count as an exact match.
- Added `docs/RECOMMENDATION_ENGINE.md`, policy/mapping contracts, API error semantics and deployment/source limitations. Updated the README and current project status.

**Recommendation semantics:** The engine distinguishes goal-wording overlap, contextual evidence and evidence confidence. Confidence is qualitative and uncalibrated; it describes evidence volume, recency, consistency, source quality and coverage, not probability of career success. Missing evidence remains unknown. Contradictory student-labelled evidence triggers a refresh/validation path without silently changing the goal. Voluntary portfolio descriptions are contextual text only, not proof of skill. No aggregate labour-market data is used to score the individual.

**Checks run:**
- `PYTHONPATH=backend pytest -q` — **153 passed** (including 15 recommendation-engine tests).
- `PYTHONPATH=backend python -m compileall -q backend/app backend/tests` — passed.
- Policy and domain-mapping JSON validation — passed; all ten current source-linked occupation identities have an authored domain-hypothesis mapping.
- Local current-graph smoke test — expected endpoint response, cited work facts and source metadata verified; temporary test profile deleted.
- TSX syntax transpilation — passed for `App.tsx`, `EvidenceLedger.tsx`, `DiscoveryLoop.tsx`, `CareerRecommendations.tsx`, and `main.tsx`. This is not a full dependency-backed typecheck or production build.
- ZIP integrity and package-content checks — passed; generated databases, `.git`, caches, installed dependencies, build outputs and nested ZIP files are excluded.

**Known limitations:** The current graph is a curated static set of ten career profiles, not the full O*NET or ESCO databases; NCS/NSDC and India-specific credential, demand and salary data remain unintegrated. Heuristic relevance and confidence are not scientifically calibrated. Frontend typecheck/Vite build remain unverified due to npm dependency and registry access limitations. Authentication/authorization and verified consent are not implemented; do not deploy with real student/minor data.

**Stage 12 exit assessment:** Identical inputs, policy versions and evaluation date produce deterministic recommendations; tests cover missing evidence, contradictions, alternatives, under-15 broad exploration, stale/unavailable catalogs, source identities, confidence and lack of numeric fit fields. Stage 12 is complete within this documented prototype scope.

**Next stage:** Stage 13 — Career pathway and action-plan engine, pending explicit user approval.


## Stage 13 checkpoint — 2026-10-17

**Objective:** Convert the Stage 12 recommendation hypotheses into age-appropriate career pathway options and practical, revisable action plans.

**Implemented:**
- Added pathway plan schemas, deterministic plan construction and persistent snapshot storage (`pathway_plans`). Added `POST /api/pathway-plans/{profile_id}/generate`, `GET /api/pathway-plans/{profile_id}`, and `GET /api/pathway-plans/{profile_id}/history`.
- Goal edits flow through the existing evidence ledger, retaining timestamped previous goals and all prior activity evidence. New plan snapshots keep the goal, inputs, version, pathway explanations, actions, references, unknowns and review instructions.
- Ages 10–14 receive one small exploratory activity without occupation labels or timed career goals. Ages 15–17 see up to three hypotheses with reasons, unknowns and validating projects. Ages 18+ receive current-state documentation checks, ordered validation/project/portfolio actions, source-linked skills/work context, and a bounded timeline only when target, current-state context, weekly availability and desired timeline are all provided.
- Explicitly separated source-listed work activities from formal prerequisites. Only a source-linked `requires_qualification` relation is labelled as a requirement; otherwise the plan reports that this catalog has no verified prerequisite information. Skill labels that do not appear in user context or evidence are marked `not_yet_documented`, not missing or deficient.
- Added the `PathwayPlanner.tsx` UI with editable goal/context, plan generation and revision, age-specific display, pathway comparisons, skill context statuses, source links, requirement caveats and plan history. Updating a goal signals the existing profile/evidence/discovery panels to refresh.
- Added `docs/PATHWAY_PLANS.md` and `data/pathway_plan_contract.json`; updated the current README/status.

**Checks run:**
- `PYTHONPATH=backend pytest -q` — **161 passed** (including eight Stage 13 tests).
- `PYTHONPATH=backend python -m compileall -q backend/app backend/tests` — passed.
- Python data/schema contracts loaded and validated; frontend TSX syntax transpilation checked for the touched entry/component files.
- Pathway API smoke test covered generate/latest/history; a temporary test profile was removed after the test.
- Release ZIP integrity and inclusion/exclusion audit passed; generated database, Git metadata, caches, installed dependencies, build output, raw source downloads, and nested ZIPs are not included.
- Dependency-backed TypeScript typecheck and Vite production build remain unverified because npm packages/registry access are unavailable in this environment.

**Limitations:** the career graph remains a curated set of ten occupation identities, not a full source taxonomy; current source coverage does not support complete India-specific formal qualifications/admission pathways. Suggested actions, effort estimates and planning timelines are heuristic prompts and not career-success promises. The API is unauthenticated and remains inappropriate for public use with real student/minor data.

**Stage 13 exit assessment:** plans contain actionable steps, expected outcomes, available evidence/source references, prerequisite/source caveats, and an explicit route for editing goals and recalculating. Stage 13 is complete within the documented prototype scope. Stage 14 has not started and awaits explicit user approval.


## Stage 14 — User journeys, navigation, and information architecture

**Status:** Implemented and contract-tested within prototype scope.

**Objective:** Connect the calibration preview, consented profile, baseline assessment, evidence ledger, daily challenge, recommendation comparison, pathway plan, provenance review, and profile settings into a coherent user journey with explicit first-time and failure states.

**Files added/changed:**
- `frontend/src/components/JourneyNavigation.tsx` — responsive sticky section navigation with an active-section indicator and real section anchors.
- `frontend/src/components/BaselineAssessment.tsx` — user-facing baseline lifecycle: start, one-item-at-a-time response, back/skip, submission, domain-level result, error/retry and next-step navigation.
- `frontend/src/App.tsx` — mounts the navigation/baseline journey and adds calibration-to-profile transition; removes overflow clipping that would interfere with a sticky header.
- `frontend/src/components/EvidenceLedger.tsx` — stable profile/settings navigation target and an explicit post-profile continuation to baseline; consent/privacy explanation remains adjacent to profile creation.
- `frontend/src/components/DiscoveryLoop.tsx`, `CareerRecommendations.tsx`, `PathwayPlanner.tsx` — primary next-step transitions; explicit mixed-evidence state in recommendation UI.
- `data/user_journey_contract.json` — machine-readable surface, transition, state and safety contract.
- `docs/USER_JOURNEYS.md` — journey, state handling, navigation architecture, known limitations and exit assessment.
- `backend/tests/test_user_journey_contract.py` — automated contract checks for real component ownership, navigation targets, transition graph, state inventory and safety invariants.

**Checks run:**
- `PYTHONPATH=backend pytest -q` — **167 passed** (full backend regression suite).
- `PYTHONPATH=backend python -m compileall -q backend/app backend/tests` — passed.
- `data/user_journey_contract.json` validation and Stage 14 contract tests — passed.
- Global TypeScript `transpileModule` syntax checks for `App.tsx`, `main.tsx`, `JourneyNavigation.tsx`, `BaselineAssessment.tsx`, `EvidenceLedger.tsx`, `DiscoveryLoop.tsx`, `CareerRecommendations.tsx`, and `PathwayPlanner.tsx` — passed for all eight implementation files. Syntax transpilation is not a typecheck.
- Archive integrity/content audit — passed; release archive includes source, journey contract, tests and documentation while excluding generated databases, caches, installed dependencies, build output, Git metadata and nested archives.
- Dependency-backed `tsc -b`, Vite production build, and browser-level interaction automation remain unverified because npm dependencies are unavailable in this environment.

**Behavior / safety:**
- Calibration remains a stateless preview and makes no profile until the user explicitly continues and confirms age-appropriate consent in the evidence ledger.
- The baseline is real UI over the existing API, uses the age band of the consented profile, supports back/skip, and visibly treats skipped domains as unknown.
- The navigation uses stable IDs, a scrollable layout on narrow screens, keyboard focus indicators, `aria-current` and a screen-reader current-section announcement.
- Graph and recommendation failures remain visible, retryable where implemented, and are not interpreted as evidence about the student.
- Conflicting student-labelled evidence triggers an explicit mixed-evidence notice and links to another validation activity; the app does not silently overwrite a hypothesis.
- The existing settings target is available even before a profile is created, allowing a first-time user to find the consent/privacy explanation.

**Limitations:** The baseline current answers are kept in component memory until submission; refreshing the browser abandons the in-progress UI draft, though the student can issue a fresh baseline. Guardian consent is still a self-attestation and the API has no authentication/authorization. The full external career datasets remain unavailable. No browser-level end-to-end run or production frontend build is claimed.

**Stage 14 exit assessment:** The required primary surfaces now have navigation targets; the baseline can be started and submitted by a normal user; profile creation and consent gate persistence; direct next-step links connect calibration → profile → baseline → challenge → career hypotheses → pathway plan → source records; settings/correction/deletion are navigable without developer tools. Stage 14 is complete within prototype scope. Stage 15 has not started and awaits explicit user approval.


## Stage 15 — Frontend implementation and visual design

**Status:** Implemented within source/design-contract scope; rendered browser audit remains unverified due missing frontend dependencies.

**Implemented:**
- Shared visual tokens and classes in `frontend/src/index.css` for canvas, surfaces, dividers, section kickers, panels, focus outlines, mobile form controls, and reduced-motion behavior.
- Balanced headings and overflow-safe wrapping for long student-provided/source text.
- Consistent vertical section rhythm and anchored scroll offsets. The Baseline and Pathway Planner no longer add redundant inner max-width and horizontal padding, aligning their contents with the other primary sections.
- Accessible darkening of small `text-slate-400` metadata text on light surfaces; source-checked WCAG contrast tests cover primary text, teal actions, indigo accents, focus ring and muted metadata.
- Shared panel treatment on major profile, challenge, recommendations, and plan surfaces without synthetic charts or misleading live-data graphics.
- Added `docs/VISUAL_DESIGN_SYSTEM.md`, `docs/STAGE15_VISUAL_AUDIT.md`, and `tests/test_stage15_visual_contract.py`.
- Full regression exposed drift in `data/sources_manifest.yaml`: version 2 omitted curated snapshot source IDs already required by importer and tests. Updated manifest to version 3 and added explicit `onet_online_curated_sample` and `esco_curated_sample` entries, with integration status limited to curated extracts. This fix preserves the guard against falsely claiming that full source datasets are integrated.

**Checks run:**
- `PYTHONPATH=backend pytest -q` — **167 passed** (includes Stage 15 visual/design source-contract and contrast checks).
- `PYTHONPATH=backend python -m compileall -q backend/app backend/tests` — passed.
- TypeScript global `transpileModule` syntax checks — all frontend implementation `.tsx` files passed; no dependency-backed typecheck is claimed.
- CSS parsing using PostCSS — passed.
- YAML source manifest parse and curated-snapshot source-ID consistency — passed.
- Archive integrity and package contents verified; generated SQLite database, `.git`, caches, installed dependencies, build outputs, and nested ZIPs excluded.

**Limitations:** `tsc -b`, `vite build`, and browser-level desktop/mobile screenshots/interactions were not run because frontend dependencies are not installed and npm cache/network access is unavailable. The static responsive-contract audit is not a substitute for rendered browser review. Authentication/authorization and verified consent remain production blockers for real student/minor data.

**Stage 15 exit assessment:** The shared visual system, responsive source classes, navigation anchors, keyboard focus and reduced-motion rules, primary surface inventory, privacy controls, and non-misleading data states are implemented and source-audited. Stage 15 is complete within this documented prototype scope; browser rendering/build checks remain unverified. Stage 16 awaits approval.


## Stage 16 — Backend, persistence, APIs, and integrations

**Status:** Complete within the documented local SQLite prototype scope.

**Implemented:**
- Centralized environment-backed database configuration in `backend/app/config.py`; relative SQLite URLs resolve from the project root, in-memory and non-SQLite URLs fail explicitly, and `.env.example` contains example values only.
- Added `backend/app/services/database.py` for shared SQLite connections, foreign-key enforcement, busy timeout/WAL setup, checksum-tracked additive schema migrations, a reproducible `init`/`status` CLI, idempotent demo seeding and non-sensitive persistence status. Development can auto-seed one clearly synthetic demo profile and challenge/evidence trail; production defaults to no demo seed.
- Added persistent `student_preferences` with GET/PUT API, and persisted recommendation snapshots/history with algorithm version, evidence count, source keys and serialized response. Recommendation persistence refuses unresolvable source-record identities and verifies that referenced student evidence belongs to the requested profile.
- Added request IDs and safe generic API error bodies for persistence and unexpected server errors; internal exception details remain in logs.
- Hardened official-source downloads with a checksum/header/time/version-verified TTL cache, forced refresh, source-level minimum request interval, bounded retries and `Retry-After` handling. Failed refreshes keep the last known file/sidecar intact and report failure explicitly rather than overwriting good data. Where the configured run ledger and migrated app database are used, cache telemetry updates `source_cache_state` best-effort.
- Added `docs/STAGE16_PERSISTENCE_AND_INTEGRATIONS.md` and `backend/tests/test_stage16_persistence.py`; added downloader tests for cache hits, cache corruption refresh, failed-refresh preservation, retry delay and persisted cache status. Existing recommendation tests now cover durable snapshot history.

**Checks run:**
- `PYTHONPATH=backend pytest -q` — **184 passed** (includes safe-error/request-ID endpoint checks in addition to persistence and source-cache tests).
- `PYTHONPATH=backend python -m compileall -q backend/app backend/tests` — passed.
- `PYTHONPATH=backend python -m app.services.database init --db <temporary-file> --no-demo` followed by `status` — passed; migration version 2 and persistent store reported correctly without a demo fixture.
- JSON contracts and YAML source manifest parsed successfully.
- ZIP integrity and required-content checks passed; generated SQLite database, `.git`, caches, installed dependencies, build outputs, raw downloads and nested archives are excluded.

**Limitations:** Only file-backed SQLite is supported. Full O*NET/ESCO and Indian NCS/NSDC datasets are not integrated; all external sources remain static snapshots/reference-first. Failed refreshes preserve the previous file while setting failure status; consumers must inspect cache freshness before use. The frontend dependency-backed TypeScript typecheck and Vite production build remain unverified because npm packages cannot be installed in the environment. Authentication, server-side authorization, verified guardian consent, data export/retention policies, managed backups, deployment security and a production privacy/security audit remain blockers for real student/minor data.

**Stage 16 exit assessment:** The synthetic demo's saved challenge/evidence trail persists across repeat initialization, preferences survive repository recreation, recommendation snapshots retain algorithm/source metadata, schema bootstrap is repeatable, API errors do not expose raw details, and external-source cache/retry failure cases are tested. Stage 16 is complete within the stated prototype scope. Stage 17 has not started and awaits explicit approval.


## Stage 17 — Explainability and source validation UI

**Status:** Complete within the documented prototype scope.

**Implemented:**
- Added a read-only `GET /api/source-registry` endpoint and `SourceRegistry` interface showing source publisher, official/supporting links, version/release, geography, licence/terms status, known limitations, truthful `live`/`cached`/`curated`/`link_only`/`unavailable` status, last successful app-side sync separately from last review, attempt status, checksum and active snapshot ID where present.
- Surfaced source/canonical records explicitly marked conflicted and kept non-exact/unresolved taxonomy mappings in a distinct uncertainty panel. An empty list is not described as proof that sources agree.
- Fixed graph audit metadata decoding: the graph repository stores JSON-encoded values, so the source registry now decodes `built_at`, `active_snapshots`, versions and limitations before reporting. It uses the graph builder’s successful active-snapshot selection logic to compare currently active versus graph-built snapshots and marks stale graphs explicitly.
- Added expandable recommendation audit trace from distinct relevant student observations and recency → local heuristic rules linked to evidence → externally sourced occupational work facts with record URLs/version/geography → evidence gaps and next validating task. Counts are computed over all relevant distinct evidence even when detail display is bounded.
- Added `backend/tests/test_stage17_source_registry.py`, `backend/tests/test_stage17_ui_contract.py`, and a recommendation test for distinct observation count/recency. Added `docs/STAGE17_EXPLAINABILITY_SOURCE_AUDIT.md`.

**Checks run:** `PYTHONPATH=backend pytest -q` — **196 passed**; `PYTHONPATH=backend python -m compileall -q backend/app backend/tests` — passed; JSON/YAML manifest contract and frontend TSX syntax checks passed; graph status smoke test reports 109 nodes/109 edges, two active curated snapshots, and `is_stale: false`; ZIP integrity and contents verified.

**Limitations:** external conflict discovery is limited to records explicitly marked conflicted in the local provenance store; the curated source graph contains only ten occupation identities and no live source feed is claimed. Full frontend typecheck/Vite production build and browser E2E checks remain unverified because npm dependencies were unavailable. API authentication/authorization and verified guardian consent remain production blockers.

**Stage 17 exit assessment:** A reviewer can trace a recommendation through student evidence, local matching logic and cited occupational source facts, and can inspect source sync status, source-record conflicts, uncertain mappings and graph snapshot freshness. Stage 17 is complete within the documented prototype scope. Stage 18 has not started and awaits explicit approval.


## Stage 18 — Privacy, security, fairness, accessibility, and child safety

**Status:** Complete within demo-only hackathon prototype scope.

**Implemented:**
- Added `docs/PRIVACY_AND_SAFETY.md` with data inventory/minimization, purpose limitation, sensitive-inference prohibitions, minor-consent boundaries, user review/correction/deletion, fairness/accessibility checklist, implemented controls, and mandatory production release gates.
- Added `backend/app/schemas/privacy_validation.py` to reject obvious email/phone/long-number identifiers in selected free-text fields, including recursively nested context. The rejection is deliberately narrow and does not claim comprehensive sensitive-data detection.
- Added validators for profile/goals, evidence and rubric text, calibration, baseline answers, challenge outputs/reflections and pathway input context. Validation errors do not echo entered values.
- Hardened `backend/app/main.py`: request IDs, safe validation errors, route-template and exception-type-only logging, `nosniff`/frame/referrer/permissions/content-security headers, private response no-store behavior, exact HTTPS-only configured CORS in production, and a fail-closed 503 guard for student-data routes in production until authentication, per-profile authorization and verified consent exist.
- Added a prominent demo-only privacy notice to profile creation, including no-real-student/child-data guidance, correction/deletion explanation and explicit guardian self-attestation limitation. Added tests for consent, deletion cascades, input handling/no-echo, production route/CORS gates, response headers, log redaction and accessible journey contracts.

**Checks run:** `PYTHONPATH=backend pytest -q backend/tests tests` — **217 passed**; Python compilation passed; JSON/YAML and TSX syntax/CSS checks passed where available.

**Limitations:** no actual authentication, ownership/authorization, independently verified guardian authority, comprehensive DLP, or legal compliance review against current Indian DPDP rules is in place. Avoid real student/minor data and public deployment. Full dependency-backed frontend typecheck/build and browser/screen-reader testing remain unverified because npm dependencies were unavailable.

**Stage 18 exit assessment:** written privacy/safety checklist and automated consent/deletion/input/accessibility tests are complete. Production release gates remain open by design. Stage 19 has not started and awaits explicit user approval.


## Stage 19 — Functional, data, and recommendation validation

**Status:** Complete within automated demo-validation scope.

**Implemented/validated:** Added deterministic scenario coverage for broad age-10 exploration with no evidence; age-16 software goal with low evidence and non-coding alternative; design/communication evidence beside a software goal; adult portfolio-based actionable gap analysis; adult unclear/conflicted evidence leading back to discovery; operation without LLM keys/live network; stale or source-less credentials not being asserted as current prerequisites; evidence correction/deletion and historical recommendation snapshots; independent performance/enjoyment signals; and current-goal changes with retained goal history. Data tests validate curated snapshot record count, non-duplicate source identities/URLs, required provenance and links, manifest source states, ten authored domain mappings, and non-exact cross-taxonomy semantics. Added `docs/VALIDATION_REPORT.md` with scenario matrix, data quality results, unverified checks, and a future consent-based pilot plan.

**Checks run:** `PYTHONPATH=backend pytest -q backend/tests tests` — **234 passed**; `PYTHONPATH=backend python -m compileall -q backend/app backend/tests` — passed; 16 JSON files and `data/sources_manifest.yaml` parsed successfully. Data record count assertions verify 10 curated records (9 O*NET OnLine extracts, 1 ESCO concept).

**Limits:** These tests establish expected behavior for code and curated data contracts, not psychometric validity, predictive validity, fairness in deployment, source availability at the current remote URL, or career outcomes.

**Stage 19 exit assessment:** All ten specified functional/data/recommendation scenarios are represented by automated tests. Stage 20 follows below.

## Stage 20 — Demo hardening, documentation, and handoff

**Status:** Complete within documented environment and hackathon prototype limits.

**Implemented:** Reproducible idempotent synthetic fixtures for 10–14, 15–17 and 18+; `scripts/demo_walkthrough.py` for a local-only live HTTP challenge submission and evidence/next-step assertion; `docs/ARCHITECTURE.md` Mermaid component/data-flow diagram; `docs/JUDGING_DEMO_SCRIPT.md`; updated README startup, source import/rebuild, demo, troubleshooting and release-boundary instructions; `docs/PROJECT_STATUS.md`; and this final validation/build record. The existing `docs/PRODUCT_CONTRACT.md`, `docs/DATA_SOURCE_REGISTER.md`, `docs/DECISIONS.md`, and `docs/PRIVACY_AND_SAFETY.md` remain the governing product/source/decision/safety references.

**Fresh smoke test:** Using a new isolated SQLite path: migrations 1–2 applied; three fixtures seeded; curated import returned 10 records/32 career facts with `runtime_fetch_performed: false`; graph rebuild produced 109 nodes/109 edges, active snapshots matched, `is_stale: false`, `source_data_is_live: false`. A local Uvicorn server was exercised by `python scripts/demo_walkthrough.py --base-url http://127.0.0.1:8765`. The script passed: age-15–17 challenge evidence count rose from 3 to 4, submissions rose by one, and the next task changed to `data-story` with an explicit reason.

**Checks not run / blocked:** An actual `npm run build` attempt failed because `react`, `vite` and `@vitejs/plugin-react` are absent from `frontend/node_modules`. It also exposed an invalid `allowImportingTsExtensions` configuration in the referenced node project; `frontend/tsconfig.node.json` was corrected to compile into `node_modules/.tmp` without that option. Dependency-backed build, browser E2E/responsive screenshots, and screen-reader testing are not claimed as passing. Available TSX syntax transpilation/CSS parsing are source-level checks only. No production identity/access-control/verified guardian-consent implementation or legal/security certification was attempted.

**Stage 20 exit assessment:** A new developer has exact setup/demo/ingestion commands, an architecture overview, a judging script, a validation report, synthetic fixtures and an executable demo smoke walkthrough. Stages 19–20 are closed for this hackathon prototype; the remaining production and evaluation gates are explicit.

## Merge: themed frontend (Stages 1–15) + Stage 16–20 package

- **Objective:** combine the Stage 20 backend/docs/tests with the themed motion frontend and theme the Stage 16–20 surfaces.
- **Changed:** backend/data/docs/scripts/tests replaced by the Stage 20 versions; themed components updated (CareerRecommendations audit trail, EvidenceLedger privacy notice/consent, DiscoveryLoop links); new BaselineAssessment, SourceRegistry, PersistencePanel, PrivacyControls, DemoProfiles; new motion components; routes `/baseline`, `/demo`.
- **Checks run:** frontend `tsc -b` passed; 13 static frontend contract tests passed (rewritten for the multi-page layout); backend files compile.
- **Not run:** backend pytest suite (dependencies unavailable in the merge environment), `vite build`, browser/mobile rendering, screen-reader testing. Run `pytest`, `npm run build` locally before relying on this.
- **Risks:** `PathwayPlanner` was not changed in the merge; the themed `data/skillscope.db` was not carried over (the database is recreated and demo fixtures seeded on startup).
