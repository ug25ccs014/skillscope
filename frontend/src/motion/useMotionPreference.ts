import { useEffect, useState } from 'react';
import { MOTION_EVENT } from './motionSwitch';

export type MotionPreference = {
  /** The visitor asked the OS/browser for less motion (or forced it with ?motion=off). */
  reducedMotion: boolean;
  /** Very low core count or memory: skip smooth-scroll and WebGL. */
  lowPower: boolean;
  /** The browser reports Data Saver. */
  saveData: boolean;
  /** WebGL can actually create a context here (false when forced off with ?webgl=off). */
  webgl: boolean;
  /** Mouse-like pointer with hover (desktop). Touch devices are false. */
  finePointer: boolean;
  /** True only when every gate passes: the animated 3D scene may run. */
  allow3D: boolean;
  /** True when Lenis smooth scrolling may run. */
  allowSmoothScroll: boolean;
};

const QUERY_REDUCED = '(prefers-reduced-motion: reduce)';
const QUERY_FINE = '(hover: hover) and (pointer: fine)';

type NavigatorExtras = Navigator & { deviceMemory?: number; connection?: { saveData?: boolean } };

/**
 * Developer switches for testing the fallbacks (documented in docs/FRONTEND_MOTION.md):
 *   ?motion=off  or localStorage.skillscope_motion = 'off'     -> behave as if reduced motion is on
 *   ?webgl=off   or localStorage.skillscope_motion = 'nowebgl' -> behave as if WebGL is unavailable
 */
function override(): 'off' | 'nowebgl' | null {
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.get('motion') === 'off') return 'off';
    if (params.get('webgl') === 'off') return 'nowebgl';
    const stored = window.localStorage.getItem('skillscope_motion');
    if (stored === 'off' || stored === 'nowebgl') return stored;
  } catch { /* storage may be blocked; ignore */ }
  return null;
}

let webglCache: boolean | null = null;
function detectWebgl(): boolean {
  if (webglCache !== null) return webglCache;
  try {
    const canvas = document.createElement('canvas');
    webglCache = Boolean(canvas.getContext('webgl2') || canvas.getContext('webgl'));
  } catch { webglCache = false; }
  return webglCache;
}

function read(): MotionPreference {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return { reducedMotion: true, lowPower: true, saveData: false, webgl: false, finePointer: false, allow3D: false, allowSmoothScroll: false };
  }
  const forced = override();
  const nav = navigator as NavigatorExtras;
  const reducedMotion = forced === 'off' || window.matchMedia(QUERY_REDUCED).matches;
  const lowPower = (typeof nav.hardwareConcurrency === 'number' && nav.hardwareConcurrency <= 2) || (typeof nav.deviceMemory === 'number' && nav.deviceMemory <= 2);
  const saveData = Boolean(nav.connection?.saveData);
  const webgl = forced !== 'nowebgl' && detectWebgl();
  const finePointer = window.matchMedia(QUERY_FINE).matches;
  const allow3D = !reducedMotion && !lowPower && !saveData && webgl;
  return { reducedMotion, lowPower, saveData, webgl, finePointer, allow3D, allowSmoothScroll: !reducedMotion && !lowPower && !saveData };
}

export function useMotionPreference(): MotionPreference {
  const [pref, setPref] = useState<MotionPreference>(read);
  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return;
    const reduced = window.matchMedia(QUERY_REDUCED);
    const fine = window.matchMedia(QUERY_FINE);
    const update = () => setPref(read());
    reduced.addEventListener('change', update);
    fine.addEventListener('change', update);
    window.addEventListener(MOTION_EVENT, update);
    return () => { reduced.removeEventListener('change', update); fine.removeEventListener('change', update); window.removeEventListener(MOTION_EVENT, update); };
  }, []);
  return pref;
}
