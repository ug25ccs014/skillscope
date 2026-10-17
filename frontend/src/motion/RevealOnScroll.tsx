import { useEffect, useRef, useState, type ReactNode } from 'react';
import { usePrefersReducedMotion } from './usePrefersReducedMotion';

/**
 * Fades/slides content in as it enters the viewport. Fail-safe by design: content is always in the DOM,
 * anything already on screen is shown straight away, and a short timer reveals the rest even if the
 * observer never fires, so a section can never stay blank.
 */
export default function RevealOnScroll({ children }: { children: ReactNode }) {
  const ref = useRef<HTMLDivElement | null>(null);
  const reduced = usePrefersReducedMotion();
  const [shown, setShown] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (reduced || !node || typeof IntersectionObserver === 'undefined') { setShown(true); return; }
    const rect = node.getBoundingClientRect();
    if (rect.top < window.innerHeight) { setShown(true); return; }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) { setShown(true); observer.disconnect(); }
    }, { threshold: 0, rootMargin: '0px 0px 120px 0px' });
    observer.observe(node);
    const failSafe = window.setTimeout(() => setShown(true), 2500);
    return () => { observer.disconnect(); window.clearTimeout(failSafe); };
  }, [reduced]);

  return <div ref={ref} className={`reveal ${shown ? 'reveal-in' : ''}`}>{children}</div>;
}
