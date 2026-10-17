import DemoProfiles from '../components/DemoProfiles';
import { apiBaseUrl } from '../shared/api';
import { NextStep } from './PageParts';

export default function DemoPage() {
  return <div className="page-body"><DemoProfiles apiBaseUrl={apiBaseUrl} /><NextStep to="/challenges" label="Start the challenge" blurb="With a demo profile selected, try a challenge and watch the evidence loop." /></div>;
}
