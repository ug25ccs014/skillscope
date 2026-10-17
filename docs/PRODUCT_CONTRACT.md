# SkillScope Product Contract

**Contract status:** Stage 2 — MVP boundary defined; awaiting approval before Stage 3  
**Product:** SkillScope AI  
**MVP context:** Hackathon-grade, end-to-end demonstrable vertical slice built from scratch. This contract defines intended product behavior; it does not claim later-stage features are already implemented.

## 1. Product promise

**SkillScope helps people discover, validate, and develop their strengths and interests over time.** It combines a person's stated interests and goals, voluntary activities, challenge evidence, optional projects/experience, and attributable career/skills information to propose testable possibilities and practical next steps. It is not a quiz that declares one correct career.

Product line: **“Most career guidance asks a student what they want to become. SkillScope helps them discover what they could become.”**

### Principles

1. Treat career recommendations as hypotheses to explore, not verdicts or guarantees.
2. Separate a person's preferences, observed task evidence, sourced occupation facts, and aggregate labour-market context.
3. Explain why a suggestion appears and what evidence could strengthen or change it.
4. Missing evidence means **unknown**, not zero ability. One task cannot establish a permanent trait.
5. Age changes the safe and appropriate entry experience; age alone must not assign ability, restrict opportunity, or determine a career.
6. A newly registered user has no assumed history, regardless of age.
7. Prefer a complete, testable user journey to multiple disconnected or decorative screens.

## 2. Primary personas and jobs to be done

### Persona A — Early explorer (ages 10–14)

**Need:** Discover many kinds of activities without being pressured to choose a career prematurely.  
**Job to be done:** “Help me try different things, notice what I enjoy or find interesting, and choose another safe activity to explore.”  
**Product behavior:** Short, age-appropriate challenges across varied areas; simple language; tentative patterns such as “worth exploring”; no fixed-career labels. Real child data collection requires the appropriate consent and privacy design before production use.

### Persona B — Direction tester (ages 15–17)

**Need:** Understand whether current interests stand up to experience, while discovering areas they have not yet tried.  
**Job to be done:** “Help me test my current ideas, notice skill gaps, and discover plausible alternatives before making important education choices.”  
**Product behavior:** Ask what the student currently likes, what they have tried, how certain they feel, and what remains unexplored. Test declared interests using more than one type of challenge and deliberately sample alternatives.

### Persona C — Career builder or career explorer (ages 18+)

**Need:** Turn existing study, skills, projects, and goals into practical next steps, or restart discovery when direction is uncertain.  
**Job to be done:** “Help me understand where I am now, what I need for a goal, which actions to prioritize, and what alternatives fit my evidence.”  
**Product behavior:** Review current education, skills, projects/experience, goals, and desired timeline where voluntarily supplied. Provide gap analysis and action steps, but preserve a discovery route for uncertain or contradictory cases.

### Persona D — Late entrant with limited evidence (any supported age)

**Need:** A useful start without fabricated personal history.  
**Job to be done:** “Start from what is actually known about me today, then help me build a reliable evidence base.”  
**Product behavior:** Run a baseline calibration, state what is known versus unknown, and collect evidence progressively. Do not simulate years of tracking.

## 3. One coherent MVP journey

The MVP is not complete when a user can only take a quiz or view a static career list. The target is one connected vertical slice:

1. **Enter:** User chooses an age band (10–14, 15–17, or 18+) without requiring a full date of birth for the MVP.
2. **Baseline:** User provides a concise, age-appropriate set of self-reported interests, career clarity, prior activities/projects/experience, and areas they have not explored. Inputs are optional where feasible and missing inputs stay unknown.
3. **Calibrate:** SkillScope chooses a starting mode using age band plus evidence amount/quality, career clarity, prior projects/experience, and exploration need. It returns the mode, rationale, and next step.
4. **Profile:** Show a transparent starter profile with stated preferences separated from demonstrated evidence, confidence/coverage cues, and a few candidate domains or pathways where supported.
5. **Challenge:** User completes a short practical activity tied to a domain or skill and provides reflection on enjoyment, difficulty, confidence, and desire to continue. For age 10–14, text and interaction must be age-appropriate.
6. **Evidence update:** Store a dated evidence item identifying whether it came from self-report, activity performance, project, external source, heuristic, or labelled demo fixture.
7. **Explain change:** Show what changed after the new evidence, what did not change, why, and what remains uncertain. Do not automatically turn enjoyment into ability or a single score into a stable personality claim.
8. **Next step:** Recommend a useful next challenge, learning action, or exploration activity with a short explanation.
9. **Pathway cards:** Show relevant skills/competencies, sourced requirements when available, evidence-backed gaps or unknowns, concrete next steps, and traceable source references. Clearly label heuristics and geographic scope.
10. **Change direction:** Allow the user to revise their career goal or enter a new discovery cycle. Recommendations should adapt to new evidence instead of trapping a user in a prior path.

## 4. MVP feature boundary

### Required in the final MVP

- Responsive, accessible web application that works on mobile and desktop.
- All three age-aware entry modes, with age treated as one calibration input rather than the only input.
- Explainable entry calibration returning starting mode, rationale, and next step.
- Short, age-appropriate baseline and a student evidence/profile representation.
- A small, diverse challenge library spanning multiple domains.
- User reflection after a challenge and a time-stamped evidence record.
- Explainable, deterministic/configurable recommendations that can update when evidence changes.
- A small but real and verified career/skill/pathway subset with source provenance. Target approximately 8–12 pathways only if the quality bar can be met; fewer verified pathways are preferable to fabricated breadth.
- Distinction between sourced facts, user-provided evidence, heuristic inference, cached/curated records, and demo/test fixtures.
- Clear next actions and skill-gap summaries that do not imply guaranteed career outcomes.
- Reproducible setup, useful empty/loading/error states, automated tests for important logic, and an honest handoff.

### MVP non-functional requirements

- Core journey functions without a generative AI provider or any one external source being available at request time.
- Recommendation decisions are reproducible and testable; any weights are documented heuristics, not claimed scientific validation.
- No secrets in source control; configuration uses environment variables and example templates.
- Data model preserves source lineage and supports dated evidence updates.
- Prefer data minimization; do not require full date of birth, exact address, or unrelated personal data for matching.
- No personal identifiable information about minors is sent to external LLM/API providers in the MVP.
- User-facing UI distinguishes current/live, cached, curated, heuristic, and demo data wherever relevant.

## 5. Demo scope versus future production scope

### Hackathon MVP demo

- Demonstrate one end-to-end user journey rather than many disconnected pages.
- Include representative profiles for all three age modes, clearly labelled as demo fixtures if synthetic.
- Show how late entry changes the baseline strategy, and how new challenge evidence can alter the next recommendation.
- Provide at least one example of a user changing or questioning an intended career direction.
- Demonstrate provenance from the actual sources integrated by the relevant stages; no fake “live” status.
- Run locally with documented instructions. The MVP should degrade honestly when an external source is unavailable.

### Explicitly out of scope for the first MVP

- Production authentication, enterprise tenancy, billing, or social networking.
- Secret surveillance or automatic collection from unrelated apps, browsing history, messages, or device activity.
- High-stakes automated decisions about school admission, employment selection, diagnosis, or financial eligibility.
- Guaranteeing jobs, salaries, admissions, exam performance, or future success.
- Claims of scientifically validated psychometrics unless an exact instrument/method and its validation evidence support the claim and usage is licensed.
- Live job vacancy scraping, labour-market forecasting, or a comprehensive real-time jobs marketplace.
- Sending identifiable child data to an external AI provider.
- Full production legal/compliance certification. However, privacy-by-design, age-appropriate defaults, consent/guardian-consent planning, user review/correction, and deletion requirements must be designed before collecting real child data.
- Broad multilingual support in the first MVP unless separately approved; architecture should avoid unnecessarily hard-coding interface strings.

## 6. Decision and recommendation contract

Every recommendation exposed in the MVP must contain, as applicable:

- **Suggestion:** domain, pathway, challenge, or next action.
- **Reasoning:** the relevant user-stated preference, observed evidence, goal, or sourced requirement.
- **Evidence status:** observed, self-reported, source-backed, inferred by a heuristic, or demo-only.
- **Confidence/coverage:** an understandable indication of evidence strength and gaps; do not present it as a validated probability unless it truly is one.
- **Unknowns:** meaningful missing evidence that might change the result.
- **Next validation step:** a challenge, project, question, or action to test the hypothesis.
- **Source reference:** where occupational/skill facts are displayed, use traceable source references and label geographic/contextual limitations.

Aggregate labour-market statistics may supply dated context only; they may not be used as proof of an individual student's interest or ability. Similar skill labels across different taxonomies are not automatically equivalent.

## 7. Data-source commitments

The official NCS, NSDC, O*NET, ESCO, and PLFS sources in the master prompt are candidates to investigate, not assumed integrations. Stage 4 must inspect exact access methods, current versions, licence/terms, attribution requirements, geography, and field coverage. Stage 5 must preserve provenance, and Stage 6 must verify actual import/refresh behavior.

For the final MVP, aim to use more than one independent, permitted source where it materially improves career/skill validation. Do not require every career record to appear in every source. Maintain original values and transparent crosswalks, preserve disagreements, and exclude records whose reuse or meaning cannot be verified. Do not use a source URL in place of actual integration evidence.

## 8. Success criteria and acceptance tests

The final MVP is accepted only when the following user-visible and technical behaviors can be demonstrated:

1. **Late entry works:** a new 16-year-old and a new 22-year-old receive appropriate starting journeys without fabricated history.
2. **Calibration is not age-only:** profile clarity, evidence quality/volume, experience/projects, and exploration need can alter the chosen starting mode.
3. **All age modes are represented:** 10–14 Discover & Shape, 15–17 Explore & Validate, and 18+ Develop & Optimize.
4. **Low evidence stays uncertain:** missing data is shown as unknown, not as low ability.
5. **Challenge loop is complete:** a user can complete a challenge, provide reflection, create an evidence record, and see a justified next step.
6. **Change is explained:** the interface shows why a recommendation changed or why it did not change after new evidence.
7. **Goal changes are supported:** a user can revise their intended pathway or re-enter discovery.
8. **Career facts are traceable:** each displayed sourced occupation/skill fact can be traced to its source record/page and release/version context where available.
9. **Source categories stay distinct:** individual evidence, occupational facts, aggregate labour data, heuristics, and demo fixtures cannot be silently mixed.
10. **Offline/source failure is handled:** the app indicates cached/source-unavailable states honestly and the core journey does not falsely claim live data.
11. **Privacy defaults are appropriate:** no full DOB or unrelated personal data is required for the baseline; no identifiable minor data is sent externally by the MVP.
12. **Core flow is reliable:** automated tests cover entry calibration, evidence recording, recommendation behavior, source provenance, and key API contracts; a manual end-to-end demo checklist is documented.
13. **Setup is reproducible:** a developer can install, run, and test the documented application in an environment with required package/network access.
14. **No false completeness:** unimplemented features are labelled as future scope; sources, APIs, tests, and model validation are reported truthfully.

## 9. Known assumptions and risks

- Initial product context is India-first; O*NET and ESCO may help with structured mappings but do not represent Indian labour-market facts by themselves.
- Official career resources may be HTML-first, use restricted access, or lack an openly reusable bulk/API interface. A permitted curated extract or link-only integration is acceptable where disclosed.
- Crosswalks between taxonomies may be uncertain, one-to-many, or geographically mismatched; preserve that uncertainty.
- Evidence from voluntary short challenges is sparse and context-dependent. It supports exploration hypotheses, not stable diagnosis.
- Age-specific design and consent obligations need specialist review before production deployment with real children.
- Network access, external registries, API availability, and credentials may block integrations in some build environments; record and work around these honestly.
- Hackathon time constrains the number of fully verified careers. Data quality takes precedence over catalogue size.

## 10. Contract change control

Any change to the core journey, age-mode behavior, data integrity rules, privacy constraints, or acceptance criteria must be recorded in `docs/DECISIONS.md` with the reason and effect on stage scope. A stage must not quietly expand its work into later stages. When a stage is approved, preserve the accepted contract and update it only through an explicit documented decision.
