import { useEffect, useRef, useState, type ReactNode } from 'react';
import { routes, toHref } from '../router';
import { useApiStatus } from '../shared/api';
import { signOut, useSession } from '../shared/auth';
import GradientBackdrop from '../motion/GradientBackdrop';
import JourneyStrip from './JourneyStrip';

const navLink = (active: boolean) =>
  `rounded-full px-4 py-2 text-sm font-semibold transition focus:outline-none focus:ring-2 focus:ring-teal-500 ${active ? 'bg-teal-50 text-teal-800' : 'text-slate-600 hover:bg-slate-100 hover:text-ink'}`;

const navRoutes = routes.filter((item) => !item.hideInNav);

export default function SiteLayout({ path, children }: { path: string; children: ReactNode }) {
  const { apiStatus, checkApi } = useApiStatus();
  const session = useSession();
  const [menuOpen, setMenuOpen] = useState(false);
  const mainRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    setMenuOpen(false);
    window.scrollTo(0, 0);
    const route = routes.find((item) => item.path === path);
    document.title = route ? (path === '/' ? route.title : `${route.title} · SkillScope AI`) : 'Page not found · SkillScope AI';
    mainRef.current?.focus({ preventScroll: true });
  }, [path]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => { if (event.key === 'Escape') setMenuOpen(false); };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className="relative min-h-screen overflow-x-clip bg-[#F7F9FC] text-ink">
      <a href="#main-content" onClick={(e) => { e.preventDefault(); mainRef.current?.focus(); }} className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-lg focus:bg-ink focus:px-4 focus:py-2 focus:text-sm focus:font-semibold focus:text-white">Skip to content</a>
      <GradientBackdrop />

      <header className="sticky top-3 z-40 mx-auto mt-3 w-[calc(100%-1.5rem)] max-w-7xl rounded-[1.75rem] border border-white bg-white/80 shadow-sm backdrop-blur-xl sm:w-[calc(100%-4rem)] lg:w-[calc(100%-6rem)]">
        <div className="flex items-center justify-between gap-3 px-4 py-2.5 sm:px-5">
          <a href={toHref('/')} className="flex items-center gap-3 rounded-xl focus:outline-none focus:ring-2 focus:ring-teal-500 focus:ring-offset-4" aria-label="SkillScope home">
            <span className="grid h-10 w-10 place-items-center rounded-2xl bg-ink text-white shadow-soft">
              <svg aria-hidden="true" viewBox="0 0 24 24" className="h-6 w-6" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="12" r="8.1" /><circle cx="12" cy="12" r="3.1" /><path d="M12 1.8v3M22.2 12h-3M12 22.2v-3M1.8 12h3" strokeLinecap="round" /></svg>
            </span>
            <span className="text-lg font-bold tracking-tight">SkillScope<span className="text-teal-600"> AI</span></span>
          </a>

          <nav aria-label="Main" className="hidden items-center gap-1 lg:flex">
            {navRoutes.map((item) => <a key={item.path} href={toHref(item.path)} aria-current={item.path === path ? 'page' : undefined} className={navLink(item.path === path)}>{item.label}</a>)}
          </nav>

          <div className="flex items-center gap-2">
            {apiStatus === 'disconnected' ? (
              <button type="button" onClick={() => void checkApi()} className="hidden items-center gap-2 rounded-full bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-700 focus:outline-none focus:ring-2 focus:ring-rose-400 sm:inline-flex"><span className="h-2 w-2 rounded-full bg-rose-500" />Offline · retry</button>
            ) : null}
{session ? (
              <>
                <a href={toHref('/login')} className="hidden items-center gap-2 rounded-full bg-slate-100 py-1.5 pl-1.5 pr-4 text-sm font-semibold text-ink transition hover:bg-slate-200 focus:outline-none focus:ring-2 focus:ring-teal-500 sm:inline-flex" aria-label="Your account">
                  <span className="grid h-8 w-8 place-items-center rounded-full bg-gradient-to-br from-teal-400 to-sky-500 text-sm font-bold text-white">{session.name.charAt(0).toUpperCase()}</span>
                  <span className="max-w-[7rem] truncate">{session.name}</span>
                </a>
              </>
            ) : (
              <>
                <a href={toHref('/login')} className="hidden rounded-full px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 focus:outline-none focus:ring-2 focus:ring-teal-500 sm:inline-flex">Log in</a>
                <a href={toHref('/start')} className="hidden items-center rounded-full bg-ink px-5 py-2.5 text-sm font-bold text-white shadow-soft transition hover:bg-slate-800 focus:outline-none focus:ring-4 focus:ring-teal-500/25 sm:inline-flex">Get started</a>
              </>
            )}
            <button type="button" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-controls="mobile-menu" className="inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-500 lg:hidden">
              <span className="sr-only">{menuOpen ? 'Close menu' : 'Open menu'}</span>
              <svg aria-hidden="true" viewBox="0 0 24 24" className="h-5 w-5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">{menuOpen ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}</svg>
            </button>
          </div>
        </div>
        {menuOpen ? (
          <nav id="mobile-menu" aria-label="Main" className="border-t border-slate-200/70 px-4 py-3 lg:hidden">
            <ul className="grid gap-1">
              {navRoutes.map((item) => <li key={item.path}><a href={toHref(item.path)} aria-current={item.path === path ? 'page' : undefined} className={`block ${navLink(item.path === path)}`}>{item.label}</a></li>)}
              <li>{session ? <button type="button" onClick={() => { signOut(); setMenuOpen(false); }} className={`block w-full text-left ${navLink(false)}`}>Log out ({session.name})</button> : <a href={toHref('/login')} className={`block ${navLink(path === '/login')}`}>Log in</a>}</li>
            </ul>
          </nav>
        ) : null}
      </header>

      {apiStatus === 'disconnected' ? (
        <div role="alert" className="relative border-b border-rose-200 bg-rose-50 px-5 py-3 text-sm text-rose-900 sm:px-8 lg:px-12">
          <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3">
            <p>We can't reach the server right now, so saving and loading won't work yet.</p>
            <button type="button" onClick={() => void checkApi()} className="rounded-lg border border-rose-300 bg-white px-3 py-1.5 text-xs font-semibold text-rose-800 focus:outline-none focus:ring-2 focus:ring-rose-400">Retry connection</button>
          </div>
        </div>
      ) : null}

      <main id="main-content" ref={mainRef} tabIndex={-1} className="relative z-10 mx-auto max-w-7xl px-5 outline-none sm:px-8 lg:px-12">
        <JourneyStrip path={path} />
        {children}
      </main>

      <footer className="relative z-10 mx-auto flex max-w-7xl flex-col items-center gap-2 px-5 py-8 text-center text-xs text-slate-500 sm:px-8 lg:px-12">
        <p className="font-bold text-slate-700">SkillScope<span className="text-teal-600"> AI</span></p>
        <p>A prototype for exploring ideas. Suggestions are not a test result or a career verdict.</p>
      </footer>
    </div>
  );
}
