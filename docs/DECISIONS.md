# Architecture & Product Decisions

## D-001 — Greenfield implementation

**Decision:** Build from an empty project; no existing application or code is assumed.

**Reason:** The project starts from scratch, and stages must be implemented in order.

## D-002 — Frontend/backend split

**Decision:** React + TypeScript + Vite + Tailwind CSS for the frontend; FastAPI for the backend.

**Reason:** Clear separation of presentation and testable API; fits the agreed coding-agent prompt.

**Constraint:** npm registry access was unavailable in the current build environment (DNS/network error). Package manifests and source were created, but frontend dependencies/build cannot be truthfully reported as installed or verified here. Install via `npm install` in a network-enabled environment.

## D-003 — SQLite target, delayed implementation

**Decision:** SQLite is the MVP persistence target; no database connection or schema is created in Stage 1.

**Reason:** The initial scope is a runnable foundation. Introduce persistence with a deliberate schema in its dedicated stage; keep a PostgreSQL migration path.

## D-004 — Heuristic recommendations, not an LLM scorer

**Decision:** Future MVP matching should be deterministic, configurable, evidence-led, and explainable. Any generative model should only help with wording/challenge drafting and must not invent evidence.

**Reason:** Reproducibility, traceability, privacy, and time-boxed MVP reliability.

## D-005 — Sources start as an unaudited shortlist

**Decision:** `data/sources_manifest.yaml` lists the official candidate sources from the master prompt as `not_integrated` and `not_yet_verified`.

**Reason:** Stage 1 must not misstate a URL list as data integration. Stage 4 owns the access and licence audit.

## D-006 — Age and entry calibration are distinct

**Decision:** Age band selects an age-appropriate initial experience, while evidence quality/volume, goal clarity, prior experience, and exploration need determine the entry mode.

**Reason:** A late entrant should not be assigned fabricated history or forced into one fixed track.

## D-007 — MVP contract and vertical slice

**Decision:** The final MVP must demonstrate one connected journey from age-band entry through baseline calibration, evidence-backed profile, practical challenge and reflection, dated evidence update, explainable recommendation change, and source-traceable pathway guidance.

**Reason:** A coherent vertical slice is more useful for testing and judging than many disconnected screens.

**Constraint:** Stage 2 locks the contract only. Calibration, source integration, evidence recording, and recommendation logic belong to their respective later stages.

## D-008 — Hackathon data coverage favors verified quality

**Decision:** Aim for a small, diverse career/pathway subset (approximately 8–12 only if records can be verified) with traceable sources. A smaller verified subset is preferable to broad fabricated coverage.

**Reason:** Recommendations depend on accurate occupational/skill evidence, explicit geographic context, and source lineage.

**Constraint:** Source access and licence must be verified in Stage 4; no source is currently claimed as integrated.


## D-009 — Separate age mode from starting path

**Decision:** Entry calibration returns both an age-appropriate `age_mode` and a more flexible `starting_path`. Ages 10–14 begin with guided exploration; ages 15–17 begin with discovery/validation strategies; ages 18+ can begin discovery, goal validation, or a requirements gap review. A user's exploration preference and later goal changes can change the path without turning age into a fixed career track.

**Reason:** Joining age sets activity design; prior evidence, clarity, experience, exploration need, contradictions, and current goals shape where to start.

**Constraint:** The calibration uses explicit deterministic heuristics, version `1.0.0`, and returns rationale/limitations. It is not a validated aptitude model and does not persist a profile. Evidence-strength labels describe reported evidence coverage only.

## D-010 — Keep calibration stateless until profile schema stage

**Decision:** `POST /api/calibration` does not save submitted age, goal, evidence count, or related inputs.

**Reason:** Stage 3 establishes the entry-mode contract; durable profiles and evidence storage require a deliberately designed schema and privacy decisions in later stages.

**Constraint:** The UI states that inputs are used for this request only. Persistent longitudinal tracking must not be implied before its persistence, consent, correction, and deletion requirements are implemented.


## D-011 — Treat unfamiliar domains as exploration opportunities

**Decision:** Entry calibration can accept a user's short summary of activities already tried and a list of domains they have had little opportunity to experience. For adults, the form additionally accepts optional education/training, skills, project/work experience, user-chosen planning constraints, and a planning horizon.

**Reason:** A student who has not yet experienced a domain cannot fairly be assigned a negative signal for that absence. Adult planning also needs practical context, but users should not be forced to disclose constraints they prefer to keep private.

**Constraint:** These inputs are request-scoped only and are not persisted. A high reported evidence count alone does not unlock adult gap analysis; the input must also include a current skills or project/work experience summary. User-provided context is not independently verified.


## Stage 4 — Source strategy and evidence boundaries

- NCS and NSDC are the India-first references, but remain link-only until exact reuse permission is confirmed for selected pages/documents.
- Plan version-pinned bulk extracts of the downloadable O*NET Database and ESCO classification for supplementary structured occupation/skill relationships; preserve their non-Indian context.
- Do not use the O*NET Web Services API as though it has the same terms as the downloadable database; its account, attribution/application-registration and no-alteration constraints are separate.
- Do not reuse the O*NET Interest Profiler instrument in the MVP. Author original challenges/feedback prompts and do not call them validated psychometrics.
- PLFS may appear only as dated, sourced aggregate labour-market context; it must never feed student-level fit, interest, aptitude or ability scoring.
- No third-party source is integrated in Stage 4. A reviewed webpage is not the same as a tested runtime download or API integration.

## D-012 — Static, traceable snapshots; never imply a live data feed

**Decision:** Source adapters write only to an allow-listed raw-data area, validate assets and record checksums/metadata before importing into the canonical provenance registry. Successful imports are static snapshots. Bundled manually curated profiles remain `curated_extract` and must not be counted as a full O*NET/ESCO integration.

**Reason:** Reproducibility, safe reruns, truthful source status, and no invented live data when external access fails.

**Constraint:** Raw downloads are not committed or bundled. If DNS/network/permission blocks official ingestion, keep the source `not_integrated`, retain the actual error in the run ledger, and use only documented, appropriately labelled curated material. O*NET/ESCO occupation data remains U.S./European contextual reference rather than Indian demand evidence.


## D-013 — Keep curated skill labels occupation-scoped until stable IDs are available

**Decision:** Stage 7 may display the short labels listed under an O*NET OnLine occupation profile's “Essential Skills” section, but the curated snapshot must preserve the section name and must not fabricate source skill-element IDs or ratings. Each current label is linked to the occupation profile as a source-backed reference; matching labels across profiles are not merged into one canonical concept yet.

**Reason:** It makes authentic source-supported skill context inspectable without silently implying canonical identity, occupational importance weights, student proficiency, or psychometric validity.

**Constraint:** Full canonical skill nodes/edges should use actual source concept identifiers and source relationship records when a permitted version-pinned O*NET Database or ESCO package is imported. Existing O*NET/ESCO occupation crosswalk edges remain explicitly “related” unless an authoritative mapping supports a stronger claim.

## D-014 — Coverage tags are editorial metadata, not taxonomy or aptitude

**Decision:** `curation_domain` exists only to ensure the demo includes varied source-backed occupational examples.

**Reason:** The user-facing prototype should cover multiple kinds of work without inferring a student's ability or asserting an official career-category scheme.

**Constraint:** The tag is stored in normalized metadata separate from `source_values`, labelled in the UI as an editorial “coverage example”, and must never be used as student evidence or a recommendation score.


## Stage 8 decision — evidence ledger, not a personality score

Student records are timestamped, typed observations with context, source kind, uncertainty and capture-time consent metadata. The application does not infer an overall ability/aptitude/career-fit score. Empty dimensions are `unknown`, and explicitly user-labelled conflicts remain `mixed`. Goal changes append dated statements. Numeric task results must retain their own rubric/scale. Repeated in-product behavior is recorded only with per-item consent and activity/time-window context; background cross-app tracking is out of scope. Consent is presently a self-attestation and the API has no authentication, so real students/minors must not use a public deployment until the production controls in `docs/STUDENT_EVIDENCE_LEDGER.md` are implemented.


## D-015 — Validation is behavioral, not psychometric

**Decision:** Treat Stage 19 test results as software/data-contract verification only. Never translate passing unit tests, interest reflections, occupational text overlap, or challenge rubrics into a claim of validated aptitude, career-fit probability, employability, fairness, or career outcomes.

**Reason:** Engineering correctness and empirical validity answer different questions. A future consent-based pilot needs its own protocol, analysis plan and approval.

**Constraint:** The test matrix and unverified validation categories must remain visible in `docs/VALIDATION_REPORT.md`.

## D-016 — One local synthetic demo path is the release baseline

**Decision:** Use three idempotently seeded `synthetic_demo` fixtures across the 10–14, 15–17 and 18+ age bands, with the teen fixture available for a live challenge/evidence/next-step walkthrough. Keep the walkthrough restricted to loopback hosts by default.

**Reason:** Judges and developers need a repeatable journey that survives clean database initialization and can demonstrate a real API state transition without external service credentials.

**Constraint:** Fixtures are not users, are not evidence of effectiveness, and must never be mixed with real personal data. Production student-data access remains blocked until identity, authorization and verified consent are implemented.
