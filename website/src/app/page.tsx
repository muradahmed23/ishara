import Link from "next/link";
import { DeviceIllustration } from "@/components/DeviceIllustration";
import { Icon } from "@/components/Icon";
import { getRelease, isDownloadable } from "@/lib/release";

const FEATURES = [
  ["head", "Head mouse", "Tilt your head to move the cursor. The headband is a real Bluetooth mouse, so it works the moment it connects."],
  ["mic", "Voice commands", "Click, double, right and middle click, scroll, drag, back and forward. Over 30 commands, all offline."],
  ["type", "Voice typing", "Say “start typing” and speak. iShara writes it down, with punctuation."],
  ["target", "Fits your head", "A guided, spoken calibration learns your range of movement and how the band sits on you."],
  ["lock", "Works everywhere", "Clicks come from the headband itself, so they work in protected windows like the On-Screen Keyboard."],
  ["wifiOff", "Private by design", "Everything runs on your computer. No internet, no account, nothing uploaded."],
] as const;

export default async function Home() {
  const release = await getRelease();
  const ready = isDownloadable(release);
  return (
    <>
      <section className="hero wrap">
        <div className="eyebrow">Hands-free computer control</div>
        <h1>Your head is the mouse.<br />Your voice does the rest.</h1>
        <p className="lead">
          iShara is a low-cost headband and Windows app for people who can&apos;t use their hands.
          Tilt to move the cursor, speak to click, scroll and type.
        </p>
        <div className="row">
          <Link href="/download" className="btn btn-primary">{ready ? `Download iShara ${release.version}` : "Get iShara"}</Link>
          <Link href="/hardware" className="btn btn-gray">Get the headband</Link>
        </div>
        <p className="hero-meta">Windows 10 &amp; 11 · works offline · open source</p>
      </section>

      <section className="wrap section-tight">
        <div className="device-stage"><div className="device"><DeviceIllustration /></div></div>
        <p className="center small muted" style={{ marginTop: 14, maxWidth: 560 }}>
          The current prototype: an ESP32 board, an MPU6050 motion sensor and a rechargeable battery on a foam headband.
        </p>
      </section>

      <div className="band"><section className="wrap section">
        <div className="section-head">
          <div className="eyebrow">What it does</div>
          <h2>Everything a mouse does.<br />No hands needed.</h2>
        </div>
        <div className="grid g3">
          {FEATURES.map(([icon, title, text]) => (
            <div className="card" key={title}>
              <div className="icon"><Icon name={icon} /></div>
              <h3>{title}</h3>
              <p>{text}</p>
            </div>
          ))}
        </div>
      </section></div>

      <section className="wrap section">
        <div className="section-head">
          <div className="eyebrow">Getting started</div>
          <h2>Ready in five minutes.</h2>
        </div>
        <div className="steps">
          <div className="step"><div><h3>Install the app</h3><p>One installer, speech models included. It opens a spoken welcome guide.</p></div></div>
          <div className="step"><div><h3>Put on the headband</h3><p>Electronics on your forehead, snug. Pair “Ishara Mouse” over Bluetooth; it beeps once.</p></div></div>
          <div className="step"><div><h3>Calibrate</h3><p>Look straight, then tilt left, right, up and down. iShara learns your movement.</p></div></div>
          <div className="step"><div><h3>Use your computer</h3><p>Move with your head, say “click”. Say “help” any time to see every command.</p></div></div>
        </div>
      </section>

      <section className="wrap section">
        <div className="cta">
          <h2>Try iShara.</h2>
          <p className="lead">Free and open source. Build the headband yourself, or request a ready-made one.</p>
          <div className="row">
            <Link href="/download" className="btn btn-primary">Download</Link>
            <Link href="/how-it-works" className="btn btn-gray">How it works</Link>
          </div>
        </div>
      </section>
    </>
  );
}
