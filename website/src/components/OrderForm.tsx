"use client";

import { useState } from "react";
import type { Kit } from "@/config/hardware";

type Mode = "server" | "mailto" | "closed";

/** Hardware order request. Delivery channel is chosen by env vars (see README). */
export function OrderForm({ kits, mode, mailto }: { kits: Kit[]; mode: Mode; mailto: string | null }) {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [error, setError] = useState("");

  if (mode === "closed") {
    return <div className="notice">Ordering opens soon. In the meantime the full parts list and wiring are above, and everything is open source.</div>;
  }

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = Object.fromEntries(new FormData(e.currentTarget)) as Record<string, string>;
    const kit = kits.find((k) => k.id === data.kit)?.name ?? data.kit;
    if (mode === "mailto" && mailto) {
      const body = `Kit: ${kit}\nQuantity: ${data.quantity}\nName: ${data.name}\nEmail: ${data.email}\nCountry / city: ${data.location}\n\n${data.message}`;
      window.location.href = `mailto:${mailto}?subject=${encodeURIComponent("iShara order request: " + kit)}&body=${encodeURIComponent(body)}`;
      setState("sent");
      return;
    }
    setState("sending");
    try {
      const r = await fetch("/api/order", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) });
      const j = await r.json();
      if (!r.ok) throw new Error(j.error || "Could not send");
      setState("sent");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send");
      setState("error");
    }
  }

  if (state === "sent") {
    return <div className="notice ok" role="status"><b>Thank you.</b> {mode === "mailto" ? "Your email app opened with the request. Press send there." : "We received your request and will reply by email with price and delivery."}</div>;
  }

  return (
    <form className="form" onSubmit={submit}>
      <fieldset className="kits" style={{ border: 0 }}>
        <legend className="small muted" style={{ marginBottom: 8 }}>Choose a kit</legend>
        {kits.filter((k) => k.available).map((k, i) => (
          <label key={k.id} className="kit">
            <input type="radio" name="kit" value={k.id} defaultChecked={i === 0} required />
            <h3>{k.name}</h3>
            <p className="muted small" style={{ marginTop: 4 }}>{k.summary}</p>
            <ul>{k.includes.map((x) => <li key={x}>{x}</li>)}</ul>
            <div className="price">{k.price ?? "Price on request"}</div>
          </label>
        ))}
      </fieldset>
      <div className="grid g2">
        <div className="field"><label htmlFor="o-name">Name</label><input id="o-name" className="input" name="name" required maxLength={80} autoComplete="name" /></div>
        <div className="field"><label htmlFor="o-email">Email</label><input id="o-email" className="input" name="email" type="email" required maxLength={120} autoComplete="email" /></div>
        <div className="field"><label htmlFor="o-loc">Country / city</label><input id="o-loc" className="input" name="location" required maxLength={80} /></div>
        <div className="field"><label htmlFor="o-qty">Quantity</label><input id="o-qty" className="input" name="quantity" type="number" min={1} max={50} defaultValue={1} required /></div>
      </div>
      <div className="field"><label htmlFor="o-msg">Anything we should know? (optional)</label><textarea id="o-msg" className="input" name="message" maxLength={1000} placeholder="For example: who will use it, special needs, delivery time" /></div>
      <input type="text" name="website" tabIndex={-1} autoComplete="off" style={{ display: "none" }} aria-hidden />
      {state === "error" && <div className="notice err" role="alert">{error}. Please try again.</div>}
      <div><button className="btn btn-primary" disabled={state === "sending"}>{state === "sending" ? "Sending…" : "Send order request"}</button></div>
      <p className="small muted">No payment now. We reply with price and delivery time.</p>
    </form>
  );
}
