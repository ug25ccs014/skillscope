import { useState } from 'react';
import TiltCard from './TiltCard';
import { MODE_ORDER, MODES, type ModeKey } from './modeConfig';
import { useModeTheme } from './ModeContext';

const descriptions: Record<ModeKey, string> = {
  discover: 'Short, safe activities to find what you enjoy.',
  explore: 'Test your interests and spot hidden strengths.',
  develop: 'Check your direction and close skill gaps.',
};

/** Decorative shape per mode: rounder for 10–14, more geometric for 18+. */
function ModeGlyph({ mode }: { mode: ModeKey }) {
  const { palette } = MODES[mode];
  return (
    <svg aria-hidden="true" viewBox="0 0 120 64" className="h-24 w-full" fill="none">
      <rect width="120" height="64" rx="20" fill={`url(#g-${mode})`} />
      <defs>
        <linearGradient id={`g-${mode}`} x1="0" y1="0" x2="120" y2="64" gradientUnits="userSpaceOnUse">
          <stop stopColor={palette.a} stopOpacity=".95" /><stop offset=".55" stopColor={palette.b} stopOpacity=".9" /><stop offset="1" stopColor={palette.c} stopOpacity=".95" />
        </linearGradient>
      </defs>
      {mode === 'discover' ? <g fill="#fff" fillOpacity=".55"><circle cx="30" cy="34" r="16" /><circle cx="62" cy="26" r="10" /><circle cx="90" cy="38" r="14" /></g> : null}
      {mode === 'explore' ? <g stroke="#fff" strokeOpacity=".75" strokeWidth="2" strokeLinecap="round"><path d="M18 44 L48 22 L74 38 L102 16" /><g fill="#fff"><circle cx="18" cy="44" r="4" /><circle cx="48" cy="22" r="4" /><circle cx="74" cy="38" r="4" /><circle cx="102" cy="16" r="4" /></g></g> : null}
      {mode === 'develop' ? <g stroke="#fff" strokeOpacity=".8" strokeWidth="2"><path d="M20 48 H46 V30 H72 V14 H100" strokeLinejoin="miter" /><g fill="#fff"><rect x="16" y="44" width="8" height="8" /><rect x="42" y="26" width="8" height="8" /><rect x="68" y="10" width="8" height="8" /></g></g> : null}
    </svg>
  );
}

/**
 * Three selectable cards that preview each mode's look. Native radio inputs give arrow-key navigation,
 * labels and a focus ring. Choosing a card only changes the visual theme; the real starting path comes from the Start page.
 */
export default function ModeCards() {
  const { mode, setMode } = useModeTheme();
  const [focused, setFocused] = useState<ModeKey | null>(null);

  return (
    <fieldset className="m-0 border-0 p-0">
      <legend className="sr-only">Preview the look of a starting mode</legend>
      <div className="grid gap-4 md:grid-cols-3">
        {MODE_ORDER.map((key) => {
          const info = MODES[key];
          const selected = mode === key;
          return (
            <label key={key} className="mode-card-label block cursor-pointer">
              <input
                type="radio" name="mode-preview" value={key} checked={selected} className="sr-only"
                onChange={() => setMode(key)}
                onFocus={(event) => setFocused(event.currentTarget.matches(':focus-visible') ? key : null)}
                onBlur={() => setFocused((current) => (current === key ? null : current))}
              />
              <TiltCard className={`rounded-[2rem] border bg-white p-4 shadow-sm transition-shadow ${selected ? 'border-transparent shadow-soft ring-2 ring-ink' : 'border-slate-200/80'} ${focused === key ? 'outline outline-4 outline-offset-2 outline-teal-500/50' : ''}`}>
                <ModeGlyph mode={key} />
                <div className="mt-4 flex items-center justify-between gap-2 px-1">
                  <span className="inline-block rounded-full bg-slate-100 px-3.5 py-1.5 text-sm font-bold text-ink">{info.ages}</span>
                  {selected ? <span className="inline-flex items-center gap-1 text-xs font-semibold text-ink"><svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.4"><path d="m5 12 5 5 9-10" strokeLinecap="round" strokeLinejoin="round" /></svg>Previewing</span> : null}
                </div>
                <h3 className="mt-3 px-1 font-display text-2xl font-semibold text-ink">{info.title}</h3>
                <p className="mt-1.5 px-1 pb-2 text-sm leading-6 text-slate-600">{descriptions[key]}</p>
              </TiltCard>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
