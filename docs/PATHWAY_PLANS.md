# Career Pathway & Action Plans — Stage 13

**Contract version:** `career-pathway-action-plan-v1.0` (machine-readable policy: `data/pathway_plan_contract.json`)  
**Scope:** Editable, persistent, age-aware action plans generated from the Stage 12 recommendation snapshot, student-controlled planning context, and the active source-linked graph. This is a prototype heuristic, not a validated career-planning instrument.

## API

- `POST /api/pathway-plans/{profile_id}/generate` — generate and persist a plan snapshot. Optional `current_goal` is an explicit goal edit when the property is included in the request. Adult-only planning inputs are accepted only for profiles in the `18_plus` age band.
- `GET /api/pathway-plans/{profile_id}` — read the latest plan snapshot.
- `GET /api/pathway-plans/{profile_id}/history?limit=20` — list prior plan versions and goal-change markers.

A newly supplied goal is written through `EvidenceLedgerRepository.update_profile`, which appends dated stated-goal evidence. Prior evidence is not deleted or rewritten. Each successfully generated plan is saved as an immutable JSON snapshot in `pathway_plans`, with the requested inputs and algorithm version. Profile deletion cascades to saved plan records.

## Age-aware modes

- **10–14, Discover & Shape:** exactly one small next activity, broad domain language, no occupation list or high-stakes career ranking, and no deadline pressure.
- **15–17, Explore & Validate:** up to three source-linked hypotheses with reasons, unknowns, and validation activities/projects. A source-backed alternative is included when the recommendation set provides one. The UI explicitly avoids presenting this as a permanent decision.
- **18+, Develop & Optimize:** up to three hypotheses, source-informed current-state/skill documentation checks, ordered challenge/project/portfolio/review actions, and qualification-source status. The active catalog does not supply a complete verified India-specific credential/admission pathway; the engine says so rather than inventing one.

## Timeline policy

An 18+ plan is time-bounded only when all of the following are available: a stated target, at least one current-state input (skills, education, or experience), weekly time availability, and a requested timeline. Otherwise, the plan remains ordered but untimed and the response lists missing inputs. Thirty/sixty/ninety-day or longer horizons are planning prompts, not forecasts or guarantees. The 10–14 and 15–17 modes do not use deadline-driven plans.

Estimated effort ranges are lightweight planning aids. They are narrowed in response to the user's stated weekly capacity but are not evidence-backed duration predictions. A user can edit inputs and regenerate a new plan.

## Sources, skills, and prerequisites

A career's source-listed work activities are marked `source_backed_work_context` with `is_prerequisite: false`; they are not turned into qualification requirements. Only an explicit, source-linked `requires_qualification` graph relationship can be emitted as a source-backed requirement. If none exists, the plan says the active catalog has no verified formal prerequisite information for the presented pathways.

Source-listed skill labels are compared against self-described context and saved evidence only by complete case-insensitive phrase matching. Results mean `self_reported_in_current_state`, `mentioned_in_evidence`, or `not_yet_documented`. The last status means “not recorded here,” not “the student lacks the skill.” Exact textual mention is not a proficiency score.

The active graph is a curated snapshot of ten occupation identities. Full O*NET/ESCO data, NCS/NSDC, verified India-specific qualification pathways, salary, labour-demand and hiring information remain outside this checkpoint. No salary/employment guarantees are generated.

## Persistence and limitations

`pathway_plans` stores plan snapshots with a profile foreign key and cascade deletion. The database table is initialized additively at service start; no destructive migration is needed for Stage 12 databases. Plan generation is deterministic for the same profile/evidence, request inputs, recommendation policy, graph snapshot, and algorithm version, apart from plan UUID and creation timestamp.

The API remains unauthenticated, and consent is a self-attestation. Do not use the prototype for real student/minor records until identity, authorization, verified consent, deployment hardening, and applicable privacy-law review are implemented.
