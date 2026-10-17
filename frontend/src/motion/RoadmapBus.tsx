import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { usePrefersReducedMotion } from './usePrefersReducedMotion';

export type RoadmapStop = { id: string; label: string; detail?: string; badge?: string | null };
type Props = { stops: RoadmapStop[]; title?: string; caption?: string };
type Phase = 'halted' | 'travelling';

const W = 840;
const H = 200;
const PAD = 60;
const SAMPLES = 240;
const DWELL_MS = 2300;

type Route = { pts: { x: number; y: number }[]; cum: number[]; total: number; stopLens: number[]; stopPts: { x: number; y: number }[]; d: string };

/** Build a gently winding road and place stops evenly along it. Spacing is decorative, not a time estimate. */
function buildRoute(count: number): Route {
  const pts: { x: number; y: number }[] = [];
  for (let i = 0; i <= SAMPLES; i += 1) {
    const t = i / SAMPLES;
    pts.push({ x: PAD + t * (W - 2 * PAD), y: H / 2 + Math.sin(t * Math.PI * 3) * 32 });
  }
  const cum = [0];
  for (let i = 1; i < pts.length; i += 1) cum.push(cum[i - 1] + Math.hypot(pts[i].x - pts[i - 1].x, pts[i].y - pts[i - 1].y));
  const total = cum[cum.length - 1];
  const stopIdx = Array.from({ length: Math.max(count, 1) }, (_, i) => (count <= 1 ? Math.round(SAMPLES / 2) : Math.round((i / (count - 1)) * SAMPLES)));
  return {
    pts, cum, total,
    stopLens: stopIdx.map((i) => cum[i]),
    stopPts: stopIdx.map((i) => pts[i]),
    d: pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' '),
  };
}

function pointAt(route: Route, len: number) {
  const target = Math.max(0, Math.min(route.total, len));
  let lo = 0;
  let hi = route.cum.length - 1;
  while (lo < hi) { const mid = (lo + hi) >> 1; if (route.cum[mid] < target) lo = mid + 1; else hi = mid; }
  const i = Math.max(1, lo);
  const span = route.cum[i] - route.cum[i - 1] || 1;
  const f = (target - route.cum[i - 1]) / span;
  const a = route.pts[i - 1];
  const b = route.pts[i];
  return { x: a.x + (b.x - a.x) * f, y: a.y + (b.y - a.y) * f, angle: (Math.atan2(b.y - a.y, b.x - a.x) * 180) / Math.PI };
}
const ease = (p: number) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2);

export default function RoadmapBus({ stops, title = 'Your route', caption }: Props) {
  const reduced = usePrefersReducedMotion();
  const count = stops.length;
  const route = useMemo(() => buildRoute(count), [count]);
  const stopsKey = stops.map((s) => s.id).join('|');

  const anim = useRef({ phase: 'halted' as Phase, from: 0, to: 0, t0: 0, dur: 0, len: 0, current: 0, target: 0, haltedAt: 0 });
  const playingRef = useRef(false);
  const rafRef = useRef<number | null>(null);
  const [view, setView] = useState({ len: 0, phase: 'halted' as Phase, current: 0 });
  const [playing, setPlaying] = useState(false);

  const publish = () => setView({ len: anim.current.len, phase: anim.current.phase, current: anim.current.current });

  const stopLoop = useCallback(() => { if (rafRef.current !== null) { cancelAnimationFrame(rafRef.current); rafRef.current = null; } }, []);

  const startTravel = useCallback((index: number, now: number) => {
    const a = anim.current;
    const to = route.stopLens[index];
    a.from = a.len; a.to = to; a.target = index; a.t0 = now;
    a.dur = Math.min(2600, 700 + Math.abs(to - a.from) * 3.2);
    a.phase = 'travelling';
  }, [route]);

  const frame = useCallback((now: number) => {
    const a = anim.current;
    if (a.phase === 'travelling') {
      const p = Math.min(1, (now - a.t0) / a.dur);
      a.len = a.from + (a.to - a.from) * ease(p);
      if (p >= 1) { a.phase = 'halted'; a.current = a.target; a.len = a.to; a.haltedAt = now; }
    } else if (playingRef.current && now - a.haltedAt >= DWELL_MS) {
      if (a.current < count - 1) startTravel(a.current + 1, now);
      else { playingRef.current = false; setPlaying(false); }
    }
    publish();
    rafRef.current = a.phase === 'travelling' || playingRef.current ? requestAnimationFrame(frame) : null;
  }, [count, startTravel]);

  const kick = useCallback(() => { if (rafRef.current === null) rafRef.current = requestAnimationFrame(frame); }, [frame]);

  // Reset whenever the plan's step list changes.
  useEffect(() => {
    stopLoop(); playingRef.current = false; setPlaying(false);
    anim.current = { phase: 'halted', from: 0, to: 0, t0: 0, dur: 0, len: route.stopLens[0] ?? 0, current: 0, target: 0, haltedAt: 0 };
    publish();
    return stopLoop;
  }, [stopsKey, route, stopLoop]);

  useEffect(() => { if (reduced && playingRef.current) { playingRef.current = false; setPlaying(false); } }, [reduced]);

  const goTo = (index: number) => {
    const next = Math.max(0, Math.min(count - 1, index));
    playingRef.current = false; setPlaying(false);
    const a = anim.current;
    if (reduced) { a.phase = 'halted'; a.current = next; a.target = next; a.len = route.stopLens[next]; publish(); return; }
    startTravel(next, performance.now()); kick();
  };
  const play = () => {
    if (reduced || count < 2) return;
    const a = anim.current;
    if (a.phase === 'halted' && a.current >= count - 1) { a.len = route.stopLens[0]; a.current = 0; a.target = 0; }
    a.haltedAt = performance.now();
    playingRef.current = true; setPlaying(true); kick();
  };
  const pause = () => { playingRef.current = false; setPlaying(false); };

  if (count === 0) return null;
  const bus = pointAt(route, view.len);
  const active = stops[view.current];
  const halted = view.phase === 'halted';
  const atEnd = view.current >= count - 1 && halted;

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 className="text-lg font-semibold text-ink">{title}</h3>
          <p className="mt-1 text-xs leading-5 text-slate-500">{caption ?? 'Each stop is a step from your saved plan, in order. Distances are decorative, not time estimates.'}</p>
        </div>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Roadmap controls">
          {!reduced && count > 1 ? (
            <button type="button" onClick={playing ? pause : play} className="rounded-lg bg-teal-700 px-3 py-2 text-xs font-semibold text-white transition hover:bg-teal-800 focus:outline-none focus:ring-2 focus:ring-teal-500">
              {playing ? 'Pause ride' : atEnd ? 'Replay ride' : 'Ride the route'}
            </button>
          ) : null}
          <button type="button" onClick={() => goTo(view.current - 1)} disabled={view.current === 0} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-40">Previous stop</button>
          <button type="button" onClick={() => goTo(view.current + 1)} disabled={atEnd} className="rounded-lg border border-slate-200 px-3 py-2 text-xs font-semibold text-slate-700 transition hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-teal-500 disabled:opacity-40">Next stop</button>
        </div>
      </div>

      <div className="mt-4 overflow-x-auto rounded-xl bg-gradient-to-b from-sky-50 to-teal-50/60">
        <svg viewBox={`0 0 ${W} ${H}`} className="block h-auto w-full min-w-[520px]" role="img" aria-label={`Roadmap with ${count} stop${count === 1 ? '' : 's'}. Currently at stop ${view.current + 1}: ${active.label}.`}>
          {/* road */}
          <path d={route.d} fill="none" stroke="#cbd5e1" strokeWidth="22" strokeLinecap="round" strokeLinejoin="round" />
          <path d={route.d} fill="none" stroke="#14b8a6" strokeOpacity="0.55" strokeWidth="22" strokeLinecap="round" strokeLinejoin="round" strokeDasharray={`${view.len} ${route.total + 40}`} />
          <path d={route.d} fill="none" stroke="#fff" strokeWidth="2" strokeDasharray="10 12" strokeLinecap="round" />

          {/* stops */}
          {route.stopPts.slice(0, count).map((pt, i) => {
            const isActive = i === view.current;
            return (
              <g key={stops[i].id} transform={`translate(${pt.x} ${pt.y})`} className="cursor-pointer" onClick={() => goTo(i)}>
                <line x1="0" y1="-14" x2="0" y2="-40" stroke="#475569" strokeWidth="2" />
                <rect x="-11" y="-52" width="22" height="14" rx="3" fill={isActive ? '#117369' : '#fff'} stroke="#117369" strokeWidth="1.5" />
                <text x="0" y="-41.5" textAnchor="middle" fontSize="10" fontWeight="700" fill={isActive ? '#fff' : '#117369'}>{i + 1}</text>
                {isActive && halted ? <circle r="16" fill="none" stroke="#117369" strokeWidth="2" className="stop-pulse" /> : null}
                <circle r="9" fill={i <= view.current ? '#117369' : '#fff'} stroke="#117369" strokeWidth="2.5" />
              </g>
            );
          })}

          {/* bus */}
          <g transform={`translate(${bus.x} ${bus.y}) rotate(${Math.max(-12, Math.min(12, bus.angle * 0.5))})`} className={halted ? 'bus bus-halted' : 'bus bus-moving'}>
            <g transform="translate(-30 -34)">
              <ellipse cx="30" cy="36" rx="30" ry="4" fill="#0f172a" opacity="0.12" />
              <rect x="0" y="4" width="60" height="26" rx="7" fill="#178C81" />
              <rect x="0" y="22" width="60" height="4" fill="#117369" />
              {[6, 20, 34].map((x) => <rect key={x} x={x} y="9" width="10" height="9" rx="2" fill="#e0f2fe" />)}
              <rect x="49" y="8" width="8" height="12" rx="2" fill="#bae6fd" />
              <rect x="45" y="12" width="1.5" height="17" fill="#0f766e" className="bus-door" />
              <circle cx="57" cy="24" r="2" fill="#fde68a" />
              <g className="bus-wheel" style={{ transformOrigin: '14px 30px' }}><circle cx="14" cy="30" r="5.5" fill="#1e293b" /><path d="M14 25v10M9 30h10" stroke="#94a3b8" strokeWidth="1.2" /></g>
              <g className="bus-wheel" style={{ transformOrigin: '44px 30px' }}><circle cx="44" cy="30" r="5.5" fill="#1e293b" /><path d="M44 25v10M39 30h10" stroke="#94a3b8" strokeWidth="1.2" /></g>
            </g>
            {halted ? <g className="passengers" aria-hidden="true"><circle cx="-4" cy="2" r="2.6" fill="#f59e0b" className="passenger p1" /><circle cx="3" cy="2" r="2.6" fill="#6366f1" className="passenger p2" /></g> : null}
          </g>
        </svg>
      </div>

      <div className="mt-4 rounded-xl bg-slate-50 p-4" aria-live="polite">
        <div className="flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-teal-700 px-2.5 py-1 text-[11px] font-bold text-white">Stop {view.current + 1} of {count}</span>
          {active.badge ? <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-800">{active.badge}</span> : null}
          <span className="text-[11px] text-slate-500">{halted ? 'Halted' : 'On the way…'}</span>
        </div>
        <p className="mt-2 text-sm font-semibold text-slate-800">{active.label}</p>
        {active.detail ? <p className="mt-1 text-xs leading-5 text-slate-600">{active.detail}</p> : null}
      </div>

      <ol className="mt-3 flex flex-wrap gap-2" aria-label="All stops">
        {stops.map((stop, i) => (
          <li key={stop.id}>
            <button type="button" onClick={() => goTo(i)} aria-current={i === view.current ? 'step' : undefined} className={`max-w-[15rem] truncate rounded-full border px-3 py-1.5 text-xs font-semibold transition focus:outline-none focus:ring-2 focus:ring-teal-500 ${i === view.current ? 'border-teal-700 bg-teal-700 text-white' : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'}`} title={stop.label}>
              {i + 1}. {stop.label}
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}
