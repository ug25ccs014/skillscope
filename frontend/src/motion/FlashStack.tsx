import { useEffect, useRef, useState } from 'react';
import { gsap, ScrollTrigger, useGSAP } from './gsapSetup';
import { useMotionPreference } from './useMotionPreference';

/** The six steps of the real journey from the Product Contract. Descriptive content, not a user's data. */
const steps = [
  { title: 'Baseline', text: 'A short, skippable set of prompts across nine domains. Anything skipped stays unknown, never zero.', icon: 'M5 4h14v16H5zM9 9h6M9 13h6M9 17h3' },
  { title: 'Calibration', text: 'Your age, what you have tried and how clear your direction is set where you begin. Not saved.', icon: 'M12 3v18M3 12h18M12 12l5-5' },
  { title: 'Profile', text: 'With your consent, record goals and activities. You can correct or delete anything.', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0' },
  { title: 'Challenge', text: 'A short activity with a visible rubric. Your own reflection is kept separate from the score.', icon: 'M13 3 5 14h6l-1 7 8-11h-6l1-7Z' },
  { title: 'Evidence', text: 'Each result is added as a timestamped observation. One result never becomes a fixed label.', icon: 'M4 19V9m6 10V5m6 14v-7m4 7H2' },
  { title: 'Next step', text: 'Possibilities with reasons, gaps and sources, plus a small action you can revise.', icon: 'M5 12h14m-6-6 6 6-6 6' },
];

function useWide(): boolean {
  const query = '(min-width: 768px)';
  const [wide, setWide] = useState(() => typeof window !== 'undefined' && typeof window.matchMedia === 'function' && window.matchMedia(query).matches);
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const media = window.matchMedia(query);
    const update = () => setWide(media.matches);
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);
  return wide;
}

function StepCard({ index, step }: { index: number; step: (typeof steps)[number] }) {
  return (
    <div className="flex h-full flex-col justify-between overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-soft">
      <div className="h-2 w-full" style={{ background: 'linear-gradient(90deg, var(--mode-a), var(--mode-b), var(--mode-c))' }} />
      <div className="p-6 sm:p-8">
        <div className="flex items-center justify-between">
          <span className="grid h-12 w-12 place-items-center rounded-2xl bg-slate-100 text-ink">
            <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={step.icon} /></svg>
          </span>
          <span className="text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Step {index + 1} of {steps.length}</span>
        </div>
        <h3 className="mt-6 font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">{step.title}</h3>
        <p className="mt-3 max-w-xl text-base leading-7 text-slate-600">{step.text}</p>
      </div>
    </div>
  );
}

/**
 * Pinned stack of six cards. As the page scrolls, the top card flies off and the next scales into place.
 * On small screens or with reduced motion it is a plain vertical list. All text is always in the DOM.
 */
export default function FlashStack() {
  const rootRef = useRef<HTMLDivElement | null>(null);
  const { reducedMotion } = useMotionPreference();
  const wide = useWide();
  const stacked = wide && !reducedMotion;

  useGSAP(() => {
    const root = rootRef.current;
    if (!root || !stacked) return;
    const cards = gsap.utils.toArray<HTMLElement>('.stack-card', root);
    const n = cards.length;
    const place = (depth: number) => ({ scale: 1 - 0.05 * Math.min(depth, 2), y: 20 * Math.min(depth, 2), opacity: depth <= 2 ? 1 - 0.3 * depth : 0 });
    cards.forEach((card, i) => gsap.set(card, { ...place(i), zIndex: n - i }));

    const tl = gsap.timeline({ scrollTrigger: { trigger: root, start: 'top 90px', end: `+=${(n - 1) * 70}%`, pin: true, scrub: 0.6, anticipatePin: 1 } });
    for (let k = 0; k < n - 1; k += 1) {
      tl.to(cards[k], { xPercent: 120, rotate: k % 2 ? -9 : 9, opacity: 0, duration: 1, ease: 'power2.in' }, k);
      for (let j = k + 1; j < n; j += 1) tl.to(cards[j], { ...place(j - k - 1), duration: 1, ease: 'none' }, k);
    }
    const refresh = window.setTimeout(() => ScrollTrigger.refresh(), 500);
    return () => window.clearTimeout(refresh);
  }, { scope: rootRef, dependencies: [stacked] });

  if (!stacked) {
    return (
      <ol className="grid gap-4 sm:grid-cols-2" aria-label="The six steps of the SkillScope journey">
        {steps.map((step, i) => <li key={step.title}><StepCard index={i} step={step} /></li>)}
      </ol>
    );
  }
  return (
    <div ref={rootRef} className="mx-auto w-full max-w-3xl">
      <ol className="relative h-[22rem]" aria-label="The six steps of the SkillScope journey">
        {steps.map((step, i) => <li key={step.title} className="stack-card absolute inset-0 will-change-transform"><StepCard index={i} step={step} /></li>)}
      </ol>
      <p aria-hidden="true" className="mt-5 text-center text-xs font-semibold text-slate-500">Keep scrolling to turn the cards</p>
    </div>
  );
}
