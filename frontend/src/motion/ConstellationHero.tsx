import { lazy, useRef } from 'react';
import { gsap, useGSAP } from './gsapSetup';
import LazyCanvas from './LazyCanvas';
import ConstellationSvg from './ConstellationSvg';
import { useMotionPreference } from './useMotionPreference';
import { useModeTheme } from './ModeContext';
import { toHref } from '../router';

const ConstellationCanvas = lazy(() => import('./ConstellationCanvas'));

const primary = 'inline-flex items-center justify-center gap-2 rounded-full bg-white px-7 py-3.5 text-sm font-bold text-ink shadow-glow transition hover:-translate-y-0.5 hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-white/40';
const secondary = 'inline-flex items-center justify-center rounded-full border border-white/30 bg-white/10 px-7 py-3.5 text-sm font-semibold text-white backdrop-blur transition hover:bg-white/20 focus:outline-none focus:ring-4 focus:ring-white/30';

// Three small floating cards. They only restate the product principles.
const floaters = [
  { text: 'Try something small', icon: 'M13 3 5 14h6l-1 7 8-11h-6l1-7Z', pos: 'left-0 top-4 float-soft', tint: 'from-amber-300 to-orange-400' },
  { text: 'Keep the evidence', icon: 'M4 19V9m6 10V5m6 14v-7m4 7H2', pos: 'right-0 top-[38%] float-soft [animation-delay:1.2s]', tint: 'from-teal-300 to-sky-400' },
  { text: 'See possibilities', icon: 'M5 12h14m-6-6 6 6-6 6', pos: 'left-6 bottom-2 float-soft [animation-delay:2.4s]', tint: 'from-indigo-300 to-violet-400' },
];

/**
 * Hero. No pinning and no scroll hijacking: the page scrolls normally.
 * The 3D constellation settles by itself in a few seconds. Without WebGL, with reduced motion,
 * low power or Data Saver it falls back to a still SVG and nothing is lost.
 */
export default function ConstellationHero() {
  const rootRef = useRef<HTMLElement | null>(null);
  const progressRef = useRef(0);
  const { allow3D, finePointer } = useMotionPreference();
  const { mode } = useModeTheme();

  useGSAP(() => {
    if (!allow3D) { progressRef.current = 0.85; return; }
    gsap.from('.hero-line', { y: 24, opacity: 0, duration: 0.8, ease: 'power3.out', stagger: 0.1, clearProps: 'all' });
    gsap.to(progressRef, { current: 0.85, duration: 5, ease: 'power2.inOut' });
  }, { scope: rootRef, dependencies: [allow3D] });

  return (
    <section ref={rootRef} aria-labelledby="home-heading" className="hero-stage relative isolate mt-4 overflow-hidden rounded-[2.5rem] text-white shadow-soft sm:mt-6">
      <LazyCanvas
        className="absolute inset-0 -z-10"
        enabled={allow3D}
        scene={ConstellationCanvas}
        sceneProps={{ progressRef, mode, parallax: finePointer }}
        fallback={<ConstellationSvg mode={mode} />}
      />
      <div aria-hidden="true" className="hero-vignette absolute inset-0 -z-10" />

      <div className="relative grid items-center gap-10 px-6 py-12 sm:px-10 sm:py-16 lg:min-h-[34rem] lg:grid-cols-[1.15fr_0.85fr] lg:px-14">
        <div>
          <div className="hero-line mb-6 inline-flex items-center gap-2 rounded-full border border-white/20 bg-white/10 px-3.5 py-2 text-sm font-medium text-white/90 backdrop-blur">
            <span className="h-2 w-2 rounded-full bg-[var(--mode-accent)]" /> Made for students aged 10 and up
          </div>
          <h1 id="home-heading" className="hero-line max-w-3xl font-display text-5xl font-semibold leading-[1.04] tracking-[-0.03em] sm:text-6xl lg:text-[4.25rem]">
            Discover what <span className="bg-gradient-to-r from-[var(--mode-a)] to-[var(--mode-c)] bg-clip-text text-transparent">you could become.</span>
          </h1>
          <p className="hero-line mt-5 max-w-xl text-base leading-7 text-white/85 sm:text-lg">
            Try small activities, collect real proof of what you enjoy, and turn it into your next steps.
          </p>
          <div className="hero-line mt-8 flex flex-wrap gap-3">
            <a href={toHref('/start')} className={primary}>
              Find my starting path
              <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="M5 12h14m-6-6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round" /></svg>
            </a>
            <a href={toHref('/careers')} className={secondary}>Browse careers</a>
          </div>
        </div>

        <div aria-hidden="true" className="relative mx-auto hidden h-80 w-full max-w-sm lg:block">
          <div className="absolute inset-6 rounded-[2.5rem] bg-gradient-to-br from-white/15 to-white/0 ring-1 ring-white/15 backdrop-blur-sm" />
          {floaters.map((item) => (
            <div key={item.text} className={`absolute ${item.pos} flex items-center gap-3 rounded-full bg-white/95 py-2.5 pl-2.5 pr-5 text-sm font-bold text-ink shadow-soft`}>
              <span className={`grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br ${item.tint} text-white`}>
                <svg viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={item.icon} /></svg>
              </span>
              {item.text}
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
