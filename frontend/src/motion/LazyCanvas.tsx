import { Component, Suspense, useEffect, useRef, useState, type ComponentType, type LazyExoticComponent, type ReactNode } from 'react';

/** Props every lazy 3D scene receives from LazyCanvas. */
export type CanvasControlProps = {
  /** True while the canvas is off-screen or the tab is hidden: the scene must stop rendering. */
  paused: boolean;
  /** Call when the WebGL context is lost so LazyCanvas can show the static fallback. */
  onContextLost: () => void;
  /** Call once the canvas has created its context so the fallback can be hidden. */
  onReady: () => void;
};

class CanvasBoundary extends Component<{ fallback: ReactNode; onError: () => void; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  componentDidCatch() { this.props.onError(); }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

type Props = {
  /** A React.lazy component, so three.js / R3F stay out of the main bundle. */
  scene: LazyExoticComponent<ComponentType<any>>;
  sceneProps?: Record<string, unknown>;
  /** When false (reduced motion, no WebGL, low power, Data Saver) only the fallback renders. */
  enabled: boolean;
  /** Static replacement: always rendered while loading, on failure, on context loss or when disabled. */
  fallback: ReactNode;
  className?: string;
};

/**
 * Lazy-loaded WebGL slot with: IntersectionObserver + tab-visibility pausing, an error boundary,
 * a context-loss handler and a static fallback. The canvas is decorative and hidden from assistive technology.
 */
export default function LazyCanvas({ scene: Scene, sceneProps, enabled, fallback, className }: Props) {
  const hostRef = useRef<HTMLDivElement | null>(null);
  const [visible, setVisible] = useState(false);
  const [wasVisible, setWasVisible] = useState(false);
  const [tabHidden, setTabHidden] = useState(() => typeof document !== 'undefined' && document.hidden);
  const [failed, setFailed] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const node = hostRef.current;
    if (!node || typeof IntersectionObserver === 'undefined') { setVisible(true); setWasVisible(true); return; }
    const observer = new IntersectionObserver((entries) => {
      const on = entries.some((entry) => entry.isIntersecting);
      setVisible(on);
      if (on) setWasVisible(true);
    }, { threshold: 0.01 });
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    const onChange = () => setTabHidden(document.hidden);
    document.addEventListener('visibilitychange', onChange);
    return () => document.removeEventListener('visibilitychange', onChange);
  }, []);

  const showScene = enabled && !failed && wasVisible;
  const paused = !visible || tabHidden;

  return (
    <div ref={hostRef} className={className} aria-hidden="true">
      {!showScene || !ready ? <div className="absolute inset-0">{fallback}</div> : null}
      {showScene ? (
        <CanvasBoundary fallback={null} onError={() => setFailed(true)}>
          <Suspense fallback={null}>
            <Scene {...sceneProps} paused={paused} onContextLost={() => setFailed(true)} onReady={() => setReady(true)} />
          </Suspense>
        </CanvasBoundary>
      ) : null}
    </div>
  );
}
