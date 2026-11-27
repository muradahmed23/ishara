"""Personal movement model.

The same mapping runs on the ESP32 (firmware/ishara_headband/ishara_headband.ino: axisSpeed / computeMove).
This Python mirror is used for the live head indicator, calibration and tests.

Algorithm (per axis):
    n = |tilt| / range_side            range = user's comfortable limit on that side
    if n < dz: speed = 0               dead zone filters small involuntary motion
    u = clamp((n - dz) / (1 - dz))     0..1
    speed = 1 + (max - 1) * u^gamma    nonlinear: fine control near centre, capped top
"""
from .protocol import clamp_model

# Fraction of the user's maximum reach used as the "comfortable" range.
COMFORT = 0.8
MIN_RANGE, MAX_RANGE = 6.0, 45.0


def axis_speed(tilt, range_neg, range_pos, max_speed, dz, gam):
    rng = range_pos if tilt >= 0 else range_neg
    n = abs(tilt) / rng
    if n < dz:
        return 0
    u = min(max((n - dz) / (1 - dz), 0.0), 1.0)
    s = 1 + (max_speed - 1) * u ** gam
    s = int(s + 0.5)             # C round(): half away from zero (s is always >= 1)
    return s if tilt > 0 else -s


def compute_move(pitch, roll, m):
    """Return (dx, dy) exactly like the firmware."""
    dx = axis_speed(roll, m["rL"], m["rR"], m["sx"], m["dz"], m["gam"])
    if m["ix"]:
        dx = -dx
    dy = -axis_speed(pitch, m["rD"], m["rU"], m["sy"], m["dz"], m["gam"])
    if m["iy"]:
        dy = -dy
    return dx, dy


def normalized(pitch, roll, m):
    """Head position in SCREEN directions, -1..1 per axis at the comfortable limit.
    x>0 = right, y>0 = down. Values can exceed 1 when beyond the limit."""
    rx = roll / (m["rR"] if roll >= 0 else m["rL"])
    x = -rx if m["ix"] else rx
    ry = pitch / (m["rU"] if pitch >= 0 else m["rD"])
    y = -ry                      # chin up = screen up
    if m["iy"]:
        y = -y
    return x, y


def ranges_from_capture(left, right, up, down, model):
    """Build a personal model from the extreme readings captured in each step.

    left/right are the roll values (deg) reached when the user tilted left/right,
    up/down the pitch values reached when looking up/down. The SIGN tells us how
    the sensor is mounted, so axis inversion is detected automatically.
    """
    m = dict(model)

    def comfy(v):
        return min(max(abs(v) * COMFORT, MIN_RANGE), MAX_RANGE)

    # Firmware: negative roll uses rL, positive roll uses rR, ix flips direction.
    if right >= left:               # right tilt -> positive roll: natural
        m["ix"], m["rR"], m["rL"] = 0, comfy(right), comfy(left)
    else:                           # mounted the other way round
        m["ix"], m["rR"], m["rL"] = 1, comfy(left), comfy(right)

    # Firmware: positive pitch uses rU and means "screen up" unless iy.
    if up >= down:
        m["iy"], m["rU"], m["rD"] = 0, comfy(up), comfy(down)
    else:
        m["iy"], m["rU"], m["rD"] = 1, comfy(down), comfy(up)
    return clamp_model(m)


def axes_from_capture(cap):
    """Work out the sensor mounting from real movements.

    cap[key] = (pitch, roll) recorded at the furthest point of each step
    (left/right/up/down), streamed with sw=ix=iy=0. Side tilts must land on one
    axis and nods on the other; if side tilts moved PITCH more than roll, the
    axes are swapped on this headband (sw=1).
    Returns (sw, left, right, up, down) with values on the corrected axes.
    """
    side_p = abs(cap["left"][0]) + abs(cap["right"][0])
    side_r = abs(cap["left"][1]) + abs(cap["right"][1])
    nod_p = abs(cap["up"][0]) + abs(cap["down"][0])
    nod_r = abs(cap["up"][1]) + abs(cap["down"][1])
    # pick the assignment where both movements land on their own axis the most
    sw = 1 if (side_p + nod_r) > (side_r + nod_p) else 0
    lr, ud = (0, 1) if sw else (1, 0)
    return (sw, cap["left"][lr], cap["right"][lr], cap["up"][ud], cap["down"][ud])


def axes_quality(cap, sw):
    """Problems with axis separation (empty = good)."""
    issues = []
    lr, ud = (0, 1) if sw else (1, 0)
    side_main = abs(cap["left"][lr]) + abs(cap["right"][lr])
    side_cross = abs(cap["left"][ud]) + abs(cap["right"][ud])
    nod_main = abs(cap["up"][ud]) + abs(cap["down"][ud])
    nod_cross = abs(cap["up"][lr]) + abs(cap["down"][lr])
    if side_cross > 0.7 * side_main or nod_cross > 0.7 * nod_main:
        issues.append("Side tilts and nods were mixed. Keep the headband firm and move one direction at a time.")
    return issues


def capture_quality(left, right, up, down):
    """Return a list of human-readable problems with a capture (empty = good)."""
    issues = []
    if abs(left) < 6 or abs(right) < 6:
        issues.append("Left/right movement was very small. Tilt a little further.")
    if abs(up) < 5 or abs(down) < 5:
        issues.append("Up/down movement was very small. Nod a little further.")
    if (left > 0) == (right > 0) and abs(left) > 3 and abs(right) > 3:
        issues.append("Left and right looked the same. Check the sensor is fixed firmly.")
    if (up > 0) == (down > 0) and abs(up) > 3 and abs(down) > 3:
        issues.append("Up and down looked the same. Check the sensor is fixed firmly.")
    return issues
