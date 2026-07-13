import { useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";

// The homepage's only "illustration" -- an abstract particle field forming
// a sphere, standing in for the idea of a live, searchable talent graph
// rather than any literal depiction of people/resumes/screens (the brief
// explicitly rules out stock illustrations). It reacts to three real
// application phases:
//
//   "idle"     -- slow ambient rotation, particles at rest radius.
//   "searching"-- particles pulse outward/inward and rotate faster,
//                 reading as "actively working" without a literal spinner.
//   "results"  -- settles into a calmer, slightly tighter formation, as if
//                 the search has resolved into something concrete.
//
// No text, no logos, no people -- purely geometric, same restraint as
// Linear/Vercel's own marketing sites use for their 3D/gradient work.

const PARTICLE_COUNT = 2200;

function ParticleField({ phase }) {
  const pointsRef = useRef(null);
  const materialRef = useRef(null);

  const { positions, baseRadii } = useMemo(() => {
    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const baseRadii = new Float32Array(PARTICLE_COUNT);
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      // Fibonacci sphere distribution -- even coverage, no clumping at poles.
      const t = i / PARTICLE_COUNT;
      const inclination = Math.acos(1 - 2 * t);
      const azimuth = Math.PI * (1 + Math.sqrt(5)) * i;
      const radius = 2.15 + (Math.random() - 0.5) * 0.18;
      const x = radius * Math.sin(inclination) * Math.cos(azimuth);
      const y = radius * Math.sin(inclination) * Math.sin(azimuth);
      const z = radius * Math.cos(inclination);
      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;
      baseRadii[i] = radius;
    }
    return { positions, baseRadii };
  }, []);

  const targetSpeed = useRef(0.06);
  const currentSpeed = useRef(0.06);
  const pulse = useRef(0);

  useFrame((state, delta) => {
    targetSpeed.current = phase === "searching" ? 0.34 : phase === "results" ? 0.045 : 0.08;
    currentSpeed.current += (targetSpeed.current - currentSpeed.current) * Math.min(1, delta * 2);

    if (pointsRef.current) {
      pointsRef.current.rotation.y += currentSpeed.current * delta;
      pointsRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.08) * 0.15;
    }

    if (phase === "searching") {
      pulse.current += delta * 2.4;
    } else {
      pulse.current += delta * 0.4;
    }

    if (materialRef.current) {
      const targetOpacity = phase === "searching" ? 0.95 : phase === "results" ? 0.55 : 0.75;
      materialRef.current.opacity += (targetOpacity - materialRef.current.opacity) * Math.min(1, delta * 3);
      const targetSize = phase === "searching" ? 0.028 : 0.022;
      materialRef.current.size += (targetSize - materialRef.current.size) * Math.min(1, delta * 3);
    }

    if (pointsRef.current) {
      const posAttr = pointsRef.current.geometry.attributes.position;
      const amp = phase === "searching" ? 0.09 : 0.03;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        const r = baseRadii[i];
        const wobble = 1 + Math.sin(pulse.current + i * 0.37) * amp * 0.05;
        const scale = wobble;
        posAttr.array[i * 3] = positions[i * 3] * scale;
        posAttr.array[i * 3 + 1] = positions[i * 3 + 1] * scale;
        posAttr.array[i * 3 + 2] = positions[i * 3 + 2] * scale;
      }
      posAttr.needsUpdate = true;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <pointsMaterial
        ref={materialRef}
        size={0.022}
        color="#8b7bff"
        transparent
        opacity={0.75}
        sizeAttenuation
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

function CoreGlow({ phase }) {
  const meshRef = useRef(null);
  useFrame((_, delta) => {
    if (!meshRef.current) return;
    const targetScale = phase === "searching" ? 1.18 : 1;
    const current = meshRef.current.scale.x;
    const next = current + (targetScale - current) * Math.min(1, delta * 2.5);
    meshRef.current.scale.setScalar(next);
  });
  return (
    <mesh ref={meshRef}>
      <icosahedronGeometry args={[0.55, 2]} />
      <meshBasicMaterial color="#6e5cf0" wireframe transparent opacity={0.35} />
    </mesh>
  );
}

export default function Scene3D({ phase = "idle", className = "" }) {
  return (
    <div className={className} aria-hidden="true">
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        dpr={[1, 1.8]}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.4} />
        <ParticleField phase={phase} />
        <CoreGlow phase={phase} />
      </Canvas>
    </div>
  );
}
