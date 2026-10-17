# Site map and navigation

The frontend is a multi-page single-page app using hash routes (`#/path`), so it needs no server rewrite rules.
Routing lives in `frontend/src/router.ts`; the shell (header, mobile menu, backend status, footer) is `frontend/src/layout/SiteLayout.tsx`.

| Route | Page | Purpose | Backend data |
|---|---|---|---|
| `#/` | Home | What SkillScope is, the three age modes, an overview journey (animated bus), honesty principles, call to action | none |
| `#/start` | Start | Age-aware entry calibration. Not saved. | `POST /api/calibration` |
| `#/profile` | Profile | Consent-aware evidence profile, evidence capture, corrections, deletion | `/api/student-profiles/*` |
| `#/challenges` | Challenges | Age-scaled challenge, rubric scoring, separate reflection, next activity | `/api/discovery-loop/*`, challenges |
| `#/careers` | Careers | Evidence-based possibility cards with confidence, gaps, sources | `GET /api/recommendations/{id}` |
| `#/plan` | Plan | Editable goal, pathway comparison, ordered steps (bus roadmap), history | `/api/pathway-plans/*` |
| `#/sources` | Sources & privacy | Cited career knowledge graph, data status, privacy notes | `/api/knowledge-graph/*` |

## Journey and states
- Each flow page ends with a "Continue" card linking to the next page (Start → Profile → Challenges → Careers → Plan → Sources & privacy).
- Pages that need a profile show a notice with a link to the Profile page when none exists.
- Header shows live backend status; a red banner with a retry button appears when the backend is unreachable.
- Unknown routes show a "Page not found" page. Route changes update the document title, scroll to top and move focus to the main content. A skip link is provided.
- Mobile: the nav collapses into a menu button (closes on navigation or Escape).

## Not yet verified
Not exercised in a real browser: mobile/desktop layout audit, keyboard walkthrough and the full journey with a running backend.
