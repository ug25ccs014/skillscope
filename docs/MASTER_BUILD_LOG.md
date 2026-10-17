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


## Stage 15 checkpoint (part 1: motion graphics) — 2026-10-17

**Objective:** Begin the Stage 15 frontend/visual work with motion graphics driven by real plan, recommendation and calibration data. Stage 14 (formal navigation/IA and journey states) has NOT been done yet and is still required.

**Implemented:**
- Fixed a runtime bug in `PathwayPlanner.tsx`: an effect referenced `loadPlan` before it was declared (temporal dead zone), which would throw on first render. The effect now sits after `loadPlan`.
- Added `frontend/src/motion/` with `RoadmapBus`, `ConfidenceGauge`, `ModeCompass`, `RevealOnScroll` and `usePrefersReducedMotion`; added keyframes to `index.css`; documented in `docs/FRONTEND_MOTION.md`.
- Wired: RoadmapBus into `PathwayPlanner` (above ordered steps), ConfidenceGauge into `CareerRecommendations`, ModeCompass into the calibration result, RevealOnScroll around the four main sections. Header label updated from "Stage 11" to "Prototype · Stage 15 UI".

**Checks run:** TypeScript transpile syntax diagnostics passed for all 11 frontend files touched or present in `src/`. Server-side render smoke test passed for RoadmapBus (5 stops, 1 stop, 0 stops), ConfidenceGauge and ModeCompass. **Not run:** dependency-backed `tsc`, Vite build, any browser test, and backend tests (backend was not modified; last recorded result was 161 passed). npm registry access failed in this environment.

**Limitations:** Animation timing is unverified in a real browser. Stage 14 deliverables and the remaining Stage 15 surfaces (source/privacy status panel, mobile/desktop overflow audit) are not done.


## Stage 14 + Stage 15 (part 2) checkpoint — 2026-10-17

**Objective:** Replace the single long scrolling page with a real multi-page site (navigation, page structure, journey continuity), remove internal stage labels from the UI, and add a Home page.

**Implemented:**
- Split the 797-line `App.tsx` into `router.ts`, `layout/SiteLayout.tsx`, `shared/api.ts`, `shared/content.ts` and `pages/` (Home, Start, Profile, Challenges, Careers, Plan, Sources & privacy). `App.tsx` is now a small router shell.
- Added sticky header with mobile menu, backend status pill and offline banner, skip link, footer, page-change focus/title handling, 404 page, and "Continue" cards between pages.
- Added a Sources & privacy page (cited knowledge graph plus a plain-language privacy section reflecting actual behaviour).
- Removed all "Stage N" labels from user-facing text; each page now has a single `h1`.
- Fixed two build-breaking issues that `noUnusedParameters` would have flagged (unused `index` in `CareerRecommendations.tsx`; leftover references during the split).
- Added `docs/SITE_MAP.md` and a Windows Command Prompt run guide in `README.md`.

**Checks run:** syntax check passed for all 20 TS/TSX files; a semantic scan for unused/undefined identifiers reported 0 issues; every route (plus an unknown route) server-rendered without error and with no stage labels. **Not run:** `npm install`, full `tsc`, Vite build, browser/mobile testing, backend tests (backend unchanged; last recorded 161 passed).

**Stage 14 exit assessment:** navigation, journey continuity and the empty/offline/unknown-route states are implemented in code. The "complete the journey without dead ends" gate is not yet confirmed in a running browser.


## Motion stages M0 + M1 + M2 checkpoint, with dead-page fixes — 2026-10-17

**Objective:** Add the motion foundation (M0), the constellation hero (M1) and the tilting mode cards (M2) from `SkillScope_AI___Motion___3D_Frontend_Prompt.md`; make the site less text-heavy; remove dead ends.

**Files changed or added (frontend only; backend untouched):**
- New in `src/motion/`: `useMotionPreference.ts`, `SmoothScrollProvider.tsx`, `gsapSetup.ts`, `LazyCanvas.tsx`, `constellationData.ts`, `ConstellationCanvas.tsx`, `ConstellationSvg.tsx`, `ConstellationHero.tsx`, `GradientBackdrop.tsx`, `ModeContext.tsx`, `modeConfig.ts`, `TiltCard.tsx`, `ModeCards.tsx`.
- New: `src/layout/JourneyStrip.tsx`.
- Changed: `package.json`, `tailwind.config.js`, `src/main.tsx`, `src/index.css`, `src/layout/SiteLayout.tsx`, `src/pages/HomePage.tsx`, `src/pages/StartPage.tsx` (mode cards tilt and follow the entered age; form logic unchanged), `src/pages/PageParts.tsx`, `src/pages/FlowPages.tsx`.
- Docs: `DECISIONS.md`, `FRONTEND_MOTION.md`, this log.

**Dead pages fixed:** Careers and Plan showed only a small text notice when no profile existed, and the Home call to action led straight to Careers. Both now show an illustrated empty state with three working next steps (create profile, try a challenge, find starting path).

**Packages added:** lenis, gsap, @gsap/react, three, @react-three/fiber, @types/three, @fontsource-variable/inter, @fontsource-variable/fraunces (version ranges only; see Decisions M-1 to M-3 in DECISIONS.md).

**Checks actually run:** TypeScript transpile syntax diagnostics: 34 files, 0 errors. Unused-import scan on the new and changed files: 0 findings.
**Not run (no npm registry access in the build environment):** `npm install`, `npm run typecheck`, `npm run build`, any browser test, WebGL rendering, 360/768/1440 px layout check, reduced-motion pass, WebGL-off pass, Lighthouse, axe, bundle sizes, backend tests (backend unchanged; last recorded 161 passed). **No performance numbers exist yet.**

**Exit gates M0 to M2:** not confirmed. Each needs the commands above run on a machine with npm access. Skipped on purpose: ShaderGradient, drei, Motion (see Decision M-3).

**Next:** M3 (flashcard scroll sections and flip cards) after approval.

## Motion stage M3 checkpoint — 2026-10-17

**Objective:** Pinned "How it works" card stack on Home and flip cards for career recommendations.
**Files:** new `src/motion/FlipCard.tsx`, `src/motion/FlashStack.tsx`; changed `src/components/CareerRecommendations.tsx` (summary flip card above the unchanged detail, now inside a collapsible), `src/pages/HomePage.tsx`, `src/index.css`, `docs/FRONTEND_MOTION.md`, this log. No new packages. Backend untouched.
**Checks run:** TypeScript transpile syntax diagnostics, 36 files, 0 errors.
**Not run:** `npm install`, typecheck, build, browser, keyboard walk-through, screen-reader check, layout at 360/768/1440 px. M0 to M2 results were also never reported back, so earlier gates remain unconfirmed.
**Skipped:** optional draggable deck for 10 to 14.
**Exit gate M3:** not confirmed (needs a keyboard-only flip test and a real recommendations response).

**Fix after first real `npm run typecheck` (2026-10-17):** `motion/modeTheme.ts` collided with `motion/ModeTheme.tsx` on Windows (case-insensitive file names, TS1149). Renamed to `motion/modeConfig.ts` and updated imports. `tsconfig.node.json` had `allowImportingTsExtensions` without `noEmit` (TS5096, present before the motion work); the option was removed because `vite.config.ts` does not need it.

**Second fix (2026-10-17):** the old `modeTheme.ts` was still on disk, so `./ModeTheme` kept resolving to it. `ModeTheme.tsx` is now `ModeContext.tsx`, so no import depends on letter case. A leftover `modeTheme.ts` is unused and may be deleted.
