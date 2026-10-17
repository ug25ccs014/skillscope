import { useCallback, useEffect, useState, type FormEvent } from 'react';

type AgeBand = '10_14' | '15_17' | '18_plus';
type ConsentBasis = 'student_confirmed' | 'guardian_confirmed';
type Preference = 'balanced' | 'explore' | 'develop' | 'validate' | 'alternative';
type Interpretation = 'supports_current_hypothesis' | 'challenges_current_hypothesis' | 'contextual_or_mixed' | 'not_interpreted';
type ChallengeDomain = 'logic_data' | 'science_research' | 'technology' | 'design_creative' | 'communication' | 'helping_social' | 'business' | 'hands_on_spatial' | 'environment';

type RubricCriterion = { criterion_id: string; label: string; observable_description: string; score_scale: string; max_score: number };
type NextChallenge = {
  challenge_id: string; challenge_version: string; domain: ChallengeDomain; skill_tags: string[];
  difficulty: string; safety_rating: string; title: string; instructions: string; expected_output: string;
  expected_minutes: number; materials: string[]; accessibility_notes: string[]; rubric: RubricCriterion[];
  reflection_prompts: string[]; reason_code: string; rationale: string; why_this_now: string; avoids_recent_repeat: boolean;
};
type LastCompletion = {
  submission_id: string; challenge_id: string; title: string; domain: ChallengeDomain; evidence_status: string;
  observed_criteria: number; objective_score: number | null; objective_max_score: number | null;
  interpretation: Interpretation; enjoyment: number | null; reported_difficulty: number | null; confidence: number | null;
  willingness_to_continue: number | null; reflection: string | null; created_at: string;
};
type DomainExposure = { domain: ChallengeDomain; submission_count: number; distinct_challenges: number; latest_at: string | null; status: string };
type LoopState = {
  loop_policy_version: string; profile_id: string; age_band: AgeBand; mode: string; preference: Preference;
  current_goal: string | null; total_submissions: number; evidence_count: number; domain_exposure: DomainExposure[];
  last_completion: LastCompletion | null; next_challenge: NextChallenge; what_changed: string; next_step: string;
  notice: string; limitations: string[];
};
type ScoreResult = {
  submission_id: string; challenge_id: string; evidence_status: string; observed_criteria: number; required_observed_criteria: number;
  objective_score: number | null; objective_max_score: number | null; explanation: string;
};
type Props = { apiBaseUrl: string };

const PROFILE_STORAGE_KEY = 'skillscope_student_evidence_profile_v1';
const PREFERENCE_STORAGE_KEY = 'skillscope_discovery_preference_v1';
const inputClass = 'mt-1.5 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10';
const domainLabels: Record<ChallengeDomain, string> = {
  logic_data: 'Logic & data', science_research: 'Science & research', technology: 'Technology',
  design_creative: 'Design & creative', communication: 'Communication', helping_social: 'Helping & social',
  business: 'Business', hands_on_spatial: 'Hands-on & spatial', environment: 'Environment',
};
const preferenceLabels: Record<Preference, string> = {
  balanced: 'Balanced next step', explore: 'Explore new areas', develop: 'Develop a clear engagement',
  validate: 'Validate an uncertain idea', alternative: 'Test an alternative',
};

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status}).`;
    try {
      const body = await response.json() as { detail?: string | Array<{ msg?: string }> };
      message = Array.isArray(body.detail) ? body.detail.map((item) => item.msg).filter(Boolean).join(' ') : body.detail ?? message;
    } catch { /* Use the safe status message. */ }
    throw new Error(message.slice(0, 1000));
  }
  return await response.json() as T;
}

function storedPreference(): Preference {
  if (typeof window === 'undefined') return 'balanced';
  const saved = window.localStorage.getItem(PREFERENCE_STORAGE_KEY);
  return saved === 'explore' || saved === 'develop' || saved === 'validate' || saved === 'alternative' || saved === 'balanced' ? saved : 'balanced';
}

function consentBasis(ageBand: AgeBand): ConsentBasis {
  return ageBand === '18_plus' ? 'student_confirmed' : 'guardian_confirmed';
}

export default function DiscoveryLoop({ apiBaseUrl }: Props) {
  const [profileId, setProfileId] = useState<string | null>(() => typeof window !== 'undefined' ? window.localStorage.getItem(PROFILE_STORAGE_KEY) : null);
  const [state, setState] = useState<LoopState | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [preference, setPreference] = useState<Preference>(storedPreference);

  const [createAgeBand, setCreateAgeBand] = useState<AgeBand>('18_plus');
  const [createGoal, setCreateGoal] = useState('');
  const [consentConfirmed, setConsentConfirmed] = useState(false);

  const [output, setOutput] = useState('');
  const [criterionScores, setCriterionScores] = useState<Record<string, string>>({});
  const [criterionNotes, setCriterionNotes] = useState<Record<string, string>>({});
  const [enjoyment, setEnjoyment] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [confidence, setConfidence] = useState('');
  const [willingness, setWillingness] = useState('');
  const [reflection, setReflection] = useState('');
  const [interpretation, setInterpretation] = useState<Interpretation>('not_interpreted');
  const [lastResult, setLastResult] = useState<ScoreResult | null>(null);

  const loadState = useCallback(async (id: string, nextPreference: Preference = preference) => {
    setLoading(true);
    setError(null);
    try {
      const body = await readJson<LoopState>(await fetch(
        `${apiBaseUrl}/api/discovery-loop/${id}?preference=${encodeURIComponent(nextPreference)}`,
        { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(8000) },
      ));
      setState(body);
    } catch (requestError) {
      const message = requestError instanceof Error ? requestError.message : 'Could not load the discovery loop.';
      if (message.includes('404') || message.toLowerCase().includes('not found')) {
        window.localStorage.removeItem(PROFILE_STORAGE_KEY);
        setProfileId(null);
        setState(null);
        window.dispatchEvent(new Event('skillscope-profile-changed'));
      }
      setError(`${message} Please try again.`);
    } finally {
      setLoading(false);
    }
  }, [apiBaseUrl, preference]);

  useEffect(() => {
    window.localStorage.setItem(PREFERENCE_STORAGE_KEY, preference);
  }, [preference]);

  useEffect(() => {
    if (profileId) void loadState(profileId, preference);
  }, [profileId, preference, loadState]);

  useEffect(() => {
    const onProfileChanged = () => {
      const next = window.localStorage.getItem(PROFILE_STORAGE_KEY);
      setProfileId(next);
      if (!next) setState(null);
    };
    window.addEventListener('skillscope-profile-changed', onProfileChanged);
    return () => window.removeEventListener('skillscope-profile-changed', onProfileChanged);
  }, []);

  useEffect(() => {
    setOutput('');
    setCriterionScores({});
    setCriterionNotes({});
    setEnjoyment(''); setDifficulty(''); setConfidence(''); setWillingness(''); setReflection('');
    setInterpretation('not_interpreted');
  }, [state?.next_challenge.challenge_id]);

  const createProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); setBusy(true); setError(null); setNotice(null);
    try {
      const body = await readJson<{ profile_id: string }>(await fetch(`${apiBaseUrl}/api/student-profiles`, {
        method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({
          age_band: createAgeBand, consent_basis: consentBasis(createAgeBand), consent_confirmed: consentConfirmed,
          current_goal: createGoal.trim() || null,
        }), signal: AbortSignal.timeout(8000),
      }));
      window.localStorage.setItem(PROFILE_STORAGE_KEY, body.profile_id);
      setProfileId(body.profile_id);
      window.dispatchEvent(new Event('skillscope-profile-changed'));
      setNotice('Profile created. The loop starts with an unknown evidence history and will update only after an activity is submitted.');
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Profile creation failed.');
    } finally { setBusy(false); }
  };

  const submitChallenge = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!profileId || !state) return;
    const missingObservation = state.next_challenge.rubric.find((criterion) => (criterionScores[criterion.criterion_id] ?? '') !== '' && !(criterionNotes[criterion.criterion_id] ?? '').trim());
    if (missingObservation) {
      setError(`Add an observable note for “${missingObservation.label}” before assigning a numeric score. You may leave the criterion unscored if there is not enough evidence.`);
      return;
    }
    setBusy(true); setError(null); setNotice(null); setLastResult(null);
    const rubricObservations = state.next_challenge.rubric.map((criterion) => {
      const rawScore = criterionScores[criterion.criterion_id] ?? '';
      const note = criterionNotes[criterion.criterion_id]?.trim();
      return {
        criterion_id: criterion.criterion_id,
        score: rawScore === '' ? null : Number(rawScore),
        observation: note || (rawScore === '' ? 'Not observed in this attempt.' : `Observed against the rubric criterion: ${criterion.label}.`),
      };
    });
    try {
      const challengeResult = await readJson<ScoreResult>(await fetch(
        `${apiBaseUrl}/api/challenges/${state.next_challenge.challenge_id}/submissions`,
        { method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
          body: JSON.stringify({
            profile_id: profileId, output: output.trim(), rubric_observations: rubricObservations,
            enjoyment: enjoyment ? Number(enjoyment) : null,
            difficulty_reported: difficulty ? Number(difficulty) : null,
            confidence: confidence ? Number(confidence) : null,
            willingness_to_continue: willingness ? Number(willingness) : null,
            reflection: reflection.trim() || null,
            hypothesis_interpretation: interpretation,
          }), signal: AbortSignal.timeout(10000) },
      ));
      setLastResult(challengeResult);
      window.dispatchEvent(new Event('skillscope-evidence-updated'));
      setNotice('The activity submission and evidence record are confirmed saved. Refreshing the next recommendation…');
      try {
        const nextState = await readJson<LoopState>(await fetch(
          `${apiBaseUrl}/api/discovery-loop/${profileId}?preference=${encodeURIComponent(preference)}`,
          { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(8000) },
        ));
        setState(nextState);
        setNotice('Activity, rubric observations, reflection, and evidence are saved. The next recommendation has been recalculated from the updated history.');
      } catch (refreshError) {
        setError(`The activity was saved, but the next recommendation could not be refreshed. Use “Reload next recommendation” before submitting another activity. ${refreshError instanceof Error ? refreshError.message : ''}`);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? `${requestError.message} Check the saved journey before retrying, in case the server recorded the request.` : 'The submission did not return a confirmed result. Reload the journey before retrying.');
    } finally { setBusy(false); }
  };

  return (
    <section id="discovery-loop" className="border-t border-slate-200/80 py-12 sm:py-16" aria-labelledby="discovery-loop-heading">
      <div className="mx-auto max-w-7xl">
        <div className="grid gap-6 lg:grid-cols-[0.72fr_1.28fr] lg:items-end">
          <div>
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Longitudinal discovery</p>
            <h1 id="discovery-loop-heading" className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">One activity changes the next step.</h1>
          </div>
          <p className="max-w-3xl text-sm leading-7 text-slate-600 sm:text-base">SkillScope saves the observable task result and your reflection separately. The next activity is selected from recorded exposure, your stated interpretation, and your chosen journey preference—not from a hidden personality or career-fit score.</p>
        </div>

        {!profileId ? (
          <form onSubmit={createProfile} className="mt-7 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-7">
            <h3 className="text-xl font-semibold text-ink">Start a saved discovery journey</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">This creates a pseudonymous profile so activity history can persist across refreshes. For ages 10–17, the prototype requires a guardian-consent confirmation; age 18+ uses student-confirmed consent.</p>
            <div className="mt-5 grid gap-4 md:grid-cols-2">
              <div><label htmlFor="loop-age" className="text-sm font-semibold text-slate-700">Age group</label><select id="loop-age" value={createAgeBand} onChange={(event) => setCreateAgeBand(event.target.value as AgeBand)} className={inputClass}><option value="10_14">10–14</option><option value="15_17">15–17</option><option value="18_plus">18+</option></select></div>
              <div><label htmlFor="loop-goal" className="text-sm font-semibold text-slate-700">Current goal or question (optional)</label><input id="loop-goal" value={createGoal} onChange={(event) => setCreateGoal(event.target.value)} maxLength={500} className={inputClass} placeholder="e.g. I want to test whether I enjoy building things" /></div>
            </div>
            <label className="mt-4 flex items-start gap-3 rounded-xl border border-slate-100 bg-slate-50 p-3.5 text-sm leading-6 text-slate-600"><input type="checkbox" checked={consentConfirmed} onChange={(event) => setConsentConfirmed(event.target.checked)} required className="mt-1" /><span>{createAgeBand === '18_plus' ? 'I confirm student consent for storing the profile and activity evidence.' : 'I confirm appropriate guardian consent for storing this profile and activity evidence.'} <strong className="font-semibold text-slate-800">This prototype records a self-attestation and does not verify identity or guardian authority.</strong></span></label>
            <button type="submit" disabled={!consentConfirmed || busy} className="mt-5 rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-50">{busy ? 'Creating profile…' : 'Create profile and start'}</button>
          </form>
        ) : null}

        {error ? <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">{error}</div> : null}
        {notice ? <div className="mt-5 rounded-xl border border-teal-100 bg-teal-50 p-4 text-sm leading-6 text-teal-900" role="status">{notice}</div> : null}
        {profileId && error && state ? <button type="button" onClick={() => void loadState(profileId, preference)} disabled={loading} className="mt-3 rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm font-semibold text-slate-700 disabled:opacity-50">{loading ? 'Refreshing…' : 'Reload next recommendation'}</button> : null}

        {profileId && loading && !state ? <div className="mt-7 rounded-2xl border border-slate-200 bg-white p-8 text-sm text-slate-500">Loading the saved discovery journey…</div> : null}

        {state ? (
          <div className="mt-7 grid gap-5 xl:grid-cols-[0.72fr_1.28fr]">
            <aside className="space-y-5">
              <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
                <div className="flex flex-wrap items-center justify-between gap-2"><span className="rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">{state.mode.replaceAll('_', ' ')}</span><span className="text-xs text-slate-400">Policy {state.loop_policy_version}</span></div>
                <h3 className="mt-4 text-xl font-semibold text-ink">Your journey so far</h3>
                <div className="mt-4 grid grid-cols-2 gap-3">
                  <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Activities saved</p><p className="mt-1 text-2xl font-semibold text-ink">{state.total_submissions}</p></div>
                  <div className="rounded-xl bg-slate-50 p-3"><p className="text-xs text-slate-500">Evidence records</p><p className="mt-1 text-2xl font-semibold text-ink">{state.evidence_count}</p></div>
                </div>
                <label htmlFor="loop-preference" className="mt-5 block text-sm font-semibold text-slate-700">What should the next step prioritize?</label>
                <select id="loop-preference" value={preference} onChange={(event) => setPreference(event.target.value as Preference)} className={inputClass}>
                  {(Object.keys(preferenceLabels) as Preference[]).map((key) => <option key={key} value={key}>{preferenceLabels[key]}</option>)}
                </select>
                <p className="mt-2 text-xs leading-5 text-slate-500">This preference is applied when this page refreshes the recommendation. It does not erase or rewrite evidence.</p>
                {state.current_goal ? <div className="mt-4 border-t border-slate-100 pt-4"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Stated goal</p><p className="mt-1.5 text-sm leading-6 text-slate-700">{state.current_goal}</p><p className="mt-1 text-xs text-slate-400">The loop does not infer domain relevance from free-text goals.</p></div> : null}
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
                <h3 className="font-semibold text-ink">Coverage, not a ranking</h3>
                <p className="mt-1.5 text-xs leading-5 text-slate-500">Unseen means unknown—not low ability or low interest.</p>
                <div className="mt-4 space-y-2.5">{state.domain_exposure.map((item) => <div key={item.domain} className="flex items-center justify-between gap-3 text-sm"><span className="text-slate-700">{domainLabels[item.domain]}</span><span className={`shrink-0 rounded-lg px-2 py-1 text-xs ${item.submission_count === 0 ? 'bg-slate-100 text-slate-500' : 'bg-teal-50 text-teal-800'}`}>{item.submission_count === 0 ? 'Unexplored' : `${item.submission_count} attempt${item.submission_count === 1 ? '' : 's'}`}</span></div>)}</div>
              </div>

              {state.last_completion ? <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Previous activity</p><h3 className="mt-1.5 font-semibold text-ink">{state.last_completion.title}</h3><p className="mt-1.5 text-sm leading-6 text-slate-600">{state.last_completion.evidence_status.replaceAll('_', ' ')} · {state.last_completion.observed_criteria} rubric criteria observed</p>{state.last_completion.objective_score !== null ? <p className="mt-2 text-sm font-semibold text-teal-800">Task-local result: {state.last_completion.objective_score}/{state.last_completion.objective_max_score}</p> : <p className="mt-2 text-sm text-amber-800">No objective score—there was not enough observed rubric evidence.</p>}<p className="mt-2 text-xs leading-5 text-slate-500">Interpretation: {state.last_completion.interpretation.replaceAll('_', ' ')}. This is the student's own report, not an AI conclusion.</p></div> : null}
            </aside>

            <div className="space-y-5">
              <div className="rounded-2xl border border-teal-100 bg-gradient-to-br from-teal-50/80 to-white p-5 sm:p-7">
                <div className="flex flex-wrap items-center gap-2"><span className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-teal-800">Next suggested activity</span><span className="text-xs text-slate-500">{state.next_challenge.expected_minutes} min · {state.next_challenge.difficulty} · safety {state.next_challenge.safety_rating}</span></div>
                <h3 className="mt-3 text-2xl font-semibold tracking-tight text-ink">{state.next_challenge.title}</h3>
                <p className="mt-2 text-sm font-medium text-teal-800">{domainLabels[state.next_challenge.domain]} · {state.next_challenge.skill_tags.join(' · ')}</p>
                <p className="mt-4 text-sm leading-7 text-slate-700">{state.next_challenge.instructions}</p>
                <div className="mt-4 grid gap-3 md:grid-cols-2"><div className="rounded-xl border border-white bg-white/80 p-3.5"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Expected output</p><p className="mt-1.5 text-sm leading-6 text-slate-700">{state.next_challenge.expected_output}</p></div><div className="rounded-xl border border-white bg-white/80 p-3.5"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">Materials</p><p className="mt-1.5 text-sm leading-6 text-slate-700">{state.next_challenge.materials.join(', ') || 'No special materials required.'}</p>{state.next_challenge.accessibility_notes.length ? <p className="mt-1.5 text-xs leading-5 text-slate-500">Accessible alternatives: {state.next_challenge.accessibility_notes.join(' ')}</p> : null}</div></div>
                <div className="mt-4 rounded-xl border border-teal-100 bg-white p-4"><p className="text-xs font-bold uppercase tracking-wide text-teal-800">Why this task, now?</p><p className="mt-1.5 text-sm leading-6 text-slate-700">{state.next_challenge.rationale}</p><p className="mt-2 text-xs leading-5 text-slate-500">{state.next_challenge.why_this_now}</p></div>
              </div>

              <form onSubmit={submitChallenge} className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-7">
                <h3 className="text-xl font-semibold text-ink">Complete and reflect</h3>
                <p className="mt-1.5 text-sm leading-6 text-slate-600">Score only what you observed in the work. Leave a criterion unscored if the submission does not provide enough evidence.</p>
                <div className="mt-5"><label htmlFor="loop-output" className="text-sm font-semibold text-slate-700">Your output or work summary</label><textarea id="loop-output" required minLength={1} maxLength={5000} value={output} onChange={(event) => setOutput(event.target.value)} className={`${inputClass} min-h-28`} placeholder="Describe the artifact, solution, observation, or steps you actually completed." /></div>

                <div className="mt-6 space-y-3"><h4 className="text-sm font-bold text-slate-800">Visible rubric · score and observation</h4>{state.next_challenge.rubric.map((criterion) => <div key={criterion.criterion_id} className="rounded-xl border border-slate-100 bg-slate-50/70 p-4"><div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between"><div className="max-w-2xl"><p className="text-sm font-semibold text-slate-800">{criterion.label}</p><p className="mt-1 text-xs leading-5 text-slate-500">{criterion.observable_description}</p></div><div className="sm:w-40"><label htmlFor={`score-${criterion.criterion_id}`} className="text-xs font-semibold text-slate-600">Observed score</label><select id={`score-${criterion.criterion_id}`} value={criterionScores[criterion.criterion_id] ?? ''} onChange={(event) => setCriterionScores((previous) => ({ ...previous, [criterion.criterion_id]: event.target.value }))} className={inputClass}><option value="">Not observed</option>{Array.from({ length: criterion.max_score + 1 }, (_, score) => <option key={score} value={String(score)}>{score}/{criterion.max_score}</option>)}</select></div></div><label htmlFor={`note-${criterion.criterion_id}`} className="mt-3 block text-xs font-semibold text-slate-600">What did you observe? (required when scored)</label><input id={`note-${criterion.criterion_id}`} maxLength={500} value={criterionNotes[criterion.criterion_id] ?? ''} onChange={(event) => setCriterionNotes((previous) => ({ ...previous, [criterion.criterion_id]: event.target.value }))} className={inputClass} placeholder="Point to evidence in the submitted work when a score is selected." /></div>)}</div>

                <div className="mt-6"><h4 className="text-sm font-bold text-slate-800">Your experience (separate from the rubric)</h4><p className="mt-1 text-xs leading-5 text-slate-500">Optional 1–5 self-reports. They do not change the objective task result.</p><div className="mt-3 grid gap-3 sm:grid-cols-2">{([{ id: 'loop-enjoyment', label: 'Enjoyment', value: enjoyment, set: setEnjoyment }, { id: 'loop-difficulty', label: 'How difficult did it feel?', value: difficulty, set: setDifficulty }, { id: 'loop-confidence', label: 'Confidence in your approach', value: confidence, set: setConfidence }, { id: 'loop-willingness', label: 'Willingness to continue', value: willingness, set: setWillingness }] as const).map((field) => <div key={field.id}><label htmlFor={field.id} className="text-xs font-semibold text-slate-600">{field.label}</label><select id={field.id} value={field.value} onChange={(event) => field.set(event.target.value)} className={inputClass}><option value="">Skip</option>{[1, 2, 3, 4, 5].map((score) => <option key={score} value={String(score)}>{score} — {score === 1 ? 'Low' : score === 5 ? 'High' : 'Middle'}</option>)}</select></div>)}</div></div>

                <div className="mt-6"><label htmlFor="loop-interpretation" className="text-sm font-semibold text-slate-700">How did this activity relate to your current idea?</label><select id="loop-interpretation" value={interpretation} onChange={(event) => setInterpretation(event.target.value as Interpretation)} className={inputClass}><option value="not_interpreted">I am not sure / skip</option><option value="supports_current_hypothesis">It supports my current idea</option><option value="challenges_current_hypothesis">It challenges my current idea</option><option value="contextual_or_mixed">It depends on context / the result is mixed</option></select><p className="mt-1.5 text-xs leading-5 text-slate-500">This self-report can affect the next task's focus. It does not prove or disprove a career direction.</p></div>
                <div className="mt-4"><label htmlFor="loop-reflection" className="text-sm font-semibold text-slate-700">Reflection (optional)</label><textarea id="loop-reflection" value={reflection} onChange={(event) => setReflection(event.target.value)} maxLength={1500} className={`${inputClass} min-h-20`} placeholder={state.next_challenge.reflection_prompts.join(' ')} /></div>
                <button type="submit" disabled={busy || !output.trim() || lastResult?.challenge_id === state.next_challenge.challenge_id} className="mt-5 rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white transition hover:bg-slate-800 disabled:cursor-wait disabled:opacity-50">{busy ? 'Saving activity and updating next step…' : lastResult?.challenge_id === state.next_challenge.challenge_id ? 'Already saved · refresh next step' : 'Save activity & update next step'}</button>
              </form>

              {lastResult ? <div className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6" role="status"><p className="text-xs font-bold uppercase tracking-wide text-teal-800">Activity saved</p><h3 className="mt-1.5 text-lg font-semibold text-ink">Rubric result: {lastResult.objective_score === null ? 'Not enough evidence' : `${lastResult.objective_score}/${lastResult.objective_max_score}`}</h3><p className="mt-2 text-sm leading-6 text-slate-600">{lastResult.explanation}</p></div> : null}
              {state.last_completion ? <div className="rounded-2xl border border-slate-200 bg-slate-50 p-5"><p className="text-xs font-bold uppercase tracking-wide text-slate-500">What changed</p><p className="mt-2 text-sm leading-6 text-slate-700">{state.what_changed}</p><p className="mt-2 text-sm font-semibold text-slate-800">Next: {state.next_step}</p></div> : null}
              <p className="text-xs leading-5 text-slate-400">{state.notice} No reminders or background monitoring are running. Loop version {state.loop_policy_version}.</p>
            </div>
          </div>
        ) : null}
        {state?.limitations?.length ? <details className="mt-5 rounded-xl border border-slate-200 bg-white p-4"><summary className="cursor-pointer text-sm font-semibold text-slate-700">Method and prototype limitations</summary><ul className="mt-3 space-y-1.5 pl-5 text-xs leading-5 text-slate-500 marker:text-slate-400">{state.limitations.map((limitation) => <li key={limitation} className="list-disc">{limitation}</li>)}</ul></details> : null}
      </div>
    </section>
  );
}
