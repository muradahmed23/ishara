# Hardware

Early working prototype: electronics mounted on a fabric/foam headband, worn on the forehead.

## Bill of materials

| Part | Notes |
|---|---|
| ESP32 dev board (ESP32-D0WD-V3, USB-C) | Bluetooth LE: HID mouse + data service |
| MPU6050 module (GY-521 / HW-123) | accelerometer + gyroscope, I²C |
| Li-Po 3.7 V 1200 mAh (603450) | power |
| USB-C Li-Po charger module (HW-373) | charging |
| Active buzzer | one beep when Bluetooth connects |
| Headband + foam support, wires, hot glue | |

## Wiring

| MPU6050 | ESP32 |
|---|---|
| VCC | 3V3 |
| GND | GND |
| SDA | D21 |
| SCL | D22 |
| AD0 | GND (I²C address 0x68) |

Buzzer: `+` → D26, `−` → GND.

## Mounting

Upright on the forehead, chip facing forward. The exact angle does not matter: the firmware
captures the user's neutral position, and calibration detects axes and directions.

## Limits of this prototype

- **No battery telemetry** (the battery is not wired to an ADC pin).
- USB is for programming and charging; the mouse works over Bluetooth.
- Left / right = tilting the head toward the shoulder (an accelerometer cannot sense turning).
- Secure the sensor wires: if one comes loose the firmware prints `MPU6050 NOT found` and stops.

## Next revision

Enclosure, proper battery mounting with voltage sensing, wire management, lighter forehead
support, compact PCB, gyroscope fusion for head *turning*.
