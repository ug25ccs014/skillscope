import { useMotionPreference } from './useMotionPreference';

/** Decorative shield with a slow breathing halo and three orbiting dots. Meaning is carried by nearby text only. */
export default function PrivacyShield({ className = 'h-40 w-40' }: { className?: string }) {
  const { reducedMotion } = useMotionPreference();
  return (
    <svg viewBox="0 0 160 160" aria-hidden="true" className={className} fill="none">
      <defs>
        <linearGradient id="shield-fill" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#4FD1C5" /><stop offset="1" stopColor="#6366F1" /></linearGradient>
      </defs>
      {!reducedMotion && <circle cx="80" cy="80" r="62" stroke="#4FD1C5" strokeWidth="2" className="shield-halo" />}
      <g className={reducedMotion ? '' : 'orbit'} style={{ transformOrigin: '80px 80px' }}>
        {[0, 120, 240].map((deg) => <circle key={deg} cx="80" cy="14" r="4.5" fill="#6366F1" transform={`rotate(${deg} 80 80)`} />)}
      </g>
      <path d="M80 30 46 43v31c0 25 14 42 34 52 20-10 34-27 34-52V43L80 30Z" fill="url(#shield-fill)" opacity=".95" />
      <rect x="66" y="74" width="28" height="22" rx="5" fill="#fff" />
      <path d="M71 74v-6a9 9 0 0 1 18 0v6" stroke="#fff" strokeWidth="5" strokeLinecap="round" />
      <circle cx="80" cy="85" r="3" fill="#12243A" />
    </svg>
  );
}
