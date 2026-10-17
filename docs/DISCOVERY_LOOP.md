# Stage 11 — Daily/regular discovery loop

**Status:** Complete within the request-driven prototype scope — 2026-10-17.  
**Policy version:** `discovery-loop-v1.0`.

## What is implemented

The loop connects the persisted profile, challenge library, rubric scorer, reflection capture, evidence ledger and next-task selection:

`Profile + saved history → age-appropriate next challenge → completed output → visible rubric → self-reflection → atomic submission/evidence write → updated exposure/history → explained next task.`

The React `DiscoveryLoop` panel supports consent-confirmed pseudonymous profile setup, age-appropriate challenge instructions, output capture, criterion-level score/observation entry, optional enjoyment/difficulty/confidence/willingness self-reports, a student-led interpretation of whether the activity supported/challenged/complicated a current hypothesis, and a free-text reflection. After a confirmed submission, the panel loads the updated loop state. The evidence ledger and challenge history use the same profile UUID in local storage so a profile can be resumed from the same browser.

The API is `GET /api/discovery-loop/{profile_id}` with optional `preference`:

- `balanced` — default; explore broadly unless a student's latest explicit interpretation indicates validation, conflict or positive engagement.
- `explore` — prioritize domains with low recorded exposure.
- `develop` — follow an explicitly positive-engagement signal when one exists; otherwise explore rather than guess.
- `validate` — seek a different challenge in the most recently tested domain when available; mixed/contextual reports make this priority explicit.
- `alternative` — try a less-exposed domain away from the most recent one where the library permits.

Response includes the current age mode, the selected age-specific variant, domain exposure counts (unseen is `unknown`, not zero ability), the last completion summary, a reason code, written rationale, next step, policy version and limitations. Lifetime domain exposure and used-challenge coverage are calculated through SQLite aggregates; narrative/engagement selection uses a bounded recent history window. The next task is derived from persisted submissions/evidence on each request, with no randomness or unlabelled composite score.

## Deterministic selection rules

1. Use the profile's recorded age band to select exactly one challenge variant.
2. Prefer challenge families the student has never tried. Once the finite library is exhausted, avoid the three most recent task families where possible.
3. If the student explicitly says the last activity challenged their current hypothesis, test a different domain; do not declare the current goal wrong.
4. If the student explicitly describes a result as mixed/context-dependent or requests validation, try a different task in the same domain when available; otherwise broaden exposure.
5. If the student explicitly supports the hypothesis or reports positive enjoyment/willingness, offer a different activity in that domain when the library has one available. This is a reason to explore further, not a finding about ability.
6. Explicit preference is followed only when there is enough relevant history to support it; a request to develop without any engagement evidence falls back to broader exploration.
7. For otherwise equal candidates, stable challenge-library order is the tie-breaker. Same profile state + policy version + preference gives the same recommendation.

Rubric totals are never used to compare different challenge families. Self-report values are stored separately from task performance. A missing/unobserved criterion remains unknown. The free-text goal is displayed as context but is not keyword-mapped to a career/domain by this stage.

## API and persistence

- `GET /api/discovery-loop/{profile_id}?preference=balanced`
- Existing `POST /api/challenges/{challenge_id}/submissions` persists the completed output, rubric results, reflection, explicit interpretation and evidence record in one SQLite transaction.
- `challenge_submissions.user_interpretation` is added with a safe additive migration for a Stage 10 database created before Stage 11.
- Every challenge submission appends a Stage 8 evidence item carrying the challenge domain, version, rubric observations, status, interpretation, and self-report context.
- `challenge_submissions` and `student_evidence_items` cascade with profile deletion.

## Verification and limitations

Automated tests cover the first task, age mode, domain exposure, persisted submission/evidence counts, deterministic repeat GETs, supported-path development, mixed-result validation, student-reported conflict, explicit alternatives, not-enough-evidence semantics, nonexistent profiles, and the Stage 10→11 additive SQLite migration.

The app does not schedule notifications or perform background monitoring. The UI preference is saved locally in this browser and sent with the API request; the API default remains `balanced`. Saved evidence history is persistent, but reminders and a notification scheduler are not implemented. The API is still unauthenticated and consent confirmation is a self-attestation, not verified guardian authority. Do not deploy with real minors' or students' data before identity, authorization, secure consent verification and production privacy/security controls are implemented. The challenge library and selection policy are exploratory heuristics, not psychometrically validated instruments or scientifically optimized recommendations.
