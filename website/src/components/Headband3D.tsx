"use client";

import { Html, Line, OrbitControls, RoundedBox } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";

/*
 * The real iShara prototype in 3D (not a concept product): a curved fabric/foam band with the
 * electronics on the forehead section: Li-Po battery, USB-C charger board, MPU6050 module,
 * ESP32 dev board, buzzer and wires. `explode` (0..1) separates the parts and shows labels.
 */

type Part = {
  name: string;
  role: string;
  pos: [number, number, number];
  out: [number, number, number]; // direction it moves when exploded
  labelSide: "left" | "right";
  label: [number, number]; // label offset from the part (kept inside the canvas)
};

const PARTS: Record<string, Part> = {
  battery: { name: "Li-Po battery", role: "3.7 V · 1200 mAh", pos: [-0.95, 0.05, 0], out: [-0.75, -0.1, 0.35], labelSide: "left", label: [0.05, 0.98] },
  charger: { name: "USB-C charger", role: "charges the battery", pos: [-0.05, 0.55, 0], out: [-0.35, 0.75, 0.4], labelSide: "left", label: [0, 0.58] },
  mpu: { name: "MPU6050", role: "measures head tilt", pos: [0.75, 0.55, 0], out: [0.55, 0.7, 0.5], labelSide: "right", label: [-0.05, 0.55] },
  esp32: { name: "ESP32", role: "Bluetooth mouse + model", pos: [0.45, -0.5, 0], out: [0.2, -0.75, 0.45], labelSide: "right", label: [-0.1, -0.56] },
  buzzer: { name: "Buzzer", role: "beeps on connect", pos: [1.35, -0.45, 0.05], out: [0.8, -0.35, 0.3], labelSide: "right", label: [-0.4, -0.42] },
};

function useExplodedPosition(part: Part, explode: MutableRefObject<number>, ref: MutableRefObject<THREE.Group | null>) {
  useFrame(() => {
    const g = ref.current;
    if (!g) return;
    const e = explode.current;
    g.position.set(part.pos[0] + part.out[0] * e, part.pos[1] + part.out[1] * e, part.pos[2] + part.out[2] * e);
  });
}

function Label({ part, explode }: { part: Part; explode: MutableRefObject<number> }) {
  const ref = useRef<HTMLDivElement>(null);
  useFrame(() => { if (ref.current) ref.current.style.opacity = String(Math.max(0, Math.min(1, (explode.current - 0.35) / 0.35))); });
  return (
    <Html position={[part.label[0], part.label[1], 0.2]} center zIndexRange={[10, 0]} style={{ pointerEvents: "none" }}>
      <div ref={ref} className={`hb-label ${part.labelSide}`} style={{ opacity: 0 }}>
        <b>{part.name}</b><span>{part.role}</span>
      </div>
    </Html>
  );
}

function Component({ id, explode, children }: { id: keyof typeof PARTS; explode: MutableRefObject<number>; children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null);
  const part = PARTS[id];
  useExplodedPosition(part, explode, ref);
  return (
    <group ref={ref} position={part.pos}>
      {children}
      <Label part={part} explode={explode} />
    </group>
  );
}

function Pins({ n, x0, dx, y, z, color = "#c7c7cc" }: { n: number; x0: number; dx: number; y: number; z: number; color?: string }) {
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <mesh key={i} position={[x0 + i * dx, y, z]}>
          <cylinderGeometry args={[0.022, 0.022, 0.05, 10]} />
          <meshStandardMaterial color={color} metalness={0.8} roughness={0.3} />
        </mesh>
      ))}
    </>
  );
}

function Band() {
  // fabric band: an open cylinder segment curving around the head, behind the electronics
  const geo = useMemo(() => new THREE.CylinderGeometry(3.2, 3.2, 1.05, 96, 1, true, -Math.PI * 0.4, Math.PI * 0.8), []);
  return (
    <group position={[0, 0, -3.32]}>
      <mesh geometry={geo}>
        <meshStandardMaterial color="#b9b9be" roughness={0.95} side={THREE.DoubleSide} />
      </mesh>
    </group>
  );
}

function Plate({ explode }: { explode: MutableRefObject<number> }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(() => { if (ref.current) ref.current.position.z = -0.08 - explode.current * 0.5; });
  return (
    <RoundedBox ref={ref} args={[3.3, 2.0, 0.06]} radius={0.12} position={[0.1, 0.02, -0.08]}>
      <meshStandardMaterial color="#ececef" roughness={0.8} />
    </RoundedBox>
  );
}

function Wires({ explode }: { explode: MutableRefObject<number> }) {
  const group = useRef<THREE.Group>(null);
  useFrame(() => { if (group.current) group.current.visible = explode.current < 0.25; });
  const w = (pts: [number, number, number][], color: string) => <Line points={pts} color={color} lineWidth={2.2} />;
  return (
    <group ref={group}>
      {w([[0.55, 0.3, 0.06], [0.45, 0.05, 0.12], [0.3, -0.25, 0.06]], "#2f6fe8")}
      {w([[0.68, 0.3, 0.06], [0.58, 0.02, 0.12], [0.42, -0.25, 0.06]], "#34c759")}
      {w([[0.82, 0.3, 0.06], [0.75, 0.02, 0.12], [0.6, -0.25, 0.06]], "#ff9500")}
      {w([[0.95, 0.3, 0.06], [0.9, 0.02, 0.12], [0.78, -0.25, 0.06]], "#af52de")}
      {w([[-0.6, 0.35, 0.06], [-0.4, 0.45, 0.12], [-0.25, 0.4, 0.06]], "#ff3b30")}
      {w([[-0.6, 0.2, 0.06], [-0.35, 0.25, 0.12], [-0.25, 0.3, 0.06]], "#1d1d1f")}
    </group>
  );
}

function Model({ explode, reduceMotion }: { explode: MutableRefObject<number>; reduceMotion: boolean }) {
  const root = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (!root.current || reduceMotion) return;
    root.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.35) * 0.18 * (1 - explode.current * 0.6);
  });
  return (
    <group ref={root} scale={0.82}>
      <Band />
      {/* mounting plate on the foam */}
      <Plate explode={explode} />

      <Component id="battery" explode={explode}>
        <RoundedBox args={[0.8, 1.5, 0.16]} radius={0.04}><meshStandardMaterial color="#d6d6db" metalness={0.5} roughness={0.35} /></RoundedBox>
        <mesh position={[0, -0.62, 0.002]}><boxGeometry args={[0.81, 0.26, 0.162]} /><meshStandardMaterial color="#e3c24a" roughness={0.5} /></mesh>
      </Component>

      <Component id="charger" explode={explode}>
        <RoundedBox args={[0.5, 0.62, 0.05]} radius={0.02}><meshStandardMaterial color="#2a5db0" roughness={0.6} /></RoundedBox>
        <RoundedBox args={[0.26, 0.1, 0.09]} radius={0.03} position={[0, 0.22, 0.05]}><meshStandardMaterial color="#c7c7cc" metalness={0.9} roughness={0.25} /></RoundedBox>
      </Component>

      <Component id="mpu" explode={explode}>
        <RoundedBox args={[0.82, 0.6, 0.05]} radius={0.02}><meshStandardMaterial color="#1f4fa3" roughness={0.55} /></RoundedBox>
        <mesh position={[0, 0.04, 0.04]}><boxGeometry args={[0.2, 0.2, 0.04]} /><meshStandardMaterial color="#1d1d1f" roughness={0.4} /></mesh>
        <Pins n={8} x0={-0.35} dx={0.1} y={-0.22} z={0.04} />
      </Component>

      <Component id="esp32" explode={explode}>
        <RoundedBox args={[1.45, 0.66, 0.06]} radius={0.02}><meshStandardMaterial color="#1d1d1f" roughness={0.5} /></RoundedBox>
        <RoundedBox args={[0.46, 0.46, 0.06]} radius={0.02} position={[0.38, 0, 0.05]}><meshStandardMaterial color="#8e8e93" metalness={0.7} roughness={0.3} /></RoundedBox>
        <RoundedBox args={[0.2, 0.16, 0.1]} radius={0.04} position={[-0.58, 0, 0.05]}><meshStandardMaterial color="#c7c7cc" metalness={0.9} roughness={0.25} /></RoundedBox>
        <Pins n={14} x0={-0.65} dx={0.1} y={0.28} z={0.04} color="#a1a1a6" />
        <mesh position={[0.62, -0.25, 0.05]}><sphereGeometry args={[0.025, 12, 12]} /><meshStandardMaterial color="#ff3b30" emissive="#ff3b30" emissiveIntensity={2} /></mesh>
      </Component>

      <Component id="buzzer" explode={explode}>
        <mesh rotation={[Math.PI / 2, 0, 0]}><cylinderGeometry args={[0.17, 0.17, 0.16, 32]} /><meshStandardMaterial color="#1d1d1f" roughness={0.4} /></mesh>
      </Component>

      <Wires explode={explode} />
    </group>
  );
}

/** Keep the whole (exploded) model in frame on narrow screens by moving the camera back. */
function FitCamera() {
  const { camera, size } = useThree();
  useFrame(() => {
    const aspect = size.width / Math.max(1, size.height);
    const dist = aspect >= 1.05 ? 6.41 : 6.41 * Math.min(2, 1.1 / aspect);
    // change only the distance, keep the angle the user dragged to (works with OrbitControls)
    if (Math.abs(camera.position.length() - dist) > 0.01) camera.position.setLength(dist);
  });
  return null;
}

export default function Headband3D({ explode, reduceMotion }: { explode: MutableRefObject<number>; reduceMotion: boolean }) {
  return (
    <Canvas
      camera={{ position: [0, 0.3, 6.4], fov: 38 }}
      dpr={[1, 2]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      aria-label="3D model of the iShara headband"
    >
      <ambientLight intensity={0.75} />
      <directionalLight position={[3, 4, 5]} intensity={1.6} />
      <directionalLight position={[-4, -2, 3]} intensity={0.5} />
      <FitCamera />
      <Model explode={explode} reduceMotion={reduceMotion} />
      <OrbitControls enableZoom={false} enablePan={false} minPolarAngle={Math.PI * 0.3} maxPolarAngle={Math.PI * 0.7}
        minAzimuthAngle={-Math.PI * 0.45} maxAzimuthAngle={Math.PI * 0.45} />
    </Canvas>
  );
}
