# Stage 10 — Challenge Library & Challenge Scoring

Status: **complete within MVP scope — 2026-10-17**.

## Purpose

Stage 10 turns exploration into practical, inspectable evidence. The library is deliberately authored by SkillScope rather than copied from a standardized psychometric instrument. It is therefore **exploratory content, not a validated assessment**.

## Library

The initial library contains **12 challenge families / 36 age-scaled variants** covering all nine target domains:

- logic & data: Pattern Detective; Data Story
- science & research: Mini Investigation
- technology: Debug the Process; Map a Routine
- design & creative: Redesign It; Idea to Prototype
- communication: Three-Minute Story
- helping/social: Help Without Guessing
- business/entrepreneurship: Tiny Business Test
- hands-on/spatial: Build a Paper Bridge
- environment: Local Eco Audit

Each family has one variant for 10–14, 15–17 and 18+. Age scaling changes framing, complexity, expected output and/or evidence expectations rather than merely changing the label.

## Challenge contract

Every challenge records:

- stable challenge ID and content version
- broad domain and one or more skill tags
- difficulty and safety rating
- content origin (`skillscope_authored`)
- optional source reference (all Stage 10 seed content is original, so it is null)
- an observable rubric with criterion IDs, descriptions and an explicit 0–2 scale
- age-specific instructions, duration, materials, accessibility notes, expected output and reflection prompts

No challenge claims psychometric validation or career-fit validity.

## Scoring model

Only rubric observations receive objective scores. The scorer:

1. validates the exact challenge and age-specific variant;
2. accepts only known rubric criterion IDs;
3. rejects duplicate criteria and scores outside the criterion's scale;
4. counts only criteria with an observed numeric score;
5. returns a reproducible objective score as the sum of observed criterion scores and the corresponding observed maximum;
6. returns `not_enough_evidence` when no rubric criterion is observed;
7. returns `partial_evidence` when some evidence is observed but the age variant's minimum criterion count is not met;
8. returns `evidence_available` once the minimum observed criterion count is met.

Scores are **challenge-local observations**. They are not normalized across challenges and are not aptitude, personality, clinical, or career-fit scores.

Reflection fields — enjoyment, reported difficulty, confidence, willingness to continue and free-text reflection — are stored separately from the objective result. They do not change the rubric score. Student confidence is retained as confidence context and is not mislabeled as curiosity.

## Evidence ledger integration

A completed submission creates one Stage 8 `challenge_performance` evidence item with:

- challenge label/version
- criterion-level rubric observations
- objective evidence status and challenge-local score (when sufficient)
- reflection fields kept as self-report/context
- challenge ID and age band

The evidence item is written in the same SQLite transaction as the submission. Failed validation therefore does not create a partial challenge record. The student's selected interpretation (`supports`, `challenges`, `mixed/context-dependent`, or `not interpreted`) is retained separately from the rubric observations and is used by Stage 11 only as a self-reported signal.

## Safety and evidence boundaries

- No clinical, personality, sensitive-trait, or hidden-monitoring inference.
- No background device/platform tracking.
- No real-money transaction is required for business challenges.
- Hands-on activities use ordinary low-risk materials; virtual/sketch alternatives are supplied where useful.
- Environment tasks avoid precise location collection and restricted-area activity.
- `not_enough_evidence` is an explicit outcome; missing observations are not converted to zero.
- The app records what a rubric observed; later stages may use it as one evidence item, not as a verdict.

## API

- `GET /api/challenges?age_band=15_17&domain=technology`
- `GET /api/challenges/{challenge_id}`
- `POST /api/challenges/{challenge_id}/submissions`

The submission response explains the exact observed criteria, objective score/max when available, evidence status, and evidence-ledger record ID. Stage 11 consumes the persisted submission and exposes an explainable next activity through `GET /api/discovery-loop/{profile_id}?preference=balanced` (see `docs/DISCOVERY_LOOP.md`).

## Current limitations

The API remains unauthenticated, matching the Stage 8 prototype boundary. Do not expose real minor/student records publicly until identity, authorization and production consent controls exist. The challenge content has not been psychometrically validated. The current scoring is a transparent rubric mechanism, not a scientific measurement of ability.
