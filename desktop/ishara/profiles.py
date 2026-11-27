"""User profiles: calibration model + app settings, stored as JSON in %APPDATA%\\Ishara."""
import json
import os
import re

from .protocol import DEFAULT_MODEL, clamp_model

APPDIR = os.path.join(os.environ.get("APPDATA", "."), "Ishara")
PROFILE_DIR = os.path.join(APPDIR, "profiles")
CONFIG_FILE = os.path.join(APPDIR, "config.json")

DEFAULT_COMMANDS = {
    "click": "left_click", "left click": "left_click",
    "right click": "right_click", "double click": "double_click",
    "middle click": "middle_click", "wheel click": "middle_click",
    "go back": "go_back", "go forward": "go_forward",
    "scroll up": "scroll_up", "scroll down": "scroll_down",
    "start drag": "drag_start", "release": "drag_release", "drop": "drag_release",
    "pause": "pause", "resume": "resume", "stop control": "stop",
    "hand mouse": "hand_mouse", "use mouse": "hand_mouse", "normal mouse": "hand_mouse",
    "head mouse": "resume", "head control": "resume",
    "start typing": "dictation_on", "stop typing": "dictation_off",
    "click lock": "click_lock", "keyboard": "keyboard",
    "center": "recenter", "find cursor": "find_cursor",
    "mute microphone": "mic_sleep", "stop listening": "mic_sleep",
    "unmute microphone": "mic_wake", "start listening": "mic_wake",
    # help menu: opens a numbered list of actions next to the cursor
    "show commands": "help_menu", "what can i say": "help_menu", "help": "help_menu",
    # only active while the help menu is open (ignored otherwise)
    "one": "menu_1", "two": "menu_2", "three": "menu_3", "four": "menu_4",
    "five": "menu_5", "six": "menu_6", "seven": "menu_7", "eight": "menu_8",
    "close": "menu_close", "cancel": "menu_close", "more": "menu_more", "back": "menu_back",
}

DEFAULT_SETTINGS = {
    "voice_enabled": True,
    "mic_device": None,            # None = Windows default microphone
    "dictation_engine": "whisper", # whisper (accurate) | vosk (basic)
    "whisper_model": "base.en",    # base.en (fast) | small.en (best accuracy, slower)
    "vocabulary": [],              # names / words dictation should prefer, e.g. people's names
    "commands": DEFAULT_COMMANDS,
    "command_cooldown": 1.0,       # s, ignore the same command repeated within this time
    "speak": True,                 # spoken feedback through the laptop speaker
    "speech_rate": 1,              # -5 (slow) .. 5 (fast)
    "speech_volume": 90,           # 0 .. 100
    "dwell_enabled": False,
    "dwell_ms": 1200,
    "dwell_radius": 8,             # px the cursor may wobble and still count as still
    "scroll_lines": 3,
    "overlay_enabled": True,
    "overlay_position": "cursor",  # cursor | top | bottom
    "overlay_seconds": 1.6,
    "lock_to_screen": True,
    "widget_enabled": True,        # floating control bar
    "widget_click_through": False, # clicks pass through the bar (it can't be pressed)
    "theme": "light",
    "calibrated": False,
    "practice_passed": [],
}


AXES_VERSION = 2


def _safe(name):
    return re.sub(r"[^A-Za-z0-9 _-]", "", name).strip() or "Default"


def _path(name):
    return os.path.join(PROFILE_DIR, _safe(name) + ".json")


def list_profiles():
    os.makedirs(PROFILE_DIR, exist_ok=True)
    names = sorted(f[:-5] for f in os.listdir(PROFILE_DIR) if f.endswith(".json"))
    return names or ["Default"]


def load(name):
    try:
        with open(_path(name), encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    settings = dict(DEFAULT_SETTINGS)
    settings.update(data.get("settings", {}))
    cmds = dict(DEFAULT_COMMANDS)
    cmds.update(settings.get("commands") or {})
    settings["commands"] = cmds
    model = clamp_model(data.get("model", DEFAULT_MODEL))
    # Axis mapping changed in firmware (forehead mount, auto-detected axes).
    # Old direction settings would now point the wrong way: drop them, recalibrate.
    if data.get("axes_version", 1) < AXES_VERSION:
        for k in ("ix", "iy", "sw"):
            model[k] = 0
        for k in ("rU", "rD", "rL", "rR"):
            model[k] = DEFAULT_MODEL[k]
        settings["calibrated"] = False
    return {"name": _safe(name), "model": model, "settings": settings}


def save(profile):
    os.makedirs(PROFILE_DIR, exist_ok=True)
    tmp = _path(profile["name"]) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"model": profile["model"], "settings": profile["settings"],
                   "axes_version": AXES_VERSION}, f, indent=2)
    os.replace(tmp, _path(profile["name"]))      # atomic: never leaves a half-written file


def delete(name):
    try:
        os.remove(_path(name))
    except OSError:
        pass


def current_name():
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f).get("profile", "Default")
    except Exception:
        return "Default"


def set_current(name):
    os.makedirs(APPDIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({"profile": _safe(name)}, f)
