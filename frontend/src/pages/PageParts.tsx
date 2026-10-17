import { useEffect, useState, type ReactNode } from 'react';
import { toHref } from '../router';

export function PageHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return (
    <div className="max-w-3xl pb-2 pt-10 lg:pt-14">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">{eyebrow}</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">{title}</h1>
      {children ? <p className="mt-4 text-base leading-7 text-slate-600">{children}</p> : null}
    </div>
  );
}

/** Closing call-to-action that moves the visitor to the next page of the journey. */
export function NextStep({ to, label, blurb }: { to: string; label: string; blurb: string }) {
  return (
    <div className="mb-14 mt-6 flex flex-col gap-4 rounded-[2rem] border border-white bg-gradient-to-br from-teal-50 via-white to-indigo-50 p-6 shadow-sm sm:flex-row sm:items-center sm:justify-between sm:px-8">
      <div><p className="text-xs font-bold uppercase tracking-[0.14em] text-teal-700">Continue</p><p className="mt-1 text-sm leading-6 text-slate-600">{blurb}</p></div>
      <a href={toHref(to)} className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-ink px-6 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/20">{label}
        <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14m-6-6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round" /></svg></a>
    </div>
  );
}

const PROFILE_STORAGE_KEY = 'skillscope_student_evidence_profile_v1';

/** True when this browser holds a saved profile locator. Updates when a profile is created or deleted on any page. */
export function useSavedProfile(): boolean {
  const read = () => { try { return Boolean(window.localStorage.getItem(PROFILE_STORAGE_KEY)); } catch { return false; } };
  const [has, setHas] = useState(read);
  useEffect(() => {
    const update = () => setHas(read());
    window.addEventListener('skillscope-profile-changed', update);
    window.addEventListener('storage', update);
    return () => { window.removeEventListener('skillscope-profile-changed', update); window.removeEventListener('storage', update); };
  }, []);
  return has;
}

const gateCopy = {
  careers: {
    eyebrow: 'Career possibilities',
    title: 'Possibilities need evidence first.',
    body: 'Create a profile and add what you have tried. Then you will see career ideas, with the reasons behind each one.',
  },
  plan: {
    eyebrow: 'Pathway plan',
    title: 'Your plan starts from your own goal.',
    body: 'Create a profile, then turn a career idea into small steps you can change any time.',
  },
} as const;

/** Ghost layout previews. They are drawn shapes only: no data, no career names, no scores. */
function CareersGhost() {
  return (
    <div className="grid gap-3 sm:grid-cols-3" aria-hidden="true">
      {[0, 1, 2].map((n) => (
        <div key={n} className="rounded-2xl border border-dashed border-slate-300 bg-white/70 p-4">
          <div className="h-3 w-2/3 rounded-full bg-slate-200" />
          <div className="mt-3 h-2 w-full rounded-full bg-slate-100" />
          <div className="mt-2 h-2 w-4/5 rounded-full bg-slate-100" />
          <div className="hatch mt-5 h-2.5 rounded-full" />
          <p className="mt-2 text-[11px] font-semibold text-slate-500">Not enough evidence yet</p>
        </div>
      ))}
    </div>
  );
}

function PlanGhost() {
  return (
    <svg viewBox="0 0 560 120" className="h-28 w-full" aria-hidden="true" fill="none">
      <path className="dash-flow" d="M20 80 C 110 20, 170 110, 270 60 S 460 20, 540 70" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" />
      {[[20, 80], [150, 66], [270, 60], [400, 52], [540, 70]].map(([x, y], i) => (
        <g key={i}><circle cx={x} cy={y} r="11" fill="#fff" stroke="#cbd5e1" strokeWidth="3" /><text x={x} y={y + 4} textAnchor="middle" fontSize="11" fontWeight="700" fill="#94a3b8">{i + 1}</text></g>
      ))}
    </svg>
  );
}

/** Shown instead of a page that needs a saved profile, so the page is never a dead end. */
export function ProfileGate({ kind }: { kind: keyof typeof gateCopy }) {
  const copy = gateCopy[kind];
  return (
    <section className="relative py-12 sm:py-16" aria-labelledby="gate-heading">
      <div className="overflow-hidden rounded-[2.5rem] border border-white bg-white/80 p-6 shadow-soft backdrop-blur sm:p-10">
        <div className="grid gap-8 lg:grid-cols-[1fr_1.1fr] lg:items-center">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">{copy.eyebrow}</p>
            <h1 id="gate-heading" className="mt-2 font-display text-4xl font-semibold leading-tight tracking-tight text-ink sm:text-5xl">{copy.title}</h1>
            <p className="mt-4 text-base leading-7 text-slate-600">{copy.body}</p>
            <div className="mt-7 flex flex-wrap gap-3">
              <a href={toHref('/profile')} className="inline-flex items-center justify-center rounded-full bg-ink px-6 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/20">Create my profile</a>
              <a href={toHref('/challenges')} className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-6 py-3 text-sm font-semibold text-slate-800 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-teal-500/20">Try a challenge first</a>
              
            </div>
          </div>
          <div className="float-soft rounded-[2rem] border border-slate-100 bg-gradient-to-br from-teal-50 via-white to-indigo-50 p-6">
            {kind === 'careers' ? <CareersGhost /> : <PlanGhost />}
            
          </div>
        </div>
      </div>
    </section>
  );
}
