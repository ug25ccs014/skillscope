# Stage 9 — Exploratory Baseline Assessment

Version: `baseline-exploratory-v1.0`

This is an original SkillScope assessment. It is **not a validated psychometric instrument**, does not diagnose ability/personality, and does not produce an aptitude or career-fit score.

## Design

Every new profile receives nine short prompts spanning:

- logic/data
- science/research
- technology
- design/creative
- communication
- helping/social problem-solving
- business
- hands-on/spatial reasoning
- environment

Each item permits skipping. Self-reported confidence is preserved. A skipped or unanswered domain remains `unknown`, never zero.

### Age modes

- **10–14 — Discover & Shape:** curiosity and broad exposure.
- **15–17 — Explore & Validate:** current hypotheses and missing exposure.
- **18+ — Develop & Optimize:** goals and existing evidence provide context; the baseline still remains an exploratory snapshot.

The assessment itself deliberately does not claim that a response demonstrates ability. Evidence created from answers is tagged with the assessment version and domain so later challenges can validate or challenge the initial signal.

## Exit-gate behavior

1. Age bands receive different calibrated modes.
2. The notice explicitly says the snapshot improves with future activities.
3. The student can skip items.
4. No final career verdict is produced.
5. Answers are appended to the Stage 8 evidence ledger as self-report/reflection evidence.
6. The next step explicitly asks for practical activity evidence in both an answered area and an unfamiliar area.

## API

- `POST /api/baseline-assessments/for/{profile_id}` — issue an assessment.
- `POST /api/baseline-assessments/submit` — submit responses and append evidence.

The MVP remains unauthenticated and therefore is not suitable for real student/minor data outside a controlled demo environment.
