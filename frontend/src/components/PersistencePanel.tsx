import { useCallback, useEffect, useState } from 'react';
import SyncPulse from '../motion/SyncPulse';
import RevealOnScroll from '../motion/RevealOnScroll';

type Fixture = { fixture_id: string; age_band: string; synthetic: boolean; data_classification: string; evidence_count: number; challenge_submission_count: number };
export type PersistenceStatus = {
  status: 'ready' | 'degraded' | 'not_initialized' | string;
  schema_version: number; persistent_store: boolean; demo_fixtures: Fixture[];
};

/** Loads the non-sensitive storage diagnostics. It never receives a file path or any profile content. */
export function usePersistenceStatus(apiBaseUrl: string) {
  const [data, setData] = useState<PersistenceStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/api/system/persistence`, { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(6000) });
      if (!response.ok) throw new Error(`The storage check returned HTTP ${response.status}.`);
      setData(await response.json() as PersistenceStatus);
    } catch (e) {
      setData(null);
      setError(e instanceof Error ? e.message : 'Could not reach the storage check.');
    } finally { setLoading(false); }
  }, [apiBaseUrl]);
  useEffect(() => { void load(); }, [load]);
  return { data, error, loading, reload: load };
}

const ageLabel: Record<string, string> = { '10_14': 'Ages 10–14', '15_17': 'Ages 15–17', '18_plus': 'Ages 18+' };

export default function PersistencePanel({ apiBaseUrl }: { apiBaseUrl: string }) {
  const { data, error, loading, reload } = usePersistenceStatus(apiBaseUrl);
  const tone = data?.status === 'ready' ? 'ok' : data ? 'warn' : 'idle';
  const label = loading ? 'Checking…' : data?.status === 'ready' ? 'Saving is working' : data ? 'Saving needs attention' : 'Not reachable';
  return (
    <section id="storage" className="ss-section border-t border-slate-200/80 py-12 sm:py-16" aria-labelledby="storage-heading">
      <div className="max-w-3xl">
        <p className="ss-section-kicker text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Saved on this device’s server</p>
        <h2 id="storage-heading" className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Your work is kept between visits.</h2>
        <p className="mt-3 text-sm leading-7 text-slate-600 sm:text-base">Profiles, evidence, challenge attempts, recommendations and plans are stored in a local database, so restarting the app does not lose them. This is a prototype store, not a production service.</p>
      </div>
      <div className="mt-6 grid gap-4 md:grid-cols-3" role="status" aria-live="polite">
        <div className="rounded-3xl border border-white bg-white/90 p-5 shadow-sm"><p className="text-xs font-semibold text-slate-500">Storage</p><div className="mt-2"><SyncPulse tone={tone} label={label} /></div><p className="mt-2 text-xs leading-5 text-slate-500">{data ? (data.persistent_store ? 'A file-backed database is in use.' : 'No persistent database was found.') : 'We could not read the status, so nothing here is confirmed.'}</p></div>
        <div className="rounded-3xl border border-white bg-white/90 p-5 shadow-sm"><p className="text-xs font-semibold text-slate-500">Database version</p><p className="mt-2 text-2xl font-semibold text-ink">{data ? data.schema_version : '—'}</p><p className="mt-1 text-xs leading-5 text-slate-500">Applied by repeatable migrations.</p></div>
        <div className="rounded-3xl border border-white bg-white/90 p-5 shadow-sm"><p className="text-xs font-semibold text-slate-500">Synthetic demo profiles</p><p className="mt-2 text-2xl font-semibold text-ink">{data ? data.demo_fixtures.length : '—'}</p><p className="mt-1 text-xs leading-5 text-slate-500">Made-up examples for demos. Never real people.</p></div>
      </div>
      {error ? <div role="alert" className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900"><p className="font-semibold">Storage status is unavailable</p><p className="mt-1">{error}</p><button type="button" onClick={() => void reload()} className="mt-3 rounded-full border border-amber-300 bg-white px-4 py-2 text-xs font-semibold focus:outline-none focus:ring-4 focus:ring-teal-500/20">Try again</button></div> : null}
      {data && data.demo_fixtures.length ? (
        <RevealOnScroll>
          <ul className="mt-4 grid gap-3 sm:grid-cols-3">
            {data.demo_fixtures.map((fixture) => (
              <li key={fixture.fixture_id} className="demo-badge rounded-2xl border border-amber-200 bg-amber-50/50 p-4 text-xs leading-5 text-amber-950"><p className="font-bold">{ageLabel[fixture.age_band] ?? fixture.age_band} · synthetic</p><p>{fixture.evidence_count} evidence · {fixture.challenge_submission_count} challenge attempt{fixture.challenge_submission_count === 1 ? '' : 's'}</p></li>
            ))}
          </ul>
        </RevealOnScroll>
      ) : null}
    </section>
  );
}
