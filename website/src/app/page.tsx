import Link from "next/link";
import { ExplodedView } from "@/components/ExplodedView";
import { HeadDemo } from "@/components/HeadDemo";
import { SignalStory } from "@/components/SignalStory";
import { Features } from "@/components/Features";
import { PlayWhenVisible } from "@/components/PlayWhenVisible";
import { Reveal } from "@/components/Reveal";
import { getRelease, isDownloadable } from "@/lib/release";


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
          <a href="#try" className="btn btn-gray">Try it with your head</a>
        </div>
        <p className="hero-meta">Windows 10 &amp; 11 · works offline · open source</p>
      </section>

      <section className="wrap section-tight" id="try" aria-labelledby="try-title">
        <div className="section-head center" style={{ textAlign: "center", marginBottom: 28 }}>
          <div className="eyebrow">Live demo</div>
          <h2 id="try-title">Try it now. No headband needed.</h2>
          <p className="lead center">Your webcam stands in for the headband. Same movement model, right in your browser.</p>
        </div>
        <div className="device-stage"><HeadDemo /></div>
      </section>

      <div className="band"><section className="wrap section">
        <Reveal anim="blur" className="section-head">
          <div className="eyebrow">What it does</div>
          <h2>Everything a mouse does.<br />No hands needed.</h2>
        </Reveal>
        <PlayWhenVisible><Features /></PlayWhenVisible>
      </section></div>

      <ExplodedView />

      <div className="band"><SignalStory /></div>

      <section className="wrap section">
        <Reveal anim="blur" className="section-head">
          <div className="eyebrow">Getting started</div>
          <h2>Ready in five minutes.</h2>
        </Reveal>
        <div className="steps">
          <Reveal anim="left" className="step"><div><h3>Install the app</h3><p>One installer, speech models included. It opens a spoken welcome guide.</p></div></Reveal>
          <Reveal anim="right" delay={60} className="step"><div><h3>Put on the headband</h3><p>Electronics on your forehead, snug. Pair “Ishara Mouse” over Bluetooth; it beeps once.</p></div></Reveal>
          <Reveal anim="left" delay={120} className="step"><div><h3>Practise and calibrate</h3><p>Short lessons, then look straight and tilt left, right, up and down. Both can be skipped.</p></div></Reveal>
          <Reveal anim="right" delay={180} className="step"><div><h3>Use your computer</h3><p>Move with your head, say “click”. Say “help” any time to see every command.</p></div></Reveal>
        </div>
      </section>

      <section className="wrap section">
        <Reveal anim="scale" className="cta">
          <h2>Try iShara.</h2>
          <p className="lead">Free and open source. Build the headband yourself, or request a ready-made one.</p>
          <div className="row">
            <Link href="/download" className="btn btn-primary">Download</Link>
            <Link href="/how-it-works" className="btn btn-gray">How it works</Link>
          </div>
        </Reveal>
      </section>
    </>
  );
}
