import type { Metadata } from "next";
import { DeviceIllustration } from "@/components/DeviceIllustration";
import { OrderForm } from "@/components/OrderForm";
import { billOfMaterials, kits, wiring } from "@/config/hardware";
import { site } from "@/config/site";

export const metadata: Metadata = { title: "Hardware", description: "The iShara headband: parts, wiring, and how to get one." };

function orderMode() {
  if (process.env.ORDER_EMAIL_TO && process.env.RESEND_API_KEY) return { mode: "server" as const, mailto: null };
  if (process.env.NEXT_PUBLIC_ORDER_EMAIL) return { mode: "mailto" as const, mailto: process.env.NEXT_PUBLIC_ORDER_EMAIL };
  return { mode: "closed" as const, mailto: null };
}

export default function HardwarePage() {
  const { mode, mailto } = orderMode();
  return (
    <>
      <section className="wrap section-tight" style={{ paddingTop: 72 }}>
        <div className="eyebrow">Hardware</div>
        <h2>The iShara headband</h2>
        <p className="lead" style={{ margin: "14px 0 32px" }}>
          An early working prototype: off-the-shelf electronics on a foam headband, worn on the forehead.
          It acts as a standard Bluetooth mouse.
        </p>
        <div className="device-stage"><div className="device"><DeviceIllustration /></div></div>
      </section>

      <section className="wrap section-tight">
        <div className="grid g2">
          <div>
            <h3 style={{ marginBottom: 14 }}>Parts</h3>
            <div className="list">{billOfMaterials.map(([a, b]) => <div className="li" key={a}><span>{a}</span><span>{b}</span></div>)}</div>
          </div>
          <div>
            <h3 style={{ marginBottom: 14 }}>Wiring: MPU6050 → ESP32</h3>
            <div className="list">{wiring.map(([a, b]) => <div className="li" key={a}><span>{a}</span><span>{b}</span></div>)}</div>
            <p className="small muted" style={{ marginTop: 12 }}>Buzzer + → D26, − → GND. Firmware and full guide on <a href={site.github} style={{ color: "var(--blue)" }}>GitHub</a>.</p>
            <h3 style={{ margin: "28px 0 10px" }}>Good to know</h3>
            <ul className="muted" style={{ marginLeft: 20, display: "grid", gap: 6 }}>
              <li>Mounting angle doesn&apos;t matter: calibration learns it.</li>
              <li>Left/right = tilting toward the shoulder.</li>
              <li>USB-C is for charging and firmware updates.</li>
              <li>This prototype does not report battery level.</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="wrap section" id="order">
        <div className="section-head">
          <div className="eyebrow">Order</div>
          <h2>Get a headband</h2>
          <p className="lead">Request an assembled headband or a DIY parts kit. We reply with price and delivery. No payment now.</p>
        </div>
        <OrderForm kits={kits} mode={mode} mailto={mailto} />
      </section>
    </>
  );
}
