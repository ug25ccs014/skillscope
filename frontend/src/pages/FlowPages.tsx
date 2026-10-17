import EvidenceLedger from '../components/EvidenceLedger';
import DiscoveryLoop from '../components/DiscoveryLoop';
import CareerRecommendations from '../components/CareerRecommendations';
import PathwayPlanner from '../components/PathwayPlanner';
import { apiBaseUrl } from '../shared/api';
import { NextStep, ProfileGate, useSavedProfile } from './PageParts';

export function ProfilePage() {
  return <div className="page-body"><EvidenceLedger apiBaseUrl={apiBaseUrl} /><NextStep to="/challenges" label="Try a challenge" blurb="Next, try a short activity." /></div>;
}
export function ChallengesPage() {
  return <div className="page-body"><DiscoveryLoop apiBaseUrl={apiBaseUrl} /><NextStep to="/careers" label="See career possibilities" blurb="See what your results point to." /></div>;
}
export function CareersPage() {
  const hasProfile = useSavedProfile();
  return <div className="page-body">{hasProfile ? <CareerRecommendations apiBaseUrl={apiBaseUrl} /> : <ProfileGate kind="careers" />}<NextStep to="/plan" label="Build my plan" blurb="Turn an idea into small next steps." /></div>;
}
export function PlanPage() {
  const hasProfile = useSavedProfile();
  return <div className="page-body">{hasProfile ? <PathwayPlanner apiBaseUrl={apiBaseUrl} /> : <ProfileGate kind="plan" />}<NextStep to="/sources" label="Check sources & privacy" blurb="See where facts come from and how your data is handled." /></div>;
}
