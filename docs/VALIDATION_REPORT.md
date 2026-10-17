# SkillScope AI — Stage 19 Validation Report

**Run date:** 2026-10-17  
**Scope:** Functional behavior, data integrity, recommendation honesty, privacy-boundary regression, and a synthetic local demo.  
**Classification:** Engineering validation of a hackathon prototype; **not** psychometric validation, production certification, or evidence of improved career outcomes.

## Executive result

- **Automated regression:** `PYTHONPATH=backend pytest -q backend/tests tests` — **234 passed** on the final re-verification run (2026-10-17).
- **Python syntax/bytecode compilation:** `PYTHONPATH=backend python -m compileall -q backend/app backend/tests` — passed.
- **Career-data integrity tests:** four Stage 19 source-snapshot/manifest/domain-mapping checks passed as part of the regression suite.
- **Frontend:** TSX syntax transpilation and CSS parsing are available static checks, not substitutes for a TypeScript project build or browser test. A dependency-backed `npm run build` was **attempted and failed** because project dependencies are absent (`react`, `vite`, and `@vitejs/plugin-react` cannot be resolved); the initial TypeScript config diagnostic was fixed in `frontend/tsconfig.node.json`, but the build remains blocked until dependencies are installed. Browser E2E was not run.
- **External datasets:** the packaged graph uses a small, local curated extract, not complete O*NET/ESCO downloads and not a live API. No external network/API key is required for the core discovery loop.

## Final Stage 19–20 re-verification (2026-10-17)

The release checks were rerun against the working project and a fresh isolated SQLite database, not inferred from the previous checkpoint:

- **Regression tests:** `PYTHONPATH=backend pytest -q backend/tests tests` — **234 passed**.
- **Python compilation:** `python -m compileall -q backend/app backend/tests tests` — passed.
- **Configuration/data files:** all 16 JSON files and `data/sources_manifest.yaml` parsed successfully.
- **Clean initialization:** database migrations and synthetic fixtures initialized successfully; `status` returned `ready` with all three expected age bands.
- **Curated import:** 10 records and 32 career facts imported; report confirms 9 O*NET OnLine curated pages plus 1 ESCO concept, with no duplicate rows skipped.
- **Knowledge graph:** rebuild/status passed with 109 nodes, 109 edges, `is_stale: false`, one unresolved crosswalk retained explicitly, and `source_data_is_live: false`.
- **Live HTTP walkthrough:** `/api/system/persistence` returned HTTP 200 and 3 fixtures. `scripts/demo_walkthrough.py` completed a synthetic challenge; evidence count increased from 3 to 4 and the next activity changed from `pattern-detective` to `data-story` with a reason.
- **Frontend static checks:** TypeScript transpilation parsed 10 `.ts`/`.tsx` source files with zero syntax diagnostics; the CSS parser accepted the stylesheet.
- **Full frontend build:** `npm run build` was attempted and remains **blocked**, because this runtime lacks the local `react`, `vite`, and `@vitejs/plugin-react` packages. The resulting missing-package/JSX type diagnostics are not evidence of a clean typecheck; install dependencies in a network-enabled environment and rerun `npm run build` before claiming frontend build success.
- **Release archive:** ZIP integrity check passed; required README/status/build-plan documents are present; no `.git`, `node_modules`, Python/pytest caches, compiled Python, SQLite databases, local `.env` files, or nested ZIPs were packaged.

This verifies local deterministic behavior and packaging, not browser E2E, live remote source availability, legal compliance, psychometric validity, penetration-test readiness, or production safety.

## Stage 19 scenario coverage

| Scenario | Check and expected behavior | Result / evidence |
|---|---|---|
| 1. Age 10, no prior activities | Broad domain exploration; no occupation label or definitive career conclusion | **PASS** — `test_under_15_recommendations_are_broad_domains_and_do_not_require_graph`; `test_entry_calibration.py` age-mode cases |
| 2. Age 16, software goal, little evidence | Baseline runs in `explore_and_validate`; software remains testable while a non-coding alternative is also offered | **PASS** — `test_stage19_teen_software_goal_low_evidence_keeps_both_coding_and_non_coding_options` |
| 3. Age 16, software goal with design/communication signals | Keep software as a possibility and show a design alternative linked to relevant observations | **PASS** — `test_stage19_teen_design_and_communication_evidence_retains_software_and_surfaces_alternative` |
| 4. Age 22, clear goal and portfolio | Produce practical, revisable gap/action planning without claiming guaranteed timing or probability | **PASS** — `test_stage19_adult_clear_target_and_portfolio_gets_practical_gap_analysis` |
| 5. Age 22, unclear goal and contradictory evidence | Re-open discovery/validation; do not force a “develop” recommendation or high confidence | **PASS** — `test_stage19_adult_with_no_goal_and_conflicting_interpretation_enters_rediscovery_without_forced_choice` |
| 6. Network/API key unavailable | Local baseline/challenge/recommendation loop works without LLM keys and truthfully marks source data non-live | **PASS** — `test_stage19_local_loop_does_not_require_external_api_keys_or_network`; catalog status also tested |
| 7. Conflicted source or stale qualification | Preserve provenance, mark conflict/staleness and do not assert an unverified/reti​red credential as a current prerequisite | **PASS** — Stage 17 source-registry conflict tests plus `test_stage19_stale_or_source_less_qualification_is_preserved_but_not_asserted_as_prerequisite` |
| 8. Evidence correction/deletion | Current profile/recommendation changes; previous recommendation snapshots remain auditable; deleted evidence is absent | **PASS** — `test_stage19_evidence_deletion_recalculates_recommendation_history`; `test_stage19_evidence_correction_is_reflected_in_future_snapshot_without_erasing_history` |
| 9. Performance vs enjoyment | Rubric observations/objective score and self-reported enjoyment are independent fields | **PASS** — `test_stage19_low_performance_high_enjoyment_and_high_performance_low_enjoyment_are_independent` |
| 10. Goal/mode change | Goal history is timestamped; age-band changes require fresh age-appropriate consent and preserve prior consent semantics | **PASS** — `test_profile_goal_is_timestamped_and_goal_changes_preserve_history` and profile update validation tests. Additional Stage 19 regressions explicitly test a no-evidence age-10 profile and a changed adult goal flowing into new recommendations while prior goal history remains traceable. |

These are deterministic behavior tests against synthetic test profiles. They do **not** establish that the recommendations predict ability, enjoyment, course completion, employability, or career success.

## Data and source-integrity checks

The active data contract tests establish the following for the bundled curation:

- Exactly **10** curated occupation records: nine records attributed to O*NET OnLine and one ESCO software-developer concept.
- Source identity is `(source_id, source_record_id)`; duplicate identities and duplicate record URLs fail tests.
- Required provenance includes publisher, source/version/date context, geographic scope, source access timestamp, HTTPS record/base/licence links, transformation notes, and limitations.
- Curated extract metadata explicitly records `runtime_fetch_performed: false`. It is not presented as a live fetch.
- The source manifest contains unique IDs and describes terms/licence state, geography, known limitations, and integration status. Full O*NET, full ESCO, NCS India, NSDC India and PLFS remain unintegrated/reference-first in this build.
- Every curated occupation maps to one SkillScope-authored domain hypothesis. The domain mappings are editorial exploration hypotheses, not official taxonomy categories. O*NET and ESCO occupation identities are not silently merged.
- The curated payload does not include salary, wage, employment-count, openings, or growth-rate values. Aggregate labour statistics are not used as individual potential scores.
- Source-record conflicts and graph snapshot freshness are surfaced by the source-registry code. Automated checks validate the current local record/metadata state; they do not independently browse the web to prove each remote URL is still available or confirm every licence interpretation with legal counsel.

## Demo run verification

`backend/tests/test_stage20_demo_fixtures.py` checks deterministic/idempotent initialization of three clearly marked synthetic fixtures for `10_14`, `15_17`, and `18_plus`, then completes a challenge through the API and checks that one evidence item is added and the next challenge changes with an explanation. The companion `scripts/demo_walkthrough.py` runs the same high-level live API path and refuses non-loopback hosts by default.

## Commands for a fresh local verification

Run from the repository root after installing `backend/requirements.txt`:

```bash
PYTHONPATH=backend pytest -q backend/tests tests
PYTHONPATH=backend python -m compileall -q backend/app backend/tests
PYTHONPATH=backend python -m app.services.database init --db /tmp/skillscope-stage20.db
PYTHONPATH=backend python -m app.services.database status --db /tmp/skillscope-stage20.db
PYTHONPATH=backend python -m app.services.ingestion.cli import-curated
PYTHONPATH=backend python -m app.services.knowledge_graph rebuild
PYTHONPATH=backend python -m app.services.knowledge_graph status
```

On Windows PowerShell, set the import path for the active command session before running Python, for example `$env:PYTHONPATH = "backend"`.

## Planned consent-based pilot (not yet conducted)

Do not recruit minors until institutional/guardian permissions, lawful basis, assent, data handling, retention, incident response, and an approved study protocol have been reviewed. A future small pilot should be explicitly framed as usability/relevance research, not a diagnostic or career-outcome trial.

1. **Design and approval:** preregister questions, inclusion/exclusion, recruitment and withdrawal procedure, data minimization, safeguarding/escalation, and independent ethics/legal review. Use separate approval and consent flows for adults and minors; do not use production personal data in the present demo.
2. **Age-stratified usability:** sample across 10–14, 15–17, and 18+ cohorts only if approvals permit; include diverse education/access contexts. Use a small exploratory sample first (for example, 5–8 usability sessions per allowed age cohort), explicitly not powered to estimate efficacy.
3. **Measures:** task completion, time-to-complete, abandonment, accessibility issues, perceived clarity/trust, explanation usefulness, perceived choice/agency, challenge enjoyment/difficulty, reflection quality, and user/counsellor relevance rating. Track missingness and withdrawals; never infer inability from non-completion.
4. **Fairness and safety review:** examine error and usability patterns by age band, language, device/accessibility needs, prior exposure and education context where ethically approved; suppress small cells and avoid collecting sensitive traits unless strictly approved and necessary. Review whether limited access/exposure is incorrectly described as a skill deficit.
5. **Analysis:** publish descriptive counts and uncertainty, separate self-reported relevance from measured task outcomes, record adverse events, and document disagreement between student and reviewer. Do not treat occupation/skill taxonomy overlap as psychometric validity.
6. **Decision gate:** fix safety/accessibility issues before broadening; define success thresholds before data collection; repeat with independent reviewers. A career-outcome or predictive-validity claim would require a separately designed, longer-term study with appropriate comparison design and privacy safeguards.

## Not verified / release blockers

- No psychometric validation, predictive/outcome validity study, external expert rating study, or longitudinal career-outcome evidence.
- No complete live O*NET/ESCO/NCS/NSDC feeds; local source records may become stale and should be reviewed before use outside a demo.
- No authenticated identity, server-enforced per-profile authorization, or independently verified guardian authority; production student-data routes fail closed, but this does not replace a complete security architecture.
- No qualified legal review of current Indian DPDP requirements, no comprehensive data-loss prevention, no deletion-from-backup/retention automation, and no independent penetration test.
- No dependency-backed frontend TypeScript/Vite build, browser-based end-to-end/accessibility inspection, screen-reader audit, or deployment smoke test in this environment.
- The demo script and tests use synthetic data only. Never put actual child/student personal data into a public or shared deployment.
