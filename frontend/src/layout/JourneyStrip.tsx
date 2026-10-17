import { toHref } from '../router';

const steps = [
  { path: '/start', label: 'Start', icon: 'M12 3v18M3 12h18' },
  { path: '/profile', label: 'Profile', icon: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0' },
  { path: '/baseline', label: 'Baseline', icon: 'M4 20V10m6 10V4m6 16v-7m4 7H2' },
  { path: '/challenges', label: 'Challenges', icon: 'M13 3 5 14h6l-1 7 8-11h-6l1-7Z' },
  { path: '/careers', label: 'Careers', icon: 'M4 7h16v12H4zM9 7V5h6v2' },
  { path: '/plan', label: 'Plan', icon: 'M5 19c4 0 3-6 7-6s3-6 7-6M5 19h.01M19 7h.01' },
  { path: '/sources', label: 'Sources', icon: 'M5 4h10l4 4v12H5zM14 4v5h5' },
];

/** Where you are in the journey. Purely navigational: every step is a real page and a real link. */
export default function JourneyStrip({ path }: { path: string }) {
  const current = steps.findIndex((step) => step.path === path);
  if (current < 0) return null;
  return (
    <nav aria-label="Journey" className="relative pt-5">
      <ol className="flex items-center gap-1 overflow-x-auto pb-1 [scrollbar-width:none] sm:gap-2">
        {steps.map((step, index) => {
          const active = index === current;
          const done = index < current;
          return (
            <li key={step.path} className="flex shrink-0 items-center gap-1 sm:gap-2">
              <a
                href={toHref(step.path)}
                aria-current={active ? 'step' : undefined}
                className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-teal-500 ${active ? 'border-ink bg-ink text-white shadow-sm' : done ? 'border-teal-200 bg-teal-50 text-teal-800 hover:bg-teal-100' : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'}`}
              >
                <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d={step.icon} /></svg>
                <span className={active ? '' : 'hidden sm:inline'}>{step.label}</span>
                {done ? <span className="sr-only">(visited earlier in the journey)</span> : null}
              </a>
              {index < steps.length - 1 ? <span aria-hidden="true" className={`h-px w-3 sm:w-6 ${done ? 'bg-teal-300' : 'bg-slate-200'}`} /> : null}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
