"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";

const Headband3D = dynamic(() => import("./Headband3D"), {
  ssr: false,
  loading: () => <div className="xv-loading">Loading 3D model…</div>,
});

const smooth = (a: number, b: number, x: number) => {
  const t = Math.min(1, Math.max(0, (x - a) / (b - a)));
  return t * t * (3 - 2 * t);
};

function webglAvailable() {
  try {
    const c = document.createElement("canvas");
    return !!(window.WebGLRenderingContext && (c.getContext("webgl2") || c.getContext("webgl")));
  } catch {
    return false;
  }
}

/** Scroll-driven exploded view of the real headband. */
export function ExplodedView() {
  const section = useRef<HTMLElement>(null);
  const explode = useRef(0);
  const [near, setNear] = useState(false);
  const [visible, setVisible] = useState(false); // render 3D only while on screen
  const [gl, setGl] = useState(true);
  const [manual, setManual] = useState<null | 0 | 1>(null);
  const [reduce, setReduce] = useState(false);
  const [exploded, setExploded] = useState(false);
  const manualRef = useRef<null | 0 | 1>(null);
  manualRef.current = manual;

  useEffect(() => {
    setGl(webglAvailable());
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReduce(mq.matches);
    const onMq = () => setReduce(mq.matches);
    mq.addEventListener("change", onMq);
    const io = new IntersectionObserver(([e]) => { if (e.isIntersecting) setNear(true); }, { rootMargin: "600px 0px" });
    const vis = new IntersectionObserver(([e]) => setVisible(e.isIntersecting), { rootMargin: "50px 0px" });
    if (section.current) { io.observe(section.current); vis.observe(section.current); }
    return () => { io.disconnect(); vis.disconnect(); mq.removeEventListener("change", onMq); };
  }, []);

  const visibleRef = useRef(false);
  visibleRef.current = visible;
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      raf = requestAnimationFrame(tick);
      const el = section.current;
      if (!el || !visibleRef.current) return;        // no layout reads while scrolled away
      let target: number;
      if (manualRef.current !== null) target = manualRef.current;
      else {
        const r = el.getBoundingClientRect();
        const span = Math.max(1, r.height - window.innerHeight);
        target = smooth(0.12, 0.7, -r.top / span);
      }
      explode.current += (target - explode.current) * (reduce ? 1 : 0.12);
      const now = explode.current > 0.5;
      setExploded((prev) => (prev === now ? prev : now));
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [reduce]);

  return (
    <section ref={section} className="xv" aria-labelledby="xv-title">
      <div className="xv-sticky">
        <div className="wrap xv-grid">
          <div className="xv-text">
            <div className="eyebrow">Inside the headband</div>
            <h2 id="xv-title">Five parts.<br />One hands-free mouse.</h2>
            <p className="lead">
              Off-the-shelf electronics on a foam headband. Scroll to take it apart, or drag to turn it.
            </p>
            <ul className="xv-list">
              <li><b>MPU6050</b> measures how your head tilts</li>
              <li><b>ESP32</b> turns tilt into cursor movement and is a Bluetooth mouse</li>
              <li><b>Li-Po battery</b> + <b>USB-C charger</b> for a day of use</li>
              <li><b>Buzzer</b> beeps once when it connects</li>
            </ul>
            <button className="btn btn-gray btn-sm" onClick={() => setManual(exploded ? 0 : 1)}>
              {exploded ? "Put it back together" : "Take it apart"}
            </button>
          </div>
          <div className="xv-canvas">
            {!gl ? (
              <div className="xv-loading">3D needs WebGL, which this browser has turned off.</div>
            ) : near ? (
              <Headband3D explode={explode} reduceMotion={reduce} active={visible} />
            ) : (
              <div className="xv-loading" />
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
