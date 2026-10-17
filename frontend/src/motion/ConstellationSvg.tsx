import { useMemo } from 'react';
import { buildConstellation, POINT_COUNT } from './constellationData';
import { MODES, type ModeKey } from './modeConfig';

// DECORATIVE: a still SVG version of the hero constellation, used when WebGL is unavailable,
// motion is reduced, or while the 3D scene loads. It shows no data, labels or career names.

export default function ConstellationSvg({ mode }: { mode: ModeKey }) {
  const { palette } = MODES[mode];
  const colors = [palette.a, palette.b, palette.c];
  const { dots, thread } = useMemo(() => {
    const d = buildConstellation();
    const project = (i: number) => ({ x: 50 + d.to[i * 3] * 5.2 + d.from[i * 3] * 0.55, y: 50 - d.to[i * 3 + 1] * 5.6 - d.from[i * 3 + 1] * 0.5 });
    const dotList = Array.from({ length: POINT_COUNT }, (_, i) => ({ ...project(i), c: d.cluster[i] % 3, r: 0.45 + (d.seeds[i] * 0.7) }));
    const path = d.path.map(project).map((p, n) => `${n === 0 ? 'M' : 'L'}${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
    return { dots: dotList, thread: path };
  }, []);

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="xMidYMid slice" className="h-full w-full" focusable="false">
      {dots.map((dot, i) => <circle key={i} cx={dot.x} cy={dot.y} r={dot.r} fill={colors[dot.c]} opacity={0.85} />)}
      <path d={thread} fill="none" stroke="#ffffff" strokeOpacity={0.75} strokeWidth={0.35} strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}
