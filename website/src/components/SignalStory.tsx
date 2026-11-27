"use client";

import { useEffect, useRef, useState } from "react";
import { axisSpeed, DEFAULT_MODEL } from "@/lib/motion";

const STEPS = [
  { t: "Your head tilts", d: "The MPU6050 on your forehead feels gravity shift as you tilt toward a shoulder or lift your chin." },
  { t: "Small movements are ignored", d: "Inside the dead zone (grey band) nothing happens, so a tired or shaky head doesn't move the cursor." },
  { t: "Bigger tilt, faster cursor", d: "Past the dead zone, speed follows a gentle curve: fine control near the centre, quick across the screen." },
  { t: "Sent as a real mouse", d: "The ESP32 sends the movement over Bluetooth every 15 ms. Windows sees an ordinary mouse." },
];

const RANGE = 15;
// a natural-looking head path: slow, mixed tilts with pauses
const pitchAt = (t: number) => 14 * Math.sin(t * 0.55) * Math.max(0, Math.sin(t * 0.21 + 1)) + 2 * Math.sin(t * 2.3);
const rollAt = (t: number) => 17 * Math.sin(t * 0.43 + 0.8) * Math.max(0, Math.cos(t * 0.17)) + 1.5 * Math.sin(t * 2.9);

export function SignalStory() {
  const box = useRef<HTMLDivElement>(null);
  const scope = useRef<HTMLCanvasElement>(null);
  const screen = useRef<HTMLCanvasElement>(null);
  const stepRefs = useRef<(HTMLLIElement | null)[]>([]);
  const [active, setActive] = useState(0);

  // highlight the step in the middle of the viewport
  useEffect(() => {
    const io = new IntersectionObserver(
      (entries) => entries.forEach((e) => { if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.i)); }),
      { rootMargin: "-45% 0px -45% 0px" },
    );
    stepRefs.current.forEach((el) => el && io.observe(el));
    return () => io.disconnect();
  }, []);

  useEffect(() => {
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0, visible = false, t = 8;
    const cur = { x: 0.5, y: 0.5 };
    const trail: { x: number; y: number }[] = [];
    const io = new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { rootMargin: "100px" });
    if (box.current) io.observe(box.current);

    const fit = (c: HTMLCanvasElement) => {
      const dpr = window.devicePixelRatio || 1, w = c.clientWidth, h = c.clientHeight;
      if (c.width !== Math.round(w * dpr)) { c.width = Math.round(w * dpr); c.height = Math.round(h * dpr); }
      const g = c.getContext("2d")!;
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      return { g, w, h };
    };

    const draw = () => {
      const sc = scope.current, sr = screen.current;
      if (!sc || !sr) return;
      // --- scope: pitch / roll over the last 8 s with the dead zone band
      const { g, w, h } = fit(sc);
      g.clearRect(0, 0, w, h);
      const mid = h / 2, k = (h / 2 - 12) / 22;
      const dz = DEFAULT_MODEL.deadZone * RANGE * k;
      g.fillStyle = "rgba(120,120,128,0.12)";
      g.fillRect(0, mid - dz, w, dz * 2);
      g.strokeStyle = "rgba(60,60,67,0.15)"; g.lineWidth = 1;
      g.beginPath(); g.moveTo(0, mid); g.lineTo(w, mid); g.stroke();
      const plot = (fn: (x: number) => number, color: string) => {
        g.strokeStyle = color; g.lineWidth = 2.2; g.lineJoin = "round"; g.beginPath();
        for (let px = 0; px <= w; px += 3) {
          const tt = t - 8 + (px / w) * 8;
          const y = mid - fn(tt) * k;
          if (px === 0) { g.moveTo(px, y); } else { g.lineTo(px, y); }
        }
        g.stroke();
      };
      plot(pitchAt, "#007aff");
      plot(rollAt, "#34c759");
      g.font = "600 11px Inter, system-ui, sans-serif";
      g.fillStyle = "#007aff"; g.fillText("pitch (up / down)", 10, 16);
      g.fillStyle = "#34c759"; g.fillText("roll (left / right)", 10, 31);
      g.fillStyle = "#6e6e73"; g.fillText("dead zone", w - 70, mid - dz - 6);

      // --- screen: the resulting cursor
      const s = fit(sr);
      s.g.clearRect(0, 0, s.w, s.h);
      const dx = axisSpeed(rollAt(t), RANGE, DEFAULT_MODEL), dy = -axisSpeed(pitchAt(t), RANGE, DEFAULT_MODEL);
      cur.x = Math.min(0.96, Math.max(0.04, cur.x + dx * 0.0022));
      cur.y = Math.min(0.94, Math.max(0.06, cur.y + dy * 0.0026));
      trail.push({ ...cur });
      if (trail.length > 120) trail.shift();
      s.g.lineWidth = 2; s.g.lineCap = "round";
      for (let i = 1; i < trail.length; i++) {
        s.g.strokeStyle = `rgba(0,122,255,${(i / trail.length) * 0.5})`;
        s.g.beginPath(); s.g.moveTo(trail[i - 1].x * s.w, trail[i - 1].y * s.h); s.g.lineTo(trail[i].x * s.w, trail[i].y * s.h); s.g.stroke();
      }
      const cx = cur.x * s.w, cy = cur.y * s.h;
      s.g.fillStyle = "#1d1d1f";
      s.g.beginPath(); s.g.moveTo(cx, cy); s.g.lineTo(cx + 13, cy + 7); s.g.lineTo(cx + 6, cy + 9); s.g.lineTo(cx + 3, cy + 16); s.g.closePath(); s.g.fill();
      s.g.strokeStyle = "#fff"; s.g.lineWidth = 1.2; s.g.stroke();
    };

    let last = performance.now();
    const loop = (now: number) => {
      raf = requestAnimationFrame(loop);
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      if (!visible) return;
      if (!reduce) t += dt;
      draw();
    };
    raf = requestAnimationFrame(loop);
    draw();
    return () => { cancelAnimationFrame(raf); io.disconnect(); };
  }, []);

  return (
    <section className="wrap section story" aria-labelledby="story-title">
      <div className="section-head">
        <div className="eyebrow">From tilt to cursor</div>
        <h2 id="story-title">What the headband sees.</h2>
        <p className="lead">This is the real movement model from the iShara firmware, running live in your browser.</p>
      </div>
      <div className="story-grid">
        <div className="story-sticky" ref={box}>
          <div className="scope-card">
            <div className="scope-title">MPU6050 tilt, last 8 seconds</div>
            <canvas ref={scope} className="scope" aria-label="Live graph of head pitch and roll" />
            <div className="scope-title">Cursor on screen</div>
            <canvas ref={screen} className="scope screen" aria-label="Resulting cursor movement" />
          </div>
        </div>
        <ol className="story-steps">
          {STEPS.map((s, i) => (
            <li key={s.t} data-i={i} ref={(el) => { stepRefs.current[i] = el; }} className={i === active ? "on" : ""}>
              <span className="story-num">{i + 1}</span>
              <div><h3>{s.t}</h3><p>{s.d}</p></div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  );
}
