import type { Metadata } from "next";
import { Playground } from "@/components/Playground";
import { Reveal } from "@/components/Reveal";

export const metadata: Metadata = { title: "How it works", description: "How iShara turns head movement and voice into mouse control." };

const PARTS = [
  ["1. The headband measures tilt", "An MPU6050 motion sensor on your forehead measures how your head tilts, relative to your own straight-ahead position captured at calibration. The angle the band sits at doesn't matter."],
  ["2. The headband moves the cursor", "The ESP32 turns tilt into cursor speed with your personal settings: a dead zone ignores small involuntary movements, a gentle curve gives fine control near the centre. It sends this as a standard Bluetooth mouse, every 15 ms."],
  ["3. The app listens", "The Windows app recognises voice commands offline (Vosk) and turns speech into text for typing (Whisper). Nothing leaves your computer."],
  ["4. The headband clicks", "When you say “click”, the app asks the headband to click. Because it is a real hardware click, it works even in windows that block software clicks, like the On-Screen Keyboard."],
  ["5. It learns you", "A spoken calibration measures how far you can comfortably move in each direction and detects how the sensor is mounted, so the cursor always follows your head."],
] as const;

export default function HowItWorks() {
  return (
    <>
      <section className="wrap section-tight" style={{ paddingTop: 72 }}>
        <div className="eyebrow">How it works</div>
        <h2>Head movement on the headband.<br />Voice on your computer.</h2>
        <p className="lead" style={{ marginTop: 14 }}>The cursor runs on the headband for the fastest response. The app adds voice, calibration, training and profiles.</p>
      </section>
      <section className="wrap section-tight">
        <div className="grid g2">
          {PARTS.map(([t, d], i) => <Reveal key={t} anim={i % 2 ? "right" : "left"} delay={(i % 2) * 80} className="card"><h3>{t}</h3><p>{d}</p></Reveal>)}
          <Reveal anim="right" delay={80} className="card">
            <h3>Built for real people</h3>
            <p>Each person gets a profile with their own calibration and settings. Seven practice lessons build confidence step by step, and every action is spoken aloud.</p>
          </Reveal>
        </div>
      </section>
      <section className="wrap section-tight" aria-labelledby="pg-title">
        <h3 id="pg-title" style={{ marginBottom: 6 }}>Play with the movement model</h3>
        <p className="muted" style={{ marginBottom: 18 }}>These are the settings calibration tunes for each person. Same math as the headband firmware.</p>
        <Playground />
      </section>
      <section className="wrap section-tight">
        <h3 style={{ marginBottom: 14 }}>Voice commands</h3>
        <div className="list">
          {[
            ["Mouse", "click · double click · right click · middle click · scroll up · scroll down · start drag · release · click lock · go back · go forward"],
            ["Control", "pause · resume · stop control · hand mouse · head mouse · center · find cursor · keyboard"],
            ["Typing", "start typing · stop typing · comma · period · new line · delete that"],
            ["Help", "help, then say a number · more · back · close"],
          ].map(([g, c]) => <div className="li" key={g}><span><b>{g}</b></span><span>{c}</span></div>)}
        </div>
      </section>
    </>
  );
}
