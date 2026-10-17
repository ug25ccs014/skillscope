# SkillScope AI — Project Status

**Current checkpoint:** Stage 13 of 20 — Career pathway and action-plan engine  
**Stage status:** Stage 13 implemented and regression-tested within the source-linked curated-graph prototype scope. Full O*NET/ESCO and Indian NCS/NSDC datasets remain unintegrated.  
**Current backend verification:** 161 tests passed. Frontend TSX syntax transpilation is checked; dependency-backed TypeScript typecheck and Vite production build remain unverified because npm installation/registry access has failed in this environment.

## Implemented stages

| Stage | Status | Outcome |
|---|---|---|
| 1. Greenfield foundation | Complete with environment limitation | React/TypeScript/Vite/Tailwind source and FastAPI health endpoint; frontend dependency installation/build remains unverified. |
| 2. Product contract and MVP boundary | Complete | Product promise, user scenarios, scope, acceptance criteria, and evidence/source guardrails. |
| 3. Age modes and entry calibration | Complete | Distinct 10–14, 15–17 and 18+ modes with contextual, reversible starting-path selection; stateless and non-diagnostic. |
| 4. Source research and licence audit | Complete at research level | Audited candidate sources and documented access/reuse limits. |
| 5. Provenance model and canonical data contract | Complete | Source records, canonical entities, provenance links and career facts, with lineage enforcement. |
| 6. Data ingestion and normalization | Complete within documented scope | Versioned and idempotent curated, O*NET CSV and ESCO CSV ZIP ingestion paths with validation and failure history. Full-source acquisition remains blocked/unverified. |
| 7. Career & Skill Knowledge Graph | Complete within documented scope | Version-aware graph projection, source-linked profile/task/skill-reference nodes, crosswalk audit, status/staleness checks, read-only APIs and cited frontend exploration section. |
| 8. Student profile & evidence ledger | Complete within documented scope | Consent-aware profiles, timestamped typed evidence, goal-change history, per-item behavior consent, correction/deletion controls and deterministic no-score signal summaries. |
| 9. Exploratory baseline assessment | Complete | Age-scaled baseline with self-report and activity evidence; explicitly non-validated. |
| 10. Challenge library and scoring | Complete | 12 authored challenge families, 36 age variants, nine domains, transparent rubric scoring. |
| 11. Daily/regular discovery loop | Complete within prototype scope | Persisted activity/evidence history, age-scaled next task, student-led interpretation, explainable deterministic policy and frontend interaction. |
| 12. Transparent recommendation and confidence engine | Complete within prototype scope | Versioned configurable initial heuristics, age-specific outputs, evidence confidence distinct from matching, cited source facts, explicit gaps, and deterministic next validation. No fit percentages. |
| 13. Career pathway and action-plan engine | Complete within prototype scope | Age-aware, persistent plans; goal-change history; source-backed skill/work context; prerequisite caveats; gated time horizons. See `docs/PATHWAY_PLANS.md`. |
| 14. User journeys and information architecture | Implemented, browser verification pending | Multi-page site with navigation, journey continuity, offline/404 states. See `docs/SITE_MAP.md`. |
| 15. Frontend and visual design | In progress (parts 1-2) | Motion graphics added (bus roadmap, confidence gauge, mode compass, scroll reveal) plus a planner crash fix. See `docs/FRONTEND_MOTION.md`. Typecheck/build/browser checks pending. |
| 16–20 | Not started | Await explicit approval after the Stage 13 checkpoint; see the master prompt for future scope. |

## Current source-backed coverage

The bundled curated snapshot now contains **10 profile records**: nine O*NET OnLine occupations and one ESCO software-developer concept. The O*NET records cover software development, data science, graphic design, market research/marketing, social and human services, solar PV installation, environmental science, project management, and electrical/electronic engineering technology. Source URLs, publisher, version context, geography, licence/adaptation metadata and limitations are retained.

The source-listed “Essential Skills” labels on the O*NET OnLine profile pages appear in the graph as **45 occupation-scoped references**. Stable O*NET skill-element IDs and occupational numeric ratings were not captured in the curated fallback, so these nodes are intentionally not merged into canonical skill concepts and are never treated as student scores. SkillScope's `curation_domain` tags are editorial coverage metadata, not official taxonomy categories.

## Graph inventory

- **109 nodes:** 10 occupations, 45 occupation-scoped skill references, 45 work activities, 7 occupational terms, 2 heuristic capability hypotheses.
- **109 edges:** 45 occupation–skill references, 45 occupation–task relationships, 12 source-term associations, 4 capability-hypothesis support edges, 1 reviewed related-occupation mapping, 1 reviewed related-work-activity mapping and 1 unresolved exact-equivalence candidate.
- The graph reports zero unresolved relationship endpoints and `source_data_is_live: false`.
- O*NET Software Developers (15-1252.00) and ESCO software developer (2512.4) remain separate nodes. Their link is reviewed as related, not exact; an unresolved exact-equivalence question is also retained.

## Current limitations that remain material

- **Full O*NET Database 31.0:** not integrated. Direct runtime download attempts failed on DNS resolution.
- **Full ESCO classification package:** not integrated. The official package-selection/download workflow was not completed in this environment.
- **NCS India and NSDC:** not integrated. The graph does not claim Indian occupation equivalences, QP/NOS requirements, qualification prerequisites or career pathways.
- **Canonical skills:** the current curated O*NET skill labels lack stable source skill-element IDs and ratings; no cross-profile canonical skill identity is asserted. ESCO skill concepts and occupation-skill relations will become graph nodes/edges only after a genuine version-pinned package is imported and validated.
- **Frontend:** an install retry on 2026-10-17 timed out after npm registry DNS `EAI_AGAIN` errors. TSX syntax transpilation passed, but dependency-backed TypeScript typecheck and Vite production build remain unverified.
- No individual ability, aptitude, interest or career-fit score is derived from occupations, skill labels or aggregate labour-market data.
- Entry calibration (Stage 3) remains stateless. Stages 8–11 supply the consent-aware evidence ledger, exploratory baseline, age-scaled challenge scoring, and request-driven longitudinal discovery loop. Stage 12 adds transparent, versioned career-hypothesis recommendations with qualitative evidence confidence. Stage 13 turns them into age-appropriate, persistent action plans with goal history, skill-documentation checks, sourced work context, and explicit limits on time-boxing; neither stage is a validated prediction.

## Stage 7 verification

- `PYTHONPATH=backend pytest -q` — **94 passed**.
- `python -m compileall -q backend/app backend/tests` — passed.
- Curated snapshot JSON, canonical JSON contract and YAML source manifest parse successfully.
- Clean import of the bundled snapshot — 10 records and 32 career facts; snapshot SHA-256 and active snapshot ID recorded in the ingestion state.
- Graph rebuild — 109 nodes and 109 edges with matching active-snapshot metadata.
- API smoke checks cover status, careers, source-cited skills, crosswalks, pagination, invalid/stale state handling, and lineage.
- ZIP integrity checked after packaging; generated SQLite database and raw source downloads are excluded from the archive.

## Stage 8 completion checkpoint

Stage 8 is implemented within the documented prototype scope. The current evidence ledger preserves timestamped, typed records and user corrections; empty signal dimensions remain `unknown`; no aptitude or career-fit score is computed. See `docs/STUDENT_EVIDENCE_LEDGER.md` and the Stage 8 section of `docs/MASTER_BUILD_LOG.md` for API contracts, test scope, and security limitations.

**Historical next checkpoint at the Stage 8 milestone:** Stage 9 — Baseline Assessment Engine. This was superseded by Stages 9–12; the current checkpoint is recorded at the top of this document.


## Stage 8 — Student Profile & Evidence Ledger

### Implemented

- `backend/app/schemas/student_evidence.py` defines age bands, consent basis, evidence types, signal dimensions, source kinds, uncertainty, user interpretations, rubric observations, profiles and summary contracts.
- `backend/app/services/evidence_ledger.py` adds SQLite persistence, foreign-key cascade deletion, profile/evidence update, filtering/pagination, deterministic signal summaries, observation recency labels, and timestamped stated-goal history.
- `backend/app/api/student_evidence.py` exposes profile create/read/correct/delete, evidence list/add/correct/delete, summary, and permanent clear-history endpoints.
- `frontend/src/components/EvidenceLedger.tsx` exposes profile setup and consent confirmation, evidence capture, challenge rubric fields, repeated-behavior specific consent/context, summary, correction and deletion controls. `App.tsx` now includes the Stage 8 interface.
- `data/student_evidence_contract.json` and `docs/STUDENT_EVIDENCE_LEDGER.md` document contracts, summary semantics, APIs, deletion paths and boundaries.

### Invariants

- Ages 10–17 require a recorded guardian-consent confirmation; adults require student consent. Each evidence record stores the applicable consent basis, timestamp and notice version at capture. The prototype records a self-attestation; it does not verify identity or guardian authority.
- Repeated in-product behavior requires explicit consent for that exact record plus non-empty `activity_name` and `time_window` context. No background monitoring exists.
- Challenge performance requires a challenge label, rubric name and criterion-level observation. A numeric score requires the original scale.
- Initial goals and goal changes become dated self-report evidence. Corrections preserve original `recorded_at`; deletion is permanent.
- Empty signal dimensions return `unknown`, not zero; the summary computes no ability, aptitude, personality or career-fit score.
- This API is unauthenticated and not appropriate for publicly deployed real student/minor data.

### Checks run

- `PYTHONPATH=backend pytest -q` — **117 passed**.
- `python -m compileall -q backend/app backend/tests` — passed.
- TypeScript `transpileModule` syntax diagnostics — passed for `App.tsx`, `EvidenceLedger.tsx` and `main.tsx`.
- `npm install --offline` — blocked because the environment cache does not contain `@types/react`; dependency-backed typecheck and Vite production build remain unverified.
- API tests use isolated temporary SQLite databases and test age consent, specific behavior consent, context, source types, rubric/scale validation, goal history, mixed/unknown summaries, filtering, corrections, timezone validation and deletion/cascade behavior.

### Limitations

- Authentication and server-side authorization are not implemented; profile UUIDs are record locators only. Consent confirmation does not verify identity or legal authority.
- No secure guardian invitation/verification, retention automation, data export, or production privacy/security audit is implemented.
- Browser storage retains an opaque profile UUID in localStorage to reopen a profile; the service persists evidence in SQLite.
- Full frontend typecheck/build could not run because npm dependencies are unavailable offline and the registry has previously failed DNS resolution.
- Stage 12 transparent recommendation/confidence engine and Stage 13 pathway/action-plan engine are implemented within prototype scope; Stage 14 onward has not started.

**Historical next checkpoint at the Stage 8 milestone:** Stage 9 — Baseline Assessment Engine. This was superseded by Stages 9–12; the current checkpoint is recorded at the top of this document.


## Stage 11 completion checkpoint

The discovery loop is implemented through `GET /api/discovery-loop/{profile_id}`. It derives the next age-scaled challenge from the persisted challenge-submission history, evidence count/domain exposure, the student's explicit interpretation of the latest activity, and an optional journey preference. The policy is versioned (`discovery-loop-v1.0`) and returns its reason code, explanation, next step, latest result, and coverage status. The React discovery panel supports consent-confirmed profile creation, a real challenge submission, criterion-level scoring, separate self-report/reflection, and a visible updated next recommendation. Activity and evidence persistence share Stage 10's SQLite transaction.

The loop is intentionally request-driven. No scheduler, email, push notification, or reminder service is implemented. The policy does not infer domain conflicts from free-text goals or use cross-rubric totals to rank skill/ability. Auth, server-side authorization, verified guardian consent, and production protection for minor data remain prerequisites for external deployment.

**Stage 11 checks:** 138 backend tests passed; Python compilation passed; contract validation passed; TSX syntax transpilation passed for `App.tsx`, `EvidenceLedger.tsx`, `DiscoveryLoop.tsx` and `main.tsx`. Dependency-backed TypeScript checking and the Vite production build remain unverified because React/npm dependencies are unavailable in this environment.


## Stage 12 completion checkpoint

The transparent recommendation engine is exposed through `GET /api/recommendations/{profile_id}?limit=5`. Its versioned initial heuristic weights are configurable in `data/recommendation_weights.json`; taxonomy-identity-bound SkillScope-authored domain hypotheses are in `data/career_domain_hypotheses.json`. The service provides explainable recommendation categories, evidence references, skill/goal/context matches, qualitative evidence-confidence breakdowns, explicit unknowns, source-attributed work activities, and a next validating challenge. Ages 10–14 receive broad domains without occupation labels.

**Stage 12 checks:** 153 backend tests passed, including 15 recommendation tests; Python compilation and JSON policy/domain mapping validation passed. A current-graph TestClient smoke test returned five recommendations over the ten-profile curated catalog, with cited source facts and a temporary profile deleted afterward. TSX syntax transpilation passed for the five principal frontend entry/component files. Dependency-backed TypeScript typechecking and Vite production build remain unverified because npm dependencies could not be installed in this environment.

**At the Stage 12 milestone, the next checkpoint was Stage 13; its completion is recorded below.


## Stage 13 completion checkpoint

Stage 13 adds `backend/app/schemas/pathway_plans.py`, `backend/app/services/pathway_plans.py`, and `backend/app/api/pathway_plans.py`; routes are registered in the API. The plan repository persists immutable snapshots in `pathway_plans` and reuses the evidence ledger for dated goal history. Goal edits recalculate from retained evidence rather than clearing history. The frontend `PathwayPlanner.tsx` supports loading the latest plan/history, editing goals, adult-only planning inputs, source display, unknown-skill statuses, revision guidance, and age-specific actions.

**Stage 13 checks:** `PYTHONPATH=backend pytest -q` — 161 passed; Python compilation and contract validation passed; frontend TSX syntax transpilation passed where available; plan API creation/latest/history smoke test passed using a temporary profile; ZIP integrity and package-content audit passed. Dependency-backed TypeScript typecheck and Vite build remain unverified because npm packages could not be installed in the environment.

**Current known limitations:** the source graph is a small curated extract; formal qualification relations and verified India-specific credentials are absent for the current hypotheses; any skill not documented is marked unrecorded rather than a deficiency; timeline ranges and suggested actions are heuristics, not guarantees. The API remains unauthenticated and is not safe for production use with real minors' data.

**Stage 13 exit assessment:** plans have actionable ordered steps, expected outcomes, supporting evidence/source references where available, explicit prerequisite/source limitations, and clear edit/recalculate controls. Stage 13 is complete within the documented prototype scope. Stage 14 has not started and awaits explicit approval.
