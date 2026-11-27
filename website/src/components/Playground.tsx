"use client";

import { useId, useMemo, useState } from "react";
import { DEFAULT_MODEL, responseCurve, type MotionModel } from "@/lib/motion";

const W = 520, H = 260, PAD = { l: 44, r: 16, t: 16, b: 38 };
const MAX_Y = 20;

/** Interactive version of the headband's movement model (same math as the firmware). */
export function Playground() {
  const [m, setM] = useState<MotionModel>(DEFAULT_MODEL);
  const id = useId();
  const pts = useMemo(() => responseCurve(m, 120), [m]);
  const x = (n: number) => PAD.l + (n / 1.2) * (W - PAD.l - PAD.r);
  const y = (s: number) => H - PAD.b - (Math.min(s, MAX_Y) / MAX_Y) * (H - PAD.t - PAD.b);
  const path = pts.map(([n, s], i) => `${i ? "L" : "M"}${x(n).toFixed(1)},${y(s).toFixed(1)}`).join(" ");
  const area = `${path} L${x(1.2)},${y(0)} L${x(0)},${y(0)} Z`;

  const slider = (key: keyof MotionModel, label: string, min: number, max: number, step: number, fmt: (v: number) => string, help: string) => (
    <div className="pg-field">
      <div className="pg-row"><label htmlFor={`${id}-${key}`}>{label}</label><output>{fmt(m[key])}</output></div>
      <input id={`${id}-${key}`} type="range" min={min} max={max} step={step} value={m[key]}
        onChange={(e) => setM({ ...m, [key]: Number(e.target.value) })} />
      <p className="small muted">{help}</p>
    </div>
  );

  return (
    <div className="pg">
      <div className="pg-controls">
        {slider("deadZone", "Dead zone", 0.05, 0.6, 0.01, (v) => `${Math.round(v * 100)}%`, "Tilt inside this share of your range is ignored.")}
        {slider("gamma", "Curve", 1, 3, 0.1, (v) => v.toFixed(1), "Higher = finer control near the centre.")}
        {slider("maxSpeed", "Top speed", 1, 20, 0.5, (v) => `${v} px`, "Pixels per 15 ms at your comfortable limit.")}
        <button className="btn btn-gray btn-sm" onClick={() => setM(DEFAULT_MODEL)}>Reset to defaults</button>
      </div>
      <svg className="pg-chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Cursor speed against head tilt">
        <rect x={x(0)} y={PAD.t} width={x(m.deadZone) - x(0)} height={H - PAD.t - PAD.b} fill="rgba(120,120,128,0.12)" />
        <line x1={x(1)} x2={x(1)} y1={PAD.t} y2={H - PAD.b} stroke="rgba(60,60,67,0.25)" strokeDasharray="4 4" />
        <line x1={PAD.l} x2={W - PAD.r} y1={y(0)} y2={y(0)} stroke="rgba(60,60,67,0.25)" />
        <line x1={PAD.l} x2={PAD.l} y1={PAD.t} y2={y(0)} stroke="rgba(60,60,67,0.25)" />
        <path d={area} fill="rgba(0,122,255,0.10)" />
        <path d={path} fill="none" stroke="#007aff" strokeWidth={2.5} strokeLinejoin="round" />
        <text x={x(m.deadZone / 2)} y={PAD.t + 14} textAnchor="middle" className="pg-t">dead zone</text>
        <text x={x(1)} y={PAD.t + 14} textAnchor="middle" className="pg-t">your limit</text>
        <text x={(W + PAD.l) / 2} y={H - 8} textAnchor="middle" className="pg-t">head tilt (share of your comfortable range)</text>
        <text x={14} y={(H - PAD.b + PAD.t) / 2} textAnchor="middle" className="pg-t" transform={`rotate(-90 14 ${(H - PAD.b + PAD.t) / 2})`}>cursor speed</text>
      </svg>
    </div>
  );
}
