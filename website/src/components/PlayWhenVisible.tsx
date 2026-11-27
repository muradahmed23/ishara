"use client";

import { useEffect, useRef, type ReactNode } from "react";

/** Runs the CSS animations inside only while on screen (class "playing"); paused otherwise. */
export function PlayWhenVisible({ children, className = "" }: { children: ReactNode; className?: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => el.classList.toggle("playing", e.isIntersecting), { rootMargin: "100px 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return <div ref={ref} className={`pause-offscreen ${className}`}>{children}</div>;
}
