# Stage 3 — Age Modes and Entry Calibration

**Rule version:** `1.0.0`
**Status:** Implemented as deterministic MVP heuristic; tests passed.
**Endpoint:** `POST /api/calibration`
**Persistence:** None. This endpoint calibrates one submitted request and does not create or save a student profile.

## Product rule

Age determines the age-appropriate activity style, not aptitude, a ceiling on opportunity, or a final career destination. The system keeps the cohort experience (`age_mode`) separate from the more flexible starting strategy (`starting_path`). An adult can re-enter exploration, a teenager can validate a stated interest, and a younger student stays in broad age-appropriate exploration even if an adult-style optimization journey is requested.

## Age modes

| Age | API age band | Mode label | Typical activity style |
|---|---|---|---|
| 10–14 | `10-14` | Discover & Shape | Short, varied, low-stakes activities across domains; no definitive career labels. |
| 15–17 | `15-17` | Explore & Validate | Establish a baseline, test stated interests, compare unfamiliar domains, and revisit changing goals. |
| 18+ | `18+` | Develop & Optimize | Career discovery, goal validation, or evidence-backed gap review and planning. |

The request accepts completed age in years. It does not require a full date of birth. Ages below 10 or above 100 are rejected by schema validation.

## Inputs

| Field | Meaning | Important limit |
|---|---|---|
| `age` | Age in completed years | Selects the age band; does not directly rate ability. |
| `career_clarity` | Self-described low/medium/high clarity | Not an assessment result. |
| `prior_evidence_count` | Self-reported number of prior activities/projects/records | Count alone does not indicate skill or talent. If the count is unknown, enter 0 and provide an activity summary if useful. |
| `prior_activity_summary` | Optional short summary of what the user has tried | If the numeric count is zero but this summary is present, it is treated as one unquantified self-reported context item for coverage only. The text is not echoed verbatim in the rationale or independently verified. |
| `prior_evidence_quality` | Self-described quality/variety | Explicitly self-reported, not independently verified. |
| `prior_projects_experience` | None/some/substantial | A qualitative input, not a credential check. |
| `exploration_need` | Self-described need to explore | High need broadens exploration in automatic adult/teen paths where a current direction exists. |
| `current_goal` | Optional current career/domain direction | A hypothesis to test, not a permanent label. Whitespace is normalized; blank text becomes `null`. |
| `unexplored_domains` | Areas the user says they have had little chance to try | One or more of 10 domains. Lack of exposure is explicitly not treated as weakness; in automatic teen entry, a stated goal plus unexplored domains can trigger broader exploration. |
| `education_summary` | Optional adult education/training context | Bounded and used only within this request. |
| `skills_summary` | Optional adult self-described skills | Bounded; not independently verified. |
| `experience_summary` | Optional adult project/work/volunteering/portfolio context | Bounded; not independently verified. |
| `planning_constraints` | Optional adult constraints the user chooses to disclose | Bounded, not echoed verbatim in the rationale, and not treated as career suitability signals. Avoid sensitive data. |
| `desired_timeline` | Optional planning horizon | `unspecified`, `under_3_months`, `3_to_6_months`, `6_to_12_months`, or `over_12_months`. It shapes planning horizon, not career worth. |
| `contradictory_evidence` | User reports conflicting signals | Causes broader exploration rather than automatic narrowing for ages 15+. |
| `career_goal_changed` | User says the direction changed recently | Avoids assuming evidence for the former goal fully supports the new one. |
| `reenter_discovery` | User explicitly requests a fresh exploration cycle | Honored within age-appropriate mode. |
| `journey_preference` | `automatic`, `explore`, `validate`, or `optimize` | A preference, not an override of age-appropriate content. |

Unknown and absent information must remain unknown. In particular, zero prior evidence must never be interpreted as low ability.

## Evidence-coverage heuristic

`evidence_strength` describes the **coverage of reported supporting information**, not the strength of a student, measured aptitude, or probability of success.

| Condition | Output |
|---|---|
| `prior_evidence_count == 0` and no activity summary | `none` |
| Count is 0 with a non-empty activity summary, count is 1–2, or quality is `unknown`/`low` | `limited` |
| Count is 3–5 with medium/high quality, or count is 6+ with medium quality | `emerging` |
| Count is 6+ and quality is `high` | `substantial` |

These are explicit convenience thresholds for the MVP. They are not empirically validated and must be revisited if evidence suggests they are confusing or misleading.

## Starting-path rules and precedence

The implementation uses explicit condition branches—not an LLM score—to return one reversible strategy.

### Ages 10–14

Always use `guided_exploration` under `discover_and_shape`. Adult-style validation or optimization preferences are translated into broad, age-appropriate activities. This keeps career labels from narrowing exploration too early.

### Ages 15–17

Precedence:

1. Explicit re-entry request or `journey_preference=explore` → `reenter_discovery`.
2. Goal changed and conflicting signals reported → `broaden_exploration`.
3. Goal changed → `baseline_discovery`.
4. Contradictory signals → `broaden_exploration`.
5. Explicit optimize/validate preference → validate a clear stated direction, or baseline discovery if there is no usable direction.
6. Low clarity or no current goal → `baseline_discovery`.
7. Automatic preference + a stated direction + one or more user-named unexplored domains → `broaden_exploration`.
8. Automatic preference + a stated direction + high exploration need → `broaden_exploration`.
9. High clarity + a stated direction → `validate_declared_interest`.
10. Otherwise → `baseline_discovery`.

### Ages 18+

Precedence:

1. Explicit `reenter_discovery` → `reenter_discovery`.
2. `journey_preference=explore` → `career_discovery`.
3. Goal changed and conflicting signals reported → `career_discovery`.
4. Goal changed → `career_goal_validation` when a current direction and at least medium clarity are present; otherwise `career_discovery`.
5. Contradictory signals → `career_discovery`.
6. Explicit validate preference → `career_goal_validation` when a direction and at least medium clarity are present; otherwise `career_discovery`.
7. Explicit optimize preference → `career_gap_analysis` only if gap-analysis conditions below hold; otherwise validate or discover.
8. Automatic preference + high exploration need, low clarity, or no goal → `career_discovery`.
9. Automatic preference + gap-analysis conditions → `career_gap_analysis`.
10. Otherwise → `career_goal_validation`.

`career_gap_analysis` requires all of the following: high career clarity, a stated current goal, evidence coverage `substantial`, self-reported project/experience level `substantial`, at least one adult skills or project/work experience summary (education alone does not establish a practical skill baseline), no reported contradictions, and no reported recent goal change. A user with a strong evidence count but no current skills or project/work context remains in goal validation rather than implying that a detailed gap analysis is ready. Education/training and the desired timeline can inform later planning, but education alone does not establish a practical skill baseline. These conditions only qualify a user to start by comparing evidence with role requirements; they do not prove that the target role is ideal.

The path name `reenter_discovery` is used for an explicitly selected fresh cycle in the teen/adult modes even though this stateless Stage 3 endpoint cannot verify whether a saved prior profile exists. The UI tells users no profile is saved yet.

## Response contract

The response includes:

- `age_band`, `age_mode`, and a human-readable age-mode label;
- `starting_path` plus its label;
- `evidence_strength` and its coverage label;
- input-specific `rationale` statements;
- a concrete suggested `next_step`;
- `considered_inputs` for transparency;
- explicit `limitations` and the `calibration_version`.

No numerical aptitude score, probability, ranked career list, or scientifically validated assessment result is returned.

## Example API request

```json
{
  "age": 16,
  "career_clarity": "low",
  "prior_evidence_count": 0,
  "prior_evidence_quality": "unknown",
  "prior_projects_experience": "none",
  "exploration_need": "high",
  "current_goal": null,
  "contradictory_evidence": false,
  "career_goal_changed": false,
  "reenter_discovery": false,
  "journey_preference": "automatic"
}
```

Expected decision: `age_mode=explore_and_validate`, `starting_path=baseline_discovery`, and `evidence_strength=none`. The rationale states that the missing evidence is unknown rather than negative evidence about ability. The rule set intentionally begins with baseline discovery instead of assuming a career direction.

## Validation and privacy constraints

- Pydantic request schemas reject out-of-range ages, negative counts, and unexpected fields.
- User-entered goal text is trimmed and bounded to 180 characters.
- The API does not persist the supplied fields. No full date of birth, address, or unrelated personal information is requested.
- User-specific fields are not sent to an external LLM or career provider in this stage.
- The result is advisory, reversible, and explicitly described as a heuristic. It must not be represented as a validated career or psychometric diagnosis.

## Stage 3 acceptance checks

- Age boundaries 10, 14, 15, 17, 18, and 100 map to disjoint expected bands/modes.
- Tests cover no prior evidence, late entry, clear and unclear goals, activities tried, contradictory signals, changed goals, explicit route preferences, re-entry, unexplored domains, adult planning context, and invalid request inputs.
- `POST /api/calibration` returns the versioned explainable response contract.
- Frontend form can submit the user-selected inputs and display the returned mode, path, evidence coverage, rationale, next step, and limitations.
- Frontend dependency installation/build remains an environment-dependent check; see `docs/PROJECT_STATUS.md`.
