import { useEffect, useState } from 'react';

const KEY = 'skillscope_motion';
const EVENT = 'skillscope-motion-changed';

/** True when the visitor turned animation off inside the app (separate from the OS-level preference). */
export function readMotionOff(): boolean {
  try { return window.localStorage.getItem(KEY) === 'off'; } catch { return false; }
}

/** Applies the switch to the page and tells motion hooks to re-read their preference. */
export function applyMotionSwitch(off: boolean): void {
  try { if (off) window.localStorage.setItem(KEY, 'off'); else window.localStorage.removeItem(KEY); } catch { /* storage may be blocked */ }
  document.documentElement.dataset.reduceMotion = off ? 'on' : 'off';
  window.dispatchEvent(new Event(EVENT));
}

export function useMotionSwitch(): [boolean, (off: boolean) => void] {
  const [off, setOff] = useState(readMotionOff);
  useEffect(() => {
    const sync = () => setOff(readMotionOff());
    window.addEventListener(EVENT, sync);
    window.addEventListener('storage', sync);
    return () => { window.removeEventListener(EVENT, sync); window.removeEventListener('storage', sync); };
  }, []);
  return [off, applyMotionSwitch];
}

export const MOTION_EVENT = EVENT;
