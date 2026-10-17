import { useCallback, useEffect, useState, type FormEvent } from 'react';
import PrivacyShield from '../motion/PrivacyShield';
import { useMotionSwitch } from '../motion/motionSwitch';
import { toHref } from '../router';

const PROFILE_STORAGE_KEY = 'skillscope_student_evidence_profile_v1';
const PREFERENCE_STORAGE_KEY = 'skillscope_discovery_preference_v1';

const journeyOptions: Array<[string, string]> = [
  ['balanced', 'Balanced mix'], ['explore', 'Explore something new'], ['develop', 'Build on what I like'], ['validate', 'Test an idea I have'], ['alternative', 'Show me alternatives'],
];
const domainOptions: Array<[string, string]> = [
  ['logic_data', 'Logic & data'], ['science_research', 'Science & research'], ['technology', 'Technology'], ['design_creative', 'Design & creative'], ['communication', 'Communication'],
  ['helping_social', 'Helping & social'], ['business', 'Business'], ['hands_on_spatial', 'Hands-on & spatial'], ['environment', 'Environment'],
];
const formatOptions: Array<[string, string, string]> = [
  ['text', 'Reading', 'Text-based activities'], ['spoken', 'Speaking', 'Talk it through instead of writing'], ['visual', 'Visual', 'Diagrams and pictures first'], ['low_materials', 'Low materials', 'Needs only paper or nothing at all'],
];

type Prefs = { journey_preference: string; preferred_domains: string[]; accessibility_formats: string[]; updated_at: string | null; persisted: boolean };

const chip = (on: boolean) => `inline-flex cursor-pointer items-center gap-2 rounded-full border px-4 py-2 text-sm font-semibold transition focus-within:ring-4 focus-within:ring-teal-500/20 ${on ? 'border-teal-500 bg-teal-50 text-teal-900' : 'border-slate-200 bg-white text-slate-700 hover:border-teal-300'}`;

export default function PrivacyControls({ apiBaseUrl }: { apiBaseUrl: string }) {
  const [profileId, setProfileId] = useState<string | null>(() => { try { return window.localStorage.getItem(PROFILE_STORAGE_KEY); } catch { return null; } });
  const [prefs, setPrefs] = useState<Prefs | null>(null);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [motionOff, setMotionOff] = useMotionSwitch();

  useEffect(() => {
    const sync = () => { try { setProfileId(window.localStorage.getItem(PROFILE_STORAGE_KEY)); } catch { setProfileId(null); } };
    window.addEventListener('skillscope-profile-changed', sync);
    return () => window.removeEventListener('skillscope-profile-changed', sync);
  }, []);

  const load = useCallback(async (id: string) => {
    setLoading(true); setError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/api/student-profiles/${id}/preferences`, { headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(8000) });
      if (response.status === 404) throw new Error('This browser points to a profile that no longer exists. Create a new profile on the Profile page.');
      if (!response.ok) throw new Error(`Preferences could not be loaded (HTTP ${response.status}).`);
      setPrefs(await response.json() as Prefs);
    } catch (e) { setPrefs(null); setError(e instanceof Error ? e.message : 'Preferences could not be loaded.'); }
    finally { setLoading(false); }
  }, [apiBaseUrl]);

  useEffect(() => { if (profileId) void load(profileId); else setPrefs(null); }, [profileId, load]);

  const toggle = (key: 'preferred_domains' | 'accessibility_formats', value: string) => {
    setSaved(false);
    setPrefs((old) => old ? { ...old, [key]: old[key].includes(value) ? old[key].filter((v) => v !== value) : [...old[key], value] } : old);
  };

  const save = async (event: FormEvent) => {
    event.preventDefault();
    if (!profileId || !prefs) return;
    setSaving(true); setError(null); setSaved(false);
    try {
      const response = await fetch(`${apiBaseUrl}/api/student-profiles/${profileId}/preferences`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, signal: AbortSignal.timeout(8000),
        body: JSON.stringify({ journey_preference: prefs.journey_preference, preferred_domains: prefs.preferred_domains, accessibility_formats: prefs.accessibility_formats }),
      });
      if (!response.ok) {
        let detail = `Preferences could not be saved (HTTP ${response.status}).`;
        try { const body = await response.json() as { detail?: unknown }; if (typeof body.detail === 'string') detail = body.detail; } catch { /* keep fallback */ }
        throw new Error(detail.slice(0, 500));
      }
      const next = await response.json() as Prefs;
      setPrefs(next); setSaved(true);
      try { window.localStorage.setItem(PREFERENCE_STORAGE_KEY, next.journey_preference); } catch { /* storage may be blocked */ }
    } catch (e) { setError(e instanceof Error ? e.message : 'Preferences could not be saved.'); }
    finally { setSaving(false); }
  };

  return (
    <section id="privacy-controls" className="ss-section border-t border-slate-200/80 py-12 sm:py-16" aria-labelledby="controls-heading">
      <div className="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
        <div>
          <div className="float-soft inline-block"><PrivacyShield /></div>
          <p className="ss-section-kicker mt-4 text-xs font-bold uppercase tracking-[0.18em] text-indigo-700">Your controls</p>
          <h2 id="controls-heading" className="mt-2 font-display text-3xl font-semibold tracking-tight text-ink sm:text-4xl">Set it up your way.</h2>
          <p className="mt-3 text-sm leading-7 text-slate-600">These choices only shape which activities you are shown and how they are presented. They are never used to label you or to narrow your options.</p>
          <ul className="mt-5 space-y-2 text-sm leading-6 text-slate-600">
            <li>• Review, correct or delete evidence, or the whole profile, on the <a className="font-semibold text-teal-800 underline underline-offset-4" href={toHref('/profile')}>Profile page</a>.</li>
            <li>• Nothing is sent to an outside AI service, and no social media is read.</li>
            <li>• The prototype is for demo data only. Please do not enter real details.</li>
          </ul>
        </div>

        <div className="space-y-5">
          <div className="rounded-3xl border border-white bg-white/90 p-5 shadow-soft sm:p-7">
            <h3 className="text-lg font-semibold text-ink">Animation</h3>
            <p className="mt-1 text-sm leading-6 text-slate-600">Turn off moving backgrounds, flips and tilts. Your device’s own “reduce motion” setting is always respected as well.</p>
            <label className={`${chip(motionOff)} mt-4`}>
              <input type="checkbox" className="sr-only" checked={motionOff} onChange={(event) => setMotionOff(event.target.checked)} />
              <span aria-hidden="true" className={`grid h-5 w-5 place-items-center rounded-full text-[11px] ${motionOff ? 'bg-teal-600 text-white' : 'bg-slate-200 text-transparent'}`}>✓</span>
              Reduce motion {motionOff ? 'is on' : 'is off'}
            </label>
          </div>

          <form onSubmit={save} className="rounded-3xl border border-white bg-white/90 p-5 shadow-soft sm:p-7" aria-describedby="prefs-note">
            <h3 className="text-lg font-semibold text-ink">Activity preferences</h3>
            <p id="prefs-note" className="mt-1 text-sm leading-6 text-slate-600">Saved with your profile. Leave anything blank to keep a broad mix.</p>
            {!profileId ? (
              <p className="mt-4 rounded-2xl border border-slate-200 bg-slate-50 p-4 text-sm leading-6 text-slate-600">Preferences are saved to a profile. <a className="font-semibold text-teal-800 underline underline-offset-4" href={toHref('/profile')}>Create a profile</a> first, then come back.</p>
            ) : loading && !prefs ? <p role="status" className="mt-4 text-sm text-slate-500">Loading your preferences…</p> : prefs ? (
              <div className="mt-5 space-y-6">
                <div>
                  <label htmlFor="journey-pref" className="text-sm font-semibold text-slate-800">What would you like next?</label>
                  <select id="journey-pref" value={prefs.journey_preference} onChange={(event) => { setSaved(false); setPrefs({ ...prefs, journey_preference: event.target.value }); }} className="mt-2 w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-800 focus:border-teal-500 focus:outline-none sm:max-w-xs">
                    {journeyOptions.map(([value, text]) => <option key={value} value={value}>{text}</option>)}
                  </select>
                </div>
                <fieldset><legend className="text-sm font-semibold text-slate-800">Topics I’m curious about</legend>
                  <div className="mt-2 flex flex-wrap gap-2">{domainOptions.map(([value, text]) => { const on = prefs.preferred_domains.includes(value); return <label key={value} className={chip(on)}><input type="checkbox" className="sr-only" checked={on} onChange={() => toggle('preferred_domains', value)} />{text}</label>; })}</div>
                </fieldset>
                <fieldset><legend className="text-sm font-semibold text-slate-800">How I like to work</legend>
                  <div className="mt-2 flex flex-wrap gap-2">{formatOptions.map(([value, text, hint]) => { const on = prefs.accessibility_formats.includes(value); return <label key={value} className={chip(on)} title={hint}><input type="checkbox" className="sr-only" checked={on} onChange={() => toggle('accessibility_formats', value)} />{text}</label>; })}</div>
                  <p className="mt-2 text-xs leading-5 text-slate-500">These describe formats you prefer. They say nothing about ability.</p>
                </fieldset>
                <div className="flex flex-wrap items-center gap-3">
                  <button type="submit" disabled={saving} className="inline-flex items-center rounded-full bg-ink px-6 py-3 text-sm font-semibold text-white shadow-soft transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/25 disabled:opacity-60">{saving ? 'Saving…' : 'Save preferences'}</button>
                  {saved ? <span role="status" className="text-sm font-semibold text-emerald-800">Saved. {prefs.persisted ? 'These will still be here next time.' : ''}</span> : null}
                </div>
              </div>
            ) : null}
            {error ? <div role="alert" className="mt-4 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm leading-6 text-rose-800">{error}</div> : null}
          </form>
        </div>
      </div>
    </section>
  );
}
