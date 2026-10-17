# Stage 8 — Student Profile & Evidence Ledger

**Checkpoint:** Implemented 2026-10-17. This is a transparent evidence store and summary surface, not an aptitude test, personality classifier, diagnostic tool, or recommendation scorer.

## Design rules

1. **Observations stay separate.** Each entry records one self-report, reflection, rubric observation, project/experience note, effort/difficulty note, or explicitly consented in-product behavior event. Records are not collapsed into a permanent, unexplained score.
2. **Unknown is not zero.** A signal with no evidence is returned as `unknown`, with an explanation that the absence is not evidence of low ability, low interest, or low potential.
3. **Signal dimensions are independent.** Interest, demonstrated performance, experience/exposure, learning progress, goal preference, practical readiness, and effort/difficulty are separately represented.
4. **Challenge scores retain their own rubric.** Any numeric rubric score must include its scale. A result on one task is not compared directly with another rubric or converted to overall ability.
5. **Interpretation is labelled as user interpretation.** Optional `supports_current_hypothesis`, `challenges_current_hypothesis`, and `contextual_or_mixed` labels are not model verdicts. Mixed labels keep the signal open rather than forcing a decision.
6. **Self-reported goals are timestamped.** A goal at profile creation is stored as a dated `stated_interest_goal` record. A goal change or removal creates another record; it does not silently overwrite the prior goal event. Crossing the under-18/adult consent boundary with existing evidence requires deleting and recreating the profile, so past evidence cannot be retrospectively relabelled under a different consent regime. The profile field is the current snapshot; the ledger retains the sequence.
7. **Consent is age-aware and explicit.** Ages 10–17 require a recorded guardian-consent confirmation; ages 18+ require the student's confirmation. Each evidence item records the consent basis, consent confirmation timestamp and notice version that applied when captured. Recording in-product behavior additionally requires consent for that specific entry and a non-empty activity and time-window context.
8. **No background monitoring.** Only explicit, contextual `in_product_behavior` records are accepted. This stage does not monitor unrelated apps or devices.
9. **Review, correction and deletion exist.** Profile goals/context and evidence observations can be corrected. An entry can be deleted; all evidence can be cleared while retaining an empty profile; or the profile and all linked evidence can be permanently deleted using the foreign-key cascade. Clearing all evidence also clears the profile’s current goal and self-reported context, leaving only the consent/profile shell.
10. **Minimize data.** No name, birth date, school identifier, file/blob, medical, or other sensitive profile fields are part of this schema. Avoid putting identifying or sensitive details in free-text context.

## Data model

- `student_profiles`: opaque UUID, broad age band, age-appropriate consent basis, consent-confirmed timestamp and notice version, current goal, self-reported context, created and updated timestamps.
- `student_evidence_items`: UUID, profile foreign key, evidence type, signal dimension, title/observation, student-entered domain/context label, source kind/reference, observed/recorded/updated timestamps, uncertainty, optional user interpretation, consent snapshot at capture, optional rubric observations, optional separately reported enjoyment/curiosity/effort/difficulty, and compact JSON context.
- Foreign keys are enabled on every SQLite connection; profile deletion cascades to evidence records.
- Rubric values and student-reported 1–5 ratings are kept as reported. They are not normalized or compared across unrelated measures.
- The summary is deterministic and versioned as `evidence-summary-v1.0`. It reports counts, optional mixed user-labelled evidence, and up to five newest records per dimension. Recency labels mean record age only, not trustworthiness or importance.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `POST` | `/api/student-profiles` | Create a profile after appropriate consent confirmation |
| `GET` | `/api/student-profiles/{profile_id}` | Review the current profile snapshot |
| `PATCH` | `/api/student-profiles/{profile_id}` | Correct current goal/context; correcting age band requires new appropriate consent |
| `GET` | `/api/student-profiles/{profile_id}/evidence` | List, filter, and paginate evidence |
| `POST` | `/api/student-profiles/{profile_id}/evidence` | Add a contextual evidence record |
| `PATCH` | `/api/student-profiles/{profile_id}/evidence/{evidence_id}` | Correct an evidence record; original recorded timestamp is retained |
| `DELETE` | `/api/student-profiles/{profile_id}/evidence/{evidence_id}` | Permanently delete one record |
| `GET` | `/api/student-profiles/{profile_id}/summary` | Explain evidence availability per signal, recent record basis, recency and uncertainty |
| `DELETE` | `/api/student-profiles/{profile_id}/evidence` | Permanently clear evidence while retaining profile shell/consent record |
| `DELETE` | `/api/student-profiles/{profile_id}` | Permanently delete profile and all linked evidence |

## Summary semantics

- `unknown`: no record exists for the dimension. This is not zero and is not a negative evaluation.
- `evidence_available`: at least one record exists; no numeric signal score is generated.
- `mixed`: the user has explicitly labelled at least one item as supporting and one as challenging their current hypothesis. This is a prompt to retain uncertainty, not a model-generated conclusion.
- A record is labelled `recent` for 0–30 days, `developing` for 31–90 days, or `older` after 90 days based on `observed_at`. Older evidence is retained and is not automatically treated as false or deleted.

## Local UI behaviour

`frontend/src/components/EvidenceLedger.tsx` provides profile creation, age-aware consent confirmation, entry creation, rubric-specific challenge results, optional ratings/reflections, record review/correction/deletion, signal summaries, clear-history and profile deletion. The browser retains only an opaque profile UUID in `localStorage` to reopen a profile in this local prototype. The entry does not collect identifying details and the UUID is not authentication.

## Material security limitation

**This unauthenticated API is not safe for real student data or public deployment.** The consent fields record a user's assertion; the system does not verify the identity or authority of the person confirming consent. Before real users—especially minors—are onboarded, implement verified authentication and server-side authorization, secure transport and deployment, consent/assent flows reviewed for the applicable jurisdiction, abuse/rate limiting, operational retention/backup policies, security review and a way to export/correct/delete data under the actual policy. Do not expose the current service publicly with student data.

## Verification

Run from the repository root:

```bash
PYTHONPATH=backend pytest -q
python -m compileall -q backend/app backend/tests
```

The Stage 8 tests cover age-appropriate consent, unknown-vs-zero summaries, per-item consent for repeated behavior, required context, rubric and score-scale validation, goal history, corrections, timezone-aware timestamps, pagination, cross-profile isolation at the record-query level, and permanent deletion/cascades.

**Out of scope:** baseline/questionnaire assessment (Stage 9), challenge library and scoring design (Stage 10), the full longitudinal recommendation loop (Stage 11), identity/authentication, third-party data ingestion of personal records, and any scientifically validated psychometric claims.
