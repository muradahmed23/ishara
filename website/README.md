# iShara website

Next.js 15 (App Router) site for iShara: product, hardware, guide and downloads.
Same design system as the desktop app ([../docs/design-system.md](../docs/design-system.md)): light theme, Inter, system blue.

**Production:** https://ishara-mu-three.vercel.app (Vercel project `ishara`)

## Pages

| Route | Content |
|---|---|
| `/` | product overview, features, getting started |
| `/how-it-works` | how the headband + app work, voice commands |
| `/hardware` | real prototype, parts, wiring, **order request** |
| `/guide` | install, wear, connect, calibrate, troubleshooting |
| `/download` | installer download driven by the release manifest |
| `/api/order` | order request endpoint (email via Resend) |

## Release data: single source of truth

The download button, version, size, SHA-256, requirements and release notes come from
[`../release/latest.json`](../release/latest.json), read **live from GitHub** (refreshed every 5 minutes),
with a copy bundled at build time as fallback (`scripts/sync-release.mjs`, runs before `dev`/`build`).

- `"status": "unreleased"` → the page shows **Coming soon** (never a fake link).
- `"status": "released"` + `installer.url` + `installer.sha256` → **Download** is enabled.

Publishing a release does not need a redeploy: edit `release/latest.json`, push.

## Hardware ordering

Configured in [`src/config/hardware.ts`](src/config/hardware.ts) (kits, contents, prices: `null` = "Price on request").
How requests are delivered depends on environment variables:

| Configuration | Behaviour |
|---|---|
| `ORDER_EMAIL_TO` + `RESEND_API_KEY` | form posts to `/api/order`, which emails the request (reply-to = buyer) |
| `NEXT_PUBLIC_ORDER_EMAIL` only | form opens the visitor's email app with the request filled in |
| none | "Ordering opens soon" |

No payment is taken; the team replies with price and delivery.

## Environment variables

All optional. Set them in Vercel → Project `ishara` → Settings → Environment Variables. Never commit them.

| Name | Scope | Purpose |
|---|---|---|
| `NEXT_PUBLIC_SITE_URL` | public | canonical URL for metadata (default: production URL) |
| `RELEASE_MANIFEST_URL` | server | override the manifest location |
| `ORDER_EMAIL_TO` | server | where order requests are sent |
| `RESEND_API_KEY` | server, **secret** | Resend API key for sending order emails |
| `ORDER_EMAIL_FROM` | server | sender, e.g. `iShara <orders@your-domain>` (verified in Resend) |
| `NEXT_PUBLIC_ORDER_EMAIL` | public | mailto fallback address |

## Develop

```powershell
cd website
npm ci
npm run dev        # http://localhost:3000
npm run build      # production build + type check
```

## Deploy

```powershell
cd website
vercel deploy --prod          # uses the linked project (website/.vercel, not committed)
```

`vercel.json` pins the framework (Next.js), install and build commands.
Large files (the ~700 MB installer) are **never** part of the site: they are GitHub Release assets.
