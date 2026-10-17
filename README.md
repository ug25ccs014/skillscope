# SkillScope AI

**Discover what you could become.** SkillScope is a career discovery and development companion that uses a person's stated interests, voluntary activities, challenge evidence, projects/experience, goals, and attributable career/skills sources to propose testable possibilities and practical next steps. Recommendations are hypotheses, not career verdicts.

> **Current checkpoint: Stages 19–20 complete (functional/data validation and demo handoff).** Stages 8–20 now include the consent-aware evidence ledger, age-scaled baseline/challenges, explainable career hypotheses and pathway plans, connected user journeys, responsive design, persistent APIs, source validation UI, and the Stage 18 privacy/security guardrails. Student-data endpoints fail closed in production until authentication, per-profile authorization, and verified consent are implemented. Free-text validation rejects obvious direct identifiers in selected fields, validation errors omit submitted values, logs avoid request contents, private responses are no-store, security headers are set, and production CORS requires explicit HTTPS origins. The project is still a hackathon prototype: do not enter real student/child data. No legal review against current Indian DPDP rules has been performed; full O*NET/ESCO and NCS/NSDC datasets remain unintegrated. The current backend regression suite reports 234 passed. Fresh SQLite initialization, import of the bundled curated snapshot, graph rebuild (109 nodes/109 relationships), graph freshness, and the synthetic HTTP demo walkthrough have been exercised. Frontend TSX/CSS static checks pass where available, but dependency-backed TypeScript typecheck, Vite production build and browser/screen-reader E2E checks remain unverified because project npm dependencies are unavailable in this environment.

## Architecture

- `frontend/` — React + TypeScript + Vite + Tailwind CSS.
- `backend/` — FastAPI service; health endpoints `/api/health` and `/health`, stateless `POST /api/calibration`, provenance/ingestion/knowledge-graph APIs, and consent-aware `/api/student-profiles` evidence-ledger APIs.
- `data/` — source manifest, curated occupation snapshot, ingestion run ledger and generated SQLite registry. The small curated snapshot is static/source-linked; no full external career dataset is marked integrated.
- `docs/` — product contract, architecture decisions, build log, status, and master prompt.
- `tests/` — cross-component/integration test planning.

SQLite is the implemented MVP persistence target, with environment-backed file path configuration, checksum-tracked additive migrations and reproducible initialization/status commands. Moving to managed PostgreSQL would require an explicit repository/transaction migration.

## Requirements

- Node.js 22+ and npm 10+
- Python 3.11+
- Git

## Run the backend

From the repository root:

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r backend/requirements.txt
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

API endpoints:

- `http://127.0.0.1:8000/health` — infrastructure health check.
- `http://127.0.0.1:8000/api/health` — API health check.
- `POST http://127.0.0.1:8000/api/calibration` — age-aware entry calibration (stateless; no profile is saved).
- `POST /api/student-profiles` — create a pseudonymous profile after age-appropriate consent confirmation.
- `GET/PATCH /api/student-profiles/{profile_id}` — review or correct profile fields; an age-band correction requires renewed appropriate consent.
- `GET/POST /api/student-profiles/{profile_id}/evidence` — list or add timestamped observations.
- `PATCH/DELETE /api/student-profiles/{profile_id}/evidence/{evidence_id}` — correct or permanently delete an observation.
- `GET /api/student-profiles/{profile_id}/summary` — explain evidence coverage per signal without producing an ability score.
- `DELETE /api/student-profiles/{profile_id}/evidence` or `/api/student-profiles/{profile_id}` — permanently clear evidence or delete the whole profile and history.
- `GET http://127.0.0.1:8000/api/ingestion/status` — source import status and active snapshot metadata.
- `GET http://127.0.0.1:8000/api/provenance/status` — provenance registry counts and external integration status.
- `GET http://127.0.0.1:8000/api/knowledge-graph/status` — career graph counts, active snapshot and freshness.
- `GET http://127.0.0.1:8000/api/knowledge-graph/careers` — source-cited career cards with selected tasks and occupation-scoped skill references.
- `GET http://127.0.0.1:8000/api/knowledge-graph/crosswalks` — reviewed-related and unresolved cross-taxonomy mappings.
- `GET /api/student-profiles/{profile_id}/preferences` and `PUT /api/student-profiles/{profile_id}/preferences` — read/write durable journey and accessibility preferences.
- `GET /api/recommendations/{profile_id}/history?limit=20` — saved recommendation snapshots including algorithm version, evidence count, and internal source keys.
- `GET /api/system/persistence` — schema version and synthetic-fixture status without exposing the database path.

- `GET /api/challenges?age_band=15_17&domain=technology` — list age-scaled challenge variants.
- `GET /api/challenges/{challenge_id}` — inspect a challenge family, all age variants and its observable rubric.
- `POST /api/challenges/{challenge_id}/submissions` — score a submitted output against the exact rubric and append challenge-performance evidence in the same transaction.
- `GET /api/discovery-loop/{profile_id}?preference=balanced` — calculate the next age-scaled challenge from persisted submissions/evidence; preferences are `balanced`, `explore`, `develop`, `validate`, or `alternative`.
- `GET /api/recommendations/{profile_id}?limit=5` — return source-traceable career hypotheses for ages 15+ or broad exploration domains for ages 10–14, with matching reasons, confidence breakdown, evidence gaps, cited occupational task facts, and a next validating challenge. Adult/teen recommendations require a current built career graph; no career facts are fabricated when it is absent or stale.
- `POST /api/pathway-plans/{profile_id}/generate` — create and persist an age-aware pathway plan; submitting a changed `current_goal` records goal history and recalculates without deleting prior evidence.
- `GET /api/pathway-plans/{profile_id}` — read the latest saved plan snapshot.
- `GET /api/pathway-plans/{profile_id}/history?limit=20` — inspect prior saved plans and goal-change markers.
- `POST /api/baseline-assessments/for/{profile_id}` and `POST /api/baseline-assessments/submit` — issue and submit an exploratory nine-domain baseline from the Baseline section.
- The primary journey navigation connects `#top`, `#evidence-ledger`, `#baseline-assessment`, `#discovery-loop`, `#career-recommendations`, `#pathway-planner`, `#career-knowledge`, and `#profile-settings`; see `docs/USER_JOURNEYS.md`.
- `http://127.0.0.1:8000/docs` — local OpenAPI documentation.

See `docs/ENTRY_CALIBRATION.md` for Stage 3 calibration, `docs/STUDENT_EVIDENCE_LEDGER.md` for the Stage 8 evidence model, `docs/RECOMMENDATION_ENGINE.md` for Stage 12 matching rules, `docs/PATHWAY_PLANS.md` for Stage 13 action-plan persistence, `docs/USER_JOURNEYS.md` for Stage 14 navigation, `docs/VISUAL_DESIGN_SYSTEM.md` and `docs/STAGE15_VISUAL_AUDIT.md` for Stage 15, and `docs/STAGE16_PERSISTENCE_AND_INTEGRATIONS.md` for database/bootstrap/cache behavior.

## Run the repeatable demo

Start from the repository root. The local database initialization creates three labelled synthetic profiles (ages 10–14, 15–17, and 18+); it is safe to re-run for schema setup, but a completed challenge remains in the database. Do not enter real student or child data.

Terminal 1:

```bash
PYTHONPATH=backend python -m app.services.database init
PYTHONPATH=backend python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2, after the API starts:

```bash
python scripts/demo_walkthrough.py
```

The walkthrough uses the 15–17 synthetic fixture, submits a challenge through the HTTP API, verifies that evidence count increases and checks that the next challenge changes with a reason. It refuses non-loopback addresses by default. For a clean judging rehearsal, stop the API, remove only your local demo database (the default is `data/skillscope.db`, excluded from the archive), initialize it again, then restart. The script never claims an external network integration is live. See `docs/JUDGING_DEMO_SCRIPT.md`.

## Source data: what is and is not integrated

The shipped snapshot contains **10 curated occupation records** (nine O*NET OnLine profile extracts and one ESCO occupation concept). It is static and source-linked, not the full O*NET database, not the full ESCO classification package, and not a live API. NCS India, NSDC India and PLFS are reference/link-only or not integrated. To reproduce the bundled graph without network access:

```bash
PYTHONPATH=backend python -m app.services.ingestion.cli import-curated
PYTHONPATH=backend python -m app.services.knowledge_graph rebuild
PYTHONPATH=backend python -m app.services.knowledge_graph status
```

Official O*NET downloads are allow-listed and recorded with version/checksum metadata; use `PYTHONPATH=backend python -m app.services.ingestion.cli download-onet --help` and import only verified matching files using `import-onet --help`. ESCO import expects the exact officially selected package and pinned version (`import-esco --help`). Do not change a source to “integrated” merely because its URL is listed or a download attempt ran. The current default active graph was rebuilt locally from the curated extract; `source_data_is_live` remains `false`.

## Troubleshooting

- **`ModuleNotFoundError` for backend imports:** run commands from the repository root and set `PYTHONPATH=backend` (on Windows PowerShell: `$env:PYTHONPATH = "backend"`).
- **SQLite migration/locking issue:** stop duplicate demo servers, check `SKILLSCOPE_DATABASE_PATH` / `SKILLSCOPE_DATABASE_URL`, then inspect with `PYTHONPATH=backend python -m app.services.database status`. Do not copy the project DB into a public archive.
- **Frontend `npm install`/build unavailable:** confirm Node 22+ and npm 10+. Retry when npm registry access works; a successful TypeScript syntax transpilation is not a full typecheck or production build. Do not report a production build as passed until `npm run build` succeeds.
- **Core loop does not require LLM credentials:** no LLM API key is needed for the deterministic local discovery/recommendation loop.
- **Unexpected source status:** inspect `GET /api/ingestion/status`, `GET /api/provenance/status`, `GET /api/knowledge-graph/status`, and `GET /api/source-registry`. Keep outdated, missing or conflicted sources visibly flagged.

## Run the frontend

In a second terminal:

```bash
cd frontend
# Optional: copy .env.example to .env.local and customize VITE_API_BASE_URL
npm install
npm run dev
```

Open the Vite URL displayed by the terminal (normally `http://localhost:5173`). Run `npm run build` for the production build.

## Initialize and inspect persistent storage

From the repository root, the app initializes its SQLite schema during startup. You can also run migrations and inspect the status explicitly:

```bash
PYTHONPATH=backend python -m app.services.database init
PYTHONPATH=backend python -m app.services.database status
# Optional isolated database; excludes the synthetic demo fixture:
PYTHONPATH=backend python -m app.services.database init --db /tmp/skillscope-local.db --no-demo
```

`SKILLSCOPE_DATABASE_URL` is a file-backed SQLite URL; relative paths resolve from the project root. In development the synthetic demo fixture is enabled by default. `SKILLSCOPE_ENV=production` turns automatic demo seeding off unless it is explicitly enabled. Override `SKILLSCOPE_SEED_DEMO=false` to disable demo seeding. Source downloads use `SKILLSCOPE_SOURCE_CACHE_TTL_SECONDS` (default one day, `0` disables cache reuse). Cache hits require a valid checksum, matching source/version metadata, retrieval timestamp, and CSV header. Failed refreshes keep the last known file but record a refresh failure; do not mistake a retained old file for fresh data.

## Initialize the local career graph

The generated SQLite database is intentionally not bundled in the ZIP. After installing backend dependencies, run these from the repository root to rebuild the local registry and graph from the bundled snapshot. These commands do not access the network:

```bash
PYTHONPATH=backend python -m app.services.ingestion.cli import-curated
PYTHONPATH=backend python -m app.services.knowledge_graph rebuild
PYTHONPATH=backend python -m app.services.knowledge_graph status
```

## Tests

From the repository root:

```bash
PYTHONPATH=backend pytest -q
python -m compileall -q backend/app backend/tests
```

## Product contract and implementation status

Read `docs/PRODUCT_CONTRACT.md` for personas, the end-to-end MVP journey, scope boundaries, acceptance criteria, privacy constraints and known assumptions. Read `docs/ENTRY_CALIBRATION.md` for Stage 3 calibration, `docs/INGESTION_PIPELINE.md` for source acquisition/normalization, and `docs/KNOWLEDGE_GRAPH.md` for graph semantics, API, source identity and mapping limits. `docs/ATTRIBUTIONS.md` records source acknowledgements and adaptations. `docs/MASTER_BUILD_LOG.md` and `docs/PROJECT_STATUS.md` track stage progress and known limitations. See `docs/PRIVACY_AND_SAFETY.md` for safeguards and mandatory production release gates, `docs/ARCHITECTURE.md` for the architecture/data flow, `docs/VALIDATION_REPORT.md` for exact passed and unverified checks plus a future pilot plan, and `docs/JUDGING_DEMO_SCRIPT.md` for the rehearsed walkthrough.

## Development sequence

The product was implemented in 20 sequential stages. Stages 1–20 are complete within their documented prototype and environment boundaries. Check `docs/PROJECT_STATUS.md`, `docs/MASTER_BUILD_LOG.md`, and `docs/VALIDATION_REPORT.md` for what was actually verified and what remains open.

## Data integrity rule

Career facts and skills must eventually carry source, URL/record identifier, publisher, version/as-of date, retrieval date, licence/terms, geographic scope, integration method, and limitations. Occupational facts, aggregate labour-market context, and individual evidence must remain distinct. A source is not “integrated” merely because its URL is listed or a URL/checksum sidecar is present. A downloaded source artifact's origin is not cryptographically attested by the importer. Stage 3 uses deterministic, documented heuristics only; it does not persist a profile. Stage 8 persists student-selected records in SQLite, but its API has no authentication/authorization and its consent fields are self-attestations. This MVP is not safe for public deployment with real student or minor data. Add verified identity, authorization, deployment security and consent verification before production use.
