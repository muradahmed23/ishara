import type { Metadata } from "next";
import { DownloadCard } from "@/components/DownloadCard";
import { getRelease } from "@/lib/release";

export const metadata: Metadata = { title: "Download", description: "Download iShara for Windows: one complete offline installer." };

export default async function DownloadPage() {
  const r = await getRelease();
  return (
    <>
      <section className="wrap section-tight" style={{ paddingTop: 72 }}>
        <div className="eyebrow">Download</div>
        <h2>iShara for Windows</h2>
        <p className="lead" style={{ margin: "14px 0 32px" }}>One installer with everything included. Press Install, and the welcome guide takes it from there.</p>
        <DownloadCard release={r} />
      </section>

      <section className="wrap section-tight">
        <div className="grid g2">
          <div>
            <h3 style={{ marginBottom: 14 }}>What happens when you install</h3>
            <div className="steps">
              <div className="step"><div><h3>Open the installer, press Install</h3><p>No administrator rights needed (you can choose “all users” if you prefer).</p></div></div>
              <div className="step"><div><h3>Everything is set up</h3><p>App, runtime and speech models. Start menu and desktop shortcuts are created.</p></div></div>
              <div className="step"><div><h3>iShara starts</h3><p>A spoken welcome guide checks the microphone, connects the headband and calibrates.</p></div></div>
            </div>
          </div>
          <div>
            <h3 style={{ marginBottom: 14 }}>Requirements</h3>
            <div className="list">
              <div className="li"><span>System</span><span>{r.requirements.os}</span></div>
              <div className="li"><span>Bluetooth</span><span>{r.requirements.bluetooth}</span></div>
              <div className="li"><span>Microphone</span><span>Built-in or headset</span></div>
              <div className="li"><span>Disk space</span><span>{(r.requirements.diskSpaceMB / 1000).toFixed(1)} GB</span></div>
              <div className="li"><span>Internet</span><span>Not needed after download</span></div>
            </div>
            <h3 style={{ margin: "28px 0 14px" }}>Included speech models</h3>
            <div className="list">
              {r.models.items.map((m) => <div className="li" key={m.name}><span>{m.purpose}</span><span className="mono">{m.name}</span></div>)}
            </div>
          </div>
        </div>
      </section>

      <section className="wrap section-tight">
        <h3 style={{ marginBottom: 14 }}>What&apos;s new in {r.version}</h3>
        <div className="list">{r.notes.map((n) => <div className="li" key={n}><span>{n}</span></div>)}</div>
        <p className="small muted" style={{ marginTop: 14 }}>
          Updates: open iShara → About → Check for updates. Your profiles and calibration are always kept.
        </p>
      </section>
    </>
  );
}
