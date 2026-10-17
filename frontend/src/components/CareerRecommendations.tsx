import { useCallback, useEffect, useState } from 'react';
import ConfidenceGauge from '../motion/ConfidenceGauge';
import FlipCard from '../motion/FlipCard';

type Category = 'explore' | 'develop' | 'challenge' | 'alternative_to_consider' | 'reconsider_refresh';
type Confidence = 'low' | 'moderate' | 'high';
type Source = {
  source_id: string; source_record_id: string; title: string; publisher: string; record_uri: string | null;
  source_version: string | null; source_type: string; geography: string | null; quality_status: string;
  fact_id: string | null; fact_type: string | null; fact_statement: string | null; evidence_role: string; notes: string[];
};
type Match = { match_type: string; label: string; explanation: string; evidence_ids: string[]; source_references: Source[] };
type EvidenceGap = { gap_type: string; label: string; explanation: string };
type PathwayFact = { fact_kind: string; statement: string; source: Source };
type EvidenceRef = {
  evidence_id: string; title: string; evidence_type: string; signal_dimension: string; source_kind: string;
  observed_at: string; domain: string | null; uncertainty: string; user_interpretation: string; why_used: string;
};
type ValidatingAction = {
  challenge_id: string | null; title: string; domain: string | null; expected_minutes: number | null;
  action: string; why_this_tests_the_hypothesis: string;
};
type Recommendation = {
  hypothesis_id: string; hypothesis_label: string; recommendation_type: string; occupation_node_id: string | null;
  occupation: string | null; taxonomy: string | null; geography: string | null; category: Category; support_level: string;
  evidence_confidence: Confidence;
  confidence_breakdown: { evidence_volume: string; recency: string; consistency: string; source_quality: string; coverage: string; explanation: string };
  rationale: string[]; matches: Match[]; distinct_observation_count: number; most_recent_observation_at: string | null;
  evidence_detail_limit: number; evidence_used: EvidenceRef[]; evidence_gaps: EvidenceGap[];
  source_backed_pathway_facts: PathwayFact[]; next_validating_action: ValidatingAction;
  source_record_count: number; source_quality_note: string; important_limitations: string[];
};
type RecommendationSet = {
  profile_id: string; age_band: '10_14' | '15_17' | '18_plus'; current_goal: string | null;
  algorithm_version: string; weights_status: string; weights: { goal_language_overlap: number; exact_skill_label_overlap: number; challenge_domain_alignment: number; repeated_activity_families: number; portfolio_context_overlap: number }; domain_hypothesis_policy_version: string;
  recommendations: Recommendation[]; evidence_count: number; evidence_count_is_truncated_for_detail: boolean;
  career_catalog_count: number; catalog_status: string; catalog_limitations: string[];
  ordering_explanation: string; global_notices: string[];
};

type Props = { apiBaseUrl: string };
const PROFILE_STORAGE_KEY = 'skillscope_student_evidence_profile_v1';
const categoryLabels: Record<Category, string> = {
  explore: 'Explore', develop: 'Develop', challenge: 'Validate with a challenge',
  alternative_to_consider: 'Alternative to consider', reconsider_refresh: 'Reconsider / refresh',
};
const categoryStyles: Record<Category, string> = {
  explore: 'bg-slate-100 text-slate-700', develop: 'bg-teal-50 text-teal-800',
  challenge: 'bg-indigo-50 text-indigo-800', alternative_to_consider: 'bg-sky-50 text-sky-800',
  reconsider_refresh: 'bg-amber-50 text-amber-900',
};
const confidenceLabels: Record<Confidence, string> = {
  low: 'Limited evidence', moderate: 'Emerging evidence', high: 'Multiple signals',
};

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status}).`;
    try { const body = await response.json() as { detail?: string }; message = body.detail ?? message; } catch { /* Keep HTTP fallback. */ }
    throw new Error(message.slice(0, 1000));
  }
  return await response.json() as T;
}

function distinctEvidence(items: EvidenceRef[]): EvidenceRef[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    if (seen.has(item.evidence_id)) return false;
    seen.add(item.evidence_id);
    return true;
  });
}

function formatObservedAt(value: string | null | undefined): string {
  if (!value) return 'Date not recorded';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? 'Date not recorded' : parsed.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' });
}


export default function CareerRecommendations({ apiBaseUrl }: Props) {
  const [profileId, setProfileId] = useState<string | null>(() => typeof window !== 'undefined' ? window.localStorage.getItem(PROFILE_STORAGE_KEY) : null);
  const [result, setResult] = useState<RecommendationSet | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (id: string) => {
    setLoading(true); setError(null);
    try {
      const body = await readJson<RecommendationSet>(await fetch(`${apiBaseUrl}/api/recommendations/${id}?limit=5`, {
        headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(10000),
      }));
      setResult(body);
    } catch (requestError) {
      setResult(null);
      setError(requestError instanceof Error ? requestError.message : 'Could not load career hypotheses.');
    } finally { setLoading(false); }
  }, [apiBaseUrl]);

  useEffect(() => {
    if (profileId) void load(profileId);
  }, [profileId, load]);

  useEffect(() => {
    const onProfileChanged = () => {
      const next = window.localStorage.getItem(PROFILE_STORAGE_KEY);
      setProfileId(next);
      setResult(null);
      if (!next) setError(null);
    };
    const onEvidenceUpdated = () => {
      const next = window.localStorage.getItem(PROFILE_STORAGE_KEY);
      setProfileId(next);
      if (next) void load(next);
    };
    window.addEventListener('skillscope-profile-changed', onProfileChanged);
    window.addEventListener('skillscope-evidence-updated', onEvidenceUpdated);
    return () => {
      window.removeEventListener('skillscope-profile-changed', onProfileChanged);
      window.removeEventListener('skillscope-evidence-updated', onEvidenceUpdated);
    };
  }, [load]);

  return (
    <section id="career-recommendations" className="ss-section scroll-mt-28 border-t border-slate-200/80 py-12 sm:py-16" aria-labelledby="career-recommendations-heading">
      <div className="mx-auto max-w-7xl">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div className="max-w-3xl">
            <p className="ss-section-kicker text-xs font-bold uppercase tracking-[0.18em] text-indigo-700">Careers</p>
            <h1 id="career-recommendations-heading" className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Career possibilities for you.</h1>
            <p className="mt-3 text-sm leading-7 text-slate-600 sm:text-base">Ideas to explore, not a verdict. They change as you add more evidence.</p>
          </div>
          {profileId ? <button type="button" onClick={() => void load(profileId)} disabled={loading} className="inline-flex shrink-0 items-center justify-center rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:border-teal-300 hover:text-teal-800 disabled:opacity-60">{loading ? 'Refreshing…' : 'Refresh recommendations'}</button> : null}
        </div>

        {!profileId ? <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 text-sm leading-6 text-slate-600">Create a profile on the <a className="font-semibold text-teal-800 underline underline-offset-4" href="#/profile">Profile page</a> (or start a challenge on the <a className="font-semibold text-teal-800 underline underline-offset-4" href="#/challenges">Challenges page</a>) to generate recommendations from attributable career records and your voluntary activity evidence. No profile is created by this panel.</div> : null}
        {loading && !result ? <div className="mt-6 rounded-2xl border border-slate-200 bg-white p-5 text-sm text-slate-500" role="status">Reviewing saved evidence and source-linked career records…</div> : null}
        {error ? <div className="mt-6 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm leading-6 text-amber-900" role="alert"><p className="font-semibold">Recommendations could not be loaded</p><p className="mt-1">{error}</p><p className="mt-2 text-xs">For occupation hypotheses, the active career knowledge graph must be built and current. Rebuild it using the documented offline import and graph commands; the system will not invent missing career facts.</p>{profileId ? <button type="button" onClick={() => void load(profileId)} className="mt-3 rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-semibold">Try again</button> : null}</div> : null}

        {result ? <>
          <div className="mt-6 flex flex-wrap gap-2 text-xs text-slate-600">
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">Algorithm {result.algorithm_version}</span>
            <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">{result.evidence_count} saved evidence records</span>
            {result.catalog_status === 'not_required_for_10_14_exploration' ? <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">Broad age-appropriate exploration</span> : <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5">{result.career_catalog_count} source-linked career records</span>}
          </div>
          {result.recommendations.some((item) => item.confidence_breakdown.consistency === 'mixed') ? <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4" role="status"><p className="text-sm font-semibold text-amber-950">Some evidence points in different directions</p><p className="mt-1 text-sm leading-6 text-amber-900">At least one hypothesis includes student-reported evidence that challenges it. That is useful information, not a failure or a diagnosis. Keep the hypothesis open and try a contrasting activity before changing the goal.</p><a href="#/challenges" className="mt-3 inline-flex rounded-lg border border-amber-300 bg-white px-3 py-2 text-xs font-semibold text-amber-950 hover:bg-amber-100">Choose a validation activity</a></div> : null}
          {result.age_band !== '10_14' ? <div className="mt-3 rounded-xl border border-slate-200 bg-white p-3.5"><p className="text-xs font-semibold text-slate-700">Initial heuristic parameters (not scientifically optimized)</p><div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-600"><span className="rounded-lg bg-slate-50 px-2.5 py-1.5">Goal wording {Math.round(result.weights.goal_language_overlap * 100)}%</span><span className="rounded-lg bg-slate-50 px-2.5 py-1.5">Exact skill label {Math.round(result.weights.exact_skill_label_overlap * 100)}%</span><span className="rounded-lg bg-slate-50 px-2.5 py-1.5">Domain evidence {Math.round(result.weights.challenge_domain_alignment * 100)}%</span><span className="rounded-lg bg-slate-50 px-2.5 py-1.5">Repeated activities {Math.round(result.weights.repeated_activity_families * 100)}%</span><span className="rounded-lg bg-slate-50 px-2.5 py-1.5">Portfolio wording {Math.round(result.weights.portfolio_context_overlap * 100)}%</span></div><p className="mt-2 text-xs leading-5 text-slate-500">These are base ordering weights, not career-fit percentages. When a type of input is unavailable, the remaining active weights are renormalized. {result.ordering_explanation}</p></div> : null}

          <div className="mt-6 grid gap-5 lg:grid-cols-2">
            {result.recommendations.map((item) => (
              <div key={item.hypothesis_id} className="min-w-0 space-y-3">
              <FlipCard
                frontLabel="Show the evidence behind this" backLabel="Back to the summary"
                front={<div className="flex h-full flex-col rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className={`rounded-full px-3 py-1 text-xs font-semibold ${categoryStyles[item.category]}`}>{categoryLabels[item.category]}</span>
                    <ConfidenceGauge level={item.evidence_confidence} label={confidenceLabels[item.evidence_confidence]} />
                  </div>
                  <h3 className="mt-4 font-display text-2xl font-semibold tracking-tight text-ink">{item.hypothesis_label}</h3>
                  {item.taxonomy ? <p className="mt-1 text-xs text-slate-500">{item.taxonomy}{item.geography ? ` · ${item.geography}` : ''}</p> : null}
                  <p className="mt-3 text-sm leading-6 text-slate-700">{item.rationale[0]}</p>
                  <p className="mt-4 text-xs font-semibold text-slate-500">A hypothesis, not a verdict. Flip for the evidence.</p>
                </div>}
                back={<div className="flex h-full flex-col rounded-3xl border border-teal-100 bg-gradient-to-br from-teal-50/80 to-white p-5 shadow-sm sm:p-6">
                  <p className="text-xs font-bold uppercase tracking-[0.14em] text-teal-800">Evidence used</p>
                  {item.evidence_used.length ? <ul className="mt-2 space-y-1.5 pl-4 text-xs leading-5 text-slate-700 marker:text-slate-400">{item.evidence_used.slice(0, 3).map((ev) => <li key={ev.evidence_id} className="list-disc">{ev.title}</li>)}{item.evidence_used.length > 3 ? <li className="list-none text-slate-500">and {item.evidence_used.length - 3} more in the full detail</li> : null}</ul> : <p className="mt-2 text-xs leading-5 text-slate-600">Not enough evidence yet. No saved evidence was used for this hypothesis.</p>}
                  <p className="mt-3 text-[11px] leading-5 text-slate-500">{item.distinct_observation_count} distinct observation{item.distinct_observation_count === 1 ? '' : 's'} · latest {formatObservedAt(item.most_recent_observation_at)}</p>
                  <p className="mt-4 text-xs font-bold uppercase tracking-[0.14em] text-slate-600">Still unknown</p>
                  {item.evidence_gaps.length ? <ul className="mt-2 space-y-1 pl-4 text-xs leading-5 text-slate-700 marker:text-slate-400">{item.evidence_gaps.slice(0, 3).map((gap, i) => <li key={`${item.hypothesis_id}-fg-${i}`} className="list-disc">{gap.label}</li>)}</ul> : <p className="mt-2 text-xs leading-5 text-slate-600">No gaps were listed.</p>}
                  <p className="mt-4 text-xs text-slate-600"><span className="font-semibold text-slate-800">Sources:</span> {item.source_record_count} source record{item.source_record_count === 1 ? '' : 's'}</p>
                  <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/70 p-3">
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-indigo-800">Next validating action</p>
                    <p className="mt-1 text-sm font-semibold text-slate-800">{item.next_validating_action.title}{item.next_validating_action.expected_minutes ? ` · ${item.next_validating_action.expected_minutes} min` : ''}</p>
                  </div>
                </div>}
              />
              <details className="rounded-2xl border border-slate-200 bg-white shadow-sm">
              <summary className="cursor-pointer rounded-2xl px-5 py-3.5 text-sm font-semibold text-ink focus:outline-none focus:ring-4 focus:ring-teal-500/20">Full detail, sources and limitations</summary>
              <article className="flex min-w-0 flex-col p-5 pt-1 sm:p-6 sm:pt-2">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className={`rounded-full px-3 py-1 text-xs font-semibold ${categoryStyles[item.category]}`}>{categoryLabels[item.category]}</span>
                  <ConfidenceGauge level={item.evidence_confidence} label={confidenceLabels[item.evidence_confidence]} />
                </div>
                <h3 className="mt-3 text-xl font-semibold tracking-tight text-ink">{item.hypothesis_label}</h3>
                {item.taxonomy ? <p className="mt-1 text-xs text-slate-500">{item.taxonomy}{item.geography ? ` · ${item.geography}` : ''}</p> : null}
                <p className="mt-3 text-sm leading-6 text-slate-700">{item.rationale[0]}</p>
                <div className="mt-4 rounded-xl bg-slate-50 p-3.5">
                  <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Why this is suggested</p>
                  <ul className="mt-2 space-y-2 pl-4 text-xs leading-5 text-slate-600 marker:text-slate-400">{item.rationale.slice(1).map((reason, i) => <li key={`${item.hypothesis_id}-reason-${i}`} className="list-disc">{reason}</li>)}</ul>
                </div>

                {item.matches.length ? <div className="mt-4"><h4 className="text-sm font-semibold text-slate-800">Evidence matches</h4><ul className="mt-2 space-y-2">{item.matches.map((match, i) => <li key={`${item.hypothesis_id}-match-${i}`} className="rounded-lg border border-teal-100/80 p-3"><p className="text-xs font-semibold text-teal-900">{match.label}</p><p className="mt-1 text-xs leading-5 text-slate-600">{match.explanation}</p></li>)}</ul></div> : null}

                <details className="mt-4 rounded-xl border border-slate-200 bg-white p-3.5">
                  <summary className="cursor-pointer text-sm font-semibold text-slate-800">Audit trail: student evidence → matching logic → source facts</summary>
                  {(() => {
                    const observations = distinctEvidence(item.evidence_used);
                    return <>
                      <div className="mt-3 rounded-lg bg-slate-50 p-3">
                        <p className="text-xs font-semibold text-slate-700">Student evidence used</p>
                        <p className="mt-1 text-xs leading-5 text-slate-600">{item.distinct_observation_count} distinct relevant observation{item.distinct_observation_count === 1 ? '' : 's'} were considered for this hypothesis. The explanation displays {observations.length} record{observations.length === 1 ? '' : 's'} (limit {item.evidence_detail_limit}). Most recent relevant observation: {formatObservedAt(item.most_recent_observation_at)}. This is a record count, not a rating of potential.</p>
                      </div>
                      {observations.length ? <ol className="mt-3 space-y-3">{observations.map((observation, index) => <li key={observation.evidence_id} className="border-l-2 border-teal-200 pl-3"><p className="text-xs font-semibold text-slate-800">{index + 1}. {observation.title}</p><p className="mt-0.5 text-[11px] text-slate-500">{formatObservedAt(observation.observed_at)} · {observation.evidence_type.replaceAll('_', ' ')} · {observation.signal_dimension.replaceAll('_', ' ')} · {observation.domain?.replaceAll('_', ' ') ?? 'Domain not recorded'}</p><p className="mt-1 text-xs leading-5 text-slate-600">Why used: {observation.why_used}</p><p className="mt-1 text-[11px] leading-5 text-slate-500">Student interpretation: {observation.user_interpretation.replaceAll('_', ' ')}</p></li>)}</ol> : <p className="mt-3 text-xs leading-5 text-slate-500">No individual evidence record is directly attached to this explanation. Treat the hypothesis as tentative and gather more evidence before relying on it.</p>}
                      <div className="mt-4 border-t border-slate-100 pt-3">
                        <p className="text-xs font-semibold text-slate-700">Local matching logic — SkillScope inference</p>
                        {item.matches.length ? <ul className="mt-2 space-y-3">{item.matches.map((match, matchIndex) => {
                          const linked = observations.filter((observation) => match.evidence_ids.includes(observation.evidence_id));
                          return <li key={`${item.hypothesis_id}-audit-match-${matchIndex}`} className="rounded-lg border border-indigo-100 bg-indigo-50/40 p-3"><p className="text-xs font-semibold text-indigo-900">{match.label}</p><p className="mt-1 text-xs leading-5 text-slate-600">{match.explanation}</p><p className="mt-1 text-[11px] leading-5 text-slate-500">Evidence linked to this rule: {linked.length ? linked.map((entry) => entry.title).join('; ') : 'No displayed observation is linked to this rule.'}</p>{match.source_references.length ? <div className="mt-2 space-y-1">{match.source_references.map((source, sourceIndex) => <p key={`${source.source_id}-${source.source_record_id}-${sourceIndex}`} className="text-[11px] leading-5 text-slate-600">Career source: {source.publisher} · {source.title}{source.record_uri ? <> · <a href={source.record_uri} target="_blank" rel="noopener noreferrer" className="font-semibold text-teal-800 underline underline-offset-2">Open source</a></> : null}</p>)}</div> : <p className="mt-2 text-[11px] text-slate-500">No external source is attached to this local matching rule.</p>}</li>;
                        })}</ul> : <p className="mt-2 text-xs text-slate-500">No explicit matching rule fired. This recommendation should be treated as broad exploration, not an evidence-backed occupation match.</p>}
                      </div>
                      <div className="mt-4 border-t border-slate-100 pt-3">
                        <p className="text-xs font-semibold text-slate-700">External occupational facts — source-derived</p>
                        {item.source_backed_pathway_facts.length ? <ul className="mt-2 space-y-2">{item.source_backed_pathway_facts.map((fact, factIndex) => <li key={`${fact.source.source_id}-${fact.source.source_record_id}-${factIndex}`} className="text-xs leading-5 text-slate-600"><p>{fact.statement}</p><p className="text-[11px] text-slate-500">{fact.source.publisher} · {fact.source.title} · {fact.source.source_version ?? 'Version not specified'} · {fact.source.geography ?? 'Geography not specified'}</p>{fact.source.record_uri ? <a href={fact.source.record_uri} target="_blank" rel="noopener noreferrer" className="text-[11px] font-semibold text-teal-800 underline underline-offset-2">Open source record</a> : <p className="text-[11px] text-slate-500">No direct record URL is attached.</p>}</li>)}</ul> : <p className="mt-2 text-xs leading-5 text-slate-500">No attributable occupational fact is available for this hypothesis in the active graph. SkillScope does not fill this gap with generated job requirements.</p>}
                      </div>
                      <p className="mt-4 text-[11px] leading-5 text-slate-500">Interpretation boundary: matching rules, category labels, ordering, and next-task selection are local heuristic inferences. A publisher’s source profile describes occupational context; it does not establish that a student is suited to that occupation. Missing data means not yet observed, not low potential.</p>
                    </>;
                  })()}
                </details>

                {item.evidence_gaps.length ? <div className="mt-4"><h4 className="text-sm font-semibold text-slate-800">What is still unknown</h4><ul className="mt-2 space-y-2">{item.evidence_gaps.slice(0, 4).map((gap, i) => <li key={`${item.hypothesis_id}-gap-${i}`}><p className="text-xs font-semibold text-slate-700">{gap.label}</p><p className="mt-0.5 text-xs leading-5 text-slate-500">{gap.explanation}</p></li>)}</ul></div> : null}

                <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/60 p-3.5">
                  <p className="text-xs font-bold uppercase tracking-[0.12em] text-indigo-800">Next validating action</p>
                  <p className="mt-1.5 text-sm font-semibold text-slate-800">{item.next_validating_action.title}{item.next_validating_action.expected_minutes ? ` · ${item.next_validating_action.expected_minutes} min` : ''}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-600">{item.next_validating_action.why_this_tests_the_hypothesis}</p>
                  <p className="mt-2 text-xs leading-5 text-slate-700">{item.next_validating_action.action}</p>
                </div>

                {item.source_backed_pathway_facts.length ? <details className="mt-4 rounded-xl border border-slate-200 p-3.5"><summary className="cursor-pointer text-sm font-semibold text-slate-700">Inspect source-backed work activities ({item.source_backed_pathway_facts.length})</summary><ul className="mt-3 space-y-3">{item.source_backed_pathway_facts.map((fact, i) => <li key={`${fact.source.source_record_id}-${i}`} className="text-xs leading-5 text-slate-600"><p>{fact.statement}</p><p className="mt-1 text-slate-400">{fact.source.publisher} · {fact.source.source_version ?? 'Version not specified'} · {fact.source.geography ?? 'Geography not specified'} · {fact.source.quality_status}</p>{fact.source.record_uri ? <a className="mt-1 inline-block font-semibold text-teal-800 underline decoration-teal-300 underline-offset-4" href={fact.source.record_uri} target="_blank" rel="noopener noreferrer">Open source record</a> : null}</li>)}</ul><p className="mt-3 text-xs text-slate-500">These are listed work activities from the source profile, not guaranteed prerequisites or a complete job description.</p></details> : null}

                <details className="mt-4 border-t border-slate-100 pt-3"><summary className="cursor-pointer text-xs font-semibold text-slate-600">Confidence details and limitations</summary><div className="mt-3 space-y-2 text-xs leading-5 text-slate-500"><p>{item.confidence_breakdown.explanation}</p><p>Evidence volume: {item.confidence_breakdown.evidence_volume.replaceAll('_', ' ')} · Recency: {item.confidence_breakdown.recency.replaceAll('_', ' ')} · Consistency: {item.confidence_breakdown.consistency.replaceAll('_', ' ')} · Source quality: {item.confidence_breakdown.source_quality.replaceAll('_', ' ')} · Coverage: {item.confidence_breakdown.coverage.replaceAll('_', ' ')}</p><p>{item.source_quality_note}</p>{item.important_limitations.map((limitation) => <p key={limitation}>• {limitation}</p>)}</div></details>
              </article>
              </details>
              </div>
            ))}
          </div>

          <div className="mt-5 rounded-2xl border border-slate-200 bg-white p-4 sm:p-5"><p className="text-sm font-semibold text-slate-800">What to remember</p><ul className="mt-2 space-y-1.5 pl-4 text-xs leading-5 text-slate-500 marker:text-slate-400">{result.global_notices.map((notice) => <li key={notice} className="list-disc">{notice}</li>)}</ul>{result.evidence_count_is_truncated_for_detail ? <p className="mt-2 text-xs text-slate-500">This profile contains more records than the 200 most-recent items used for detailed explanation; volume reflects the full count, while explanation detail is bounded for performance.</p> : null}</div>
        <div className="mt-5 flex flex-wrap gap-3"><a href="#/plan" className="inline-flex items-center rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-soft transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/20">Turn a hypothesis into a plan</a><a href="#/sources" className="inline-flex items-center rounded-full border border-slate-200 bg-white px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-teal-300 hover:text-teal-800 focus:outline-none focus:ring-4 focus:ring-teal-500/20">Inspect career sources</a></div>
        </> : null}
      </div>
    </section>
  );
}
