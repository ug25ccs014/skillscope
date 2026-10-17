import { useEffect, useState } from 'react';

type Level = 'low' | 'moderate' | 'high';
const STEPS: Record<Level, number> = { low: 1, moderate: 2, high: 3 };

/**
 * Three-step indicator of *evidence strength* (volume, recency, consistency, source quality, coverage).
 * It is deliberately not a percentage and is not a probability of success or fit.
 */
export default function ConfidenceGauge({ level, label }: { level: Level; label: string }) {
  const [filled, setFilled] = useState(0);
  useEffect(() => {
    const id = window.setTimeout(() => setFilled(STEPS[level]), 60);
    return () => window.clearTimeout(id);
  }, [level]);
  return (
    <span className="inline-flex items-center gap-2" role="img" aria-label={`Evidence strength: ${label} (step ${STEPS[level]} of 3). This is not a chance of success.`}>
      <span className="flex gap-1" aria-hidden="true">
        {[1, 2, 3].map((step) => (
          <span key={step} className="gauge-seg h-2 w-6 rounded-full bg-slate-200">
            <span className={`gauge-fill block h-full rounded-full bg-teal-500 ${filled >= step ? 'gauge-fill-on' : ''}`} style={{ transitionDelay: `${(step - 1) * 140}ms` }} />
          </span>
        ))}
      </span>
      <span className="text-xs text-slate-500">{label}</span>
    </span>
  );
}
