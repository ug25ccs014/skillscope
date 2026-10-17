import { useEffect, useState } from 'react';

/**
 * DEMO sign-in. There is no account system in the backend yet, so this only remembers a name and email
 * in this browser. It never stores a password and it protects nothing.
 * To add real accounts later, replace signIn/signOut here with calls to a backend endpoint; the UI does not change.
 */
export type Session = { name: string; email: string };

const KEY = 'skillscope_session_v1';
const EVENT = 'skillscope-auth-changed';

export function readSession(): Session | null {
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as Partial<Session>;
    return parsed.name && parsed.email ? { name: parsed.name, email: parsed.email } : null;
  } catch { return null; }
}

export function signIn(email: string, name?: string): Session {
  const clean = email.trim().toLowerCase();
  const fallback = clean.split('@')[0].replace(/[._-]+/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  const session: Session = { name: (name ?? '').trim() || fallback, email: clean };
  try { window.localStorage.setItem(KEY, JSON.stringify(session)); } catch { /* storage blocked */ }
  window.dispatchEvent(new Event(EVENT));
  return session;
}

export function signOut(): void {
  try { window.localStorage.removeItem(KEY); } catch { /* storage blocked */ }
  window.dispatchEvent(new Event(EVENT));
}

export function useSession(): Session | null {
  const [session, setSession] = useState<Session | null>(readSession);
  useEffect(() => {
    const update = () => setSession(readSession());
    window.addEventListener(EVENT, update);
    window.addEventListener('storage', update);
    return () => { window.removeEventListener(EVENT, update); window.removeEventListener('storage', update); };
  }, []);
  return session;
}
