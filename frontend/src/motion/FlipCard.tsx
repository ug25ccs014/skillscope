import { useId, useState, type ReactNode } from 'react';
import { useMotionPreference } from './useMotionPreference';

/**
 * A two-faced card. The toggle is a real <button> with aria-pressed. The hidden face is aria-hidden and inert,
 * so screen readers read, and keyboards reach, only the visible face. Under reduced motion the faces swap instantly.
 */
export default function FlipCard({ front, back, frontLabel, backLabel, className = '' }: {
  front: ReactNode; back: ReactNode; frontLabel: string; backLabel: string; className?: string;
}) {
  const [flipped, setFlipped] = useState(false);
  const { reducedMotion } = useMotionPreference();
  const id = useId();
  const toggle = () => setFlipped((value) => !value);

  return (
    <div className={`flip-scene ${reducedMotion ? 'flip-reduced' : ''} ${className}`}>
      <div className={`flip-inner ${flipped ? 'flip-on' : ''}`} onClick={(event) => { if ((event.target as HTMLElement).closest('a,button')) return; toggle(); }}>
        <div id={`${id}-front`} className="flip-face" data-hidden={flipped} aria-hidden={flipped} inert={flipped}>{front}</div>
        <div id={`${id}-back`} className="flip-face flip-back" data-hidden={!flipped} aria-hidden={!flipped} inert={!flipped}>{back}</div>
      </div>
      <button
        type="button" onClick={toggle} aria-pressed={flipped} aria-controls={`${id}-front ${id}-back`}
        className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-teal-300 hover:text-teal-800 focus:outline-none focus:ring-4 focus:ring-teal-500/20"
      >
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 12a8 8 0 0 1 14-5.3L20 9M20 4v5h-5M20 12a8 8 0 0 1-14 5.3L4 15M4 20v-5h5" /></svg>
        {flipped ? backLabel : frontLabel}
      </button>
    </div>
  );
}
