import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import * as THREE from "three";
import { getConnectors } from "../api";

// AlphaSource's signature visual object -- not a decorative particle
// effect, but a literal diagram of what the product does: one core
// (the AI orchestration layer -- Query Understanding + Discovery
// Decision Engine + Matching/Ranking) with real connected data sources
// orbiting it. The orbiting nodes are populated from GET /connectors --
// whatever the backend actually reports as registered, in its real
// enabled/health state -- never a hardcoded "GitHub, Greenhouse, ATS"
// list baked into the frontend.
//
// Three real, backend-driven states:
//   idle       -- core breathes slowly, connectors sit at rest.
//   searching  -- energy pulses travel from the core out to each
//                 connector that `activeConnectors` (from the real
//                 discovery.connector_results of THIS search) says was
//                 actually attempted, then a return pulse travels back
//                 in -- literally "search -> core -> connectors activate
//                 -> candidates emerge."
//   results    -- everything settles; the core dims to a calm resting
//                 glow.

const FALLBACK_CONNECTORS = [
  { name: "github", enabled: true },
  { name: "greenhouse_ats", enabled: true },
  { name: "browser_extension", enabled: true },
];

function labelFor(name) {
  const known = {
    github: "GitHub",
    greenhouse_ats: "Greenhouse",
    browser_extension: "Browser Extension",
    csv_import: "CSV Import",
    resume_import: "Resume Import",
    hrms: "HRMS",
  };
  return known[name] || name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

function CoreSphere({ phase }) {
  const meshRef = useRef(null);
  const glowRef = useRef(null);

  useFrame((state, delta) => {
    if (!meshRef.current) return;
    const t = state.clock.elapsedTime;
    const breathe = phase === "idle" ? Math.sin(t * 0.6) * 0.04 : phase === "searching" ? Math.sin(t * 3) * 0.09 : 0.02;
    const targetScale = 1 + breathe;
    meshRef.current.scale.setScalar(THREE.MathUtils.lerp(meshRef.current.scale.x, targetScale, Math.min(1, delta * 4)));
    meshRef.current.rotation.y += delta * (phase === "searching" ? 0.5 : 0.12);

    if (glowRef.current) {
      const targetOpacity = phase === "searching" ? 0.5 : phase === "results" ? 0.18 : 0.3;
      glowRef.current.material.opacity = THREE.MathUtils.lerp(
        glowRef.current.material.opacity,
        targetOpacity,
        Math.min(1, delta * 3)
      );
    }
  });

  return (
    <group>
      <mesh ref={glowRef}>
        <sphereGeometry args={[0.62, 32, 32]} />
        <meshBasicMaterial color="#6e5cf0" transparent opacity={0.3} />
      </mesh>
      <mesh ref={meshRef}>
        <icosahedronGeometry args={[0.42, 4]} />
        <meshStandardMaterial
          color="#0a0c14"
          emissive="#8b7bff"
          emissiveIntensity={0.55}
          roughness={0.25}
          metalness={0.6}
          wireframe={false}
        />
      </mesh>
      <mesh rotation={[Math.PI / 2.4, 0, 0]}>
        <torusGeometry args={[0.58, 0.004, 8, 96]} />
        <meshBasicMaterial color="#8b7bff" transparent opacity={0.35} />
      </mesh>
    </group>
  );
}

function ConnectorNode({ index, total, connector, active, phase }) {
  const groupRef = useRef(null);
  const dotRef = useRef(null);
  const radius = 1.85;
  const baseAngle = (index / total) * Math.PI * 2;
  const tiltOffsets = useMemo(() => [0.12, -0.08, 0.05, -0.14, 0.09][index % 5], [index]);

  useFrame((state, delta) => {
    if (!groupRef.current) return;
    const speed = phase === "searching" && active ? 0.35 : 0.05;
    const angle = baseAngle + state.clock.elapsedTime * speed;
    const y = Math.sin(state.clock.elapsedTime * 0.4 + index) * 0.25 * tiltOffsets * 4;
    groupRef.current.position.set(Math.cos(angle) * radius, y, Math.sin(angle) * radius);

    if (dotRef.current) {
      const targetScale = active && phase === "searching" ? 1.6 : 1;
      dotRef.current.scale.setScalar(
        THREE.MathUtils.lerp(dotRef.current.scale.x, targetScale, Math.min(1, delta * 5))
      );
      const targetIntensity = active && phase === "searching" ? 1.4 : connector?.enabled === false ? 0.15 : 0.6;
      dotRef.current.material.emissiveIntensity = THREE.MathUtils.lerp(
        dotRef.current.material.emissiveIntensity,
        targetIntensity,
        Math.min(1, delta * 4)
      );
    }
  });

  const color = connector?.enabled === false ? "#565c74" : active && phase === "searching" ? "#3ddc97" : "#8b7bff";

  return (
    <group ref={groupRef}>
      <mesh ref={dotRef}>
        <sphereGeometry args={[0.09, 16, 16]} />
        <meshStandardMaterial color="#0a0c14" emissive={color} emissiveIntensity={0.6} roughness={0.3} metalness={0.4} />
      </mesh>
    </group>
  );
}

function EnergyLine({ index, total, active, phase }) {
  const lineRef = useRef(null);
  const radius = 1.85;
  const baseAngle = (index / total) * Math.PI * 2;

  const geometry = useMemo(() => {
    const points = [new THREE.Vector3(0, 0, 0), new THREE.Vector3(Math.cos(baseAngle) * radius, 0, Math.sin(baseAngle) * radius)];
    return new THREE.BufferGeometry().setFromPoints(points);
  }, [baseAngle]);

  useFrame((_, delta) => {
    if (!lineRef.current) return;
    const targetOpacity = active && phase === "searching" ? 0.55 : 0.08;
    lineRef.current.material.opacity = THREE.MathUtils.lerp(lineRef.current.material.opacity, targetOpacity, Math.min(1, delta * 3));
  });

  return (
    <line ref={lineRef} geometry={geometry}>
      <lineBasicMaterial color={active && phase === "searching" ? "#3ddc97" : "#6e5cf0"} transparent opacity={0.08} />
    </line>
  );
}

function Scene({ phase, activeConnectors, connectors }) {
  const list = connectors.length > 0 ? connectors : FALLBACK_CONNECTORS;
  return (
    <>
      <ambientLight intensity={0.5} />
      <pointLight position={[2, 2, 2]} intensity={1.2} color="#8b7bff" />
      <CoreSphere phase={phase} />
      {list.map((connector, i) => (
        <EnergyLine
          key={`line-${connector.name}`}
          index={i}
          total={list.length}
          active={activeConnectors.has(connector.name)}
          phase={phase}
        />
      ))}
      {list.map((connector, i) => (
        <ConnectorNode
          key={connector.name}
          index={i}
          total={list.length}
          connector={connector}
          active={activeConnectors.has(connector.name)}
          phase={phase}
        />
      ))}
    </>
  );
}

/**
 * @param phase "idle" | "searching" | "results"
 * @param activeConnectorNames string[] -- real connector `source_name`s
 *   from THIS search's discovery.connector_results where attempted=true.
 *   Drives which orbit node pulses -- never fabricated.
 */
export default function DiscoveryCore({ phase = "idle", activeConnectorNames = [], className = "" }) {
  const [connectors, setConnectors] = useState([]);

  useEffect(() => {
    let cancelled = false;
    getConnectors().then((list) => {
      if (!cancelled && Array.isArray(list) && list.length > 0) setConnectors(list);
    });
    return () => {
      cancelled = true;
    };
  }, []);

  const activeConnectors = useMemo(() => new Set(activeConnectorNames), [activeConnectorNames]);
  const labeledConnectors = useMemo(
    () => (connectors.length > 0 ? connectors : FALLBACK_CONNECTORS),
    [connectors]
  );

  return (
    <div className={className} aria-hidden="true">
      <Canvas camera={{ position: [0, 1.1, 5.2], fov: 42 }} dpr={[1, 1.8]} gl={{ antialias: true, alpha: true }}>
        <Scene phase={phase} activeConnectors={activeConnectors} connectors={labeledConnectors} />
      </Canvas>
      <div className="pointer-events-none absolute inset-0 flex items-end justify-center pb-1">
        {phase !== "idle" && (
          <div className="flex flex-wrap justify-center gap-x-3 gap-y-0.5 text-[10px] tracking-wide text-ink-500">
            {labeledConnectors.slice(0, 5).map((c) => (
              <span
                key={c.name}
                className={activeConnectors.has(c.name) && phase === "searching" ? "text-signal-green" : ""}
              >
                {labelFor(c.name)}
              </span>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
