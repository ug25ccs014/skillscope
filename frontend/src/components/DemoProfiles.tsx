import { useState } from 'react';
import TiltCard from '../motion/TiltCard';
import RevealOnScroll from '../motion/RevealOnScroll';
import { useModeTheme } from '../motion/ModeContext';
import { MODES, type ModeKey } from '../motion/modeConfig';
import { usePersistenceStatus } from './PersistencePanel';
import { toHref } from '../router';

const PROFILE_STORAGE_KEY = 'skillscope_student_evidence_profile_v1';
const bandToMode: Record<string, ModeKey> = { '10_14': 'discover', '15_17': 'explore', '18_plus': 'develop' };
const bandBlurb: Record<string, string> = {
  '10_14': 'Broad, gentle exploration. No career label is offered.',
  '15_17': 'Starts from a stated goal with little evidence, then tests it with a baseline and contrasting challenges.',
  '18_plus': 'A clearer target: look at skill gaps and practical next actions.',
};

const loopSteps = [
  { to: '/challenges', title: 'Do one challenge', line: 'Open the recommended activity and add a reflection.' },
  { to: '/profile', title: 'Watch the ledger grow', line: 'The evidence count goes up by one, with its own timestamp.' },
  { to: '/challenges', title: 'See the next step change', line: 'The next activity shows why it was chosen now.' },
  { to: '/careers', title: 'Trace a recommendation', line: 'Open the audit trail from your evidence to cited sources.' },
];

export default function DemoProfiles({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { data, error, loading, reload } = usePersistenceStatus(apiBaseUrl);
  const { setMode } = useModeTheme();
  const [chosen, setChosen] = useState<string | null>(null);

  const selectProfile = (profileId: string, band: string) => {
    try { window.localStorage.setItem(PROFILE_STORAGE_KEY, profileId); } catch { /* storage may be blocked */ }
    window.dispatchEvent(new Event('skillscope-profile-changed'));
    setMode(bandToMode[band] ?? 'explore');
    setChosen(band);
  };

  const fixtures = (data?.demo_fixtures ?? []) as Array<{ fixture_id: string; profile_id?: string; age_band: string; evidence_count: number; challenge_submission_count: number; description?: string }>;

  return (
    <section className="ss-section py-12 sm:py-16" aria-labelledby="demo-heading">
      <div className="max-w-3xl">
        <p className="ss-section-kicker text-xs font-bold uppercase tracking-[0.18em] text-amber-800">Demo</p>
        <h1 id="demo-heading" className="mt-2 font-display text-4xl font-semibold tracking-tight text-ink sm:text-5xl">Try SkillScope with a made-up student.</h1>
        <p className="mt-4 text-base leading-7 text-slate-600">Pick one of three synthetic profiles, one for each starting path. They are invented for demonstrations. Using one never touches real information.</p>
      </div>

      <div role="note" className="demo-badge mt-6 rounded-2xl border border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-950"><p className="font-bold">Synthetic demo data</p><p className="mt-1">These profiles, their evidence and their challenge history were generated for testing. Career information shown elsewhere is a small curated extract, not a live job-market feed.</p></div>

      {loading ? <p role="status" className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500">Looking for demo profiles…</p> : null}
      {error ? <div role="alert" className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-sm leading-6 text-amber-900"><p className="font-semibold">Demo profiles could not be loaded</p><p className="mt-1">{error} Start the backend and reload, then try again.</p><button type="button" onClick={() => void reload()} className="mt-3 rounded-full border border-amber-300 bg-white px-4 py-2 text-xs font-semibold focus:outline-none focus:ring-4 focus:ring-teal-500/20">Try again</button></div> : null}
      {data && !fixtures.length ? <p role="status" className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 text-sm leading-6 text-slate-600">No demo profiles are set up on this server. Initialise the database with demo data, as described in the README, or <a className="font-semibold text-teal-800 underline underline-offset-4" href={toHref('/profile')}>create your own demo profile</a>.</p> : null}

      {fixtures.length ? (
        <ul className="mt-8 grid gap-5 md:grid-cols-3">
          {fixtures.map((fixture, index) => {
            const mode = MODES[bandToMode[fixture.age_band] ?? 'explore'];
            const profileId = fixture.profile_id;
            const active = chosen === fixture.age_band;
            return (
              <li key={fixture.fixture_id} className="stage-rise" style={{ animationDelay: `${index * 120}ms` }}>
                <TiltCard className="h-full rounded-[2rem] border border-white bg-white/90 shadow-soft">
                  <div className="flex h-full flex-col p-6">
                    <span className="h-2 w-16 rounded-full" style={{ background: `linear-gradient(90deg, ${mode.palette.a}, ${mode.palette.b}, ${mode.palette.c})` }} aria-hidden="true" />
                    <p className="mt-4 text-xs font-bold uppercase tracking-[0.16em] text-slate-500">Ages {mode.ages}</p>
                    <h2 className="mt-1 font-display text-2xl font-semibold text-ink">{mode.title}</h2>
                    <p className="mt-2 text-sm leading-6 text-slate-600">{bandBlurb[fixture.age_band] ?? ''}</p>
                    <dl className="mt-4 grid grid-cols-2 gap-3 text-center">
                      <div className="rounded-2xl bg-slate-50 p-3"><dt className="text-[11px] font-semibold text-slate-500">Evidence</dt><dd className="mt-1 text-xl font-semibold text-ink">{fixture.evidence_count}</dd></div>
                      <div className="rounded-2xl bg-slate-50 p-3"><dt className="text-[11px] font-semibold text-slate-500">Challenges</dt><dd className="mt-1 text-xl font-semibold text-ink">{fixture.challenge_submission_count}</dd></div>
                    </dl>
                    <span className="mt-4 inline-flex w-fit rounded-full bg-amber-100 px-3 py-1 text-[11px] font-bold text-amber-900">Synthetic · not a real student</span>
                    <div className="mt-auto pt-5">
                      {profileId ? <button type="button" onClick={() => selectProfile(profileId, fixture.age_band)} aria-pressed={active} className={`inline-flex w-full items-center justify-center rounded-full px-5 py-3 text-sm font-semibold transition focus:outline-none focus:ring-4 focus:ring-teal-500/25 ${active ? 'bg-teal-600 text-white' : 'bg-ink text-white shadow-soft hover:bg-slate-800'}`}>{active ? 'Using this profile ✓' : 'Use this demo profile'}</button> : <p className="text-xs text-slate-500">This server did not return a profile locator for this demo.</p>}
                    </div>
                  </div>
                </TiltCard>
              </li>
            );
          })}
        </ul>
      ) : null}

      {chosen ? <div role="status" className="mt-5 rounded-2xl border border-teal-200 bg-teal-50 p-4 text-sm leading-6 text-teal-950">Demo profile selected. The Challenges, Careers and Plan pages now use it. Use the steps below to see the evidence loop.</div> : null}

      <RevealOnScroll>
        <div className="mt-14">
          <p className="ss-section-kicker text-xs font-bold uppercase tracking-[0.18em] text-teal-700">The loop in four steps</p>
          <h2 className="mt-2 font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Try something. Watch the next step change.</h2>
          <ol className="relative mt-8 grid gap-4 md:grid-cols-4">
            <svg aria-hidden="true" viewBox="0 0 100 4" preserveAspectRatio="none" className="absolute left-[12%] right-[12%] top-8 hidden h-1 w-[76%] md:block"><path d="M0 2 H100" pathLength="1" className="line-draw" stroke="#94a3b8" strokeWidth="2" strokeLinecap="round" strokeDasharray="0.02 0.03" fill="none" vectorEffect="non-scaling-stroke" /></svg>
            {loopSteps.map((step, i) => (
              <li key={step.title}>
                <a href={toHref(step.to)} className="group relative flex h-full flex-col items-center rounded-[2rem] border border-white bg-white/85 px-5 pb-6 pt-5 text-center shadow-sm transition duration-base ease-out hover:-translate-y-1 hover:shadow-soft focus:outline-none focus:ring-4 focus:ring-teal-500/20">
                  <span className="relative grid h-14 w-14 place-items-center rounded-full bg-gradient-to-br from-teal-400 to-indigo-500 text-lg font-bold text-white shadow-lg ring-8 ring-white">{i + 1}</span>
                  <h3 className="mt-4 font-display text-xl font-semibold text-ink">{step.title}</h3>
                  <p className="mt-1 text-sm leading-6 text-slate-600">{step.line}</p>
                </a>
              </li>
            ))}
          </ol>
        </div>
      </RevealOnScroll>

      <div className="mt-12 rounded-3xl border border-slate-200 bg-white/90 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-ink">What this demo does not show</h2>
        <ul className="mt-3 space-y-2 pl-5 text-sm leading-6 text-slate-600 marker:text-slate-400">
          <li className="list-disc">It is not a validated test, and it does not predict anyone’s career.</li>
          <li className="list-disc">Guardian consent for under-18s is a recorded confirmation only. Identity is not verified.</li>
          <li className="list-disc">Career facts come from a small curated snapshot (O*NET and ESCO). Indian sources such as NCS, NSDC and PLFS are not integrated yet.</li>
        </ul>
        <p className="mt-3 text-xs text-slate-500">Backend running on <code>{apiBaseUrl}</code></p>
      </div>
    </section>
  );
}
