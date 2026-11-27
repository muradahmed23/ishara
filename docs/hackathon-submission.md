# iShara: Hackathon Submission

> Fields marked **[FILL IN]** need information only you have. Everything else is accurate to what is built.

---

## Project name
**iShara**

## Tagline (one line)
Hands-free computer control: tilt your head to move the cursor, speak to click and type.

## Short description (≈50 words)
iShara is a low-cost head-tilt mouse headband plus an offline voice-control app for people who cannot use their hands. An ESP32 + MPU6050 headband acts as a real Bluetooth mouse; the Windows app adds 30+ voice commands, voice typing, guided spoken calibration and training. No internet, no account, nothing uploaded.

## Problem
People with upper-limb disabilities (spinal cord injury, ALS, cerebral palsy, amputation, stroke) often cannot use a mouse or keyboard. Commercial head mice and eye trackers exist but are expensive, need special software or setup, and are hard for one person to calibrate alone. Free alternatives are usually webcam-based, sensitive to lighting, and drain the computer.

## Solution
iShara combines two parts:
1. **Headband (hardware):** an ESP32 dev board and MPU6050 motion sensor on a foam headband, powered by a 1200 mAh Li-Po battery. It is a **standard Bluetooth mouse**: tilting the head toward a shoulder moves the cursor left/right, lifting or lowering the chin moves it up/down. The movement model (dead zone, response curve, speed) runs **on the headband** for the fastest response.
2. **Desktop app (Windows):** adds **offline voice control** (click, double/right/middle click, scroll, drag, back/forward, pause, emergency stop, on-screen keyboard), **voice typing**, a **spoken onboarding** (microphone → typing accuracy → headband → Bluetooth → training → calibration), seven practice lessons and per-person profiles.

## How it works (technical)
- **Firmware (C++/Arduino, ESP32):** reads the MPU6050 over I²C, builds a head frame from the user's own straight-ahead position (so any mounting angle works), applies the personal movement model and sends HID mouse reports every 15 ms over Bluetooth LE. A custom BLE GATT service streams live head data to the app and receives settings and commands.
- **Hardware clicks:** when the user says "click", the app asks the headband to click as a real Bluetooth mouse. Unlike software clicks, these work even in protected windows such as the Windows On-Screen Keyboard.
- **Desktop app (Python):** Vosk for offline command recognition, faster-whisper for offline dictation, Bleak for Bluetooth LE, a WebView2 interface (HTML/CSS/JS) and native always-on-top overlays (status tag, floating control bar, numbered help menu).
- **Calibration:** guided and spoken; detects axes and directions from the user's real movements; waits for a still, straight head and a held limit before capturing.
- **Distribution:** a 223 MB offline Windows installer (PyInstaller + Inno Setup) with the speech models included; the optional high-accuracy model (486 MB) is offered during onboarding, downloaded in the background, SHA-256 verified. Versioned releases with an in-app update checker that never overwrites user profiles.
- **Website (Next.js on Vercel):** live in-browser demo that uses the webcam in place of the headband (MediaPipe face tracking, same movement model as the firmware), an interactive 3D model of the real prototype with its actual wiring, and download/hardware pages driven by one release manifest.

## Tech stack
ESP32 · MPU6050 · Arduino (C++) · Bluetooth LE HID + GATT · Python · Vosk · faster-whisper (CTranslate2) · Bleak · pywebview / WebView2 · Tkinter · PyInstaller · Inno Setup · Next.js 15 · React 19 · TypeScript · Three.js / React Three Fiber · MediaPipe · Vercel · GitHub Actions

## Key features
- Head-tilt mouse that works the moment it pairs (no driver; it is a standard Bluetooth mouse)
- 30+ offline voice commands; every command listed in a spoken, numbered help menu ("help")
- Voice typing with punctuation; optional high-accuracy model
- Hardware clicks that work on the On-Screen Keyboard and admin windows
- Spoken onboarding and calibration; training and calibration can be skipped
- Hand-mouse mode: switch to a normal mouse with one phrase; voice clicks keep working
- Emergency stop ("stop control") and pause/resume
- Per-person profiles; settings and calibration survive updates
- 100% offline and private: nothing is uploaded
- One-click Windows installer, verified downloads, update checker

## Impact
- **Who benefits:** people with limited or no hand/arm movement, temporary injuries, repetitive strain injury, and anyone who needs hands-free control.
- **Low cost:** built from widely available parts (ESP32, MPU6050, Li-Po battery, charger board, buzzer, headband). **[FILL IN: total parts cost, e.g. "≈ PKR X / $Y"]**
- **Independence:** the spoken setup lets a person set up and calibrate without someone else's hands.
- **Privacy:** speech never leaves the computer.

## What makes it different
- The movement runs on the headband, so it works as a mouse even without the app.
- Clicks are hardware clicks, so they work where software tools are blocked.
- Calibration adapts to how the band sits on each person; directions match the firmware exactly.
- Open source, fully offline, and installable by a non-technical user.

## Challenges we ran into
- **Sensor orientation:** the MPU6050 is mounted upright on the forehead at an angle. We built a head frame from the user's straight-ahead position and verified all four directions with live tests.
- **Calibration reliability:** early versions captured "straight" while the head was still moving, reversing directions. Calibration now waits for a still, upright head and a held limit.
- **Protected windows:** Windows blocks software clicks into the On-Screen Keyboard; we moved clicks to the headband as real Bluetooth HID clicks.
- **Package size:** speech models made the first installer 659 MB; we moved the large model to an optional verified download and removed unused libraries (now 223 MB).
- **Hardware:** loose sensor wires stop the cursor; the app now shows the sensor status.

## What's next
Enclosure and compact PCB, battery level monitoring, gyroscope fusion for head **turning**, macOS/Linux app, multiple languages, code-signed installer, user trials with occupational therapists.

## Links
- **Website / live demo:** https://ishara-mu-three.vercel.app
- **Try it with your head (webcam demo):** https://ishara-mu-three.vercel.app/#try
- **Download (Windows installer 2.0.1):** https://ishara-mu-three.vercel.app/download
- **Source code:** https://github.com/muradahmed23/ishara
- **Demo video:** **[FILL IN after upload]**

## Team
- **[FILL IN: name, role]**: e.g. hardware & firmware
- **[FILL IN: name, role]**: e.g. desktop app & website
- **Institution:** Bahria University: Embedded Systems Design (CEN-440) **[confirm / FILL IN]**

## Category / track
**[FILL IN: e.g. Accessibility / Health / Hardware / AI]**

## Built with (for "how was AI used" questions, if asked)
Development was assisted by Claude Code (Anthropic) for software, firmware tuning, packaging and the website; hardware was built and tested by the team.
