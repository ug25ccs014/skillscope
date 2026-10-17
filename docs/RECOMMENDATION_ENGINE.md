# Stage 12 — Transparent recommendation and confidence engine

**Status:** Implemented within the source-linked curated-graph MVP — 2026-10-17.  
**Algorithm version:** `transparent-career-match-v1.0`  
**Domain hypothesis policy:** `career-domain-hypotheses-v1.0`

## Purpose and age-specific behavior

The API proposes testable hypotheses; it does not classify a person or predict career success. At ages 10–14, the service intentionally withholds occupational labels and returns broad, age-appropriate challenge domains ordered by least recorded exposure. At ages 15–17 and 18+, it can return a small, explainable set of source-linked occupation hypotheses when a current career graph is available.

For ages 15+, each item includes:

- a category: `explore`, `develop`, `challenge`, `alternative_to_consider`, or `reconsider_refresh`;
- why it was included, the signals used, and the specific evidence records supporting the explanation;
- a qualitative evidence-confidence label and its volume, recency, consistency, source-quality and coverage breakdown;
- evidence gaps expressed as unrecorded or unverified information, never as inferred deficits;
- work activities drawn from the occupation's source-linked graph nodes, retaining source record/version/geography and quality metadata;
- an age-scaled SkillScope-authored challenge chosen to validate a small part of the hypothesis.

The output does not expose a numerical career-fit score, probability or percentage. The private weighted ordering is only a stable shortlist mechanism.

## Configurable initial parameters

`data/recommendation_weights.json` is the version-controlled weight contract. Its initial parameters are deliberately labelled as not scientifically optimized:

| Component | Base weight | Evidence use |
| --- | ---: | --- |
| Current-goal / occupation-title wording overlap | 25% | Uses shared meaningful words in the goal and source-listed occupation label; wording is not intent validation. |
| Exact source skill-label text overlap | 25% | Requires a source skill label to occur in recorded rubric observations or user-provided evidence text. It does not establish proficiency. |
| Challenge-domain alignment | 25% | Uses challenge evidence in an explicit SkillScope-authored domain hypothesis for a source occupation. It represents exposure, not aptitude. |
| Repeated activity families | 15% | Records whether the same broad domain has been sampled in more than one challenge family; challenge scores from different rubrics are never compared. |
| Voluntary portfolio text overlap | 10% | Surfaces shared terms between voluntarily submitted project evidence and source profile text; it is not a project quality score. |

Only components with usable inputs contribute. Missing components are omitted and the active weights renormalized. A zero lexical overlap is not interpreted as low ability; it only means that this transparent heuristic found no wording overlap to use for ordering.

## Authored domain associations vs sourced facts

`data/career_domain_hypotheses.json` maps exact taxonomy identities to broad challenge domains. Every entry is labelled `skillscope_authored_hypotheses_not_official_taxonomy` and includes a rationale based on the curated work-activity descriptions. This mapping is not an official O*NET or ESCO classification, does not create exact cross-taxonomy equivalence, and does not state a student is capable or incapable in a domain. O*NET and ESCO occupation identities remain separate.

Source-backed task facts are drawn only from attributed graph task nodes. The engine does not invent qualification requirements, salary, labour-market demand, learning prerequisites or India-specific conditions when those facts are absent. It does not use aggregate labour-market data to score an individual.

## Confidence is separate from match ordering

`evidence_confidence` is qualitative (`low`, `moderate`, `high`) and intentionally uncalibrated. It describes the amount, diversity, recency, consistency and provenance of evidence around this hypothesis. It is not confidence that someone will succeed in the occupation.

The high band requires at least six relevant observations, three different challenge families or project/portfolio records, two source kinds or signal dimensions, relevant evidence within 90 days, no unresolved student-labelled conflict and at least one reviewed/verified career source reference. Moderate requires at least three relevant observations, two challenge families, recent evidence, no current contradictory self-report and a reviewed/verified source. Other cases remain low. These are conservative initial rules, not validation results; the exact rule is versioned in the service and tests.

`reconsider_refresh` is used when the student explicitly labels relevant activity as challenging a current hypothesis or when relevant evidence is older than 90 days. The engine explains the conflict and recommends testing/refreshing; it never silently changes the current goal. Positive interpretation/engagement in a domain can surface `alternative_to_consider`, but does not override user choice.

## Data absence and bounded processing

No related activity, no exact skill label, no portfolio, or no qualification record becomes an explicit gap such as “not recorded yet.” It is not treated as zero ability or as a skill gap that the user is presumed to have. Detailed evidence explanations use up to the 200 most recent ledger records for predictable request time; the total record count is still reported, and the response flags when detail was truncated.

## API contract

`GET /api/recommendations/{profile_id}?limit=5` (limit 1–10).

- `404`: profile does not exist.
- `503`: for ages 15+, the occupation graph has not been built / is unavailable. The endpoint refuses to fabricate source-linked career facts.
- `409`: the graph is stale relative to the active source snapshots. Rebuild before requesting new occupation hypotheses.
- ages 10–14 do not require the career graph because their response contains broad domains, not occupations.

To build the bundled curated extract locally, from the project root run:

```bash
PYTHONPATH=backend python -m app.services.ingestion.cli import-curated
PYTHONPATH=backend python -m app.services.knowledge_graph rebuild
PYTHONPATH=backend python -m app.services.knowledge_graph status
```

Those commands use the bundled snapshot; they do not fetch full O*NET or ESCO data.

## Validation

Tests cover configurable policy/version and weight sum, same-state repeatability, no numeric fit field, low confidence with missing evidence, student-labelled contradictory evidence, alternative hypotheses, exact-label overlap explanation, portfolio text use, under-15 broad-domain behavior, stale/missing graph behavior, source citations, and taxonomy identity preservation. These tests verify deterministic software rules; they do not validate the weights as scientifically predictive.

## Known limitations

- The active graph contains ten curated career profiles, not full source databases.
- O*NET records are primarily United States occupational context; ESCO is European classification context. These are not substitutes for India-specific career or qualification advice.
- Full NCS/NSDC occupation standards and qualification pathways are not integrated.
- Source-backed task lists are selected profile extracts, not exhaustive job descriptions or necessarily entry-level requirements.
- Broad domain relationships are SkillScope-authored heuristics, not official taxonomy facts.
- The recommendation API inherits the MVP's missing authentication/authorization and unverified self-attested consent; do not deploy with real student/minor data until production identity, security, consent and privacy controls exist.
- No psychometric validation, outcome calibration, causal learning model, scheduled monitoring or push notification is implemented.
