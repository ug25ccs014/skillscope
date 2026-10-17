# Frontend motion graphics (Stage 15, part 1)

All motion is decorative and is driven by real data already returned by the API. Nothing is simulated.
Every animation is disabled under `prefers-reduced-motion`, and the same information is always present as text.

| Component | File | Driven by | What it shows | Reduced-motion behaviour |
|---|---|---|---|---|
| RoadmapBus | `frontend/src/motion/RoadmapBus.tsx` | `plan.actions` from `GET /api/pathway-plans/{id}` | A bus drives along a winding road and halts at each stop (door opens, passengers hop out, stop pulses). One stop = one saved plan step, in order. Stop spacing is decorative, not a time estimate. | No auto-ride; the bus jumps between stops with Previous/Next or by clicking a stop. |
| ConfidenceGauge | `frontend/src/motion/ConfidenceGauge.tsx` | `evidence_confidence` (low / moderate / high) | Three segments fill in sequence. It is an evidence-strength indicator, not a percentage and not a chance of success. | Segments appear filled without animation. |
| ModeCompass | `frontend/src/motion/ModeCompass.tsx` | `calibration.age_mode` | Needle swings to the *starting* mode (Discover / Explore / Develop). Modes remain reversible. | Needle placed without swing. |
| RevealOnScroll | `frontend/src/motion/RevealOnScroll.tsx` | viewport position | Sections fade/slide in once. | Shown immediately. |

Keyframes and transitions live at the bottom of `frontend/src/index.css`.

## Known limits
- Animation timing (rAF loop in RoadmapBus) has not been exercised in a real browser in the build environment. It was syntax-checked and server-side rendered only.
- The bus is drawn for 1–8+ stops; very long plans compress the stop spacing (the chip list below the road remains readable).


## Motion layer M0 to M2 (2026-10-17)

| Piece | File | What it does | Fallback / how to disable |
|---|---|---|---|
| Motion preference | `motion/useMotionPreference.ts` | Reports reduced-motion, low-power, save-data, WebGL support, fine pointer, and the combined `allow3D` / `allowSmoothScroll` flags | Test with `?motion=off` (acts like reduced motion), `?webgl=off`, or `localStorage.skillscope_motion = 'off' \| 'nowebgl'` |
| Smooth scroll | `motion/SmoothScrollProvider.tsx` | Lenis driven by the GSAP ticker (`autoRaf: false`) | Not started when reduced motion, low power or Data Saver |
| Tokens and themes | `index.css`, `tailwind.config.js`, `motion/modeTheme.ts` | Duration/easing variables; per-mode colour variables that cross-fade | Colours switch instantly if the browser lacks `@property` |
| LazyCanvas | `motion/LazyCanvas.tsx` | Lazy WebGL slot; pauses off-screen and when the tab is hidden; error boundary; context-loss handler; static fallback | Renders only the fallback when disabled |
| Hero | `motion/ConstellationHero.tsx`, `ConstellationCanvas.tsx`, `ConstellationSvg.tsx` | Pinned, scroll-scrubbed 130-point constellation. Points settle into 4 clusters; one thread links a short path. `dpr` clamped to [1, 1.75]. Pointer parallax on desktop only (off for 10 to 14) | Still SVG, no pinning |
| Backdrop | `motion/GradientBackdrop.tsx` | Slow decorative glows in the mode colours | Static under reduced motion |
| Mode cards | `motion/ModeCards.tsx`, `TiltCard.tsx` | Three tilting cards (CSS perspective) with a pointer-following shine; native radio inputs | No tilt on touch or reduced motion |
| Empty states | `pages/PageParts.tsx` (`ProfileGate`) | Careers and Plan show an illustrated "create a profile first" page instead of a text notice. Preview shapes are labelled layout-only | n/a |
| Journey strip | `layout/JourneyStrip.tsx` | Six-step progress navigation shown on flow pages | n/a |

Age-aware calm: the 10 to 14 theme uses the slowest drift and heaviest scroll smoothing, and no pointer parallax.

Not done yet: M3 (flashcards), M4 (loop and ledger motion), M5 (graph), M6 (roadmap and polish), M7 (hardening, `docs/MOTION_SYSTEM.md`).

## M3 — Flashcard sections (2026-10-17)

| Piece | File | Driven by | Reduced motion / small screens |
|---|---|---|---|
| FlashStack | `motion/FlashStack.tsx` | Six descriptive journey steps (baseline, calibration, profile, challenge, evidence, next step). Not user data | Plain vertical list under 768 px or with reduced motion. All text stays in the DOM |
| FlipCard | `motion/FlipCard.tsx` | Real `/api/recommendations` response in `CareerRecommendations.tsx` | Instant face swap. Toggle is a `button` with `aria-pressed`; hidden face is `aria-hidden` and `inert` |

Flip card front: hypothesis label, category, qualitative confidence. Back: evidence used (or "Not enough evidence yet"), gaps, source record count, next validating action. No percentage fit is shown. The previous full card is still reachable under "Full detail, sources and limitations".
Not built: the optional draggable deck for 10 to 14 (needs the `motion` package; deferred).
