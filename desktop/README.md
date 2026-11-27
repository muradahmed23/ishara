# Desktop app

Windows app (Python) — voice control, calibration, training and profiles for the iShara headband.

```powershell
..\scripts\setup.ps1     # once
..\scripts\run.ps1       # start (add -Sim to run without the headband)
python -m pytest -q      # tests
```

| Module | Role |
|---|---|
| `ishara_app.py` | entry point; single instance; `--sim`, `--classic` |
| `ishara/protocol.py` | BLE UUIDs, packet and settings format (matches the firmware) |
| `ishara/link.py` | BLE client with auto-reconnect; hardware simulator |
| `ishara/model.py` | movement model (mirror of the firmware) + calibration math |
| `ishara/calib.py` | guided calibration flow (pure logic, unit-tested) |
| `ishara/controller.py` | single source of truth: actions, modes, dwell, help menu |
| `ishara/voice.py` | Vosk command grammar + Whisper dictation |
| `ishara/speech.py` | spoken feedback (Windows TTS) |
| `ishara/screen.py` | Windows cursor and input layer (ClipCursor, SendInput fallback) |
| `ishara/profiles.py` | per-user profiles in `%APPDATA%\Ishara` |
| `ishara/webui.py` + `ishara/web/` | main window: HTML/CSS/JS in Edge WebView2 |
| `ishara/ui/` | always-on-top overlays (status tag, floating bar, help menu), practice lessons |

Design system (colours, type, components): [../docs/design-system.md](../docs/design-system.md).
