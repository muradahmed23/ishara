import type { Metadata } from "next";

export const metadata: Metadata = { title: "Guide", description: "Install, wear, connect, calibrate and troubleshoot iShara." };

const GUIDE: [string, string[]][] = [
  ["Install iShara", ["Download the installer from the Download page and open it.", "Press Install. The app, runtime and speech models are all included.", "iShara starts automatically and opens the welcome guide."]],
  ["Wear the headband", ["Place the electronics on your forehead, sensor board facing outwards.", "Make the band snug so it can't slide.", "Keep the wires tucked in."]],
  ["Connect over Bluetooth", ["Switch the headband on (charge via USB-C first if needed).", "Windows Settings → Bluetooth & devices → Add device → Bluetooth → Ishara Mouse.", "It beeps once when connected. You only pair once."]],
  ["Calibrate", ["In the app: Training → Calibration.", "Look straight, then tilt left, right, up and down. Hold each until you hear “Got it”.", "Recalibrate if the band moves or another person uses it."]],
  ["Adjust speed and steadiness", ["Settings → Movement: Speed (faster or slower).", "Dead zone: bigger if the cursor drifts when you hold still.", "Smoothing: lower is steadier, higher reacts faster."]],
  ["Click, scroll and drag", ["Point with your head, say “click”, “right click”, “double click” or “middle click”.", "Say “scroll up” / “scroll down”.", "Say “start drag”, move, then “release”."]],
  ["Type with your voice", ["Say “start typing”, then speak.", "Say “comma”, “period”, “new line”, “delete that”.", "Say “stop typing” to return to commands."]],
  ["Pause and emergency stop", ["“pause” / “resume” freezes and restarts the cursor.", "“stop control” stops immediately in an emergency.", "“hand mouse” lets you use a normal mouse; “head mouse” switches back."]],
  ["Microphone not working", ["If the status says Muted, say “start listening”.", "Pick the right microphone: Settings → Voice → Input device.", "Windows Settings → Privacy → Microphone: allow desktop apps."]],
  ["Bluetooth keeps disconnecting", ["Stay within a few metres of the computer; check the battery.", "Remove “Ishara Mouse” in Windows Bluetooth settings and add it again.", "If Bluetooth is connected but the cursor doesn't move, check the sensor wires (Help → Your headband shows the sensor status)."]],
  ["Profiles", ["Profiles → type a name → Add. Each person has their own calibration.", "Switch, then calibrate for the new person."]],
  ["Update iShara", ["About → Check for updates → Download → Install.", "Downloads are verified (SHA-256) before they run.", "Profiles, calibration and settings are always kept."]],
];

export default function Guide() {
  return (
    <section className="wrap section-tight" style={{ paddingTop: 72 }}>
      <div className="eyebrow">Guide</div>
      <h2>Getting started &amp; troubleshooting</h2>
      <p className="lead" style={{ margin: "14px 0 32px" }}>The same guides are inside the app (Help page), with a Read aloud button on every topic.</p>
      {GUIDE.map(([t, steps], i) => (
        <details className="q" key={t} open={i === 0}>
          <summary>{t}</summary>
          <div className="body"><ol>{steps.map((s) => <li key={s}>{s}</li>)}</ol></div>
        </details>
      ))}
    </section>
  );
}
