import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react';

type AgeBand = '10_14' | '15_17' | '18_plus';
type ConsentBasis = 'student_confirmed' | 'guardian_confirmed';
type EvidenceType =
  | 'stated_interest_goal'
  | 'activity_reflection'
  | 'challenge_performance'
  | 'effort_difficulty'
  | 'project_portfolio'
  | 'academic_experience'
  | 'repeated_in_product_behavior';
type SignalDimension =
  | 'interest'
  | 'demonstrated_performance'
  | 'experience_exposure'
  | 'learning_progress'
  | 'goal_preference'
  | 'practical_readiness'
  | 'effort_difficulty';
type UserInterpretation = 'supports_current_hypothesis' | 'challenges_current_hypothesis' | 'contextual_or_mixed' | 'not_interpreted';
type EvidenceSourceKind = 'self_report' | 'challenge_result' | 'user_added_project' | 'academic_self_report' | 'in_product_behavior';
type Uncertainty = 'low' | 'medium' | 'high' | 'not_assessed';

type StudentProfile = {
  profile_id: string;
  age_band: AgeBand;
  consent_basis: ConsentBasis;
  consent_confirmed_at: string;
  current_goal: string | null;
  self_reported_context: string | null;
  created_at: string;
  updated_at: string;
};
type RubricObservation = { criterion: string; observation: string; score?: number; score_scale?: string };
type EvidenceItem = {
  evidence_id: string;
  profile_id: string;
  evidence_type: EvidenceType;
  signal_dimension: SignalDimension;
  title: string;
  observation: string;
  domain: string | null;
  source_kind: EvidenceSourceKind;
  source_reference: string | null;
  observed_at: string;
  recorded_at: string;
  updated_at: string;
  uncertainty: Uncertainty;
  user_interpretation: UserInterpretation;
  consent_basis_at_capture: ConsentBasis;
  challenge_label: string | null;
  rubric_name: string | null;
  rubric_version: string | null;
  rubric_observations: RubricObservation[];
  reported_enjoyment: number | null;
  reported_curiosity: number | null;
  reported_effort: number | null;
  reported_difficulty: number | null;
  context: Record<string, string | number | boolean | null>;
};
type SignalSummary = {
  signal_dimension: SignalDimension;
  status: 'unknown' | 'evidence_available' | 'mixed';
  evidence_count: number;
  interpretation_counts: Record<string, number>;
  explanation: string;
  recent_evidence: Array<{
    evidence_id: string;
    title: string;
    evidence_type: EvidenceType;
    observation: string;
    source_kind: EvidenceSourceKind;
    observed_at: string;
    age_in_days: number;
    recency: 'recent' | 'developing' | 'older';
    uncertainty: Uncertainty;
    user_interpretation: UserInterpretation;
    context: Record<string, string | number | boolean | null>;
  }>;
};
type ProfileSummary = {
  profile_id: string;
  generated_at: string;
  overall_status: 'unknown' | 'evidence_available';
  overall_explanation: string;
  evidence_count: number;
  signals: SignalSummary[];
  limitations: string[];
};
type Props = { apiBaseUrl: string; initialAge?: number; initialGoal?: string; initialContext?: string };

const PROFILE_STORAGE_KEY = 'skillscope_student_evidence_profile_v1';
const evidenceTypeOptions: Array<{ value: EvidenceType; label: string; hint: string }> = [
  { value: 'stated_interest_goal', label: 'Stated interest or goal', hint: 'What the student says they like, want, or would like to try.' },
  { value: 'activity_reflection', label: 'Activity reflection', hint: 'Enjoyment, curiosity, or reflection after an activity.' },
  { value: 'challenge_performance', label: 'Challenge performance', hint: 'A specific observed result with its own challenge and rubric.' },
  { value: 'effort_difficulty', label: 'Effort or difficulty report', hint: 'Self-reported effort or difficulty, not ability.' },
  { value: 'project_portfolio', label: 'Project or portfolio evidence', hint: 'A student-added project description or link.' },
  { value: 'academic_experience', label: 'Academic or learning experience', hint: 'Relevant, self-reported coursework or experience.' },
  { value: 'repeated_in_product_behavior', label: 'Repeated in-product behavior', hint: 'Only explicitly recorded interactions in SkillScope; no background monitoring.' },
];
const signalLabels: Record<SignalDimension, string> = {
  interest: 'Interest',
  demonstrated_performance: 'Demonstrated performance',
  experience_exposure: 'Experience / exposure',
  learning_progress: 'Learning progress',
  goal_preference: 'Goal preference',
  practical_readiness: 'Practical readiness',
  effort_difficulty: 'Effort / difficulty',
};
const allowedDimensions: Record<EvidenceType, SignalDimension[]> = {
  stated_interest_goal: ['interest', 'goal_preference'],
  activity_reflection: ['interest', 'learning_progress', 'effort_difficulty'],
  challenge_performance: ['demonstrated_performance', 'learning_progress', 'practical_readiness'],
  effort_difficulty: ['effort_difficulty', 'learning_progress', 'interest'],
  project_portfolio: ['experience_exposure', 'demonstrated_performance', 'practical_readiness', 'learning_progress'],
  academic_experience: ['experience_exposure', 'demonstrated_performance', 'learning_progress', 'practical_readiness'],
  repeated_in_product_behavior: ['interest', 'learning_progress', 'experience_exposure'],
};
const sourceKindByType: Record<EvidenceType, EvidenceSourceKind> = {
  stated_interest_goal: 'self_report',
  activity_reflection: 'self_report',
  challenge_performance: 'challenge_result',
  effort_difficulty: 'self_report',
  project_portfolio: 'user_added_project',
  academic_experience: 'academic_self_report',
  repeated_in_product_behavior: 'in_product_behavior',
};
const recencyDescription: Record<string, string> = {
  recent: 'Recent · observed within 30 days',
  developing: 'Developing · observed 31–90 days ago',
  older: 'Older record · more than 90 days ago',
};
const labelClass = 'block text-xs font-bold uppercase tracking-[0.12em] text-slate-500';
const fieldClass = 'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 outline-none focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10';
const buttonClass = 'inline-flex items-center justify-center rounded-xl border border-slate-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-slate-700 transition hover:border-teal-300 hover:text-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:cursor-wait disabled:opacity-60';

function ageBandLabel(band: AgeBand) {
  return band === '10_14' ? '10–14' : band === '15_17' ? '15–17' : '18+';
}
function ageBandConsentBasis(band: AgeBand): ConsentBasis {
  return band === '18_plus' ? 'student_confirmed' : 'guardian_confirmed';
}
function prettyType(value: string) {
  return value.replaceAll('_', ' ');
}
function shortDate(value: string) {
  try { return new Intl.DateTimeFormat(undefined, { dateStyle: 'medium' }).format(new Date(value)); }
  catch { return value; }
}
async function parseResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let message = `Request failed (HTTP ${response.status}).`;
    try {
      const body = await response.json() as { detail?: unknown };
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) {
        const firstMessage = body.detail.find((entry): entry is { msg: string } =>
          typeof entry === 'object' && entry !== null && 'msg' in entry && typeof (entry as { msg?: unknown }).msg === 'string');
        message = firstMessage?.msg ?? message;
      }
      // Do not echo request payloads back into the UI; validation responses may include the user's input.
    } catch { /* retain the safe status message */ }
    throw new Error(message.slice(0, 1000));
  }
  if (response.status === 204) return undefined as T;
  return await response.json() as T;
}

function initialAgeBand(age: number): AgeBand {
  const safeAge = Number.isFinite(age) && age >= 10 && age <= 100 ? age : 16;
  if (safeAge <= 14) return '10_14';
  if (safeAge <= 17) return '15_17';
  return '18_plus';
}

export default function EvidenceLedger({ apiBaseUrl, initialAge = 16, initialGoal = '', initialContext = '' }: Props) {
  const [profileId, setProfileId] = useState<string | null>(() => typeof window !== 'undefined' ? window.localStorage.getItem(PROFILE_STORAGE_KEY) : null);

  useEffect(() => {
    const syncProfile = () => {
      const nextId = window.localStorage.getItem(PROFILE_STORAGE_KEY);
      setProfileId(nextId);
      if (!nextId) { setProfile(null); setItems([]); setSummary(null); }
    };
    window.addEventListener('skillscope-profile-changed', syncProfile);
    return () => window.removeEventListener('skillscope-profile-changed', syncProfile);
  }, []);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [items, setItems] = useState<EvidenceItem[]>([]);
  const [summary, setSummary] = useState<ProfileSummary | null>(null);
  const [initializing, setInitializing] = useState(Boolean(profileId));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [createAgeBand, setCreateAgeBand] = useState<AgeBand>(() => initialAgeBand(initialAge));
  const [createGoal, setCreateGoal] = useState(initialGoal);
  const [createContext, setCreateContext] = useState(initialContext);
  const [creationTouched, setCreationTouched] = useState(false);
  const [createConsent, setCreateConsent] = useState(false);

  const [editAgeBand, setEditAgeBand] = useState<AgeBand>('18_plus');
  const [editGoal, setEditGoal] = useState('');
  const [editContext, setEditContext] = useState('');
  const [editConsent, setEditConsent] = useState(false);
  const [showProfileEdit, setShowProfileEdit] = useState(false);

  const [evidenceType, setEvidenceType] = useState<EvidenceType>('stated_interest_goal');
  const [signalDimension, setSignalDimension] = useState<SignalDimension>('interest');
  const [title, setTitle] = useState('');
  const [observation, setObservation] = useState('');
  const [domain, setDomain] = useState('');
  const [sourceReference, setSourceReference] = useState('');
  const [uncertainty, setUncertainty] = useState<Uncertainty>('not_assessed');
  const [interpretation, setInterpretation] = useState<UserInterpretation>('not_interpreted');
  const [enjoyment, setEnjoyment] = useState('');
  const [curiosity, setCuriosity] = useState('');
  const [effort, setEffort] = useState('');
  const [difficulty, setDifficulty] = useState('');
  const [challengeLabel, setChallengeLabel] = useState('');
  const [rubricName, setRubricName] = useState('');
  const [rubricVersion, setRubricVersion] = useState('');
  const [criterion, setCriterion] = useState('');
  const [criterionObservation, setCriterionObservation] = useState('');
  const [criterionScore, setCriterionScore] = useState('');
  const [criterionScale, setCriterionScale] = useState('');
  const [behaviorActivity, setBehaviorActivity] = useState('');
  const [behaviorWindow, setBehaviorWindow] = useState('');
  const [behaviorConsent, setBehaviorConsent] = useState(false);
  const [editingItem, setEditingItem] = useState<EvidenceItem | null>(null);
  const [editItemTitle, setEditItemTitle] = useState('');
  const [editItemObservation, setEditItemObservation] = useState('');
  const [editItemDimension, setEditItemDimension] = useState<SignalDimension>('interest');
  const [editItemUncertainty, setEditItemUncertainty] = useState<Uncertainty>('not_assessed');
  const [editItemInterpretation, setEditItemInterpretation] = useState<UserInterpretation>('not_interpreted');

  const activeDimensions = useMemo(() => allowedDimensions[evidenceType], [evidenceType]);

  const refreshData = useCallback(async (id: string) => {
    const [profileResult, evidenceResult, summaryResult] = await Promise.all([
      fetch(`${apiBaseUrl}/api/student-profiles/${id}`, { headers: { Accept: 'application/json' } }),
      fetch(`${apiBaseUrl}/api/student-profiles/${id}/evidence?limit=100&offset=0`, { headers: { Accept: 'application/json' } }),
      fetch(`${apiBaseUrl}/api/student-profiles/${id}/summary`, { headers: { Accept: 'application/json' } }),
    ]);
    const nextProfile = await parseResponse<StudentProfile>(profileResult);
    const evidenceBody = await parseResponse<{ items: EvidenceItem[]; count: number }>(evidenceResult);
    const nextSummary = await parseResponse<ProfileSummary>(summaryResult);
    setProfile(nextProfile);
    setItems(evidenceBody.items);
    setSummary(nextSummary);
    setEditAgeBand(nextProfile.age_band);
    setEditGoal(nextProfile.current_goal ?? '');
    setEditContext(nextProfile.self_reported_context ?? '');
    setEditConsent(false);
  }, [apiBaseUrl]);

  useEffect(() => {
    if (!profileId) {
      setInitializing(false);
      return;
    }
    let cancelled = false;
    setInitializing(true);
    void (async () => {
      try {
        await refreshData(profileId);
        if (!cancelled) setError(null);
      } catch (requestError) {
        if (cancelled) return;
        const message = requestError instanceof Error ? requestError.message : 'Could not load the saved evidence profile.';
        if (message.includes('404') || message.toLowerCase().includes('not found')) {
          window.localStorage.removeItem(PROFILE_STORAGE_KEY);
          window.dispatchEvent(new Event('skillscope-profile-changed'));
          setProfileId(null);
          setProfile(null);
          setItems([]);
          setSummary(null);
        } else setError(message);
      } finally {
        if (!cancelled) setInitializing(false);
      }
    })();
    return () => { cancelled = true; };
  }, [profileId, refreshData]);

  const clearMessages = () => { setError(null); setSuccess(null); };
  const resetEvidenceForm = () => {
    setEvidenceType('stated_interest_goal'); setSignalDimension('interest'); setTitle(''); setObservation('');
    setDomain(''); setSourceReference(''); setUncertainty('not_assessed'); setInterpretation('not_interpreted');
    setEnjoyment(''); setCuriosity(''); setEffort(''); setDifficulty(''); setChallengeLabel('');
    setRubricName(''); setRubricVersion(''); setCriterion(''); setCriterionObservation('');
    setCriterionScore(''); setCriterionScale(''); setBehaviorActivity(''); setBehaviorWindow(''); setBehaviorConsent(false);
  };

  const submitProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); clearMessages(); setBusy(true);
    try {
      const body = await parseResponse<StudentProfile>(await fetch(`${apiBaseUrl}/api/student-profiles`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({
          age_band: createAgeBand, consent_basis: ageBandConsentBasis(createAgeBand), consent_confirmed: createConsent,
          current_goal: createGoal.trim() || null, self_reported_context: createContext.trim() || null,
        }),
      }));
      window.localStorage.setItem(PROFILE_STORAGE_KEY, body.profile_id);
      setProfileId(body.profile_id); setProfile(body);
      window.dispatchEvent(new Event('skillscope-profile-changed'));
      await refreshData(body.profile_id);
      setSuccess('Profile created. No history has been invented; it starts with unknown signals until you add evidence.');
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Profile creation failed.'); }
    finally { setBusy(false); }
  };

  const saveProfile = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!profileId || !profile) return; clearMessages(); setBusy(true);
    const payload: Record<string, unknown> = {
      current_goal: editGoal.trim() || null,
      self_reported_context: editContext.trim() || null,
    };
    if (editAgeBand !== profile.age_band) {
      payload.age_band = editAgeBand;
      payload.consent_basis = ageBandConsentBasis(editAgeBand);
      payload.consent_confirmed = editConsent;
    }
    try {
      await parseResponse<StudentProfile>(await fetch(`${apiBaseUrl}/api/student-profiles/${profileId}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(payload),
      }));
      await refreshData(profileId); setShowProfileEdit(false); setSuccess('Profile details updated.');
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Profile update failed.'); }
    finally { setBusy(false); }
  };

  const submitEvidence = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!profileId) return; clearMessages(); setBusy(true);
    const rubricObservations: RubricObservation[] = evidenceType === 'challenge_performance' && criterion.trim() && criterionObservation.trim()
      ? [{ criterion: criterion.trim(), observation: criterionObservation.trim(), ...(criterionScore.trim() ? { score: Number(criterionScore), score_scale: criterionScale.trim() } : {}) }]
      : [];
    const context: Record<string, string | number | boolean | null> = {};
    if (evidenceType === 'repeated_in_product_behavior') {
      context.activity_name = behaviorActivity.trim(); context.time_window = behaviorWindow.trim();
    }
    const payload: Record<string, unknown> = {
      evidence_type: evidenceType, signal_dimension: signalDimension, title: title.trim(), observation: observation.trim(),
      domain: domain.trim() || null, source_kind: sourceKindByType[evidenceType], uncertainty, user_interpretation: interpretation,
      context, behavior_consent_confirmed: evidenceType === 'repeated_in_product_behavior' ? behaviorConsent : false,
      ...(sourceReference.trim() ? { source_reference: sourceReference.trim() } : {}),
      ...(enjoyment ? { reported_enjoyment: Number(enjoyment) } : {}),
      ...(curiosity ? { reported_curiosity: Number(curiosity) } : {}),
      ...(effort ? { reported_effort: Number(effort) } : {}),
      ...(difficulty ? { reported_difficulty: Number(difficulty) } : {}),
      ...(evidenceType === 'challenge_performance' ? {
        challenge_label: challengeLabel.trim(), rubric_name: rubricName.trim(), rubric_version: rubricVersion.trim() || null,
        rubric_observations: rubricObservations,
      } : {}),
    };
    try {
      await parseResponse<EvidenceItem>(await fetch(`${apiBaseUrl}/api/student-profiles/${profileId}/evidence`, {
        method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify(payload),
      }));
      await refreshData(profileId); resetEvidenceForm(); setSuccess('Evidence saved. It is stored as one contextual observation, not as a final trait or score.');
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not save this evidence item.'); }
    finally { setBusy(false); }
  };

  const beginEditItem = (item: EvidenceItem) => {
    setEditingItem(item); setEditItemTitle(item.title); setEditItemObservation(item.observation);
    setEditItemDimension(item.signal_dimension); setEditItemUncertainty(item.uncertainty); setEditItemInterpretation(item.user_interpretation);
  };
  const saveItemCorrection = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault(); if (!profileId || !editingItem) return; clearMessages(); setBusy(true);
    try {
      await parseResponse<EvidenceItem>(await fetch(`${apiBaseUrl}/api/student-profiles/${profileId}/evidence/${editingItem.evidence_id}`, {
        method: 'PATCH', headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
        body: JSON.stringify({ title: editItemTitle.trim(), observation: editItemObservation.trim(), signal_dimension: editItemDimension, uncertainty: editItemUncertainty, user_interpretation: editItemInterpretation }),
      }));
      await refreshData(profileId); setEditingItem(null); setSuccess('Evidence corrected. Its original recorded timestamp is preserved.');
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not correct this evidence item.'); }
    finally { setBusy(false); }
  };
  const deleteItem = async (item: EvidenceItem) => {
    if (!profileId || !window.confirm(`Permanently delete “${item.title}”?`)) return;
    clearMessages(); setBusy(true);
    try {
      await parseResponse<void>(await fetch(`${apiBaseUrl}/api/student-profiles/${profileId}/evidence/${item.evidence_id}`, { method: 'DELETE' }));
      await refreshData(profileId); if (editingItem?.evidence_id === item.evidence_id) setEditingItem(null);
      setSuccess('Evidence item permanently deleted.');
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not delete evidence.'); }
    finally { setBusy(false); }
  };
  const clearHistory = async () => {
    if (!profileId || !window.confirm('Permanently delete every evidence item while retaining the empty profile? This cannot be undone.')) return;
    clearMessages(); setBusy(true);
    try {
      const result = await parseResponse<{ deleted_count: number }>(await fetch(`${apiBaseUrl}/api/student-profiles/${profileId}/evidence`, { method: 'DELETE' }));
      await refreshData(profileId); setEditingItem(null); setSuccess(`${result.deleted_count} evidence item(s) permanently deleted. The empty profile remains.`);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not clear evidence history.'); }
    finally { setBusy(false); }
  };
  const deleteProfile = async () => {
    if (!profileId || !window.confirm('Permanently delete this profile and all its evidence history? This cannot be undone.')) return;
    clearMessages(); setBusy(true);
    try {
      await parseResponse<{ deleted: boolean }>(await fetch(`${apiBaseUrl}/api/student-profiles/${profileId}`, { method: 'DELETE' }));
      window.localStorage.removeItem(PROFILE_STORAGE_KEY); setProfileId(null); setProfile(null); setItems([]); setSummary(null); setEditingItem(null);
      window.dispatchEvent(new Event('skillscope-profile-changed'));
      setSuccess('Profile and all evidence history permanently deleted.');
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not delete this profile.'); }
    finally { setBusy(false); }
  };
  const retryProfileLoad = async () => {
    if (!profileId) return;
    setInitializing(true); setError(null);
    try { await refreshData(profileId); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : 'Could not reopen the saved profile.'); }
    finally { setInitializing(false); }
  };

  useEffect(() => {
    if (!profileId && !creationTouched) {
      setCreateAgeBand(initialAgeBand(initialAge));
      setCreateGoal(initialGoal);
      setCreateContext(initialContext);
      setCreateConsent(false);
    }
  }, [initialAge, initialGoal, initialContext, profileId, creationTouched]);

  return (
    <section id="evidence-ledger" className="ss-section scroll-mt-28 border-t border-slate-200/80 py-12 sm:py-16" aria-labelledby="evidence-ledger-heading">
      <div className="grid gap-8 lg:grid-cols-[0.82fr_1.18fr] lg:items-start">
        <div>
          <p className="ss-section-kicker text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Your profile</p>
          <h1 id="evidence-ledger-heading" className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Build your profile from what you try.</h1>
          <p className="mt-4 text-sm leading-7 text-slate-600">Add things you have tried and what you noticed. You can edit or delete anything.</p>
          <div className="mt-5 rounded-2xl border border-teal-100 bg-teal-50/70 p-4"><p className="text-sm font-semibold text-teal-950">Unknown is not zero.</p><p className="mt-1 text-sm leading-6 text-teal-900/80">A hard task may reflect the task, tiredness, unfamiliarity or context. SkillScope does not turn one result into a fixed ability or a career label.</p></div>
          <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-xs leading-5 text-amber-950"><p className="font-bold">Prototype privacy boundary</p><p className="mt-1">The consent checkbox is a recorded self-attestation, not identity or guardian verification. Profile IDs are locators, not authentication. Use demo information only: no real names, school details or children's data. Production use needs verified identity, authorization, security and retention controls.</p></div>
        </div>

        <div id="profile-settings" className="scroll-mt-28 min-w-0 space-y-5">
          {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800" role="alert">{error}</div> : null}
          {success ? <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800" role="status">{success}</div> : null}

          {initializing ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 text-sm text-slate-500" role="status">Loading your saved evidence profile…</div>
          ) : !profileId ? (
            <form onSubmit={submitProfile} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
              <p className="text-xs font-bold uppercase tracking-[0.15em] text-slate-500">Create your profile</p>
              <h3 className="mt-2 text-xl font-semibold text-ink">Get started</h3>
              <p className="mt-2 text-sm leading-6 text-slate-500">No name, date of birth or school needed. This stores only what you choose to enter.</p>
              <aside role="note" aria-labelledby="privacy-safety-notice-heading" className="mt-4 rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm leading-6 text-amber-950">
                <h4 id="privacy-safety-notice-heading" className="font-bold">Prototype privacy and safety notice — demo data only</h4>
                <p id="privacy-safety-notice-copy" className="mt-1">Do not enter real student or child data, names, contact details, government identifiers, or sensitive personal information (including health, disability, religion, caste, sexuality, or political views). Use synthetic examples only.</p>
                <ul className="mt-2 list-disc space-y-1 pl-5">
                  <li>SkillScope stores the age band, optional goal/context, and the activities, reflections, preferences, and plans you choose to save in the configured local database. The browser stores a profile locator.</li>
                  <li>You can review and correct your profile or evidence and permanently delete an evidence item, all evidence, or the profile using the controls below.</li>
                  <li>SkillScope does not scrape social media, monitor other apps, or send personal data to an external LLM in this prototype. A project link is only stored as a user-provided reference.</li>
                  <li>For anyone under 18, this is only a demo consent declaration. Guardian identity and legal consent are not independently verified. Do not use real children's data.</li>
                </ul>
              </aside>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <label className={labelClass}>Age band
                  <select className={fieldClass} value={createAgeBand} onChange={(event) => { setCreationTouched(true); setCreateAgeBand(event.target.value as AgeBand); setCreateConsent(false); }}>
                    <option value="10_14">10–14</option><option value="15_17">15–17</option><option value="18_plus">18+</option>
                  </select>
                </label>
                <label className={labelClass}>Current goal (optional)
                  <input className={fieldClass} maxLength={500} value={createGoal} onChange={(event) => { setCreationTouched(true); setCreateGoal(event.target.value); }} placeholder="A direction you'd like to explore" />
                </label>
              </div>
              <label className={`${labelClass} mt-4`}>Self-reported context (optional)
                <textarea className={fieldClass} rows={3} maxLength={1500} value={createContext} onChange={(event) => { setCreationTouched(true); setCreateContext(event.target.value); }} placeholder="Prior activities, access or experience—avoid identifying details." />
              </label>
              <label className="mt-5 flex items-start gap-3 rounded-xl border border-slate-200 bg-slate-50 p-3.5 text-sm leading-6 text-slate-700">
                <input type="checkbox" checked={createConsent} onChange={(event) => setCreateConsent(event.target.checked)} className="mt-1 h-4 w-4 shrink-0 accent-teal-700" aria-describedby="privacy-safety-notice-copy" required />
                <span>{createAgeBand === '18_plus' ? 'I consent to storing this profile and evidence I choose to add.' : 'I confirm that appropriate guardian consent has been obtained for storing this student profile and its evidence.'}</span>
              </label>
              <button className={`${buttonClass} mt-5 w-full bg-ink text-white hover:border-ink hover:text-white`} disabled={busy || !createConsent}>{busy ? 'Creating profile…' : 'Create evidence profile'}</button>
            </form>
          ) : !profile ? (
            <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <h3 className="text-lg font-semibold text-ink">Could not load your profile</h3>
              <p className="mt-2 text-sm leading-6 text-slate-600">We could not load your profile just now. Please try again.</p>
              <button type="button" className={`${buttonClass} mt-4`} onClick={() => void retryProfileLoad()} disabled={busy || initializing}>Retry loading profile</button>
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Your profile · consented storage</p>
                    <h3 className="mt-2 text-xl font-semibold text-ink">Evidence profile</h3>
                    <p className="mt-1 text-xs leading-5 text-slate-500">Age band {ageBandLabel(profile.age_band)} · Consent confirmation recorded {shortDate(profile.consent_confirmed_at)}</p>
                  </div>
                  <button type="button" className={buttonClass} onClick={() => { setShowProfileEdit((shown) => !shown); setEditAgeBand(profile.age_band); setEditGoal(profile.current_goal ?? ''); setEditContext(profile.self_reported_context ?? ''); setEditConsent(false); }}>{showProfileEdit ? 'Cancel edit' : 'Correct profile'}</button>
                </div>
                {showProfileEdit ? (
                  <form className="mt-5 border-t border-slate-100 pt-5" onSubmit={saveProfile}>
                    <div className="grid gap-4 sm:grid-cols-2">
                      <label className={labelClass}>Age band
                        <select className={fieldClass} value={editAgeBand} onChange={(event) => { setEditAgeBand(event.target.value as AgeBand); setEditConsent(false); }}>
                          <option value="10_14">10–14</option><option value="15_17">15–17</option><option value="18_plus">18+</option>
                        </select>
                      </label>
                      <label className={labelClass}>Current goal
                        <input className={fieldClass} maxLength={500} value={editGoal} onChange={(event) => setEditGoal(event.target.value)} placeholder="What would you like to explore?" />
                      </label>
                    </div>
                    <label className={`${labelClass} mt-4`}>Self-reported context
                      <textarea className={fieldClass} rows={3} maxLength={1500} value={editContext} onChange={(event) => setEditContext(event.target.value)} />
                    </label>
                    {editAgeBand !== profile.age_band ? (
                      <label className="mt-4 flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-3.5 text-sm leading-6 text-amber-950">
                        <input type="checkbox" checked={editConsent} onChange={(event) => setEditConsent(event.target.checked)} className="mt-1 h-4 w-4 shrink-0 accent-teal-700" required />
                        <span>{editAgeBand === '18_plus' ? 'I reconfirm consent as the adult student.' : 'I confirm appropriate guardian consent has been obtained for the corrected age band.'}</span>
                      </label>
                    ) : null}
                    <button type="submit" className={`${buttonClass} mt-4`} disabled={busy || (editAgeBand !== profile.age_band && !editConsent)}>{busy ? 'Saving…' : 'Save corrections'}</button>
                  </form>
                ) : (
                  <div className="mt-4 grid gap-3 sm:grid-cols-2">
                    <div className="rounded-xl bg-slate-50 p-3.5"><p className="text-xs font-bold uppercase tracking-wide text-slate-400">Current goal</p><p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{profile.current_goal || 'Not stated yet'}</p></div>
                    <div className="rounded-xl bg-slate-50 p-3.5"><p className="text-xs font-bold uppercase tracking-wide text-slate-400">Context / experience</p><p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">{profile.self_reported_context || 'Not provided yet'}</p></div>
                  </div>
                )}
                <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-4">
                  <span className="text-xs text-slate-500">{items.length} item(s) loaded · {summary?.evidence_count ?? 0} total recorded</span>
                  <div className="flex flex-wrap gap-2">
                    <button type="button" className={buttonClass} onClick={() => void clearHistory()} disabled={busy || items.length === 0}>Delete evidence history</button>
                    <button type="button" className="inline-flex items-center justify-center rounded-xl border border-rose-200 bg-white px-3.5 py-2.5 text-sm font-semibold text-rose-700 hover:bg-rose-50 disabled:opacity-50" onClick={() => void deleteProfile()} disabled={busy}>Delete profile + history</button>
                  </div>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-teal-100 bg-teal-50/60 p-4"><div><p className="text-sm font-semibold text-teal-950">Profile ready</p><p className="mt-1 text-xs leading-5 text-teal-900/80">Start your baseline now, or add a prior project or activity first.</p></div><a href="#/baseline" className="inline-flex items-center rounded-full bg-ink px-5 py-2.5 text-sm font-semibold text-white shadow-soft transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/20">Continue to baseline</a></div>

              <form onSubmit={submitEvidence} className="ss-panel rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Add contextual evidence</p>
                <h3 className="mt-2 text-xl font-semibold text-ink">What did you observe—or what did you report?</h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">Choose one main evidence type. The ledger does not automatically interpret the meaning for you.</p>
                <div className="mt-5">
                  <label className={labelClass}>Evidence type
                    <select className={fieldClass} value={evidenceType} onChange={(event) => {
                      const nextType = event.target.value as EvidenceType; setEvidenceType(nextType);
                      setSignalDimension(allowedDimensions[nextType][0]); setBehaviorConsent(false);
                    }}>
                      {evidenceTypeOptions.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
                    </select>
                  </label>
                  <p className="mt-1.5 text-xs leading-5 text-slate-500">{evidenceTypeOptions.find((option) => option.value === evidenceType)?.hint}</p>
                </div>
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <label className={labelClass}>Signal dimension
                    <select className={fieldClass} value={signalDimension} onChange={(event) => setSignalDimension(event.target.value as SignalDimension)}>
                      {activeDimensions.map((dimension) => <option key={dimension} value={dimension}>{signalLabels[dimension]}</option>)}
                    </select>
                  </label>
                  <label className={labelClass}>Domain or context label (optional)
                    <input className={fieldClass} maxLength={100} value={domain} onChange={(event) => setDomain(event.target.value)} placeholder="e.g. design, coding, science" />
                  </label>
                </div>
                <label className={`${labelClass} mt-4`}>Title
                  <input className={fieldClass} required maxLength={160} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="A short, neutral description" />
                </label>
                <label className={`${labelClass} mt-4`}>Observation or reflection
                  <textarea className={fieldClass} required rows={3} maxLength={2400} value={observation} onChange={(event) => setObservation(event.target.value)} placeholder="What happened? Separate the observed result from how it felt or what you think it means." />
                </label>
                {evidenceType === 'challenge_performance' ? (
                  <div className="mt-4 rounded-xl border border-indigo-100 bg-indigo-50/50 p-4">
                    <p className="text-sm font-semibold text-indigo-950">Challenge and rubric details</p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <label className={labelClass}>Challenge label<input className={fieldClass} required maxLength={160} value={challengeLabel} onChange={(event) => setChallengeLabel(event.target.value)} /></label>
                      <label className={labelClass}>Rubric name<input className={fieldClass} required maxLength={160} value={rubricName} onChange={(event) => setRubricName(event.target.value)} /></label>
                      <label className={labelClass}>Rubric version (optional)<input className={fieldClass} maxLength={80} value={rubricVersion} onChange={(event) => setRubricVersion(event.target.value)} placeholder="e.g. 1.0" /></label>
                      <label className={labelClass}>Rubric criterion<input className={fieldClass} required maxLength={120} value={criterion} onChange={(event) => setCriterion(event.target.value)} placeholder="e.g. explain the approach" /></label>
                    </div>
                    <label className={`${labelClass} mt-3`}>Observed against this criterion<input className={fieldClass} required maxLength={500} value={criterionObservation} onChange={(event) => setCriterionObservation(event.target.value)} placeholder="What the rubric actually showed" /></label>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <label className={labelClass}>Numeric result (optional)<input className={fieldClass} type="number" value={criterionScore} onChange={(event) => setCriterionScore(event.target.value)} placeholder="Only if a score was actually given" /></label>
                      <label className={labelClass}>Exact score scale<input className={fieldClass} value={criterionScale} onChange={(event) => setCriterionScale(event.target.value)} placeholder="Required with score, e.g. 0–4" /></label>
                    </div>
                    <p className="mt-2 text-xs leading-5 text-indigo-900/75">Scores are retained only with their own rubric and stated scale. They are not normalized against other tasks or treated as overall ability.</p>
                  </div>
                ) : null}
                {evidenceType === 'repeated_in_product_behavior' ? (
                  <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-4">
                    <p className="text-sm font-semibold text-amber-950">Explicit interaction context</p>
                    <div className="mt-3 grid gap-3 sm:grid-cols-2">
                      <label className={labelClass}>Activity<input className={fieldClass} required maxLength={160} value={behaviorActivity} onChange={(event) => setBehaviorActivity(event.target.value)} placeholder="The in-product activity" /></label>
                      <label className={labelClass}>Time window<input className={fieldClass} required maxLength={160} value={behaviorWindow} onChange={(event) => setBehaviorWindow(event.target.value)} placeholder="e.g. this session" /></label>
                    </div>
                    <label className="mt-3 flex items-start gap-3 rounded-xl border border-amber-200 bg-white p-3 text-sm leading-5 text-amber-950">
                      <input type="checkbox" checked={behaviorConsent} onChange={(event) => setBehaviorConsent(event.target.checked)} className="mt-1 h-4 w-4 shrink-0 accent-teal-700" required />
                      <span>I agree to record this specific in-product interaction with the activity and time-window context shown above.</span>
                    </label>
                    <p className="mt-2 text-xs leading-5 text-amber-900/80">This form records a deliberate, contextual entry only. It does not enable tracking in the background or across other apps.</p>
                  </div>
                ) : null}
                <div className="mt-4 grid gap-4 sm:grid-cols-2">
                  <label className={labelClass}>Uncertainty
                    <select className={fieldClass} value={uncertainty} onChange={(event) => setUncertainty(event.target.value as Uncertainty)}>
                      <option value="not_assessed">Not assessed</option><option value="low">Low · relatively clear observation</option><option value="medium">Medium · some ambiguity</option><option value="high">High · uncertain or context-limited</option>
                    </select>
                  </label>
                  <label className={labelClass}>Your interpretation (optional)
                    <select className={fieldClass} value={interpretation} onChange={(event) => setInterpretation(event.target.value as UserInterpretation)}>
                      <option value="not_interpreted">Leave uninterpreted</option><option value="supports_current_hypothesis">Seems to support current hypothesis</option><option value="challenges_current_hypothesis">Raises a question about current hypothesis</option><option value="contextual_or_mixed">Mixed or needs more context</option>
                    </select>
                  </label>
                </div>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <label className={labelClass}>Source / portfolio URL (optional)<input className={fieldClass} type="url" value={sourceReference} onChange={(event) => setSourceReference(event.target.value)} placeholder="https://…" /></label>
                  <label className={labelClass}>Enjoyment reported (1–5)<select className={fieldClass} value={enjoyment} onChange={(event) => setEnjoyment(event.target.value)}><option value="">Not reported</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
                  <label className={labelClass}>Curiosity reported (1–5)<select className={fieldClass} value={curiosity} onChange={(event) => setCuriosity(event.target.value)}><option value="">Not reported</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
                  <label className={labelClass}>Effort reported (1–5)<select className={fieldClass} value={effort} onChange={(event) => setEffort(event.target.value)}><option value="">Not reported</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
                  <label className={labelClass}>Difficulty reported (1–5)<select className={fieldClass} value={difficulty} onChange={(event) => setDifficulty(event.target.value)}><option value="">Not reported</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}</option>)}</select></label>
                </div>
                <div className="mt-5 flex flex-wrap justify-end gap-2 border-t border-slate-100 pt-4">
                  <button type="button" className={buttonClass} onClick={resetEvidenceForm} disabled={busy}>Clear form</button>
                  <button type="submit" className={`${buttonClass} bg-ink text-white hover:border-ink hover:text-white`} disabled={busy}>{busy ? 'Saving…' : 'Save evidence'}</button>
                </div>
              </form>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div className="flex flex-wrap items-end justify-between gap-3">
                  <div><p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Signal summary</p><h3 className="mt-2 text-xl font-semibold text-ink">What the current record can—and cannot—say</h3></div>
                  <span className="rounded-full border border-slate-200 px-3 py-1.5 text-xs text-slate-500">{summary?.evidence_count ?? 0} evidence item(s)</span>
                </div>
                <p className="mt-3 text-sm leading-6 text-slate-500">{summary?.overall_explanation ?? 'Loading summary…'}</p>
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {summary?.signals.map((signal) => (
                    <article key={signal.signal_dimension} className="rounded-xl border border-slate-100 bg-slate-50 p-3.5">
                      <div className="flex items-center justify-between gap-2"><h4 className="text-sm font-semibold text-slate-800">{signalLabels[signal.signal_dimension]}</h4><span className={`rounded-full px-2 py-1 text-[10px] font-bold uppercase tracking-wide ${signal.status === 'unknown' ? 'bg-slate-200 text-slate-600' : signal.status === 'mixed' ? 'bg-amber-100 text-amber-900' : 'bg-teal-100 text-teal-900'}`}>{prettyType(signal.status)}</span></div>
                      <p className="mt-2 text-xs leading-5 text-slate-600">{signal.explanation}</p>
                      <p className="mt-2 text-xs font-semibold text-slate-400">{signal.evidence_count} record(s) · no numeric signal score</p>
                      {signal.recent_evidence.length ? <ul className="mt-3 space-y-2 border-t border-slate-200 pt-3">{signal.recent_evidence.slice(0, 2).map((entry) => <li key={entry.evidence_id} className="text-xs leading-5"><p className="font-semibold text-slate-700">{entry.title}</p><p className="mt-0.5 text-slate-500">{shortDate(entry.observed_at)} · {recencyDescription[entry.recency]} · {prettyType(entry.uncertainty)} uncertainty</p></li>)}</ul> : null}
                    </article>
                  ))}
                </div>
                {summary?.limitations.length ? <details className="mt-4 rounded-xl border border-slate-100 p-3.5"><summary className="cursor-pointer text-xs font-semibold text-teal-800 underline underline-offset-4">How to read this summary</summary><ul className="mt-3 space-y-1 pl-4 text-xs leading-5 text-slate-500 marker:text-slate-400">{summary.limitations.map((limitation) => <li key={limitation} className="list-disc">{limitation}</li>)}</ul></details> : null}
              </div>

              <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
                <div className="flex flex-wrap items-end justify-between gap-3"><div><p className="text-xs font-bold uppercase tracking-[0.15em] text-teal-700">Review and correct</p><h3 className="mt-2 text-xl font-semibold text-ink">Evidence history</h3></div><span className="text-xs text-slate-400">Newest observations first</span></div>
                {items.length ? <div className="mt-4 space-y-3">{items.map((item) => (
                  <article key={item.evidence_id} className="rounded-xl border border-slate-100 p-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0"><div className="flex flex-wrap gap-2"><span className="rounded-full bg-teal-50 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-teal-800">{prettyType(item.evidence_type)}</span><span className="rounded-full bg-slate-100 px-2 py-1 text-[10px] font-semibold text-slate-600">{signalLabels[item.signal_dimension]}</span></div><h4 className="mt-2 break-words text-sm font-semibold text-slate-800">{item.title}</h4><p className="mt-1 whitespace-pre-wrap break-words text-sm leading-6 text-slate-600">{item.observation}</p><p className="mt-2 text-xs leading-5 text-slate-400">Observed {shortDate(item.observed_at)} · recorded {shortDate(item.recorded_at)} · {prettyType(item.source_kind)} · {prettyType(item.uncertainty)} uncertainty</p>
                        {item.rubric_observations.length ? <ul className="mt-2 space-y-1 border-l-2 border-indigo-100 pl-3 text-xs leading-5 text-slate-600">{item.rubric_observations.map((rubricRow, index) => <li key={`${item.evidence_id}-${index}`}><span className="font-semibold">{rubricRow.criterion}:</span> {rubricRow.observation}{rubricRow.score !== null && rubricRow.score !== undefined ? ` · ${rubricRow.score} (${rubricRow.score_scale})` : ''}</li>)}</ul> : null}
                        {item.source_reference ? <a className="mt-2 inline-block break-all text-xs font-semibold text-teal-800 underline underline-offset-4" href={item.source_reference} target="_blank" rel="noopener noreferrer">Open source / project reference</a> : null}
                        {item.user_interpretation !== 'not_interpreted' ? <p className="mt-2 text-xs text-slate-500">Your interpretation: {prettyType(item.user_interpretation)}</p> : null}
                      </div>
                      <div className="flex shrink-0 gap-2"><button type="button" className={buttonClass} onClick={() => beginEditItem(item)} disabled={busy}>Correct</button><button type="button" className="rounded-xl border border-rose-200 px-3 py-2 text-xs font-semibold text-rose-700 hover:bg-rose-50" onClick={() => void deleteItem(item)} disabled={busy}>Delete</button></div>
                    </div>
                    {editingItem?.evidence_id === item.evidence_id ? (
                      <form onSubmit={saveItemCorrection} className="mt-4 space-y-3 border-t border-slate-100 pt-4">
                        <label className={labelClass}>Corrected title<input className={fieldClass} required maxLength={160} value={editItemTitle} onChange={(event) => setEditItemTitle(event.target.value)} /></label>
                        <label className={labelClass}>Corrected observation<textarea className={fieldClass} required rows={3} maxLength={2400} value={editItemObservation} onChange={(event) => setEditItemObservation(event.target.value)} /></label>
                        <div className="grid gap-3 sm:grid-cols-3">
                          <label className={labelClass}>Signal dimension<select className={fieldClass} value={editItemDimension} onChange={(event) => setEditItemDimension(event.target.value as SignalDimension)}>{allowedDimensions[item.evidence_type].map((dimension) => <option key={dimension} value={dimension}>{signalLabels[dimension]}</option>)}</select></label>
                          <label className={labelClass}>Uncertainty<select className={fieldClass} value={editItemUncertainty} onChange={(event) => setEditItemUncertainty(event.target.value as Uncertainty)}><option value="not_assessed">Not assessed</option><option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option></select></label>
                          <label className={labelClass}>Interpretation<select className={fieldClass} value={editItemInterpretation} onChange={(event) => setEditItemInterpretation(event.target.value as UserInterpretation)}><option value="not_interpreted">Not interpreted</option><option value="supports_current_hypothesis">Supports current hypothesis</option><option value="challenges_current_hypothesis">Challenges current hypothesis</option><option value="contextual_or_mixed">Contextual or mixed</option></select></label>
                        </div>
                        <div className="flex flex-wrap gap-2"><button type="submit" className={`${buttonClass} bg-ink text-white hover:border-ink hover:text-white`} disabled={busy}>Save correction</button><button type="button" className={buttonClass} onClick={() => setEditingItem(null)} disabled={busy}>Cancel</button></div>
                      </form>
                    ) : null}
                  </article>
                ))}</div> : <div className="mt-4 rounded-xl border border-dashed border-slate-200 p-6 text-center"><p className="text-sm font-semibold text-slate-700">No evidence has been recorded yet.</p><p className="mt-1 text-sm leading-6 text-slate-500">Each signal stays unknown until you add relevant evidence. Nothing is assumed to be zero.</p></div>}
              </div>
            </>
          )}
        </div>
      </div>
    </section>
  );
}
