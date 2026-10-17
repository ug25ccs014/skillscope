import { useEffect, useState } from 'react';

export type RouteInfo = { path: string; label: string; title: string; hideInNav?: boolean };

/** Pages of the site, in journey order. Hash routing keeps the app a static site with no server rewrites. */
export const routes: RouteInfo[] = [
  { path: '/', label: 'Home', title: 'SkillScope AI — Discover what you could become' },
  { path: '/start', label: 'Start', title: 'Find your starting path' },
  { path: '/profile', label: 'Profile', title: 'Your evidence profile' },
  { path: '/baseline', label: 'Baseline', title: 'Your starting snapshot', hideInNav: true },
  { path: '/challenges', label: 'Challenges', title: 'Daily challenge' },
  { path: '/careers', label: 'Careers', title: 'Career possibilities' },
  { path: '/plan', label: 'Plan', title: 'Your pathway plan' },
  { path: '/sources', label: 'Sources & privacy', title: 'Sources and privacy' },
  { path: '/demo', label: 'Demo', title: 'Try a demo profile', hideInNav: true },
  { path: '/login', label: 'Log in', title: 'Log in', hideInNav: true },
];

export const toHref = (path: string) => `#${path}`;

export function readPath(): string {
  const hash = window.location.hash.replace(/^#/, '');
  return hash.startsWith('/') ? hash.split('?')[0] : '/';
}

export function useRoute(): string {
  const [path, setPath] = useState(readPath);
  useEffect(() => {
    const onChange = () => setPath(readPath());
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return path;
}
