# SkillScope Visual Design System

**Introduced:** Stage 15 · **Scope:** responsive frontend design and interaction consistency.

## Product design principles

1. **Evidence before conclusions.** A screen should state whether information is user-reported, an observed challenge result, a source-linked occupational fact, or a heuristic interpretation.
2. **Explore without fixing a label.** Ages 10–14 see broad activities and plain language; ages 15–17 see validation and alternatives; adults can inspect deeper context and practical planning inputs. These are the same product, not separate applications.
3. **Progressive disclosure.** Keep the primary action and immediate context visible; place source lineage, limitations, and detailed confidence dimensions in disclosures when that reduces clutter.
4. **Calm, readable hierarchy.** A pale neutral canvas, dark ink, teal for actions/evidence navigation, and restrained indigo/amber for distinctions and cautions. Do not use decoration as a substitute for data.
5. **Unknown remains unknown.** Empty, unavailable, stale, skipped, mixed, and not-yet-documented states must be rendered explicitly and never disguised as zero or a negative result.

## Shared tokens

| Token | Value | Use |
|---|---|---|
| `--ss-ink` | `#12243a` | Primary headings and body emphasis |
| `--ss-canvas` | `#f5f8fb` | App/page canvas |
| `--ss-surface` | `#ffffff` | Reading and form surfaces |
| `--ss-line` | `#dce5ed` | Quiet dividers and card edges |
| `--ss-teal` | `#117369` | Primary action / evidence accent |
| `--ss-indigo` | `#4338a8` | Secondary classification accent |
| `--ss-focus` | `#087f73` | Keyboard focus indicator |
| `--ss-radius-card` | `1.25rem` | Main panels |

Contrast ratios were calculated from these color values using the WCAG relative-luminance formula. Ink on white is approximately 15.68:1; teal on white 5.71:1; indigo on white 8.86:1; and the focus teal on white 4.89:1. The low-contrast Tailwind `text-slate-400` utility is darkened in the global stylesheet to `#5c6b7d` for metadata on light surfaces (approximately 5.45:1 on white). This does not substitute for a rendered contrast audit of every semantic/state combination.

## Layout and responsive behavior

- The app shell provides the shared page width and horizontal inset. Embedded section components no longer add a second `max-width + horizontal padding` layer that made the lower sections narrower than the intro.
- Primary content sections use common borders and vertical rhythm, and each section has a stable anchor offset below the sticky navigation.
- Main content grids stack by default and introduce columns at Tailwind `sm`, `md`, `lg`, or `xl` breakpoints only where the component has enough width.
- Inputs are shrink-safe; metadata and long user/source text can wrap rather than widening the page.
- On viewports up to 640 CSS pixels, text inputs use a 16px font (avoiding browser auto-zoom) and buttons have a minimum 42px height. The sticky navigation remains horizontally scrollable rather than squeezing links into unreadable sizes.

## Accessibility behaviors

- All links and controls receive a consistent visible `:focus-visible` outline.
- Section navigation uses real anchors and an `aria-current` state; state messages use existing `aria-live`, `role="status"`, and `role="alert"` patterns.
- Reduced-motion preferences disable smooth scrolling and minimize animation/transition duration.
- Form controls retain their visible labels, and checkboxes/radios use the primary accent color.
- No chart is drawn from demo constants as if it were live profile data. Counts shown in the interface come from backend responses and are accompanied by source/coverage limitations where relevant.

## Shared classes

- `.ss-app-shell`: restrained canvas gradients.
- `.ss-site-header`: shared header divider.
- `.ss-section`: min-width protection for anchored page sections.
- `.ss-section-kicker`: compact, uppercase section eyebrow style.
- `.ss-panel`: consistent surface, edge, radius, and low-elevation shadow.
- `.ss-panel--quiet`: lower-emphasis surface.
- `.ss-panel--hero`: larger intro-panel radius.

The frontend remains React + TypeScript + Vite + Tailwind. Shared component rewrites and a new component library were deliberately avoided in this stage to keep scope limited and minimize risk to the working API flows.
