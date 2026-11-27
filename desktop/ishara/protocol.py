"""Bluetooth data protocol shared with the ESP32 firmware (firmware/ishara_headband/ishara_headband.ino).

Keep UUIDs and packet layout in sync with the firmware.
"""
import struct
from dataclasses import dataclass

DEVICE_NAME = "Ishara Mouse"
SVC_UUID = "b7a10001-5f3c-4e2a-9d1b-1a2b3c4d5e6f"
DATA_UUID = "b7a10002-5f3c-4e2a-9d1b-1a2b3c4d5e6f"   # notify, 10 bytes
CMD_UUID = "b7a10003-5f3c-4e2a-9d1b-1a2b3c4d5e6f"    # write, text command
CONF_UUID = "b7a10004-5f3c-4e2a-9d1b-1a2b3c4d5e6f"   # read, "k=v,k=v"

FLAG_PAUSED, FLAG_CALIBRATING, FLAG_SENSOR_OK = 1, 2, 4

# Keys understood by the firmware, with the same limits it enforces.
MODEL_LIMITS = {
    "p0": (-90, 90), "r0": (-180, 180),
    "rU": (4, 60), "rD": (4, 60), "rL": (4, 60), "rR": (4, 60),
    "dz": (0.05, 0.6), "sx": (1, 30), "sy": (1, 30),
    "gam": (1.0, 3.0), "alpha": (0.05, 1.0), "ix": (0, 1), "iy": (0, 1), "sw": (0, 1),
}

DEFAULT_MODEL = {
    "p0": 0.0, "r0": 0.0, "rU": 15.0, "rD": 12.0, "rL": 15.0, "rR": 15.0,
    "dz": 0.22, "sx": 6.0, "sy": 5.0, "gam": 1.6, "alpha": 0.25, "ix": 0, "iy": 0, "sw": 0,
}


@dataclass
class Sample:
    pitch: float      # deg, relative to neutral, smoothed
    roll: float       # deg, relative to neutral, smoothed
    gyro: float       # deg/s, total rotation speed
    dx: int           # mouse move the firmware just sent
    dy: int
    paused: bool
    calibrating: bool
    sensor_ok: bool
    seq: int


def unpack_sample(data: bytes) -> Sample:
    """Decode the 10-byte live packet. Raises ValueError on bad length."""
    if len(data) != 10:
        raise ValueError(f"bad packet length {len(data)}")
    p, r, g, dx, dy, flags, seq = struct.unpack("<hhhbbBB", data)
    return Sample(p / 100.0, r / 100.0, g / 10.0, dx, dy,
                  bool(flags & FLAG_PAUSED), bool(flags & FLAG_CALIBRATING),
                  bool(flags & FLAG_SENSOR_OK), seq)


def pack_sample(s: Sample) -> bytes:
    """Encode a sample (used by the simulator and tests)."""
    flags = (FLAG_PAUSED if s.paused else 0) | (FLAG_CALIBRATING if s.calibrating else 0) \
        | (FLAG_SENSOR_OK if s.sensor_ok else 0)
    return struct.pack("<hhhbbBB", int(s.pitch * 100), int(s.roll * 100), int(s.gyro * 10),
                       s.dx, s.dy, flags, s.seq & 0xFF)


def clamp_model(model: dict) -> dict:
    out = dict(DEFAULT_MODEL)
    for k, v in model.items():
        if k in MODEL_LIMITS:
            lo, hi = MODEL_LIMITS[k]
            out[k] = min(max(float(v), lo), hi)
    for k in ("ix", "iy", "sw"):
        out[k] = int(out[k] >= 0.5)
    return out


NEUTRAL_KEYS = ("p0", "r0")


def model_to_text(model: dict, include_neutral=False) -> str:
    """The neutral position (p0, r0) is owned by the headband: it depends on how the
    band sits on the head today, so the app never overwrites it unless asked."""
    m = clamp_model(model)
    keys = [k for k in MODEL_LIMITS if include_neutral or k not in NEUTRAL_KEYS]
    return ",".join(f"{k}={m[k]:.3f}" if k not in ("ix", "iy", "sw") else f"{k}={m[k]}" for k in keys)


def text_to_model(text: str) -> dict:
    model = {}
    for part in text.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            try:
                model[k.strip()] = float(v)
            except ValueError:
                pass
    return clamp_model(model)
