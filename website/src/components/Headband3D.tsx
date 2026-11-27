"use client";

import { ContactShadows, Html, OrbitControls, RoundedBox } from "@react-three/drei";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useEffect, useMemo, useRef, type MutableRefObject } from "react";
import * as THREE from "three";
import { RoomEnvironment } from "three/examples/jsm/environments/RoomEnvironment.js";

/*
 * The real iShara prototype in 3D (not a concept product), modelled on photos of the hardware:
 * grey fleece headband with a white foam mount; black ESP32 dev board with a metal RF shield;
 * blue MPU6050 (GY-521) breakout; blue USB-C Li-Po charger; silver 1200 mAh pouch cell with
 * yellow tape; black buzzer; coloured jumper wires.
 * Realism without downloads: studio lighting is generated in the browser (RoomEnvironment),
 * board markings and fabric are drawn into canvas textures, soft contact shadows underneath.
 * `explode` (0..1) separates the parts and fades in labels.
 */

type V3 = [number, number, number];

type Part = {
  name: string;
  role: string;
  pos: [number, number, number];
  out: [number, number, number];
  label: [number, number];
};

const PARTS_POS = {
  battery: [-0.95, 0.05, 0] as V3, charger: [-0.05, 0.55, 0] as V3, mpu: [0.75, 0.55, 0] as V3,
  esp32: [0.45, -0.5, 0] as V3, buzzer: [1.35, -0.45, 0.05] as V3,
};

const PARTS: Record<string, Part> = {
  battery: { name: "Li-Po battery", role: "3.7 V · 1200 mAh", pos: PARTS_POS.battery, out: [-0.75, -0.1, 0.35], label: [0.05, 0.98] },
  charger: { name: "USB-C charger", role: "charges the battery", pos: PARTS_POS.charger, out: [-0.35, 0.75, 0.4], label: [0, 0.58] },
  mpu: { name: "MPU6050", role: "measures head tilt", pos: PARTS_POS.mpu, out: [0.55, 0.7, 0.5], label: [-0.05, 0.55] },
  esp32: { name: "ESP32", role: "Bluetooth mouse + model", pos: PARTS_POS.esp32, out: [0.2, -0.75, 0.45], label: [-0.1, -0.56] },
  buzzer: { name: "Buzzer", role: "beeps on connect", pos: PARTS_POS.buzzer, out: [0.8, -0.35, 0.3], label: [-0.4, -0.42] },
};

/* ---------------- real pin layout (from the prototype photo + firmware wiring) ---------------- */
// ESP32 DevKit V1, 30 pins, as printed on the board (USB on the left)
const ESP_TOP = ["VIN", "GND", "D13", "D12", "D14", "D27", "D26", "D25", "D33", "D32", "D35", "D34", "VN", "VP", "EN"];
const ESP_BOTTOM = ["3V3", "GND", "D15", "D2", "D4", "RX2", "TX2", "D5", "D18", "D19", "D21", "RX0", "TX0", "D22", "D23"];
const ESP_W = 1.45, ESP_PIN_X0 = -0.665, ESP_PIN_DX = 0.095, ESP_ROW_Y = 0.29;
const MPU_PINS = ["VCC", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"];
const MPU_PIN_X0 = -0.35, MPU_PIN_DX = 0.1, MPU_ROW_Y = -0.24;
// charger solder pads, board-local (board is 0.5 x 0.62)
const CHARGER_PADS: [string, number, number][] = [["B+", 0.125, -0.12], ["B-", 0.125, -0.24], ["OUT+", -0.15, -0.24], ["OUT-", -0.02, -0.24]];
const PIN_TIP_Z = 0.13; // header pins stick out of the boards

const espPin = (row: "top" | "bottom", name: string): V3 => {
  const i = (row === "top" ? ESP_TOP : ESP_BOTTOM).indexOf(name);
  const [px, py] = PARTS_POS.esp32;
  return [px + ESP_PIN_X0 + i * ESP_PIN_DX, py + (row === "top" ? ESP_ROW_Y : -ESP_ROW_Y), PIN_TIP_Z];
};
const mpuPin = (name: string): V3 => {
  const i = MPU_PINS.indexOf(name);
  const [px, py] = PARTS_POS.mpu;
  return [px + MPU_PIN_X0 + i * MPU_PIN_DX, py + MPU_ROW_Y, PIN_TIP_Z];
};
const chargerPad = (name: string): V3 => {
  const [, x, y] = CHARGER_PADS.find((p) => p[0] === name)!;
  const [px, py] = PARTS_POS.charger;
  return [px + x, py + y, 0.03];
};

/* ---------------- canvas textures (drawn once, no network) ---------------- */
function canvasTexture(w: number, h: number, draw: (g: CanvasRenderingContext2D) => void, repeat?: [number, number]) {
  const c = document.createElement("canvas");
  c.width = w; c.height = h;
  draw(c.getContext("2d")!);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 8;
  if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
  return t;
}

function noise(g: CanvasRenderingContext2D, w: number, h: number, base: string, spread: number) {
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  const img = g.getImageData(0, 0, w, h);
  for (let i = 0; i < img.data.length; i += 4) {
    const n = (Math.random() - 0.5) * spread;
    img.data[i] += n; img.data[i + 1] += n; img.data[i + 2] += n;
  }
  g.putImageData(img, 0, 0);
}

type Textures = Record<"fleece" | "foam" | "foil" | "esp" | "shield" | "mpu" | "charger", THREE.CanvasTexture>;

function makeTextures(): Textures {
  const fleece = canvasTexture(256, 256, (g) => {
    noise(g, 256, 256, "#8f9096", 40);
    for (let i = 0; i < 1400; i++) {            // soft fibre tufts
      g.fillStyle = `rgba(${Math.random() < 0.5 ? "255,255,255" : "70,70,75"},${0.05 + Math.random() * 0.08})`;
      g.beginPath(); g.arc(Math.random() * 256, Math.random() * 256, 1 + Math.random() * 3, 0, 7); g.fill();
    }
  }, [10, 2]);
  const foam = canvasTexture(256, 256, (g) => noise(g, 256, 256, "#f2f2f4", 14), [3, 2]);
  const foil = canvasTexture(256, 512, (g) => {
    const grd = g.createLinearGradient(0, 0, 256, 512);
    grd.addColorStop(0, "#dcdce0"); grd.addColorStop(0.5, "#c9c9ce"); grd.addColorStop(1, "#e2e2e6");
    g.fillStyle = grd; g.fillRect(0, 0, 256, 512);
    for (let i = 0; i < 40; i++) {              // pouch wrinkles
      g.strokeStyle = `rgba(255,255,255,${0.08 + Math.random() * 0.12})`; g.lineWidth = 1 + Math.random() * 2;
      const y = Math.random() * 512;
      g.beginPath(); g.moveTo(0, y); g.bezierCurveTo(80, y + 20 * Math.random(), 170, y - 20 * Math.random(), 256, y + 10); g.stroke();
    }
    g.save(); g.translate(128, 230); g.rotate(-Math.PI / 2); g.fillStyle = "#3a3a3c"; g.textAlign = "center";
    g.font = "600 30px monospace"; g.fillText("603450 1200mAh", 0, -10);
    g.font = "500 26px monospace"; g.fillText("3.7V 4.44Wh", 0, 26); g.restore();
  });
  const esp = canvasTexture(1024, 464, (g) => {
    g.fillStyle = "#151517"; g.fillRect(0, 0, 1024, 464);
    g.strokeStyle = "rgba(255,255,255,0.07)"; g.lineWidth = 3;
    for (let i = 0; i < 18; i++) { g.beginPath(); g.moveTo(80 + i * 44, 120); g.lineTo(120 + i * 44, 340); g.stroke(); }
    const px = (i: number) => ((ESP_PIN_X0 + i * ESP_PIN_DX) / ESP_W + 0.5) * 1024;
    g.textAlign = "center";
    for (let i = 0; i < 15; i++) {
      g.fillStyle = "#c8a45a"; // gold pads under the header pins
      g.beginPath(); g.arc(px(i), 34, 17, 0, 7); g.fill();
      g.beginPath(); g.arc(px(i), 430, 17, 0, 7); g.fill();
      g.fillStyle = "#e9e9ec"; g.font = "600 19px sans-serif";
      g.fillText(ESP_TOP[i], px(i), 82); g.fillText(ESP_BOTTOM[i], px(i), 396);
    }
    g.font = "600 22px sans-serif"; g.fillText("EN", 110, 175); g.fillText("BOOT", 110, 310);
    g.font = "700 26px sans-serif"; g.fillText("ESP32 DEVKIT V1", 380, 250);
  });
  const shield = canvasTexture(256, 256, (g) => {
    const grd = g.createLinearGradient(0, 0, 256, 256); grd.addColorStop(0, "#d4d5d9"); grd.addColorStop(1, "#9a9ca3");
    g.fillStyle = grd; g.fillRect(0, 0, 256, 256);
    g.fillStyle = "#2c2c2e"; g.font = "700 26px sans-serif"; g.textAlign = "center";
    g.fillText("ESP32-WROOM-32", 128, 110); g.font = "500 18px sans-serif"; g.fillText("Wi-Fi + BLE", 128, 150); g.fillText("CE  ROHS", 128, 180);
  });
  const mpu = canvasTexture(320, 240, (g) => {
    g.fillStyle = "#1d4e9e"; g.fillRect(0, 0, 320, 240);
    g.fillStyle = "#e9eefb"; g.font = "700 22px sans-serif"; g.fillText("MPU-6050", 170, 34);
    g.font = "500 15px sans-serif"; g.fillText("HW-123", 205, 58);
    const pins = ["VCC", "GND", "SCL", "SDA", "XDA", "XCL", "AD0", "INT"];
    g.font = "600 13px sans-serif"; g.textAlign = "center";
    pins.forEach((p, i) => g.fillText(p, 26 + i * 38, 196));
    g.strokeStyle = "#e9eefb"; g.lineWidth = 2;                        // axis arrows
    g.beginPath(); g.moveTo(268, 110); g.lineTo(300, 110); g.moveTo(284, 94); g.lineTo(284, 126); g.stroke();
    g.fillStyle = "#e3c24a"; g.fillRect(150, 60, 34, 18);              // tantalum capacitor
  });
  const charger = canvasTexture(400, 496, (g) => {
    g.fillStyle = "#2457a8"; g.fillRect(0, 0, 400, 496);
    g.fillStyle = "#e9eefb"; g.font = "700 30px sans-serif";
    g.save(); g.translate(40, 300); g.rotate(-Math.PI / 2); g.fillText("HW-373 V1.2", 0, 0); g.restore();
    g.fillStyle = "#1d1d1f"; g.fillRect(150, 190, 90, 70); // charger IC
    g.textAlign = "center"; g.font = "700 24px sans-serif";
    for (const [name, x, y] of CHARGER_PADS) {
      const cx = (x / 0.5 + 0.5) * 400, cy = (0.5 - y / 0.62) * 496;
      g.fillStyle = "#cfd0d4"; g.beginPath(); g.arc(cx, cy, 20, 0, 7); g.fill();
      g.fillStyle = "#e9eefb"; g.fillText(name, cx, cy - 30);
    }
  });
  return { fleece, foam, foil, esp, shield, mpu, charger };
}

/* ---------------- studio lighting generated in the browser ---------------- */
function StudioEnvironment() {
  const { gl, scene } = useThree();
  useEffect(() => {
    const pmrem = new THREE.PMREMGenerator(gl);
    const env = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = env;
    scene.environmentIntensity = 0.55;   // reflections without washing out colours
    return () => { scene.environment = null; env.dispose(); pmrem.dispose(); };
  }, [gl, scene]);
  return null;
}

/* ---------------- parts ---------------- */
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
      <div ref={ref} className="hb-label" style={{ opacity: 0 }}><b>{part.name}</b><span>{part.role}</span></div>
    </Html>
  );
}

function Component({ id, explode, children }: { id: keyof typeof PARTS; explode: MutableRefObject<number>; children: React.ReactNode }) {
  const ref = useRef<THREE.Group>(null);
  const part = PARTS[id];
  useExplodedPosition(part, explode, ref);
  return <group ref={ref} position={part.pos}>{children}<Label part={part} explode={explode} /></group>;
}

function HeaderPins({ n, x0, dx, y, z, gold = false }: { n: number; x0: number; dx: number; y: number; z: number; gold?: boolean }) {
  const geo = useMemo(() => new THREE.CylinderGeometry(0.018, 0.018, 0.12, 8), []);
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <group key={i} position={[x0 + i * dx, y, z]}>
          <mesh rotation={[Math.PI / 2, 0, 0]} geometry={geo} castShadow>
            <meshStandardMaterial color={gold ? "#d4af37" : "#cfd0d4"} metalness={1} roughness={0.25} />
          </mesh>
          <mesh position={[0, 0, -0.03]}><boxGeometry args={[0.07, 0.07, 0.05]} /><meshStandardMaterial color="#111" roughness={0.7} /></mesh>
        </group>
      ))}
    </>
  );
}

function Band({ tex }: { tex: Textures }) {
  // thick fleece strap curving around the head (its front face sits just behind the foam mount)
  const geo = useMemo(() => {
    const shape = new THREE.Shape();
    const R = 3.2, T = 0.12, a0 = -Math.PI * 0.42, a1 = Math.PI * 0.42, seg = 80;
    for (let i = 0; i <= seg; i++) {
      const a = a0 + ((a1 - a0) * i) / seg;
      if (i === 0) shape.moveTo(Math.sin(a) * R, Math.cos(a) * R); else shape.lineTo(Math.sin(a) * R, Math.cos(a) * R);
    }
    for (let i = seg; i >= 0; i--) { const a = a0 + ((a1 - a0) * i) / seg; shape.lineTo(Math.sin(a) * (R - T), Math.cos(a) * (R - T)); }
    const g = new THREE.ExtrudeGeometry(shape, { depth: 1.05, bevelEnabled: true, bevelSize: 0.04, bevelThickness: 0.04, bevelSegments: 3, curveSegments: 1 });
    // shape lies in x/y (front of the arc at +y); rotate +90 deg about X so the arc front faces +z
    // (towards the camera) and the extrusion depth becomes the band's height, then centre it
    g.rotateX(Math.PI / 2);
    g.translate(0, 0.52, 0);
    return g;
  }, []);
  return (
    <mesh geometry={geo} position={[0, 0, -3.32]} receiveShadow>
      <meshStandardMaterial map={tex.fleece} bumpMap={tex.fleece} bumpScale={0.05} roughness={1} envMapIntensity={0.3} />
    </mesh>
  );
}

function Plate({ explode, tex }: { explode: MutableRefObject<number>; tex: Textures }) {
  const ref = useRef<THREE.Mesh>(null);
  useFrame(() => { if (ref.current) ref.current.position.z = -0.1 - explode.current * 0.5; });
  return (
    <RoundedBox ref={ref} args={[3.3, 2.0, 0.12]} radius={0.12} smoothness={4} position={[0.1, 0.02, -0.1]} receiveShadow castShadow>
      <meshStandardMaterial map={tex.foam} bumpMap={tex.foam} bumpScale={0.02} roughness={0.95} />
    </RoundedBox>
  );
}

/* coloured jumper wires as real tubes */
// Each wire runs from its real source to its real destination
// (firmware header: MPU SDA D21, SCL D22, buzzer D26; docs/hardware.md).
function route(a: V3, b: V3, lift: number, via: [number, number]): V3[] {
  const mid: V3 = [via[0], via[1], lift];
  return [a, [a[0], a[1], a[2] + 0.12], [(a[0] + mid[0]) / 2, (a[1] + mid[1]) / 2, lift * 0.9], mid,
    [(b[0] + mid[0]) / 2, (b[1] + mid[1]) / 2, lift * 0.9], [b[0], b[1], b[2] + 0.12], b];
}
const BAT_PLUS: V3 = [-0.82, 0.83, 0.03], BAT_MINUS: V3 = [-1.08, 0.83, 0.03];
const BUZ_PLUS: V3 = [1.2, -0.39, 0.06], BUZ_MINUS: V3 = [1.2, -0.51, 0.06];
export const WIRES: { pts: V3[]; color: string; what: string }[] = [
  { what: "battery + -> charger B+", color: "#e5372b", pts: route(BAT_PLUS, chargerPad("B+"), 0.26, [-0.4, 0.95]) },
  { what: "battery - -> charger B-", color: "#1d1d1f", pts: route(BAT_MINUS, chargerPad("B-"), 0.22, [-0.55, 0.78]) },
  { what: "charger OUT+ -> ESP32 VIN", color: "#e5372b", pts: route(chargerPad("OUT+"), espPin("top", "VIN"), 0.3, [-0.26, 0.05]) },
  { what: "charger OUT- -> ESP32 GND", color: "#1d1d1f", pts: route(chargerPad("OUT-"), espPin("top", "GND"), 0.26, [-0.1, 0.05]) },
  { what: "MPU VCC -> ESP32 3V3", color: "#ff453a", pts: route(mpuPin("VCC"), espPin("bottom", "3V3"), 0.42, [0.0, -0.55]) },
  { what: "MPU GND -> ESP32 GND", color: "#2c2c2e", pts: route(mpuPin("GND"), espPin("bottom", "GND"), 0.38, [0.12, -0.6]) },
  { what: "MPU SCL -> ESP32 D22", color: "#ffd60a", pts: route(mpuPin("SCL"), espPin("bottom", "D22"), 0.4, [1.12, -0.5]) },
  { what: "MPU SDA -> ESP32 D21", color: "#34c759", pts: route(mpuPin("SDA"), espPin("bottom", "D21"), 0.34, [0.86, -0.55]) },
  { what: "buzzer + -> ESP32 D26", color: "#ff9500", pts: route(BUZ_PLUS, espPin("top", "D26"), 0.28, [0.85, -0.08]) },
  { what: "buzzer - -> ESP32 GND", color: "#1d1d1f", pts: route(BUZ_MINUS, espPin("top", "GND"), 0.24, [0.4, 0.02]) },
];
function Wire({ pts, color }: { pts: V3[]; color: string }) {
  const geo = useMemo(() => new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts.map((p) => new THREE.Vector3(p[0], p[1], p[2]))), 64, 0.017, 8, false), [pts]);
  useEffect(() => () => geo.dispose(), [geo]);
  const ends = [pts[0], pts[pts.length - 1]];
  return (
    <group>
      <mesh geometry={geo} castShadow><meshStandardMaterial color={color} roughness={0.45} /></mesh>
      {ends.map((p, i) => (
        <mesh key={i} position={p}><sphereGeometry args={[0.028, 12, 12]} /><meshStandardMaterial color="#c9cace" metalness={1} roughness={0.25} /></mesh>
      ))}
    </group>
  );
}
function Wires({ explode }: { explode: MutableRefObject<number> }) {
  const group = useRef<THREE.Group>(null);
  useFrame(() => { if (group.current) group.current.visible = explode.current < 0.25; });
  return <group ref={group}>{WIRES.map((w, i) => <Wire key={i} pts={w.pts} color={w.color} />)}</group>;
}

function Model({ explode, reduceMotion }: { explode: MutableRefObject<number>; reduceMotion: boolean }) {
  const tex = useMemo(makeTextures, []);
  useEffect(() => () => { Object.values(tex).forEach((t) => t.dispose()); }, [tex]);
  const root = useRef<THREE.Group>(null);
  useFrame((state) => {
    if (!root.current || reduceMotion) return;
    root.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.35) * 0.18 * (1 - explode.current * 0.6);
  });
  return (
    <group ref={root} scale={0.92}>
      <Band tex={tex} />
      <Plate explode={explode} tex={tex} />

      <Component id="battery" explode={explode}>
        <RoundedBox args={[0.8, 1.5, 0.16]} radius={0.05} smoothness={4} castShadow>
          <meshStandardMaterial map={tex.foil} metalness={0.75} roughness={0.32} />
        </RoundedBox>
        <mesh position={[0, -0.63, 0.004]} castShadow>
          <boxGeometry args={[0.81, 0.24, 0.162]} />
          <meshPhysicalMaterial color="#e0b93a" roughness={0.35} clearcoat={0.6} />
        </mesh>
        {[0.13, -0.13].map((x) => (
          <mesh key={x} position={[x, 0.78, 0.02]} castShadow><boxGeometry args={[0.07, 0.1, 0.012]} /><meshStandardMaterial color="#d8d9dd" metalness={1} roughness={0.3} /></mesh>
        ))}
      </Component>

      <Component id="charger" explode={explode}>
        <RoundedBox args={[0.5, 0.62, 0.04]} radius={0.015} castShadow><meshStandardMaterial map={tex.charger} roughness={0.55} /></RoundedBox>
        <RoundedBox args={[0.26, 0.1, 0.09]} radius={0.035} position={[0, 0.22, 0.05]} castShadow><meshStandardMaterial color="#c9cace" metalness={1} roughness={0.2} /></RoundedBox>
        <mesh position={[0.12, -0.05, 0.03]}><sphereGeometry args={[0.02, 12, 12]} /><meshStandardMaterial color="#ff3b30" emissive="#ff3b30" emissiveIntensity={3} /></mesh>
      </Component>

      <Component id="mpu" explode={explode}>
        <RoundedBox args={[0.82, 0.6, 0.04]} radius={0.015} castShadow><meshStandardMaterial map={tex.mpu} roughness={0.55} /></RoundedBox>
        <mesh position={[-0.02, 0.04, 0.035]} castShadow><boxGeometry args={[0.15, 0.15, 0.03]} /><meshStandardMaterial color="#141416" roughness={0.35} /></mesh>
        {[[-0.33, 0.22], [0.33, 0.22]].map(([x, y], i) => (
          <mesh key={i} position={[x, y, 0.021]} rotation={[Math.PI / 2, 0, 0]}>
            <cylinderGeometry args={[0.045, 0.045, 0.002, 24]} /><meshStandardMaterial color="#d4af37" metalness={1} roughness={0.3} />
          </mesh>
        ))}
        <HeaderPins n={8} x0={MPU_PIN_X0} dx={MPU_PIN_DX} y={MPU_ROW_Y} z={0.07} gold />
      </Component>

      <Component id="esp32" explode={explode}>
        <RoundedBox args={[1.45, 0.66, 0.045]} radius={0.015} castShadow><meshStandardMaterial map={tex.esp} roughness={0.55} /></RoundedBox>
        <RoundedBox args={[0.5, 0.46, 0.05]} radius={0.01} position={[0.38, 0, 0.045]} castShadow>
          <meshStandardMaterial map={tex.shield} metalness={0.95} roughness={0.28} />
        </RoundedBox>
        <RoundedBox args={[0.2, 0.15, 0.09]} radius={0.04} position={[-0.6, 0, 0.06]} castShadow><meshStandardMaterial color="#c9cace" metalness={1} roughness={0.2} /></RoundedBox>
        {[[-0.48, 0.17], [-0.48, -0.17]].map(([x, y], i) => (
          <mesh key={i} position={[x, y, 0.04]} castShadow><boxGeometry args={[0.07, 0.07, 0.04]} /><meshStandardMaterial color="#d9d9dc" roughness={0.4} /></mesh>
        ))}
        <HeaderPins n={15} x0={ESP_PIN_X0} dx={ESP_PIN_DX} y={ESP_ROW_Y} z={0.07} />
        <HeaderPins n={15} x0={ESP_PIN_X0} dx={ESP_PIN_DX} y={-ESP_ROW_Y} z={0.07} />
        <mesh position={[0.66, -0.2, 0.035]}><sphereGeometry args={[0.022, 12, 12]} /><meshStandardMaterial color="#ff3b30" emissive="#ff3b30" emissiveIntensity={3} /></mesh>
      </Component>

      <Component id="buzzer" explode={explode}>
        <mesh rotation={[Math.PI / 2, 0, 0]} castShadow><cylinderGeometry args={[0.17, 0.17, 0.16, 40]} /><meshStandardMaterial color="#111113" roughness={0.45} /></mesh>
        <mesh position={[0, 0, 0.081]}><circleGeometry args={[0.035, 24]} /><meshStandardMaterial color="#2c2c2e" /></mesh>
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

export default function Headband3D({ explode, reduceMotion, active = true }: { explode: MutableRefObject<number>; reduceMotion: boolean; active?: boolean }) {
  return (
    <Canvas
      frameloop={active ? "always" : "never"}   // no rendering while scrolled away (saves battery, keeps scrolling smooth)
      shadows
      camera={{ position: [0, 0.3, 6.4], fov: 38 }}
      dpr={[1, 1.5]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance", toneMapping: THREE.ACESFilmicToneMapping, toneMappingExposure: 0.9 }}
      aria-label="3D model of the iShara headband"
    >
      <StudioEnvironment />
      <ambientLight intensity={0.15} />
      <directionalLight position={[2.5, 4, 5]} intensity={1.4} castShadow shadow-mapSize={[1024, 1024]} shadow-bias={-0.0004} />
      <directionalLight position={[-4, 1, 3]} intensity={0.35} />
      <FitCamera />
      <Model explode={explode} reduceMotion={reduceMotion} />
      <ContactShadows position={[0, -1.25, 0]} opacity={0.35} scale={7} blur={2.6} far={2.5} />
      <OrbitControls enableZoom={false} enablePan={false} minPolarAngle={Math.PI * 0.3} maxPolarAngle={Math.PI * 0.7}
        minAzimuthAngle={-Math.PI * 0.45} maxAzimuthAngle={Math.PI * 0.45} />
    </Canvas>
  );
}
