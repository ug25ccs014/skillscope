# Stage 4 — Source Access Audit

Date of research review: 2026-10-17

## Evidence scope

The official pages listed in `DATA_SOURCE_REGISTER.md` were reviewed using the available research browser. This establishes what those pages say, not that SkillScope's local runtime can download a dataset or execute API calls. No external dataset was downloaded and no source adapter was implemented during Stage 4.

## Feasibility by source

| Source | Official page access | Documented data route | Local runtime verification | Decision for this stage |
|---|---|---|---|---|
| NCS | Reviewed | Career portal/reference pages; no public API or bulk download confirmed by reviewed page | Not tested | Link-only; confirm page-level terms before copying/caching |
| NSDC QP/NOS | Reviewed | Official listings and per-record standards/curriculum pages | Not tested | Link-only; inspect status and rights per record |
| O*NET Database 31.0 | Reviewed | Official versioned bulk files (CSV/JSON and other formats); separate Web Services | Download not attempted | Plan bulk snapshot under the downloadable database CC BY 4.0 terms; record version/file/hash |
| ESCO | Reviewed | Download portal supports machine-readable export; public web-service API documented | Download/API not executed | Plan version-pinned bulk CSV; verify package version metadata due official page discrepancy |
| PLFS Annual Report 2025 | Official PDF and catalogue visible in research | Published report/PDF and catalogue | Local download not attempted | Link-first; contextual aggregates only after terms and table/definition check |
| O*NET Interest Profiler | Tool-specific licence reviewed | Verbatim redistribution and modification paths specified by separate licences | Tool not copied or tested | Excluded from MVP questionnaire; create original prompts |

## Network environment caveat

A prior attempt to install frontend dependencies failed because DNS resolution for `registry.npmjs.org` returned `EAI_AGAIN`. This does not prove that each source host is unreachable, but it means the build cannot assume general internet egress. Consequently, this report does not claim live API/download success from the app runtime. Re-run access checks in the actual development environment in Stage 6 before importing data.

## Required Stage 6 proof before any source becomes integrated

1. Run a permitted official source fetch or download from the app/developer environment.
2. Capture the exact URL, retrieval timestamp, package/version metadata, response status, downloaded filename and SHA-256 checksum.
3. Review archive contents and validate representative records and required fields.
4. Confirm the exact licence/terms for the selected files and retain attribution/changes notices.
5. Keep raw source assets separate from normalized records and preserve the original source identifiers.
6. If a download/API fails or terms are unclear, record the actual error and leave that source `not_integrated`; use only a permitted link-only reference or legally compatible, clearly labelled cached snapshot.
