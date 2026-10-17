import { useEffect, useState, type FormEvent, type ReactNode } from 'react';
import ModeCompass from '../motion/ModeCompass';
import TiltCard from '../motion/TiltCard';
import { MODE_ORDER, MODES, modeFromAge, modeFromApi } from '../motion/modeConfig';
import { useModeTheme } from '../motion/ModeContext';
import { ageModeDescriptions } from '../shared/content';
import { apiBaseUrl, useApiStatus } from '../shared/api';
import { NextStep } from './PageParts';

type Rating = 'low' | 'medium' | 'high';
type EvidenceQuality = 'unknown' | 'low' | 'medium' | 'high';
type ExperienceLevel = 'none' | 'some' | 'substantial';
type JourneyPreference = 'automatic' | 'explore' | 'validate' | 'optimize';
type DesiredTimeline = 'unspecified' | 'under_3_months' | '3_to_6_months' | '6_to_12_months' | 'over_12_months';
type ExplorationDomain =
  | 'creative_design'
  | 'analytical_logic'
  | 'hands_on_making'
  | 'social_collaboration'
  | 'communication_storytelling'
  | 'science_experimentation'
  | 'technology_computing'
  | 'environment_sustainability'
  | 'business_entrepreneurship'
  | 'health_wellbeing';

type CalibrationResponse = {
  age_band: '10-14' | '15-17' | '18+';
  age_mode: 'discover_and_shape' | 'explore_and_validate' | 'develop_and_optimize';
  age_mode_label: string;
  starting_path: string;
  starting_path_label: string;
  evidence_strength: 'none' | 'limited' | 'emerging' | 'substantial';
  evidence_strength_label: string;
  rationale: string[];
  next_step: string;
  considered_inputs: string[];
  limitations: string[];
  calibration_version: string;
};


const explorationDomainOptions: Array<{ value: ExplorationDomain; label: string }> = [
  { value: 'creative_design', label: 'Creative design' },
  { value: 'analytical_logic', label: 'Analytical and logical problem-solving' },
  { value: 'hands_on_making', label: 'Hands-on building and making' },
  { value: 'social_collaboration', label: 'Social collaboration' },
  { value: 'communication_storytelling', label: 'Communication and storytelling' },
  { value: 'science_experimentation', label: 'Science and experimentation' },
  { value: 'technology_computing', label: 'Technology and computing' },
  { value: 'environment_sustainability', label: 'Environment and sustainability' },
  { value: 'business_entrepreneurship', label: 'Business and entrepreneurship' },
  { value: 'health_wellbeing', label: 'Health and wellbeing' },
];

function FieldLabel({ htmlFor, children, hint }: { htmlFor: string; children: ReactNode; hint?: string }) {
  return (
    <label htmlFor={htmlFor} className="block text-sm font-semibold text-slate-700">
      {children}
      {hint ? <span className="mt-1 block text-xs font-normal leading-5 text-slate-500">{hint}</span> : null}
    </label>
  );
}

const inputClass = 'mt-2 w-full rounded-xl border border-slate-200 bg-white px-3.5 py-3 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:border-teal-500 focus:ring-4 focus:ring-teal-500/10';


export default function StartPage() {
  const { apiStatus, checkApi } = useApiStatus();
  const [age, setAge] = useState('16');
  const { mode: themeMode, setMode: setThemeMode } = useModeTheme();
  const [careerClarity, setCareerClarity] = useState<Rating>('low');
  const [currentGoal, setCurrentGoal] = useState('');
  const [evidenceCount, setEvidenceCount] = useState('0');
  const [priorActivitySummary, setPriorActivitySummary] = useState('');
  const [evidenceQuality, setEvidenceQuality] = useState<EvidenceQuality>('unknown');
  const [experience, setExperience] = useState<ExperienceLevel>('none');
  const [explorationNeed, setExplorationNeed] = useState<Rating>('medium');
  const [journeyPreference, setJourneyPreference] = useState<JourneyPreference>('automatic');
  const [unexploredDomains, setUnexploredDomains] = useState<ExplorationDomain[]>([]);
  const [educationSummary, setEducationSummary] = useState('');
  const [skillsSummary, setSkillsSummary] = useState('');
  const [experienceSummary, setExperienceSummary] = useState('');
  const [planningConstraints, setPlanningConstraints] = useState('');
  const [desiredTimeline, setDesiredTimeline] = useState<DesiredTimeline>('unspecified');
  const [contradictoryEvidence, setContradictoryEvidence] = useState(false);
  const [careerGoalChanged, setCareerGoalChanged] = useState(false);
  const [reenterDiscovery, setReenterDiscovery] = useState(false);
  const [calibration, setCalibration] = useState<CalibrationResponse | null>(null);
  // Theme follows the entered age live (visual only); once a result exists it follows the API's starting mode.
  useEffect(() => {
    const fromApi = calibration ? modeFromApi(calibration.age_mode) : null;
    const parsed = Number(age);
    setThemeMode(fromApi ?? (age.trim() !== '' && Number.isFinite(parsed) ? modeFromAge(parsed) : 'explore'));
  }, [age, calibration, setThemeMode]);
  const [calibrating, setCalibrating] = useState(false);
  const [calibrationError, setCalibrationError] = useState<string | null>(null);
  const isAdultEntry = Number(age) >= 18;

  const submitCalibration = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCalibrating(true);
    setCalibrationError(null);
    setCalibration(null);

    const requestBody = {
      age: Number(age),
      career_clarity: careerClarity,
      prior_evidence_count: Number(evidenceCount),
      prior_activity_summary: priorActivitySummary.trim() || null,
      prior_evidence_quality: evidenceQuality,
      prior_projects_experience: experience,
      exploration_need: explorationNeed,
      current_goal: currentGoal.trim() || null,
      unexplored_domains: unexploredDomains,
      education_summary: isAdultEntry ? educationSummary.trim() || null : null,
      skills_summary: isAdultEntry ? skillsSummary.trim() || null : null,
      experience_summary: isAdultEntry ? experienceSummary.trim() || null : null,
      planning_constraints: isAdultEntry ? planningConstraints.trim() || null : null,
      desired_timeline: isAdultEntry ? desiredTimeline : 'unspecified',
      contradictory_evidence: contradictoryEvidence,
      career_goal_changed: careerGoalChanged,
      reenter_discovery: reenterDiscovery,
      journey_preference: journeyPreference,
    };

    try {
      const response = await fetch(`${apiBaseUrl}/api/calibration`, {
        method: 'POST',
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify(requestBody),
        signal: AbortSignal.timeout(8000),
      });
      if (!response.ok) {
        const errorBody = (await response.json().catch(() => null)) as { detail?: string | Array<{ msg?: string }> } | null;
        const detail = Array.isArray(errorBody?.detail)
          ? errorBody.detail.map((item) => item.msg).filter(Boolean).join(' ')
          : errorBody?.detail;
        throw new Error(detail || `Calibration request failed with HTTP ${response.status}.`);
      }
      const result = (await response.json()) as CalibrationResponse;
      setCalibration(result);
    } catch (error) {
      setCalibrationError(
        error instanceof Error
          ? `${error.message} Make sure the FastAPI server is running and VITE_API_BASE_URL is correct.`
          : 'The calibration request failed. Check the API connection and try again.',
      );
    } finally {
      setCalibrating(false);
    }
  };

  return (
    <div className="page-body">
      <div className="grid items-start gap-10 py-10 lg:grid-cols-[0.82fr_1.18fr] lg:gap-12 lg:py-14">
        <div className="pt-2 lg:sticky lg:top-24">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Start here</p>
          <h1 className="mt-2 text-4xl font-semibold tracking-tight text-ink sm:text-5xl">Find your starting path.</h1>
          <p className="mt-4 text-base leading-7 text-slate-600">Tell us a little about where you are, and we will suggest a good place to begin.</p>
          <div className="mt-8 space-y-3" role="list" aria-label="SkillScope age modes">
            {MODE_ORDER.map((key) => {
              const mode = ageModeDescriptions[MODE_ORDER.indexOf(key)];
              const active = themeMode === key;
              return (
                <div key={mode.ages} role="listitem">
                  <TiltCard maxTilt={5} className={`flex gap-4 rounded-2xl border bg-white/80 p-4 shadow-sm ${active ? 'border-transparent shadow-soft ring-2 ring-ink' : 'border-white'}`}>
                    <span className="min-w-[4.4rem] rounded-xl px-2 py-2 text-center text-sm font-bold" style={{ background: `linear-gradient(135deg, ${MODES[key].palette.a}, ${MODES[key].palette.c})`, color: '#12243A' }}>{mode.ages}</span>
                    <div><h2 className="font-semibold text-ink">{mode.title}{active ? <span className="ml-2 text-xs font-semibold text-teal-800">Matches the age you entered</span> : null}</h2><p className="mt-1 text-sm leading-6 text-slate-600">{mode.description}</p></div>
                  </TiltCard>
                </div>
              );
            })}
          </div>
        </div>
          <div className="mx-auto w-full max-w-2xl lg:ml-auto">
            <div className="rounded-[2rem] border border-white bg-white/95 p-5 shadow-soft backdrop-blur sm:p-7 lg:p-8">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Takes about a minute</p>
                  <h2 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">Find your starting path</h2>
                  <p className="mt-2 text-sm leading-6 text-slate-500">Rough answers are fine. Nothing is saved.</p>
                </div>
                <div className="hidden h-11 w-11 shrink-0 place-items-center rounded-2xl bg-teal-50 text-teal-700 sm:grid">
                  <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="8.5"/><path d="M12 7v5l3 2" strokeLinecap="round"/></svg>
                </div>
              </div>

              {apiStatus === 'disconnected' ? (
                <div className="mt-5 flex items-center justify-between gap-3 rounded-2xl bg-rose-50 px-4 py-3 text-sm text-rose-800" role="alert">
                  <span>We can't reach the server right now.</span>
                  <button type="button" onClick={() => void checkApi()} className="shrink-0 rounded-full bg-white px-4 py-2 text-xs font-semibold text-rose-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-rose-400">Retry</button>
                </div>
              ) : null}

              <form className="mt-6 space-y-5" onSubmit={submitCalibration}>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <FieldLabel htmlFor="age" hint="Completed years; no birth date needed.">Your age</FieldLabel>
                    <input id="age" className={inputClass} type="number" min={10} max={100} step={1} required value={age} onChange={(event) => setAge(event.target.value)} />
                  </div>
                  <div>
                    <FieldLabel htmlFor="career-clarity" hint="How clear your current direction feels.">Career clarity</FieldLabel>
                    <select id="career-clarity" className={inputClass} value={careerClarity} onChange={(event) => setCareerClarity(event.target.value as Rating)}>
                      <option value="low">Low — still unsure</option>
                      <option value="medium">Medium — a few ideas</option>
                      <option value="high">High — clear direction</option>
                    </select>
                  </div>
                </div>

                <div>
                  <FieldLabel htmlFor="current-goal" hint="Optional. A goal is a hypothesis to explore, not a permanent label.">Current career or domain idea</FieldLabel>
                  <input id="current-goal" className={inputClass} type="text" maxLength={180} placeholder="e.g. software engineering, design, health sciences" value={currentGoal} onChange={(event) => setCurrentGoal(event.target.value)} />
                </div>

                <div>
                  <FieldLabel htmlFor="prior-activity-summary" hint="Briefly describe activities, subjects, challenges or projects you have tried. Do not include sensitive personal details.">What have you tried so far? (optional)</FieldLabel>
                  <textarea id="prior-activity-summary" className={inputClass} rows={2} maxLength={240} placeholder="e.g. built a small website, helped organize an event, tried a science experiment" value={priorActivitySummary} onChange={(event) => setPriorActivitySummary(event.target.value)} />
                </div>

                <div className="border-t border-slate-100 pt-5">
                  <h3 className="text-sm font-semibold text-ink">Which areas have you had little chance to try?</h3>
                  <p className="mt-1 text-xs leading-5 text-slate-500">Select any that fit. Unfamiliarity is an opportunity to explore, not a weakness.</p>
                  <div className="mt-3 grid gap-2 sm:grid-cols-2">
                    {explorationDomainOptions.map((domain) => (
                      <label key={domain.value} className="flex cursor-pointer items-start gap-2.5 rounded-xl border border-slate-100 px-3 py-2.5 text-sm text-slate-700 transition hover:border-teal-200">
                        <input
                          className="mt-0.5 h-4 w-4 shrink-0 accent-teal-600"
                          type="checkbox"
                          checked={unexploredDomains.includes(domain.value)}
                          onChange={(event) => setUnexploredDomains((current) => event.target.checked
                            ? [...current, domain.value]
                            : current.filter((item) => item !== domain.value))}
                        />
                        <span>{domain.label}</span>
                      </label>
                    ))}
                  </div>
                </div>

                <div className="border-t border-slate-100 pt-5">
                  <h3 className="text-sm font-semibold text-ink">What evidence do you already have?</h3>
                  <p className="mt-1 text-xs leading-5 text-slate-500">Count activities, relevant projects, work samples or other experiences you choose to include.</p>
                  <div className="mt-3 grid gap-4 sm:grid-cols-2">
                    <div>
                      <FieldLabel htmlFor="evidence-count" hint="If you are unsure, enter 0 and describe your activities above.">Number of evidence items (if known)</FieldLabel>
                      <input id="evidence-count" className={inputClass} type="number" min={0} max={10000} step={1} required value={evidenceCount} onChange={(event) => setEvidenceCount(event.target.value)} />
                    </div>
                    <div>
                      <FieldLabel htmlFor="evidence-quality">Evidence quality / variety</FieldLabel>
                      <select id="evidence-quality" className={inputClass} value={evidenceQuality} onChange={(event) => setEvidenceQuality(event.target.value as EvidenceQuality)}>
                        <option value="unknown">Unknown / not sure</option>
                        <option value="low">Limited variety</option>
                        <option value="medium">Some useful variety</option>
                        <option value="high">Broad, relevant evidence</option>
                      </select>
                    </div>
                    <div>
                      <FieldLabel htmlFor="experience">Project / practical experience</FieldLabel>
                      <select id="experience" className={inputClass} value={experience} onChange={(event) => setExperience(event.target.value as ExperienceLevel)}>
                        <option value="none">None yet</option>
                        <option value="some">Some experience</option>
                        <option value="substantial">Substantial experience</option>
                      </select>
                    </div>
                    <div>
                      <FieldLabel htmlFor="exploration-need">Need to explore new areas</FieldLabel>
                      <select id="exploration-need" className={inputClass} value={explorationNeed} onChange={(event) => setExplorationNeed(event.target.value as Rating)}>
                        <option value="low">Low — focus on a direction</option>
                        <option value="medium">Medium — some exploration</option>
                        <option value="high">High — explore broadly</option>
                      </select>
                    </div>
                  </div>
                </div>

                {isAdultEntry ? (
                  <div className="border-t border-slate-100 pt-5">
                    <h3 className="text-sm font-semibold text-ink">Extra context for adult career planning</h3>
                    <p className="mt-1 text-xs leading-5 text-slate-500">All fields are optional. Share only what is useful; do not enter sensitive personal information. These details are used for this request only.</p>
                    <div className="mt-3 space-y-4">
                      <div>
                        <FieldLabel htmlFor="education-summary">Education / training context</FieldLabel>
                        <input id="education-summary" className={inputClass} type="text" maxLength={200} placeholder="e.g. B.Tech Computer Science, currently studying" value={educationSummary} onChange={(event) => setEducationSummary(event.target.value)} />
                      </div>
                      <div>
                        <FieldLabel htmlFor="skills-summary">Skills you can currently evidence</FieldLabel>
                        <textarea id="skills-summary" className={inputClass} rows={2} maxLength={300} placeholder="e.g. Python, SQL, data visualization, presentation" value={skillsSummary} onChange={(event) => setSkillsSummary(event.target.value)} />
                      </div>
                      <div>
                        <FieldLabel htmlFor="experience-summary">Projects, work, volunteering or portfolio</FieldLabel>
                        <textarea id="experience-summary" className={inputClass} rows={2} maxLength={300} placeholder="A brief summary of practical work you have done" value={experienceSummary} onChange={(event) => setExperienceSummary(event.target.value)} />
                      </div>
                      <div>
                        <FieldLabel htmlFor="planning-constraints">Optional planning constraints</FieldLabel>
                        <input id="planning-constraints" className={inputClass} type="text" maxLength={240} placeholder="e.g. 5 hours per week, prefer low-cost resources" value={planningConstraints} onChange={(event) => setPlanningConstraints(event.target.value)} />
                      </div>
                      <div>
                        <FieldLabel htmlFor="desired-timeline">Preferred planning timeline</FieldLabel>
                        <select id="desired-timeline" className={inputClass} value={desiredTimeline} onChange={(event) => setDesiredTimeline(event.target.value as DesiredTimeline)}>
                          <option value="unspecified">Not sure yet</option>
                          <option value="under_3_months">Under 3 months</option>
                          <option value="3_to_6_months">3–6 months</option>
                          <option value="6_to_12_months">6–12 months</option>
                          <option value="over_12_months">Over 12 months</option>
                        </select>
                      </div>
                    </div>
                  </div>
                ) : null}

                <div className="border-t border-slate-100 pt-5">
                  <h3 className="text-sm font-semibold text-ink">Choose how you'd like to start</h3>
                  <div className="mt-3">
                    <FieldLabel htmlFor="journey-preference">Preferred journey</FieldLabel>
                    <select id="journey-preference" className={inputClass} value={journeyPreference} onChange={(event) => setJourneyPreference(event.target.value as JourneyPreference)}>
                      <option value="automatic">Recommend a starting point</option>
                      <option value="explore">Explore from a fresh perspective</option>
                      <option value="validate">Validate a direction I have in mind</option>
                      <option value="optimize">Improve a direction I'm already pursuing</option>
                    </select>
                  </div>

                  <div className="mt-4 space-y-3">
                    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-100 p-3.5 transition hover:border-teal-200">
                      <input className="mt-1 h-4 w-4 accent-teal-600" type="checkbox" checked={contradictoryEvidence} onChange={(event) => setContradictoryEvidence(event.target.checked)} />
                      <span><span className="block text-sm font-semibold text-slate-800">My experiences point in different directions</span><span className="mt-1 block text-xs leading-5 text-slate-500">For example, your stated interests and practical experiences do not seem to align.</span></span>
                    </label>
                    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-100 p-3.5 transition hover:border-teal-200">
                      <input className="mt-1 h-4 w-4 accent-teal-600" type="checkbox" checked={careerGoalChanged} onChange={(event) => setCareerGoalChanged(event.target.checked)} />
                      <span><span className="block text-sm font-semibold text-slate-800">My career goal has changed recently</span><span className="mt-1 block text-xs leading-5 text-slate-500">Calibrate against the current direction instead of assuming earlier evidence still fits.</span></span>
                    </label>
                    <label className="flex cursor-pointer items-start gap-3 rounded-xl border border-slate-100 p-3.5 transition hover:border-teal-200">
                      <input className="mt-1 h-4 w-4 accent-teal-600" type="checkbox" checked={reenterDiscovery} onChange={(event) => setReenterDiscovery(event.target.checked)} />
                      <span><span className="block text-sm font-semibold text-slate-800">I'd like to re-enter discovery</span><span className="mt-1 block text-xs leading-5 text-slate-500">Career exploration can be restarted at any age; the activities remain age-appropriate.</span></span>
                    </label>
                  </div>
                </div>

                <button type="submit" disabled={calibrating} className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-ink px-5 py-3.5 font-semibold text-white shadow-soft transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/20 disabled:cursor-wait disabled:opacity-70">
                  {calibrating ? 'Calibrating your starting path…' : 'Calibrate my starting path'}
                  {!calibrating ? <svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 12h14m-6-6 6 6-6 6" strokeLinecap="round" strokeLinejoin="round" /></svg> : null}
                </button>
              </form>

              {calibrationError ? (
                <div className="mt-5 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-800" role="alert">{calibrationError}</div>
              ) : null}

              {calibration ? (
                <section className="mt-6 rounded-2xl border border-teal-100 bg-gradient-to-br from-teal-50/80 to-white p-5 sm:p-6" aria-live="polite" aria-labelledby="result-heading">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <p className="text-xs font-bold uppercase tracking-[0.16em] text-teal-700">Your calibration result</p>
                    <span className="rounded-full border border-teal-100 bg-white px-3 py-1 text-xs font-semibold text-teal-800">Age band {calibration.age_band}</span>
                  </div>
                  <div className="mt-3 flex flex-wrap items-center gap-4"><ModeCompass mode={calibration.age_mode} /><h3 id="result-heading" className="text-2xl font-semibold tracking-tight text-ink">{calibration.age_mode_label}</h3></div>
                  <p className="mt-1 text-sm text-slate-600">Recommended starting path: <span className="font-semibold text-slate-900">{calibration.starting_path_label}</span></p>

                  <div className="mt-4 rounded-xl border border-white bg-white/90 p-4">
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-slate-400">Evidence coverage</p>
                    <p className="mt-1 font-semibold text-ink">{calibration.evidence_strength_label}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500">This describes how much supporting information was reported—not ability or future potential.</p>
                  </div>

                  <div className="mt-5">
                    <h4 className="text-sm font-semibold text-ink">Why this is the starting point</h4>
                    <ul className="mt-3 space-y-2.5">
                      {calibration.rationale.map((reason, index) => (
                        <li key={`${index}-${reason}`} className="flex gap-2.5 text-sm leading-6 text-slate-600">
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-teal-600" />
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="mt-5 rounded-xl bg-ink p-4 text-white">
                    <p className="text-xs font-bold uppercase tracking-[0.12em] text-teal-200">Suggested next step</p>
                    <p className="mt-2 text-sm leading-6 text-slate-100">{calibration.next_step}</p>
                  </div>

                  <details className="mt-4 rounded-xl border border-slate-200 bg-white p-3.5">
                    <summary className="cursor-pointer text-sm font-semibold text-slate-700">How to interpret this result</summary>
                    <ul className="mt-3 space-y-2 pl-4 text-xs leading-5 text-slate-500 marker:text-slate-400">
                      {calibration.limitations.map((limitation) => <li key={limitation} className="list-disc">{limitation}</li>)}
                    </ul>
                    <p className="mt-3 text-xs text-slate-400">Rule version {calibration.calibration_version} · The API does not persist this profile.</p>
                  </details>

                  <button type="button" onClick={() => { setCalibration(null); setCalibrationError(null); }} className="mt-4 rounded-lg px-2 py-2 text-sm font-semibold text-teal-800 underline decoration-teal-300 underline-offset-4 hover:text-teal-950 focus:outline-none focus:ring-2 focus:ring-teal-500">Adjust answers and recalibrate</button>
                </section>
              ) : null}

              <p className="mt-5 border-t border-slate-100 pt-4 text-xs leading-5 text-slate-400">This uses transparent rules, not a validated psychometric model. Inputs are used for this request only and are not saved.</p>
            </div>
          </div>
      </div>
      <NextStep to="/profile" label="Create my profile" blurb="This calibration is not saved. Create a profile to keep your evidence and get challenges, possibilities and a plan." />
    </div>
  );
}
