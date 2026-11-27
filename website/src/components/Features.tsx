import { Reveal } from "./Reveal";

/* "Everything a mouse does": a bento grid, each card with its own small CSS animation. */

function HeadMouseArt() {
  return (
    <div className="art art-head" aria-hidden>
      <svg viewBox="0 0 200 120" className="head-svg">
        <g className="head-tilt">
          <circle cx="60" cy="52" r="24" fill="#fff" stroke="#1d1d1f" strokeWidth="2.5" />
          <rect x="44" y="34" width="32" height="10" rx="3" fill="#1d1d1f" />
          <rect x="52" y="36" width="10" height="6" rx="1.5" fill="#2a5db0" />
          <path d="M36 102c4-14 13-22 24-22s20 8 24 22" fill="none" stroke="#1d1d1f" strokeWidth="2.5" strokeLinecap="round" />
        </g>
        <rect x="110" y="18" width="80" height="62" rx="8" fill="#fff" stroke="rgba(60,60,67,.2)" />
        <rect x="110" y="18" width="80" height="10" rx="5" fill="rgba(120,120,128,.12)" />
        <g className="head-cursor"><path d="M0 0 10 6 5 7 3 12z" fill="#007aff" stroke="#fff" strokeWidth="1" /></g>
      </svg>
    </div>
  );
}

function VoiceArt() {
  return (
    <div className="art art-voice" aria-hidden>
      <div className="wave">{Array.from({ length: 14 }).map((_, i) => <i key={i} style={{ animationDelay: `${(i % 7) * 0.09}s` }} />)}</div>
      <div className="cycle">
        <span>“click”</span><span>“scroll down”</span><span>“right click”</span>
      </div>
    </div>
  );
}

function TypingArt() {
  const words = ["Hello,", "this", "was", "typed", "by", "voice."];
  return (
    <div className="art art-type" aria-hidden>
      <div className="doc">
        {words.map((w, i) => <span key={w} style={{ animationDelay: `${0.35 * i}s` }}>{w} </span>)}
        <b className="caret" />
      </div>
    </div>
  );
}

function CalibrateArt() {
  return (
    <div className="art art-cal" aria-hidden>
      <div className="rings"><i /><i /><i /></div>
      <div className="dot" />
    </div>
  );
}

function KeyboardArt() {
  const rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"];
  return (
    <div className="art art-kbd" aria-hidden>
      {rows.map((r, ri) => (
        <div className="krow" key={r}>
          {r.split("").map((k, ki) => (
            <span key={k} className={(ri === 0 && ki === 3) || (ri === 1 && ki === 6) || (ri === 2 && ki === 4) ? `press p${ri}` : ""}>{k}</span>
          ))}
        </div>
      ))}
    </div>
  );
}

export function Features() {
  return (
    <div className="bento">
      <Reveal anim="up" className="bcard b-wide">
        <HeadMouseArt />
        <div className="btext"><h3>Head mouse</h3><p>Tilt your head to move the cursor. The headband is a real Bluetooth mouse: it works the moment it connects.</p></div>
      </Reveal>
      <Reveal anim="up" delay={80} className="bcard">
        <VoiceArt />
        <div className="btext"><h3>Voice commands</h3><p>Click, double, right and middle click, scroll, drag, back and forward. 30+ commands, offline.</p></div>
      </Reveal>
      <Reveal anim="scale" className="bcard">
        <TypingArt />
        <div className="btext"><h3>Voice typing</h3><p>Say “start typing” and speak. iShara writes it, with punctuation.</p></div>
      </Reveal>
      <Reveal anim="scale" delay={80} className="bcard">
        <CalibrateArt />
        <div className="btext"><h3>Fits your head</h3><p>A spoken calibration learns your range of movement and your straight-ahead position.</p></div>
      </Reveal>
      <Reveal anim="scale" delay={160} className="bcard">
        <KeyboardArt />
        <div className="btext"><h3>Works everywhere</h3><p>Clicks come from the headband itself, so they even work on the On-Screen Keyboard.</p></div>
      </Reveal>
      <Reveal anim="up" className="bcard b-full b-dark">
        <div className="bstats">
          <div><b>0</b><span>bytes uploaded</span></div>
          <div><b>15 ms</b><span>movement updates</span></div>
          <div><b>30+</b><span>voice commands</span></div>
          <div><b>100%</b><span>offline</span></div>
        </div>
        <div className="btext"><h3>Private by design</h3><p>Speech recognition and everything else run on your own computer. No account, no internet needed.</p></div>
      </Reveal>
    </div>
  );
}
