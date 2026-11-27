# iShara — App Theme & Build Details

Source of truth for how the iShara desktop app looks and is built today.
Everything below is taken from the actual code (`ishara/web/app.css`, `ishara/web/index.html`,
`ishara/web/app.js`, `ishara/ui/theme.py`, `ishara/ui/overlay.py`).

---

## 1. What iShara is

A Windows desktop app for a **head-controlled mouse with voice commands**, built for people
who cannot use their hands.

- **Hardware:** forehead-mounted headband — ESP32 dev board + MPU6050 IMU + 3.7 V 1200 mAh
  Li-Po + buzzer, held on a fabric/foam band. Electronics are visible (early prototype).
- **Head tilt moves the cursor.** The headband is a real Bluetooth HID mouse, so it works
  even without the app.
- **Voice commands click, scroll, drag, type** (offline speech recognition).
- **The app** shows live status, runs calibration and training, and stores per-user settings.

---

## 2. Tech stack

| Part | Technology |
|---|---|
| Language | Python 3.10+ (tested on 3.14), Windows only |
| Main window | **pywebview** using Windows **Edge WebView2**; UI is plain **HTML + CSS + vanilla JS** (`ishara/web/`) |
| JS ⇄ Python | `window.pywebview.api.<method>()` → `Api` class in `ishara/webui.py`; UI polls `state()` ~30×/s |
| Always-on-top pieces | **Tkinter** (hidden root): cursor status tag, floating control bar, help menu, practice lessons (`ishara/ui/`) |
| Bluetooth data link | **bleak** (BLE): live head data in, settings/commands out |
| Voice commands | **Vosk** (offline) |
| Dictation | **faster-whisper** (offline), Vosk as fallback |
| Microphone | **sounddevice** |
| Spoken feedback | Windows text-to-speech |
| Clicks | Sent by the headband as hardware Bluetooth HID clicks (work on protected windows such as the On-Screen Keyboard); Windows `SendInput` as fallback |
| Storage | JSON profiles in `%APPDATA%\Ishara` |

No frameworks, no build step, no CDN — fonts and icons are bundled, everything works offline.

---

## 3. Design language

**"Apple-inspired, minimal."** Code comment in `app.css`:
> Neutral surfaces, one system blue for actions, colour only when it means something.

Rules:
- Neutral grey/white surfaces; **one accent colour (system blue)** only for primary actions and active states.
- Green / orange / red **only** when they carry meaning (ok / warning / error).
- No gradients, glows or heavy shadows. Soft, layered shadows only.
- Rounded corners everywhere; generous spacing; calm motion.
- Light and Dark appearance (user setting).

---

## 4. Typography

- **Font:** **Inter** (bundled TTF: Regular 400, Medium 500, SemiBold 600). Fallback: `"Segoe UI Variable Text", system-ui, sans-serif`.
- **Base:** 13 px, line-height 1.4.

| Use | Size | Weight | Letter-spacing |
|---|---|---|---|
| Page title (toolbar h1) | 26 px | 600 | −0.02em |
| About hero name | 22 px | 600 | −0.02em |
| Sheet title (calibration) | 20 px | 600 | −0.02em |
| Brand name / card title / tile value | 15 px | 600 | −0.01em |
| Body, buttons | 13 px | 400 / 500 | — |
| Secondary text, labels | 12 px | 400 | — |
| Small text, group headers | 11 px | 400–500 | group header: UPPERCASE, +0.04em |

Numbers use `font-variant-numeric: tabular-nums`.

---

## 5. Colour tokens (CSS variables)

### Light (default)
| Token | Value | Use |
|---|---|---|
| `--bg` | `#F5F5F7` | window background |
| `--side` | `#EDEDF0` | sidebar, sheet side panel |
| `--surface` | `#FFFFFF` | cards, groups, tiles |
| `--fill` | `rgba(120,120,128,.08)` | grey buttons, inputs, segmented control |
| `--fill-2` | `rgba(120,120,128,.14)` | hover, switch off |
| `--text` | `#1D1D1F` | primary text |
| `--text-2` | `#6E6E73` | secondary text |
| `--text-3` | `#A1A1A6` | tertiary / disabled |
| `--sep` | `rgba(60,60,67,.12)` | hairline separators |
| `--blue` | `#007AFF` | primary action, active, focus |
| `--blue-press` | `#0062CC` | primary hover/press |
| `--blue-soft` | `rgba(0,122,255,.10)` | focus ring, soft highlight |
| `--green` | `#34C759` | success, switch on, connected |
| `--orange` | `#FF9500` | warning |
| `--red` | `#FF3B30` | error, danger |
| `--shadow` | `0 1px 2px rgba(0,0,0,.04), 0 6px 20px rgba(0,0,0,.05)` | cards |
| `--shadow-lg` | `0 20px 60px rgba(0,0,0,.18), 0 2px 8px rgba(0,0,0,.06)` | sheets/dialogs |
| `--r` | `14px` | default radius |
| `--ease` | `cubic-bezier(.25,.8,.25,1)` | all transitions |

### Dark (`[data-theme="dark"]`)
| Token | Value |
|---|---|
| `--bg` | `#000000` |
| `--side` | `#161618` |
| `--surface` | `#1C1C1E` |
| `--fill` / `--fill-2` | `rgba(120,120,128,.18)` / `.28` |
| `--text` / `--text-2` / `--text-3` | `#F5F5F7` / `#98989D` / `#636366` |
| `--sep` | `rgba(84,84,88,.6)` |
| `--blue` / `--blue-press` / `--blue-soft` | `#0A84FF` / `#409CFF` / `rgba(10,132,255,.18)` |
| `--green` / `--orange` / `--red` | `#30D158` / `#FF9F0A` / `#FF453A` |
| `--shadow` / `--shadow-lg` | `0 1px 2px rgba(0,0,0,.4)` / `0 20px 60px rgba(0,0,0,.6)` |

Theme is switched by setting `document.documentElement.dataset.theme` (Settings → Appearance: Light / Dark).

### Native (Tkinter) palette — `ishara/ui/theme.py`
Light matches the web tokens (bg `#F5F5F7`, card `#FFFFFF`, text `#1D1D1F`, accent `#007AFF`,
green `#34C759`, amber `#FF9500`, red `#FF3B30`, borders `#E3E3E8`).
The cursor status tag is inverted: charcoal `#1D1D1F` background, white text.
⚠️ Known inconsistency: the native **dark** palette uses a different, softer set
(bg `#161617`, card `#1E1E20`, accent `#6B8CF0`, green `#3DB07A`, amber `#E3A94E`, red `#E4706C`)
than the web dark tokens. They should be unified.
Native icons use the **Segoe Fluent Icons** font (Windows 11).

---

## 6. Layout

Window: **1140 × 760**, minimum **940 × 640**, background `#F5F5F7`.

```
┌──────────────┬──────────────────────────────────────────────┐
│ SIDEBAR 224px│ TOOLBAR: page title (26px)   [status capsules]│
│  logo mark   ├──────────────────────────────────────────────┤
│  iShara      │ PAGE (max-width 980px, scrolls)               │
│              │                                               │
│  Home        │                                               │
│  Training    │                                               │
│  Settings    │                                               │
│  Profiles    │                                               │
│  About       │                                               │
│              │                                               │
│  (avatar +   │                                               │
│   profile)   │                                               │
└──────────────┴──────────────────────────────────────────────┘
```

- **Sidebar** (224 px, `--side`): logo mark, brand name + subtitle, nav items (34 px high,
  8 px radius, icon + label, grey → filled when active), current profile avatar at the bottom.
- **Logo mark:** a rounded square (30 px, 8 px radius; 56 px / 14 px radius on About) in text
  colour, with a small dot and a short bar in surface colour — an abstract "i" / person.
- **Toolbar:** page title + status **capsules** (28 px pills, 14 px radius, white with shadow,
  7 px LED dot: grey / green / orange / red) for Headband and Microphone.
- Pages fade/slide in (`enter .35s`).

---

## 7. Pages

### Home
- **Tile row** (grid `repeat(3,1fr) 1.15fr`, 12 px gap): **Headband**, **Head control**,
  **Microphone** status tiles (30 px round icon, label 12 px, value 15 px/600) + an action tile
  with a large **Pause control** button ("or say 'pause'").
- **Head tracking card** (tag "Live"): 220 × 220 px live plot of head position with dead-zone
  and range, plus readouts: Direction, Up/down, Left/right, Cursor, Your range; **Recalibrate** button.
- **Voice card** (tag "Offline"): state + animated level **meter** (4 px bars), segmented
  **Commands / Dictation**, "Heard", "Last action", **Mute microphone**, **All voice commands**.

### Training
- **Calibration** — opens a full-window **sheet**.
- **Practice** — "Seven short lessons", opens full screen; each lesson unlocks the next.

### Settings (iOS-style grouped list)
Groups: Direction (reverse left/right, up/down), Movement (speed, dead zone, smoothing, curve),
Microphone, Spoken feedback, Dictation, Voice commands (editable phrases), Clicking (dwell
click), Scrolling & screen, Cursor status tag, Floating bar, Appearance & tools (Light/Dark,
On-screen keyboard, **Emergency stop**).

### Profiles
One profile per user: their calibration and settings. Create, switch, delete.

### About
Hero with large logo mark, name (22 px), version.

---

## 8. Components

| Component | Spec |
|---|---|
| **Button** | 32 px high, 0 14 px padding, 8 px radius, weight 500, press = `scale(.97)` |
| — primary | blue bg, white text, hover `--blue-press` |
| — gray | `--fill` bg, hover `--fill-2` |
| — plain | blue text, hover `--blue-soft` |
| — danger | red text on `--fill` |
| — large | 42 px high, 12 px radius, 14 px text |
| **Card** | white, 16 px radius, `--shadow` |
| **Tag** | 11 px/500, green text on `rgba(52,199,89,.12)`, 6 px radius |
| **Grouped list** | white group, 12 px radius; cells ≥ 48 px, 16 px padding; hairline separators inset 16 px; optional 30 px coloured icon square (blue/green/gray/orange), title 500, subtitle 12 px, value right-aligned |
| **Switch** | 44 × 26 px, knob 22 px white with shadow; off `--fill-2`, on **green** |
| **Segmented control** | `--fill` track, 9 px radius; 28 px segments, selected = white + small shadow |
| **Slider** | range + 48 px right-aligned value |
| **Input** | `--fill`; focus = white + 3 px `--blue-soft` ring |
| **Phrase chip** | 26 px pill, `--fill`, hover blue-soft/blue text (voice command phrases) |
| **Status capsule** | 28 px pill, LED dot |
| **Sheet** (calibration) | dimmed backdrop (fade .25s), large rounded panel with `--shadow-lg`; left side panel 250 px with step list |
| **Step list** | 18 px circles joined by 1 px lines; done = green circle + white check; current = 5 px blue ring, text 500; upcoming = grey outline |

Motion: 0.12–0.35 s, `--ease`. Scrollbar: 10 px, rounded `--fill-2` thumb.

---

## 9. Always-on-top overlays (Tkinter, click-through where noted)

- **Cursor status tag** — small charcoal pill (28 px) next to the cursor, white text, e.g.
  "Moving Diagonally", "Left Click Executed", "Hand Mouse — say 'head mouse'". Click-through,
  never takes focus, fades. Position: next to cursor / top / bottom.
- **Floating control bar** — 360 × 44 px pill, always on top, draggable:
  `[state dot + Active] [mic] [current cursor action] [pause]`. Double-click opens the main
  window. Optional click-through.
- **Help menu** — numbered list next to the cursor ("say a number"), 3 pages, 8 items each.
- **Practice lessons** — full-screen Tk windows.

---

## 10. Calibration flow (sheet)

Steps: **Look straight → Tilt left → Tilt right → Look up → Look down → Try it → Complete.**
- Spoken instructions for every step; mouse movement paused during the flow.
- Each step waits until the user is back to straight, accepts only a *new* direction, and
  captures only after the user **holds their limit for 1 second** (progress bar fills while holding).
- Axes and directions are **detected automatically** from the user's movements, so it works
  however the headband sits.
- "Try it": a square pad with a crosshair centre and four target circles (blue outline → green
  when hit); a blue dot shows the head position; orange warning text if the capture looked wrong.

---

## 11. Voice commands (all listed in the help menu)

| Group | Say |
|---|---|
| Mouse | click, double click, right click, middle click / wheel click, scroll up, scroll down, start drag, release / drop, click lock, go back, go forward |
| Control | hand mouse / use mouse / normal mouse, head mouse / head control / resume, pause, stop control, center (re-center head), find cursor, keyboard |
| Typing | start typing, stop typing |
| Microphone | mute microphone / stop listening, unmute microphone / start listening |
| Help | help / show commands / what can I say → then a number, more, back, close |

---

## 12. Honest constraints (don't invent features)

- **No battery telemetry** — the battery is not wired to an ESP32 pin; do not show a battery level.
- USB is only for programming/charging; the mouse works over **Bluetooth**.
- The headband's only sound is **one beep when Bluetooth connects**.
- Left/right is controlled by **tilting the head toward the shoulder** (not turning).
- Fully offline; no accounts, no cloud.
