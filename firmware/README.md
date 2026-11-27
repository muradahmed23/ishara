# Headband firmware

`ishara_headband/ishara_headband.ino` — ESP32 + MPU6050.

- Bluetooth HID mouse: head tilt → cursor, plus hardware clicks requested by the app.
- iShara data service: live head data to the app, settings and commands from it ([protocol](../docs/protocol.md)).
- Personal movement model and calibration stored in flash.

## Build & flash

```powershell
..\scripts\flash-firmware.ps1             # auto-detects the USB port
..\scripts\flash-firmware.ps1 -Port COM6
..\scripts\flash-firmware.ps1 -CompileOnly
```

Board: **ESP32 Dev Module**, partition scheme **Huge APP** (BLE needs the space).

Using the Arduino IDE instead: open `ishara_headband/ishara_headband.ino`, copy
`libraries/ESP32-BLE-Mouse` into your Arduino `libraries` folder, select the board and partition
scheme above, and upload.

## Library

`libraries/ESP32-BLE-Mouse` is [T-vK/ESP32-BLE-Mouse](https://github.com/T-vK/ESP32-BLE-Mouse),
vendored and patched to build on ESP32 Arduino core 3.x. It also lets the firmware add the
iShara data service to the same BLE server (`onStarted` hook).

## Serial (115200 baud)

| Key | Action |
|---|---|
| `c` | recalibrate the neutral position |
| `d` | toggle live readout: `D pitch roll dx dy sw ix iy` |
