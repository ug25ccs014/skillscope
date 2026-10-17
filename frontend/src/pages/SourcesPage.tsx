import { useCallback, useEffect, useState } from 'react';
import { apiBaseUrl } from '../shared/api';
import { toHref } from '../router';

type GraphSourceReference = {
  source_id: string;
  source_record_id: string;
  title: string;
  publisher: string;
  record_uri: string | null;
  source_version: string | null;
  source_type: string;
  geography: string | null;
  quality_status: string;
  license_reference: string | null;
  fact_id: string | null;
  fact_type: string | null;
  fact_statement: string | null;
  evidence_role: string;
  notes: string[];
};

type GraphNode = {
  node_id: string;
  node_type: string;
  label: string;
  description: string | null;
  taxonomy: string | null;
  external_id: string | null;
  geography: string | null;
  evidence_class: string;
  attributes: Record<string, unknown>;
  source_references: GraphSourceReference[];
};

type CareerCard = GraphNode & {
  tasks: GraphNode[];
  skills: GraphNode[];
  occupational_terms: GraphNode[];
  relationships: GraphEdge[];
  citations: GraphSourceReference[];
};

type GraphEdge = {
  edge_id: string;
  from_node_id: string;
  to_node_id: string;
  from_label: string;
  to_label: string;
  relation_type: string;
  mapping_type: 'exact' | 'reviewed_related' | 'weak_lexical' | 'unresolved';
  review_status: 'sourced' | 'reviewed' | 'proposed' | 'unresolved' | 'rejected';
  description: string | null;
  attributes: Record<string, unknown>;
  notes: string[];
  source_references: GraphSourceReference[];
};

type GraphStatus = {
  status: string;
  node_count: number;
  edge_count: number;
  nodes_by_type: Record<string, number>;
  edges_by_relation: Record<string, number>;
  active_snapshots: Record<string, string>;
  built_from_active_snapshots: Record<string, string>;
  is_stale: boolean;
  unresolved_crosswalk_count: number;
  unresolved_relationship_count: number;
  source_data_is_live: boolean;
  built_at: string | null;
  limitations: string[];
};

type CollectionResponse<T> = {
  items: T[];
  count: number;
  note?: string;
  graph_built_at?: string;
};


export default function SourcesPage() {
  const [careerCards, setCareerCards] = useState<CareerCard[]>([]);
  const [graphCrosswalks, setGraphCrosswalks] = useState<GraphEdge[]>([]);
  const [graphStatus, setGraphStatus] = useState<GraphStatus | null>(null);
  const [graphLoadState, setGraphLoadState] = useState<'loading' | 'ready' | 'unavailable' | 'not_built' | 'stale'>('loading');
  const [graphError, setGraphError] = useState<string | null>(null);
  const loadCareerGraph = useCallback(async () => {
    setGraphLoadState('loading');
    setGraphError(null);
    try {
      const statusResponse = await fetch(`${apiBaseUrl}/api/knowledge-graph/status`, {
        headers: { Accept: 'application/json' },
        signal: AbortSignal.timeout(6000),
      });
      if (!statusResponse.ok) throw new Error(`Knowledge graph status returned HTTP ${statusResponse.status}.`);
      const nextStatus = (await statusResponse.json()) as GraphStatus;
      setGraphStatus(nextStatus);
      if (nextStatus.status !== 'ready') {
        setGraphLoadState('not_built');
        setGraphError('The source graph has not been built for the current database yet. Run the documented knowledge-graph rebuild command after importing the curated snapshot.');
        setCareerCards([]);
        setGraphCrosswalks([]);
        return;
      }
      if (nextStatus.is_stale) {
        setGraphLoadState('stale');
        setGraphError('The active source snapshot changed after this graph was built. Rebuild the graph before using these records.');
        setCareerCards([]);
        setGraphCrosswalks([]);
        return;
      }
      const [careerResponse, crosswalkResponse] = await Promise.all([
        fetch(`${apiBaseUrl}/api/knowledge-graph/careers?limit=100`, {
          headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(8000),
        }),
        fetch(`${apiBaseUrl}/api/knowledge-graph/crosswalks?limit=100`, {
          headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(8000),
        }),
      ]);
      if (!careerResponse.ok || !crosswalkResponse.ok) {
        const failedStatus = !careerResponse.ok ? careerResponse.status : crosswalkResponse.status;
        throw new Error(`Knowledge graph records returned HTTP ${failedStatus}.`);
      }
      const careerResult = (await careerResponse.json()) as CollectionResponse<CareerCard>;
      const crosswalkResult = (await crosswalkResponse.json()) as CollectionResponse<GraphEdge>;
      setCareerCards(careerResult.items ?? []);
      setGraphCrosswalks(crosswalkResult.items ?? []);
      setGraphLoadState('ready');
    } catch (error) {
      setGraphLoadState('unavailable');
      setGraphError(error instanceof Error
        ? `${error.message} Make sure the FastAPI server is running and the graph projection has been built.`
        : 'The source-backed career graph could not be loaded.');
      setCareerCards([]);
      setGraphCrosswalks([]);
    }
  }, []);

  useEffect(() => {
    void loadCareerGraph();
  }, [loadCareerGraph]);

  return (
    <div className="page-body">
        <section id="career-knowledge" className="border-t border-slate-200/80 py-12 sm:py-16" aria-labelledby="career-knowledge-heading">
          <div className="flex flex-col gap-5 md:flex-row md:items-end md:justify-between">
            <div className="max-w-3xl">
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Career knowledge graph</p>
              <h1 id="career-knowledge-heading" className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Explore the work behind a career.</h1>
              <p className="mt-3 text-sm leading-7 text-slate-600 sm:text-base">These are source-backed occupational reference records, not personalized matches. SkillScope shows their source, geography and limitations so you can inspect the evidence rather than trust an unexplained score.</p>
            </div>
            <button type="button" onClick={() => void loadCareerGraph()} disabled={graphLoadState === 'loading'} className="inline-flex shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-teal-300 hover:text-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:cursor-wait disabled:opacity-60">
              {graphLoadState === 'loading' ? 'Loading source graph…' : 'Reload source graph'}
            </button>
          </div>

          {graphStatus ? (
            <div className="mt-6 flex flex-wrap gap-2 text-xs text-slate-600" aria-live="polite">
              <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">{graphStatus.node_count} graph nodes</span>
              <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">{graphStatus.edge_count} relationships</span>
              <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">{graphStatus.unresolved_crosswalk_count} unresolved exact-equivalence question{graphStatus.unresolved_crosswalk_count === 1 ? '' : 's'}</span>
              <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">Static snapshot · Not live job-market data</span>
            </div>
          ) : null}

          {graphError ? (
            <div className={`mt-6 rounded-2xl border p-4 text-sm leading-6 ${graphLoadState === 'stale' || graphLoadState === 'not_built' ? 'border-amber-200 bg-amber-50 text-amber-900' : 'border-slate-200 bg-white text-slate-600'}`} role="status">
              {graphError}
            </div>
          ) : null}

          {graphLoadState === 'ready' ? (
            <>
              <div className="mt-8 grid gap-5 md:grid-cols-2 xl:grid-cols-3">
                {careerCards.map((career) => {
                  const citations = career.citations?.length ? career.citations : career.source_references;
                  return (
                    <article key={career.node_id} className="flex min-w-0 flex-col rounded-2xl border border-slate-200/80 bg-white p-5 shadow-sm sm:p-6">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide text-slate-600">{career.taxonomy ?? 'Source taxonomy'}</span>
                        <span className="rounded-full bg-teal-50 px-2.5 py-1 text-[11px] font-semibold text-teal-800">{career.evidence_class === 'curated_extract' ? 'Curated extract' : career.evidence_class}</span>
                      </div>
                      <h3 className="mt-4 text-xl font-semibold tracking-tight text-ink">{career.label}</h3>
                      <p className="mt-2 text-xs font-medium text-slate-400">{career.geography ?? 'Geography not specified in the record'}</p>
                      {typeof career.attributes.curation_domain === 'string' ? (
                        <div className="mt-2">
                          <span className="inline-flex rounded-full border border-indigo-100 bg-indigo-50 px-2.5 py-1 text-[11px] font-medium text-indigo-800">Coverage example · {career.attributes.curation_domain.replaceAll('_', ' ')}</span>
                          {career.attributes.curation_domain_is_editorial ? <p className="mt-1 text-[10px] leading-4 text-slate-400">SkillScope editorial tag, not an official classification or student ability label.</p> : null}
                        </div>
                      ) : null}
                      <p className="mt-4 text-sm leading-6 text-slate-600">{career.description ?? 'No source-backed summary is available in this record.'}</p>

                      {career.tasks.length ? (
                        <div className="mt-5">
                          <h4 className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Selected work activities</h4>
                          <ul className="mt-3 space-y-2.5">
                            {career.tasks.slice(0, 4).map((task) => (
                              <li key={task.node_id} className="flex gap-2.5 text-sm leading-5 text-slate-600">
                                <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" />
                                <span>{task.label}</span>
                              </li>
                            ))}
                          </ul>
                          <p className="mt-2 text-[11px] leading-5 text-slate-400">Selected paraphrases only; not a complete task list.</p>
                        </div>
                      ) : null}

                      {career.skills.length ? (
                        <div className="mt-5">
                          <h4 className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Source-listed essential skills</h4>
                          <div className="mt-3 flex flex-wrap gap-1.5">
                            {career.skills.slice(0, 6).map((skill) => (
                              <span key={skill.node_id} className="rounded-lg border border-teal-100 bg-teal-50 px-2 py-1 text-xs text-teal-900">{skill.label}</span>
                            ))}
                          </div>
                          <p className="mt-2 text-[11px] leading-5 text-slate-400">Names from the occupational profile’s Essential Skills section. No source skill ID or rating is carried in this extract; these are not your skill scores.</p>
                        </div>
                      ) : null}

                      {career.occupational_terms.length ? (
                        <div className="mt-5">
                          <h4 className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500">Terms preserved from the extract</h4>
                          <div className="mt-2 flex flex-wrap gap-1.5">
                            {career.occupational_terms.slice(0, 5).map((term) => <span key={term.node_id} className="rounded-lg border border-slate-100 bg-slate-50 px-2 py-1 text-[11px] text-slate-600">{term.label}</span>)}
                          </div>
                          <p className="mt-2 text-[11px] leading-5 text-slate-400">The source category was not captured, so these are not labelled as skills or as your interests.</p>
                        </div>
                      ) : null}

                      <div className="mt-auto pt-6">
                        <div className="rounded-xl border border-slate-100 bg-slate-50 p-3.5">
                          <p className="text-xs font-semibold text-slate-700">Source evidence · {citations.length} reference{citations.length === 1 ? '' : 's'}</p>
                          {citations.slice(0, 1).map((source) => (
                            <p key={`${source.source_record_id}-${source.fact_id ?? source.evidence_role}`} className="mt-1.5 text-xs leading-5 text-slate-500">{source.publisher} · {source.source_version ?? 'Version not specified'}</p>
                          ))}
                          <details className="mt-2.5 border-t border-slate-200 pt-2.5">
                            <summary className="cursor-pointer text-xs font-semibold text-teal-800 underline decoration-teal-300 underline-offset-4">Inspect source references and lineage</summary>
                            <ul className="mt-3 space-y-3">
                              {citations.map((source, index) => (
                                <li key={`${source.source_record_id}-${source.fact_id ?? index}`} className="text-xs leading-5 text-slate-600">
                                  <p className="font-semibold text-slate-800">{source.title}</p>
                                  <p>{source.publisher}</p>
                                  <p className="text-slate-400">{source.source_type} · {source.quality_status} · {source.geography ?? 'Geography not specified'}</p>
                                  <p className="break-words text-slate-400">{source.source_version ?? 'Version not specified'}</p>
                                  {source.record_uri ? <a className="mt-1 inline-block font-semibold text-teal-800 underline decoration-teal-300 underline-offset-4 hover:text-teal-950" href={source.record_uri} target="_blank" rel="noopener noreferrer">Open source record</a> : <p>No record URL is available.</p>}
                                  {source.fact_statement ? <p className="mt-1.5">Evidence role: {source.evidence_role}. {source.fact_statement}</p> : <p className="mt-1.5">Evidence role: {source.evidence_role}.</p>}
                                  {source.notes.length ? <p className="mt-1 text-slate-400">{source.notes.join(' ')}</p> : null}
                                  {source.license_reference ? <a className="mt-1 inline-block text-slate-500 underline underline-offset-4" href={source.license_reference} target="_blank" rel="noopener noreferrer">Reuse / licence information</a> : null}
                                </li>
                              ))}
                            </ul>
                          </details>
                        </div>
                      </div>
                    </article>
                  );
                })}
              </div>

              <div className="mt-8 rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-indigo-700">Cross-taxonomy audit</p>
                    <h3 className="mt-1 text-xl font-semibold tracking-tight text-ink">Related does not mean identical.</h3>
                  </div>
                  <p className="text-xs text-slate-500">{graphCrosswalks.length} relationship records to inspect</p>
                </div>
                <p className="mt-3 max-w-4xl text-sm leading-6 text-slate-600">O*NET and ESCO use distinct occupational classifications and geographic contexts. SkillScope keeps their records separate. Connections marked “reviewed related” are editorial relationships; an unresolved record explicitly flags where exact equivalence has not been established.</p>
                {graphCrosswalks.length ? (
                  <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    {graphCrosswalks.map((edge) => (
                      <article key={edge.edge_id} className="rounded-xl border border-slate-100 bg-slate-50 p-4">
                        <div className="flex flex-wrap items-center gap-2">
                          <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${edge.review_status === 'unresolved' ? 'bg-amber-100 text-amber-900' : 'bg-teal-50 text-teal-800'}`}>{edge.review_status.replaceAll('_', ' ')}</span>
                          <span className="text-[11px] text-slate-400">{edge.mapping_type.replaceAll('_', ' ')}</span>
                        </div>
                        <p className="mt-3 text-sm font-semibold text-slate-800">{edge.from_label} ↔ {edge.to_label}</p>
                        {edge.description ? <p className="mt-1.5 text-sm leading-5 text-slate-600">{edge.description}</p> : null}
                        {edge.notes.length ? <ul className="mt-2 space-y-1 pl-4 text-xs leading-5 text-slate-500 marker:text-slate-400">{edge.notes.map((note) => <li key={note} className="list-disc">{note}</li>)}</ul> : null}
                        <div className="mt-3 flex flex-wrap gap-2">
                          {edge.source_references.map((source, index) => (
                            source.record_uri ? <a key={`${source.source_record_id}-${index}`} className="text-xs font-semibold text-teal-800 underline decoration-teal-300 underline-offset-4" href={source.record_uri} target="_blank" rel="noopener noreferrer">Source {index + 1}: {source.title}</a> : null
                          ))}
                        </div>
                      </article>
                    ))}
                  </div>
                ) : <p className="mt-3 text-sm text-slate-500">No cross-taxonomy mappings are available in the active graph.</p>}
              </div>

              <div className="mt-5 rounded-xl border border-slate-200/80 bg-white/70 p-4 text-xs leading-5 text-slate-500">
                <p className="font-semibold text-slate-700">What this data does not claim</p>
                <p className="mt-1">The packaged graph is built from ten curated occupation records, not full O*NET/ESCO datasets. No Indian job demand, salary, qualification prerequisite, student ability, or validated career-fit score is inferred here. Canonical skill concepts with stable source IDs will appear only when a permitted source provides them; the two SkillScope-authored capability hypotheses are labelled as interpretations, not official skills.</p>
                {graphStatus?.limitations?.length ? <details className="mt-2"><summary className="cursor-pointer font-semibold text-teal-800 underline underline-offset-4">Full graph limitations</summary><ul className="mt-2 space-y-1 pl-4 marker:text-slate-400">{graphStatus.limitations.map((limitation) => <li key={limitation} className="list-disc">{limitation}</li>)}</ul></details> : null}
              </div>
            </>
          ) : null}
        </section>

      <section id="privacy" className="border-t border-slate-200/80 py-12 sm:py-16" aria-labelledby="privacy-heading">
        <div className="max-w-3xl">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-indigo-700">Privacy and safety</p>
          <h2 id="privacy-heading" className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">How your data is handled.</h2>
          <p className="mt-3 text-sm leading-7 text-slate-600 sm:text-base">This is a prototype, and these notes describe what it actually does today.</p>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {[
            ['Where data lives', 'Profiles, evidence, challenge attempts and plans are stored in a SQLite database on the computer running the backend. Your browser keeps one opaque profile ID so you can reopen your profile.'],
            ['Consent', 'Ages 10 to 17 require a recorded guardian-consent confirmation; adults confirm their own consent. These are self-attestations. SkillScope does not verify identity or guardian authority.'],
            ['No sign-in yet', 'The API has no authentication. Use demo information only and do not enter real details about children until sign-in, verified consent and a security review exist.'],
            ['Your controls', 'You can correct or permanently delete evidence and your profile on the Profile page. The starting-path calculator on the Start page does not save anything.'],
            ['No hidden tracking', 'SkillScope does not watch activity in the background and does not read social media or other accounts. Repeated-behaviour evidence is recorded only with your specific consent.'],
            ['No outside AI service', 'Recommendations and plans come from transparent, rule-based logic that you can inspect. No external AI service receives your information.'],
          ].map(([title, body]) => <article key={title} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm"><h3 className="font-semibold text-ink">{title}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{body}</p></article>)}
        </div>
        <p className="mt-5 text-sm text-slate-600">Manage your saved information on the <a className="font-semibold text-teal-800 underline underline-offset-4" href={toHref('/profile')}>Profile page</a>.</p>
      </section>
    </div>
  );
}
