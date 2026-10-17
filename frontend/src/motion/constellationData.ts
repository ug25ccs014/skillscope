// DECORATIVE: procedural points for the hero. They carry no labels, numbers or career names and represent no data.

export const POINT_COUNT = 130;
export const CLUSTER_COUNT = 4;

/** Small deterministic PRNG so the scene is identical on every render (no flicker under StrictMode). */
function mulberry32(seed: number) {
  let t = seed >>> 0;
  return () => {
    t += 0x6d2b79f5;
    let r = Math.imul(t ^ (t >>> 15), 1 | t);
    r ^= r + Math.imul(r ^ (r >>> 7), 61 | r);
    return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
  };
}

const CENTERS: Array<[number, number, number]> = [
  [-5.5, 2.6, -5],
  [5.2, 3.2, -9],
  [-2.8, -3.2, -12],
  [6.4, -2.4, -3],
];

/** Order in which the thread visits the clusters. */
const PATH_ORDER = [0, 2, 3, 1];

export type Constellation = {
  from: Float32Array;
  to: Float32Array;
  cluster: Uint8Array;
  seeds: Float32Array;
  path: number[];
};

export function buildConstellation(): Constellation {
  const rand = mulberry32(20261017);
  const from = new Float32Array(POINT_COUNT * 3);
  const to = new Float32Array(POINT_COUNT * 3);
  const cluster = new Uint8Array(POINT_COUNT);
  const seeds = new Float32Array(POINT_COUNT);
  const members: number[][] = Array.from({ length: CLUSTER_COUNT }, () => []);

  for (let i = 0; i < POINT_COUNT; i += 1) {
    const c = i % CLUSTER_COUNT;
    cluster[i] = c;
    members[c].push(i);
    seeds[i] = rand();
    from[i * 3] = (rand() - 0.5) * 32;
    from[i * 3 + 1] = (rand() - 0.5) * 17;
    from[i * 3 + 2] = 4 - rand() * 40;
    const [cx, cy, cz] = CENTERS[c];
    to[i * 3] = cx + (rand() - 0.5) * 3.4;
    to[i * 3 + 1] = cy + (rand() - 0.5) * 3.0;
    to[i * 3 + 2] = cz + (rand() - 0.5) * 3.4;
  }

  const path: number[] = [];
  PATH_ORDER.forEach((c) => {
    path.push(members[c][0], members[c][1]);
  });
  return { from, to, cluster, seeds, path };
}
