import { useEffect, useState } from 'react';
import { MOTION_EVENT, readMotionOff } from './motionSwitch';

const QUERY = '(prefers-reduced-motion: reduce)';

function read(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return true;
  return readMotionOff() || window.matchMedia(QUERY).matches;
}

/** True when the visitor's OS/browser, or the in-app "reduce motion" switch, asks for less motion. Defaults to true if unknown (safe default). */
export function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState<boolean>(read);
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const media = window.matchMedia(QUERY);
    const onChange = () => setReduced(read());
    onChange();
    media.addEventListener('change', onChange);
    window.addEventListener(MOTION_EVENT, onChange);
    return () => { media.removeEventListener('change', onChange); window.removeEventListener(MOTION_EVENT, onChange); };
  }, []);
  return reduced;
}
