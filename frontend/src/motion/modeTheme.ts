/** The three starting modes and their visual themes. Colours here must match the CSS variables in index.css. */
export type ModeKey = 'discover' | 'explore' | 'develop';

export type Palette = { a: string; b: string; c: string };

export type ModeInfo = {
  key: ModeKey;
  ages: string;
  title: string;
  feel: string;
  palette: Palette;
  /** 10–14 gets the gentlest motion: slow drift, no pointer parallax, heavy smoothing. */
  calm: boolean;
  /** Per-frame smoothing for the scroll-driven scene (lower = softer). */
  damping: number;
  /** Drift speed multiplier for the ambient constellation motion. */
  drift: number;
};

export const MODE_ORDER: ModeKey[] = ['discover', 'explore', 'develop'];

export const MODES: Record<ModeKey, ModeInfo> = {
  discover: { key: 'discover', ages: '10–14', title: 'Discover & Shape', feel: 'Slow, soft and rounded', palette: { a: '#FFB36B', b: '#FF8E7A', c: '#7FDCCF' }, calm: true, damping: 0.03, drift: 0.35 },
  explore: { key: 'explore', ages: '15–17', title: 'Explore & Validate', feel: 'Medium energy', palette: { a: '#4FD1C5', b: '#5BC0EB', c: '#9AA5FF' }, calm: false, damping: 0.06, drift: 0.6 },
  develop: { key: 'develop', ages: '18+', title: 'Develop & Optimize', feel: 'Crisp and precise', palette: { a: '#7C8CFF', b: '#2DD4BF', c: '#A5B4FC' }, calm: false, damping: 0.12, drift: 0.85 },
};

export function modeFromAge(age: number): ModeKey {
  if (!Number.isFinite(age)) return 'explore';
  if (age <= 14) return 'discover';
  if (age <= 17) return 'explore';
  return 'develop';
}

/** Maps the API's age_mode value to a theme key. Returns null for anything unknown. */
export function modeFromApi(value: string): ModeKey | null {
  if (value === 'discover_and_shape') return 'discover';
  if (value === 'explore_and_validate') return 'explore';
  if (value === 'develop_and_optimize') return 'develop';
  return null;
}
