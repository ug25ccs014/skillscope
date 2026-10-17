import { useCallback, useEffect, useState } from 'react';
import RevealOnScroll from '../motion/RevealOnScroll';
import SyncPulse from '../motion/SyncPulse';

type SourceStatus = 'live' | 'cached' | 'curated' | 'link_only' | 'unavailable';
type SourceItem = {
  source_id: string; publisher: string; name: string; official_url: string; reference_urls: string[];
  terms_url: string | null; geography: string | null; source_role: string; source_version_or_release: string | null;
  reviewed_on: string | null; integration_status: string; runtime_access_status: string; status: SourceStatus;
  status_explanation: string; last_successful_sync_at: string | null; last_attempt_at: string | null;
  last_attempt_status: string | null; active_snapshot_id: string | null; checksum_sha256: string | null;
  license_terms_status: string; limitations: string[]; source_data_is_live: boolean;
};
type Conflict = {
  source_id: string; source_record_id: string; publisher: string; title: string; record_uri: string | null;
  source_version: string | null; geography: string | null; limitations: string[]; explanation: string;
};
type MappingUncertainty = {
  edge_id: string; from_label: string; to_label: string; relation_type: string; mapping_type: string;
  review_status: string; description: string | null; notes: string[];
  source_references: Array<{ title: string; publisher: string; record_uri: string | null; source_version: string | null }>;
  explanation: string;
};
type RegistryResponse = {
  manifest_version: string | number | null; manifest_last_reviewed: string | null; manifest_status: string;
  generated_at: string; sources: SourceItem[]; conflicted_source_records: Conflict[];
  mapping_uncertainties: MappingUncertainty[]; graph_status: { status?: string; node_count?: number; edge_count?: number; built_at?: string | null; is_stale?: boolean; active_snapshots?: Record<string, string>; built_from_active_snapshots?: Record<string, string>; graph_schema_version?: string | number | null; builder_version?: string | null; unresolved_relationship_count?: number; limitations?: string[] };
  source_data_is_live: boolean; notes: string[];
};
type Props = { apiBaseUrl: string };

const statusLabel: Record<SourceStatus, string> = {
  live: 'Live', cached: 'Cached snapshot', curated: 'Curated extract', link_only: 'Link only', unavailable: 'Not integrated',
};
const statusClass: Record<SourceStatus, string> = {
  live: 'bg-emerald-50 text-emerald-800 border-emerald-200',
  cached: 'bg-sky-50 text-sky-800 border-sky-200',
  curated: 'bg-indigo-50 text-indigo-800 border-indigo-200',
  link_only: 'bg-slate-100 text-slate-700 border-slate-200',
  unavailable: 'bg-amber-50 text-amber-900 border-amber-200',
};

function formatDate(value: string | null | undefined): string {
  if (!value) return 'No successful app-side sync recorded';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? value : parsed.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' });
}

async function readResponse(response: Response): Promise<RegistryResponse> {
  if (!response.ok) {
    let detail = `Source registry request failed (HTTP ${response.status}).`;
    try { const body = await response.json() as { detail?: string }; if (body.detail) detail = body.detail; } catch { /* keep safe fallback */ }
    throw new Error(detail.slice(0, 800));
  }
  return await response.json() as RegistryResponse;
}

export default function SourceRegistry({ apiBaseUrl }: Props) {
  const [registry, setRegistry] = useState<RegistryResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<'all' | SourceStatus>('all');
  const [query, setQuery] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/api/source-registry`, {
        headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(10000),
      });
      setRegistry(await readResponse(response));
    } catch (requestError) {
      setRegistry(null);
      setError(requestError instanceof Error ? requestError.message : 'Could not load source audit data.');
    } finally { setLoading(false); }
  }, [apiBaseUrl]);

  useEffect(() => { void load(); }, [load]);

  const filteredSources = (registry?.sources ?? []).filter((source) => {
    const matchesStatus = filter === 'all' || source.status === filter;
    const text = `${source.name} ${source.publisher} ${source.source_id} ${source.geography ?? ''}`.toLocaleLowerCase();
    return matchesStatus && text.includes(query.trim().toLocaleLowerCase());
  });

  return (
    <section id="source-registry" className="ss-section scroll-mt-28 border-t border-slate-200/80 py-12 sm:py-16" aria-labelledby="source-registry-heading">
      <div className="w-full min-w-0">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="ss-section-kicker text-xs font-bold uppercase tracking-[0.18em] text-indigo-700">Source audit</p>
            <h2 id="source-registry-heading" className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Inspect where career information comes from.</h2>
            <p className="mt-3 text-sm leading-7 text-slate-600 sm:text-base">This register separates actual local imports from reviewed links and planned integrations. A source being listed or readable online does not mean SkillScope has downloaded it or uses it to make a recommendation.</p>
          </div>
          <button type="button" onClick={() => void load()} disabled={loading} className="inline-flex shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-teal-300 hover:text-teal-800 disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-teal-500">{loading ? 'Refreshing…' : 'Refresh source status'}</button>
        </div>

        {loading && !registry ? <p role="status" className="mt-5 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">Loading source manifest and local ingestion status…</p> : null}
        {error ? <div role="alert" className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900"><p className="font-semibold">Source audit is temporarily unavailable</p><p className="mt-1">{error}</p><p className="mt-2 text-xs">Career reference cards may still display cached, source-linked records; do not interpret an audit-panel failure as a live-source outage.</p></div> : null}

        {registry ? <>
          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs font-semibold text-slate-500">Manifest version</p><p className="mt-1 text-lg font-semibold text-ink">{registry.manifest_version ?? 'Unversioned'}</p><p className="mt-1 text-xs text-slate-500">Reviewed {registry.manifest_last_reviewed ?? 'date not recorded'}</p></div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs font-semibold text-slate-500">Source records</p><p className="mt-1 text-lg font-semibold text-ink">{registry.sources.length}</p><p className="mt-1 text-xs text-slate-500">Listed in the local register</p></div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs font-semibold text-slate-500">Knowledge graph</p><p className="mt-1 text-lg font-semibold capitalize text-ink">{(registry.graph_status.status ?? 'unknown').replaceAll('_', ' ')}</p><div className="mt-1"><SyncPulse tone={registry.graph_status.status === 'ready' && !registry.graph_status.is_stale ? 'ok' : 'warn'} label={registry.graph_status.status === 'ready' && !registry.graph_status.is_stale ? 'Snapshot matches' : 'Needs attention'} /></div><p className="mt-1 text-xs text-slate-500">{registry.graph_status.node_count ?? 0} nodes · {registry.graph_status.edge_count ?? 0} relationships</p><p className="mt-1 text-xs text-slate-500">Built {formatDate(registry.graph_status.built_at)}</p>{registry.graph_status.status === 'ready' ? <p className={`mt-2 text-xs font-semibold ${registry.graph_status.is_stale ? 'text-amber-800' : 'text-emerald-800'}`} role="status">{registry.graph_status.is_stale ? 'Stale: graph snapshot differs from currently active source snapshots.' : 'Graph snapshot matches the currently active source snapshots.'}</p> : null}</div>
            <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs font-semibold text-slate-500">Source data status</p><p className="mt-1 text-lg font-semibold text-ink">{registry.source_data_is_live ? 'Live source detected' : 'No live feed declared'}</p><p className="mt-1 text-xs text-slate-500">Audit generated {formatDate(registry.generated_at)}</p></div>
          </div>

          <div className="mt-6 flex flex-col gap-3 rounded-xl border border-slate-200 bg-white p-4 sm:flex-row sm:items-center">
            <label className="flex-1"><span className="sr-only">Search source register</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search publisher, source, or geography…" className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500" /></label>
            <label className="sm:w-56"><span className="sr-only">Filter source status</span><select value={filter} onChange={(event) => setFilter(event.target.value as 'all' | SourceStatus)} className="w-full rounded-lg border border-slate-200 bg-white px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-teal-500"><option value="all">All statuses</option><option value="live">Live</option><option value="cached">Cached snapshots</option><option value="curated">Curated extracts</option><option value="link_only">Link-only references</option><option value="unavailable">Not integrated</option></select></label>
            <span className="text-xs text-slate-500" aria-live="polite">{filteredSources.length} shown</span>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            {filteredSources.map((source) => (
              <RevealOnScroll key={source.source_id}><article className="ss-panel h-full min-w-0 rounded-3xl border border-slate-200 bg-white p-5 transition duration-base ease-out hover:-translate-y-0.5 hover:shadow-soft sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="min-w-0"><h3 className="break-words text-lg font-semibold text-ink">{source.name}</h3><p className="mt-1 text-sm text-slate-500">{source.publisher}</p></div>
                  <span className={`shrink-0 rounded-full border px-2.5 py-1 text-xs font-semibold ${statusClass[source.status]}`}>{statusLabel[source.status]}</span>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-600">{source.source_role}</p>
                <dl className="mt-4 grid gap-3 sm:grid-cols-2">
                  <div><dt className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Geography</dt><dd className="mt-1 text-xs leading-5 text-slate-700">{source.geography ?? 'Not recorded'}</dd></div>
                  <div><dt className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Version / release</dt><dd className="mt-1 text-xs leading-5 text-slate-700">{source.source_version_or_release ?? 'Not recorded'}</dd></div>
                  <div><dt className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Last successful sync</dt><dd className="mt-1 text-xs leading-5 text-slate-700">{formatDate(source.last_successful_sync_at)}</dd></div>
                  <div><dt className="text-[11px] font-bold uppercase tracking-wide text-slate-400">Last reviewed</dt><dd className="mt-1 text-xs leading-5 text-slate-700">{source.reviewed_on ?? 'Not recorded'} (review is not a sync)</dd></div>
                </dl>
                <div className="mt-4 rounded-xl bg-slate-50 p-3.5"><p className="text-xs font-semibold text-slate-700">What this status means</p><p className="mt-1 text-xs leading-5 text-slate-600">{source.status_explanation}</p><p className="mt-2 text-[11px] leading-5 text-slate-500">Runtime: {source.runtime_access_status.replaceAll('_', ' ')} · Integration: {source.integration_status.replaceAll('_', ' ')}</p>{source.last_attempt_status ? <p className="mt-1 text-[11px] text-slate-500">Last attempt: {source.last_attempt_status.replaceAll('_', ' ')} · {formatDate(source.last_attempt_at)}</p> : null}</div>
                <details className="mt-4 border-t border-slate-100 pt-3"><summary className="cursor-pointer text-sm font-semibold text-teal-800 underline decoration-teal-300 underline-offset-4">Publisher links, terms, and limitations ({source.limitations.length})</summary>
                  <div className="mt-3 space-y-3 text-xs leading-5 text-slate-600"><p className="font-semibold">Known limitations</p><ul className="space-y-1 pl-4 marker:text-slate-400">{source.limitations.map((limit, index) => <li key={`${source.source_id}-limit-${index}`} className="list-disc">{limit}</li>)}</ul><p className="font-semibold">Reuse and licensing</p><p>{source.license_terms_status}</p><div className="flex flex-wrap gap-x-4 gap-y-2"><a href={source.official_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-teal-800 underline underline-offset-4">Official source</a>{source.terms_url ? <a href={source.terms_url} target="_blank" rel="noopener noreferrer" className="font-semibold text-teal-800 underline underline-offset-4">Licence / terms</a> : null}{source.reference_urls.map((url, index) => <a key={`${source.source_id}-ref-${index}`} href={url} target="_blank" rel="noopener noreferrer" className="font-semibold text-teal-800 underline underline-offset-4">Reference {index + 1}</a>)}</div>{source.active_snapshot_id ? <p>Active local snapshot: <code className="break-all">{source.active_snapshot_id}</code>{source.checksum_sha256 ? <span className="block break-all">SHA-256: {source.checksum_sha256}</span> : null}</p> : null}</div>
                </details>
              </article></RevealOnScroll>
            ))}
          </div>
          {!filteredSources.length ? <p className="mt-4 rounded-xl border border-slate-200 bg-white p-4 text-sm text-slate-500">No sources match the selected filter.</p> : null}

          <div className="mt-8 grid gap-5 xl:grid-cols-2">
            <section className="rounded-2xl border border-amber-200 bg-amber-50/60 p-5 sm:p-6" aria-labelledby="source-conflicts-heading">
              <h3 id="source-conflicts-heading" className="text-lg font-semibold text-ink">Source records marked conflicted</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">Records in this list are explicitly marked conflicted in the local provenance store. An empty list means no record is currently flagged this way; it does not prove that every external source agrees.</p>
              {registry.conflicted_source_records.length ? <ul className="mt-4 space-y-3">{registry.conflicted_source_records.map((item) => <li key={`${item.source_id}:${item.source_record_id}`} className="rounded-xl border border-amber-200 bg-white p-3"><p className="text-sm font-semibold text-slate-800">{item.title}</p><p className="mt-1 text-xs text-slate-500">{item.publisher} · {item.source_version ?? 'Version not recorded'} · {item.geography ?? 'Geography not recorded'}</p><p className="mt-2 text-xs leading-5 text-amber-900">{item.explanation}</p>{item.limitations.map((limit, i) => <p key={i} className="mt-1 text-xs text-slate-600">{limit}</p>)}{item.record_uri ? <a href={item.record_uri} target="_blank" rel="noopener noreferrer" className="mt-2 inline-block text-xs font-semibold text-teal-800 underline underline-offset-4">Open source record</a> : null}</li>)}</ul> : <p className="mt-4 text-sm font-medium text-amber-900">No source record is currently marked conflicted.</p>}
            </section>
            <section className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" aria-labelledby="mapping-uncertainties-heading">
              <h3 id="mapping-uncertainties-heading" className="text-lg font-semibold text-ink">Non-exact occupational mappings</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">These records identify related or unresolved taxonomy mappings. They are shown as mapping uncertainty—not described as a factual contradiction unless the source record itself is explicitly conflicted.</p>
              {registry.mapping_uncertainties.length ? <ul className="mt-4 space-y-3">{registry.mapping_uncertainties.map((item) => <li key={item.edge_id} className="rounded-xl border border-slate-200 bg-slate-50 p-3"><div className="flex flex-wrap gap-2 text-[11px]"><span className="rounded-full bg-amber-100 px-2 py-1 font-semibold text-amber-900">{item.review_status.replaceAll('_', ' ')}</span><span className="rounded-full bg-white px-2 py-1 text-slate-600">{item.mapping_type.replaceAll('_', ' ')}</span></div><p className="mt-2 text-sm font-semibold text-slate-800">{item.from_label} ↔ {item.to_label}</p>{item.description ? <p className="mt-1 text-xs leading-5 text-slate-600">{item.description}</p> : null}<p className="mt-2 text-xs leading-5 text-slate-500">{item.explanation}</p>{item.notes.map((note, i) => <p key={i} className="mt-1 text-xs leading-5 text-slate-500">{note}</p>)}<div className="mt-2 flex flex-wrap gap-3">{item.source_references.map((source, i) => source.record_uri ? <a key={i} href={source.record_uri} target="_blank" rel="noopener noreferrer" className="text-xs font-semibold text-teal-800 underline underline-offset-4">{source.publisher}: {source.title}</a> : null)}</div></li>)}</ul> : <p className="mt-4 text-sm text-slate-500">No non-exact cross-taxonomy mapping was returned by the current graph query, or the graph has not been built.</p>}
            </section>
          </div>

          {registry.graph_status.status === 'ready' ? <details className="mt-5 rounded-xl border border-slate-200 bg-white p-4"><summary className="cursor-pointer text-sm font-semibold text-slate-700">Graph build and snapshot audit</summary><div className="mt-3 space-y-3 text-xs leading-5 text-slate-600"><p>Builder version: {registry.graph_status.builder_version ?? 'Not recorded'} · Schema version: {registry.graph_status.graph_schema_version ?? 'Not recorded'} · Unresolved relationships: {registry.graph_status.unresolved_relationship_count ?? 0}</p><div className="grid gap-3 sm:grid-cols-2"><div><p className="font-semibold">Currently active snapshots</p><pre className="mt-1 whitespace-pre-wrap break-all rounded-lg bg-slate-50 p-2">{JSON.stringify(registry.graph_status.active_snapshots ?? {}, null, 2)}</pre></div><div><p className="font-semibold">Snapshots used to build the graph</p><pre className="mt-1 whitespace-pre-wrap break-all rounded-lg bg-slate-50 p-2">{JSON.stringify(registry.graph_status.built_from_active_snapshots ?? {}, null, 2)}</pre></div></div>{(registry.graph_status.limitations ?? []).map((limit, index) => <p key={`graph-limit-${index}`}>{limit}</p>)}</div></details> : null}
          <div className="mt-5 rounded-xl border border-slate-200 bg-white p-4"><p className="text-xs font-semibold text-slate-700">Audit notes</p><ul className="mt-2 space-y-1 pl-4 text-xs leading-5 text-slate-500 marker:text-slate-400">{registry.notes.map((note, index) => <li key={index} className="list-disc">{note}</li>)}</ul></div>
        </> : null}
      </div>
    </section>
  );
}
