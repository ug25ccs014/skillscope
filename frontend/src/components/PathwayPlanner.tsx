import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react';

type AgeBand = '10_14' | '15_17' | '18_plus';
type Timeline = 'unspecified' | '30_days' | '60_days' | '90_days' | '6_months' | '12_months';
type SourceReference = {
  source_id: string; source_record_id: string; title: string; publisher: string;
  record_uri: string | null; source_version: string | null; geography: string | null;
  quality_status: string; notes: string[];
};
type PathwayFact = { fact_kind: string; statement: string; source: SourceReference };
type PlanAction = {
  step_id: string; order: number; phase: string; time_horizon_days: number | null;
  time_horizon_label: string | null; action_type: string; title: string; why_this_step: string;
  instructions: string[]; expected_outcome: string; estimated_hours_min: number | null;
  estimated_hours_max: number | null; skill_labels: string[]; evidence_ids: string[];
  source_references: SourceReference[]; prerequisite_status: string; prerequisite_note: string;
  action_origin: string;
};
type PathwayOption = {
  pathway_id: string; label: string; occupation_node_id: string | null; taxonomy: string | null;
  geography: string | null; recommendation_category: string; evidence_confidence: string;
  why_plausible: string[]; skill_or_interest_matches: string[]; what_remains_unknown: string[];
  pathway_facts: PathwayFact[]; validation_actions: PlanAction[]; comparison_note: string;
};
type SkillGap = {
  skill_label: string; status: 'self_reported_in_current_state' | 'mentioned_in_evidence' | 'not_yet_documented';
  explanation: string; source_references: SourceReference[];
};
type Requirement = {
  label: string; status: 'source_backed_requirement' | 'source_backed_work_context' | 'not_available_in_catalog';
  statement: string; is_prerequisite: boolean | null; source_references: SourceReference[]; limitations: string[];
};
type PathwayPlan = {
  plan_id: string; profile_id: string; age_band: AgeBand; mode: string; algorithm_version: string;
  recommendation_algorithm_version: string; current_goal: string | null; previous_goal: string | null;
  goal_change_detected: boolean; goal_change_handling: string; created_at: string;
  inputs_used: Record<string, string | number | null>; pathway_options: PathwayOption[];
  skills_to_check_or_develop: SkillGap[]; requirements_and_sources: Requirement[]; actions: PlanAction[];
  timebox: { status: 'time_bounded' | 'missing_inputs' | 'not_applicable_age_mode'; requested_timeline: Timeline; explanation: string; missing_inputs: string[]; available_hours_per_week: number | null };
  revision_instructions: string[]; limitations: string[];
};
type PlanHistoryItem = { plan_id: string; created_at: string; current_goal: string | null; age_band: AgeBand; goal_change_detected: boolean; action_count: number; pathway_count: number; algorithm_version: string };
type StudentProfile = { profile_id: string; age_band: AgeBand; current_goal: string | null };
type Props = { apiBaseUrl: string };

const PROFILE_STORAGE_KEY = 'skillscope_student_evidence_profile_v1';
const fieldClass = 'mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10';
const buttonClass = 'inline-flex items-center justify-center rounded-full bg-ink px-6 py-3.5 text-sm font-bold text-white shadow-soft transition hover:-translate-y-0.5 hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/25 disabled:cursor-wait disabled:opacity-60';

async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status}).`;
    try { const body = await response.json() as { detail?: unknown }; if (typeof body.detail === 'string') message = body.detail; } catch { /* keep safe status */ }
    throw new Error(message.slice(0, 900));
  }
  return await response.json() as T;
}
function dateLabel(value: string) {
  try { return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)); }
  catch { return value; }
}
function ageLabel(age: AgeBand) { return age === '10_14' ? '10–14' : age === '15_17' ? '15–17' : '18+'; }
function SourceLine({ source }: { source: SourceReference }) {
  return <div className="mt-2 rounded-2xl bg-slate-50 p-3 text-xs leading-5 text-slate-600"><p className="font-semibold text-slate-800">{source.title} · {source.publisher}</p><p>{source.source_version ?? 'Version not specified'} · {source.geography ?? 'Geography not specified'}</p>{source.record_uri ? <a className="mt-1 inline-block font-semibold text-teal-800 underline underline-offset-4" href={source.record_uri} target="_blank" rel="noopener noreferrer">Open source</a> : null}</div>;
}

const skillStatusLabel: Record<SkillGap['status'], string> = {
  self_reported_in_current_state: 'You listed this',
  mentioned_in_evidence: 'In your evidence',
  not_yet_documented: 'Not recorded yet',
};
const skillStatusStyle: Record<SkillGap['status'], string> = {
  self_reported_in_current_state: 'bg-emerald-50 text-emerald-800',
  mentioned_in_evidence: 'bg-sky-50 text-sky-800',
  not_yet_documented: 'bg-slate-100 text-slate-600',
};
const goalIdeas = ['Software engineering', 'Design', 'Health sciences'];
const sectionTitle = 'font-display text-2xl font-semibold tracking-tight text-ink sm:text-3xl';
const detailsSummary = 'cursor-pointer text-sm font-semibold text-teal-800';

export default function PathwayPlanner({ apiBaseUrl }: Props) {
  const [profileId, setProfileId] = useState<string | null>(() => typeof window !== 'undefined' ? window.localStorage.getItem(PROFILE_STORAGE_KEY) : null);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [plan, setPlan] = useState<PathwayPlan | null>(null);
  const [history, setHistory] = useState<PlanHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [goal, setGoal] = useState('');
  const [skills, setSkills] = useState('');
  const [education, setEducation] = useState('');
  const [experience, setExperience] = useState('');
  const [constraints, setConstraints] = useState('');
  const [weeklyHours, setWeeklyHours] = useState('');
  const [timeline, setTimeline] = useState<Timeline>('unspecified');
  const resultsRef = useRef<HTMLDivElement | null>(null);


  const loadPlan = useCallback(async (id: string) => {
    setLoading(true); setError(null);
    try {
      const nextProfile = await parseResponse<StudentProfile>(await fetch(`${apiBaseUrl}/api/student-profiles/${id}`, { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(7000) }));
      setProfile(nextProfile); setGoal(nextProfile.current_goal ?? '');
      const [planResponse, historyResponse] = await Promise.all([
        fetch(`${apiBaseUrl}/api/pathway-plans/${id}`, { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(8000) }),
        fetch(`${apiBaseUrl}/api/pathway-plans/${id}/history?limit=10`, { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(8000) }),
      ]);
      if (planResponse.ok) setPlan(await planResponse.json() as PathwayPlan); else setPlan(null);
      if (historyResponse.ok) setHistory(await historyResponse.json() as PlanHistoryItem[]); else setHistory([]);
    } catch (e) {
      setError(e instanceof Error ? `${e.message} Please try again.` : 'Could not load the pathway planner.');
    } finally { setLoading(false); }
  }, [apiBaseUrl]);

  useEffect(() => { if (profileId) void loadPlan(profileId); else { setPlan(null); setHistory([]); setProfile(null); } }, [profileId, loadPlan]);

  useEffect(() => {
    const syncProfile = () => {
      const nextId = window.localStorage.getItem(PROFILE_STORAGE_KEY);
      if (nextId !== profileId) {
        setProfileId(nextId);
        setPlan(null); setHistory([]); setProfile(null); setError(null);
      } else if (nextId) {
        // A saved goal or evidence update can change the current plan even when profile ID stays put.
        void loadPlan(nextId);
      }
    };
    window.addEventListener('skillscope-profile-changed', syncProfile);
    return () => window.removeEventListener('skillscope-profile-changed', syncProfile);
  }, [profileId, loadPlan]);

  const generate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!profileId || !profile) return;
    setBusy(true); setError(null);
    const request: Record<string, string | number | null> = { current_goal: goal.trim() || null };
    if (profile.age_band === '18_plus') {
      request.current_skills_summary = skills.trim() || null;
      request.education_summary = education.trim() || null;
      request.experience_summary = experience.trim() || null;
      request.planning_constraints = constraints.trim() || null;
      request.available_hours_per_week = weeklyHours ? Number(weeklyHours) : null;
      request.desired_timeline = timeline;
    }
    try {
      const response = await fetch(`${apiBaseUrl}/api/pathway-plans/${profileId}/generate`, {
        method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify(request), signal: AbortSignal.timeout(20000),
      });
      const updated = await parseResponse<PathwayPlan>(response);
      setPlan(updated);
      await loadPlan(profileId);
      window.requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }));
      if (updated.goal_change_detected) {
        // Refresh the evidence ledger and discovery-loop panels without replacing profile identity.
        window.dispatchEvent(new Event('skillscope-profile-changed'));
      }
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not generate a plan.'); }
    finally { setBusy(false); }
  };

  const modeName = profile ? (profile.age_band === '10_14' ? 'Discover & Shape' : profile.age_band === '15_17' ? 'Explore & Validate' : 'Develop & Optimize') : '';

  return (
    <section id="pathway-planner" className="py-10 sm:py-14" aria-labelledby="pathway-planner-heading">
      <div className="mx-auto max-w-4xl">
        <div className="text-center">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Your plan</p>
          <h1 id="pathway-planner-heading" className="mt-2 font-display text-4xl font-semibold tracking-tight text-ink sm:text-5xl">Turn ideas into next steps.</h1>
          <p className="mx-auto mt-3 max-w-xl text-base leading-7 text-slate-600">Tell us what you want to work toward. We will give you small steps to try.</p>
        </div>

        {!profileId ? (
          <div className="mt-8 rounded-[2rem] border border-white bg-white/90 p-8 text-center shadow-soft">
            <p className="text-lg font-semibold text-ink">First, create your profile</p>
            <p className="mt-1 text-sm text-slate-600">It takes a minute, and your plan is built from it.</p>
            <a href="#/profile" className={`${buttonClass} mt-5`}>Create my profile</a>
          </div>
        ) : null}
        {profileId && loading && !profile ? <p className="mt-8 text-center text-sm text-slate-500">Loading your plan…</p> : null}
        {error ? <div role="alert" className="mt-6 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-800">{error}</div> : null}

        {profile ? <div className="mt-8 space-y-8">
          {/* STEP 1: goal */}
          <form onSubmit={generate} className="rounded-[2rem] border border-white bg-white/90 p-6 shadow-soft sm:p-8">
            <div className="flex flex-wrap items-center gap-3">
              <span className="grid h-9 w-9 place-items-center rounded-full bg-gradient-to-br from-teal-400 to-sky-500 text-sm font-bold text-white">1</span>
              <h2 className="text-xl font-semibold text-ink">What do you want to work toward?</h2>
              <span className="ml-auto rounded-full bg-teal-50 px-3 py-1 text-xs font-semibold text-teal-800">Ages {ageLabel(profile.age_band)} · {modeName}</span>
            </div>
            <label htmlFor="pathway-goal" className="sr-only">Your goal</label>
            <textarea id="pathway-goal" className={fieldClass} rows={2} maxLength={500} value={goal} onChange={(e) => setGoal(e.target.value)} placeholder={profile.age_band === '10_14' ? 'What would you like to try next?' : 'For example: become a designer, or learn to code'} />
            {!goal.trim() ? (
              <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-slate-500">
                <span>Ideas:</span>
                {goalIdeas.map((idea) => <button key={idea} type="button" onClick={() => setGoal(idea)} className="rounded-full border border-slate-200 bg-white px-3.5 py-1.5 text-xs font-semibold text-slate-700 transition hover:border-teal-400 hover:text-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500">{idea}</button>)}
              </div>
            ) : null}
            <p className="mt-3 text-xs text-slate-500">Not sure yet? Leave it empty and we will show you some options.</p>

            {profile.age_band === '18_plus' ? (
              <details className="mt-5 rounded-2xl bg-slate-50 p-4">
                <summary className={detailsSummary}>Want a plan with dates? Add a few details (optional)</summary>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <label htmlFor="pathway-skills" className="block text-sm font-semibold text-slate-700 sm:col-span-2">Skills you already have<textarea id="pathway-skills" className={fieldClass} rows={2} maxLength={1800} value={skills} onChange={(e) => setSkills(e.target.value)} placeholder="Tools, languages, strengths" /></label>
                  <label htmlFor="pathway-education" className="block text-sm font-semibold text-slate-700">Education or learning<textarea id="pathway-education" className={fieldClass} rows={2} maxLength={1500} value={education} onChange={(e) => setEducation(e.target.value)} placeholder="Courses, self-study" /></label>
                  <label htmlFor="pathway-experience" className="block text-sm font-semibold text-slate-700">Projects or work<textarea id="pathway-experience" className={fieldClass} rows={2} maxLength={1800} value={experience} onChange={(e) => setExperience(e.target.value)} placeholder="Projects, jobs, volunteering" /></label>
                  <label htmlFor="pathway-constraints" className="block text-sm font-semibold text-slate-700 sm:col-span-2">Anything that limits you <span className="font-normal text-slate-500">(optional)</span><textarea id="pathway-constraints" className={fieldClass} rows={2} maxLength={1200} value={constraints} onChange={(e) => setConstraints(e.target.value)} placeholder="Budget, schedule, equipment, location" /></label>
                  <label htmlFor="pathway-hours" className="block text-sm font-semibold text-slate-700">Hours free per week<input id="pathway-hours" className={fieldClass} type="number" min="1" max="80" value={weeklyHours} onChange={(e) => setWeeklyHours(e.target.value)} placeholder="e.g. 5" /></label>
                  <label htmlFor="pathway-timeline" className="block text-sm font-semibold text-slate-700">How soon?<select id="pathway-timeline" className={fieldClass} value={timeline} onChange={(e) => setTimeline(e.target.value as Timeline)}><option value="unspecified">Not decided</option><option value="30_days">30 days</option><option value="60_days">60 days</option><option value="90_days">90 days</option><option value="6_months">6 months</option><option value="12_months">12 months</option></select></label>
                </div>
              </details>
            ) : profile.age_band === '10_14' ? <p className="mt-3 text-xs text-slate-500">No deadlines. Just something small to try.</p> : null}

            <button type="submit" disabled={busy || loading} className={`${buttonClass} mt-6 w-full sm:w-auto`}>{busy ? 'Making your plan…' : plan ? 'Update my plan' : 'Make my plan'}</button>
            {plan?.goal_change_detected ? <p className="mt-3 text-xs text-teal-800">Your goal changed. Your earlier evidence is kept.</p> : null}
          </form>

          {/* Empty state */}
          {!plan ? (
            <div className="rounded-[2rem] border-2 border-dashed border-slate-300/80 bg-white/50 p-10 text-center">
              <div className="mx-auto grid h-16 w-16 place-items-center rounded-full bg-gradient-to-br from-amber-200 to-rose-200 text-ink"><svg aria-hidden="true" viewBox="0 0 24 24" className="h-8 w-8" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d="M5 19c4 0 3-6 7-6s3-6 7-6M5 19h.01M19 7h.01" /></svg></div>
              <p className="mt-4 text-lg font-semibold text-ink">Your plan will show up here</p>
              <p className="mt-1 text-sm text-slate-600">Press “Make my plan” above.</p>
            </div>
          ) : (
            <div ref={resultsRef} className="scroll-mt-28 space-y-10">
              {/* Summary */}
              <div className="relative overflow-hidden rounded-[2rem] bg-gradient-to-br from-ink via-[#16384A] to-[#1B1F4D] p-7 text-white shadow-soft sm:p-9">
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-200">Your plan</p>
                <h2 className="mt-2 font-display text-3xl font-semibold tracking-tight sm:text-4xl">{plan.current_goal || 'Exploring your options'}</h2>
                <div className="mt-4 flex flex-wrap gap-2 text-xs font-semibold">
                  <span className="rounded-full bg-white/15 px-3 py-1.5">{plan.actions.length} steps</span>
                  <span className="rounded-full bg-white/15 px-3 py-1.5">{plan.pathway_options.length} paths to explore</span>
                  <span className="rounded-full bg-white/15 px-3 py-1.5">Saved {dateLabel(plan.created_at)}</span>
                </div>
                {plan.age_band === '18_plus' && plan.timebox.status === 'missing_inputs' ? <p className="mt-4 text-sm text-white/80">Want dates on your steps? Open “Want a plan with dates?” above and add your free hours and how soon.</p> : null}
              </div>

              {/* STEP 2: next steps */}
              {plan.actions.length ? (
                <div>
                  <h2 className={sectionTitle}>Do this next</h2>
                  <ol className="relative mt-6 space-y-4">
                    <span aria-hidden="true" className="absolute bottom-6 left-[1.35rem] top-6 w-0.5 bg-gradient-to-b from-teal-300 via-sky-300 to-indigo-300" />
                    {plan.actions.map((action, i) => (
                      <li key={action.step_id} className="relative flex gap-4">
                        <span className="relative z-10 grid h-11 w-11 shrink-0 place-items-center rounded-full bg-gradient-to-br from-teal-400 to-sky-500 text-base font-bold text-white shadow-lg ring-4 ring-[#F7F9FC]">{action.order}</span>
                        <div className="min-w-0 flex-1 rounded-[1.75rem] border border-white bg-white/90 p-5 shadow-sm">
                          <div className="flex flex-wrap items-center gap-2">
                            <h3 className="text-lg font-semibold text-ink">{action.title}</h3>
                            {i === 0 ? <span className="rounded-full bg-amber-100 px-2.5 py-1 text-[11px] font-bold text-amber-900">Start here</span> : null}
                            {action.time_horizon_label ? <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-800">{action.time_horizon_label}</span> : null}
                            {action.estimated_hours_min !== null && action.estimated_hours_max !== null ? <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">{action.estimated_hours_min}–{action.estimated_hours_max} hrs</span> : null}
                          </div>
                          <p className="mt-2 text-sm leading-6 text-slate-600">{action.why_this_step}</p>
                          <details className="mt-3">
                            <summary className={detailsSummary}>How to do it</summary>
                            <ul className="mt-2 space-y-1.5 pl-5 text-sm leading-6 text-slate-700 marker:text-teal-500">{action.instructions.map((instruction, index) => <li key={index} className="list-disc">{instruction}</li>)}</ul>
                            <p className="mt-3 rounded-2xl bg-teal-50 p-3 text-sm leading-6 text-teal-900"><span className="font-semibold">You will have: </span>{action.expected_outcome}</p>
                            {action.prerequisite_note ? <p className="mt-2 text-xs leading-5 text-slate-500">{action.prerequisite_note}</p> : null}
                            {action.source_references.map((source, j) => <SourceLine key={`${source.source_record_id}-${j}`} source={source} />)}
                          </details>
                        </div>
                      </li>
                    ))}
                  </ol>
                </div>
              ) : null}

              {/* STEP 3: paths */}
              {plan.pathway_options.length ? (
                <div>
                  <h2 className={sectionTitle}>Paths to explore</h2>
                  <p className="mt-2 text-sm text-slate-600">These are ideas to test, not a final answer.</p>
                  <div className="mt-6 grid gap-4 md:grid-cols-2">
                    {plan.pathway_options.map((option) => (
                      <article key={option.pathway_id} className="flex flex-col rounded-[1.75rem] border border-white bg-white/90 p-5 shadow-sm">
                        <span className="self-start rounded-full bg-indigo-50 px-3 py-1 text-[11px] font-bold text-indigo-800">Evidence: {option.evidence_confidence}</span>
                        <h3 className="mt-3 font-display text-xl font-semibold leading-snug text-ink">{option.label}</h3>
                        {option.why_plausible[0] ? <p className="mt-2 text-sm leading-6 text-slate-600">{option.why_plausible[0]}</p> : null}
                        {option.skill_or_interest_matches.length ? <div className="mt-3 flex flex-wrap gap-1.5">{option.skill_or_interest_matches.slice(0, 4).map((m) => <span key={m} className="rounded-full bg-teal-50 px-2.5 py-1 text-[11px] font-semibold text-teal-800">{m}</span>)}</div> : null}
                        <details className="mt-4">
                          <summary className={detailsSummary}>See why and how to test it</summary>
                          {option.why_plausible.length > 1 ? <ul className="mt-2 space-y-1.5 pl-5 text-sm leading-6 text-slate-600">{option.why_plausible.slice(1).map((reason, index) => <li key={index} className="list-disc">{reason}</li>)}</ul> : null}
                          {option.what_remains_unknown.length ? <><p className="mt-3 text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Still unknown</p><ul className="mt-1 space-y-1.5 pl-5 text-xs leading-5 text-slate-600">{option.what_remains_unknown.map((item, index) => <li key={index} className="list-disc">{item}</li>)}</ul></> : null}
                          {option.validation_actions.length ? <><p className="mt-3 text-xs font-bold uppercase tracking-[0.12em] text-slate-500">Try this</p>{option.validation_actions.map((step) => <div key={step.step_id} className="mt-2 rounded-2xl bg-slate-50 p-3"><p className="text-sm font-semibold text-slate-800">{step.title}</p><p className="mt-1 text-xs leading-5 text-slate-600">{step.why_this_step}</p><p className="mt-1 text-xs leading-5 text-slate-600">You will have: {step.expected_outcome}</p>{step.source_references.map((source, i) => <SourceLine key={`${source.source_record_id}-${i}`} source={source} />)}</div>)}</> : null}
                          <p className="mt-3 text-xs leading-5 text-slate-500">{option.comparison_note}</p>
                        </details>
                      </article>
                    ))}
                  </div>
                </div>
              ) : null}

              {/* Skills */}
              {plan.skills_to_check_or_develop.length ? (
                <div>
                  <h2 className={sectionTitle}>Skills to build</h2>
                  <p className="mt-2 text-sm text-slate-600">“Not recorded yet” only means we have no record. It does not mean you lack the skill.</p>
                  <div className="mt-5 flex flex-wrap gap-2.5">
                    {plan.skills_to_check_or_develop.map((gap) => (
                      <span key={gap.skill_label} className="inline-flex items-center gap-2 rounded-full border border-white bg-white/90 py-2 pl-4 pr-2 text-sm font-semibold text-ink shadow-sm">
                        {gap.skill_label}
                        <span className={`rounded-full px-2.5 py-1 text-[11px] font-semibold ${skillStatusStyle[gap.status]}`}>{skillStatusLabel[gap.status]}</span>
                      </span>
                    ))}
                  </div>
                  <details className="mt-4 rounded-2xl bg-white/70 p-4">
                    <summary className={detailsSummary}>See details</summary>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">{plan.skills_to_check_or_develop.map((gap) => <div key={gap.skill_label} className="rounded-2xl bg-slate-50 p-3"><p className="text-sm font-semibold text-slate-800">{gap.skill_label}</p><p className="mt-1 text-xs leading-5 text-slate-600">{gap.explanation}</p>{gap.source_references.map((source, i) => <SourceLine key={`${source.source_record_id}-${i}`} source={source} />)}</div>)}</div>
                  </details>
                </div>
              ) : null}

              {/* Good to know */}
              <details className="rounded-[2rem] border border-white bg-white/80 p-6 shadow-sm">
                <summary className="cursor-pointer text-lg font-semibold text-ink">Good to know</summary>
                <div className="mt-4 space-y-6">
                  {plan.requirements_and_sources.length ? <div><h3 className="font-semibold text-ink">Requirements and sources</h3><p className="mt-1 text-xs leading-5 text-slate-500">Work activities are not entry requirements. Only qualifications linked to a source are marked as prerequisites.</p><div className="mt-3 space-y-3">{plan.requirements_and_sources.map((item, index) => <article key={`${item.label}-${index}`} className="rounded-2xl bg-slate-50 p-4"><p className="font-semibold text-slate-800">{item.label}</p><p className="mt-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{item.status.replaceAll('_', ' ')}{item.is_prerequisite === true ? ' · prerequisite' : item.is_prerequisite === false ? ' · not a prerequisite' : ''}</p><p className="mt-2 text-sm leading-6 text-slate-600">{item.statement}</p>{item.limitations.map((limit) => <p key={limit} className="mt-1 text-xs leading-5 text-slate-500">{limit}</p>)}{item.source_references.map((source, i) => <SourceLine key={`${source.source_record_id}-${i}`} source={source} />)}</article>)}</div></div> : null}
                  <div><h3 className="font-semibold text-ink">Changing your plan</h3><ul className="mt-2 space-y-1.5 pl-5 text-sm leading-6 text-slate-600">{plan.revision_instructions.map((item) => <li key={item} className="list-disc">{item}</li>)}</ul>{plan.goal_change_handling ? <p className="mt-2 text-xs leading-5 text-slate-500">{plan.goal_change_handling}</p> : null}{plan.timebox.explanation ? <p className="mt-2 text-xs leading-5 text-slate-500">{plan.timebox.explanation}</p> : null}{plan.limitations.map((item) => <p key={item} className="mt-2 text-xs leading-5 text-slate-500">{item}</p>)}</div>
                  {history.length > 1 ? <div><h3 className="font-semibold text-ink">Earlier plans ({history.length})</h3><ol className="mt-2 space-y-2">{history.map((item) => <li key={item.plan_id} className="rounded-2xl bg-slate-50 p-3 text-xs leading-5 text-slate-600"><p className="font-semibold text-slate-800">{item.current_goal || 'Exploring options'}{item.goal_change_detected ? ' · goal changed' : ''}</p><p>{dateLabel(item.created_at)} · {item.action_count} steps · {item.pathway_count} paths</p></li>)}</ol></div> : null}
                </div>
              </details>
            </div>
          )}
        </div> : null}
      </div>
    </section>
  );
}
