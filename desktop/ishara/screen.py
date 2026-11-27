"""Final mouse-control layer: screen geometry, boundary protection, input injection.

Boundary protection (defence in depth):
1. Windows never lets a Bluetooth HID mouse move the cursor off the desktop.
2. ClipCursor() locks ALL mouse input to the active monitor (or to a single
   point while paused), so the cursor cannot even drift to another monitor.
3. Every position this app sets itself goes through clamp_point().
"""
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

# ---------------------------------------------------------------- geometry


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", wintypes.DWORD), ("rcMonitor", RECT),
                ("rcWork", RECT), ("dwFlags", wintypes.DWORD)]


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def clamp_point(x, y, rect):
    """rect = (left, top, right, bottom) exclusive right/bottom.
    X = clamp(x, left, right-1), Y = clamp(y, top, bottom-1)."""
    left, top, right, bottom = rect
    return int(clamp(x, left, right - 1)), int(clamp(y, top, bottom - 1))


def cursor_pos():
    pt = wintypes.POINT()
    user32.GetCursorPos(ctypes.byref(pt))
    return pt.x, pt.y


def monitor_rect(x=None, y=None):
    """Full rectangle of the monitor containing (x, y), default: the cursor.
    This is the 'active screen'."""
    if x is None:
        x, y = cursor_pos()
    hmon = user32.MonitorFromPoint(wintypes.POINT(int(x), int(y)), 2)   # NEAREST
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(MONITORINFO)
    user32.GetMonitorInfoW(hmon, ctypes.byref(info))
    r = info.rcMonitor
    return r.left, r.top, r.right, r.bottom


def at_edge(x, y, rect, margin=1):
    """Which edges the point touches: subset of {'left','right','top','bottom'}."""
    left, top, right, bottom = rect
    edges = set()
    if x <= left + margin - 1:
        edges.add("left")
    if x >= right - margin:
        edges.add("right")
    if y <= top + margin - 1:
        edges.add("top")
    if y >= bottom - margin:
        edges.add("bottom")
    return edges


def set_cursor(x, y, rect=None):
    rect = rect or monitor_rect()
    cx, cy = clamp_point(x, y, rect)
    user32.SetCursorPos(cx, cy)
    return cx, cy


def center_cursor():
    rect = monitor_rect()
    return set_cursor((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2, rect)


def clip_to(rect):
    """Lock all mouse input inside rect (None = release)."""
    if rect is None:
        user32.ClipCursor(None)
    else:
        r = RECT(*rect)
        user32.ClipCursor(ctypes.byref(r))


def freeze_cursor():
    """Pause: clip the cursor to its current pixel so nothing can move it."""
    x, y = cursor_pos()
    clip_to((x, y, x + 1, y + 1))


# ---------------------------------------------------------------- input injection
INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0002, 0x0004
MOUSEEVENTF_RIGHTDOWN, MOUSEEVENTF_RIGHTUP = 0x0008, 0x0010
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP, KEYEVENTF_UNICODE = 0x0002, 0x0004
ULONG_PTR = ctypes.c_size_t


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", ctypes.c_long), ("dy", ctypes.c_long), ("mouseData", wintypes.DWORD),
                ("dwFlags", wintypes.DWORD), ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [("wVk", wintypes.WORD), ("wScan", wintypes.WORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ULONG_PTR)]


class _U(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("pad", ctypes.c_byte * 32)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _U)]


def _send(*inputs):
    arr = (INPUT * len(inputs))(*inputs)
    sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if sent != len(inputs):
        raise OSError("Windows blocked the input (an admin window may have focus)")


def _mouse(flags, data=0):
    i = INPUT(type=INPUT_MOUSE)
    i.u.mi = MOUSEINPUT(0, 0, data & 0xFFFFFFFF, flags, 0, 0)
    return i


def left_down():
    _send(_mouse(MOUSEEVENTF_LEFTDOWN))


def left_up():
    _send(_mouse(MOUSEEVENTF_LEFTUP))


def left_click():
    _send(_mouse(MOUSEEVENTF_LEFTDOWN), _mouse(MOUSEEVENTF_LEFTUP))


def right_click():
    _send(_mouse(MOUSEEVENTF_RIGHTDOWN), _mouse(MOUSEEVENTF_RIGHTUP))


MOUSEEVENTF_MIDDLEDOWN, MOUSEEVENTF_MIDDLEUP = 0x0020, 0x0040
MOUSEEVENTF_XDOWN, MOUSEEVENTF_XUP = 0x0080, 0x0100
XBUTTON1, XBUTTON2 = 1, 2           # 1 = Back, 2 = Forward


def middle_click():
    _send(_mouse(MOUSEEVENTF_MIDDLEDOWN), _mouse(MOUSEEVENTF_MIDDLEUP))


def back_click():
    _send(_mouse(MOUSEEVENTF_XDOWN, XBUTTON1), _mouse(MOUSEEVENTF_XUP, XBUTTON1))


def forward_click():
    _send(_mouse(MOUSEEVENTF_XDOWN, XBUTTON2), _mouse(MOUSEEVENTF_XUP, XBUTTON2))


def double_click():
    left_click()
    ctypes.windll.kernel32.Sleep(60)
    left_click()


def scroll(lines):
    """lines > 0 scrolls up, < 0 scrolls down."""
    _send(_mouse(MOUSEEVENTF_WHEEL, int(lines * 120)))


def type_text(text):
    """Type unicode text into the focused window."""
    seq = []
    for ch in text:
        code = ord(ch)
        for flags in (KEYEVENTF_UNICODE, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP):
            i = INPUT(type=INPUT_KEYBOARD)
            i.u.ki = KEYBDINPUT(0, code, flags, 0, 0)
            seq.append(i)
    if seq:
        _send(*seq)


def key_press(vk):
    down = INPUT(type=INPUT_KEYBOARD)
    down.u.ki = KEYBDINPUT(vk, 0, 0, 0, 0)
    up = INPUT(type=INPUT_KEYBOARD)
    up.u.ki = KEYBDINPUT(vk, 0, KEYEVENTF_KEYUP, 0, 0)
    _send(down, up)


VK_BACK, VK_RETURN = 0x08, 0x0D


def left_button_is_down():
    return bool(user32.GetAsyncKeyState(0x01) & 0x8000)
