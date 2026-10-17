# Stage 4 — Data Source Register

**Reviewed on:** 17 October 2026  
**Stage status:** Source research complete; no external career dataset is imported or connected to the app.  
**Important boundary:** Official source pages were reviewed through the research browser. A successful research-page view does **not** prove that an API call or bulk download works from the application runtime. Runtime downloads have not been performed in this stage. The development session previously experienced a DNS failure to the npm registry; thus runtime source connectivity remains explicitly unverified.

## Executive decision

Use an **India-first, evidence-separated source strategy**:

1. Keep **NCS** and **NSDC QP/NOS** as authoritative Indian reference sources. At this stage, link to exact official pages and preserve record metadata; do not copy/re-host their text or scrape lists until the applicable rights are confirmed for the specific page/document.
2. Plan small, version-pinned **ESCO** and **O*NET Database** extracts for structured occupation/skill relationships. Use them as supplementary taxonomies, not as evidence of Indian demand. Prefer official bulk downloads because exact releases can be pinned and normalized while preserving source lineage.
3. Treat **PLFS** as dated, aggregate labour-market context only. It must never be fed into a student interest, ability, potential, or career-fit score.
4. Do **not** copy the O*NET Interest Profiler questionnaire into the MVP. Write original challenges and reflection prompts, and do not call them a validated psychometric instrument.

No source is marked integrated. Stages 5–6 must implement the provenance model and then ingest only the selected, permitted data.

## Source decision matrix

| Source | What official pages establish | Access and reuse decision | Intended use | Important limitations | Stage 4 integration status |
|---|---|---|---|---|---|
| National Career Service (NCS) | Official Indian government career/job-seeker portal. Reviewed official Terms & Conditions page says content can change without notice and provides disclaimers/governing-law language. The reviewed terms page does not itself establish a blanket open-data licence. | **Link-only** to exact career information pages until terms for the exact page/material or written permission establish what may be cached, copied, adapted, or redistributed. No public API/download was verified from reviewed pages. | India-first career-information reference and manual cross-check. | Rolling web content; the absence of a blanket licence on the reviewed page is not proof that no separate rule/policy applies. | Not integrated |
| NSDC National Occupational Standards (NOS), Qualification Packs (QP), model curricula | Official listing describes NOS as workplace performance/knowledge standards and shows records from different status categories, including aligned/cleared, under validation, and retired. | **Link-only, record-by-record review.** Preserve QP/NOS code and exact status. The reviewed pages do not establish one blanket reuse licence for all downloadable documents; specific notices may have narrower terms. | Indian competency/qualification cross-check for a chosen occupation, after checking the exact QP/NOS record. | Some retired standards explicitly say not to train against them. Vocational QPs do not represent every occupation. Similar names do not prove qualification equivalence. | Not integrated |
| O*NET Database 31.0 | The official release page identifies version 31.0 (August 2026) as current production at review time and offers database downloads in tabular formats including CSV/JSON. The downloadable database files are covered by CC BY 4.0 except where the official licence identifies exceptions. | **Future pinned bulk download** of selected database files. At ingestion, record release, exact files, access time and SHA-256. Use required attribution, version number, licence link and modifications notice. Avoid Web Services for transformations unless its separate terms are specifically reviewed: web-service data is subject to account/registration and no-alteration requirements, and external results may have other rights. | Secondary structured skill, ability, work activity and occupation reference; cross-check against, but never substitute for, Indian records. | O*NET-SOC represents the U.S. economy. It is not evidence of Indian salaries, demand, qualifications or hiring practice. | Selected for future snapshot; not integrated |
| ESCO classification | Official portal offers downloadable datasets in multiple machine-readable formats. The reuse FAQ allows reuse without charge subject to attribution and clearly indicating adaptations. The download page labels ESCO v1.2.1 (last update 10 December 2025), while the API page lists default v1.0.9 and also v1.2.0. | **Future version-pinned English CSV extract** of only needed occupation/skill relationship modules. Do not rely on an unpinned API default. Inspect the actual exported package and record its version/metadata at ingestion. Include the required statement: “This service uses the ESCO classification of the European Commission.” Clearly label adaptations. | Supplementary concept graph and vocabulary crosswalk; preserve ESCO URIs and source relationships. | European labour-market taxonomy; labels and links do not establish Indian equivalence or demand. Official page version discrepancy means package-level version verification is mandatory. | Selected for future snapshot; not integrated |
| Periodic Labour Force Survey (PLFS), Annual Report 2025 | Official MoSPI/NSO publication page provides the Annual Report 2025 press note/report covering January–December 2025; the press note is dated 27 March 2026. The official catalogue lists PLFS material. | **Link-first context reference.** For any extracted table or figure, capture exact page/table, period, geography, definitions, release date and access date; do not assume a blanket redistribution licence before checking applicable terms. | A separate labour-market context panel, with date/geography, separate from the student profile and recommendation scoring. | Aggregate and lagged labour statistics; definitions and denominators matter. Never use as individual ability/interest evidence. | Selected for context only; not integrated |
| O*NET Career Exploration Tools / Interest Profiler | The official tool licence page distinguishes verbatim redistribution (CC BY-ND 4.0) from modifying/extending the tools (O*NET Tools Developer License, attribution and product-validation obligations). | **Excluded from MVP questionnaire copy.** Independently author age-appropriate activity prompts. Reconsider tool-derived content only if the team deliberately meets the specific licence and validation requirements. | Licence guardrail only. | A newly authored quiz inspired by broad career-exploration ideas is not thereby validated. Do not copy protected question wording or scoring. | Excluded; no tool content imported |

## Detailed verification and citations

The URLs below are official publisher pages reviewed on 17 October 2026. The register records what each page establishes; unverified runtime access remains unverified.

### 1. NCS — India-first career reference

- Portal: <https://www.ncs.gov.in/>
- Terms & Conditions: <https://ncs.gov.in/terms&condition>
- The terms page reviewed states that website content may change without prior notice and provides legal disclaimers and governing-law conditions. It does not on its own establish a blanket permission for bulk data reuse.
- Decision: use outbound links and exact page-level references until the applicable conditions for the selected material have been confirmed. Do not represent this portal as having a public API or bulk data feed without direct evidence.

### 2. NSDC — Indian occupational standards

- NOS/QP overview: <https://www.nsdcindia.org/national-occupational-standards-and-model-curriculum>
- NOS listings: <https://nsdcindia.org/national-occupational-standards>
- Example listing illustrating lifecycle labels: <https://nsdcindia.org/nos-listing/150>
- The pages define what NOS/QPs represent and expose status differences. Status is a first-class field: a retired standard must not appear as a current recommended pathway. Licence/reuse terms have to be checked at the specific document/record level.
- Decision: use the exact official record as a reference; never silently replace it with an international role name or treat a draft/retired role as current.

### 3. O*NET — versioned occupational/skill reference

- Database/release: <https://www.onetcenter.org/database.html> and <https://www.onetcenter.org/db_releases.html>
- Downloadable database licence: <https://www.onetcenter.org/license_db.html>
- Web Services licence: <https://services.onetcenter.org/help/license_data>
- The official database page identifies the 31.0 database as the current production release for August 2026. The database download licence is CC BY 4.0, with required attribution and an indication of changes. The Web Services terms are separate: account holders must credit/link the service and register the leveraging application URL; published API data is to be presented without modification, and API results can contain third-party data exceptions.
- Decision: later use a versioned bulk snapshot for local mapping/normalization rather than assuming API data can be altered freely under the bulk database licence.

### 4. ESCO — structured skills/occupations graph

- Download portal: <https://esco.ec.europa.eu/en/use-esco/download>
- API documentation: <https://esco.ec.europa.eu/en/use-esco/use-esco-services-api/esco-web-service-api>
- Reuse FAQ: <https://esco.ec.europa.eu/en/about-esco/faq?page=1>
- The Commission says the ESCO classification may be reused free of charge subject to acknowledgement and clear marking of adaptations. The download portal identifies ESCO v1.2.1 last updated 10 December 2025; the API page also lists default v1.0.9 and v1.2.0. Because those page-level versions differ, a data ingestor must inspect the actual selected package and pin the downloaded release. Do not confuse classification-data reuse conditions with the separate software licences for API implementation components.
- Decision: later import a narrow, version-pinned English CSV subset and its relationships/URIs. Map to Indian roles only through explicit crosswalk records with confidence and review notes.

### 5. PLFS — aggregate labour context only

- Official report/press note: <https://www.mospi.gov.in/uploads/latestReleases/latest_release_1774607827733_3e8964a9-268b-4cc9-ad65-cfc8a9e32f08_Press_note_AR_PLFS_2025_23032025_V2.1_26032026_final.pdf>
- Official catalogue: <https://esankhyiki.mospi.gov.in/catalogue-main/catalogue?page=0&product=PLFS>
- The official report reviewed identifies Annual Report 2025 for January–December 2025 and a press note dated 27 March 2026. Any future display must state period, geography, table, measure definition and release date. The report's precise blanket reuse terms were not confirmed in this source audit.
- Decision: source-link first; show contextual aggregate statistics only after checking reuse and preserving the exact statistical definitions. Never use PLFS to score an individual.

### 6. O*NET Interest Profiler — questionnaire exclusion

- Tool-specific licence: <https://www.onetcenter.org/license_tools.html>
- Verbatim tool redistribution is covered by CC BY-ND 4.0 with attribution and no modified/extended redistribution. Modification or extension requires the O*NET Tools Developer License, attribution/linking and validation of every product incorporating the tool content.
- Decision: the MVP will author original challenge and reflection prompts. They are exploratory product interactions, not a validated psychometric tool.

## Access feasibility: what has and has not been verified

**Verified through official page review:** source portals/landing pages and the licences/terms above could be read in web research on the review date; official pages describe O*NET bulk formats, ESCO download formats and ESCO reuse conditions; the official PLFS report URL and catalogue were visible.

**Not verified in the application runtime:** none of the selected datasets was downloaded into the repository, no external API request was executed by the application, no API credentials were configured, and no application source adapter exists at this stage. The build environment previously failed to resolve `registry.npmjs.org` (`EAI_AGAIN`), so runtime network access cannot be assumed from public page visibility. Stage 6 must test the permitted download/API from the actual development environment before setting any record to integrated. If that fails, record the error and use only permitted link-only references or a properly documented, licence-compatible cached snapshot.

## Source-selection policy for later stages

- **First Indian reference:** NCS, linked out until exact reuse permissions are known.
- **Indian competency corroboration:** selected current NSDC QP/NOS records, individually reviewed and status-checked; link-only until record-specific reuse is clear.
- **Structured concept graph:** ESCO, version-pinned English CSV subset.
- **Structured work/skill reference:** O*NET 31.0 downloadable database subset, CC BY 4.0 attribution and modification notices.
- **Context only:** PLFS report tables with exact dates/definitions and no individual scoring.
- **Questionnaire rule:** original SkillScope tasks only; no copied O*NET Interest Profiler instrument in MVP.

Cross-source comparison is for triangulation, not voting. Disagreement can reflect geography, occupational granularity, taxonomy definitions or publication timing. A role/skill mapping must preserve the original identifiers and explain whether it is an exact match, a reviewed related concept, a weak lexical candidate, or unresolved.

## Stage 4 exit checklist

- [x] All five requested source families (NCS, NSDC, O*NET, ESCO, PLFS) reviewed from official pages.
- [x] O*NET downloadable database licence and separate Interest Profiler/Web Services terms documented.
- [x] ESCO reuse statement and API/download version discrepancy documented.
- [x] NCS/NSDC reuse uncertainties and record status risks documented rather than assumed away.
- [x] PLFS separated from individual assessment and recommendations.
- [x] A small future source subset and permitted access strategy selected.
- [x] `data/sources_manifest.yaml` updated; no source marked integrated.
- [ ] Actual external data package download tested from runtime — blocked/unavailable in this session, explicitly tracked; must be retried in a network-enabled development environment before Stage 6 import.


## Stage 19 source-contract audit (2026-10-17)

Automated integrity checks verify that the active curated snapshot is explicitly a non-live `curated_extract`, includes exactly 10 unique `(source_id, source_record_id)` records and unique HTTPS record URLs, retains publisher/version/release/geography/access-time/licence/transformation/limitation metadata, and does not embed salary, wage, employment-count, openings or growth-rate numbers. The current nine O*NET OnLine profile extracts and one ESCO software-developer concept were imported to the local graph; the full O*NET Database, full ESCO classification, NCS, NSDC and PLFS remain unintegrated/reference-first. See `docs/VALIDATION_REPORT.md` for the exact checks and caveats. Automated metadata checks do not replace live URL checks, legal licence review, or source refresh.
