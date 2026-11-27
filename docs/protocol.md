# Headband ⇄ App protocol (Bluetooth LE)

Source of truth: `firmware/ishara_headband/ishara_headband.ino` and `desktop/ishara/protocol.py`.
**Change both together.**

Device name: **`Ishara Mouse`**. It exposes the standard HID mouse service plus the iShara service:

| Characteristic | UUID | Properties | Content |
|---|---|---|---|
| Service | `b7a10001-5f3c-4e2a-9d1b-1a2b3c4d5e6f` | | |
| Data | `b7a10002-…` | notify, read | live head data, 10 bytes, ~30 Hz |
| Command | `b7a10003-…` | write | text command |
| Config | `b7a10004-…` | read | current settings, `k=v,k=v` |

## Live data packet (10 bytes, little-endian)

| Offset | Type | Field |
|---|---|---|
| 0 | int16 | pitch × 100 (deg, relative to neutral, + = chin up) |
| 2 | int16 | roll × 100 (deg, + = toward right shoulder) |
| 4 | int16 | gyro × 10 (deg/s, total rotation speed) |
| 6 | int8 | dx sent to the cursor |
| 7 | int8 | dy sent to the cursor |
| 8 | uint8 | flags: 1 = paused, 2 = calibrating, 4 = sensor OK |
| 9 | uint8 | sequence number |

## Commands (UTF-8 text)

| Command | Effect |
|---|---|
| `CAL` | capture the neutral head position (2 s, keep still) |
| `PAUSE` / `RESUME` | stop / restart cursor movement |
| `SET k=v,…` | change settings (range-checked on the device) |
| `SAVE` | store settings in flash |
| `RESET` | factory settings + recalibrate |
| `HID L` · `R` · `M` · `D` | left · right · middle · double click |
| `HID B` · `F` | back · forward button |
| `HID DOWN` · `UP` | press · release left button (drag) |
| `HID WHEEL n` | scroll n lines (−20 … 20) |

## Settings

| Key | Range | Meaning |
|---|---|---|
| `rU` `rD` `rL` `rR` | 4–60° | comfortable range up / down / left / right |
| `dz` | 0.05–0.6 | dead zone, fraction of range |
| `sx` `sy` | 1–30 | top speed, px per report |
| `gam` | 1–3 | response curve (> 1 = finer near centre) |
| `alpha` | 0.05–1 | smoothing |
| `ix` `iy` | 0 / 1 | reverse left-right / up-down |
| `sw` | 0 / 1 | swap axes (mounting) |
| `p0` `r0` | — | mounting tilt (info only) |

Speed per axis: `n = |tilt| / range`; no movement while `n < dz`;
`speed = 1 + (max − 1) · ((n − dz) / (1 − dz))^gam`.
