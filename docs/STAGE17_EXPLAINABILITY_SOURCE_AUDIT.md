# Stage 17 — Explainability and Source Validation UI

## Outcome

Stage 17 adds a source-audit endpoint and student/reviewer interface, and joins each recommendation's evidence references to its local matching rules and source-backed occupational facts. It is designed to let a reviewer trace a hypothesis without treating a heuristic as scientific truth.

## API

`GET /api/source-registry` returns:

- manifest version, last-reviewed date, and recorded manifest status;
- publisher/name, official and supporting links, geography, source role, source version/release, review date, integration and runtime status;
- a truthful state label (`live`, `cached`, `curated`, `link_only`, `unavailable`), last successful app-side import/sync timestamp where one exists, last attempt state, active snapshot identifier and SHA-256 where available;
- recorded reuse/licensing statement and known limitations;
- source records or canonical entities explicitly marked `conflicted` in the local provenance registry;
- non-exact cross-taxonomy mappings, separately labelled as mapping uncertainty;
- compact career-graph status, including builder/schema version, unresolved relationship count, decoded build timestamp, limitations, and comparison of currently active source snapshot IDs against the IDs used to build the graph.

Invalid manifest/state files return an explicit service-unavailable response. The API does not expose local filesystem paths or raw exception details. “Live” requires an explicit runtime success record that declares live data; a reviewed web page, cached file, curated extract, or URL alone is insufficient.

## Recommendation audit trail

The recommendation card includes an expandable audit trace:

1. distinct relevant observation count and the most recent observation timestamp, computed over all distinct evidence considered;
2. a bounded list of individual evidence records, each labelled with observation time, evidence type, signal dimension, domain, interpretation and why it was used;
3. each local matching rule with the evidence IDs/titles linked to that rule and any cited source record;
4. source-derived occupational facts with publisher, title, source version, geography, and direct record link;
5. an explicit boundary between local heuristic inference and external source facts, plus the next validating activity already associated with the hypothesis.

The displayed evidence detail is bounded per recommendation for UI performance. The full distinct-observation count and latest timestamp are separate response fields and are not calculated from the truncated display list.

## Conflict semantics

- Source records and canonical entities marked `conflicted` are surfaced as unresolved conflicts.
- Crosswalk edges with non-exact mappings or unresolved/proposed review states are surfaced separately. A “reviewed related” mapping means related concepts, not equivalent concepts and not necessarily contradictory source facts.
- An empty conflict list is not stated as evidence that all external sources agree.

## Validation

- Unit tests validate status classification (live only with explicit evidence, cached vs curated vs link-only vs unavailable), sync timestamps, invalid/duplicate source manifests, conflicted source rows, conflicted canonical entities, and non-exact mapping disclosure.
- Recommendation tests validate full distinct-observation counts/latest timestamps separately from bounded evidence-detail lists.
- Source-registry API test validates the public response contract against the local manifest.
- Stale-snapshot tests confirm graph metadata is decoded and active snapshot drift is surfaced; UI contract tests enforce evidence → matching → source-fact trace and graph freshness disclosure.
- A stale-snapshot fixture confirms graph metadata is JSON-decoded and a changed active snapshot is flagged; source registry UI contract tests verify evidence → matching → fact trace and graph snapshot disclosure.
- Full backend suite and syntax validation are recorded in `docs/MASTER_BUILD_LOG.md`.

## Limitations

- Only the existing small curated O*NET OnLine/ESCO extract is represented in the graph; complete O*NET/ESCO datasets and Indian NCS/NSDC occupational data have not been imported.
- No live source feed is currently claimed.
- Source disagreement is shown when the local provenance registry explicitly marks the record/entity conflicted; this does not automatically discover every possible contradiction in arbitrary external documents.
- The frontend has syntax-transpilation checks only. Dependency-backed TypeScript checking, a Vite production build and real browser E2E checks remain unverified because npm dependencies were not installable in the current environment.
- Authentication and authorization remain incomplete; do not use with real student/minor records in an exposed deployment.
