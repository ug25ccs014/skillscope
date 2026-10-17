import { useState, type FormEvent, type ReactNode } from 'react';
import ConstellationSvg from '../motion/ConstellationSvg';
import { useModeTheme } from '../motion/ModeContext';
import { signIn, signOut, useSession } from '../shared/auth';
import { toHref } from '../router';

type Tab = 'login' | 'signup';
type Errors = Partial<Record<'name' | 'email' | 'password', string>>;

const perks = [
  { text: 'Try small activities', icon: 'M13 3 5 14h6l-1 7 8-11h-6l1-7Z', tint: 'from-amber-300 to-orange-400' },
  { text: 'Keep your evidence', icon: 'M4 19V9m6 10V5m6 14v-7m4 7H2', tint: 'from-teal-300 to-sky-400' },
  { text: 'Get your next steps', icon: 'M5 12h14m-6-6 6 6-6 6', tint: 'from-indigo-300 to-violet-400' },
];

const inputBase = 'w-full rounded-2xl border bg-white py-3.5 pl-12 pr-4 text-sm text-slate-800 outline-none transition placeholder:text-slate-400 focus:ring-4';
const inputOk = 'border-slate-200 focus:border-teal-500 focus:ring-teal-500/15';
const inputBad = 'border-rose-300 focus:border-rose-400 focus:ring-rose-400/15';

function Field({ id, label, icon, error, children }: { id: string; label: string; icon: string; error?: string; children: ReactNode }) {
  return (
    <div>
      <label htmlFor={id} className="block text-sm font-semibold text-slate-700">{label}</label>
      <div className="relative mt-2">
        <svg aria-hidden="true" viewBox="0 0 24 24" className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={icon} /></svg>
        {children}
      </div>
      {error ? <p id={`${id}-error`} className="mt-1.5 text-xs font-medium text-rose-600">{error}</p> : null}
    </div>
  );
}

export default function LoginPage() {
  const { mode } = useModeTheme();
  const session = useSession();
  const [tab, setTab] = useState<Tab>('login');
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [errors, setErrors] = useState<Errors>({});
  const [busy, setBusy] = useState(false);

  const switchTab = (next: Tab) => { setTab(next); setErrors({}); };

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const next: Errors = {};
    if (tab === 'signup' && !name.trim()) next.name = 'Please tell us what to call you.';
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) next.email = 'Enter a valid email address.';
    if (tab === 'signup' ? password.length < 8 : password.length < 1) next.password = tab === 'signup' ? 'Use at least 8 characters.' : 'Enter your password.';
    setErrors(next);
    if (Object.keys(next).length) return;
    setBusy(true);
    window.setTimeout(() => {
      signIn(email, tab === 'signup' ? name : undefined);
      setBusy(false);
      window.location.hash = toHref('/start');
    }, 500);
  };

  return (
    <div className="page-body py-8 sm:py-12">
      <div className="mx-auto grid max-w-5xl overflow-hidden rounded-[2.5rem] bg-white shadow-soft lg:grid-cols-[0.95fr_1.05fr]">
        {/* Left: brand panel */}
        <div className="hero-stage relative isolate hidden overflow-hidden p-10 text-white lg:flex lg:flex-col lg:justify-between">
          <div aria-hidden="true" className="absolute inset-0 -z-10 opacity-70"><ConstellationSvg mode={mode} /></div>
          <div aria-hidden="true" className="hero-vignette absolute inset-0 -z-10" />
          <a href={toHref('/')} className="inline-flex items-center gap-3 self-start rounded-full focus:outline-none focus:ring-4 focus:ring-white/30" aria-label="SkillScope home">
            <span className="grid h-10 w-10 place-items-center rounded-2xl bg-white/15 backdrop-blur"><svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="8.1" /><circle cx="12" cy="12" r="3.1" /><path d="M12 1.8v3M22.2 12h-3M12 22.2v-3M1.8 12h3" strokeLinecap="round" /></svg></span>
            <span className="text-lg font-bold tracking-tight">SkillScope<span className="text-[var(--mode-accent)]"> AI</span></span>
          </a>
          <div>
            <h2 className="font-display text-5xl font-semibold leading-[1.05] tracking-[-0.02em]">{tab === 'login' ? 'Welcome back.' : 'Start your journey.'}</h2>
            <p className="mt-3 max-w-xs text-base leading-7 text-white/80">Discover what you could become.</p>
            <ul className="mt-8 space-y-3">
              {perks.map((perk) => (
                <li key={perk.text} className="flex w-fit items-center gap-3 rounded-full bg-white/95 py-2 pl-2 pr-5 text-sm font-bold text-ink shadow-soft">
                  <span className={`grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br ${perk.tint} text-white`}><svg aria-hidden="true" viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round"><path d={perk.icon} /></svg></span>
                  {perk.text}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Right: form */}
        <div className="p-6 sm:p-10 lg:p-12">
          {session ? (
            <div className="flex h-full flex-col items-center justify-center py-8 text-center">
              <span className="grid h-20 w-20 place-items-center rounded-full bg-gradient-to-br from-teal-400 to-sky-500 text-3xl font-bold text-white shadow-glow">{session.name.charAt(0).toUpperCase()}</span>
              <h1 className="mt-5 font-display text-3xl font-semibold text-ink">Hi, {session.name}</h1>
              <p className="mt-1 text-sm text-slate-500">{session.email}</p>
              <div className="mt-7 flex flex-wrap justify-center gap-3">
                <a href={toHref('/start')} className="inline-flex items-center justify-center rounded-full bg-ink px-7 py-3.5 text-sm font-bold text-white shadow-soft transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/25">Continue</a>
                <button type="button" onClick={signOut} className="inline-flex items-center justify-center rounded-full border border-slate-300 bg-white px-7 py-3.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-teal-500/20">Log out</button>
              </div>
            </div>
          ) : (
            <>
              <div role="tablist" aria-label="Log in or create an account" className="mx-auto flex w-full max-w-sm rounded-full bg-slate-100 p-1.5">
                {([['login', 'Log in'], ['signup', 'Create account']] as const).map(([key, label]) => (
                  <button key={key} type="button" role="tab" aria-selected={tab === key} onClick={() => switchTab(key)} className={`flex-1 rounded-full px-4 py-2.5 text-sm font-bold transition focus:outline-none focus:ring-2 focus:ring-teal-500 ${tab === key ? 'bg-white text-ink shadow-sm' : 'text-slate-500 hover:text-ink'}`}>{label}</button>
                ))}
              </div>

              <div className="mx-auto mt-8 max-w-sm">
                <h1 className="font-display text-3xl font-semibold tracking-tight text-ink">{tab === 'login' ? 'Log in' : 'Create your account'}</h1>
                <p className="mt-1 text-sm text-slate-500">{tab === 'login' ? 'Good to see you again.' : 'It only takes a moment.'}</p>

                <form onSubmit={submit} noValidate className="mt-6 space-y-4">
                  {tab === 'signup' ? (
                    <Field id="auth-name" label="Your name" icon="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 8a7 7 0 0 1 14 0" error={errors.name}>
                      <input id="auth-name" className={`${inputBase} ${errors.name ? inputBad : inputOk}`} type="text" autoComplete="given-name" maxLength={60} value={name} onChange={(e) => setName(e.target.value)} placeholder="First name or nickname" aria-invalid={Boolean(errors.name)} aria-describedby={errors.name ? 'auth-name-error' : undefined} />
                    </Field>
                  ) : null}
                  <Field id="auth-email" label="Email" icon="M4 6h16v12H4zM4 7l8 6 8-6" error={errors.email}>
                    <input id="auth-email" className={`${inputBase} ${errors.email ? inputBad : inputOk}`} type="email" autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" aria-invalid={Boolean(errors.email)} aria-describedby={errors.email ? 'auth-email-error' : undefined} />
                  </Field>
                  <Field id="auth-password" label="Password" icon="M6 11h12v9H6zM8.5 11V8a3.5 3.5 0 0 1 7 0v3" error={errors.password}>
                    <input id="auth-password" className={`${inputBase} pr-14 ${errors.password ? inputBad : inputOk}`} type={show ? 'text' : 'password'} autoComplete={tab === 'login' ? 'current-password' : 'new-password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder={tab === 'login' ? 'Your password' : 'At least 8 characters'} aria-invalid={Boolean(errors.password)} aria-describedby={errors.password ? 'auth-password-error' : undefined} />
                    <button type="button" onClick={() => setShow((v) => !v)} aria-pressed={show} className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full px-3 py-1.5 text-xs font-bold text-teal-800 hover:bg-teal-50 focus:outline-none focus:ring-2 focus:ring-teal-500">{show ? 'Hide' : 'Show'}</button>
                  </Field>

                  <button type="submit" disabled={busy} className="inline-flex w-full items-center justify-center rounded-full bg-ink px-6 py-4 text-sm font-bold text-white shadow-soft transition hover:-translate-y-0.5 hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/25 disabled:cursor-wait disabled:opacity-70">
                    {busy ? 'One moment…' : tab === 'login' ? 'Log in' : 'Create account'}
                  </button>
                </form>

                <div className="my-6 flex items-center gap-3 text-xs font-semibold uppercase tracking-widest text-slate-400"><span className="h-px flex-1 bg-slate-200" />or<span className="h-px flex-1 bg-slate-200" /></div>
                <a href={toHref('/start')} className="inline-flex w-full items-center justify-center rounded-full border border-slate-300 bg-white px-6 py-3.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-4 focus:ring-teal-500/20">Continue without an account</a>
                <p className="mt-5 text-center text-xs text-slate-400">Demo sign-in: details stay on this device only.</p>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
