import { useEffect, type ReactNode } from 'react';
import Lenis from 'lenis';
import { gsap, ScrollTrigger } from './gsapSetup';
import { useMotionPreference } from './useMotionPreference';

/**
 * Lenis smooth scrolling driven by the GSAP ticker, so ScrollTrigger and Lenis share one clock.
 * Disabled entirely for reduced motion, low-power devices and Data Saver: native scrolling is used instead.
 */
export default function SmoothScrollProvider({ children }: { children: ReactNode }) {
  const { allowSmoothScroll } = useMotionPreference();

  useEffect(() => {
    if (!allowSmoothScroll) return;
    const lenis = new Lenis({ autoRaf: false, lerp: 0.1, smoothWheel: true });
    const onScroll = () => ScrollTrigger.update();
    lenis.on('scroll', onScroll);
    const tick = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(tick);
    gsap.ticker.lagSmoothing(0);
    return () => {
      gsap.ticker.remove(tick);
      lenis.off('scroll', onScroll);
      lenis.destroy();
    };
  }, [allowSmoothScroll]);

  return <>{children}</>;
}
