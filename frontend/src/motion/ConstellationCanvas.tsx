import { useEffect, useMemo, useRef, type RefObject } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';
import { buildConstellation, POINT_COUNT } from './constellationData';
import { MODES, type ModeKey } from './modeConfig';
import type { CanvasControlProps } from './LazyCanvas';

// DECORATIVE: a procedural constellation. It shows no data, labels, numbers or career names.

type SceneProps = { progressRef: RefObject<number>; mode: ModeKey; parallax: boolean };

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const smooth = (v: number) => { const x = clamp01(v); return x * x * (3 - 2 * x); };

function makeDotTexture(): THREE.Texture {
  const size = 64;
  const canvas = document.createElement('canvas');
  canvas.width = size; canvas.height = size;
  const ctx = canvas.getContext('2d');
  if (ctx) {
    const g = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
    g.addColorStop(0, 'rgba(255,255,255,1)');
    g.addColorStop(0.35, 'rgba(255,255,255,0.85)');
    g.addColorStop(1, 'rgba(255,255,255,0)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, size, size);
  }
  return new THREE.CanvasTexture(canvas);
}

function Constellation({ progressRef, mode, parallax }: SceneProps) {
  const data = useMemo(() => buildConstellation(), []);

  const objects = useMemo(() => {
    const positions = new Float32Array(POINT_COUNT * 3);
    positions.set(data.from);
    const colors = new Float32Array(POINT_COUNT * 3);
    const pointGeometry = new THREE.BufferGeometry();
    pointGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    pointGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    const texture = makeDotTexture();
    const pointMaterial = new THREE.PointsMaterial({ size: 0.34, sizeAttenuation: true, vertexColors: true, map: texture, transparent: true, opacity: 0.95, depthWrite: false });
    const points = new THREE.Points(pointGeometry, pointMaterial);
    points.frustumCulled = false;

    const linePositions = new Float32Array(data.path.length * 3);
    const lineGeometry = new THREE.BufferGeometry();
    lineGeometry.setAttribute('position', new THREE.BufferAttribute(linePositions, 3));
    lineGeometry.setDrawRange(0, 0);
    const lineMaterial = new THREE.LineBasicMaterial({ color: '#ffffff', transparent: true, opacity: 0.9 });
    const line = new THREE.Line(lineGeometry, lineMaterial);
    line.frustumCulled = false;

    return { positions, colors, pointGeometry, pointMaterial, points, linePositions, lineGeometry, lineMaterial, line, texture };
  }, [data]);

  useEffect(() => () => {
    objects.pointGeometry.dispose(); objects.pointMaterial.dispose(); objects.texture.dispose();
    objects.lineGeometry.dispose(); objects.lineMaterial.dispose();
  }, [objects]);

  const state = useRef({ smoothed: 0, colorsReady: false });
  const target = useMemo(() => ({ a: new THREE.Color(), b: new THREE.Color(), c: new THREE.Color(), cur: [new THREE.Color(), new THREE.Color(), new THREE.Color()] }), []);

  useFrame(({ clock, camera, pointer }) => {
    const info = MODES[mode];
    const t = clock.getElapsedTime();
    const s = state.current;

    s.smoothed += (progressRef.current - s.smoothed) * info.damping;
    const p = s.smoothed;
    const settle = smooth((p - 0.08) / 0.6);

    target.a.set(info.palette.a); target.b.set(info.palette.b); target.c.set(info.palette.c);
    const palette = [target.a, target.b, target.c];
    let changed = !s.colorsReady;
    for (let k = 0; k < 3; k += 1) {
      if (!s.colorsReady) target.cur[k].copy(palette[k]);
      else { target.cur[k].lerp(palette[k], 0.05); changed = true; }
    }
    s.colorsReady = true;

    const { positions, colors } = objects;
    const amp = 0.35 * (1 - settle * 0.6);
    for (let i = 0; i < POINT_COUNT; i += 1) {
      const seed = data.seeds[i] * 6.2831;
      const k = i * 3;
      positions[k] = data.from[k] + (data.to[k] - data.from[k]) * settle + Math.sin(t * info.drift + seed) * amp;
      positions[k + 1] = data.from[k + 1] + (data.to[k + 1] - data.from[k + 1]) * settle + Math.cos(t * info.drift * 0.8 + seed) * amp;
      positions[k + 2] = data.from[k + 2] + (data.to[k + 2] - data.from[k + 2]) * settle;
      if (changed) {
        const col = target.cur[data.cluster[i] % 3];
        colors[k] = col.r; colors[k + 1] = col.g; colors[k + 2] = col.b;
      }
    }
    objects.pointGeometry.attributes.position.needsUpdate = true;
    if (changed) objects.pointGeometry.attributes.color.needsUpdate = true;

    const lp = objects.linePositions;
    data.path.forEach((index, n) => {
      lp[n * 3] = positions[index * 3]; lp[n * 3 + 1] = positions[index * 3 + 1]; lp[n * 3 + 2] = positions[index * 3 + 2];
    });
    objects.lineGeometry.attributes.position.needsUpdate = true;
    const drawn = Math.floor(smooth((p - 0.55) / 0.4) * data.path.length);
    objects.lineGeometry.setDrawRange(0, drawn >= 2 ? drawn : 0);
    objects.lineMaterial.color.copy(target.cur[0]).lerp(new THREE.Color('#ffffff'), 0.55);

    const px = parallax && !info.calm ? pointer.x * 0.9 : 0;
    const py = parallax && !info.calm ? pointer.y * 0.55 : 0;
    camera.position.x += (px - camera.position.x) * 0.05;
    camera.position.y += (py - camera.position.y) * 0.05;
    camera.position.z = 14 - p * 15;
    camera.lookAt(0, 0, camera.position.z - 20);
  });

  return (
    <>
      <primitive object={objects.points} />
      <primitive object={objects.line} />
    </>
  );
}

export default function ConstellationCanvas({ paused, onContextLost, onReady, progressRef, mode, parallax }: CanvasControlProps & SceneProps) {
  return (
    <Canvas
      className="!absolute inset-0"
      dpr={[1, 1.75]}
      frameloop={paused ? 'never' : 'always'}
      camera={{ position: [0, 0, 14], fov: 55, near: 0.1, far: 90 }}
      gl={{ antialias: false, alpha: true, powerPreference: 'low-power' }}
      onCreated={({ gl }) => {
        gl.domElement.addEventListener('webglcontextlost', (event) => { event.preventDefault(); onContextLost(); });
        onReady();
      }}
    >
      <Constellation progressRef={progressRef} mode={mode} parallax={parallax} />
    </Canvas>
  );
}
