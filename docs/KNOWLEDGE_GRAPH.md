# Stage 7 — Career & Skill Knowledge Graph

**Status:** Implemented and verified for the bundled curated snapshot. Full O*NET Database, full ESCO, NCS India, and NSDC datasets are not integrated.

## Purpose

The graph connects sourced occupational profiles to selected tasks and source-listed skill references while preserving source identity, geography, release context, source URI, licence and mapping uncertainty. It is a version-aware projection of the Stage 5 provenance registry and Stage 6 ingestion snapshots. It is not a student assessment, labour-market forecaster, or live feed.

## Current curated coverage

`data/curated/occupations_snapshot.json` contains ten source-linked occupation profiles:

- Nine O*NET OnLine profile extracts: Software Developers (15-1252.00), Data Scientists (15-2051.00), Graphic Designers (27-1024.00), Market Research Analysts and Marketing Specialists (13-1161.00), Social and Human Service Assistants (21-1093.00), Solar Photovoltaic Installers (47-2231.00), Environmental Scientists and Specialists, Including Health (19-2041.00), Project Management Specialists (13-1082.00), and Electrical and Electronic Engineering Technologists and Technicians (17-3023.00).
- One ESCO software-developer concept (2512.4) retaining its original concept URI.

The O*NET profile pages were reviewed from official O*NET OnLine pages, including their Tasks and Essential Skills sections. The summary/task wording is paraphrased. A small set of labels from the source's “Essential Skills” section is retained for the nine O*NET profiles; the extract does **not** capture a stable source skill-element ID or an occupation-specific numeric rating for those labels.

`curation_domain` is a SkillScope editorial coverage tag added to ensure the demo represents technical, analytical, creative, business, social-support, environmental and hands-on examples. It is not an official taxonomy category, a competency, or a student signal. Full profile URLs, publisher, version context, geography, licence reference, modifications and limitations are stored with every record.

## Graph inventory after Stage 7 build

| Node type | Count | Meaning |
|---|---:|---|
| Occupation | 10 | Source occupation profile nodes; the O*NET and ESCO software-developer labels remain separate |
| Skill | 45 | Occupation-scoped labels shown under O*NET OnLine's Essential Skills section; not merged into canonical skill concepts |
| Work activity | 45 | Selected paraphrased work/task statements from the profile records |
| Occupational term | 7 | Older selected O*NET terms whose original source category was not captured; they remain terms, not skills or student interests |
| Capability hypothesis | 2 | SkillScope-authored, heuristic concepts supported by selected O*NET and ESCO task phrases |
| **Total nodes** | **109** | |

| Relationship | Count | Meaning |
|---|---:|---|
| `occupation_has_skill` | 45 | The cited O*NET profile lists the label in its Essential Skills section; no rating is implied |
| `performs_task` | 45 | Selected task paraphrase associated with the source occupation profile |
| `associated_with_source_term` | 12 | Selected term carried over with its source-category limitation |
| `supports_capability_hypothesis` | 4 | Task evidence for a SkillScope-authored heuristic hypothesis |
| `related_occupation` | 1 | Reviewed O*NET/ESCO software-developer relationship; **related**, not exact |
| `related_work_activity` | 1 | Reviewed relationship between selected software-debugging task phrases; **related**, not exact |
| `crosswalk_candidate` | 1 | Unresolved exact-equivalence candidate retained for review |
| **Total edges** | **109** | |

No dangling relationship endpoints were reported in the current projection. `source_data_is_live` remains `false`.

## Important identity and evidence rules

1. **Source taxonomy identities remain separate.** O*NET's 15-1252.00 and ESCO's 2512.4/URI are separate occupation nodes. Their manually reviewed relationship is not official and does not claim one-to-one equivalence.
2. **Skill labels are not canonical skill concepts yet.** Each Essential Skills label is linked to the profile where it appears. Because the stable source skill-element ID was not included in the curated extract, nodes are deliberately occupation-scoped; equal text on two profiles is not automatically merged into one source concept. The graph attributes mark the missing source ID and the absence of a rating.
3. **No occupational reference is student evidence.** Work activities, source-listed skills, occupational terms, source ratings and aggregate context cannot be used as a student's own skill or interest score.
4. **Heuristics remain marked.** The two capability hypotheses are authored by SkillScope, are not official taxonomy skills, and have not been psychometrically or occupationally validated.
5. **No false qualification pathway.** NCS and NSDC records are not integrated; no Indian qualification prerequisite or pathway is inferred. No salary, vacancy or Indian demand claim is created from these profiles.
6. **Snapshot freshness matters.** Each graph build records the active source snapshot IDs. API requests reject a missing or stale graph; rebuild after a successful import rather than mixing earlier source versions.
7. **Reuse and modification must be visible.** O*NET attribution and ESCO acknowledgement/adaptation notes are in `docs/ATTRIBUTIONS.md`; profile cards expose source URLs and licence links.

## API

All endpoints are read-only:

- `GET /api/knowledge-graph/status` — node/edge counts, active snapshots, freshness and limitations.
- `GET /api/knowledge-graph/careers?limit=50&offset=0` — profile cards with source references, tasks, skill references, occupational terms and relationships.
- `GET /api/knowledge-graph/nodes?node_type=skill&q=critical&limit=50&offset=0` — filtered node search and pagination.
- `GET /api/knowledge-graph/nodes/{node_id}` — one node and its source lineage.
- `GET /api/knowledge-graph/edges?relation_type=occupation_has_skill&limit=100` — relationships and references.
- `GET /api/knowledge-graph/crosswalks?review_status=unresolved` — related and unresolved cross-taxonomy mappings.

The UI offers cited career cards, source-lineage inspection, the essential-skill labels with caveats, an explicit crosswalk audit and a limitations section. If API status says not built or stale, UI does not pretend the graph is current.

## Reproduce the local graph

Run from the repository root after installing backend dependencies:

```bash
PYTHONPATH=backend python -m app.services.ingestion.cli import-curated \
  --snapshot data/curated/occupations_snapshot.json \
  --manifest data/sources_manifest.yaml \
  --database data/skillscope.db \
  --state-file data/ingestion_state.json

PYTHONPATH=backend python -m app.services.knowledge_graph rebuild
PYTHONPATH=backend python -m app.services.knowledge_graph status
PYTHONPATH=backend pytest -q
```

The ZIP excludes the generated SQLite file; the commands above rebuild the local source registry and graph from the bundled curated snapshot. They make no external requests.

## Verification and limitations

- Backend regression suite: `PYTHONPATH=backend pytest -q` — 94 passed after Stage 7 changes.
- Clean local import: 10 records, 32 career facts, no duplicates; 45 source-listed skill references are included in those facts.
- Graph: 109 nodes and 109 edges; 10 occupation nodes, 45 occupation-scoped skill reference nodes, 45 work activities, 7 occupational terms and 2 heuristic capability hypotheses.
- Graph rebuild is repeatable and fails closed when active source state is invalid or stale.
- A frontend install retry on 2026-10-17 timed out after npm registry DNS `EAI_AGAIN` errors. TSX syntax transpilation passed, but the full TypeScript typecheck and Vite production build remain unverified.
- The full O*NET/ESCO packages remain unintegrated. No real NCS or NSDC qualification pathway has been imported. This is not production-ready occupational advice.
