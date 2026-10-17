import type { ComponentType } from 'react';
import SiteLayout from './layout/SiteLayout';
import HomePage from './pages/HomePage';
import StartPage from './pages/StartPage';
import SourcesPage from './pages/SourcesPage';
import { ProfilePage, ChallengesPage, CareersPage, PlanPage } from './pages/FlowPages';
import { toHref, useRoute } from './router';

function NotFoundPage() {
  return (
    <div className="py-24 text-center">
      <p className="text-xs font-bold uppercase tracking-[0.18em] text-teal-700">Page not found</p>
      <h1 className="mt-2 text-4xl font-semibold tracking-tight text-ink">We could not find that page.</h1>
      <a href={toHref('/')} className="mt-6 inline-flex rounded-xl bg-ink px-5 py-3 text-sm font-semibold text-white focus:outline-none focus:ring-4 focus:ring-teal-500/20">Go to the home page</a>
    </div>
  );
}

const pages: Record<string, ComponentType> = {
  '/': HomePage,
  '/start': StartPage,
  '/profile': ProfilePage,
  '/challenges': ChallengesPage,
  '/careers': CareersPage,
  '/plan': PlanPage,
  '/sources': SourcesPage,
};

export default function App() {
  const path = useRoute();
  const Page = pages[path] ?? NotFoundPage;
  return (
    <SiteLayout path={path}>
      <div key={path} className="page-enter"><Page /></div>
    </SiteLayout>
  );
}
