import { useEffect, useMemo, useState } from 'react';
import TiltCard from '../motion/TiltCard';
import RevealOnScroll from '../motion/RevealOnScroll';

type AgeBand = '10_14' | '15_17' | '18_plus';
type BaselineItemType = 'self_report' | 'mini_activity' | 'reflection';
type BaselineItem = {
  item_id: string;
  item_type: BaselineItemType;
  domain: string;
  prompt: string;
  instructions: string | null;
  options: string[];
  allow_skip: boolean;
  expected_minutes: number;
  age_bands: AgeBand[];
  rubric: string[];
};
type Assessment = {
  assessment_id: string;
  profile_id: string;
  age_band: AgeBand;
  mode: string;
  version: string;
  notice: string;
  items: BaselineItem[];
  expected_minutes: number;
};
type BaselineResponseDraft = { answer: string; skipped: boolean; curiosity: string };
type DomainResult = {
  domain: string;
  evidence_status: string;
  response_count: number;
  skipped_count: number;
  confidence_observed: boolean;
  interpretation: string;
};
type Result = {
  assessment_id: string;
  profile_id: string;
  age_band: AgeBand;
  mode: string;
  version: string;
  statement: string;
  domain_results: DomainResult[];
  evidence_created_count: number;
  next_step: string;
};

type Props = { apiBaseUrl: string };
const PROFILE_STORAGE_KEY = 'skillscope_student_evidence_profile_v1';
const fieldClass = 'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-800 outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10';
const buttonClass = 'inline-flex items-center justify-center rounded-full border border-slate-200 bg-white px-5 py-3 text-sm font-semibold text-slate-700 transition hover:border-teal-300 hover:text-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:cursor-wait disabled:opacity-60';

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status}).`;
    try {
      const body = await response.json() as { detail?: unknown };
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) {
        const first = body.detail.find((item): item is { msg: string } => typeof item === 'object' && item !== null && 'msg' in item && typeof (item as { msg?: unknown }).msg === 'string');
        message = first?.msg ?? message;
      }
    } catch { /* Keep the safe HTTP fallback. */ }
    throw new Error(message.slice(0, 900));
  }
  return await response.json() as T;
}

function labelForAge(age: AgeBand) {
  return age === '10_14' ? '10–14 · Discover & Shape' : age === '15_17' ? '15–17 · Explore & Validate' : '18+ · Develop & Optimize';
}
function prettyDomain(value: string) { return value.replaceAll('_', ' '); }

export default function BaselineAssessment({ apiBaseUrl }: Props) {
  const [profileId, setProfileId] = useState<string | null>(() => typeof window !== 'undefined' ? window.localStorage.getItem(PROFILE_STORAGE_KEY) : null);
  const [assessment, setAssessment] = useState<Assessment | null>(null);
  const [answers, setAnswers] = useState<Record<string, BaselineResponseDraft>>({});
  const [activeIndex, setActiveIndex] = useState(0);
  const [result, setResult] = useState<Result | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const onProfileChanged = () => {
      const next = window.localStorage.getItem(PROFILE_STORAGE_KEY);
      if (next !== profileId) {
        setProfileId(next);
        setAssessment(null);
        setAnswers({});
        setActiveIndex(0);
        setResult(null);
        setError(null);
      }
    };
    window.addEventListener('skillscope-profile-changed', onProfileChanged);
    return () => window.removeEventListener('skillscope-profile-changed', onProfileChanged);
  }, [profileId]);

  const currentItem = assessment?.items[activeIndex] ?? null;
  const currentDraft = currentItem ? answers[currentItem.item_id] ?? { answer: '', skipped: false, curiosity: '' } : null;
  const progress = useMemo(() => assessment?.items.length ? Math.round(((activeIndex + 1) / assessment.items.length) * 100) : 0, [assessment, activeIndex]);

  const issueAssessment = async () => {
    if (!profileId) return;
    setBusy(true); setError(null); setResult(null);
    try {
      const next = await readJson<Assessment>(await fetch(`${apiBaseUrl}/api/baseline-assessments/for/${profileId}`, {
        method: 'POST', headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(10000),
      }));
      setAssessment(next);
      setAnswers(Object.fromEntries(next.items.map((item) => [item.item_id, { answer: '', skipped: false, curiosity: '' }])));
      setActiveIndex(0);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Could not start the baseline. Check the connection and try again.');
    } finally { setBusy(false); }
  };

  const submitResponses = async (activeAnswers: Record<string, BaselineResponseDraft>) => {
    if (!assessment) return;
    setBusy(true); setError(null);
    try {
      const responses = assessment.items.map((item) => {
        const draft = activeAnswers[item.item_id] ?? { answer: '', skipped: false, curiosity: '' };
        const skipped = draft.skipped || !draft.answer.trim();
        return {
          item_id: item.item_id,
          skipped,
          answer: skipped ? null : draft.answer.trim(),
          confidence: draft.curiosity ? Number(draft.curiosity) : null,
        };
      });
      const submitted = await readJson<Result>(await fetch(`${apiBaseUrl}/api/baseline-assessments/submit`, {
        method: 'POST', headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ assessment_id: assessment.assessment_id, responses }), signal: AbortSignal.timeout(15000),
      }));
      setResult(submitted);
      setAssessment(null);
      setAnswers({});
      window.dispatchEvent(new Event('skillscope-profile-changed'));
    } catch (requestError) {
      setError(requestError instanceof Error ? `${requestError.message} Your answers remain in this open page. If the server already accepted the submission, review your evidence profile before retrying.` : 'Could not submit the baseline. Your answers remain in this open page. If the server already accepted the submission, review your evidence profile before retrying.');
    } finally { setBusy(false); }
  };

  const advance = () => {
    if (!assessment || !currentItem || !currentDraft) return;
    if (!currentDraft.skipped && !currentDraft.answer.trim()) {
      setError('Add a short response or use “Skip this item” to continue.');
      return;
    }
    setError(null);
    if (activeIndex < assessment.items.length - 1) setActiveIndex((index) => index + 1);
    else void submitResponses(answers);
  };

  const skipCurrent = () => {
    if (!assessment || !currentItem) return;
    const nextAnswers = { ...answers, [currentItem.item_id]: { answer: '', skipped: true, curiosity: '' } };
    setAnswers(nextAnswers);
    setError(null);
    if (activeIndex < assessment.items.length - 1) setActiveIndex((index) => index + 1);
    else void submitResponses(nextAnswers);
  };

  return (
    <section id="baseline-assessment" className="ss-section scroll-mt-28 border-t border-slate-200/80 py-10 sm:py-14 lg:py-16" aria-labelledby="baseline-assessment-heading">
      <div className="w-full min-w-0">
        <div className="max-w-3xl">
          <p className="ss-section-kicker text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Baseline</p>
          <h1 id="baseline-assessment-heading" className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Start with what you have tried—not a label.</h1>
          <p className="mt-3 text-sm leading-7 text-slate-600 sm:text-base">A short baseline across different domains. It records your responses and exploratory activity evidence; it does not calculate an aptitude score or decide your career.</p>
          <p className="mt-3 rounded-xl border border-teal-100 bg-teal-50/70 p-4 text-sm leading-6 text-teal-950">This is an initial snapshot. It will improve as you try activities and share feedback.</p>
        </div>

        {!profileId ? (
          <div className="mt-6 rounded-2xl border border-dashed border-slate-300 bg-white p-6 sm:p-8">
            <h3 className="text-lg font-semibold text-ink">First, choose what to save</h3>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">Create a pseudonymous evidence profile and review the privacy explanation. For a profile under 18, this prototype requires a guardian-consent confirmation; it does not verify identity or legal authority.</p>
            <a href="#/profile" className={`${buttonClass} mt-4`}>Review profile and consent</a>
          </div>
        ) : result ? (
          <div className="mt-6 space-y-5">
            <div className="rounded-3xl border border-white bg-white/90 p-6 shadow-soft sm:p-8" role="status">
              <p className="text-xs font-bold uppercase tracking-[0.16em] text-teal-700">Baseline saved · {result.version}</p>
              <h3 className="mt-2 text-2xl font-semibold tracking-tight text-ink">Your first snapshot is ready</h3>
              <p className="mt-3 text-sm leading-6 text-slate-600">{result.statement}</p>
              <p className="mt-3 text-sm font-semibold text-slate-800">{result.evidence_created_count} evidence record(s) added.</p>
              <p className="mt-2 text-sm leading-6 text-slate-600">{result.next_step}</p>
            </div>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {result.domain_results.map((domain) => (
                <RevealOnScroll key={domain.domain}><TiltCard className="h-full rounded-2xl border border-slate-200 bg-white shadow-sm"><article className="h-full p-4">
                  <p className="text-sm font-semibold capitalize text-slate-800">{prettyDomain(domain.domain)}</p>
                  <p className={`mt-2 text-xs font-semibold ${domain.evidence_status === 'unknown' ? 'text-amber-800' : 'text-teal-800'}`}>{domain.evidence_status.replaceAll('_', ' ')}</p>
                  <p className="mt-1 text-xs leading-5 text-slate-500">{domain.interpretation}</p>
                  {domain.skipped_count ? <p className="mt-1 text-xs text-slate-400">Skipped: {domain.skipped_count}</p> : null}
                </article></TiltCard></RevealOnScroll>
              ))}
            </div>
            <div className="flex flex-wrap gap-3">
              <a href="#/challenges" className={`${buttonClass} bg-ink text-white hover:border-ink hover:bg-slate-800 hover:text-white`}>Continue to daily activity</a>
              <button type="button" onClick={() => setResult(null)} className={buttonClass}>Start another snapshot</button>
            </div>
            <p className="text-xs leading-5 text-slate-500">A skipped or unanswered domain is shown as unknown, not as a low result. Results are exploratory and not scientifically validated.</p>
          </div>
        ) : assessment && currentItem && currentDraft ? (
          <div className="mt-6 grid gap-5 lg:grid-cols-[0.36fr_0.64fr]">
            <aside className="rounded-2xl border border-slate-200 bg-white p-5 sm:p-6">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-teal-700">{labelForAge(assessment.age_band)}</p>
              <p className="mt-3 text-sm font-semibold text-slate-800">{activeIndex + 1} of {assessment.items.length} prompts</p>
              <div className="mt-2 h-2.5 overflow-hidden rounded-full bg-slate-100" aria-label={`${progress}% complete`} role="progressbar" aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}><div className="baseline-bar h-full rounded-full bg-gradient-to-r from-teal-500 via-sky-500 to-indigo-500" style={{ width: `${progress}%` }} /></div>
              <p className="mt-3 text-xs leading-5 text-slate-500">About {assessment.expected_minutes} minutes · You can skip any item.</p>
              <div className="mt-5 flex flex-wrap gap-1.5">{assessment.items.map((item, index) => <span key={item.item_id} className={`step-dot grid h-7 w-7 place-items-center rounded-full text-[11px] font-semibold ${index === activeIndex ? 'step-dot-active bg-ink text-white' : answers[item.item_id]?.skipped ? 'bg-amber-50 text-amber-900' : answers[item.item_id]?.answer ? 'bg-teal-50 text-teal-900' : 'bg-slate-100 text-slate-500'}`}>{index + 1}</span>)}</div>
            </aside>
            <div className="rounded-3xl border border-white bg-white/90 p-5 shadow-soft sm:p-7">
              <p className="text-xs font-bold uppercase tracking-[0.14em] text-slate-500 capitalize">{prettyDomain(currentItem.domain)} · {currentItem.item_type.replaceAll('_', ' ')}</p>
              <h3 className="mt-3 text-xl font-semibold leading-7 text-ink sm:text-2xl">{currentItem.prompt}</h3>
              {currentItem.instructions ? <p className="mt-3 rounded-xl bg-slate-50 p-3 text-sm leading-6 text-slate-600">{currentItem.instructions}</p> : null}
              {currentItem.options.length ? (
                <fieldset className="mt-5 space-y-2">
                  <legend className="text-sm font-semibold text-slate-700">Choose the response closest to your experience</legend>
                  {currentItem.options.map((option) => (
                    <label key={option} className={`flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 text-sm ${currentDraft.answer === option ? 'border-teal-500 bg-teal-50' : 'border-slate-200 hover:border-teal-200'}`}>
                      <input type="radio" name={`answer-${currentItem.item_id}`} value={option} checked={currentDraft.answer === option} onChange={() => setAnswers((old) => ({ ...old, [currentItem.item_id]: { ...currentDraft, answer: option, skipped: false } }))} className="mt-0.5 accent-teal-700" />
                      <span>{option}</span>
                    </label>
                  ))}
                </fieldset>
              ) : (
                <label className="mt-5 block text-sm font-semibold text-slate-700" htmlFor={`answer-${currentItem.item_id}`}>
                  Your response
                  <textarea id={`answer-${currentItem.item_id}`} className={`${fieldClass} min-h-32`} maxLength={2000} value={currentDraft.answer} onChange={(event) => setAnswers((old) => ({ ...old, [currentItem.item_id]: { ...currentDraft, answer: event.target.value, skipped: false } }))} placeholder="Write a few words about your idea or approach. You do not need to get it 'right'." />
                </label>
              )}
              <div className="mt-5 max-w-sm">
                <label htmlFor={`curiosity-${currentItem.item_id}`} className="text-sm font-semibold text-slate-700">How curious do you feel about this domain? <span className="font-normal text-slate-400">(optional)</span></label>
                <select id={`curiosity-${currentItem.item_id}`} className={fieldClass} value={currentDraft.curiosity} onChange={(event) => setAnswers((old) => ({ ...old, [currentItem.item_id]: { ...currentDraft, curiosity: event.target.value } }))}>
                  <option value="">Skip this reflection</option><option value="1">1 — Not very curious right now</option><option value="2">2 — A little curious</option><option value="3">3 — Somewhat curious</option><option value="4">4 — Quite curious</option><option value="5">5 — Very curious</option>
                </select>
              </div>
              {error ? <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm leading-6 text-rose-800" role="alert">{error}</div> : null}
              <div className="mt-6 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-4">
                <button type="button" className={buttonClass} onClick={() => { setError(null); setActiveIndex((index) => Math.max(0, index - 1)); }} disabled={busy || activeIndex === 0}>Back</button>
                <div className="flex flex-wrap gap-2">
                  <button type="button" className={buttonClass} onClick={skipCurrent} disabled={busy || !currentItem.allow_skip}>Skip this item</button>
                  <button type="button" className={`${buttonClass} bg-ink text-white hover:border-ink hover:bg-slate-800 hover:text-white`} onClick={advance} disabled={busy}>{busy ? 'Saving…' : activeIndex === assessment.items.length - 1 ? 'Submit baseline' : 'Next question'}</button>
                </div>
              </div>
              <p className="mt-4 text-xs leading-5 text-slate-400">Baseline v{assessment.version} · No career or ability score is produced.</p>
            </div>
          </div>
        ) : (
          <div className="mt-6 rounded-3xl border border-white bg-white/90 p-6 shadow-soft sm:p-8">
            <h3 className="text-xl font-semibold text-ink">Ready for a short starting snapshot?</h3>
            <p className="mt-2 text-sm leading-6 text-slate-600">The age band comes from your saved profile. It uses broad interest questions and three small exploratory activities. You can skip prompts and change your profile later.</p>
            {error ? <div className="mt-4 rounded-xl border border-rose-200 bg-rose-50 p-3.5 text-sm text-rose-800" role="alert">{error}<p className="mt-1 text-xs">Check your API connection and saved profile, then retry. Answers are only submitted when you finish this snapshot.</p></div> : null}
            <button type="button" className={`${buttonClass} mt-5 bg-ink text-white hover:border-ink hover:text-white`} onClick={() => void issueAssessment()} disabled={busy}>{busy ? 'Preparing assessment…' : 'Begin baseline assessment'}</button>
          </div>
        )}
      </div>
    </section>
  );
}
