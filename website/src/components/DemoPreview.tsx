/* Animated "attract mode" behind the demo's start panel: a cursor glides between bubbles
   and pops them, while a head tilts, so the section feels alive before the camera starts. */
import { PlayWhenVisible } from "./PlayWhenVisible";

export function DemoPreview() {
  return (
    <PlayWhenVisible className="preview">
    <div aria-hidden>
      <i className="pb b1" /><i className="pb b2" /><i className="pb b3" /><i className="pb b4" />
      <div className="pcursor"><span /></div>
      <svg className="phead" viewBox="0 0 80 80">
        <g className="phead-tilt">
          <circle cx="40" cy="32" r="18" fill="#fff" stroke="#1d1d1f" strokeWidth="2" />
          <rect x="28" y="19" width="24" height="7" rx="2" fill="#1d1d1f" />
          <path d="M20 74c3-11 10-17 20-17s17 6 20 17" fill="none" stroke="#1d1d1f" strokeWidth="2" strokeLinecap="round" />
        </g>
      </svg>
    </div>
    </PlayWhenVisible>
  );
}
