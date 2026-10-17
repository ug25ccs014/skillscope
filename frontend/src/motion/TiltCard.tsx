import { useRef, type PointerEvent as ReactPointerEvent, type ReactNode } from 'react';
import { useMotionPreference } from './useMotionPreference';

/**
 * A card that tilts toward a mouse pointer with a soft shine (CSS perspective and transforms only, no WebGL).
 * Touch and pen input get no tilt, only the CSS press animation. Reduced motion disables tilt entirely.
 */
export default function TiltCard({ children, className = '', maxTilt = 7 }: { children: ReactNode; className?: string; maxTilt?: number }) {
  const cardRef = useRef<HTMLDivElement | null>(null);
  const frame = useRef(0);
  const { reducedMotion, finePointer } = useMotionPreference();
  const enabled = finePointer && !reducedMotion;

  const onMove = (event: ReactPointerEvent<HTMLDivElement>) => {
    if (!enabled || event.pointerType !== 'mouse') return;
    const node = cardRef.current;
    if (!node) return;
    const { clientX, clientY } = event;
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      const rect = node.getBoundingClientRect();
      const x = (clientX - rect.left) / rect.width;
      const y = (clientY - rect.top) / rect.height;
      node.style.setProperty('--ry', `${((x - 0.5) * 2 * maxTilt).toFixed(2)}deg`);
      node.style.setProperty('--rx', `${((0.5 - y) * 2 * maxTilt).toFixed(2)}deg`);
      node.style.setProperty('--mx', `${(x * 100).toFixed(1)}%`);
      node.style.setProperty('--my', `${(y * 100).toFixed(1)}%`);
    });
  };
  const onLeave = () => {
    cancelAnimationFrame(frame.current);
    const node = cardRef.current;
    if (!node) return;
    node.style.setProperty('--rx', '0deg'); node.style.setProperty('--ry', '0deg');
  };

  return (
    <div className="tilt-scene" onPointerMove={onMove} onPointerLeave={onLeave}>
      <div ref={cardRef} className={`tilt-card ${className}`}>
        {children}
        {enabled ? <span aria-hidden="true" className="tilt-shine" /> : null}
      </div>
    </div>
  );
}
