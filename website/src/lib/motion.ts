/**
 * The iShara personal movement model, the same math as the headband firmware
 * (firmware/ishara_headband: axisSpeed) and desktop/ishara/model.py.
 *
 *   n = |tilt| / range            0 = straight, 1 = comfortable limit
 *   n < deadZone      -> 0        small involuntary movement is ignored
 *   u = (n - dz) / (1 - dz)       clamped 0..1
 *   speed = 1 + (max - 1) * u^gamma
 */
export type MotionModel = {
  deadZone: number; // 0.05..0.6
  gamma: number; // 1..3
  maxSpeed: number; // px per 15 ms report
};

export const DEFAULT_MODEL: MotionModel = { deadZone: 0.22, gamma: 1.6, maxSpeed: 6 };

export function axisSpeed(tilt: number, range: number, m: MotionModel): number {
  if (!Number.isFinite(tilt) || range <= 0) return 0;
  const n = Math.abs(tilt) / range;
  if (n < m.deadZone) return 0;
  const u = Math.min(1, Math.max(0, (n - m.deadZone) / (1 - m.deadZone)));
  const s = 1 + (m.maxSpeed - 1) * Math.pow(u, m.gamma);
  return tilt > 0 ? s : -s;
}

/** Response curve samples for charts: [n, speed] with n from 0 to 1.2. */
export function responseCurve(m: MotionModel, steps = 60): [number, number][] {
  const out: [number, number][] = [];
  for (let i = 0; i <= steps; i++) {
    const n = (i / steps) * 1.2;
    out.push([n, Math.abs(axisSpeed(n, 1, m))]);
  }
  return out;
}

export const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));
