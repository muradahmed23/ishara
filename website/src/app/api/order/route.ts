import { NextResponse } from "next/server";
import { kits } from "@/config/hardware";

/**
 * Hardware order request -> email via Resend (https://resend.com).
 * Needs ORDER_EMAIL_TO and RESEND_API_KEY (server-only, set in Vercel). Optional ORDER_EMAIL_FROM.
 * Without them this route answers 503 and the page uses its mailto / "opens soon" fallback.
 */
const clean = (v: unknown, max: number) => String(v ?? "").replace(/[\r\n]+/g, " ").trim().slice(0, max);

export async function POST(req: Request) {
  const to = process.env.ORDER_EMAIL_TO;
  const key = process.env.RESEND_API_KEY;
  if (!to || !key) return NextResponse.json({ error: "Ordering is not configured" }, { status: 503 });

  let b: Record<string, unknown>;
  try {
    b = await req.json();
  } catch {
    return NextResponse.json({ error: "Invalid request" }, { status: 400 });
  }
  if (b.website) return NextResponse.json({ ok: true }); // honeypot: silently ignore bots

  const kit = kits.find((k) => k.id === b.kit && k.available);
  const name = clean(b.name, 80), email = clean(b.email, 120), location = clean(b.location, 80);
  const quantity = Math.min(50, Math.max(1, Number(b.quantity) || 1));
  const message = String(b.message ?? "").trim().slice(0, 1000);
  if (!kit || !name || !location || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    return NextResponse.json({ error: "Please fill in all required fields" }, { status: 400 });
  }

  const r = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: process.env.ORDER_EMAIL_FROM ?? "iShara <onboarding@resend.dev>",
      to: [to],
      reply_to: email,
      subject: `iShara order request: ${kit.name} × ${quantity}`,
      text: `Kit: ${kit.name}\nQuantity: ${quantity}\nName: ${name}\nEmail: ${email}\nCountry / city: ${location}\n\n${message}`,
    }),
  });
  if (!r.ok) return NextResponse.json({ error: "Could not send the request" }, { status: 502 });
  return NextResponse.json({ ok: true });
}
