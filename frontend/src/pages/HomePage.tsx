import RevealOnScroll from '../motion/RevealOnScroll';
import ConstellationHero from '../motion/ConstellationHero';
import StageRail from '../motion/StageRail';
import AuditTrailFlow from '../motion/AuditTrailFlow';
import { toHref } from '../router';

// Short, visual overview of the real journey. Each step links to its real page.
const journey = [
  { to: '/start', title: 'Start', line: 'Find where to begin', icon: 'M12 3v18M3 12h18', tint: 'from-amber-300 to-orange-400' },
  { to: '/profile', title: 'Profile', line: 'Keep your evidence', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0', tint: 'from-teal-300 to-emerald-400' },
  { to: '/challenges', title: 'Challenge', line: 'Try a quick activity', icon: 'M13 3 5 14h6l-1 7 8-11h-6l1-7Z', tint: 'from-sky-300 to-blue-400' },
  { to: '/careers', title: 'Careers', line: 'Compare possibilities', icon: 'M4 7h16v12H4zM9 7V5h6v2', tint: 'from-indigo-300 to-violet-400' },
  { to: '/plan', title: 'Plan', line: 'Take small next steps', icon: 'M5 19c4 0 3-6 7-6s3-6 7-6M5 19h.01M19 7h.01', tint: 'from-rose-300 to-pink-400' },
];

const pillars = [
  { title: 'Evidence, not labels', line: 'Missing means unknown, never low.', icon: 'M4 19V9m6 10V5m6 14v-7m4 7H2', tint: 'from-teal-400 to-emerald-500', bg: 'from-teal-50 to-white' },
  { title: 'Sources you can check', line: 'Every fact shows where it came from.', icon: 'M5 4h10l4 4v12H5zM14 4v5h5M9 14h6M9 17h4', tint: 'from-indigo-400 to-violet-500', bg: 'from-indigo-50 to-white' },
  { title: 'You stay in control', line: 'Change or delete anything, any time.', icon: 'M12 3 4 6v6c0 4.5 3.2 7.6 8 9 4.8-1.4 8-4.5 8-9V6l-8-3Zm-3 9 2.2 2.2L15.5 10', tint: 'from-amber-400 to-orange-500', bg: 'from-amber-50 to-white' },
];

const eyebrow = 'text-xs font-bold uppercase tracking-[0.18em] text-teal-700';
const h2 = 'mt-2 font-display text-3xl font-semibold tracking-tight text-ink sm:text-5xl';

export default function HomePage() {
  return (
    <div className="page-body">
      <ConstellationHero />

      <RevealOnScroll>
        <section className="pt-16 pb-16 sm:pt-24 sm:pb-24" aria-labelledby="how-heading">
          <div className="text-center">
            <p className={eyebrow}>How it works</p>
            <h2 id="how-heading" className={h2}>Five steps. Your pace.</h2>
          </div>
          <ol className="relative mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-5 lg:gap-5">
            <div aria-hidden="true" className="absolute left-[10%] right-[10%] top-9 hidden border-t-2 border-dashed border-slate-300/80 lg:block" />
            {journey.map((step, i) => (
              <li key={step.to} className={i % 2 ? 'lg:mt-10' : ''}>
                <a href={toHref(step.to)} className="group relative flex h-full flex-col items-center rounded-[2rem] border border-white bg-white/80 px-5 pb-7 pt-6 text-center shadow-sm backdrop-blur transition duration-base ease-out hover:-translate-y-1.5 hover:shadow-soft focus:outline-none focus:ring-4 focus:ring-teal-500/25">
                  <span className={`relative grid h-16 w-16 place-items-center rounded-full bg-gradient-to-br ${step.tint} text-white shadow-lg ring-8 ring-white`}>
                    <svg aria-hidden="true" viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d={step.icon} /></svg>
                    <span className="absolute -right-1 -top-1 grid h-6 w-6 place-items-center rounded-full bg-ink text-[11px] font-bold text-white">{i + 1}</span>
                  </span>
                  <h3 className="mt-5 font-display text-2xl font-semibold text-ink">{step.title}</h3>
                  <p className="mt-1 text-sm text-slate-600">{step.line}</p>
                </a>
              </li>
            ))}
          </ol>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="pb-16 sm:pb-24" aria-labelledby="pillars-heading">
          <div className="text-center">
            <p className={eyebrow}>Our promise</p>
            <h2 id="pillars-heading" className={h2}>Built to be honest.</h2>
          </div>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {pillars.map((pillar) => (
              <article key={pillar.title} className={`rounded-[2rem] border border-white bg-gradient-to-b ${pillar.bg} p-7 shadow-sm transition duration-base ease-out hover:-translate-y-1 hover:shadow-soft`}>
                <span className={`grid h-14 w-14 place-items-center rounded-full bg-gradient-to-br ${pillar.tint} text-white shadow-lg`}>
                  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-7 w-7" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d={pillar.icon} /></svg>
                </span>
                <h3 className="mt-5 font-display text-2xl font-semibold text-ink">{pillar.title}</h3>
                <p className="mt-1.5 text-sm leading-6 text-slate-600">{pillar.line}</p>
              </article>
            ))}
          </div>
        </section>
      </RevealOnScroll>

      <RevealOnScroll>
        <section className="pb-16 sm:pb-24" aria-labelledby="trust-heading">
          <div className="text-center">
            <p className={eyebrow}>Built to be trusted</p>
            <h2 id="trust-heading" className={h2}>Saved, explained, protected.</h2>
            <p className="mx-auto mt-3 max-w-2xl text-base leading-7 text-slate-600">Your work stays between visits, every suggestion can be traced, and you decide what is kept.</p>
          </div>
          <div className="mt-10"><StageRail /></div>
          <div className="mx-auto mt-10 max-w-2xl rounded-[2rem] border border-white bg-gradient-to-br from-teal-50 via-white to-indigo-50 p-5 shadow-sm"><AuditTrailFlow /></div>
        </section>
      </RevealOnScroll>

      <div className="cta-band relative mb-16 flex flex-col items-center gap-5 overflow-hidden rounded-[2.5rem] px-8 py-12 text-center text-white sm:py-16">
        <h2 className="relative font-display text-4xl font-semibold tracking-tight sm:text-5xl">Ready to begin?</h2>
        <p className="relative text-white/80">It takes about a minute.</p>
        <div className="relative flex flex-wrap items-center justify-center gap-3"><a href={toHref('/start')} className="relative inline-flex items-center justify-center rounded-full bg-white px-8 py-4 text-sm font-bold text-ink shadow-glow transition hover:-translate-y-0.5 hover:bg-slate-100 focus:outline-none focus:ring-4 focus:ring-white/30">Find my starting path</a><a href={toHref('/demo')} className="relative inline-flex items-center justify-center rounded-full border border-white/40 bg-white/10 px-8 py-4 text-sm font-bold text-white backdrop-blur transition hover:bg-white/20 focus:outline-none focus:ring-4 focus:ring-white/30">Try a demo student</a></div>
      </div>
    </div>
  );
}
