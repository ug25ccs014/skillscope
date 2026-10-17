# Stage 5 — Provenance Model & Canonical Data Contract

## Purpose

Stage 5 establishes the auditable data layer required before external career/skill data is imported. It does **not** import external datasets.

The design preserves the distinction between:

- facts copied or referenced from an external source;
- normalized values created by SkillScope;
- cross-source mappings;
- user-provided evidence;
- heuristics;
- synthetic/demo fixtures.

This distinction is mandatory because the Stage 4 source register states that a research-page view does not prove runtime integration, and because cross-source differences may reflect geography, taxonomy granularity, publication timing, or licensing constraints.

## Canonical chain

```text
SourceRecord
    │
    └── source_id + source_record_id + version + URL + licence + dates
              │
              ▼
CanonicalEntity
    │         │
    │         ├── source_values  (preserved original values)
    │         └── normalized_values (SkillScope representation)
    │
    └── ProvenanceLink
              │
              ├── mapping_type
              └── mapping_notes
              │
              ▼
CareerFact
    │
    └── displayable statement/value with full evidence chain
```

## Required source identity

Every imported source record supports:

- stable `source_id` and source record ID;
- publisher and geography;
- source URI and record URI where available;
- source version/release date;
- access and ingestion timestamps;
- exact licence/terms reference;
- checksum when a package/file is imported;
- quality status and verification timestamp;
- limitations.

## Required entity lineage

Every canonical occupation, skill, qualification, work activity, career pathway or labour-market fact supports:

- a stable SkillScope internal ID;
- original source identifiers;
- original source values retained unchanged;
- normalized values kept separately;
- transformation/mapping notes;
- source type;
- quality status;
- confidence only when meaningful and explainable.

## Mapping policy

Cross-source mappings are explicitly typed:

1. `exact` — identifiers or semantics support a direct correspondence.
2. `reviewed_related` — human/reviewer-supported related concept, not identity.
3. `weak_lexical` — lexical candidate only; never sufficient for a strong recommendation.
4. `unresolved` — relationship is retained for review but must not be presented as established equivalence.

**Cross-source comparison is triangulation, not voting.** O*NET, ESCO, NCS and NSDC should not be blended into one undifferentiated score.

## Display rule

A career fact marked `sourced` must resolve to:

`CareerFact → CanonicalEntity → SourceRecord + ProvenanceLink`

The UI/API must be able to show the source name, original record/page, version/release, geography, access/verification state, and any relevant limitation.

If the chain cannot be resolved, the fact must not be presented as sourced.

## Labour-market rule

PLFS and similar aggregate labour-market evidence can support a dated context statement, but it must never become an individual student's aptitude, interest, potential, personality, or career-fit score.

## No external data yet

The Stage 4 manifest remains authoritative for integration status. Stage 5 creates the machinery only. External source ingestion belongs to later stages after permitted runtime access and exact source-version checks.
