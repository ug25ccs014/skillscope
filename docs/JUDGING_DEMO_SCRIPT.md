# SkillScope AI — 4–5 Minute Judging Demo

**Use synthetic demo fixtures only.** Before presenting, start the API on loopback, open the frontend, confirm `/api/system/persistence` shows three synthetic fixtures, and check that the source registry says the career data is curated/non-live. Do not claim the sources are live or that this prototype is safe for real student data.

## 0:00–0:35 — Problem and differentiator

“Most career guidance asks a student what they want to become. SkillScope helps them discover what they could become. Instead of treating a one-time quiz as a verdict, we collect voluntary activity evidence over time and use it to suggest hypotheses, alternatives and the next small experiment.”

Highlight the three entry modes: 10–14 Discover & Shape, 15–17 Explore & Validate, and 18+ Develop & Optimize. Clarify that age band shapes the initial journey; actual path also responds to goals, experience and evidence quality.

## 0:35–1:15 — Age-aware entry and first-time uncertainty

Show or describe the three clearly labelled synthetic profiles in `GET /api/system/persistence`. Explain that an age-10 profile gets broad domain exploration, not an occupation label. For an age-16 new user, a software goal does not automatically imply skill or commitment: the system starts with baseline/validation, includes non-coding alternatives and labels missing evidence as unknown.

## 1:15–2:20 — Complete one challenge and show the loop

Use the seeded 15–17 fixture. In the Discovery Loop, record the current evidence count and recommended challenge. Open the challenge, submit the activity, and add the reflection/rubric observation. Return to the loop and show that the evidence count increased and the next challenge/reason changed. Point to the evidence ledger: objective rubric observations, enjoyment, difficulty, confidence and willingness to continue are kept distinct.

**Reliable fallback:** from the repository root, use two terminals:

```bash
PYTHONPATH=backend python -m app.services.database init
PYTHONPATH=backend python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal after the API is ready:

```bash
python scripts/demo_walkthrough.py
```

The script uses the synthetic teen fixture, completes one challenge via HTTP, checks ledger growth and the changed next step, then prints a machine-readable result. Run it only against a local demo database. Reinitialize the database before the live presentation to restore the starter state.

## 2:20–3:10 — Explainable recommendations

Show at least one recommendation and expand its trace. Distinguish current-goal overlap, self-reported interest, challenge evidence, sourced occupational work facts, heuristic mapping and uncertainty. Show a design/product alternative for a teen with design/communication evidence while retaining software as a possibility. Do not call the output a score, diagnosis, validated aptitude, or prediction.

## 3:10–3:45 — Provenance and data limits

Open the source registry. Mention that the prototype includes a ten-record curated extract (nine O*NET OnLine pages and one ESCO concept) and preserves source identifiers and uncertainty; the full O*NET/ESCO packages and Indian NCS/NSDC/PLFS datasets are not integrated. The app labels the data curated/non-live, and the source graph does not use aggregate labour statistics to rank an individual.

## 3:45–4:25 — Responsible design and evidence of testing

Show the demo-only privacy warning, correction/deletion controls, source freshness/conflict panels and pathway plan. State: “The API intentionally fails closed for student-data routes in production until authentication, per-profile authorization and verified consent exist.” Report the validated regression count from `docs/VALIDATION_REPORT.md`, and disclose that frontend dependency-backed build/browser testing and independent legal/security review remain outstanding.

## 4:25–5:00 — Roadmap and close

“Next steps are broader licensed source integration, independent usability and fairness evaluation, accessibility and security review, and a consent-based age-stratified pilot. We do not claim scientific career prediction today. The value is a traceable loop: try something, reflect, update evidence, inspect alternatives, and choose the next useful experiment.”

## Before judging: rehearsal checklist

- [ ] Restore deterministic synthetic starter state with database init.
- [ ] Confirm all three age-mode fixtures are visible and marked synthetic.
- [ ] Complete the live challenge loop once; ensure evidence count and next step change.
- [ ] Expand a recommendation explanation and one source reference.
- [ ] Show curated/non-live source status and privacy boundary.
- [ ] Keep `docs/VALIDATION_REPORT.md` open for exact passed and unverified checks.
