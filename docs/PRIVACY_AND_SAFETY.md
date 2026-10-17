# SkillScope Privacy, Safety, Security, Fairness and Accessibility Checklist

**Status:** Stage 18 prototype safety baseline. This document is an implementation checklist, not a certification, privacy policy for public launch, or legal opinion.

> **DEMO ONLY. Do not enter real student or child data.** Under-18 consent is a self-attestation and is not identity-verified. Public deployment and use with real student/minor records are blocked until the release gates below are met.

## 1. Data minimization and inventory

| Data | Why the prototype needs it | Current storage | Safeguard / limitation |
|---|---|---|---|
| Age band, not date of birth | Pick the age-appropriate journey | Student profile in SQLite | No full DOB is requested or required. |
| Optional goal and learning context | Tailor challenge and plan explanations | Profile and timestamped goal evidence | Optional, bounded free text; avoid identifying or sensitive details. |
| Challenge output, rubric observations, reflection and self-ratings | Preserve one contextual activity observation | Evidence ledger and challenge submission tables | Separate observed performance from interest/enjoyment/difficulty; bounded input lengths. |
| Baseline answers | Produce an exploratory starting snapshot | Baseline response/evidence tables | Skips remain unknown; baseline is not a validated psychometric instrument. |
| Preferences and action-plan/recommendation snapshots | Continue the user's requested journey and preserve version history | SQLite | Deleted with the profile by foreign-key cascades where schemas apply. |
| Profile locator | Reopen the selected local profile | Browser local storage | A locator is not authentication or authorization. |
| Project reference URL | Let the user identify a project they chose to share | Evidence record | User-provided reference only; the app does not scrape or fetch the student's account. |

No name, school identifier, precise date of birth, email address, or telephone number is needed for the MVP. Selected narrative fields reject obvious email and phone/long-number patterns. This check is intentionally limited and **is not a comprehensive sensitive-data detector**; it cannot guarantee that all identifying or sensitive details are removed from prose.

## 2. Purpose limitation and prohibited inference

- Student-entered profile/evidence data is used for the local discovery loop, explanation, recommendations and pathway planning only.
- There are no schema fields or recommendation dimensions for health, disability, religion, caste, sexuality, political views, or other sensitive traits. The engine must not infer or store these characteristics.
- Do not label a child's character, fix a student's identity, or narrow future opportunities based on activity behavior.
- Distinguish interest, rubric-observed performance, experience/exposure, learning progress, stated goal, practical readiness and reported effort/difficulty.
- Lack of evidence or access is unknown/lack of exposure, not low capability. Do not score individual potential using aggregate labour-market data.
- The core recommendation engine is deterministic and local. No external LLM receives student/profile data by default; no LLM is required for the core loop.
- Do not scrape social media, code repositories, school systems, or other third-party accounts. Any future connector must be user-initiated, narrowly scoped, consented, permissioned under provider terms and independently security-reviewed.

## 3. Consent and child safety

- Profile creation API validation requires explicit consent confirmation and the age-appropriate basis: guardian-confirmed for ages 10–17 and student-confirmed for adults.
- The UI must show the conspicuous demo-only notice before profile creation, explain what is stored and how to correct/delete it, and state that a guardian confirmation is not independently verified.
- This is only a recorded self-attestation; it does **not** prove the identity, authority, or legal consent of a guardian. Do not use real children's data in this hackathon prototype.
- Repeated in-product behavior may only be recorded with per-interaction confirmation and named activity/time-window context. Background monitoring is not implemented.
- When age correction crosses the minor/adult consent boundary, existing evidence prevents silent relabeling; the user is directed to delete and recreate the profile with the correct consent basis.
- No diagnosis, clinical assessment, personality label, aptitude verdict, or career outcome prediction is produced.

## 4. Review, correction and deletion

- Users can view and correct profile fields and evidence items.
- Users can permanently delete an individual evidence item, all evidence (which also clears the profile's current goal/context), or the entire profile.
- Foreign-key cascades are intended to remove profile-linked evidence, baseline assessments/responses, challenge submissions, preferences, pathway plans, recommendation snapshots and demo-fixture references when the profile is deleted.
- A local development database, filesystem snapshots, logs from external infrastructure, backups and downloaded artifacts may have different retention behavior. The prototype has no automatic retention scheduler, DSAR workflow, or verified export/erasure orchestration; production operations must cover them.
- The browser's stored profile locator is removed after successful profile deletion. It is not a secure session token.

## 5. Security baseline implemented in Stage 18

- API request-validation errors omit submitted values; selected free-text schemas reject obvious email/phone/long numeric identifiers.
- Application error logs record request IDs, route templates and exception types rather than exception contents or request bodies. External server/access logs still need deployment-specific review and path/query redaction.
- Standard response headers include `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`, and restrictive `Permissions-Policy`; private data responses are `no-store`.
- Production CORS requires explicitly configured HTTPS origins; development localhost origins are not silently defaulted into production.
- **Student-data routes fail closed with HTTP 503 when `SKILLSCOPE_ENV=production`** until authenticated identity, per-profile authorization and verified consent exist. This is a deployment guard, not authentication.
- Inputs use bounded lengths, typed enums, `extra='forbid'` on core contracts, range limits, timezone checks and field/cross-field validation. The URL reference field stores user-entered URLs but does not fetch them.
- Secrets belong in deployment environment/secret management, never committed `.env` files. Keep `SKILLSCOPE_SEED_DEMO=false` in production and never use real student records as fixtures.

## 6. Fairness and inclusion

- Do not rank by school name/prestige, gender, caste, religion, disability, income, precise location or ability to pay.
- A chosen goal is one hypothesis, not an instruction to suppress alternatives.
- For minors, use broad exploration and supportive language. A single low performance result must not lower a student's general potential; repeated poor results with high enjoyment and high results with low enjoyment remain different signals.
- Recommendations should expose gaps and unknowns, propose accessible/low-material alternatives, and preserve a student's ability to reject a hypothesis or change goals.
- Evidence confidence is qualitative evidence sufficiency; it is not the probability of career success, and the prototype has not been validated for outcomes or fairness.

## 7. Accessibility checklist

- [x] Primary sections have explicit accessible names (`aria-labelledby`).
- [x] Inputs use visible labels; the consent checkbox references the privacy notice.
- [x] Asynchronous errors use `role="alert"`; status/success regions use `role="status"` where implemented.
- [x] Focus-visible outlines, keyboard-operable native inputs/disclosures, reduced-motion CSS and small-screen layout tokens are present.
- [x] Muted small text uses a higher-contrast override; primary text/focus colors have a source-level WCAG AA contrast test.
- [ ] A real screen-reader/keyboard audit across supported browsers has not been completed.
- [ ] A browser-rendered desktop/mobile visual and end-to-end audit has not been completed because frontend dependencies could not be installed here.

## 8. Tested Stage 18 requirements

- [x] Adult/minor consent gate; wrong/missing guardian basis rejected.
- [x] Profile/evidence deletion and dependent-record deletion cascade verified against SQLite foreign keys.
- [x] Oversized/unknown fields and obvious email/phone identifiers rejected without persistence; validation response does not echo the submitted identifier.
- [x] Production mode blocks student-data endpoints until authorization/verified consent exists.
- [x] Security headers, `no-store` behavior, production CORS validation and route/exception log redaction verified.
- [x] UI contract tests check the visible demo-only privacy notice, consent description, labels, section names, focus-visible, reduced motion, and alert/status patterns.

## 9. Mandatory production release gates — not yet met

- [ ] Implement authenticated identities, role/guardian relationships, ownership checks for every student-scoped read/write/delete, session lifecycle and abuse/rate limiting. UUID possession must never be treated as authorization.
- [ ] Independently verify guardian authority/consent when required, document student/guardian rights, withdrawal and retention procedures, and validate consent records with legal/privacy reviewers.
- [ ] Review the then-current Indian DPDP framework and rules plus every other applicable jurisdiction with qualified counsel before release. **No legal compliance review has been performed for this checkpoint.**
- [ ] Establish and test data retention, backups, deletion from backups, export/correction/erasure request workflows, encryption in transit/at rest, secret rotation, incident response and deployment log policy.
- [ ] Threat-model uploads/connectors, verify provider permissions/terms before any integration, and independently review all outbound network/LLM paths.
- [ ] Perform security testing/penetration testing, accessibility audit with assistive technology, and an age-stratified consent-based usability/fairness pilot.
- [ ] Validate recommendations using a documented research design. A passing software test suite does not establish psychometric validity, fairness or real-world career outcomes.

**Release decision:** Not approved for public deployment or real student/minor data. Stage 18 closes the demo safeguards and test exit gate; it does not claim regulatory compliance or production readiness.


## Stage 20 handoff note (2026-10-17)

The repeatable judging walkthrough uses synthetic fixtures only and refuses non-loopback hosts by default. That is a risk-reduction measure for rehearsal, not a substitute for authentication or authorization. Production student-data APIs continue to fail closed when `SKILLSCOPE_ENV=production` until the required identity, ownership and verified-consent controls exist. The Stage 19 validation suite is not a privacy certification and is not evidence of psychometric or career-outcome validity. See `docs/VALIDATION_REPORT.md` for the precise verification boundary.
