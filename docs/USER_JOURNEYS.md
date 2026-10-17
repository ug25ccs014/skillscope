# Stage 14 — User journeys, navigation, and information architecture

**Contract version:** `user-journey-v1.0`  
**Status:** Implemented and regression-tested within the local prototype scope.

## Purpose

SkillScope is presented as one continuous discovery-to-development journey rather than a set of disconnected tools. `JourneyNavigation.tsx` provides responsive, keyboard-accessible anchor navigation with a current-section indicator. The navigation stays available during scrolling and each major section has a stable target ID. On narrow screens the navigation can scroll horizontally rather than forcing links to wrap into a confusing multi-line menu.

## Primary journey

1. **Welcome and age-band entry** — `#top`. The user enters completed years, not a date of birth, and can request stateless entry calibration. The result is a suggested starting path, not a persisted profile or career verdict. From the result, the user proceeds to profile and consent.
2. **Consent and privacy** — `#evidence-ledger`. The profile is pseudonymous; the user reviews what is stored and confirms the age-appropriate consent basis. Under-18 guardian consent remains a self-attestation; the app explicitly states that it cannot verify identity or authority. No profile is created until that action is submitted.
3. **Baseline assessment** — `#baseline-assessment`. A saved profile can issue a short, nine-domain baseline. The current prompt is shown one at a time, users can go back or skip, and answers remain in the open page until final submission. The result shows exploratory/unknown domain status, not a normalized score. Network and validation failures provide an alert and leave the current draft available for retry while the page remains open.
4. **Evidence profile** — `#evidence-ledger` / `#profile-settings`. Students can review the profile and evidence count, add contextual evidence, correct entries, clear the history or delete the profile and history. Goal and age-band corrections retain the ledger's consent requirements.
5. **Daily challenge and reflection** — `#discovery-loop`. The student follows the current age-scaled activity, records observable output against its rubric, separately records enjoyment/difficulty/confidence/willingness, and provides an optional interpretation. Successful submission persists challenge and evidence together; the next task is derived from saved history.
6. **Career exploration and comparison** — `#career-recommendations`. The app presents provisional hypotheses, evidence matches, missing information, confidence context and a validating action. Mixed student-labelled evidence receives an explicit warning and a path back to validation instead of silent reconciliation.
7. **Pathway roadmap** — `#pathway-planner`. The plan can be generated or recalculated after a goal change, and includes age-appropriate actions, available source references, unknown requirements and history. Timelines are not promised unless the necessary adult planning inputs are supplied.
8. **Source and provenance review** — `#career-knowledge`. Career reference records show their source lineage, geography/version status, mapping uncertainty and catalog limitations. A stale, unavailable or unbuilt graph is an explicit source state—not permission to invent facts.
9. **Data review and settings** — `#profile-settings`. This target exists in the first-visit state as well as after profile creation and opens the same profile/consent/settings surface. Review, correction, evidence deletion and profile deletion remain discoverable through the primary navigation.

## State handling

| State | Expected user-facing behavior |
|---|---|
| First visit / no profile | Calibration preview remains available; baseline, discovery, recommendations and pathway tools explain the profile/consent prerequisite and link to it. |
| Consent not confirmed | The profile creation form requires its explicit confirmation. Validation feedback is shown in the form; no profile is silently created. |
| Loading | API-driven panels display a loading/status message and disable duplicate submit actions while a request is in progress. |
| Backend/API unavailable | The affected component shows a safe error plus a retry path. Stateless calibration stays distinct from saved profile state. |
| Empty evidence | Evidence summaries use `unknown`; recommendation/pathway panels explain that more activity is needed. |
| Baseline not started | A plain-language start panel explains duration, skip behavior, age band and non-diagnostic purpose. |
| Baseline submission failure | Error remains visible and responses remain in component state so the user can retry without re-answering while the current page is open. |
| Source graph not built / stale / offline | The career graph panel names its state and limitation; it does not fabricate occupation records. Profile/evidence/challenge flows remain separate from source-graph availability. |
| Conflicting/mixed evidence | Recommendation panel explicitly says the signals point in different directions, does not switch a goal automatically, and links to a validation activity. |
| Missing pathway plan | The planner shows a clear empty state and provides a generate action. |
| Goal changes | The planner recalculates from retained evidence; prior plans/goal history are not silently erased. |
| Profile deleted | Components subscribe to the profile-change event, clear their displayed profile-specific state and return to the no-profile entry state. |

## Navigation architecture

The fixed order reflects the user’s primary journey: **Start → Profile & consent → Baseline → Daily activity → Career options → Roadmap → Sources → Data & settings**. A student may revisit any section; the links are not rigid gates, except when the underlying API genuinely requires a saved and consent-confirmed profile. Anchor IDs are centralized in `JourneyNavigation.tsx` and listed in `data/user_journey_contract.json`.

Cross-step actions reinforce the sequence: calibration can continue to profile/consent; profile can continue to baseline; a completed baseline can continue to a challenge; a completed challenge can open career hypotheses; and career hypotheses can open the pathway plan. Source context remains inspectable from career cards and the plan.

## Safety and product boundaries

- The baseline is original exploratory content, not a validated psychometric instrument.
- Ages 10–14 see broad exploration rather than career rankings; the page does not add data-heavy visualizations to that experience.
- A reported curiosity value stays separate from rubric observations and is not an ability score.
- No reminders or background tracking are started by navigating between steps.
- Consent is not verified guardian identity. The unauthenticated prototype must not be deployed publicly with real student/minor data.
- A current graph is only a small curated source-linked snapshot. Source failures and missing Indian labor-market context remain visible.

## Validation and exit assessment

Automated contract tests verify that every required surface has a real implementation file and navigation anchor, that all declared transitions reference known surfaces, and that the required first-time/loading/offline/error/conflict states are represented. TSX syntax transpilation checks the changed frontend sources. A dependency-backed Vite build and browser-level interaction test remain unverified while npm dependencies cannot be installed in the environment; therefore this checkpoint validates the journey/navigation implementation, not a claim of production readiness.
