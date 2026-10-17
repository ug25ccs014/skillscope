# SkillScope AI — Third-party Data Attributions

This file is the human-readable attribution and adaptation notice for third-party occupational data used or bundled by SkillScope. Update it whenever an asset is added, removed, or transformed.

## O*NET OnLine curated profile extract

- **Publisher:** U.S. Department of Labor, Employment and Training Administration (USDOL/ETA); O*NET OnLine is developed by the National Center for O*NET Development.
- **Source:** https://www.onetonline.org/
- **Content licence:** CC BY 4.0 for O*NET OnLine content except content identified by O*NET as third-party content or otherwise excluded from the licence.
- **Licence:** https://creativecommons.org/licenses/by/4.0/
- **Specific O*NET OnLine licence and exclusions:** https://www.onetonline.org/help/license
- **Included here:** a manually curated extract of nine O*NET OnLine occupation profiles in `data/curated/occupations_snapshot.json`: Software Developers (15-1252.00), Data Scientists (15-2051.00), Graphic Designers (27-1024.00), Market Research Analysts and Marketing Specialists (13-1161.00), Social and Human Service Assistants (21-1093.00), Solar Photovoltaic Installers (47-2231.00), Environmental Scientists and Specialists, Including Health (19-2041.00), Project Management Specialists (13-1082.00), and Electrical and Electronic Engineering Technologists and Technicians (17-3023.00).
- **Skill-label handling:** for the O*NET Online profiles, a small set of labels shown in each page’s “Essential Skills” section is retained with the category name. This extract does not capture stable skill-element IDs or occupation-specific ratings. They are represented as occupation-scoped source references, not canonical skill concepts, weights, or student scores.
- **Editorial tags:** SkillScope adds a `curation_domain` to balance the demo’s topic coverage. It is product metadata only, not an official O*NET category, source-backed competency, or student signal.
- **Modifications:** SkillScope-authored concise paraphrases/summaries and selected terms; not a complete profile or bulk copy. Wage/employment fields and known third-party content are excluded from this curated extract.
- **Required notice for modified content:** “This page includes information from O*NET OnLine by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license. O*NET® is a trademark of USDOL/ETA. SkillScope has modified all or some of this information. USDOL/ETA has not approved, endorsed, or tested these modifications.”
- **Non-endorsement:** SkillScope is not approved, endorsed, or tested by USDOL/ETA or the National Center for O*NET Development.
- **Geography/limitations:** U.S. occupational context, not evidence of Indian demand, wages, qualifications, or a student's individual aptitude.

## O*NET Database 31.0 (future import; not currently downloaded)

If and when the official O*NET 31.0 downloadable database is imported, include the following attribution for the exact version and disclose changes:

> This page includes information from the O*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA). Used under the CC BY 4.0 license. O*NET® is a trademark of USDOL/ETA. SkillScope has modified all or some of this information. USDOL/ETA has not approved, endorsed, or tested these modifications.

- Official licence: https://www.onetcenter.org/license_db.html
- Official release page: https://www.onetcenter.org/db_releases.html
- Asset state: **not downloaded / not integrated** in this environment. Database licence coverage has exceptions; check exact selected files and any embedded third-party material.

## ESCO curated concept extract

- **Publisher:** European Commission, Directorate-General for Employment, Social Affairs and Inclusion.
- **Official dataset/download page:** https://esco.ec.europa.eu/en/use-esco/download
- **Reuse conditions:** https://esco.ec.europa.eu/en/about-esco/faq?page=1
- **Required acknowledgement for services/tools/apps:** “This service uses the ESCO classification of the European Commission.”
- **Modifications:** SkillScope's bundled record is a concise, adapted/curated summary of one ESCO software-developer concept. Any adaptation must be clearly identified as such.
- **Included here:** one ESCO software-developer concept record, retaining the original concept URI in `data/curated/occupations_snapshot.json`. The O*NET–ESCO occupation and work-activity links are manually reviewed “related” links; they do not assert exact concept equivalence.
- **Geography/limitations:** European classification context; not proof of Indian hiring demand, salary, regulated qualifications, or equivalence to any O*NET/NCS/NSDC record.
- **Asset state:** bundled as a small curated extract only; no official ESCO bulk package or live API result was downloaded during this run.

## NCS, NSDC and PLFS references

- **NCS:** https://www.ncs.gov.in/ — links/reference only. This project does not reproduce or redistribute NCS page contents until the specific reuse terms are verified.
- **NSDC National Occupational Standards:** https://nsdcindia.org/national-occupational-standards — link and review each current record individually; do not redistribute full QP/NOS documents without record-specific confirmation of terms.
- **MoSPI PLFS:** https://esankhyiki.mospi.gov.in/ — potential aggregate, dated labour-market context only. No PLFS table/data extract is bundled. It must never contribute to an individual student's aptitude, interest, or fit score.

## General rule

A source listed in this file is not automatically integrated. Actual import must preserve the exact source package/version, access timestamp, URI, checksum, licence reference, and transformation notes. Do not use third-party O*NET Web Services results under the database licence by assumption. Keep public UI attribution visible wherever these records are shown, not only in developer documentation.
