import { useMotionPreference } from './useMotionPreference';

type Tone = 'ok' | 'warn' | 'idle';
const tones: Record<Tone, { dot: string; ring: string; text: string }> = {
  ok: { dot: 'bg-emerald-500', ring: 'bg-emerald-400', text: 'text-emerald-800' },
  warn: { dot: 'bg-amber-500', ring: 'bg-amber-400', text: 'text-amber-900' },
  idle: { dot: 'bg-slate-400', ring: 'bg-slate-300', text: 'text-slate-700' },
};

/** Small status dot that pulses while a store is healthy. The word next to it always states the status. */
export default function SyncPulse({ tone, label }: { tone: Tone; label: string }) {
  const { reducedMotion } = useMotionPreference();
  const t = tones[tone];
  return (
    <span className={`inline-flex items-center gap-2 text-xs font-semibold ${t.text}`}>
      <span className="relative flex h-2.5 w-2.5" aria-hidden="true">
        {tone === 'ok' && !reducedMotion ? <span className={`absolute inline-flex h-full w-full rounded-full opacity-60 ${t.ring} sync-ping`} /> : null}
        <span className={`relative inline-flex h-2.5 w-2.5 rounded-full ${t.dot}`} />
      </span>
      {label}
    </span>
  );
}
