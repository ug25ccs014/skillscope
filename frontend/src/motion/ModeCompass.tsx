import { useEffect, useState } from 'react';

type Mode = 'discover_and_shape' | 'explore_and_validate' | 'develop_and_optimize';
const ANGLE: Record<Mode, number> = { discover_and_shape: -58, explore_and_validate: 0, develop_and_optimize: 58 };
const NAMES: Record<Mode, string> = { discover_and_shape: 'Discover', explore_and_validate: 'Explore', develop_and_optimize: 'Develop' };

/** A needle that swings to the *starting* mode. Modes are reversible starting points, not a verdict. */
export default function ModeCompass({ mode }: { mode: Mode }) {
  const [angle, setAngle] = useState(0);
  useEffect(() => {
    setAngle(0);
    const id = window.setTimeout(() => setAngle(ANGLE[mode]), 120);
    return () => window.clearTimeout(id);
  }, [mode]);
  return (
    <svg viewBox="0 0 200 120" className="h-24 w-40 shrink-0" role="img" aria-label={`Starting mode: ${NAMES[mode]}. You can change this at any time.`}>
      <path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="#cbd5e1" strokeWidth="10" strokeLinecap="round" />
      {(Object.keys(ANGLE) as Mode[]).map((m) => {
        const rad = ((ANGLE[m] - 90) * Math.PI) / 180;
        return <g key={m}><circle cx={100 + 80 * Math.cos(rad)} cy={100 + 80 * Math.sin(rad)} r={m === mode ? 7 : 5} fill={m === mode ? '#117369' : '#94a3b8'} /></g>;
      })}
      <g className="compass-needle" style={{ transform: `rotate(${angle}deg)`, transformOrigin: '100px 100px' }}>
        <path d="M100 100 L100 36" stroke="#12243A" strokeWidth="4" strokeLinecap="round" />
        <path d="M94 44 L100 30 L106 44 Z" fill="#12243A" />
      </g>
      <circle cx="100" cy="100" r="8" fill="#12243A" />
      <text x="20" y="116" fontSize="10" fill="#64748b" textAnchor="middle">Discover</text>
      <text x="100" y="22" fontSize="10" fill="#64748b" textAnchor="middle">Explore</text>
      <text x="180" y="116" fontSize="10" fill="#64748b" textAnchor="middle">Develop</text>
    </svg>
  );
}
