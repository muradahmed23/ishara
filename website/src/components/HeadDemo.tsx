"use client";

import type { FaceLandmarker } from "@mediapipe/tasks-vision";
import { useCallback, useEffect, useRef, useState } from "react";
import { axisSpeed, clamp, DEFAULT_MODEL, type MotionModel } from "@/lib/motion";

/*
 * "Try it with your head": the iShara experience in the browser.
 * Webcam -> MediaPipe face landmarker (runs locally, nothing is uploaded) -> head pitch/roll
 * -> the same movement model as the headband -> a cursor. Pop bubbles by saying "click"
 * (Web Speech API, Chrome/Edge) or by holding the cursor on a bubble (dwell, every browser).
 * Directions are calibrated from the visitor's own movement, like the real app.
 */

const VISION_WASM = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.17/wasm";
const FACE_MODEL =
  "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task";
const MODEL: MotionModel = { ...DEFAULT_MODEL, maxSpeed: 9 };
const DWELL_MS = 1100;
const BUBBLE_R = 34;
const CURSOR_R = 9;

type Phase =
  | "idle" | "loading" | "neutral" | "right" | "up" | "play"
  | "denied" | "nocamera" | "unsupported" | "error";

type Bubble = { id: number; x: number; y: number; born: number };

const PROMPTS: Partial<Record<Phase, string>> = {
  loading: "Starting the camera and face tracking…",
  neutral: "Look straight at the screen and keep still.",
  right: "Tilt your head toward your RIGHT shoulder and hold.",
  up: "Now lift your chin and look UP, and hold.",
};

// Minimal Web Speech API types (not in the TypeScript DOM lib)
type SpeechResultEvent = { resultIndex: number; results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal: boolean }> };
type Recognizer = {
  continuous: boolean; interimResults: boolean; lang: string;
  onresult: ((e: SpeechResultEvent) => void) | null; onend: (() => void) | null; onerror: ((e: { error: string }) => void) | null;
  start: () => void; stop: () => void;
};

/** Head pitch / roll in degrees from MediaPipe's 4x4 column-major transform. */
function headAngles(d: ArrayLike<number>) {
  const r00 = d[0], r10 = d[1], r21 = d[6], r22 = d[10];
  return { pitch: (Math.atan2(r21, r22) * 180) / Math.PI, roll: (Math.atan2(r10, r00) * 180) / Math.PI };
}
const wrap = (a: number) => ((((a + 180) % 360) + 360) % 360) - 180;

export function HeadDemo() {
  const [phase, setPhase] = useState<Phase>("idle");
  const [progress, setProgress] = useState(0);
  const [score, setScore] = useState(0);
  const [voice, setVoice] = useState<"off" | "on" | "unsupported">("off");
  const [heard, setHeard] = useState("");
  const [, force] = useState(0);

  const videoRef = useRef<HTMLVideoElement>(null);
  const areaRef = useRef<HTMLDivElement>(null);
  const cursorRef = useRef<HTMLDivElement>(null);
  const ringRef = useRef<HTMLDivElement>(null);

  // mutable engine state (kept out of React to run at 60 fps)
  const eng = useRef({
    stream: null as MediaStream | null,
    landmarker: null as FaceLandmarker | null,
    raf: 0,
    rec: null as Recognizer | null,
    alive: false,
    phase: "idle" as Phase,
    p0: 0, r0: 0, sx: 1, sy: 1, rangeX: 14, rangeY: 12,
    samples: [] as { p: number; r: number }[],
    holdSince: 0, extreme: 0,
    pf: 0, rf: 0, x: 0, y: 0, last: 0,
    bubbles: [] as Bubble[], nextId: 1, dwellId: 0, dwellSince: 0,
    lastVideoTime: -1, noFaceSince: 0,
  });

  const go = useCallback((p: Phase) => {
    eng.current.phase = p;
    eng.current.samples = [];
    eng.current.holdSince = 0;
    eng.current.extreme = 0;
    setProgress(0);
    setPhase(p);
  }, []);

  const spawn = useCallback(() => {
    const a = areaRef.current;
    const e = eng.current;
    if (!a) return;
    const w = a.clientWidth, h = a.clientHeight, m = BUBBLE_R + 16;
    for (let tries = 0; tries < 20; tries++) {
      const x = m + Math.random() * (w - 2 * m), y = m + Math.random() * (h - 2 * m);
      const far = Math.hypot(x - e.x, y - e.y) > 160 && e.bubbles.every((b) => Math.hypot(b.x - x, b.y - y) > 2.6 * BUBBLE_R);
      if (far || tries === 19) { e.bubbles.push({ id: e.nextId++, x, y, born: performance.now() }); break; }
    }
    force((n) => n + 1);
  }, []);

  const pop = useCallback((id: number) => {
    const e = eng.current;
    const before = e.bubbles.length;
    e.bubbles = e.bubbles.filter((b) => b.id !== id);
    if (e.bubbles.length === before) return;
    e.dwellId = 0;
    setScore((s) => s + 1);
    spawn();
  }, [spawn]);

  /** "click": pop the bubble under the cursor, if any. */
  const clickAtCursor = useCallback(() => {
    const e = eng.current;
    const hit = e.bubbles.find((b) => Math.hypot(b.x - e.x, b.y - e.y) <= BUBBLE_R + CURSOR_R);
    if (hit) pop(hit.id);
    if (ringRef.current) { ringRef.current.classList.remove("click"); void ringRef.current.offsetWidth; ringRef.current.classList.add("click"); }
  }, [pop]);

  const stopAll = useCallback(() => {
    const e = eng.current;
    e.alive = false;
    cancelAnimationFrame(e.raf);
    e.stream?.getTracks().forEach((t) => t.stop());
    e.stream = null;
    try { e.landmarker?.close(); } catch { /* already closed */ }
    e.landmarker = null;
    if (e.rec) { e.rec.onend = null; try { e.rec.stop(); } catch { /* not started */ } }
    e.rec = null;
  }, []);

  useEffect(() => stopAll, [stopAll]);

  const startVoice = useCallback(() => {
    const W = window as unknown as { SpeechRecognition?: new () => Recognizer; webkitSpeechRecognition?: new () => Recognizer };
    if (eng.current.rec) return;                       // already listening (e.g. after Recalibrate)
    const Ctor = W.SpeechRecognition ?? W.webkitSpeechRecognition;
    if (!Ctor) { setVoice("unsupported"); return; }
    const rec = new Ctor();
    rec.continuous = true; rec.interimResults = true; rec.lang = "en-US";
    let lastFire = 0;
    rec.onresult = (ev) => {
      for (let i = ev.resultIndex; i < ev.results.length; i++) {
        const text = ev.results[i][0].transcript.toLowerCase();
        setHeard(text.trim());
        if (/\b(click|clique|klick|quick)\b/.test(text) && performance.now() - lastFire > 700) {
          lastFire = performance.now();
          clickAtCursor();
        }
      }
    };
    rec.onerror = (ev) => { if (ev.error === "not-allowed" || ev.error === "service-not-allowed") setVoice("unsupported"); };
    rec.onend = () => { if (eng.current.alive && eng.current.rec === rec) { try { rec.start(); } catch { /* restarting */ } } };
    try { rec.start(); eng.current.rec = rec; setVoice("on"); } catch { setVoice("unsupported"); }
  }, [clickAtCursor]);

  const loop = useCallback(() => {
    const e = eng.current;
    if (!e.alive) return;
    e.raf = requestAnimationFrame(loop);
    const v = videoRef.current, lm = e.landmarker, area = areaRef.current;
    if (!v || !lm || !area || v.readyState < 2) return;
    const now = performance.now();
    if (v.currentTime === e.lastVideoTime) return;
    e.lastVideoTime = v.currentTime;

    let res;
    try { res = lm.detectForVideo(v, now); } catch { return; }
    const mtx = res.facialTransformationMatrixes?.[0]?.data;
    if (!mtx) { if (!e.noFaceSince) e.noFaceSince = now; return; }
    e.noFaceSince = 0;
    const { pitch, roll } = headAngles(mtx);

    if (e.phase === "neutral") {
      e.samples.push({ p: pitch, r: roll });
      setProgress(Math.min(1, e.samples.length / 45));
      if (e.samples.length >= 45) {
        e.p0 = e.samples.reduce((s, q) => s + q.p, 0) / e.samples.length;
        e.r0 = e.samples.reduce((s, q) => s + q.r, 0) / e.samples.length;
        go("right");
      }
      return;
    }
    const dp = wrap(pitch - e.p0), dr = wrap(roll - e.r0);

    if (e.phase === "right" || e.phase === "up") {
      const val = e.phase === "right" ? dr : dp;
      const need = e.phase === "right" ? 8 : 6;
      if (Math.abs(val) >= need) {
        if (!e.holdSince) e.holdSince = now;
        if (Math.abs(val) > Math.abs(e.extreme)) e.extreme = val;
        const held = (now - e.holdSince) / 700;
        setProgress(Math.min(1, held));
        if (held >= 1) {
          if (e.phase === "right") { e.sx = Math.sign(e.extreme) || 1; e.rangeX = clamp(Math.abs(e.extreme) * 0.8, 8, 30); go("up"); }
          else {
            e.sy = Math.sign(e.extreme) || 1; e.rangeY = clamp(Math.abs(e.extreme) * 0.8, 6, 25);
            e.x = area.clientWidth / 2; e.y = area.clientHeight / 2; e.pf = 0; e.rf = 0; e.last = now;
            e.bubbles = []; spawn(); spawn(); spawn();
            go("play"); startVoice();
          }
        }
      } else { e.holdSince = 0; setProgress(0); }
      return;
    }

    if (e.phase === "play") {
      // calibrated directions: + = right / up
      const tx = dr * e.sx, ty = dp * e.sy;
      e.rf += 0.35 * (tx - e.rf);
      e.pf += 0.35 * (ty - e.pf);
      const dt = Math.min(0.05, (now - (e.last || now)) / 1000); // seconds, capped after tab switches
      e.last = now;
      const k = dt / 0.015; // firmware reports every 15 ms
      const w = area.clientWidth, h = area.clientHeight;
      e.x = clamp(e.x + axisSpeed(e.rf, e.rangeX, MODEL) * k, CURSOR_R, w - CURSOR_R);
      e.y = clamp(e.y - axisSpeed(e.pf, e.rangeY, MODEL) * k, CURSOR_R, h - CURSOR_R);
      if (cursorRef.current) cursorRef.current.style.transform = `translate(${e.x}px, ${e.y}px)`;

      // dwell: hold the cursor on a bubble to pop it (works without voice)
      const over = e.bubbles.find((b) => Math.hypot(b.x - e.x, b.y - e.y) <= BUBBLE_R);
      if (over) {
        if (e.dwellId !== over.id) { e.dwellId = over.id; e.dwellSince = now; }
        const f = Math.min(1, (now - e.dwellSince) / DWELL_MS);
        ringRef.current?.style.setProperty("--dwell", String(f));
        if (f >= 1) pop(over.id);
      } else if (e.dwellId) { e.dwellId = 0; ringRef.current?.style.setProperty("--dwell", "0"); }
    }
  }, [go, pop, spawn, startVoice]);

  const start = useCallback(async () => {
    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) { setPhase("unsupported"); return; }
    stopAll();
    setScore(0); setHeard(""); setVoice("off");
    go("loading");
    const e = eng.current;
    try {
      e.stream = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" }, audio: false });
    } catch (err) {
      const name = (err as DOMException)?.name;
      setPhase(name === "NotAllowedError" || name === "SecurityError" ? "denied" : "nocamera");
      return;
    }
    try {
      const v = videoRef.current!;
      v.srcObject = e.stream;
      await v.play();
      const { FaceLandmarker, FilesetResolver } = await import("@mediapipe/tasks-vision");
      const files = await FilesetResolver.forVisionTasks(VISION_WASM);
      const make = (delegate: "GPU" | "CPU") => FaceLandmarker.createFromOptions(files, {
        baseOptions: { modelAssetPath: FACE_MODEL, delegate },
        runningMode: "VIDEO", numFaces: 1, outputFacialTransformationMatrixes: true,
      });
      e.landmarker = await make("GPU").catch(() => make("CPU"));
      e.alive = true; e.lastVideoTime = -1;
      go("neutral");
      e.raf = requestAnimationFrame(loop);
    } catch {
      stopAll();
      setPhase("error");
    }
  }, [go, loop, stopAll]);

  const stop = useCallback(() => { stopAll(); eng.current.bubbles = []; go("idle"); }, [go, stopAll]);

  const running = ["loading", "neutral", "right", "up", "play"].includes(phase);
  const failMsg: Partial<Record<Phase, string>> = {
    denied: "Camera permission was blocked. Allow the camera in your browser's address bar and try again.",
    nocamera: "No camera found, or it is used by another app. Close other apps using the camera and try again.",
    unsupported: "This browser can't use the camera here. Try Chrome or Edge on a computer.",
    error: "Face tracking could not start (it needs an internet connection the first time). Please try again.",
  };

  return (
    <div className="demo">
      <div className="demo-area" ref={areaRef} aria-live="polite">
        <video ref={videoRef} className={`demo-video${running ? " on" : ""}`} playsInline muted aria-hidden />

        {phase === "play" && eng.current.bubbles.map((b) => (
          <button key={b.id} className="bubble" style={{ left: b.x - BUBBLE_R, top: b.y - BUBBLE_R, width: BUBBLE_R * 2, height: BUBBLE_R * 2 }}
            onClick={() => pop(b.id)} aria-label="Bubble" />
        ))}
        {phase === "play" && (
          <div className="demo-cursor" ref={cursorRef} aria-hidden style={{ transform: `translate(${eng.current.x}px, ${eng.current.y}px)` }}>
            <div className="ring" ref={ringRef} />
          </div>
        )}

        {phase !== "play" && (
          <div className="demo-panel">
            {phase === "idle" && (<>
              <h3>Try iShara with your head</h3>
              <p className="muted">Your webcam stands in for the headband. Tilt your head to move, say <b>“click”</b> or hold still on a bubble to pop it.</p>
              <button className="btn btn-primary" onClick={start}>Start the demo</button>
              <p className="small muted">The camera stays on your device. Nothing is recorded or uploaded.</p>
            </>)}
            {(phase === "loading" || phase === "neutral" || phase === "right" || phase === "up") && (<>
              <div className="demo-step">{phase === "loading" ? "Starting" : phase === "neutral" ? "Step 1 of 3" : phase === "right" ? "Step 2 of 3" : "Step 3 of 3"}</div>
              <h3>{PROMPTS[phase]}</h3>
              <div className="demo-progress"><div style={{ width: `${Math.round(progress * 100)}%` }} /></div>
              <button className="btn btn-gray btn-sm" onClick={stop}>Cancel</button>
            </>)}
            {failMsg[phase] && (<>
              <h3>Camera not available</h3>
              <p className="muted">{failMsg[phase]}</p>
              <button className="btn btn-primary" onClick={start}>Try again</button>
            </>)}
          </div>
        )}
      </div>

      {phase === "play" && (
        <div className="demo-bar">
          <span className="demo-score">Popped <b>{score}</b></span>
          <span className="small muted">
            {voice === "on" ? <>Say <b>“click”</b>{heard ? <> · heard “{heard.slice(-28)}”</> : null}</>
              : voice === "unsupported" ? "Voice not available in this browser: hold still on a bubble"
              : "Starting voice…"}
          </span>
          <div className="row" style={{ gap: 8 }}>
            <button className="btn btn-gray btn-sm" onClick={() => go("neutral")}>Recalibrate</button>
            <button className="btn btn-gray btn-sm" onClick={stop}>Stop</button>
          </div>
        </div>
      )}
    </div>
  );
}
