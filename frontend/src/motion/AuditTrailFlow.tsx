import { useMotionPreference } from './useMotionPreference';

const nodes = [
  { x: 70, label: 'Your evidence', sub: 'what you did and said', tone: '#117369', tint: '#EFFAF8' },
  { x: 280, label: 'Matching rules', sub: 'local inference', tone: '#4F46E5', tint: '#EEF2FF' },
  { x: 490, label: 'Cited sources', sub: 'external facts', tone: '#B45309', tint: '#FFFBEB' },
];

/**
 * Decorative explainer for the audit trail: student evidence flows into local matching rules, which are
 * set beside (not mixed with) externally sourced facts. It carries no data, only the shape of the logic.
 * Under reduced motion the flowing dashes and pulses stop and the diagram stays fully readable.
 */
export default function AuditTrailFlow({ className = '' }: { className?: string }) {
  const { reducedMotion } = useMotionPreference();
  return (
    <figure className={className}>
      <svg viewBox="0 0 560 150" role="img" aria-label="Diagram: your evidence feeds local matching rules, which are shown beside cited external sources. Local inference and sourced facts are kept separate." className="h-auto w-full">
        <path d="M118 62 H232" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" className={reducedMotion ? '' : 'dash-flow'} fill="none" />
        <path d="M328 62 H442" stroke="#94a3b8" strokeWidth="3" strokeLinecap="round" strokeDasharray="2 8" fill="none" />
        <text x="385" y="50" textAnchor="middle" fontSize="10" fontWeight="700" fill="#64748b">kept separate</text>
        {nodes.map((n, i) => (
          <g key={n.label}>
            {!reducedMotion && <circle cx={n.x} cy="62" r="34" fill="none" stroke={n.tone} strokeWidth="2" className="node-ring" style={{ animationDelay: `${i * 500}ms` }} />}
            <circle cx={n.x} cy="62" r="30" fill={n.tint} stroke={n.tone} strokeWidth="2.5" />
            <text x={n.x} y="68" textAnchor="middle" fontSize="18" fontWeight="800" fill={n.tone}>{i + 1}</text>
            <text x={n.x} y="118" textAnchor="middle" fontSize="13" fontWeight="700" fill="#12243A">{n.label}</text>
            <text x={n.x} y="135" textAnchor="middle" fontSize="11" fill="#475569">{n.sub}</text>
          </g>
        ))}
      </svg>
    </figure>
  );
}
