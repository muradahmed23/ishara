"use client";

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";

type Anim = "up" | "scale" | "left" | "right" | "blur";

/**
 * Animates its children into view once, when they scroll into the viewport.
 * Content is visible without JavaScript (the hidden state only applies under html.js),
 * and prefers-reduced-motion turns the animation off (see globals.css).
 */
export function Reveal({
  children, anim = "up", delay = 0, className = "", style, as: Tag = "div",
}: { children: ReactNode; anim?: Anim; delay?: number; className?: string; style?: CSSProperties; as?: "div" | "section" | "li" }) {
  const ref = useRef<HTMLElement>(null);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => {
      if (e.isIntersecting) {
        el.classList.add("in");
        io.disconnect();
        // after the entrance, drop the stagger delay so hover effects respond instantly
        window.setTimeout(() => { el.style.transitionDelay = ""; }, delay + 800);
      }
    }, { rootMargin: "0px 0px -8% 0px", threshold: 0.12 });
    io.observe(el);
    return () => io.disconnect();
  }, [delay]);
  return (
    <Tag ref={ref as never} className={`reveal r-${anim} ${className}`} style={{ ...style, transitionDelay: delay ? `${delay}ms` : undefined }}>
      {children}
    </Tag>
  );
}
