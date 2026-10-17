# SkillScope AI — 20-Stage Master Build Prompt

**Purpose:** Use this prompt with a coding agent (Claude Code, Antigravity, or a comparable agent) to plan, build, validate, and harden SkillScope AI without losing the product vision or inventing unsupported data.

---

## MASTER PROMPT — COPY FROM HERE

### Your role

Act as a senior product engineer, full-stack architect, data engineer, career-guidance researcher, UX designer, QA engineer, and privacy/security reviewer. You are responsible for delivering a working, demonstrable SkillScope AI MVP, not just a plan or mock-up.

**This is a greenfield project. Assume there is no existing repository, application, code, database, design system, or prior implementation to preserve.** Start from the empty workspace available to you. First verify the current working directory and available runtime/tooling; do not mistake unrelated environment files for project code. Choose a simple, maintainable architecture and document the choice. Unless the environment makes it impractical, use React + TypeScript + Vite + Tailwind for the frontend, FastAPI for the backend, and SQLite for the hackathon MVP, with a clean path to PostgreSQL later. Use a clearly separated frontend, backend, data, tests, and docs structure. Do not spend time searching for a nonexistent application or claim that legacy code was audited. If a dependency cannot be installed, record the blocker and use a compatible fallback rather than fabricating success.

### Product vision

**SkillScope helps people discover, validate, and develop their strengths and interests over time.** It is not a quiz that declares one “correct” career. It combines a user's stated interests, voluntary activities, challenge performance, projects, goals, and trustworthy career/skills data to propose testable possibilities and practical next steps.

Product principle: **“Most career guidance asks a student what they want to become. SkillScope helps them discover what they could become.”**

The product supports three broad life stages, but age must not be the only input to onboarding:

- **Age 10–14 — Discover & Shape:** safe, broad exploration through short activities across varied domains; identify tentative patterns, not fixed careers.
- **Age 15–17 — Explore & Validate:** establish a baseline quickly, test declared interests, identify missing exposure, and surface plausible alternatives with evidence.
- **Age 18+ — Develop & Optimize:** assess the current state, map gaps to chosen goals, propose projects/learning/opportunities, and compare alternative pathways where useful.

Every entry age must lead into the same continuous evidence-and-learning system. A person who joins late must not be treated as if SkillScope already knows their history. Age chooses the initial experience; **entry calibration** chooses how much exploration, validation, or optimization is needed. Users may change goals or re-enter discovery at any time.

### Non-negotiable execution rules

1. **Execute the 20 stages in order, one stage at a time.** Do not try to implement all stages in one giant run. For the current stage, make the intended changes, run available checks, document the result, and stop at its exit gate. Wait for the user's approval/instruction before beginning the next stage. If the user explicitly authorizes multiple stages, continue only through the approved range.
2. Stage 1 is greenfield initialization, not repository reconnaissance. Create the foundational project structure and developer documentation from scratch. At each stage, update a concise checkpoint in `docs/MASTER_BUILD_LOG.md`: objective, files changed, tests/checks run, outcome, unresolved risks, and next stage. Keep `docs/DECISIONS.md` for meaningful architectural/product decisions.
3. Do not invent integrations, API responses, dataset contents, credentials, test results, or successful network calls. If a source cannot be accessed, state that explicitly and use a clearly labelled, source-backed snapshot if a permitted one is available.
4. Use **real, attributable source data from more than one independent source** wherever it improves career/skill validation. Store a source manifest and provenance for every imported record. Do not use a generic synthetic/Kaggle dataset as authoritative occupational truth. Synthetic records are permitted only for explicitly labelled demo users and test fixtures.
5. Check each source's latest documentation, version, terms, licence, attribution requirements, access method, and country/sector coverage before integrating it. Do not scrape behind logins, bypass rate limits, ignore terms/robots rules, or collect unrelated personal data.
6. Separate **occupation facts**, **labour-market context**, and **the individual student's evidence**. These are different things and must never be silently conflated.
7. Prefer transparent, deterministic, testable recommendation logic for the MVP. An LLM may help phrase explanations or draft challenge text, but it must not invent student evidence, silently assign scores, or fabricate career facts. The app must still function if an LLM or external API is unavailable.
8. Do not claim a career match, psychometric test, model, or outcome is scientifically validated unless the exact method and validation evidence support that claim. Label initial scoring as a configurable heuristic and clearly record its limitations.
9. For minors, use age-appropriate design, data minimization, clear consent/guardian-consent handling, and safe defaults. Do not secretly track activity across unrelated platforms or infer sensitive personal traits. Never send a minor's identifiable personal information to an external model/API in the MVP.
10. Do not let the user interface present demo or stale source data as live. Show source, geography, version/as-of date, and whether a record is live, cached, or demo-only when relevant.
11. Do not add fake buttons, fake “AI analysis” states, placeholder charts presented as genuine findings, or unimplemented features advertised as complete.
12. Keep the application usable on mobile and desktop, handle empty/error/loading states, and include sensible keyboard and accessibility behavior.
13. If an external account/API key or other user-only credential is needed, create a clear configuration path and `.env.example`; do not invent a key or block all progress. Continue with an honest fallback and document the limitation.
14. Finish by giving a concise implementation report: what works, how to run it, data sources genuinely integrated, checks actually run, current limitations, and the demo flow.

### Data-source baseline to investigate

Treat these as an initial research shortlist, **not a claim that all have already been integrated or that every platform provides a public API**. Verify access and licensing before use.

1. **India National Career Service (NCS)** — https://www.ncs.gov.in/ and https://dge.gov.in/ncs. Investigate official sector/job-role information and Indian occupational context. Use permitted structured downloads or documented endpoints where available. If there is no usable public API for a field, link to the official information or include a small manually curated extract with a source URL and access date; do not pretend it was retrieved live.
2. **National Skill Development Corporation (NSDC)** — https://www.nsdcindia.org/national-occupational-standards-and-model-curriculum and https://www.nsdcindia.org/national-occupational-standards. Investigate National Occupational Standards, Qualification Packs, job-role competencies, and model curricula. Track the version/status of each qualification; avoid presenting retired standards as current.
3. **O*NET** — https://www.onetcenter.org/database.html and https://services.onetcenter.org/reference/online/data. Investigate occupations, skills, interests, abilities, work activities, education/training, and official API/bulk data. It is a useful structured reference but primarily reflects the US occupational context, so do not label it India-specific.
4. **ESCO (European Skills, Competences, Qualifications and Occupations)** — https://esco.ec.europa.eu/en/use-esco-services-api and https://esco.ec.europa.eu/en/use-esco/use-esco-services-api. Investigate its occupation/skill taxonomy and API or bulk download. Track the selected version. It provides European/multilingual classification context; do not treat its geographic context as India-specific.
5. **MoSPI Periodic Labour Force Survey (PLFS)** — https://esankhyiki.mospi.gov.in/catalogue-main/catalogue?page=0&product=PLFS. Use only as appropriately dated **aggregate labour-market context** (e.g., broad employment/industry patterns). Do not use aggregate labour statistics as evidence of an individual student's interests or abilities.
6. **Optional education context: UDISE+** — https://api.udiseplus.gov.in/ and https://www.data.gov.in/catalog/unified-district-information-system-education-plus-udise-plus. Use only if a particular aggregate education-context feature genuinely needs it. This is not an interest detector and must not be used to infer an individual child's aptitude.

For all sources, record the exact dataset/API/page, publisher, URL, accessed date, data version/release date, licence/terms checked, allowed use, geographic scope, last refresh, integration mode (API, official download, curated extract, or link-only), known limitations, and fields used. Verify source status again at build time; URLs and versions may change.

---

## Stage 1 — Greenfield initialization and runnable foundation

**Goal:** Turn the empty workspace into a clean, documented project foundation that can be run locally.

- Verify the working directory and available versions of Node.js, npm/pnpm, Python, and Git. Do not spend time looking for a pre-existing SkillScope implementation; none exists.
- Confirm the default architecture: React + TypeScript + Vite + Tailwind frontend, FastAPI backend, SQLite persistence for the MVP, and a documented route to PostgreSQL if needed. Adjust only if tooling constraints require it, and record the reason in `docs/DECISIONS.md`.
- Create the initial directory structure, for example `frontend/`, `backend/`, `data/`, `tests/`, and `docs/`, adapting it when a monorepo layout is more practical.
- Add `.gitignore`, `.env.example` with placeholder variable names only, README setup/run instructions, dependency manifests/lockfiles where supported, and scripts for local development.
- Create `docs/PRODUCT_CONTRACT.md` with the agreed product vision, age-aware entry calibration, data-source principles, privacy principles, and MVP boundaries. Create `docs/MASTER_BUILD_LOG.md`, `docs/DECISIONS.md`, and `docs/PROJECT_STATUS.md`.
- Implement the smallest real health check for the backend and a simple frontend shell that can reach or clearly report backend status. Do not build the full product UI in this stage.
- Install dependencies and run the initial frontend/backend startup checks, lint/type checks if configured, and a production build where practical. Report exact commands and outcomes.
- Keep secrets out of source control. Do not add fake dataset contents or describe unbuilt features as complete.

**Exit gate:** The greenfield folder structure and architecture are documented; frontend and backend have reproducible run commands; the minimal app shell and backend health endpoint work (or a precise environment blocker is documented); and a checkpoint exists in `docs/MASTER_BUILD_LOG.md`. Stop and wait for approval before Stage 2.

## Stage 2 — Product contract and MVP boundary

**Goal:** Define what SkillScope is and what the first demonstrable version must do.

Build the MVP around one coherent journey:

1. A user selects/enters an age band and completes a short baseline.
2. The system calibrates the starting mode using age, career clarity, available evidence, experience, and exploration need.
3. The user receives an evidence-backed, uncertainty-aware profile and a few candidate domains/career pathways.
4. The user completes a domain challenge and reflects on enjoyment, difficulty, and desire to continue.
5. SkillScope adds a new evidence record, shows what changed (and why), and recommends the next useful challenge or action.
6. Career cards explain relevant skills, likely gaps, practical next steps, and source evidence.

Separate the hackathon demo scope from future production features. Prioritize a complete vertical slice over many disconnected screens. Do not claim years of longitudinal insight from a new account.

**Exit gate:** `docs/PRODUCT_CONTRACT.md` specifies primary personas, core journey, MVP features, out-of-scope items, success criteria, and known assumptions.

## Stage 3 — Age modes and entry calibration

**Goal:** Make joining age change the initial experience without trapping people in a fixed track.

Implement the initial modes:

- **10–14 Discover & Shape:** short, safe, varied activities across creative, analytical, hands-on, social, communication, scientific, technical, environmental, and business domains. Report tentative patterns such as “worth exploring,” never “your ideal career.”
- **15–17 Explore & Validate:** ask what the student currently thinks they like, what they have tried, their confidence in a possible direction, and which areas they have not experienced. Validate stated interests using multiple types of challenges and intentionally sample alternatives.
- **18+ Develop & Optimize:** capture existing education, projects, skills, experience, goals, constraints the user chooses to disclose, and desired timeline. Produce practical gap analysis and an action roadmap while leaving room for career discovery.

Build an explicit **Entry Calibration** function. Its inputs should include age band, amount and quality of prior evidence, career clarity, prior projects/experience, and exploration need. Its output should include the starting mode, rationale, and next step. For example, a 16-year-old with low evidence and low career clarity should receive more discovery; a 22-year-old with a portfolio and clear goal may begin with gap analysis; a 22-year-old with contradictory evidence may begin with rediscovery.

Allow mode switching and career-goal changes. Age must not be used to suppress opportunities, assign ability, or make deterministic predictions.

**Exit gate:** Unit tests cover late joiners, low-data profiles, clear goals, unclear goals, contradictory evidence, and re-entering discovery.

## Stage 4 — Source research, access feasibility, and licence audit

**Goal:** Establish what real data can legitimately be used.

- Inspect the official NCS, NSDC, O*NET, ESCO, and PLFS sources above; confirm source versions and whether downloads/APIs are genuinely accessible in the development environment.
- Choose the smallest high-value subset that can be verified during the build. Prefer an India-first occupational layer from NCS/NSDC, enriched by structured skill/occupation relationships from O*NET/ESCO where useful.
- Verify the precise licence and attribution requirements for the exact data files and tools selected. In particular, do not copy or modify the O*NET Interest Profiler questionnaire unless its applicable licence allows the intended use. If using an instrument verbatim or modifying it, follow the relevant official terms. Do not call a newly created questionnaire “validated” merely because it resembles an established framework.
- Decide whether each source will be integrated via API, official bulk download, small source-backed extract, or link-only reference. Avoid brittle scraping when a permitted route is unavailable.
- Keep source limitations explicit: country differences, different occupation taxonomies, publication lag, discontinued/retired standards, and mismatched skill scales.

**Exit gate:** `docs/DATA_SOURCE_REGISTER.md` records the selected sources, exact access methods, licences/terms, data versions, status, limitations, and reasons for inclusion/exclusion. No source is marked “integrated” unless code or data actually uses it.

## Stage 5 — Provenance model and canonical data contract

**Goal:** Ensure data remains traceable and auditable after normalization.

Design a canonical schema that preserves source identity. At minimum, relevant imported entities should support:

- stable internal ID;
- source ID and source record URI/URL;
- original source title/name/code;
- publisher and geography;
- source version or release date;
- accessed/ingested timestamp;
- licence/terms reference;
- source field values and normalized field values where needed;
- transformation/mapping notes;
- quality status and last verification date;
- source type (official, research, user-provided, heuristic, demo fixture);
- confidence/limitations where appropriate.

Create a `data/sources_manifest.yaml` (or equivalent format appropriate to the existing repository). Do not overwrite original values when mapping them to the internal taxonomy. Preserve mapping lineage so reviewers can see which source supports each occupation, skill, credential, or labour-market statement.

**Exit gate:** A developer can trace each displayed sourced career fact back to its original record/page and version. The UI/API can distinguish sourced facts from inferences and demo values.

## Stage 6 — Data ingestion and normalization

**Goal:** Import real data reliably without pretending unavailable sources are live.

- Implement small, testable adapters/loaders for the chosen sources. Make them safe to rerun and idempotent.
- Add schema validation, duplicate detection, stable ID mapping, encoding handling, retries/rate limiting for APIs, cache/fallback behavior, and clear errors.
- Record the last successful fetch/import and source freshness.
- Keep original source files separate from normalized output where permitted. Do not commit huge raw data dumps or restricted content unnecessarily; document reproducible download instructions instead.
- If network access/keys are unavailable, use an official downloadable or manually curated, source-backed sample only if permitted. Label it **cached snapshot** or **curated extract**, with an access date. Never fabricate a live API response.
- Do not use PLFS aggregate data in individual scoring. It may appear in a separate labour-market context panel with geography/date and interpretation limits.

**Exit gate:** Automated checks validate imported records and provenance. The app degrades gracefully when one or more sources are offline.

## Stage 7 — Career and skill knowledge graph

**Goal:** Relate careers to skills, activities, learning pathways, and source evidence.

Create a lightweight graph or relational representation with entities/relationships such as:

- occupation/career pathway;
- skills and competencies;
- work activities/tasks;
- interests or activity preferences where supported by the source;
- education/qualification pathways and prerequisites where sourced;
- projects/challenges that can demonstrate or develop a skill;
- source records and crosswalks between taxonomies.

Implement a mapping layer between NCS/NSDC terminology and O*NET/ESCO terminology only where a mapping can be supported. Mark uncertain or many-to-many mappings explicitly. Never merge unlike skill scales or assume that similar labels mean identical competencies.

For a hackathon MVP, use a small, diverse, **verified** subset of careers across technical, creative, social/helping, business, analytical, hands-on, and environment-related domains. Every card must cite its supporting sources. Expand coverage only when data quality is maintained.

**Exit gate:** A reviewer can inspect at least two source references for the sampled career/skill facts where independent corroboration is available, and can see unresolved discrepancies rather than concealed assumptions.

## Stage 8 — Student profile and evidence ledger

**Goal:** Represent what the system knows without pretending observations are certainty.

Store evidence items as time-stamped records, not only as a single unexplained score. Distinguish at least:

- stated interest or goal;
- enjoyment/curiosity reported after an activity;
- performance on a specific challenge and its rubric;
- effort/difficulty reported by the user;
- voluntarily added project/portfolio evidence;
- academic/self-reported experience where relevant;
- repeated behavior within SkillScope, with consent and context;
- evidence source, age-appropriate consent status, date, recency, and uncertainty.

Separate **interest**, **current demonstrated performance**, **experience/exposure**, **learning progress**, **goal preference**, and **practical readiness**. A low score on one challenge is not proof of low ability or low interest. Low engagement may indicate task design, context, fatigue, or low prior exposure; do not treat it as a definitive personality trait.

Users must be able to review and correct their stated information. Provide a way to remove evidence/profile history in accordance with the project's data policy.

**Exit gate:** Profile summaries can explain which recent evidence supports each signal. Missing evidence is treated as unknown, not as zero ability.


**Stage 8 implementation checkpoint (2026-10-17):** The current MVP provides typed SQLite profiles/evidence, age-aware consent self-attestations, timestamped initial and changed goals, explicit per-item consent and context for repeated in-product behavior, rubric-specific challenge observations, review/correction/deletion APIs, and deterministic signal summaries (`unknown`, `evidence_available`, `mixed`). No ability/aptitude/career-fit score is produced. Tests cover these invariants (`117 passed` at final Stage 8 verification). The API remains unauthenticated and consent is not identity-verified; the prototype is not safe for public use with real student/minor data. Frontend syntax transpilation passed, but full Vite/typecheck is still unverified because dependencies are not cached and registry access failed. See `docs/STUDENT_EVIDENCE_LEDGER.md` and `docs/PROJECT_STATUS.md`. Stage 9 has not been started pending approval.

## Stage 9 — Baseline assessment engine

**Goal:** Give every entry age a fair, age-appropriate starting point.

- Build a short baseline with plain-language questions and activities mapped to a broad set of domains. Include both self-report and activity-based evidence; do not rely only on marks, a single aptitude quiz, or the user's declared dream career.
- Ensure age-appropriate duration and reading level. Let users skip questions and mark confidence/uncertainty.
- For 10–14, prioritize exploration and curiosity over career matching. For 15–17, establish current hypotheses and missing-exposure areas. For 18+, capture goals, existing proof of work, and target requirements.
- If using a standardized instrument or third-party question set, follow its exact terms/licence and preserve its validated wording/scoring where required. If you create a new item set, label it as an exploratory baseline, not a validated psychometric assessment.
- Provide a visible explanation: “This is an initial snapshot. It will improve as you try activities and share feedback.”

**Exit gate:** New users in each age band receive a meaningfully different baseline and appropriate first recommendation. No result presents a final career verdict.

## Stage 10 — Challenge library and challenge scoring

**Goal:** Turn exploration into practical evidence.

Create short, age-scaled challenges with metadata including domain, skill tags, difficulty, expected duration, materials/accessibility needs, instructions, safety rating, expected output, scoring rubric, reflection prompts, and source/reference when the task content is externally derived.

Include a diverse starting library (for the demo, at least 8–12 solid challenges) spanning several domains such as logic/data, science/research, coding/technology, design/creative work, communication/storytelling, helping/social problem-solving, business/entrepreneurship, hands-on/spatial reasoning, and environment. A challenge may map to more than one skill.

Score only what the rubric observes. Separate objective task result from self-reported enjoyment, challenge difficulty, confidence, and willingness to continue. Add sensible “not enough evidence” outcomes. Do not infer clinical, personality, or sensitive characteristics.

**Exit gate:** Every challenge has a clear output, transparent rubric, age band, and skill mapping. Scores can be explained and reproduced in tests.

## Stage 11 — Daily/regular discovery loop

**Goal:** Implement the longitudinal mechanism that distinguishes SkillScope from a static career quiz.

Use this loop:

`Current profile → choose challenge → complete activity → score visible rubric → reflect → append evidence → update confidence/profile → explain what changed → select next activity.`

The next task should balance:

- developing a demonstrated interest/skill;
- validating an uncertain hypothesis;
- exploring a domain with little exposure;
- testing an alternative pathway if evidence conflicts with the current goal;
- avoiding repetitive challenges that only reinforce one early result.

For the hackathon demo, demonstrate the loop end-to-end with a real interaction and persisted state. Future reminders or push notifications may be documented but must not be represented as implemented unless they genuinely work.

**Exit gate:** Completing a challenge changes the stored evidence and visibly affects the explanation or next recommendation according to deterministic, testable rules.

## Stage 12 — Transparent recommendation and confidence engine

**Goal:** Recommend paths as hypotheses supported by evidence, not deterministic labels.

Create a versioned, documented scoring/matching method combining only signals relevant to a career pathway, such as:

- user-stated interests and goals;
- skill overlap between evidence and sourced career requirements;
- rubric-based challenge evidence;
- repeated observations across different activities;
- experience/portfolio evidence the user voluntarily provides;
- missing skill/experience areas and available learning pathways.

Weights must be configurable and labelled as **initial heuristic parameters**, not scientifically optimized weights. Normalize source measures carefully; do not compare unrelated numeric scales. Track evidence volume, recency, consistency, source quality, and coverage so confidence is not confused with fit. Keep labour-market information as a separate contextual dimension unless a clearly justified use is documented.

Return a useful range of recommendations, for example:

- **Explore:** promising but under-tested;
- **Develop:** aligns with current goals/evidence and has actionable growth steps;
- **Challenge:** a small activity to test an uncertain skill or interest;
- **Alternative to consider:** a plausible adjacent path supported by evidence;
- **Reconsider/refresh:** current evidence conflicts or is too old, so ask the user or run another test rather than silently switching their goal.

Every recommendation must expose: the evidence used, the skill/interest matches, evidence gaps, confidence level and reason, source-backed pathway facts, and the next validating action. Avoid false precision (e.g., “97.43% suitable for doctor”). Do not claim the system has discovered a person's “true” interest.

**Exit gate:** Same inputs and algorithm version produce repeatable output. Tests cover low confidence, contradictory evidence, missing data, and an alternative recommendation.

## Stage 13 — Career pathway and action-plan engine

**Goal:** Convert suggestions into next steps appropriate to the user's stage.

- Ages 10–14: recommend the next small activity, exposure, or project; do not pressure them to pick a career or show a high-stakes ranking.
- Ages 15–17: show a small group of pathways, why each is plausible, what remains unknown, and projects that can validate each option.
- Ages 18+: show a current-state-to-target gap analysis, ordered learning/projects/portfolio actions, and a time-bounded plan (for example, a 30/60/90-day plan only when the necessary inputs are present). Mark prerequisites and credentials with sources.
- Include adjacent/transferable skills and pathways, not only popular high-status careers. Avoid presenting salary/employment guarantees. Any compensation/outlook figure must have geography, date, measure definition, and a trustworthy source; omit it if not verified.
- Let the user edit a goal and recalculate the plan. Career changes should trigger a new discovery/validation loop without erasing historical evidence.

**Exit gate:** Plans contain actionable steps, evidence/requirements, expected outcomes, and a clear way to revise them.

## Stage 14 — User journeys, navigation, and information architecture

**Goal:** Make the product coherent before polishing individual screens.

Define navigation and state transitions for:

1. welcome and age-band entry;
2. consent/guardian-consent and privacy explanation when relevant;
3. entry calibration;
4. baseline assessment;
5. student evidence profile;
6. daily challenge and reflection;
7. career exploration/comparison;
8. pathway roadmap and next steps;
9. source/provenance detail;
10. profile data review/correction/deletion and settings.

Avoid overwhelming the younger users with data-heavy graphs. Provide adult/18+ users with deeper details as relevant. Build empty, first-time, loading, offline-source, error, and conflicting-evidence states. Keep the critical daily loop short enough to be demoed quickly.

**Exit gate:** A user can complete the entire primary journey without dead ends or relying on developer tools.

## Stage 15 — Frontend implementation and visual design

**Goal:** Implement a usable, polished responsive interface consistent with the current repo.

Use a clear hierarchy, readable typography, intentional spacing, strong but restrained visual identity, accessible contrast, and responsive layout. Prefer meaningful data visualizations over decorative boxes. Give the three modes distinct language and task depth without making them feel like separate products.

Required visible surfaces for the MVP:

- age-aware onboarding and entry calibration explanation;
- baseline discovery results with uncertainty;
- profile showing separate signals and evidence count/recency;
- challenge workspace with instructions and reflection;
- career comparison/cards that expose evidence and source references;
- next-step plan tailored to the age mode;
- data/source status and privacy controls.

Every interactive control must work. Do not render static hard-coded charts as if live. If demo examples are included, visibly label the demo profile and the data state.

**Exit gate:** Check all primary screens at desktop and mobile widths, with no major overflow, broken navigation, inaccessible controls, or misleading placeholder content.

## Stage 16 — Backend, persistence, APIs, and integrations

**Goal:** Make core user flows persist and work beyond a static mock-up.

Implement or adapt the backend/API and persistence layer using the existing stack. Store user profile/preferences, evidence history, assessment responses, challenge attempts, recommendations with algorithm version, saved goals/roadmaps, and data-source metadata. Add schema validation, safe error responses, migrations or reproducible database setup, and seeded demo fixtures that are clearly marked as synthetic.

Secure secrets via environment variables; add `.env.example` with dummy variable names only. Never commit keys or personally identifiable test data. External data integrations must have timeout, rate-limit, caching, error, and stale-data behavior. Ensure all recommendation evidence links resolve to internal source records, which in turn point to the original source.

**Exit gate:** Restarting the app does not lose the demo user's saved challenge/evidence state. Main endpoints or server actions are tested, and source failures do not crash core profile/challenge flows.

## Stage 17 — Explainability and source validation UI

**Goal:** Make the system auditable by the student, reviewer, or counsellor.

For each recommended pathway provide an explanation structured around:

- what the user did/said that is relevant;
- which skills/interests the evidence suggests;
- how many distinct observations support it and how recent they are;
- what remains uncertain or has not been tested;
- what occupational/skill sources say about the pathway;
- which fields are local inference versus externally sourced fact;
- which next task would most efficiently validate the hypothesis.

Create a data-source page/panel with publisher, link, source version/date, geography, last sync, status (live/cached/curated/link-only), and known limitations. If two sources disagree, display or log the discrepancy; do not choose one silently. Be candid when an item is based on a heuristic or incomplete data.

**Exit gate:** A demo reviewer can trace at least one recommendation from the student evidence through the matching logic to cited career/skill sources.

## Stage 18 — Privacy, security, fairness, accessibility, and child safety

**Goal:** Make safety a product requirement, not a future note.

- Use privacy by design: collect only fields needed for the feature, prefer age band over full date of birth if sufficient, explain each data use, and provide review/correction/deletion flows.
- For users under 18, include an appropriate consent/guardian-consent workflow and age-appropriate notice. In a hackathon-only prototype, clearly identify it as a demo flow and do not use real children's data. Production requirements must be reviewed against the then-current applicable law, including India's DPDP framework, before release.
- Store no special-category/sensitive inferences, do not infer health, disability, religion, caste, sexuality, political views, or other sensitive traits. Do not use a child's behaviour to label their character or limit their opportunities.
- Do not scrape a student's social media or third-party accounts. Any future integration (e.g., a portfolio or code repository) must be user-initiated, narrowly scoped, consented, and permitted by the provider's terms. The MVP can use manual project links or uploads instead.
- Keep personal records out of application logs. Add authorization checks appropriate to the app, validate inputs, and protect secrets. For external LLM calls, use no personal/minor data by default; make the LLM optional.
- Check accessibility and inclusive language. Recommendations must not rely solely on grades, school prestige, gender stereotypes, location stereotypes, or ability to pay. Distinguish a lack of exposure/opportunity from lack of capability.

**Exit gate:** Add a written privacy/safety checklist in `docs/PRIVACY_AND_SAFETY.md`; test consent gates, deletion behavior, input handling, and major accessibility paths. State clearly what remains unreviewed before production.

**Stage 18 implementation checkpoint (2026-10-17):** Implemented `docs/PRIVACY_AND_SAFETY.md`; added selected-field email/phone/long-number detection without echoing submitted values, request-ID and safe-error handling, privacy-preserving exception logs, restrictive security headers/no-store behavior, explicit HTTPS-only production CORS, and a production-mode fail-closed guard for student-data routes while authenticated identity, per-profile authorization and verified consent remain absent. The profile creation UI shows a conspicuous demo-only notice and explains that guardian consent is self-attested. Deletion cascade, consent basis, input handling, route gating, headers, log redaction and major accessibility source-contract tests were added. `PYTHONPATH=backend pytest -q backend/tests tests` reports **217 passed**. Python compilation, JSON/YAML validation and TSX syntax/CSS checks passed where available. **Not achieved:** no production identity/authorization system or independently verified guardian authority, no legal review against the then-current Indian DPDP framework, no comprehensive DLP, and no dependency-backed frontend build/browser/assistive-technology audit. Use synthetic data only; do not deploy publicly with real student/minor data. Stage 18 is complete within the hackathon demo scope; Stage 19 awaits explicit user approval.

## Stage 19 — Functional, data, and recommendation validation

**Goal:** Test not just whether screens render, but whether data and recommendations behave honestly.

Run available unit, integration, and end-to-end checks. Add test fixtures for at least these scenarios:

1. **Age 10, no history:** broad exploration, no definitive occupation label.
2. **Age 16, says “software engineering,” little evidence:** baseline plus coding and non-coding challenge recommendations.
3. **Age 16, software interest plus strong evidence in communication/design:** retain software as a possibility and propose a design/product alternative to validate, with a transparent explanation.
4. **Age 22, clear target and portfolio:** show gap analysis and practical next actions.
5. **Age 22, unclear goal and conflicting evidence:** start a rediscovery/validation cycle, not a forced choice.
6. **No network/API key:** core loop works from valid cached data and displays the true data status.
7. **Conflicting source record or outdated qualification:** preserve provenance and flag for verification.
8. **Evidence deletion/correction:** remove or recalculate dependent profile/recommendation state appropriately.
9. **Repeated low performance but high enjoyment, and high performance but low enjoyment:** keep skill and interest signals distinct.
10. **Mode change or career change:** history remains traceable; future recommendations use current goals without pretending the past did not happen.

Validate data itself: required fields, record counts, duplicate IDs, stable links, licence metadata, source dates, mapping coverage, and any discrepancies. Cross-source checks must compare like with like. A data-source test does not prove the recommendation engine is psychometrically valid; report these as separate validation categories.

For future real-world evaluation, document a consent-based pilot plan with age-stratified usability/relevance feedback, challenge completion and reflection measures, recommendation explanation usefulness, and fairness checks. Do not claim career outcomes are validated by a hackathon demo.

**Exit gate:** Report exactly which checks passed/failed/skipped and why. Never write “all tests passed” unless that is what actually happened.

## Stage 20 — Demo hardening, documentation, and handoff

**Goal:** Deliver a stable demo and a responsible path beyond the MVP.

- Fix blockers found in the earlier stages; run install, lint, type checks, tests, and production build where the environment supports them.
- Add a clear README with prerequisites, exact setup/run commands, environment variables, database initialization, how to refresh/import each data source, demo credentials only if applicable, and troubleshooting steps.
- Add or update: `docs/PRODUCT_CONTRACT.md`, `docs/DATA_SOURCE_REGISTER.md`, `docs/DECISIONS.md`, `docs/PRIVACY_AND_SAFETY.md`, `docs/VALIDATION_REPORT.md`, `docs/MASTER_BUILD_LOG.md`, and a compact architecture diagram/description.
- Prepare one reliable demo account/fixture per entry mode (10–14, 15–17, 18+) using synthetic demo data clearly labelled as such. Demonstrate age-based mode **and** evidence-based calibration. The demo must show one challenge being completed, the evidence ledger changing, and at least one recommendation/next step changing for an explainable reason.
- Provide a short judging/demo script: problem, differentiator, real source data and provenance, age-aware entry, live evidence loop, transparent recommendation, validation limits, privacy-by-design, and next steps.
- Document production work still needed: approved live integrations, source refresh jobs, fuller data coverage, legal/privacy review, empirical pilot, psychometric validation if making assessment claims, monitoring, deployment security, and scaling.
- Never claim that persistent multi-year tracking, production guardian verification, real-time labour-market coverage, or scientifically proven career prediction is complete unless it really is implemented and verified.

**Final exit gate:** A new developer can set up and run the project from the README; the main demo journey works; source provenance is visible; the build/test status is truthful; and remaining limitations are documented.

---

## Cross-stage acceptance criteria

The build is not complete unless these remain true after Stage 20:

- Joining at age 10, 16, or 22 produces the appropriate different initial experience.
- A 16-year-old with low evidence is not treated like a long-time SkillScope user.
- Age is not the only calibration input; career clarity and evidence quality also affect starting mode.
- Career options remain revisable, and new evidence can strengthen, weaken, or open a hypothesis transparently.
- Interest, performance, experience, exposure, and confidence are represented separately.
- Multiple authentic sources are used where available, with source-level provenance, licence/terms checks, geography, and update dates.
- Aggregate labour-market statistics do not become individual aptitude scores.
- No external source is represented as live when the app is using cached or curated data.
- Every career recommendation includes reasons, uncertainty, evidence gaps, and a next validating action.
- The MVP works without an LLM or a live external API.
- Child privacy, consent, correction, deletion, accessibility, and fairness are treated as product requirements.
- All tests and limitations are reported honestly.

## Recommended hackathon prioritization

If time is limited, protect this end-to-end vertical slice first:

1. Three different age-aware onboarding experiences plus entry calibration.
2. A small, source-backed career/skill knowledge base from multiple authentic sources, with visible provenance.
3. Baseline discovery + a functional challenge + feedback.
4. An evidence ledger and transparent, deterministic recommendation update.
5. Career cards and stage-appropriate next steps.
6. Tests for the three age modes and cold-start cases, followed by responsive UI and demo hardening.

Implement fewer flows completely rather than many screens that only look functional. If a source integration is blocked by access, licence, credentials, or network conditions, use a documented official snapshot or link-only reference and show the limitation; never simulate successful retrieval.

## End of master prompt

Start with Stage 1 now in the empty workspace. Complete only Stage 1, update `docs/MASTER_BUILD_LOG.md`, provide the exact commands/tests and outcomes, list changed files and unresolved blockers, and then stop for user approval. Do not begin Stage 2 until the user explicitly tells you to continue. When approved, repeat the same staged process through Stage 20. Ask for user input only when genuinely blocked by a decision or credential that cannot safely be assumed; otherwise make a documented, reversible choice within the current approved stage. At the end of Stage 20, deliver the working project and a truthful handoff report.


## Final Stage 19–20 execution checkpoint (2026-10-17)

Stages 19 and 20 were executed together at the user's request and are complete within demo scope. See `docs/VALIDATION_REPORT.md`, `docs/ARCHITECTURE.md`, `docs/JUDGING_DEMO_SCRIPT.md`, `docs/PROJECT_STATUS.md`, and `docs/MASTER_BUILD_LOG.md`. Final automated suite at the checkpoint: **234 passed**. A clean isolated database imported 10 curated records/32 facts and rebuilt a non-stale graph (109 nodes/109 edges); the local HTTP walkthrough completed a synthetic challenge, added one evidence item and changed the next task with a reason.

Release boundary: An actual `npm run build` attempt failed because `react`, `vite` and `@vitejs/plugin-react` are absent. The TypeScript node-project config diagnostic found during that attempt was corrected in `frontend/tsconfig.node.json`; dependency-backed TypeScript check, Vite build, browser E2E and screen-reader audit remain unverified. There is no psychometric or career-outcome validation; full O*NET/ESCO data and Indian NCS/NSDC/PLFS feeds are not integrated; production authentication, per-profile authorization, independently verified guardian consent, comprehensive DLP, and qualified legal/security review remain unimplemented. Do not deploy publicly with real student/minor data. Stage 20 is the final documented hackathon handoff, not a production-readiness claim.
