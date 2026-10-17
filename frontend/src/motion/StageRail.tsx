import { toHref } from '../router';
import TiltCard from './TiltCard';

type Item = { to: string; title: string; line: string; tint: string; icon: string };

const items: Item[] = [
  { to: '/profile', title: 'Saved', line: 'Your evidence is stored, so it is still here next visit.', tint: 'from-teal-400 to-emerald-500', icon: 'M4 7c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3Zm0 0v5c0 1.7 3.6 3 8 3s8-1.3 8-3V7M4 12v5c0 1.7 3.6 3 8 3s8-1.3 8-3v-5' },
  { to: '/careers', title: 'Explained', line: 'Trace a suggestion from your evidence to cited sources.', tint: 'from-indigo-400 to-violet-500', icon: 'M5 12h4m6 0h4M9 12a3 3 0 1 0 6 0 3 3 0 0 0-6 0Zm-7 0h.01M22 12h-.01' },
  { to: '/sources', title: 'Protected', line: 'Consent, correction and deletion. No outside AI sees your data.', tint: 'from-amber-400 to-orange-500', icon: 'M12 3 4 6v6c0 4.5 3.2 7.6 8 9 4.8-1.4 8-4.5 8-9V6l-8-3Zm-3 9 2.2 2.2L15.5 10' },
  { to: '/sources', title: 'Your way', line: 'Reduce motion and pick the formats you like to work in.', tint: 'from-sky-400 to-blue-500', icon: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-5v3m0 12v3M3 12h3m12 0h3M5.6 5.6l2.1 2.1m8.6 8.6 2.1 2.1m0-12.8-2.1 2.1M7.7 16.3l-2.1 2.1' },
  { to: '/demo', title: 'Demo-ready', line: 'Three made-up students, one for each starting path.', tint: 'from-rose-400 to-pink-500', icon: 'M8 5v14l11-7L8 5Z' },
];

/** Five trust features, each linking to the real page where it lives. Cards rise in one after another. */
export default function StageRail() {
  return (
    <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
      {items.map((item, index) => (
        <li key={item.title} className="stage-rise" style={{ animationDelay: `${index * 110}ms` }}>
          <TiltCard className="h-full rounded-[2rem] border border-white bg-white/85 shadow-sm">
            <a href={toHref(item.to)} className="flex h-full flex-col items-start p-6 focus:outline-none focus-visible:ring-4 focus-visible:ring-teal-500/30">
              <span className={`grid h-12 w-12 place-items-center rounded-2xl bg-gradient-to-br ${item.tint} text-white shadow-lg`}>
                <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d={item.icon} /></svg>
              </span>
              <h3 className="mt-4 font-display text-xl font-semibold text-ink">{item.title}</h3>
              <p className="mt-1.5 text-sm leading-6 text-slate-600">{item.line}</p>
            </a>
          </TiltCard>
        </li>
      ))}
    </ul>
  );
}
